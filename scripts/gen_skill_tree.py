#!/usr/bin/env python3
"""Generate Pufferfish's Skills datapack content (category/experience/definitions/
skills/connections JSON) from a compact Python spec, writing into
pack/kubejs/data/puffish_skills/puffish_skills/ (KubeJS's raw-datapack folder).

Hand-typing hundreds of node x/y coordinates is how the upstream "Default Skill
Trees" pack looks (a sprawling hex snowflake) - not practical to author by hand
for twelve categories, so this generates a simple, reliable branching layout
per category instead: a 5-node shared trunk (general passives) forking at its
last node into two parallel 5-node spec paths (15 nodes/category total). Tree
shape can be revisited later; the JSON schema mirrors what's in the real
default-skill-trees mod jar (verified by extracting it) plus the `exclusive`
connections group (verified against the actual puffish_skills-0.18.0 source via
javap - see the gen_category docstring below).

Item 11 overhaul (DECISIONS.md "Item 11 (skill trees) - research verdicts"):
every category gets a hard-but-respeccable fork instead of one long linear
chain. Path themes stack DIFFERENT FAMILIES OF UPSIDES (no node anywhere
carries a downside) - e.g. swords forks into cadence (attack_speed-heavy) vs
power (attack_damage+knockback). Respec is handled entirely out-of-band by
pack/kubejs/server_scripts/skill_respec.js via net.puffish.skillsmod.api.
SkillsAPI; nothing in this generator enforces exclusivity beyond the one
`exclusive` connection - the mod does the rest natively.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "pack" / "kubejs" / "data" / "puffish_skills" / "puffish_skills"


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent="\t") + "\n")


def gen_category(cat_id, title, icon_item, background, experience_expr, sources, definitions, trunk, path_a, path_b):
    """trunk/path_a/path_b: each a list of exactly 5 definition ids, in unlock
    order.

    Layout: trunk nodes n0-n4 form a shared straight line (y=0). At n4 the
    tree forks into two parallel 5-node columns - path_a continuing upward
    (a0-a4, y=-40) and path_b continuing downward (b0-b4, y=40), each linked
    to n4 by a normal edge from its first node (a0/b0) and internally chained
    normal a0-a1-a2-a3-a4 / b0-b1-b2-b3-b4.

    Exclusivity: exactly ONE `exclusive.bidirectional` edge, [a0, b0] - the
    two fork-entry nodes. This is deliberately minimal, not one edge per
    node pair: verified by reading net.puffish.skillsmod.server.data.
    CategoryData.getSkillState (javap against the real puffish_skills-0.18.0
    jar) that exclusion is evaluated per-skill from its own
    `required_exclusions` (definitions.json field, defaults to 1 when
    omitted - confirmed via the class's Optional<Integer>.orElse(1) parse)
    against how many of ITS OWN exclusive-neighbors are currently unlocked.
    Since a1-a4/b1-b4 are still gated behind a0/b0 via ordinary `normal`
    prerequisites (requiredSkills), excluding just the entry node blocks the
    whole rival path with no extra connections needed. Exclusion state is
    re-evaluated live off the unlocked-skill set (not cached), which is what
    lets a respec "just work" once the abandoned path's nodes are unlocked
    -> false again.

    Correctness gotcha (also from getSkillState): a skill already in the
    unlocked set returns UNLOCKED unconditionally, checked BEFORE the
    exclusion test - so becoming excluded never auto-locks or un-rewards an
    already-unlocked node. A respec routine MUST explicitly .lock() every
    node of the abandoned path, not just rely on exclusion kicking in (see
    skill_respec.js).
    """
    assert len(trunk) == 5, f"{cat_id}: trunk must have exactly 5 nodes, got {len(trunk)}"
    assert len(path_a) == 5, f"{cat_id}: path_a must have exactly 5 nodes, got {len(path_a)}"
    assert len(path_b) == 5, f"{cat_id}: path_b must have exactly 5 nodes, got {len(path_b)}"

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

    trunk_ids = [f"n{i}" for i in range(5)]
    a_ids = [f"a{i}" for i in range(5)]
    b_ids = [f"b{i}" for i in range(5)]

    skills = {}
    for i, node_id in enumerate(trunk_ids):
        skills[node_id] = {"x": i * 32, "y": 0, "definition": trunk[i]}
        # n0 (the trunk's first node) MUST carry "root": true - verified via
        # javap against net.puffish.skillsmod.config.skill.SkillConfig.parse
        # (installed puffish_skills-0.18.1-1.21-neoforge.jar): the "root"
        # JSON field defaults to false (Optional<Boolean>.orElse(false))
        # when omitted, and net.puffish.skillsmod.server.data.CategoryData.
        # getSkillState only ever returns AVAILABLE/AFFORDABLE for a node
        # that is EITHER (a) connected via a `normal` edge to an already-
        # UNLOCKED neighbor, OR (b) isRoot() true - there is no other entry
        # point into a tree. Every prior generated category omitted "root"
        # entirely (issue #24: "have plenty of skill points but am unable to
        # allocate them" - reproduced across all 12 categories, not just
        # one), so with unlockedSkills starting empty for every player, every
        # node in every category permanently evaluated to LOCKED regardless
        # of points held. Only n0 needs it (one root per category; the tree
        # is a single connected component from there via `normal` edges).
        if i == 0:
            skills[node_id]["root"] = True
    for i, node_id in enumerate(a_ids):
        skills[node_id] = {"x": (5 + i) * 32, "y": -40, "definition": path_a[i]}
    for i, node_id in enumerate(b_ids):
        skills[node_id] = {"x": (5 + i) * 32, "y": 40, "definition": path_b[i]}
    write_json(cat_dir / "skills.json", skills)

    normal_pairs = [[trunk_ids[i], trunk_ids[i + 1]] for i in range(4)]
    normal_pairs.append([trunk_ids[4], a_ids[0]])
    normal_pairs.append([trunk_ids[4], b_ids[0]])
    normal_pairs += [[a_ids[i], a_ids[i + 1]] for i in range(4)]
    normal_pairs += [[b_ids[i], b_ids[i + 1]] for i in range(4)]

    connections = {
        "normal": {"bidirectional": normal_pairs},
        "exclusive": {"bidirectional": [[a_ids[0], b_ids[0]]]},
    }
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
# Trunk = first 5 nodes of the pre-overhaul 10-node rotation (unchanged).
# Fork: A = mining_speed/pickaxe_speed (cadence/utility - dig everything
# faster), B = fortune only (power/control - fewer, richer drops).
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
    },
    trunk=["mining_speed+3%", "fortune+0.1", "mining_speed+3%", "pickaxe_speed+3%", "fortune+0.1"],
    path_a=["mining_speed+3%", "pickaxe_speed+3%", "mining_speed+3%", "pickaxe_speed+3%", "mining_speed+3%"],
    path_b=["fortune+0.1", "fortune+0.1", "fortune+0.1", "fortune+0.1", "fortune+0.1"],
))

# ---------------------------------------------------------------------------
# Melee weapon classes (gear overhaul, post-Phase-9): one category per
# playstyle instead of a single blanket "Swords" bucket. Every non-sword
# type is one of Epic Fight's 5 custom weapon classes (dagger/greatsword/
# longsword/spear/tachi), each with a real one/two-handed mechanical
# identity (confirmed by reading their own capabilities/weapons/*.json -
# see DESIGN.md's gear overhaul section). Each category's trigger is a
# vanillaplusplus:<type>s item tag (generated by scripts/gen_weapon_tiers.py,
# covering all 10 tiers per class) rather than enumerating items inline.
# Reward *magnitudes* deliberately mirror the original swords/bows curve
# (100 + level * 40 XP curve, ~2-6% per node) - there's no live client in
# this sandbox to playtest actual combat balance, so keeping every category
# on the same mathematical shape and just varying *which* attributes it
# targets is the most defensible way to keep them comparably powerful
# without being able to verify it in play.
#
# Item 11 fork themes are all attributes-only and flow through VANILLA
# attack_speed/attack_damage - verified (DECISIONS.md "Item 11 research
# verdicts") that generic.attack_speed literally multiplies Epic Fight's
# attack-animation playback rate and generic.attack_damage flows through
# vanilla Player.attack() which Epic Fight reuses, so both actually affect
# animation-driven combat. Every melee category forks into a cadence path
# (attack_speed-led: fast/many hits) vs a power path (attack_damage-led:
# fewer/harder hits) - the flagship "fast vs slow-deliberate" split the user
# asked for. LANDMINE (verified, do not reintroduce): never put an
# `epicfight:` attribute (impact/armor_negation/stamina/...) in a
# puffish_skills:attribute reward - Epic Fight attaches those via a raw
# mixin bypassing the DefaultAttributeRegistry puffish's AttributeReward
# validation checks against, and datapack load is expected to hard-fail.
# ---------------------------------------------------------------------------
CATEGORIES.append(gen_category(
    "swords", "Swords", "diamond_sword", "nether",
    "100 + level * 40",
    [kill_entity_source("weapon_check", "silentgear:sword", 2)],
    {
        "sword_damage+3%": attr_reward("+3% Sword Damage", "diamond_sword", "puffish_attributes:sword_damage", 0.03, "multiply_base", "item"),
        "attack_speed+3%": attr_reward("+3% Attack Speed", "sugar", "generic.attack_speed", 0.03, "multiply_base", "item"),
        "melee_damage+2%": attr_reward("+2% Melee Damage", "strength", "puffish_skills:player.melee_damage", 0.02, "multiply_total"),
        "knockback+5%": attr_reward("+5% Knockback", "feather", "puffish_attributes:knockback", 0.05, "multiply_base", "item"),
        "attack_damage+3%": attr_reward("+3% Attack Damage", "iron_sword", "generic.attack_damage", 0.03, "multiply_base", "item"),
    },
    trunk=["sword_damage+3%", "attack_speed+3%", "sword_damage+3%", "melee_damage+2%", "attack_speed+3%"],
    path_a=["attack_speed+3%", "sword_damage+3%", "attack_speed+3%", "sword_damage+3%", "attack_speed+3%"],
    path_b=["attack_damage+3%", "knockback+5%", "attack_damage+3%", "knockback+5%", "attack_damage+3%"],
))

# Daggers - fast, dual-wieldable (1h/2h), low per-hit impact but many
# strikes (confirmed via capability file: max_strikes 0/1, impact ~0.8-1.0
# vs greatsword's single impact 4.0+). Identity: speed + mobility + luck
# (precision strikes), not raw power. Fork: A = attack_speed(larger)+
# movement_speed (cadence/utility, leaning further into the class's own
# identity), B = luck+melee_damage (power/control, precision crits).
CATEGORIES.append(gen_category(
    "daggers", "Daggers", "epicfight:iron_dagger", "husbandry",
    "100 + level * 40",
    [kill_entity_source("weapon_check", "#vanillaplusplus:daggers", 2)],
    {
        "attack_speed+4%": attr_reward("+4% Attack Speed", "sugar", "generic.attack_speed", 0.04, "multiply_base", "item"),
        "move_speed+2%": attr_reward("+2% Movement Speed", "feather", "generic.movement_speed", 0.02, "multiply_base", "item"),
        "luck+1": attr_reward("+1 Luck", "rabbit_foot", "generic.luck", 1, "addition", "item"),
        "melee_damage+2%": attr_reward("+2% Melee Damage", "strength", "puffish_skills:player.melee_damage", 0.02, "multiply_total"),
        "attack_speed+6%": attr_reward("+6% Attack Speed", "sugar", "generic.attack_speed", 0.06, "multiply_base", "item"),
    },
    trunk=["attack_speed+4%", "move_speed+2%", "attack_speed+4%", "luck+1", "move_speed+2%"],
    path_a=["attack_speed+6%", "move_speed+2%", "attack_speed+6%", "move_speed+2%", "attack_speed+6%"],
    path_b=["luck+1", "melee_damage+2%", "luck+1", "melee_damage+2%", "luck+1"],
))

# Greatswords - always two-handed, highest single-hit impact and armor
# negation of any melee class, fewest strikes. Identity: raw power, tanky.
# Fork: A = attack_speed(modest) only (cadence/utility - the class's one
# concession to speed), B = attack_damage+max_health+knockback (power/
# control, leaning further into the class's own identity).
CATEGORIES.append(gen_category(
    "greatswords", "Greatswords", "epicfight:iron_greatsword", "end",
    "100 + level * 40",
    [kill_entity_source("weapon_check", "#vanillaplusplus:greatswords", 2)],
    {
        "attack_damage+4%": attr_reward("+4% Attack Damage", "iron_sword", "generic.attack_damage", 0.04, "multiply_base", "item"),
        "knockback+6%": attr_reward("+6% Knockback", "feather", "puffish_attributes:knockback", 0.06, "multiply_base", "item"),
        "max_health+5%": attr_reward("+5% Max Health", "totem_of_undying", "generic.max_health", 0.05, "multiply_total", "item"),
        "attack_speed+2%": attr_reward("+2% Attack Speed", "sugar", "generic.attack_speed", 0.02, "multiply_base", "item"),
    },
    trunk=["attack_damage+4%", "knockback+6%", "attack_damage+4%", "max_health+5%", "knockback+6%"],
    path_a=["attack_speed+2%", "attack_speed+2%", "attack_speed+2%", "attack_speed+2%", "attack_speed+2%"],
    path_b=["attack_damage+4%", "max_health+5%", "knockback+6%", "attack_damage+4%", "max_health+5%"],
))

# Longswords - versatile hybrid (works one or two-handed, "common" stat
# profile rather than a distinct 1h/2h split). Identity: balanced jack-of-
# all-trades, small bonuses spread across both speed and power. Fork:
# A = attack_speed+movement_speed (cadence/utility), B = attack_damage+
# melee_damage (power/control) - both paths reuse the trunk's own
# definitions, no new attributes needed for this one.
CATEGORIES.append(gen_category(
    "longswords", "Longswords", "epicfight:iron_longsword", "adventure",
    "100 + level * 40",
    [kill_entity_source("weapon_check", "#vanillaplusplus:longswords", 2)],
    {
        "attack_damage+2%": attr_reward("+2% Attack Damage", "iron_sword", "generic.attack_damage", 0.02, "multiply_base", "item"),
        "attack_speed+2%": attr_reward("+2% Attack Speed", "sugar", "generic.attack_speed", 0.02, "multiply_base", "item"),
        "move_speed+1%": attr_reward("+1% Movement Speed", "feather", "generic.movement_speed", 0.01, "multiply_base", "item"),
        "melee_damage+3%": attr_reward("+3% Melee Damage", "strength", "puffish_skills:player.melee_damage", 0.03, "multiply_total"),
    },
    trunk=["attack_damage+2%", "attack_speed+2%", "melee_damage+3%", "move_speed+1%", "attack_damage+2%"],
    path_a=["attack_speed+2%", "move_speed+1%", "attack_speed+2%", "move_speed+1%", "attack_speed+2%"],
    path_b=["attack_damage+2%", "melee_damage+3%", "attack_damage+2%", "melee_damage+3%", "attack_damage+2%"],
))

# Spears - dual-mode reach weapon (1h with more armor negation, 2h with
# more strikes but less impact - confirmed via capability file). Identity:
# reach/range and armor penetration over raw speed. Fork: A = knockback+
# attack_speed (cadence/utility, quick jabs), B = entity_interaction_range
# (reach)+attack_damage (power/control, leaning further into the class's
# own identity).
CATEGORIES.append(gen_category(
    "spears", "Spears", "epicfight:iron_spear", "husbandry",
    "100 + level * 40",
    [kill_entity_source("weapon_check", "#vanillaplusplus:spears", 2)],
    {
        "reach+0.5": attr_reward("+0.5 Attack Reach", "epicfight:iron_spear", "minecraft:player.entity_interaction_range", 0.5, "addition", "item"),
        "attack_damage+3%": attr_reward("+3% Attack Damage", "iron_sword", "generic.attack_damage", 0.03, "multiply_base", "item"),
        "knockback+4%": attr_reward("+4% Knockback", "feather", "puffish_attributes:knockback", 0.04, "multiply_base", "item"),
        "melee_damage+2%": attr_reward("+2% Melee Damage", "strength", "puffish_skills:player.melee_damage", 0.02, "multiply_total"),
        "attack_speed+3%": attr_reward("+3% Attack Speed", "sugar", "generic.attack_speed", 0.03, "multiply_base", "item"),
    },
    trunk=["reach+0.5", "attack_damage+3%", "knockback+4%", "reach+0.5", "melee_damage+2%"],
    path_a=["knockback+4%", "attack_speed+3%", "knockback+4%", "attack_speed+3%", "knockback+4%"],
    path_b=["reach+0.5", "attack_damage+3%", "reach+0.5", "attack_damage+3%", "reach+0.5"],
))

# Tachi - combo/quickdraw focused ("common" profile, moderate impact,
# multi-strike). Identity: speed + mobility + a bit of luck, similar
# flavor to daggers but leaning more damage than pure evasion. Fork:
# A = attack_speed+movement_speed (cadence/utility), B = attack_damage+luck
# (power/control) - both paths reuse the trunk's own definitions.
CATEGORIES.append(gen_category(
    "tachi", "Tachi", "epicfight:iron_tachi", "nether",
    "100 + level * 40",
    [kill_entity_source("weapon_check", "#vanillaplusplus:tachis", 2)],
    {
        "attack_speed+3%": attr_reward("+3% Attack Speed", "sugar", "generic.attack_speed", 0.03, "multiply_base", "item"),
        "attack_damage+3%": attr_reward("+3% Attack Damage", "iron_sword", "generic.attack_damage", 0.03, "multiply_base", "item"),
        "move_speed+1%": attr_reward("+1% Movement Speed", "feather", "generic.movement_speed", 0.01, "multiply_base", "item"),
        "luck+1": attr_reward("+1 Luck", "rabbit_foot", "generic.luck", 1, "addition", "item"),
    },
    trunk=["attack_speed+3%", "attack_damage+3%", "move_speed+1%", "attack_speed+3%", "luck+1"],
    path_a=["attack_speed+3%", "move_speed+1%", "attack_speed+3%", "move_speed+1%", "attack_speed+3%"],
    path_b=["attack_damage+3%", "luck+1", "attack_damage+3%", "luck+1", "attack_damage+3%"],
))

# ---------------------------------------------------------------------------
# Bows (updated for the gear overhaul: bow/crossbow now craft through
# Silent Gear, which - like sword - uses one generic item id per gear type
# regardless of material, so this keys on silentgear:bow/silentgear:crossbow
# instead of vanilla's bow/crossbow ids). Fork: A = bow/crossbow projectile
# speed alternating (cadence/utility - faster shots, both weapon types),
# B = ranged_damage only (power/control).
# ---------------------------------------------------------------------------
CATEGORIES.append(gen_category(
    "bows", "Bows", "bow", "adventure",
    "100 + level * 40",
    [kill_entity_source("weapon_check", "silentgear:bow", 2),
     kill_entity_source("weapon_check2", "silentgear:crossbow", 2)],
    {
        "ranged_damage+3%": attr_reward("+3% Ranged Damage", "bow", "puffish_skills:player.ranged_damage", 0.03, "multiply_total", "item"),
        "bow_speed+3%": attr_reward("+3% Bow Projectile Speed", "arrow", "puffish_attributes:bow_projectile_speed", 0.03, "multiply_base", "item"),
        "crossbow_speed+3%": attr_reward("+3% Crossbow Projectile Speed", "crossbow", "puffish_attributes:crossbow_projectile_speed", 0.03, "multiply_base", "item"),
    },
    trunk=["ranged_damage+3%", "bow_speed+3%", "ranged_damage+3%", "crossbow_speed+3%", "ranged_damage+3%"],
    path_a=["bow_speed+3%", "crossbow_speed+3%", "bow_speed+3%", "crossbow_speed+3%", "bow_speed+3%"],
    path_b=["ranged_damage+3%", "ranged_damage+3%", "ranged_damage+3%", "ranged_damage+3%", "ranged_damage+3%"],
))

# ---------------------------------------------------------------------------
# Running. Fork: A = sprinting_speed only (cadence/utility), B = jump+
# step_height (power/control - clearing terrain rather than crossing it
# fast).
# ---------------------------------------------------------------------------
CATEGORIES.append(gen_category(
    "running", "Running", "leather_boots", "husbandry",
    "100 + level * 30",
    [stat_source("minecraft.custom:minecraft.sprint_one_cm", "0.02")],
    {
        "sprint_speed+3%": attr_reward("+3% Sprinting Speed", "speed", "puffish_attributes:sprinting_speed", 0.03, "multiply_base"),
        "stamina+5%": attr_reward("+5% Stamina", "saturation", "puffish_skills:player.stamina", 0.05, "multiply_total"),
        "jump+3%": attr_reward("+3% Jump", "jump_boost", "puffish_skills:player.jump", 0.03, "multiply_total"),
        "step_height+0.25": attr_reward("+0.25 Step Height", "scaffolding", "generic.step_height", 0.25, "addition", "item"),
    },
    trunk=["sprint_speed+3%", "stamina+5%", "sprint_speed+3%", "jump+3%", "stamina+5%"],
    path_a=["sprint_speed+3%", "sprint_speed+3%", "sprint_speed+3%", "sprint_speed+3%", "sprint_speed+3%"],
    path_b=["jump+3%", "step_height+0.25", "jump+3%", "step_height+0.25", "jump+3%"],
))

# ---------------------------------------------------------------------------
# Swimming. Fork: A = water_movement_efficiency only (cadence/utility),
# B = oxygen_bonus+submerged_mining_speed (power/control - staying down
# longer and working while there).
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
    trunk=["water_efficiency+8%", "oxygen+10%", "water_efficiency+8%", "submerged_mining_speed+5%", "oxygen+10%"],
    path_a=["water_efficiency+8%", "water_efficiency+8%", "water_efficiency+8%", "water_efficiency+8%", "water_efficiency+8%"],
    path_b=["oxygen+10%", "submerged_mining_speed+5%", "oxygen+10%", "submerged_mining_speed+5%", "oxygen+10%"],
))

# ---------------------------------------------------------------------------
# Building (no native trigger - granted via KubeJS BlockEvents.placed, see
# pack/kubejs/server_scripts/skills.js). Fork: A = block_break_speed only
# (cadence/utility), B = block_interaction_range+step_height (power/
# control - reaching/traversing more of the build without moving).
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
    trunk=["reach+0.5", "break_speed+3%", "reach+0.5", "step_height+0.25", "break_speed+3%"],
    path_a=["break_speed+3%", "break_speed+3%", "break_speed+3%", "break_speed+3%", "break_speed+3%"],
    path_b=["reach+0.5", "step_height+0.25", "reach+0.5", "step_height+0.25", "reach+0.5"],
))

# ---------------------------------------------------------------------------
# Magic (Phase 7 - mage/summoner combat archetype, instructions.md). Reward
# attributes are Ars Nouveau's own perk attributes (ars_nouveau:ars_nouveau.
# perk.{mana_regen,max_mana,spell_damage,warding} - confirmed by decompiling
# com.hollingsworth.arsnouveau.api.perk.PerkAttributes; the registered id is
# literally the dotted string passed to DeferredRegister.register(), not a
# shortened form), not puffish_attributes (which predates Ars Nouveau being
# in the pack and has nothing magic-specific). XP source is a kill_entity
# check for holding an ars_nouveau:wand at the kill - an approximation, not
# exact (a spell can kill well after the wand leaves hand, e.g. a
# slow-falling AOE), but it mirrors the same kill_entity_source pattern
# Swords/Bows already use with no new mechanism needed. Fork: A = mana_regen
# only (cadence/utility - cast more often), B = spell_damage+max_mana
# (power/control - hit harder, less often).
# ---------------------------------------------------------------------------
CATEGORIES.append(gen_category(
    "magic", "Magic", "ars_nouveau:wand", "story",
    "100 + level * 40",
    [kill_entity_source("weapon_check", "ars_nouveau:wand", 2)],
    {
        "spell_damage+3%": attr_reward("+3% Spell Damage", "ars_nouveau:wand", "ars_nouveau:ars_nouveau.perk.spell_damage", 0.03, "multiply_base", "item"),
        "max_mana+10": attr_reward("+10 Max Mana", "ars_nouveau:source_gem", "ars_nouveau:ars_nouveau.perk.max_mana", 10, "addition", "item"),
        "mana_regen+10%": attr_reward("+10% Mana Regen", "ars_nouveau:amulet_of_mana_regen", "ars_nouveau:ars_nouveau.perk.mana_regen", 0.1, "multiply_base", "item"),
    },
    trunk=["spell_damage+3%", "max_mana+10", "spell_damage+3%", "mana_regen+10%", "max_mana+10"],
    path_a=["mana_regen+10%", "mana_regen+10%", "mana_regen+10%", "mana_regen+10%", "mana_regen+10%"],
    path_b=["spell_damage+3%", "max_mana+10", "spell_damage+3%", "max_mana+10", "spell_damage+3%"],
))

write_json(OUT / "config.json", {"version": 3, "categories": CATEGORIES})
print(f"generated {len(CATEGORIES)} categories under {OUT}")
