#!/usr/bin/env python3
"""Repin nix/release.json to a minted GitHub release's server-bundle asset.

This is the last step of the release pipeline (HANDOFF.md's "Release
pipeline" section) as of the NixOS flake/module addition: every time a
release is cut, this script must run afterward so nix/release.json stays
current. The NixOS module's primary deployment path is a MANUALLY
downloaded release zip (`services.vanillaplusplus.serverArchive` -- see
README.md's "Running on NixOS" section for why: there's no verified,
purely-declarative way to auto-fetch a private repo's release asset from
within a Nix derivation in this project's validation environment, so we
don't ship that as a real mechanism). nix/release.json's job now is purely
informational/verification: it records which release is "current" and
that release's real sha256, so (a) operators know what to download, and
(b) the module's sync script can warn (not fail) if the archive an
operator points it at doesn't match the pinned hash.

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
   size/sha256 (SRI form)/sha256Hex (plain hex, what the module's sync
   script compares an operator-provided archive against).

Auth: needs a GitHub token with at least read access to this private
repo's releases. Resolution order:
  1. --token argument
  2. GITHUB_TOKEN / VPP_GITHUB_TOKEN environment variable
  3. `gh auth token` (if the gh CLI is installed and logged in)
Never hardcode a token in this file or print one it reads.

Usage:
  python3 scripts/update_nix_release.py                # latest release
  python3 scripts/update_nix_release.py --tag v0.1.0   # a specific tag
"""
import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", default=None, help="release tag to pin (default: latest)")
    ap.add_argument("--token", default=None, help="GitHub token (prefer env var instead)")
    ap.add_argument(
        "--scratch",
        default="/tmp/vpp-nix-release-scratch",
        help="scratch dir for the downloaded asset (default: /tmp/vpp-nix-release-scratch)",
    )
    args = ap.parse_args()

    token = get_token(args.token)

    if args.tag:
        release = api_get(f"/repos/{REPO}/releases/tags/{args.tag}", token)
    else:
        release = api_get(f"/repos/{REPO}/releases/latest", token)

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

    data = {
        "_comment": (
            "Informational pin of the current minted GitHub release, for the NixOS "
            "module's manually-downloaded serverArchive path to verify against (warns, "
            "doesn't fail, on a mismatch -- custom/local bundles are supported). "
            "Regenerated by scripts/update_nix_release.py at every release cut (see "
            "HANDOFF.md's release pipeline) -- do not hand-edit except for emergencies, "
            "and re-run the script afterward to confirm the hash still matches."
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
    RELEASE_JSON.write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote {RELEASE_JSON}")
    print("Next: git add nix/release.json && commit -- the flake now resolves this pinned release.")


if __name__ == "__main__":
    main()
