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


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    keep = set()
    for key, ingredient, display_name, harvest_name, tier_index in MATERIALS:
        data = material_json(key, ingredient, display_name, harvest_name, tier_index)
        (OUT / f"{key}.json").write_text(json.dumps(data, indent=2) + "\n")
        keep.add(f"{key}.json")
        print(f"wrote {key}.json (tier {tier_index})")

    # Remove stale files from renamed/removed materials (same "keep set"
    # cleanup pattern as build_server.py) - a prior version of this script
    # left old-named files behind after a rename, which is harmless on its
    # own but confusing clutter.
    for existing in OUT.glob("*.json"):
        if existing.name not in keep:
            existing.unlink()
            print(f"removed stale {existing.name}")


if __name__ == "__main__":
    main()
