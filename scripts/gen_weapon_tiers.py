#!/usr/bin/env python3
"""Gear overhaul Part 3: Epic Fight weapon-type integration.

Epic Fight ships 5 custom weapon types (dagger/greatsword/longsword/spear/
tachi) across 6 material tiers (wood/stone/iron/gold/diamond/netherite,
its own hard ceiling). Silent Gear has no `gear_type` for any of these (only
Java-registered gear types are supported - see DESIGN.md's gear overhaul
section for why: no NeoForge dev/Gradle toolchain in this sandbox to add a
real one), so this generates:

1. `pack/kubejs/startup_scripts/weapon_items.js` - registers 20 new items
   (5 types x 4 new tiers: Allthemodium/Vibranium/Unobtainium/Star Alloy,
   the tiers beyond Epic Fight's native netherite ceiling). Item
   registration is game-registry content, so it has to be a *startup*
   script, not a server script (server_scripts only run once a server/world
   exists; the registry needs to exist before that).
2. `pack/kubejs/data/epicfight/capabilities/weapons/*.json` - one capability
   file per new item, extending Epic Fight's own diamond->netherite stat
   growth outward for the 4 new tiers. Deliberately a flat, modest,
   monotonic bump (not a compounding ratio): Epic Fight's own diamond->
   netherite deltas aren't a clean multiplier in the first place (some
   stats like armor_negation don't even move, or move inconsistently per
   weapon type) - continuing a "ratio" from noisy source data would risk
   producing nonsensical numbers over 4 more steps. There is no live client
   in this sandbox to playtest actual combat balance either way, so a
   simple, disclosed, monotonic formula is the defensible choice over
   hand-waved "realistic-looking" numbers.
3. `pack/kubejs/data/minecraft/tags/item/swords.json` - adds the 20 new
   items to the shared tag (tags MERGE across datapacks by default, unlike
   the plain single-file resources Part 1's material collision bug hit -
   this is additive, not an overwrite risk).
4. `pack/kubejs/server_scripts/weapon_smithing.js` - removes Epic Fight's
   own 30 tiered recipes (they're flat crafting-table recipes straight from
   raw ingots/vanilla swords - the exact thing being eliminated) and adds
   50 new ones (5 types x all 10 tiers): each requires a Silent-Gear-crafted
   `silentgear:sword_blade` part (any material - going through Silent
   Gear's own blueprint+workbench process is what satisfies "the same
   smithing process", not necessarily an exact material match) plus that
   tier's own raw material item (already tier-locked via ProgressiveStages)
   plus a stick. One consistent recipe shape across all 50 rather than
   preserving each weapon type's original distinct shape - a deliberate
   simplification instructions.md explicitly allows ("adjust recipes/
   methods of attaining some gear").
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KUBEJS = ROOT / "pack" / "kubejs"

WEAPON_TYPES = ["dagger", "greatsword", "longsword", "spear", "tachi"]

NATIVE_TIERS = ["wooden", "stone", "iron", "golden", "diamond", "netherite"]
NEW_TIERS = ["vpp_allthemodium", "vpp_vibranium", "vpp_unobtainium", "vpp_star_alloy"]
ALL_TIERS = NATIVE_TIERS + NEW_TIERS

# Raw material item consumed by the smithing-substitute recipe, per tier.
TIER_MATERIAL_ITEM = {
    "wooden": "minecraft:oak_planks",
    "stone": "minecraft:cobblestone",
    "iron": "minecraft:iron_ingot",
    "golden": "minecraft:gold_ingot",
    "diamond": "minecraft:diamond",
    "netherite": "minecraft:netherite_ingot",
    "vpp_allthemodium": "allthemodium:allthemodium_ingot",
    "vpp_vibranium": "allthemodium:vibranium_ingot",
    "vpp_unobtainium": "allthemodium:unobtainium_ingot",
    "vpp_star_alloy": "allthemodium:unobtainium_vibranium_alloy_ingot",
}

# Netherite capability attributes (Epic Fight's own, read directly from the
# installed jar) - the baseline the 4 new tiers grow outward from.
NETHERITE_CAPS = {
    "dagger": {"one_hand": {"armor_negation": 10.0, "max_strikes": 0, "impact": 0.9},
               "two_hand": {"armor_negation": 10.0, "max_strikes": 1, "impact": 0.9}},
    "greatsword": {"common": {"armor_negation": 20.0, "impact": 4.4, "max_strikes": 4}},
    "longsword": {"common": {"armor_negation": 10.0, "impact": 3.0, "max_strikes": 2}},
    "spear": {"one_hand": {"armor_negation": 25.0, "impact": 2.9, "max_strikes": 1},
              "two_hand": {"armor_negation": 10.0, "impact": 2.4, "max_strikes": 3}},
    "tachi": {"common": {"armor_negation": 10.0, "impact": 2.6, "max_strikes": 2}},
}

IMPACT_STEP_BONUS = 0.15  # +15% impact per new tier beyond netherite, flat (not compounding on itself oddly)


def js_string(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def new_item_id(weapon_type, tier):
    # Strip the "vpp_" prefix used for the (Silent Gear-namespaced) material
    # keys - our own "vanillaplusplus:" item namespace already disambiguates,
    # no need for a redundant second prefix on the item path itself.
    clean_tier = tier[len("vpp_"):] if tier.startswith("vpp_") else tier
    return f"vanillaplusplus:{clean_tier}_{weapon_type}"


def scaled_capability(weapon_type, step):
    """step: 1 for the first new tier (allthemodium) through 4 (star_alloy)."""
    base = NETHERITE_CAPS[weapon_type]
    out = {}
    for profile_name, stats in base.items():
        scaled = dict(stats)
        if "impact" in scaled:
            scaled["impact"] = round(scaled["impact"] * (1 + IMPACT_STEP_BONUS * step), 2)
        out[profile_name] = scaled
    return {"attributes": out, "type": f"epicfight:{weapon_type}"}


def gen_items_and_capabilities():
    startup_dir = KUBEJS / "startup_scripts"
    # Epic Fight's ItemCapabilityReloadListener resolves the target item's
    # namespace from the *data folder* a capability file lives under (e.g.
    # `data/epicfight/capabilities/weapons/x.json` -> looks up item
    # `epicfight:x`), not from any namespace written inside the JSON -
    # confirmed by decompiling ItemCapabilityReloadListener.apply(): it does
    # `ResourceLocation.fromNamespaceAndPath(key.getNamespace(), splitPath[1])`
    # where key.getNamespace() is the data-folder namespace. Since our new
    # items are registered as `vanillaplusplus:*`, the capability files must
    # live under `data/vanillaplusplus/capabilities/weapons/`, not
    # `data/epicfight/...` (confirmed live: the latter produced 20 "No item
    # named epicfight:<x>" warnings and silently no-op'd every capability).
    cap_dir = KUBEJS / "data" / "vanillaplusplus" / "capabilities" / "weapons"
    startup_dir.mkdir(parents=True, exist_ok=True)
    cap_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        "// GENERATED by scripts/gen_weapon_tiers.py - do not hand-edit, re-run the script instead.",
        "// New weapon items for the 4 tiers beyond Epic Fight's native netherite ceiling",
        "// (Allthemodium/Vibranium/Unobtainium/Star Alloy) - see DESIGN.md's gear overhaul section.",
        "StartupEvents.registry('item', event => {",
    ]
    for tier in NEW_TIERS:
        for weapon_type in WEAPON_TYPES:
            item_id = new_item_id(weapon_type, tier)
            # event.create() needs the FULL "namespace:path" id - passing a
            # bare path defaults to the "kubejs:" namespace (confirmed via a
            # live boot: items registered as "kubejs:allthemodium_dagger"
            # instead of "vanillaplusplus:allthemodium_dagger" until this was
            # fixed). No creative-tab assignment: .tab()/.group() both don't
            # exist on this KubeJS version's ItemBuilder (confirmed via two
            # separate live-boot errors - "Cannot find function tab", then
            # "Item builder .group() is no longer supported, use
            # StartupEvents.modifyCreativeTab!") - purely cosmetic (which
            # creative-inventory tab the item appears under), not worth
            # chasing a second API for; the items still craft/function fine.
            lines.append(f"    event.create({js_string(item_id)}).maxStackSize(1)")
    lines.append("})")
    (startup_dir / "weapon_items.js").write_text("\n".join(lines) + "\n")
    print(f"wrote startup_scripts/weapon_items.js ({len(NEW_TIERS) * len(WEAPON_TYPES)} items)")

    for step, tier in enumerate(NEW_TIERS, start=1):
        for weapon_type in WEAPON_TYPES:
            item_id = new_item_id(weapon_type, tier)
            path = item_id.split(":")[1]
            cap = scaled_capability(weapon_type, step)
            (cap_dir / f"{path}.json").write_text(json.dumps(cap, indent="\t") + "\n")
    print(f"wrote {len(NEW_TIERS) * len(WEAPON_TYPES)} epicfight capability files")

    tag_values = [new_item_id(weapon_type, tier) for tier in NEW_TIERS for weapon_type in WEAPON_TYPES]
    tag_dir = KUBEJS / "data" / "minecraft" / "tags" / "item"
    tag_dir.mkdir(parents=True, exist_ok=True)
    (tag_dir / "swords.json").write_text(json.dumps({"values": tag_values}, indent=2) + "\n")
    print("wrote data/minecraft/tags/item/swords.json (merges with Epic Fight's own entries)")

    # One custom tag per weapon-class (all 10 tiers each), used by
    # gen_skill_tree.py's kill_entity_source triggers so the 5 Epic-Fight-
    # driven RPG skill categories each key on a single tag instead of
    # enumerating 10 items per category inline.
    vpp_tag_dir = KUBEJS / "data" / "vanillaplusplus" / "tags" / "item"
    vpp_tag_dir.mkdir(parents=True, exist_ok=True)
    for weapon_type in WEAPON_TYPES:
        items = []
        for tier in NATIVE_TIERS:
            items.append(f"epicfight:{tier}_{weapon_type}")
        for tier in NEW_TIERS:
            items.append(new_item_id(weapon_type, tier))
        (vpp_tag_dir / f"{weapon_type}s.json").write_text(json.dumps({"values": items}, indent=2) + "\n")
    print(f"wrote {len(WEAPON_TYPES)} vanillaplusplus:*s item tags for skill-tree triggers")


def gen_weapon_smithing_script():
    lines = [
        "// GENERATED by scripts/gen_weapon_tiers.py - do not hand-edit, re-run the script instead.",
        "// Gear overhaul Part 3: Epic Fight's own tiered weapon recipes (flat crafting-table",
        "// recipes straight from raw ingots/vanilla swords) removed and replaced with a",
        "// Silent-Gear-parts-gated recipe for all 10 tiers x 5 weapon types.",
        "ServerEvents.recipes(event => {",
        "    // Remove Epic Fight's own native recipes for its 6 built-in tiers.",
    ]
    for tier in NATIVE_TIERS:
        for weapon_type in WEAPON_TYPES:
            lines.append(f"    event.remove({{ id: {js_string(f'epicfight:{tier}_{weapon_type}')} }})")

    lines.append("")
    lines.append("    // Add back one consistent smithing-gated recipe per (type x tier): a Silent Gear")
    lines.append("    // sword_blade part (any material - going through Silent Gear's own blueprint +")
    lines.append("    // workbench process is what satisfies 'the same smithing process') + that tier's")
    lines.append("    // own raw material (already tier-locked via ProgressiveStages) + a stick grip.")
    for tier in ALL_TIERS:
        material_item = TIER_MATERIAL_ITEM[tier]
        for weapon_type in WEAPON_TYPES:
            if tier in NEW_TIERS:
                result_id = new_item_id(weapon_type, tier)
            else:
                result_id = f"epicfight:{tier}_{weapon_type}"
            recipe_name = f"vanillaplusplus:{tier}_{weapon_type}_smithing"
            lines.append(
                f"    event.shapeless({js_string(result_id)}, "
                f"[{js_string('silentgear:sword_blade')}, {js_string(material_item)}, 'minecraft:stick'])"
                f".id({js_string(recipe_name)})"
            )
    lines.append("})")
    out_path = KUBEJS / "server_scripts" / "weapon_smithing.js"
    out_path.write_text("\n".join(lines) + "\n")
    print(f"wrote server_scripts/weapon_smithing.js ({len(NATIVE_TIERS) * len(WEAPON_TYPES)} removed, "
          f"{len(ALL_TIERS) * len(WEAPON_TYPES)} added)")


def main():
    gen_items_and_capabilities()
    gen_weapon_smithing_script()


if __name__ == "__main__":
    main()
