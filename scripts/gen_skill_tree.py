#!/usr/bin/env python3
"""Generate Pufferfish's Skills datapack content (category/experience/definitions/
skills/connections JSON) from a compact Python spec, writing into
pack/kubejs/data/puffish_skills/puffish_skills/ (KubeJS's raw-datapack folder).

Hand-typing hundreds of node x/y coordinates is how the upstream "Default Skill
Trees" pack looks (a sprawling hex snowflake) - not practical to author by hand
for six categories, so this generates a simple, reliable linear chain per
category instead. Tree shape can be revisited later; the JSON schema mirrors
what's in the real default-skill-trees mod jar (verified by extracting it).
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "pack" / "kubejs" / "data" / "puffish_skills" / "puffish_skills"


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent="\t") + "\n")


def gen_category(cat_id, title, icon_item, background, experience_expr, sources, definitions, chain):
    """chain: list of definition ids, one per node, in unlock order (linear)."""
    cat_dir = OUT / "categories" / cat_id

    write_json(cat_dir / "category.json", {
        "unlocked_by_default": True,
        "title": title,
        "icon": {"type": "item", "data": {"item": icon_item}},
        "background": f"textures/gui/advancements/backgrounds/{background}.png",
    })

    write_json(cat_dir / "experience.json", {
        "experience_per_level": {"type": "expression", "data": {"expression": experience_expr}},
        "sources": sources,
    })

    write_json(cat_dir / "definitions.json", definitions)

    skills = {}
    node_ids = []
    for i, definition in enumerate(chain):
        node_id = f"n{i}"
        node_ids.append(node_id)
        skills[node_id] = {"x": i * 32, "y": 0, "definition": definition}
    write_json(cat_dir / "skills.json", skills)

    connections = {"normal": {"bidirectional": [[node_ids[i], node_ids[i + 1]] for i in range(len(node_ids) - 1)]}}
    write_json(cat_dir / "connections.json", connections)

    return cat_id


def attr_reward(title, icon_effect_or_item, attribute, value, operation, icon_type="effect"):
    icon = {"type": icon_type, "data": ({"effect": icon_effect_or_item} if icon_type == "effect" else {"item": icon_effect_or_item})}
    return {
        "title": title,
        "icon": icon,
        "rewards": [{"type": "puffish_skills:attribute", "data": {"attribute": attribute, "value": value, "operation": operation}}],
    }


def mine_block_source(ore_tiers):
    """ore_tiers: list of (test_key, block_or_tag, xp) - mirrors the verified
    default-skill-trees mine_block source shape (silk_touch-aware)."""
    variables = {
        "silk_touch": {
            "operations": [
                {"type": "get_tool_item_stack"},
                {"type": "puffish_skills:test", "data": {"nbt": '{Enchantments:[{id:"minecraft:silk_touch"}]}'}},
            ]
        }
    }
    conditions = []
    for key, block, xp in ore_tiers:
        variables[key] = {
            "operations": [
                {"type": "get_mined_block_state"},
                {"type": "puffish_skills:test", "data": {"block": block}},
            ]
        }
        conditions.append({"condition": f"!silk_touch & {key}", "expression": str(xp)})
    return {"type": "puffish_skills:mine_block", "data": {"variables": variables, "experience": conditions}}


def kill_entity_source(weapon_test_block, weapon_items_or_tag, base_xp):
    return {
        "type": "puffish_skills:kill_entity",
        "data": {
            "variables": {
                "used_right_weapon": {
                    "operations": [
                        {"type": "get_weapon_item_stack"},
                        {"type": "puffish_skills:test", "data": {"item": weapon_items_or_tag}},
                    ]
                },
                "dropped_xp": {"operations": [{"type": "get_dropped_experience"}]},
            },
            "experience": [{"condition": "used_right_weapon", "expression": f"{base_xp} + dropped_xp"}],
        },
    }


def stat_source(stat_id, xp_per_unit):
    """stat_id: e.g. "minecraft.custom:minecraft.sprint_one_cm" - the mod's
    BuiltinJson#parseStat packs StatType(namespace.path) : Stat(namespace.path)
    into a single string with '.' splitting each half's namespace/path and
    ':' separating the two halves (confirmed by reading the real source,
    github.com/pufmat/skillsmod, not just decompiled bytecode - two prior
    guesses from bytecode alone were wrong).

    IncreaseStatExperienceSource follows the exact same
    variables+test-operation pattern as mine_block/kill_entity (all three
    go through LegacyCalculation.parse): "amount" is NOT implicitly bound -
    it must be declared via the get_increase_amount operation, and matching
    the specific stat requires chaining get_stat -> puffish_skills:test
    (registered on the STAT prototype by StatCondition, taking a "stat"
    field) since awardStat's mixin hook fires for every stat increase, not
    just the one we care about."""
    return {
        "type": "puffish_skills:increase_stat",
        "data": {
            "variables": {
                "is_target_stat": {
                    "operations": [
                        {"type": "get_stat"},
                        {"type": "puffish_skills:test", "data": {"stat": stat_id}},
                    ]
                },
                "amount": {"operations": [{"type": "get_increase_amount"}]},
            },
            "experience": [{"condition": "is_target_stat", "expression": f"amount * {xp_per_unit}"}],
        },
    }


CATEGORIES = []

# ---------------------------------------------------------------------------
# Mining
# ---------------------------------------------------------------------------
CATEGORIES.append(gen_category(
    "mining", "Mining", "diamond_pickaxe", "stone",
    "100 + level * 40",
    [mine_block_source([
        ("stone_like", "#base_stone_overworld", 1),
        ("coal_ore", "#c:ores/coal", 6),
        ("copper_ore", "#c:ores/copper", 6),
        ("iron_ore", "#c:ores/iron", 10),
        ("gold_ore", "#c:ores/gold", 10),
        ("redstone_ore", "#c:ores/redstone", 8),
        ("lapis_ore", "#c:ores/lapis", 8),
        ("diamond_ore", "#c:ores/diamond", 14),
        ("emerald_ore", "#c:ores/emerald", 14),
        ("zinc_ore", "create:zinc_ore", 10),
        ("deepslate_zinc_ore", "create:deepslate_zinc_ore", 12),
    ])],
    {
        "mining_speed+3%": attr_reward("+3% Mining Speed", "haste", "puffish_attributes:mining_speed", 0.03, "multiply_base"),
        "pickaxe_speed+3%": attr_reward("+3% Pickaxe Speed", "diamond_pickaxe", "puffish_attributes:pickaxe_speed", 0.03, "multiply_base", "item"),
        "fortune+0.1": attr_reward("+0.1 Fortune", "diamond", "puffish_skills:player.fortune", 0.1, "addition", "item"),
        "submerged_mining_speed+5%": attr_reward("+5% Underwater Mining Speed", "diamond_pickaxe", "minecraft:player.submerged_mining_speed", 0.05, "multiply_base", "item"),
    },
    ["mining_speed+3%", "fortune+0.1", "mining_speed+3%", "pickaxe_speed+3%", "fortune+0.1",
     "mining_speed+3%", "submerged_mining_speed+5%", "fortune+0.1", "pickaxe_speed+3%", "mining_speed+3%"],
))

# ---------------------------------------------------------------------------
# Swords
# ---------------------------------------------------------------------------
CATEGORIES.append(gen_category(
    "swords", "Swords", "diamond_sword", "nether",
    "100 + level * 40",
    [kill_entity_source("weapon_check", "#minecraft:swords", 2)],
    {
        "sword_damage+3%": attr_reward("+3% Sword Damage", "diamond_sword", "puffish_attributes:sword_damage", 0.03, "multiply_base", "item"),
        "attack_speed+3%": attr_reward("+3% Attack Speed", "sugar", "generic.attack_speed", 0.03, "multiply_base", "item"),
        "melee_damage+2%": attr_reward("+2% Melee Damage", "strength", "puffish_skills:player.melee_damage", 0.02, "multiply_total"),
        "knockback+5%": attr_reward("+5% Knockback", "feather", "puffish_attributes:knockback", 0.05, "multiply_base", "item"),
    },
    ["sword_damage+3%", "attack_speed+3%", "sword_damage+3%", "melee_damage+2%", "attack_speed+3%",
     "sword_damage+3%", "knockback+5%", "melee_damage+2%", "sword_damage+3%", "attack_speed+3%"],
))

# ---------------------------------------------------------------------------
# Bows
# ---------------------------------------------------------------------------
CATEGORIES.append(gen_category(
    "bows", "Bows", "bow", "adventure",
    "100 + level * 40",
    [kill_entity_source("weapon_check", "bow", 2),
     kill_entity_source("weapon_check2", "crossbow", 2)],
    {
        "ranged_damage+3%": attr_reward("+3% Ranged Damage", "bow", "puffish_skills:player.ranged_damage", 0.03, "multiply_total", "item"),
        "bow_speed+3%": attr_reward("+3% Bow Projectile Speed", "arrow", "puffish_attributes:bow_projectile_speed", 0.03, "multiply_base", "item"),
        "crossbow_speed+3%": attr_reward("+3% Crossbow Projectile Speed", "crossbow", "puffish_attributes:crossbow_projectile_speed", 0.03, "multiply_base", "item"),
    },
    ["ranged_damage+3%", "bow_speed+3%", "ranged_damage+3%", "crossbow_speed+3%", "ranged_damage+3%",
     "bow_speed+3%", "ranged_damage+3%", "crossbow_speed+3%", "ranged_damage+3%", "bow_speed+3%"],
))

# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------
CATEGORIES.append(gen_category(
    "running", "Running", "leather_boots", "husbandry",
    "100 + level * 30",
    [stat_source("minecraft.custom:minecraft.sprint_one_cm", "0.02")],
    {
        "sprint_speed+3%": attr_reward("+3% Sprinting Speed", "speed", "puffish_attributes:sprinting_speed", 0.03, "multiply_base"),
        "stamina+5%": attr_reward("+5% Stamina", "saturation", "puffish_skills:player.stamina", 0.05, "multiply_total"),
        "jump+3%": attr_reward("+3% Jump", "jump_boost", "puffish_skills:player.jump", 0.03, "multiply_total"),
    },
    ["sprint_speed+3%", "stamina+5%", "sprint_speed+3%", "jump+3%", "stamina+5%",
     "sprint_speed+3%", "jump+3%", "stamina+5%", "sprint_speed+3%", "jump+3%"],
))

# ---------------------------------------------------------------------------
# Swimming
# ---------------------------------------------------------------------------
CATEGORIES.append(gen_category(
    "swimming", "Swimming", "turtle_helmet", "end",
    "100 + level * 30",
    [stat_source("minecraft.custom:minecraft.swim_one_cm", "0.03")],
    {
        "water_efficiency+8%": attr_reward("+8% Water Movement", "dolphins_grace", "generic.water_movement_efficiency", 0.08, "multiply_total"),
        "oxygen+10%": attr_reward("+10% Oxygen", "conduit_power", "generic.oxygen_bonus", 0.1, "multiply_total"),
        "submerged_mining_speed+5%": attr_reward("+5% Underwater Mining Speed", "turtle_helmet", "minecraft:player.submerged_mining_speed", 0.05, "multiply_base", "item"),
    },
    ["water_efficiency+8%", "oxygen+10%", "water_efficiency+8%", "submerged_mining_speed+5%", "oxygen+10%",
     "water_efficiency+8%", "oxygen+10%", "submerged_mining_speed+5%", "water_efficiency+8%", "oxygen+10%"],
))

# ---------------------------------------------------------------------------
# Building (no native trigger - granted via KubeJS BlockEvents.placed, see
# pack/kubejs/server_scripts/skills.js)
# ---------------------------------------------------------------------------
CATEGORIES.append(gen_category(
    "building", "Building", "bricks", "husbandry",
    "100 + level * 30",
    [],
    {
        "reach+0.5": attr_reward("+0.5 Block Reach", "bricks", "minecraft:player.block_interaction_range", 0.5, "addition", "item"),
        "break_speed+3%": attr_reward("+3% Block Break Speed", "iron_pickaxe", "minecraft:player.block_break_speed", 0.03, "multiply_base", "item"),
        "step_height+0.25": attr_reward("+0.25 Step Height", "scaffolding", "generic.step_height", 0.25, "addition", "item"),
    },
    ["reach+0.5", "break_speed+3%", "reach+0.5", "step_height+0.25", "break_speed+3%",
     "reach+0.5", "step_height+0.25", "break_speed+3%", "reach+0.5", "step_height+0.25"],
))

write_json(OUT / "config.json", {"version": 3, "categories": CATEGORIES})
print(f"generated {len(CATEGORIES)} categories under {OUT}")
