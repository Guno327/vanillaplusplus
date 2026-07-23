#!/usr/bin/env python3
"""Resolve pack/manifest.json entries against Modrinth (default) or CurseForge
(for the small set of mods that are CurseForge-exclusive, e.g. the FTB suite)
and write pack/mods.lock.json.

The lockfile is the reproducible, git-friendly source of truth for exact files/hashes.
Re-run this after editing manifest.json to pick up new mods or version bumps.

CurseForge entries (manifest "source": "curseforge") exist because FTB Quests/
Teams/Library are not published on Modrinth at all (confirmed by search - only
third-party addons for them are). There's no CurseForge API key in this sandbox,
so entries are resolved by direct CDN download rather than the official API:
CurseForge serves files from https://mediafilez.forgecdn.net/files/<fileId
without its last 3 digits>/<fileId's last 3 digits, zero-padded>/<filename> with
no auth required (verified - this is the same CDN a browser's download button
hits). The fileId + exact filename per Minecraft/loader version must be looked
up manually (e.g. via the CurseForge files page) and pinned in manifest.json,
since we have no keyless API to query them - update those two fields by hand
on a version bump, same spirit as everything else in this no-packwiz pipeline.

A third manifest "source", "local", exists for this pack's own hand-rolled
mods (GitHub #67 established the convention: each one lives under its own
mods-src/<modid>/ tree, see that directory's README.md for why). There is no
remote host for these - the manifest entry's "local_path" field must point at
a jar a real `gradle build` in that mod's own tree already produced; see
resolve_one_local() below for exactly what gets hashed and how build_server.py/
build_mrpack.py consume the result differently from a downloaded mod.
"""
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "pack" / "manifest.json"
LOCKFILE = ROOT / "pack" / "mods.lock.json"
UA = {"User-Agent": "vanilla-plus-plus/0.1 (+github.com/gunnarhovik327)"}


def api(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def pick_file(files, loader, slug):
    """Pick the file matching our loader out of a version's file list.

    Caught via an actual L0 boot-log FML warning ("is a Fabric mod and
    cannot be loaded") for noisiumed: a single Modrinth *version* can
    bundle jars for multiple loaders at once (fabric/forge/neoforge all
    published under one version_number), and the 'primary' flag is not
    guaranteed to point at the file for the loader we actually queried for
    - noisiumed's primary file was its Fabric jar even when queried with
    loaders=["neoforge"]. Prefer a file whose name unambiguously names our
    loader; only fall back to 'primary'/first when that's not possible.
    """
    if len(files) == 1:
        return files[0]
    loader_matches = [f for f in files if loader.lower() in f["filename"].lower()]
    if len(loader_matches) == 1:
        return loader_matches[0]
    if len(loader_matches) > 1:
        return next((f for f in loader_matches if f.get("primary")), loader_matches[0])
    print(f"  WARNING: {slug}: no filename unambiguously matches loader {loader!r} among "
          f"{[f['filename'] for f in files]}, falling back to primary/first - verify manually",
          file=sys.stderr)
    return next((f for f in files if f.get("primary")), files[0])


def resolve_one(slug, minecraft, loader, pin_version=None):
    """pin_version: exact Modrinth version_number to use instead of newest -
    for cases where a dependent mod hasn't caught up to the latest release
    yet (e.g. a compat addon pinned to an older base mod's version range)."""
    params = urllib.parse.urlencode(
        {"loaders": json.dumps([loader]), "game_versions": json.dumps([minecraft])}
    )
    versions = api(f"https://api.modrinth.com/v2/project/{slug}/version?{params}")
    if not versions:
        raise SystemExit(f"no versions found for {slug} on {loader} {minecraft}")
    if pin_version:
        matches = [ver for ver in versions if ver["version_number"] == pin_version]
        if not matches:
            raise SystemExit(f"pinned version {pin_version!r} not found for {slug}")
        v = matches[0]
    else:
        v = versions[0]  # Modrinth returns newest-first
    primary = pick_file(v["files"], loader, slug)
    return {
        "slug": slug,
        "project_id": v["project_id"],
        "version_id": v["id"],
        "version_number": v["version_number"],
        "filename": primary["filename"],
        "url": primary["url"],
        "hashes": primary["hashes"],
        "filesize": primary["size"],
    }


def resolve_one_local(slug, entry):
    """Resolve a manifest entry whose "source" is "local" - a mod built from
    this repo's own mods-src/<modid>/ tree (GitHub #67 established this
    convention: every hand-rolled Vanilla++ mod lives under mods-src/ with
    its own NeoForge gradle build, independently publishable to Modrinth,
    see mods-src/<modid>/README.md) rather than resolved from Modrinth/
    CurseForge. There is no remote URL for these - "local_path" (manifest
    field, repo-relative) must point at the real jar a real `gradle build`
    already produced under that mod's own build/libs/. This function does
    NOT invoke gradle itself (this pipeline has never shelled out to a
    build tool for any other mod source either) - it only hashes whatever
    jar is already sitting at local_path, exactly the same "pin whatever
    real artifact already exists" spirit as resolve_one_curseforge above.

    check_lockfile.py (scripts/ci/) only requires the lock entry's "url" to
    be a non-empty string, not a fetchable one, so a local mod's lock entry
    uses a repo-relative path string in that field (documented below)
    instead of an HTTP URL - build_server.py/build_mrpack.py both special-
    case source=="local" to copy from local_path rather than download from
    "url"."""
    local_path = entry.get("local_path")
    if not local_path:
        raise SystemExit(f"{slug}: manifest entry has \"source\": \"local\" but no \"local_path\"")
    jar_path = ROOT / local_path
    if not jar_path.is_file():
        raise SystemExit(
            f"{slug}: local_path {local_path!r} does not exist - build it first, e.g.:\n"
            f"  cd mods-src/{slug} && gradle build\n"
            f"(see mods-src/{slug}/README.md \"Build instructions\")"
        )
    data = jar_path.read_bytes()
    return {
        "slug": slug,
        "project_id": entry.get("local_project_id", slug),
        "version_id": entry.get("mod_version", "local"),
        "version_number": entry.get("mod_version", "local"),
        "filename": jar_path.name,
        # Not a fetchable URL - a repo-relative path documenting where the
        # jar this hash matches actually lives. build_server.py/
        # build_mrpack.py know to copy from "local_path" (below), not fetch
        # this field, for source=="local" entries.
        "url": local_path,
        "local_path": local_path,
        "hashes": {
            "sha1": hashlib.sha1(data).hexdigest(),
            "sha512": hashlib.sha512(data).hexdigest(),
        },
        "filesize": len(data),
    }


def resolve_one_curseforge(slug, entry):
    file_id = entry["cf_file_id"]
    filename = entry["cf_filename"]
    url = f"https://mediafilez.forgecdn.net/files/{file_id // 1000}/{file_id % 1000:03d}/{filename}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    return {
        "slug": slug,
        "project_id": entry.get("cf_project_slug", slug),
        "version_id": str(file_id),
        "version_number": entry.get("cf_version_number", str(file_id)),
        "filename": filename,
        "url": url,
        "hashes": {
            "sha1": hashlib.sha1(data).hexdigest(),
            "sha512": hashlib.sha512(data).hexdigest(),
        },
        "filesize": len(data),
    }


def main():
    manifest = json.loads(MANIFEST.read_text())
    minecraft = manifest["minecraft"]
    loader = manifest["loader"]

    existing = {}
    if LOCKFILE.exists():
        existing = {m["slug"]: m for m in json.loads(LOCKFILE.read_text())["mods"]}

    resolved = []
    for entry in manifest["mods"]:
        slug = entry["slug"]
        print(f"resolving {slug}...", file=sys.stderr)
        if entry.get("source") == "curseforge":
            info = resolve_one_curseforge(slug, entry)
        elif entry.get("source") == "local":
            info = resolve_one_local(slug, entry)
        else:
            info = resolve_one(slug, minecraft, loader, pin_version=entry.get("pin_version"))
        info["side"] = entry.get("side", "both")
        info["phase"] = entry.get("phase")
        info["note"] = entry.get("note", "")
        resolved.append(info)
        changed = existing.get(slug, {}).get("version_id") != info["version_id"]
        marker = "NEW/UPDATED" if slug not in existing or changed else "unchanged"
        print(f"  -> {info['version_number']} ({info['filename']}) [{marker}]", file=sys.stderr)

    lock = {"minecraft": minecraft, "loader": loader}
    # loader_installer is a manually-pinned NeoForge server-installer spec
    # (issue #64/#82) whose SOURCE OF TRUTH is the manifest, not Modrinth
    # resolution. It MUST be carried into the generated lockfile verbatim:
    # build_server.py hard-fails without it, and this regenerates the whole
    # lockfile, so dropping it here (as this script used to) silently broke
    # every server boot/mint until the next boot-tier run caught it. Copied,
    # not synthesised - the checksum can only come from the real artifact.
    installer = manifest.get("loader_installer")
    if installer is not None:
        lock["loader_installer"] = installer
    lock["mods"] = resolved
    LOCKFILE.write_text(json.dumps(lock, indent=2) + "\n")
    print(f"wrote {LOCKFILE}", file=sys.stderr)


if __name__ == "__main__":
    main()
