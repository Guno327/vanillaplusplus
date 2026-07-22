#!/usr/bin/env python3
"""Repin nix/release.json to a minted GitHub release's server-bundle asset.

This is the last step of the release pipeline (HANDOFF.md's "Release
pipeline" section) as of the NixOS flake/module addition: every time a
release is cut, this script must run afterward so nix/release.json stays
current.

GitHub Actions section: the NixOS module's `serverArchive` option now
DEFAULTS to fetching the server bundle from Modrinth's own CDN (a stable,
public, unauthenticated URL - see nix/module.nix and #28's Modrinth
work), so this script also queries Modrinth's public API (no auth needed)
for the version matching this release and records its file's CDN URL +
hash. The GitHub-side asset info (assetId/assetApiUrl/sha256) is still
recorded too - it's what the module's mismatch-check warns against when
an operator points `serverArchive` at a manual/custom build, same as
before this change.

What it does:
1. Resolves a release via the GitHub API - by default the *latest*
   release (draft/prerelease-aware: pass --tag to target a specific one,
   e.g. a prerelease like v0.1.0, since /releases/latest only returns the
   newest non-prerelease/non-draft release).
2. Finds the server-bundle asset (name matching
   vanilla-plus-plus-server-<version>.zip).
3. Downloads the asset's actual bytes back from the release (the same
   Accept: application/octet-stream asset-API endpoint), confirms the
   size matches the API's reported size, and hashes it - the canonical
   bytes are what got uploaded, never the local working tree.
4. Writes nix/release.json with the new tag/version/assetId/assetApiUrl/
   size/sha256 (SRI form)/sha256Hex (plain hex). That GitHub pin is what
   nix/module.nix's default `serverArchive` fetchurl actually uses.

Modrinth is OPT-IN (--modrinth / --modrinth-only), not part of a normal
mint. It used to run unconditionally, back when the module preferred a
Modrinth CDN url; the module has fetched straight from the GitHub release
asset since #28, and this repo is public so that url needs no credentials.
Leaving the lookup on cost every mint ~30s of "not visible yet" retries and
ended with a "re-run with --modrinth-only" instruction for a pin nothing
reads - purely misleading, since the Modrinth project is still in draft and
its public API 404s (#44).

Auth: needs a GitHub token with at least read access to this repo's
releases (the repo is public, so this is mostly about rate limits, not
privacy). Resolution order:
  1. --token argument
  2. GITHUB_TOKEN / VPP_GITHUB_TOKEN environment variable
  3. `gh auth token` (if the gh CLI is installed and logged in)
Never hardcode a token in this file or print one it reads. Modrinth's API
needs no auth at all - it's a public read.

Usage:
  python3 scripts/update_nix_release.py                # newest release
  python3 scripts/update_nix_release.py --tag v0.1.0   # a specific tag
  python3 scripts/update_nix_release.py --modrinth --tag v0.3.0
    # also look up + record the optional Modrinth pin (opt-in; only
    # meaningful once the Modrinth project is out of draft - see #44)
"""
import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASE_JSON = ROOT / "nix" / "release.json"
REPO = "Guno327/vanillaplusplus"
API = "https://api.github.com"
ASSET_PREFIX = "vanilla-plus-plus-server-"
ASSET_SUFFIX = ".zip"

# This project's own Modrinth project (see .github/workflows/publish-
# modrinth.yml / #28) - not a secret, same constant shape as e.g.
# scripts/build_mrpack.py's NEOFORGE_VERSION.
MODRINTH_PROJECT_ID = "Yw2p2yPA"
MODRINTH_API = "https://api.modrinth.com/v2"
MODRINTH_POLL_ATTEMPTS = 6
MODRINTH_POLL_DELAY_S = 5


def get_token(cli_token: str | None) -> str:
    if cli_token:
        return cli_token
    import os

    for var in ("GITHUB_TOKEN", "VPP_GITHUB_TOKEN"):
        if os.environ.get(var):
            return os.environ[var]
    try:
        out = subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, timeout=10
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    print(
        "error: no GitHub token found. Pass --token, set GITHUB_TOKEN/"
        "VPP_GITHUB_TOKEN, or `gh auth login` first.",
        file=sys.stderr,
    )
    sys.exit(1)


def api_get(path: str, token: str) -> dict:
    req = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "vpp-update-nix-release",
        },
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        print(f"error: GitHub API {path} -> HTTP {e.code}: {e.read().decode()[:300]}", file=sys.stderr)
        sys.exit(1)


def download_asset(asset_url: str, token: str, dest: Path) -> None:
    req = urllib.request.Request(
        asset_url,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/octet-stream",
            "User-Agent": "vpp-update-nix-release",
        },
    )
    with urllib.request.urlopen(req) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)


def sha256_digest(path: Path) -> bytes:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.digest()


def sha256_sri(digest: bytes) -> str:
    return "sha256-" + base64.b64encode(digest).decode()


def detect_neoforge_version(zip_path: Path) -> str | None:
    """The NixOS module's java invocation needs
    libraries/net/neoforged/neoforge/<version>/unix_args.txt, mirroring
    run.sh. Detect it from the archive's own central directory (fast --
    doesn't extract the ~370MB payload, just lists entries) so a future
    NeoForge bump doesn't silently break the module's default without
    anyone noticing."""
    pattern = re.compile(r"^libraries/net/neoforged/neoforge/([^/]+)/unix_args\.txt$")
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():
            m = pattern.match(name)
            if m:
                return m.group(1)
    return None


def fetch_modrinth_server_file(version: str, asset_name: str) -> dict | None:
    """Looks up this project's Modrinth version matching `version`
    (e.g. "0.2.0") and returns {"versionId", "url", "sha512"} for the file
    named `asset_name` within it, or None if not found after polling
    (the async publish workflow may not have finished yet - non-fatal)."""
    req = urllib.request.Request(
        f"{MODRINTH_API}/project/{MODRINTH_PROJECT_ID}/version",
        headers={"User-Agent": "vpp-update-nix-release"},
    )
    for attempt in range(1, MODRINTH_POLL_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(req) as r:
                versions = json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Two real causes collapse to the same 404 here: the
                # version genuinely doesn't exist yet (publish workflow
                # still running - polling helps), or the Modrinth PROJECT
                # itself is still in draft/unpublished status (its public
                # API is 404 for everything, versions included, no matter
                # how long you wait - polling never helps, only the owner
                # submitting the project for review does). Ground-truthed
                # 2026-07-20: GET /project/{id} alone 404s the same way
                # while still in draft.
                versions = []
            else:
                print(f"warning: Modrinth API error looking up versions: HTTP {e.code}", file=sys.stderr)
                versions = []
        except urllib.error.URLError as e:
            print(f"warning: Modrinth API unreachable: {e}", file=sys.stderr)
            versions = []

        match = next((v for v in versions if v.get("version_number") == version), None)
        if match:
            file_match = next((f for f in match.get("files", []) if f.get("filename") == asset_name), None)
            if file_match:
                return {
                    "versionId": match["id"],
                    "url": file_match["url"],
                    "sha512": file_match["hashes"]["sha512"],
                }
            print(
                f"warning: found Modrinth version {version!r} but it has no file named {asset_name!r} "
                f"(has: {[f.get('filename') for f in match.get('files', [])]})",
                file=sys.stderr,
            )
            return None

        if attempt < MODRINTH_POLL_ATTEMPTS:
            print(
                f"Modrinth version {version!r} not visible yet (attempt {attempt}/{MODRINTH_POLL_ATTEMPTS}) "
                f"- the publish-modrinth.yml workflow may still be running, retrying in {MODRINTH_POLL_DELAY_S}s..."
            )
            time.sleep(MODRINTH_POLL_DELAY_S)

    print(
        f"warning: Modrinth version {version!r} still not found after polling - "
        "nix/release.json's `modrinth` fields will be omitted. Either the "
        "publish-modrinth.yml workflow run for this release hasn't finished yet "
        "(re-run with --modrinth-only once it has), or the Modrinth project itself "
        f"({MODRINTH_PROJECT_ID}) is still in draft/unpublished status, in which case "
        "polling will never succeed - the project needs to be submitted for review on "
        "modrinth.com first (owner-only action).",
        file=sys.stderr,
    )
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", default=None, help="release tag to pin (default: newest published release, prereleases included)")
    ap.add_argument("--token", default=None, help="GitHub token (prefer env var instead)")
    ap.add_argument(
        "--scratch",
        default="/tmp/vpp-nix-release-scratch",
        help="scratch dir for the downloaded asset (default: /tmp/vpp-nix-release-scratch)",
    )
    ap.add_argument(
        "--modrinth",
        action="store_true",
        help="also look up and record the optional Modrinth pin (opt-in; nothing in "
             "nix/module.nix reads it - see #44)",
    )
    ap.add_argument(
        "--modrinth-only",
        action="store_true",
        help="skip the GitHub download/hash pass and only (re-)fetch the optional Modrinth `modrinth` "
             "fields into the existing nix/release.json - use once the async publish workflow "
             "has actually finished, if the main run above warned it hadn't yet",
    )
    args = ap.parse_args()

    if args.modrinth_only:
        if not RELEASE_JSON.exists():
            print(f"error: {RELEASE_JSON} does not exist yet - run without --modrinth-only first", file=sys.stderr)
            sys.exit(1)
        data = json.loads(RELEASE_JSON.read_text())
        modrinth = fetch_modrinth_server_file(data["version"], data["assetName"])
        if modrinth is None:
            sys.exit(1)
        data["modrinth"] = {"projectId": MODRINTH_PROJECT_ID, **modrinth}
        RELEASE_JSON.write_text(json.dumps(data, indent=2) + "\n")
        print(f"wrote {RELEASE_JSON} (modrinth fields only)")
        return

    token = get_token(args.token)

    if args.tag:
        release = api_get(f"/repos/{REPO}/releases/tags/{args.tag}", token)
    else:
        # NOT /releases/latest: that endpoint excludes prereleases, and every
        # release this project has ever cut is a disclosed beta prerelease, so
        # it 404s here (hit for real during the v0.3.0 mint). List instead and
        # take the newest by published date, prereleases included - drafts
        # excluded, since a draft has no downloadable asset to pin.
        releases = api_get(f"/repos/{REPO}/releases?per_page=20", token)
        published = [r for r in releases if not r.get("draft")]
        if not published:
            print(f"error: no published releases found on {REPO}", file=sys.stderr)
            sys.exit(1)
        release = max(published, key=lambda r: r.get("published_at") or r.get("created_at") or "")
        print(f"resolved newest release: {release['tag_name']}"
              f"{' (prerelease)' if release.get('prerelease') else ''}")

    tag = release["tag_name"]
    assets = release.get("assets", [])
    server_assets = [
        a for a in assets if a["name"].startswith(ASSET_PREFIX) and a["name"].endswith(ASSET_SUFFIX)
    ]
    if not server_assets:
        print(f"error: no {ASSET_PREFIX}*{ASSET_SUFFIX} asset found on release {tag}", file=sys.stderr)
        sys.exit(1)
    if len(server_assets) > 1:
        print(f"error: multiple server-bundle assets found on release {tag}, expected exactly one: "
              f"{[a['name'] for a in server_assets]}", file=sys.stderr)
        sys.exit(1)
    asset = server_assets[0]

    version = asset["name"][len(ASSET_PREFIX):-len(ASSET_SUFFIX)]

    scratch = Path(args.scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    dest = scratch / asset["name"]
    print(f"== downloading {asset['name']} ({asset['size']} bytes) from release {tag} ==")
    download_asset(asset["url"], token, dest)

    actual_size = dest.stat().st_size
    if actual_size != asset["size"]:
        print(
            f"error: downloaded size {actual_size} != API-reported size {asset['size']} "
            "-- refusing to pin a possibly-truncated/corrupt download",
            file=sys.stderr,
        )
        sys.exit(1)

    digest = sha256_digest(dest)
    sri = sha256_sri(digest)
    hex_digest = digest.hex()
    print(f"size OK ({actual_size} bytes), sha256 = {sri} ({hex_digest})")

    neoforge_version = detect_neoforge_version(dest)
    if neoforge_version is None:
        print(
            "warning: could not detect NeoForge version from "
            "libraries/net/neoforged/neoforge/<version>/unix_args.txt inside the "
            "archive -- nix/release.json's neoforgeVersion will be left unset, and "
            "nix/module.nix's hardcoded 21.1.235 fallback will apply. Check whether "
            "the bundle layout changed.",
            file=sys.stderr,
        )
    else:
        print(f"detected NeoForge version: {neoforge_version}")

    if args.modrinth:
        print(f"== looking up Modrinth version {version!r} (project {MODRINTH_PROJECT_ID}) ==")
        modrinth = fetch_modrinth_server_file(version, asset["name"])
    else:
        modrinth = None

    data = {
        "_comment": (
            "Pin of the current minted release's server bundle. nix/module.nix's "
            "serverArchive option defaults to fetching this release's GitHub asset "
            "(repo/tag/assetName) via pkgs.fetchurl, verified against `sha256` at "
            "build time - a real declarative fetch, not a runtime check. This repo is "
            "public, so that url needs no credentials. Regenerated by "
            "scripts/update_nix_release.py at every release cut (see HANDOFF.md's "
            "release pipeline) -- do not hand-edit except for emergencies, and re-run "
            "the script afterward to confirm the hash still matches. An optional "
            "`modrinth` object may also be present if the pin was generated with "
            "--modrinth; nothing in the module reads it today, and it stays absent "
            "while the Modrinth project is in draft (#44)."
        ),
        "repo": REPO,
        "tag": tag,
        "version": version,
        "assetName": asset["name"],
        "assetId": asset["id"],
        "assetApiUrl": asset["url"],
        "size": asset["size"],
        "sha256": sri,
        "sha256Hex": hex_digest,
    }
    if neoforge_version is not None:
        data["neoforgeVersion"] = neoforge_version
    if modrinth is not None:
        data["modrinth"] = {"projectId": MODRINTH_PROJECT_ID, **modrinth}
    RELEASE_JSON.write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote {RELEASE_JSON}")
    if args.modrinth and modrinth is None:
        print(
            "note: the Modrinth pin was requested but the version was not visible - "
            "the publish workflow may still be running, or the project is still in "
            "draft (#44). Nothing in nix/module.nix reads that pin, so this does not "
            "block anything."
        )
    else:
        print("Next: git add nix/release.json && commit -- the flake now resolves this pinned release.")


if __name__ == "__main__":
    main()
