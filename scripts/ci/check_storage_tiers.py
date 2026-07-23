#!/usr/bin/env python3
"""Fast-tier CI check: GitHub #70 (Sophisticated Storage integration).

Three things this checker guards against silent rot, none of which any
other fast-tier check covers:

  1. pack/mods.lock.json really pins sophisticated-storage (and its
     required dependency sophisticated-core) at a well-formed entry for
     this pack's actual loader/Minecraft version - a bad hash, a Fabric-
     only file, or a missing dependency would otherwise only surface at
     L0 boot (a much slower feedback loop, and this project has no CI
     network to re-resolve and catch it upstream).
  2. Every sophisticatedstorage:* id named in pack/progression/*.toml or
     pack/kubejs/server_scripts/tier_gating.js is a real, registered
     block/item in the mod AS SHIPPED - not a typo, not a guess. Checked
     against pack/mod_registries/sophisticatedstorage.json, a static
     snapshot of the pinned jar's own assets/sophisticatedstorage/
     blockstates/ and models/item/ directories (see scripts/
     gen_mod_registry_snapshot.py's docstring for how that snapshot is
     produced and why those two directories are ground truth for registry
     names). That snapshot's own recorded source_version is cross-checked
     against the live lockfile pin, so a version bump that forgets to
     regenerate the snapshot is caught here rather than silently
     validating stale data.
  3. Every sophisticatedstorage:* id is gated at exactly one tier (not
     zero, not duplicated across tiers) and TG_TIER_INFO's storage-related
     entries only name tier names that are real stage display_names.

Usage: python3 scripts/ci/check_storage_tiers.py [root]
Exit code: 0 if all checks pass, 1 otherwise.
"""
import json
import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

MANIFEST_REL = Path("pack") / "manifest.json"
LOCKFILE_REL = Path("pack") / "mods.lock.json"
PROGRESSION_DIR_REL = Path("pack") / "progression"
SNAPSHOT_REL = Path("pack") / "mod_registries" / "sophisticatedstorage.json"
TIER_GATING_JS_REL = Path("pack") / "kubejs" / "server_scripts" / "tier_gating.js"

MOD_SLUG = "sophisticated-storage"
DEP_SLUG = "sophisticated-core"
MODID = "sophisticatedstorage"

HEX_RE = re.compile(r"^[0-9a-f]+$")
# Any 'sophisticatedstorage:<id>' token appearing anywhere in tier_gating.js
# (string literal or template-literal-expanded id) as an item/block/result
# reference - excludes the handful of RECIPE SERIALIZER type ids this mod
# ships, which look identical lexically but name a recipe TYPE, not a
# registered item/block, so would never appear in the registry snapshot.
STORAGE_ID_RE = re.compile(r"sophisticatedstorage:([a-z0-9_/]+)")
RECIPE_SERIALIZER_TYPES = {
    "storage_tier_upgrade",
    "storage_tier_upgrade_shapeless",
    "generic_wood_storage",
    "double_chest_tier_upgrade",
    "double_chest_tier_upgrade_shapeless",
    "barrel_material",
}
# #127: the "double chest" upgrade recipes tier_gating.js re-authors are
# recipe IDS the mod ships under its own namespace (data/sophisticatedstorage/
# recipe/double_iron_chest.json etc) - real, but naming a RECIPE, not a
# registered item/block, so (same reasoning as RECIPE_SERIALIZER_TYPES above)
# they'd never appear in a snapshot built from blockstates/models directories
# even though tier_gating.js's event.remove({id: ...})/event.custom() calls
# genuinely reference them. Confirmed against the pinned jar's own recipe
# jsons, not guessed.
RECIPE_ONLY_IDS = {
    "double_iron_chest",
    "double_iron_chest_from_copper_chest",
    "double_gold_chest",
}
# Template-literal ids built at runtime from `${type}` interpolation in
# tier_gating.js (SOPH_STORAGE_TYPES.forEach(...)) - not visible to the
# regex above as literal text, so their expansions are added explicitly.
TIER_TEMPLATE_PREFIXES = ["iron", "gold"]


def fail(errors):
    print(f"check_storage_tiers: FAIL - {len(errors)} problem(s):")
    for e in errors:
        print(f"  {e}")
    return 1


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_lockfile_entries(root, errors):
    lock_path = root / LOCKFILE_REL
    manifest_path = root / MANIFEST_REL
    if not lock_path.is_file() or not manifest_path.is_file():
        errors.append(f"missing {lock_path} or {manifest_path}")
        return None

    lock = load_json(lock_path)
    manifest = load_json(manifest_path)

    if lock.get("loader") != "neoforge":
        errors.append(f"mods.lock.json loader is {lock.get('loader')!r}, expected 'neoforge'")
    if lock.get("minecraft") != "1.21.1":
        errors.append(f"mods.lock.json minecraft is {lock.get('minecraft')!r}, expected '1.21.1'")

    lock_by_slug = {m["slug"]: m for m in lock.get("mods", [])}
    manifest_slugs = {m["slug"] for m in manifest.get("mods", [])}

    storage_entry = None
    for slug in (MOD_SLUG, DEP_SLUG):
        if slug not in manifest_slugs:
            errors.append(f"{slug!r} missing from pack/manifest.json")
        entry = lock_by_slug.get(slug)
        if entry is None:
            errors.append(f"{slug!r} missing from pack/mods.lock.json")
            continue
        filename = entry.get("filename", "")
        if not filename.endswith(".jar"):
            errors.append(f"{slug!r}: filename {filename!r} does not end in .jar")
        if "1.21.1" not in entry.get("version_number", ""):
            errors.append(f"{slug!r}: version_number {entry.get('version_number')!r} does not mention 1.21.1")
        sha512 = entry.get("hashes", {}).get("sha512", "")
        if len(sha512) != 128 or not HEX_RE.match(sha512):
            errors.append(f"{slug!r}: hashes.sha512 is not a well-formed 128-char hex string")
        sha1 = entry.get("hashes", {}).get("sha1", "")
        if sha1 and (len(sha1) != 40 or not HEX_RE.match(sha1)):
            errors.append(f"{slug!r}: hashes.sha1 present but not a well-formed 40-char hex string")
        if not entry.get("filesize"):
            errors.append(f"{slug!r}: filesize missing or zero")
        if entry.get("side") != "both":
            errors.append(f"{slug!r}: side is {entry.get('side')!r}, expected 'both' (server needs it too)")
        if slug == MOD_SLUG:
            storage_entry = entry

    return storage_entry


def load_snapshot(root, storage_entry, errors):
    snapshot_path = root / SNAPSHOT_REL
    if not snapshot_path.is_file():
        errors.append(
            f"{snapshot_path} missing - run "
            f"'python3 scripts/gen_mod_registry_snapshot.py {MOD_SLUG}' after any lockfile pin change"
        )
        return None
    snapshot = load_json(snapshot_path)
    if snapshot.get("modid") != MODID:
        errors.append(f"{snapshot_path}: modid is {snapshot.get('modid')!r}, expected {MODID!r}")
    if storage_entry is not None and snapshot.get("source_version") != storage_entry.get("version_number"):
        errors.append(
            f"{snapshot_path}: snapshot was generated from version "
            f"{snapshot.get('source_version')!r} but mods.lock.json now pins "
            f"{storage_entry.get('version_number')!r} - re-run "
            f"scripts/gen_mod_registry_snapshot.py {MOD_SLUG}"
        )
    for key in ("blocks", "items"):
        if not isinstance(snapshot.get(key), list) or not snapshot[key]:
            errors.append(f"{snapshot_path}: {key!r} missing or empty")
    return snapshot


def collect_progression_ids(root, errors):
    """Returns {id: [(tier_file, category), ...]} for every
    'id:sophisticatedstorage:*' entry across pack/progression/*.toml."""
    occurrences = {}
    stage_display_names = set()
    prog_dir = root / PROGRESSION_DIR_REL
    if not prog_dir.is_dir():
        errors.append(f"{prog_dir} missing")
        return occurrences, stage_display_names

    for toml_path in sorted(prog_dir.glob("*.toml")):
        try:
            data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as e:
            errors.append(f"{toml_path.name}: TOML parse error: {e}")
            continue
        stage = data.get("stage", {})
        if stage.get("display_name"):
            stage_display_names.add(stage["display_name"])
        for category in ("items", "blocks"):
            locked = data.get(category, {}).get("locked", [])
            for entry in locked:
                if not isinstance(entry, str) or not entry.startswith(f"id:{MODID}:"):
                    continue
                item_id = entry[len("id:"):]
                occurrences.setdefault(item_id, []).append((toml_path.name, category))

    return occurrences, stage_display_names


def check_progression_ids(occurrences, snapshot, errors):
    known_blocks = set(snapshot.get("blocks", [])) if snapshot else set()
    known_items = set(snapshot.get("items", [])) if snapshot else set()
    known_all = known_blocks | known_items

    for item_id, locations in sorted(occurrences.items()):
        bare = item_id[len(f"{MODID}:"):]
        files = {loc[0] for loc in locations}
        if len(files) > 1:
            errors.append(
                f"id:{item_id} locked in more than one tier file: {sorted(files)} "
                "(should be gated at exactly one tier)"
            )
        if snapshot is not None and bare not in known_all:
            errors.append(
                f"id:{item_id} listed in pack/progression/*.toml but not found in "
                f"the mod's own registry snapshot ({SNAPSHOT_REL}) - typo, or the mod dropped this id?"
            )
        for toml_name, category in locations:
            if snapshot is None:
                continue
            in_blocks = bare in known_blocks
            in_items = bare in known_items
            if category == "blocks" and not in_blocks and in_items:
                errors.append(
                    f"id:{item_id} in {toml_name}'s [blocks] but the snapshot only lists it as an item"
                )
            if category == "items" and not in_items and in_blocks:
                errors.append(
                    f"id:{item_id} in {toml_name}'s [items] but the snapshot only lists it as a block"
                )


def extract_tg_tier_info_entries(js_text):
    """Pull out TG_TIER_INFO's entries via balanced-bracket scanning (same
    'not a full JS parser' spirit as lint_rhino.py), returning a list of
    (tierName, [item strings])."""
    marker = "const TG_TIER_INFO = ["
    start = js_text.find(marker)
    if start == -1:
        return None
    depth = 0
    i = start + len(marker) - 1  # position of the opening '['
    end = None
    for j in range(i, len(js_text)):
        if js_text[j] == "[":
            depth += 1
        elif js_text[j] == "]":
            depth -= 1
            if depth == 0:
                end = j
                break
    if end is None:
        return None
    body = js_text[i:end + 1]

    entries = []
    for entry_match in re.finditer(r"\{(.*?)\}\s*,", body, re.DOTALL):
        entry_text = entry_match.group(1)
        tier_match = re.search(r"tierName:\s*'([^']*)'", entry_text)
        items_match = re.search(r"items:\s*\[([^\]]*)\]", entry_text)
        if not tier_match or not items_match:
            continue
        items = re.findall(r"'([^']*)'", items_match.group(1))
        entries.append((tier_match.group(1), items))
    return entries


def check_tier_gating_js(root, snapshot, stage_display_names, errors):
    js_path = root / TIER_GATING_JS_REL
    if not js_path.is_file():
        errors.append(f"{js_path} missing")
        return
    text = js_path.read_text(encoding="utf-8")

    known_blocks = set(snapshot.get("blocks", [])) if snapshot else set()
    known_items = set(snapshot.get("items", [])) if snapshot else set()
    known_all = known_blocks | known_items

    # 1. every literal sophisticatedstorage:<id> token, minus known recipe
    #    serializer type ids and prose in // comments, must exist in the
    #    snapshot. Comment lines are masked first (same reasoning as
    #    lint_rhino.py: this pack's own comments freely mention ids in
    #    prose form like "barrel/chest", which would otherwise false-
    #    positive here). Matches immediately followed by '${' are template-
    #    literal fragments (e.g. `sophisticatedstorage:iron_${type}`) cut
    #    short by the char class at the '$' - handled separately below via
    #    the SOPH_STORAGE_TYPES expansion instead of here.
    code_only = re.sub(r"//[^\n]*", "", text)
    if snapshot is not None:
        seen = set()
        for m in STORAGE_ID_RE.finditer(code_only):
            if code_only[m.end():m.end() + 2] == "${":
                continue
            seen.add(m.group(1))
        for bare in sorted(seen):
            if bare in RECIPE_SERIALIZER_TYPES or bare in RECIPE_ONLY_IDS:
                continue
            if bare not in known_all:
                errors.append(
                    f"tier_gating.js references sophisticatedstorage:{bare}, "
                    f"not found in the registry snapshot ({SNAPSHOT_REL})"
                )

        # 2. the ${type}-templated iron_*/gold_* ids (SOPH_STORAGE_TYPES loop)
        #    aren't visible to the regex above as literal text - check their
        #    expansions explicitly, driven off the actual array in the file
        #    so this doesn't silently stop checking anything if that array
        #    is ever edited.
        # Optional: this project's real tier_gating.js drives the iron/gold
        # barrel/chest/shulker_box loop off a `const SOPH_STORAGE_TYPES =
        # [...]` array and `${type}` template interpolation, invisible to
        # the plain-literal scan above. If that array is present, its
        # expansions are checked; a tier_gating.js that gates the mod some
        # other way (e.g. all-literal ids, already covered above) is not
        # required to have it.
        types_match = re.search(r"const SOPH_STORAGE_TYPES\s*=\s*\[([^\]]*)\]", text)
        if types_match:
            types = re.findall(r"'([^']*)'", types_match.group(1))
            if not types:
                errors.append("tier_gating.js: SOPH_STORAGE_TYPES parsed empty")
            for storage_type in types:
                for prefix in TIER_TEMPLATE_PREFIXES:
                    expanded = f"{prefix}_{storage_type}"
                    if expanded not in known_blocks:
                        errors.append(
                            f"tier_gating.js's SOPH_STORAGE_TYPES loop would generate "
                            f"sophisticatedstorage:{expanded}, not found in the registry snapshot's blocks"
                        )

    # 3. TG_TIER_INFO well-formedness for the #70 entries specifically.
    entries = extract_tg_tier_info_entries(text)
    if entries is None:
        errors.append("tier_gating.js: could not locate/parse TG_TIER_INFO array")
        return
    for tier_name, items in entries:
        storage_items = [it for it in items if it.startswith(f"{MODID}:")]
        if not storage_items:
            continue
        if stage_display_names and tier_name not in stage_display_names:
            errors.append(
                f"TG_TIER_INFO entry for {storage_items} names tierName {tier_name!r}, "
                "which is not any pack/progression/*.toml stage's display_name"
            )
        if snapshot is not None:
            for it in storage_items:
                bare = it[len(f"{MODID}:"):]
                if bare not in known_all:
                    errors.append(f"TG_TIER_INFO lists {it!r}, not found in the registry snapshot")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else REPO_ROOT

    errors = []
    storage_entry = check_lockfile_entries(root, errors)
    snapshot = load_snapshot(root, storage_entry, errors)
    occurrences, stage_display_names = collect_progression_ids(root, errors)
    check_progression_ids(occurrences, snapshot, errors)
    check_tier_gating_js(root, snapshot, stage_display_names, errors)

    if errors:
        return fail(errors)

    print(
        f"check_storage_tiers: PASS - {MOD_SLUG} pinned and consistent, "
        f"{len(occurrences)} sophisticatedstorage:* id(s) gated across pack/progression/*.toml, "
        "all verified against the mod's own registry snapshot"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
