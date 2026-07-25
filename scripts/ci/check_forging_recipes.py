#!/usr/bin/env python3
"""Fast-tier CI check: structural + coverage integrity of vppintegration's
`overgeared:forging` recipes (GitHub #67 Phase 2 - "Extending to the pack's
full material ladder", see `mods-src/vppintegration/README.md`).

These recipes give the Overgeared anvil a way to forge every Silent Gear
tool-head part out of every metal tier this pack's own material ladder
defines (`scripts/gen_gear_materials.py`'s `MATERIALS` list - vanilla
copper/iron, plus Create's andesite alloy/brass/refined radiance and
Allthemodium's allthemodium/vibranium/unobtainium/star-alloy chain), with the
`AbstractSmithingAnvilBlockEntityMixin` correcting the placeholder result's
material at craft time (see `VppIntegration.java`'s class doc). This check
cannot run the mixin or a real Silent Gear/Overgeared jar, so everything it
validates against is a hardcoded, ground-truthed constant (see each
constant's own comment for how it was verified) - the same trust model
`check_vppquests.py`'s TASK_TYPES/REWARD_TYPES already uses for this repo's
other data-driven CI checks.

Checks:
  - Every `data/overgeared/recipe/forging/*.json` under vppintegration's
    resources is valid JSON, is `"type": "overgeared:forging"`, and has the
    required fields (`category`, `hammering` (int >= 1), `key` (a one-symbol
    map of `{"item": ...}` or `{"tag": ...}`), `pattern` (non-empty list of
    strings), `result` (`id` + `count`), `tier` (one of Overgeared's real
    `AnvilTier` values - confirmed via `javap` against
    `net.stirdrem.overgeared.AnvilTier`: stone/iron/above_a/above_b).
  - Every recipe's `result.id` is a real Silent Gear part item id (verified
    against Silent Gear's own `data/silentgear/recipe/gear/*.json` - see
    SG_PART_RESULT_IDS below for exactly which file backs which id).
  - Every recipe's `key` item is either one of Overgeared's own native
    `heated_*` items (verified via `javap` against
    `net.stirdrem.overgeared.item.ModItems`) or one of vppintegration's own
    (verified against `HeatedMetals.java`'s `registerSimpleItem` calls), or
    a `tag` key is one of the gemstone tags the cold-forging recipes already
    use (`c:gems/<gem>`).
  - Full (part type x targeted metal) coverage: every metal in
    TARGETED_METALS has a forging recipe for all 6 of REQUIRED_PART_TYPES -
    fails loudly (naming the exact missing pairs) if not.

Usage: python3 scripts/ci/check_forging_recipes.py [root]
Exit code: 0 if every recipe is structurally valid, every id/tag resolves,
and the full metal-ladder coverage matrix is complete; 1 otherwise.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

FORGING_DIR_REL = Path("mods-src") / "vppintegration" / "src" / "main" / "resources" / "data" / "overgeared" / "recipe" / "forging"

# net.stirdrem.overgeared.AnvilTier's real enum constants (javap against the
# installed overgeared jar): STONE, IRON, ABOVE_A, ABOVE_B -> serialized as
# their lowercase StringRepresentable names.
ALLOWED_TIERS = {"stone", "iron", "above_a", "above_b"}

# Silent Gear part item ids a "TOOL_HEADS"-category forging recipe can
# legitimately produce, keyed by the (arbitrary) short part-type name this
# check uses internally. Ground-truthed against Silent Gear's own
# data/silentgear/recipe/gear/<part>_head.json (or gear/sword_head.json,
# whose OWN "result.id" is "silentgear:sword_blade", not "sword_head" - the
# file name and the item id are not the same string; this was a real bug the
# Phase 1 boot test caught, see mods-src/vppintegration/README.md).
PART_TYPE_RESULT_IDS = {
    "axe_head": "silentgear:axe_head",
    "hammer_head": "silentgear:hammer_head",
    "hoe_head": "silentgear:hoe_head",
    "pickaxe_head": "silentgear:pickaxe_head",
    "shovel_head": "silentgear:shovel_head",
    "sword_blade": "silentgear:sword_blade",
}
RESULT_ID_TO_PART_TYPE = {v: k for k, v in PART_TYPE_RESULT_IDS.items()}
REQUIRED_PART_TYPES = set(PART_TYPE_RESULT_IDS)

# Overgeared's own native heated-metal items (javap against
# net.stirdrem.overgeared.item.ModItems: HEATED_IRON_INGOT/HEATED_COPPER_INGOT
# are the only two backed by a plain vanilla ingredient this pack's own
# material ladder also uses - HEATED_STEEL_INGOT/HEATED_CRUDE_STEEL/
# HEATED_SILVER_INGOT/HEATED_NETHERITE_ALLOY exist too but aren't wired to
# any Silent Gear material in this pack, so they're deliberately not mapped
# to a material below).
NATIVE_HEATED_ITEM_TO_MATERIAL = {
    "overgeared:heated_copper_ingot": "copper",
    "overgeared:heated_iron_ingot": "iron",
}

# vppintegration's own heated-metal items (HeatedMetals.java's
# `registerSimpleItem` calls) - one per this pack's own material-ladder tier
# beyond copper/iron (scripts/gen_gear_materials.py's MATERIALS list is the
# ground-truth source for this list: vpp_andesite_alloy/vpp_brass/
# vpp_refined_radiance/vpp_allthemodium/vpp_vibranium/vpp_unobtainium/
# vpp_star_alloy).
VPPINTEGRATION_HEATED_ITEM_TO_MATERIAL = {
    "vppintegration:heated_andesite_alloy": "andesite_alloy",
    "vppintegration:heated_brass_ingot": "brass",
    "vppintegration:heated_refined_radiance": "refined_radiance",
    "vppintegration:heated_allthemodium_ingot": "allthemodium",
    "vppintegration:heated_vibranium_ingot": "vibranium",
    "vppintegration:heated_unobtainium_ingot": "unobtainium",
    "vppintegration:heated_star_alloy": "star_alloy",
}

KNOWN_KEY_ITEM_TO_MATERIAL = {**NATIVE_HEATED_ITEM_TO_MATERIAL, **VPPINTEGRATION_HEATED_ITEM_TO_MATERIAL}

# Gemstone tags the existing cold-forging recipes use (c:gems/<gem> - not
# part of this check's own metal-ladder coverage requirement, just needs to
# be a recognized, non-error key so this check doesn't flag the existing
# cold-forging recipes as broken).
KNOWN_KEY_TAGS = {
    "c:gems/cinnabar", "c:gems/fluorite", "c:gems/peridot",
    "c:gems/ruby", "c:gems/sapphire",
}

# This pack's own metal ladder (GitHub #67 Phase 2 scope) - every one of
# these must have a forging recipe for all 6 REQUIRED_PART_TYPES. Copper/iron
# are vanilla-tier (Phase 1); the remaining 7 are this pack's own Create/
# Allthemodium material-ladder tiers (scripts/gen_gear_materials.py).
TARGETED_METALS = {
    "copper", "iron",
    "andesite_alloy", "brass", "refined_radiance",
    "allthemodium", "vibranium", "unobtainium", "star_alloy",
}


def _iter_forging_files(root):
    d = root / FORGING_DIR_REL
    if not d.is_dir():
        return []
    return sorted(d.glob("*.json"))


def check_forging_recipes(root):
    """Returns (errors, stats)."""
    errors = []
    stats = {"recipes": 0, "materials_covered": 0}
    coverage = {}  # material -> set of part types

    for path in _iter_forging_files(root):
        rel = path.relative_to(root)
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errors.append(f"{rel}: invalid JSON: {e}")
            continue
        if not isinstance(doc, dict):
            errors.append(f"{rel}: top-level value is not an object")
            continue

        stats["recipes"] += 1

        if doc.get("type") != "overgeared:forging":
            errors.append(f"{rel}: 'type' is {doc.get('type')!r}, expected 'overgeared:forging'")
            continue

        if not isinstance(doc.get("category"), str):
            errors.append(f"{rel}: 'category' is missing/not a string")

        hammering = doc.get("hammering")
        if not isinstance(hammering, int) or isinstance(hammering, bool) or hammering < 1:
            errors.append(f"{rel}: 'hammering' is missing/not a positive int")

        tier = doc.get("tier", "stone")
        if tier not in ALLOWED_TIERS:
            errors.append(f"{rel}: 'tier' is {tier!r}, expected one of {sorted(ALLOWED_TIERS)}")

        pattern = doc.get("pattern")
        if not isinstance(pattern, list) or not pattern or not all(isinstance(p, str) for p in pattern):
            errors.append(f"{rel}: 'pattern' is missing/not a non-empty list of strings")

        # --- key ---
        key = doc.get("key")
        material = None
        if not isinstance(key, dict) or not key:
            errors.append(f"{rel}: 'key' is missing/not a non-empty object")
        else:
            for symbol, ingredient in key.items():
                if not isinstance(ingredient, dict):
                    errors.append(f"{rel}: key symbol {symbol!r} is not an object")
                    continue
                if "item" in ingredient:
                    item_id = ingredient["item"]
                    if item_id not in KNOWN_KEY_ITEM_TO_MATERIAL:
                        errors.append(
                            f"{rel}: key item {item_id!r} is not a known heated-metal item "
                            f"(native Overgeared or vppintegration's own HeatedMetals.java)"
                        )
                    else:
                        material = KNOWN_KEY_ITEM_TO_MATERIAL[item_id]
                elif "tag" in ingredient:
                    tag_id = ingredient["tag"]
                    if tag_id not in KNOWN_KEY_TAGS:
                        errors.append(f"{rel}: key tag {tag_id!r} is not a known cold-forging gem tag")
                else:
                    errors.append(f"{rel}: key symbol {symbol!r} has neither 'item' nor 'tag'")

        # --- result ---
        result = doc.get("result")
        part_type = None
        if not isinstance(result, dict) or not isinstance(result.get("id"), str):
            errors.append(f"{rel}: 'result' is missing/not an object with a string 'id'")
        else:
            result_id = result["id"]
            if result_id not in RESULT_ID_TO_PART_TYPE:
                errors.append(
                    f"{rel}: result id {result_id!r} is not a known Silent Gear tool-head part id "
                    f"(expected one of {sorted(PART_TYPE_RESULT_IDS.values())})"
                )
            else:
                part_type = RESULT_ID_TO_PART_TYPE[result_id]
            if not isinstance(result.get("count", 1), int):
                errors.append(f"{rel}: result 'count' is not an int")

        if material is not None and part_type is not None:
            coverage.setdefault(material, set()).add(part_type)

    stats["materials_covered"] = len(coverage)

    for metal in sorted(TARGETED_METALS):
        have = coverage.get(metal, set())
        missing = REQUIRED_PART_TYPES - have
        if missing:
            errors.append(
                f"metal {metal!r} is missing forging recipes for part type(s): {sorted(missing)}"
            )

    return errors, stats


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else REPO_ROOT

    errors, stats = check_forging_recipes(root)

    if errors:
        print(f"check_forging_recipes: FAIL - {len(errors)} issue(s):")
        for err in errors:
            print(f"  {err}")
        return 1

    print(
        "check_forging_recipes: PASS - "
        f"{stats['recipes']} recipe(s) valid, "
        f"{len(TARGETED_METALS)} metal(s) x {len(REQUIRED_PART_TYPES)} part type(s) fully covered"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
