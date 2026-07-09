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


def resolve_one(slug, minecraft, loader):
    params = urllib.parse.urlencode(
        {"loaders": json.dumps([loader]), "game_versions": json.dumps([minecraft])}
    )
    versions = api(f"https://api.modrinth.com/v2/project/{slug}/version?{params}")
    if not versions:
        raise SystemExit(f"no versions found for {slug} on {loader} {minecraft}")
    v = versions[0]  # Modrinth returns newest-first
    primary = next((f for f in v["files"] if f.get("primary")), v["files"][0])
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
        else:
            info = resolve_one(slug, minecraft, loader)
        info["side"] = entry.get("side", "both")
        info["phase"] = entry.get("phase")
        info["note"] = entry.get("note", "")
        resolved.append(info)
        changed = existing.get(slug, {}).get("version_id") != info["version_id"]
        marker = "NEW/UPDATED" if slug not in existing or changed else "unchanged"
        print(f"  -> {info['version_number']} ({info['filename']}) [{marker}]", file=sys.stderr)

    LOCKFILE.write_text(json.dumps({"minecraft": minecraft, "loader": loader, "mods": resolved}, indent=2) + "\n")
    print(f"wrote {LOCKFILE}", file=sys.stderr)


if __name__ == "__main__":
    main()
