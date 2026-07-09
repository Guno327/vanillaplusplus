#!/usr/bin/env python3
"""Generate Silent Gear material datapack JSON for Vanilla++'s own tier
ladder, writing into pack/kubejs/data/silentgear/silentgear_materials/
(KubeJS's raw-datapack injection folder, same technique as Phase 3's
puffish_skills categories).

Gear overhaul (post-Phase-9): the user wants every weapon/tool/armor piece
to come from either a boss drop or Silent Gear's own smithing process -
which means Silent Gear needs a material for every one of our own tiers
(Tiers 0-9), not just vanilla's wood/stone/iron/diamond/netherite. Schema
confirmed by reading the installed jar's own materials directly
(data/silentgear/silentgear_materials/iron.json, diamond.json) - a
"silentgear:simple" material has a crafting.ingredient (item or tag), and
per-part ("main" for tools, "armor_main"/"plates" would be armor's
equivalent, but this mod uses "main" uniformly with armor/<piece> sub-keys)
stat blocks. Netherite is NOT a normal material in this scheme - it's a
"silentgear:coating" (a smithing-table upgrade layer multiplying whatever
base material was used, mirroring vanilla's own netherite upgrade
mechanic), which we deliberately don't replicate: all 7 new materials here
are plain "main" materials like iron/diamond, for a simpler, more
predictable one-material-per-tier mental model matching tiers 0 (wood/
stone, Silent Gear's own built-ins) through 3 (already vanilla-ore-based).

Stat curve: interpolated/extrapolated from Silent Gear's own iron (Tier
"1"-equivalent) and diamond (Tier "2"-equivalent) reference materials,
continuing their growth rate outward for the 4 new tiers beyond precision_age
(Allthemodium/Vibranium/Unobtainium/Alloy - the late-game "meta material"
mod the user asked to lean on for the top of the ladder, since Stellaris
itself adds no ores). This is a deliberately simple, consistent formula
(not hand-tuned per material) - there's no way to playtest actual combat
balance in this sandbox (no live client), so a clean, disclosed formula is
more defensible than ad-hoc numbers that look plausible but aren't verified
either way.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "pack" / "kubejs" / "data" / "silentgear" / "silentgear_materials"
TAG_OUT = ROOT / "pack" / "kubejs" / "data" / "vanillaplusplus" / "tags" / "block"

# Utility overhaul Part 1: harvest_tier.incorrect_blocks_for_tool was always
# pointing at these tag ids, but the tags themselves were never created -
# they resolved to empty, meaning every one of our materials' tools could
# mine every block in the game regardless of tier (a real bug, found by
# decompiling Silent Gear's own iron/diamond materials and noticing they
# point to SILENT GEAR'S OWN tags, which just reference vanilla's real
# hierarchy - e.g. `silentgear:incorrect_for_iron_tools` is literally
# `["#minecraft:incorrect_for_iron_tool"]`, not a Silent-Gear-invented block
# list). NeoForge itself patches `minecraft:incorrect_for_diamond_tool` to
# include `#neoforge:needs_netherite_tool`, and Allthemodium patches
# `minecraft:incorrect_for_netherite_tool` with `#c:needs_allthemodium_tool`
# (etc.) while also shipping ready-made `c:incorrect_for_allthemodium_tool`/
# `..._vibranium_tool`/`..._unobtainium_tool` tags that are each exactly
# "everything from the next tier up" - so our own tags just need to plug
# into this existing chain, not enumerate any blocks ourselves.
TIER_INCORRECT_TAGS = {
    1: ["minecraft:incorrect_for_iron_tool", "minecraft:incorrect_for_diamond_tool",
        "minecraft:incorrect_for_netherite_tool"],
    2: ["minecraft:incorrect_for_diamond_tool", "minecraft:incorrect_for_netherite_tool"],
    # Nothing in vanilla distinguishes diamond-tier from netherite-tier block
    # hardness (both have an empty native "incorrect" list), so tier 3
    # (refined_radiance, our "netherite-equivalent") needs the exact same
    # exclusion set as tier 2 to still keep Allthemodium's ores out of reach.
    3: ["minecraft:incorrect_for_diamond_tool", "minecraft:incorrect_for_netherite_tool"],
    4: ["c:incorrect_for_allthemodium_tool"],
    5: ["c:incorrect_for_vibranium_tool"],
    6: ["c:incorrect_for_unobtainium_tool"],
    7: [],  # top tier, nothing above it to exclude
}

# (key, ingredient tag-or-item, display name, harvest_tier name, tier_index)
# tier_index 1 = andesite_age (~iron), 2 = brass_age (~diamond), continuing
# the same growth rate for 3-9.
# Every key is prefixed "vpp_" - Silent Gear ships 132 materials of its own
# and one of our first-draft keys ("brass") silently collided with an
# existing one (a real, weaker-than-iron generic brass material already
# matching Create's brass ingot via the "c:ingots/brass" common tag) since
# KubeJS's datapack injection just overwrites same-id files. Found via a
# live boot - the material COUNT was 138 instead of the expected 139 (132 +
# 7 new), one short because "silentgear:brass" got replaced instead of
# added. Namespacing every key rules this out regardless of what any
# current or future Silent Gear material happens to be named.
MATERIALS = [
    ("vpp_andesite_alloy", {"item": "create:andesite_alloy"}, "Andesite Alloy", "andesite_alloy", 1),
    ("vpp_brass", {"item": "create:brass_ingot"}, "Brass", "brass", 2),
    # Create's own precision_age materials are two mutually-exclusive,
    # per-world-seed random items (a player gets refined_radiance OR
    # shadow_steel, never both) with no combined tag to match either -
    # confirmed no such tag exists in the installed Create jar. Simplifying
    # to refined_radiance alone as the Silent Gear ingredient rather than
    # inventing a compound-ingredient structure Silent Gear's own material
    # parser may not support; ProgressiveStages' existing tier-unlock
    # trigger still accepts either item, this only affects what you smith
    # tools/weapons out of.
    ("vpp_refined_radiance", {"item": "create:refined_radiance"}, "Refined Radiance", "refined_radiance", 3),
    ("vpp_allthemodium", {"item": "allthemodium:allthemodium_ingot"}, "Allthemodium", "allthemodium", 4),
    ("vpp_vibranium", {"item": "allthemodium:vibranium_ingot"}, "Vibranium", "vibranium", 5),
    ("vpp_unobtainium", {"item": "allthemodium:unobtainium_ingot"}, "Unobtainium", "unobtainium", 6),
    ("vpp_star_alloy", {"item": "allthemodium:unobtainium_vibranium_alloy_ingot"}, "Star Alloy", "star_alloy", 7),
]

# Reference points from Silent Gear's own iron.json (tier_index=1 baseline)
# and diamond.json (tier_index=2 baseline) - see module docstring.
IRON_MAIN = {
    "attack_damage": 2.0, "attack_speed": 0.0, "durability": 250.0,
    "harvest_speed": 6.0, "enchantment_value": 14.0, "rarity": 20.0,
    "armor": 15.0, "armor/helmet": 2.0, "armor/chestplate": 6.0,
    "armor/leggings": 5.0, "armor/boots": 2.0, "armor_durability": 15.0,
    "magic_armor": 6.0, "magic_damage": 1.0, "ranged_damage": 1.0,
    "projectile_accuracy": 1.1, "projectile_speed": 1.0, "charging_value": 0.7,
    "draw_speed": 0.1,
}
DIAMOND_MAIN = {
    "attack_damage": 3.0, "attack_speed": 0.0, "durability": 1561.0,
    "harvest_speed": 8.0, "enchantment_value": 10.0, "rarity": 70.0,
    "armor": 20.0, "armor/helmet": 3.0, "armor/chestplate": 8.0,
    "armor/leggings": 6.0, "armor/boots": 3.0, "armor_durability": 33.0,
    "magic_armor": 4.0, "magic_damage": 1.0, "ranged_damage": 2.0,
    "projectile_accuracy": 1.1, "projectile_speed": 0.9, "charging_value": 0.8,
    "draw_speed": -0.2, "armor_toughness": 8.0,
}
# Per-tier-step growth ratio, derived from the iron->diamond jump (tier 1->2)
# but damped for stats where a straight ratio would be wildly unstable
# (durability jumps ~6.24x from iron->diamond in Silent Gear's own numbers -
# continuing THAT literally would make Tier 9 durability meaningless, so
# durability instead grows at a flatter, still-substantial 1.8x/tier).
GROWTH = {
    "attack_damage": 1.20, "durability": 1.8, "harvest_speed": 1.15,
    "enchantment_value": 1.10, "rarity": 1.35, "armor": 1.12,
    "armor/helmet": 1.12, "armor/chestplate": 1.12, "armor/leggings": 1.12,
    "armor/boots": 1.12, "armor_durability": 1.8, "magic_armor": 1.15,
    "magic_damage": 1.15, "ranged_damage": 1.15, "armor_toughness": 1.20,
}

# Utility overhaul Part 3: "additional utility... auto-smelting, increased
# AoE" is satisfied entirely by Silent Gear's own data-driven trait system,
# already used for material flavor elsewhere (see iron.json's "malleable"
# trait) - no new mod or item needed, just a "traits" list on our own
# materials' main properties, applying automatically to every tool/weapon/
# armor piece made from that material. Confirmed by reading each trait's
# JSON + doc comments in the installed jar: `widen` (mining AoE - "level N
# = radius (2N+3)x(2N+3)", max level 3), `magnetic` (auto-pickup nearby
# items, max level 5), `magmatic` (auto-smelts mined ore, max level 1 -
# only meaningful on harvest tools), `fortunate` (built-in Fortune I-III,
# max level 3), `reach` (+block/entity interaction range, max level 5).
# `multi_break` (vein-miner-style) is a documented no-op stub in the jar
# itself ("This trait has never been coded") and is deliberately not used.
# Monotonically increasing by tier, same disclosed-simple-formula category
# as the stat curves above (no live client to playtest actual feel either
# way).
TRAITS_BY_TIER = {
    1: [("reach", 1)],
    2: [("reach", 2), ("magnetic", 1)],
    3: [("widen", 1), ("magnetic", 2)],
    4: [("widen", 2), ("magnetic", 3), ("fortunate", 1)],
    5: [("widen", 2), ("magmatic", 1), ("magnetic", 3), ("fortunate", 2)],
    6: [("widen", 3), ("magmatic", 1), ("magnetic", 4), ("fortunate", 2)],
    7: [("widen", 3), ("magmatic", 1), ("magnetic", 5), ("fortunate", 3), ("reach", 5)],
}


def traits_for(tier_index):
    return [
        {"conditions": [], "level": level, "trait": f"silentgear:{name}"}
        for name, level in TRAITS_BY_TIER[tier_index]
    ]


def scaled_main(tier_index):
    # Start from diamond (tier 2) and grow outward for tier_index > 2;
    # tier 1 (andesite_alloy) just uses iron's numbers directly.
    if tier_index <= 1:
        return dict(IRON_MAIN)
    result = dict(DIAMOND_MAIN)
    steps = tier_index - 2
    for key, ratio in GROWTH.items():
        if key in result:
            result[key] = round(result[key] * (ratio ** steps), 2)
    return result


def material_json(key, ingredient, display_name, harvest_name, tier_index):
    main = scaled_main(tier_index)
    tip_bonus_scale = 1.0 + 0.15 * max(tier_index - 1, 0)
    return {
        "type": "silentgear:simple",
        "parent": "silentgear:empty",
        "crafting": {
            "can_salvage": True,
            "categories": ["metal", "vanillaplusplus_tier"],
            "gear_type_blacklist": [],
            "ingredient": ingredient,
            "part_substitutes": {},
        },
        "display": {
            "color": "#FFFFFFFF",
            "main_texture_type": "HIGH_CONTRAST",
            "name": {"translate": f"material.vanillaplusplus.{key}", "fallback": display_name},
            "name_prefix": "",
        },
        "properties": {
            "silentgear:main": {
                **main,
                "harvest_tier": {
                    "incorrect_blocks_for_tool": f"vanillaplusplus:incorrect_for_{harvest_name}_tools",
                    "level_hint": str(tier_index + 1),
                    "name": harvest_name,
                },
                "traits": traits_for(tier_index),
            },
            "silentgear:rod": {
                "harvest_speed": {"operation": "MULTIPLY_TOTAL", "value": 0.1},
            },
            "silentgear:tip": {
                "attack_damage": {"operation": "ADD", "value": round(1.0 * tip_bonus_scale, 2)},
                "durability": {"operation": "ADD", "value": round(128.0 * tip_bonus_scale, 2)},
                "harvest_speed": {"operation": "ADD", "value": round(1.0 * tip_bonus_scale, 2)},
                "harvest_tier": {
                    "incorrect_blocks_for_tool": f"vanillaplusplus:incorrect_for_{harvest_name}_tools",
                    "level_hint": str(tier_index + 1),
                    "name": harvest_name,
                },
            },
        },
    }


def incorrect_blocks_tag_json(tier_index):
    values = [f"#{v}" for v in TIER_INCORRECT_TAGS[tier_index]]
    return {"values": values}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    TAG_OUT.mkdir(parents=True, exist_ok=True)
    keep = set()
    tag_keep = set()
    for key, ingredient, display_name, harvest_name, tier_index in MATERIALS:
        data = material_json(key, ingredient, display_name, harvest_name, tier_index)
        (OUT / f"{key}.json").write_text(json.dumps(data, indent=2) + "\n")
        keep.add(f"{key}.json")
        print(f"wrote {key}.json (tier {tier_index})")

        tag_name = f"incorrect_for_{harvest_name}_tools.json"
        tag_data = incorrect_blocks_tag_json(tier_index)
        (TAG_OUT / tag_name).write_text(json.dumps(tag_data, indent=2) + "\n")
        tag_keep.add(tag_name)
        print(f"wrote tags/block/{tag_name} ({len(tag_data['values'])} entries)")

    # Remove stale files from renamed/removed materials (same "keep set"
    # cleanup pattern as build_server.py) - a prior version of this script
    # left old-named files behind after a rename, which is harmless on its
    # own but confusing clutter.
    for existing in OUT.glob("*.json"):
        if existing.name not in keep:
            existing.unlink()
            print(f"removed stale {existing.name}")
    for existing in TAG_OUT.glob("incorrect_for_*_tools.json"):
        if existing.name not in tag_keep:
            existing.unlink()
            print(f"removed stale tags/block/{existing.name}")


if __name__ == "__main__":
    main()
