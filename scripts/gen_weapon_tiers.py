#!/usr/bin/env python3
"""Gear overhaul Parts 3 + 5: Epic Fight weapon-type integration + boss uniques.

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

Part 5 - boss unique weapons - adds 3 more custom items sharing the exact
same item-namespace/tag/capability machinery above (so they count for
puffish_skills XP and count as `#minecraft:swords` like everything else),
but obtainable ONLY as loot (no smithing recipe), with stats that exceed
what any tier's own smithing route can produce plus a baked-in enchantment
(applied via each loot table's `minecraft:set_enchantments` function, which
writes the enchantments component directly - no enchantability tag needed
on the item itself):
- Duskfang (dagger): Apotheosis boss-dungeon drop (data/apotheosis/
  loot_table/entity/boss_drops.json + rare_boss_drops.json).
- Withering Maul (greatsword): Wither drop. Vanilla's own wither.json loot
  table is empty (confirmed via decompiling the vanilla data jar - the
  Nether Star drop is hardcoded in Wither's Java class, bypassing the loot
  table entirely), so overriding it with our own pool doesn't remove or
  risk the Nether Star.
- Starfall Tachi (tachi): Ender Dragon drop. Same situation - vanilla's
  ender_dragon.json loot table is also empty (dragon egg/XY handled in
  Java), safe to populate.
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

# Part 5 boss-unique weapons: loot-only, no smithing recipe. Stats exceed the
# scaled_capability() curve above (extra flat armor_negation bonus on top of
# the step-scaled impact) so they're a genuine step above anything craftable,
# plus a baked-in enchantment applied via the loot table itself.
BOSS_UNIQUES = {
    "duskfang": {
        "weapon_type": "dagger",
        "step": 2,  # roughly vibranium-tier impact scaling
        "armor_negation_bonus": 5.0,
        "enchantments": {"minecraft:sharpness": 3, "minecraft:looting": 2},
        "source": "apotheosis",
    },
    "withering_maul": {
        "weapon_type": "greatsword",
        "step": 3,  # roughly unobtainium-tier impact scaling
        "armor_negation_bonus": 6.0,
        "enchantments": {"minecraft:sharpness": 4, "minecraft:fire_aspect": 2},
        "source": "wither",
    },
    "starfall_tachi": {
        "weapon_type": "tachi",
        "step": 4.5,  # beyond star_alloy's own step-4 ceiling
        "armor_negation_bonus": 4.0,
        "enchantments": {"minecraft:sharpness": 5, "minecraft:looting": 3},
        "source": "ender_dragon",
    },
}


def boss_unique_id(name):
    return f"vanillaplusplus:{name}"


def scaled_capability_with_bonus(weapon_type, step, armor_negation_bonus):
    base = NETHERITE_CAPS[weapon_type]
    out = {}
    for profile_name, stats in base.items():
        scaled = dict(stats)
        if "impact" in scaled:
            scaled["impact"] = round(scaled["impact"] * (1 + IMPACT_STEP_BONUS * step), 2)
        if "armor_negation" in scaled:
            scaled["armor_negation"] = round(scaled["armor_negation"] + armor_negation_bonus, 2)
        out[profile_name] = scaled
    return {"attributes": out, "type": f"epicfight:{weapon_type}"}


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

    # Part 5: boss-unique items - own startup script (kept separate from the
    # systematic tier ladder above for clarity), same capabilities/ dir.
    boss_lines = [
        "// GENERATED by scripts/gen_weapon_tiers.py - do not hand-edit, re-run the script instead.",
        "// Gear overhaul Part 5: boss-unique weapons. Loot-only, no smithing recipe -",
        "// see data/minecraft/loot_table/entities/{wither,ender_dragon}.json and",
        "// data/apotheosis/loot_table/entity/{boss_drops,rare_boss_drops}.json.",
        "StartupEvents.registry('item', event => {",
    ]
    for name in BOSS_UNIQUES:
        boss_lines.append(f"    event.create({js_string(boss_unique_id(name))}).maxStackSize(1)")
    boss_lines.append("})")
    (startup_dir / "boss_weapons.js").write_text("\n".join(boss_lines) + "\n")
    print(f"wrote startup_scripts/boss_weapons.js ({len(BOSS_UNIQUES)} items)")

    for name, info in BOSS_UNIQUES.items():
        cap = scaled_capability_with_bonus(info["weapon_type"], info["step"], info["armor_negation_bonus"])
        (cap_dir / f"{name}.json").write_text(json.dumps(cap, indent="\t") + "\n")
    print(f"wrote {len(BOSS_UNIQUES)} epicfight capability files for boss uniques")

    tag_values = [new_item_id(weapon_type, tier) for tier in NEW_TIERS for weapon_type in WEAPON_TYPES]
    tag_values += [boss_unique_id(name) for name in BOSS_UNIQUES]
    tag_dir = KUBEJS / "data" / "minecraft" / "tags" / "item"
    tag_dir.mkdir(parents=True, exist_ok=True)
    (tag_dir / "swords.json").write_text(json.dumps({"values": tag_values}, indent=2) + "\n")
    print("wrote data/minecraft/tags/item/swords.json (merges with Epic Fight's own entries)")

    # One custom tag per weapon-class (all 10 tiers each, plus any boss
    # uniques of that type), used by gen_skill_tree.py's kill_entity_source
    # triggers so the 5 Epic-Fight-driven RPG skill categories each key on a
    # single tag instead of enumerating items per category inline.
    vpp_tag_dir = KUBEJS / "data" / "vanillaplusplus" / "tags" / "item"
    vpp_tag_dir.mkdir(parents=True, exist_ok=True)
    for weapon_type in WEAPON_TYPES:
        items = []
        for tier in NATIVE_TIERS:
            items.append(f"epicfight:{tier}_{weapon_type}")
        for tier in NEW_TIERS:
            items.append(new_item_id(weapon_type, tier))
        for name, info in BOSS_UNIQUES.items():
            if info["weapon_type"] == weapon_type:
                items.append(boss_unique_id(name))
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


def loot_item_entry(name, weight):
    info = BOSS_UNIQUES[name]
    entry = {
        "type": "minecraft:item",
        "name": boss_unique_id(name),
        "weight": weight,
        "functions": [
            {
                "function": "minecraft:set_enchantments",
                "enchantments": info["enchantments"],
                "add": False,
            }
        ],
    }
    return entry


def gen_boss_loot():
    data_dir = KUBEJS / "data"

    # Wither: vanilla's own loot table is empty (Nether Star drop is
    # hardcoded in the Wither's Java class, not the loot table) - confirmed
    # via decompiling the vanilla data jar, so overriding it is additive
    # and safe. 1-in-4 chance.
    wither_table = {
        "type": "minecraft:entity",
        "pools": [
            {
                "rolls": 1.0,
                "bonus_rolls": 0.0,
                "entries": [
                    loot_item_entry("withering_maul", 1),
                    {"type": "minecraft:empty", "weight": 3},
                ],
            }
        ],
    }
    wither_path = data_dir / "minecraft" / "loot_table" / "entities" / "wither.json"
    wither_path.parent.mkdir(parents=True, exist_ok=True)
    wither_path.write_text(json.dumps(wither_table, indent=2) + "\n")

    # Ender Dragon: same situation, vanilla table is empty (egg/XP handled in
    # Java). 1-in-2 chance, repeatable via respawned dragons.
    dragon_table = {
        "type": "minecraft:entity",
        "pools": [
            {
                "rolls": 1.0,
                "bonus_rolls": 0.0,
                "entries": [
                    loot_item_entry("starfall_tachi", 1),
                    {"type": "minecraft:empty", "weight": 1},
                ],
            }
        ],
    }
    dragon_path = data_dir / "minecraft" / "loot_table" / "entities" / "ender_dragon.json"
    dragon_path.parent.mkdir(parents=True, exist_ok=True)
    dragon_path.write_text(json.dumps(dragon_table, indent=2) + "\n")

    # Apotheosis boss-dungeon tables: these DO have real content already (its
    # own gem/sigil drops), so we preserve every existing entry exactly and
    # append Duskfang as one more weighted option in each pool - confirmed
    # exact original content by decompiling the Apotheosis jar.
    boss_drops = {
        "type": "minecraft:entity",
        "pools": [
            {
                "bonus_rolls": 0.0,
                "entries": [
                    {"type": "apotheosis:random_gem", "quality": 1, "weight": 30},
                    {
                        "type": "placebo:stack_entry",
                        "min": 1,
                        "max": 1,
                        "quality": 1,
                        "stack": {"count": 1, "id": "apotheosis:sigil_of_malice"},
                        "weight": 25,
                    },
                    loot_item_entry("duskfang", 15),
                    {"type": "minecraft:empty", "weight": 45},
                ],
                "rolls": 1.0,
            }
        ],
        "random_sequence": "apotheosis:entity/boss_drops",
    }
    boss_drops_path = data_dir / "apotheosis" / "loot_table" / "entity" / "boss_drops.json"
    boss_drops_path.parent.mkdir(parents=True, exist_ok=True)
    boss_drops_path.write_text(json.dumps(boss_drops, indent=2) + "\n")

    rare_boss_drops = {
        "type": "minecraft:entity",
        "pools": [
            {
                "bonus_rolls": 0.0,
                "entries": [
                    {"type": "apotheosis:random_gem", "quality": 1, "weight": 45},
                    {
                        "type": "placebo:stack_entry",
                        "min": 1,
                        "max": 1,
                        "quality": 1,
                        "stack": {"count": 1, "id": "apotheosis:sigil_of_malice"},
                        "weight": 30,
                    },
                    {
                        "type": "minecraft:tag",
                        "expand": True,
                        "name": "apotheosis:boss_music_discs",
                        "weight": 5,
                    },
                    loot_item_entry("duskfang", 15),
                    {"type": "minecraft:empty", "weight": 20},
                ],
                "rolls": 1.0,
            }
        ],
        "random_sequence": "apotheosis:entity/rare_boss_drops",
    }
    rare_boss_drops_path = data_dir / "apotheosis" / "loot_table" / "entity" / "rare_boss_drops.json"
    rare_boss_drops_path.parent.mkdir(parents=True, exist_ok=True)
    rare_boss_drops_path.write_text(json.dumps(rare_boss_drops, indent=2) + "\n")

    print("wrote 4 boss loot tables (wither, ender_dragon, apotheosis boss_drops + rare_boss_drops)")


def main():
    gen_items_and_capabilities()
    gen_weapon_smithing_script()
    gen_boss_loot()


if __name__ == "__main__":
    main()
