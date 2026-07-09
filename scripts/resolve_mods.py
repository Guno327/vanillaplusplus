#!/usr/bin/env python3
"""Resolve pack/manifest.json entries against the Modrinth API and write pack/mods.lock.json.

The lockfile is the reproducible, git-friendly source of truth for exact files/hashes.
Re-run this after editing manifest.json to pick up new mods or version bumps.
"""
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
