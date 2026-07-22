#!/usr/bin/env python3
"""Generate a static, offline snapshot of a mod's own block/item registry
names, for CI checks that need to verify "does this item id actually exist
in the mod as shipped" without network access (see scripts/ci/
check_storage_tiers.py, GitHub #70).

WHY THIS EXISTS. #70 (Sophisticated Storage) requires the CI fast tier to
assert that every sophisticatedstorage:* id referenced in pack/progression/
*.toml and pack/kubejs/server_scripts/tier_gating.js is a real, registered
item/block in the pinned jar - not a typo'd or guessed id. CI has no network
and installs nothing (see scripts/ci/README-equivalent comments in
run_all.py / check_lockfile.py), so that check can't download the jar
itself. This script is the one-time (per version bump), network-using step
that produces the static ground truth those checks read - run it by hand
locally whenever pack/mods.lock.json's pin for the target mod changes,
same workflow as scripts/resolve_mods.py itself.

Ground truth extraction method: a block/item's registry name is derivable
from two directories every Forge/NeoForge mod jar ships for its own
resources - assets/<modid>/blockstates/*.json (one file per registered
BLOCK) and assets/<modid>/models/item/*.json (one file per registered ITEM,
including BlockItems) - both keyed by registry name. This was verified by
hand against sophisticatedstorage-1.21.1-1.5.80.1999.jar: 59 blockstates,
132 item models, and cross-checked against the mod's own lang file and
recipe output ids (data/sophisticatedstorage/recipe/*.json result.id) which
agree exactly - e.g. "iron_barrel" appears in both blockstates and item
models (it's a block with a BlockItem), "stack_upgrade_tier_1" only in item
models (a plain item), matching the mod's actual design.

Usage: python3 scripts/gen_mod_registry_snapshot.py <manifest-slug>
  e.g. python3 scripts/gen_mod_registry_snapshot.py sophisticated-storage
Reads the pinned URL for that slug out of pack/mods.lock.json, downloads it,
reads its own neoforge.mods.toml for the real modid, and writes
pack/mod_registries/<modid>.json.
"""
import json
import sys
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCKFILE = ROOT / "pack" / "mods.lock.json"
OUT_DIR = ROOT / "pack" / "mod_registries"
UA = {"User-Agent": "vanilla-plus-plus/0.1 (+github.com/gunnarhovik327)"}


def find_modid(zf):
    for name in zf.namelist():
        if name.endswith("mods.toml"):
            text = zf.read(name).decode("utf-8", "replace")
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("modId="):
                    return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("could not find modId in any *mods.toml in the jar")


def registry_names(zf, prefix, suffix):
    """Registry name = path relative to prefix, minus suffix - this
    includes subdirectories, since some mods put registry name segments in
    real subfolders (e.g. sophisticatedstorage:chipped/botanist_workbench_
    upgrade, verified against that recipe's own result.id and its
    sophisticatedcore:item_enabled condition's itemRegistryName)."""
    names = set()
    for name in zf.namelist():
        if name.startswith(prefix) and name.endswith(suffix) and name != prefix:
            base = name[len(prefix):-len(suffix)]
            if base:
                names.add(base)
    return names


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        raise SystemExit("usage: gen_mod_registry_snapshot.py <manifest-slug>")
    slug = argv[0]

    lock = json.loads(LOCKFILE.read_text())
    entry = next((m for m in lock["mods"] if m["slug"] == slug), None)
    if entry is None:
        raise SystemExit(f"slug {slug!r} not found in {LOCKFILE}")

    print(f"downloading {entry['url']}...", file=sys.stderr)
    req = urllib.request.Request(entry["url"], headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()

    zf = zipfile.ZipFile(BytesIO(data))
    modid = find_modid(zf)

    blocks = registry_names(zf, f"assets/{modid}/blockstates/", ".json")
    items = registry_names(zf, f"assets/{modid}/models/item/", ".json")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{modid}.json"
    out_path.write_text(json.dumps({
        "modid": modid,
        "source_slug": slug,
        "source_version": entry["version_number"],
        "source_filename": entry["filename"],
        "blocks": sorted(blocks),
        "items": sorted(items),
    }, indent=2) + "\n")
    print(f"wrote {out_path} ({len(blocks)} blocks, {len(items)} items)", file=sys.stderr)


if __name__ == "__main__":
    main()
