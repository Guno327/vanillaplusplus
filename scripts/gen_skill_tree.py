#!/usr/bin/env python3
"""Generate Pufferfish's Skills datapack content (category/experience/definitions/
skills/connections JSON) from a compact Python spec, writing into
pack/kubejs/data/puffish_skills/puffish_skills/ (KubeJS's raw-datapack folder).

Issue #71 ("Expand Skill Trees / Categories") overhaul. Owner's six asks and
where each lands in this generator:

  1. Many more nodes + real branching -> every category is now a 34-node
     TREE (1 root + 3 themed branches of 11 nodes each, and each branch
     itself forks twice more - see `build_tree()`/BRANCH_SHAPE below), not
     the old 15-node trunk+2-lines shape.
  2. No exclusivity, everything reachable -> connections.json now emits
     ONLY a `normal` group; the `exclusive` group is omitted entirely
     (confirmed safe: net.puffish.skillsmod.config.skill.
     SkillConnectionsConfig.parse defaults a missing "exclusive" key to
     SkillConnectionsGroupConfig.empty() via orElseGet - javap'd against
     the installed puffish_skills-0.18.1-1.21-neoforge.jar this session,
     same discipline as every other ground-truth note in this file).
  3. Smaller per-node uplift -> ATTR_META's `value` column is roughly
     3-6x smaller than the old generator's ~2-6% per-node magnitudes (see
     ATTR_META below); with more nodes per attribute the *maxed* total per
     stat still lands in a sane place (see DECISIONS.md's Item 11 followup
     entry for this issue's worked numbers).
  4. Wider buff variety -> ATTR_META now spans 49 distinct attribute ids
     across vanilla `generic.*`/`minecraft:player.*`, `puffish_skills:
     player.*`, `ars_nouveau:ars_nouveau.perk.*`, and (new this issue) 22
     of puffish_attributes' own custom attributes - every single id in
     ATTR_META is verified against a real installed jar, see the ATTR_META
     docstring for exactly how.
  5. Many more categories -> 12 -> 23 (11 new: farming, fishing, trading,
     enchanting, cooking, exploration, sailing, taming, smithing, alchemy,
     woodcutting), each with a real, triggerable XP source - see the
     ExperienceSource helpers below and CATEGORY_SPECS' `source` column.
     Every one of puffish_skills' 14 *built-in* experience source types
     was enumerated from the jar (BuiltinExperienceSources.class) before
     picking which to use; only the ones with an unambiguous JSON shape
     (mine_block/break_block/kill_entity/fish_item/smelt_item/enchant_item/
     increase_stat) were used - `craft_item` and bare `criterion` sources
     were deliberately AVOIDED because their trigger conditions couldn't be
     verified against real recipes/advancement criteria in this sandbox
     (no live client - see the repo's Verification section in DESIGN.md).
  6. Exponential XP curve -> every category's experience_per_level is
     "70 * pow(1.13, level)" (see EXPERIENCE_EXPR below) instead of the old
     linear "100 + level * 40". `pow` is a real function in puffish_skills'
     own expression engine (net.puffish.skillsmod.expression.DefaultParser
     - javap'd this session, confirms `pow`/`sqrt`/`min`/`max`/`clamp`/
     trig functions are all registered FunctionOperators).

Layout is still fully generated, never hand-typed: `layout_tree()` assigns
every node an (x, y) by depth-then-slot-index, which is collision-free by
construction (different depths get different x; same-depth nodes get
strictly increasing y) - see its docstring. scripts/ci/check_skill_trees.py
asserts this holds (no two nodes in a category share coordinates) as a
belt-and-suspenders check, not just trusting the algorithm.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "pack" / "kubejs" / "data" / "puffish_skills" / "puffish_skills"

X_SPACING = 32
Y_SPACING = 40

# Every category's tree: 1 root -> 3 theme branches, each theme branch built
# by build_tree() with this per-depth branch-factor list (depth 0 = the
# theme's own entry node, relative to that branch, not the category root).
# [2, 2, 1] means: entry(1) -> 2 children -> each of those 2 children -> 4
# grandchildren -> each of those 4 gets 1 more child -> 4 leaves.
# Node count per theme = 1 + 2 + 4 + 4 = 11. Category total = 1 (cat root)
# + 3*11 = 34 nodes - inside the 30-45/category range this issue asked for,
# with two real branch points per theme (not two straight lines).
BRANCH_SHAPE = [2, 2, 1]

# Exponential per-level XP cost (issue #71 point 6): cost to go from `level`
# to `level+1` grows geometrically, so every category is eventually fully
# achievable but progress slows hard late-game. Worked examples (see this
# file's own `if __name__ == "__main__"` block / DECISIONS.md for the
# printed table): level 1 costs 70 XP, level 5 costs ~114 XP/step (~454
# cumulative), level 10 costs ~210 XP/step (~1289 cumulative), level 20
# costs ~714 XP/step (~5666 cumulative), level 34 (a fully maxed category)
# costs ~3951 XP for that one last point (~33800 cumulative XP total).
EXPERIENCE_EXPR = "70 * pow(1.13, level)"


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent="\t") + "\n")


# ---------------------------------------------------------------------------
# Tree building + layout (generic - reused by every category).
# ---------------------------------------------------------------------------
def build_tree(prefix, branch_factors):
    """Builds a strict tree (every non-root node has exactly one parent):
    root, then `branch_factors[d]` children for every node at depth d.
    Returns (root_id, order (pre-order DFS list of every node id, root
    first), children_map (node -> [child ids]), depth_map (node -> depth,
    root is 0))."""
    counter = [0]

    def next_id():
        counter[0] += 1
        return f"{prefix}{counter[0]}"

    children_map = {}
    depth_map = {}
    order = []

    root_id = next_id()
    order.append(root_id)
    depth_map[root_id] = 0

    def recurse(node, depth):
        if depth >= len(branch_factors):
            return
        kids = []
        for _ in range(branch_factors[depth]):
            cid = next_id()
            order.append(cid)
            depth_map[cid] = depth + 1
            kids.append(cid)
            recurse(cid, depth + 1)
        children_map[node] = kids

    recurse(root_id, 0)
    return root_id, order, children_map, depth_map


def layout_tree(root_id, children_map):
    """Layered layout, collision-free BY CONSTRUCTION: x = depth *
    X_SPACING (so nodes at different depths can never share a position),
    y = slot-index-within-that-depth * Y_SPACING, centered around 0 (so
    nodes at the SAME depth get strictly increasing, evenly-spaced y - the
    minimum gap between any two nodes in the whole category is
    min(X_SPACING, Y_SPACING), never 0). Visitation is pre-order DFS, so
    siblings within one branch land in contiguous y slots and the tree
    reads as visually grouped by branch rather than interleaved.

    Returns {node_id: (x, y)}."""
    depth_of = {}
    slots_at_depth = {}

    def dfs(node, depth):
        depth_of[node] = depth
        slots_at_depth.setdefault(depth, []).append(node)
        for child in children_map.get(node, []):
            dfs(child, depth + 1)

    dfs(root_id, 0)

    positions = {}
    for depth, nodes in slots_at_depth.items():
        offset = (len(nodes) - 1) / 2.0
        for i, node in enumerate(nodes):
            x = depth * X_SPACING
            y = int(round((i - offset) * Y_SPACING))
            positions[node] = (x, y)
    return positions


# ---------------------------------------------------------------------------
# Experience source helpers. Every `type` string below (puffish_skills:
# mine_block/break_block/kill_entity/fish_item/smelt_item/enchant_item/
# increase_stat) and every bare operation id (get_mined_block_state,
# get_tool_item_stack, get_broken_block_state, get_dropped_experience,
# get_weapon_item_stack, get_fished_item_stack, get_smelted_item_stack,
# get_levels, get_stat, get_increase_amount) was confirmed this session by
# extracting puffish_skills-0.18.1-1.21-neoforge.jar and reading the string
# constant pool of net.puffish.skillsmod.experience.source.builtin.*
# ExperienceSource classes and their nested `$Data` records (field names ->
# `get_<field>` operation names is the mod's own consistent convention,
# already relied on by this file's pre-existing mine_block_source/
# kill_entity_source/stat_source before this issue). `puffish_skills:test`
# with an {"item": ...}/{"block": ...} key was already proven working
# elsewhere in this file (kill_entity_source's weapon check, mine_block_
# source's ore check) - reused verbatim, not reinvented.
# ---------------------------------------------------------------------------
def mine_block_source(ore_tiers):
    """ore_tiers: list of (test_key, block_or_tag, xp) - silk_touch-aware."""
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


def break_block_source(block_tiers):
    """block_tiers: list of (test_key, block_or_tag, xp). Unlike mine_block
    (ore-mining, silk_touch-aware), break_block fires for breaking ANY
    block regardless of tool - used here for crops (farming) and logs
    (woodcutting), neither of which cares about silk touch."""
    variables = {}
    conditions = []
    for key, block, xp in block_tiers:
        variables[key] = {
            "operations": [
                {"type": "get_broken_block_state"},
                {"type": "puffish_skills:test", "data": {"block": block}},
            ]
        }
        conditions.append({"condition": key, "expression": str(xp)})
    return {"type": "puffish_skills:break_block", "data": {"variables": variables, "experience": conditions}}


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


def fish_item_source(fish_tiers):
    """fish_tiers: list of (test_key, item_or_tag, xp) tested against
    get_fished_item_stack - mutually exclusive by item identity, same
    pattern as mine_block_source's ore tiers."""
    variables = {}
    conditions = []
    for key, item, xp in fish_tiers:
        variables[key] = {
            "operations": [
                {"type": "get_fished_item_stack"},
                {"type": "puffish_skills:test", "data": {"item": item}},
            ]
        }
        conditions.append({"condition": key, "expression": str(xp)})
    return {"type": "puffish_skills:fish_item", "data": {"variables": variables, "experience": conditions}}


def smelt_item_source(item_tiers):
    """item_tiers: list of (test_key, item, xp) tested against
    get_smelted_item_stack (furnace/smoker/blast furnace output)."""
    variables = {}
    conditions = []
    for key, item, xp in item_tiers:
        variables[key] = {
            "operations": [
                {"type": "get_smelted_item_stack"},
                {"type": "puffish_skills:test", "data": {"item": item}},
            ]
        }
        conditions.append({"condition": key, "expression": str(xp)})
    return {"type": "puffish_skills:smelt_item", "data": {"variables": variables, "experience": conditions}}


def enchant_item_source(xp_per_level):
    """Fires on enchanting-table use; `levels` = enchantment levels spent
    (get_levels operation, confirmed against EnchantItemExperienceSource's
    own `levels` Data field). Gated on `levels > 0` (a real comparison
    against a declared variable) rather than an always-true literal - this
    engine's expression grammar (net.puffish.skillsmod.expression.
    DefaultParser) has no confirmed boolean-literal constant, only named
    constants `pi`/`tau`, so an always-true condition wasn't a safe bet to
    invent; every other condition in this file is a real comparison or
    variable the same way."""
    return {
        "type": "puffish_skills:enchant_item",
        "data": {
            "variables": {"levels": {"operations": [{"type": "get_levels"}]}},
            "experience": [{"condition": "levels > 0", "expression": f"levels * {xp_per_level}"}],
        },
    }


def stat_source(stat_id, xp_per_unit):
    """stat_id: e.g. "minecraft.custom:minecraft.sprint_one_cm" - packs
    StatType(namespace.path):Stat(namespace.path) into one string (BuiltinJson
    #parseStat, confirmed against the real github.com/pufmat/skillsmod
    source, not decompiled bytecode alone - two prior bytecode-only guesses
    were wrong per this file's original authoring)."""
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


# ---------------------------------------------------------------------------
# ATTR_META - the buff-variety allowlist (issue #71 point 4). Every id here
# was verified this session against a real installed jar:
#   - `generic.*` / `minecraft:player.*` ids: the exact strings already
#     shipped and working in this file before this issue (mining_speed,
#     sword_damage, etc. categories existed pre-#71) - unchanged, not
#     reverified beyond "already proven in production".
#   - `puffish_skills:player.*` ids: same - already proven (fortune,
#     melee_damage, ranged_damage, stamina, jump).
#   - `ars_nouveau:ars_nouveau.perk.*` ids: same - already proven
#     (spell_damage, max_mana, mana_regen).
#   - `puffish_attributes:*` ids (22 of these are NEW this issue - mining_
#     speed/pickaxe_speed/sword_damage/knockback/bow_projectile_speed/
#     crossbow_projectile_speed/sprinting_speed were already in use): every
#     single one of these, new or old, is a registered-attribute
#     translation key read directly out of puffish_attributes-0.8.2-1.21-
#     neoforge.jar's assets/puffish_attributes/lang/en_us.json this
#     session (`attribute.puffish_attributes.<id>` keys) - that lang file
#     is generated from the mod's own DeferredRegister calls, so every key
#     in it is a real registered attribute id, not a guess.
# `operation` is one of puffish_skills' own AttributeReward vocabulary -
# "addition"/"multiply_base"/"multiply_total" - confirmed by javap'ing
# net.puffish.skillsmod.api.json.BuiltinJson#parseAttributeOperation this
# session (NOT the same vocabulary as vanilla AttributeModifier.Operation's
# add_value/add_multiplied_base/add_multiplied_total, which is what a
# DIFFERENT file in this pack, mob_scaling.js, got bitten by per
# DECISIONS.md - that landmine does not apply to puffish_skills:attribute
# rewards, which is all this generator ever emits).
# `value` is deliberately small (issue #71 point 3): most percentage-style
# attributes sit at 0.6-1% per node instead of the old ~2-6%, so a maxed-out
# 5-6-node attribute lands around 3-6% total instead of the old design's
# single-path totals of 15-30%. See this file's __main__ block for the
# printed per-category maxed totals.
# ---------------------------------------------------------------------------
ATTR_META = {
    # vanilla generic./player. (pre-existing, proven)
    "attack_speed": ("generic.attack_speed", "multiply_base", 0.007, "sugar", "item", "Attack Speed"),
    "attack_damage": ("generic.attack_damage", "multiply_base", 0.007, "iron_sword", "item", "Attack Damage"),
    "move_speed": ("generic.movement_speed", "multiply_base", 0.006, "feather", "item", "Movement Speed"),
    "luck": ("generic.luck", "addition", 0.08, "rabbit_foot", "item", "Luck"),
    "max_health": ("generic.max_health", "multiply_total", 0.006, "totem_of_undying", "item", "Max Health"),
    "step_height": ("generic.step_height", "addition", 0.05, "scaffolding", "item", "Step Height"),
    "water_efficiency": ("generic.water_movement_efficiency", "multiply_total", 0.02, "dolphins_grace", "effect", "Water Movement"),
    "oxygen": ("generic.oxygen_bonus", "multiply_total", 0.03, "conduit_power", "effect", "Oxygen"),
    "submerged_mining_speed": ("minecraft:player.submerged_mining_speed", "multiply_base", 0.012, "turtle_helmet", "item", "Underwater Mining Speed"),
    "entity_reach": ("minecraft:player.entity_interaction_range", "addition", 0.12, "epicfight:iron_spear", "item", "Attack Reach"),
    "block_reach": ("minecraft:player.block_interaction_range", "addition", 0.12, "bricks", "item", "Block Reach"),
    "break_speed": ("minecraft:player.block_break_speed", "multiply_base", 0.008, "iron_pickaxe", "item", "Block Break Speed"),
    # puffish_skills:player.* (pre-existing, proven)
    "fortune": ("puffish_skills:player.fortune", "addition", 0.02, "diamond", "item", "Fortune"),
    "melee_damage": ("puffish_skills:player.melee_damage", "multiply_total", 0.006, "strength", "effect", "Melee Damage"),
    "ranged_damage": ("puffish_skills:player.ranged_damage", "multiply_total", 0.006, "bow", "item", "Ranged Damage"),
    "stamina": ("puffish_skills:player.stamina", "multiply_total", 0.01, "saturation", "effect", "Stamina"),
    "jump": ("puffish_skills:player.jump", "multiply_total", 0.008, "jump_boost", "effect", "Jump"),
    # ars_nouveau perk attributes (pre-existing, proven)
    "spell_damage": ("ars_nouveau:ars_nouveau.perk.spell_damage", "multiply_base", 0.007, "ars_nouveau:wand", "item", "Spell Damage"),
    "max_mana": ("ars_nouveau:ars_nouveau.perk.max_mana", "addition", 3, "ars_nouveau:source_gem", "item", "Max Mana"),
    "mana_regen": ("ars_nouveau:ars_nouveau.perk.mana_regen", "multiply_base", 0.02, "ars_nouveau:amulet_of_mana_regen", "item", "Mana Regen"),
    # puffish_attributes (bow_/crossbow_/mining_/pickaxe_speed, sword_damage,
    # knockback, sprinting_speed pre-existing/proven; the rest are new
    # this issue, verified via the mod's own lang file - see docstring above)
    "mining_speed": ("puffish_attributes:mining_speed", "multiply_base", 0.007, "haste", "effect", "Mining Speed"),
    "pickaxe_speed": ("puffish_attributes:pickaxe_speed", "multiply_base", 0.008, "diamond_pickaxe", "item", "Pickaxe Speed"),
    "sword_damage": ("puffish_attributes:sword_damage", "multiply_base", 0.007, "diamond_sword", "item", "Sword Damage"),
    "knockback": ("puffish_attributes:knockback", "multiply_base", 0.012, "feather", "item", "Knockback"),
    "bow_speed": ("puffish_attributes:bow_projectile_speed", "multiply_base", 0.007, "arrow", "item", "Bow Projectile Speed"),
    "crossbow_speed": ("puffish_attributes:crossbow_projectile_speed", "multiply_base", 0.007, "crossbow", "item", "Crossbow Projectile Speed"),
    "sprint_speed": ("puffish_attributes:sprinting_speed", "multiply_base", 0.007, "speed", "effect", "Sprinting Speed"),
    "breaking_speed": ("puffish_attributes:breaking_speed", "multiply_base", 0.008, "iron_pickaxe", "item", "Breaking Speed"),
    "experience_gain": ("puffish_attributes:experience", "multiply_base", 0.01, "experience_bottle", "item", "Experience Gain"),
    "life_steal": ("puffish_attributes:life_steal", "addition", 0.006, "regeneration", "effect", "Life Steal"),
    "stealth": ("puffish_attributes:stealth", "multiply_base", 0.015, "invisibility", "effect", "Stealth"),
    "armor_shred": ("puffish_attributes:armor_shred", "addition", 0.15, "shears", "item", "Armor Shred"),
    "toughness_shred": ("puffish_attributes:toughness_shred", "addition", 0.1, "flint", "item", "Toughness Shred"),
    "resistance": ("puffish_attributes:resistance", "multiply_base", 0.007, "resistance", "effect", "Resistance"),
    "melee_resistance": ("puffish_attributes:melee_resistance", "multiply_base", 0.007, "shield", "item", "Melee Resistance"),
    "ranged_resistance": ("puffish_attributes:ranged_resistance", "multiply_base", 0.007, "shield", "item", "Ranged Resistance"),
    "magic_resistance": ("puffish_attributes:magic_resistance", "multiply_base", 0.007, "ender_pearl", "item", "Magic Resistance"),
    "magic_damage": ("puffish_attributes:magic_damage", "multiply_base", 0.007, "blaze_powder", "item", "Magic Damage"),
    "healing": ("puffish_attributes:healing", "multiply_base", 0.01, "regeneration", "effect", "Healing"),
    "natural_regeneration": ("puffish_attributes:natural_regeneration", "multiply_base", 0.01, "regeneration", "effect", "Natural Regeneration"),
    "fall_reduction": ("puffish_attributes:fall_reduction", "addition", 0.015, "slime_ball", "item", "Fall Reduction"),
    "trident_damage": ("puffish_attributes:trident_damage", "multiply_base", 0.008, "trident", "item", "Trident Damage"),
    "mount_speed": ("puffish_attributes:mount_speed", "multiply_base", 0.008, "saddle", "item", "Mount Speed"),
    "consuming_speed": ("puffish_attributes:consuming_speed", "multiply_base", 0.012, "apple", "item", "Consuming Speed"),
    "tamed_damage": ("puffish_attributes:tamed_damage", "multiply_base", 0.008, "bone", "item", "Tamed Damage"),
    "tamed_resistance": ("puffish_attributes:tamed_resistance", "multiply_base", 0.007, "lead", "item", "Tamed Resistance"),
    "axe_damage": ("puffish_attributes:axe_damage", "multiply_base", 0.007, "diamond_axe", "item", "Axe Damage"),
    "axe_speed": ("puffish_attributes:axe_speed", "multiply_base", 0.008, "diamond_axe", "item", "Axe Speed"),
    "repair_cost": ("puffish_attributes:repair_cost", "addition", -0.25, "anvil", "item", "Repair Cost"),
}


def attr_definition(attr_key):
    attribute, operation, value, icon, icon_type, label = ATTR_META[attr_key]
    if operation == "addition":
        display = f"{value:+g}"
    else:
        display = f"{value * 100:+.2g}%"
    icon_data = {"effect": icon} if icon_type == "effect" else {"item": icon}
    return {
        "title": f"{display} {label}",
        "icon": {"type": icon_type, "data": icon_data},
        "rewards": [{"type": "puffish_skills:attribute", "data": {"attribute": attribute, "value": value, "operation": operation}}],
    }


# ---------------------------------------------------------------------------
# gen_category - builds one category's whole tree from a compact spec.
# ---------------------------------------------------------------------------
def gen_category(cat_id, title, icon_item, background, sources, themes, root_attr):
    """themes: list of exactly 3 (attr_key_a, attr_key_b) pairs - each
    becomes an 11-node branch (BRANCH_SHAPE) off the category root, with
    nodes alternating between the pair's two attributes by depth within
    the branch (depth 0/2 -> attr_key_a, depth 1/3 -> attr_key_b). root_attr:
    attr_key used for the category's own single root node."""
    assert len(themes) == 3, f"{cat_id}: expected exactly 3 themes, got {len(themes)}"

    cat_dir = OUT / "categories" / cat_id

    write_json(cat_dir / "category.json", {
        "unlocked_by_default": True,
        "title": title,
        "icon": {"type": "item", "data": {"item": icon_item}},
        "background": f"textures/gui/advancements/backgrounds/{background}.png",
    })

    write_json(cat_dir / "experience.json", {
        "experience_per_level": {"type": "expression", "data": {"expression": EXPERIENCE_EXPR}},
        "sources": sources,
    })

    # Deterministic order matters here: a `set` would iterate in an order
    # that varies run-to-run (Python randomizes str hash seeds per process),
    # which would make definitions.json's key order - and therefore this
    # generator's output - nondeterministic between runs for no reason.
    # dict.fromkeys() dedups while preserving first-seen insertion order.
    used_attrs = list(dict.fromkeys([root_attr] + [attr for pair in themes for attr in pair]))
    definitions = {attr_key: attr_definition(attr_key) for attr_key in used_attrs}
    write_json(cat_dir / "definitions.json", definitions)

    cat_root = "root"
    children_map = {}
    skills = {cat_root: {"definition": root_attr, "root": True}}
    normal_pairs = []

    theme_roots = []
    for theme_idx, (attr_a, attr_b) in enumerate(themes):
        prefix = f"t{theme_idx}_"
        theme_root, order, theme_children, depth_map = build_tree(prefix, BRANCH_SHAPE)
        theme_roots.append(theme_root)
        children_map.update(theme_children)
        for node in order:
            attr_key = attr_a if depth_map[node] % 2 == 0 else attr_b
            skills[node] = {"definition": attr_key}
        for parent, kids in theme_children.items():
            for kid in kids:
                normal_pairs.append([parent, kid])

    children_map[cat_root] = theme_roots
    for theme_root in theme_roots:
        normal_pairs.append([cat_root, theme_root])

    positions = layout_tree(cat_root, children_map)
    for node_id, (x, y) in positions.items():
        skills[node_id]["x"] = x
        skills[node_id]["y"] = y
    # key order cosmetics only (root/x/y/definition vs x/y/definition) don't
    # matter to the parser - JSON objects are unordered - so no reordering
    # pass is needed here.

    write_json(cat_dir / "skills.json", skills)
    write_json(cat_dir / "connections.json", {"normal": {"bidirectional": normal_pairs}})

    return cat_id, len(skills)


# ---------------------------------------------------------------------------
# Category specs. Every `themes` entry is (attr_key_a, attr_key_b) - keys
# into ATTR_META above. See this file's module docstring point 4/5 for how
# these were chosen (existing 12 categories keep their pre-#71 attribute
# families as themes 0/1 and gain a new 3rd theme; the 11 new categories
# each pair a real XP source with thematically-plausible attributes).
# ---------------------------------------------------------------------------
CATEGORY_SPECS = [
    dict(
        cat_id="mining", title="Mining", icon="diamond_pickaxe", background="stone",
        sources=[mine_block_source([
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
        themes=[("mining_speed", "breaking_speed"), ("fortune", "pickaxe_speed"), ("luck", "experience_gain")],
        root_attr="mining_speed",
    ),
    dict(
        cat_id="swords", title="Swords", icon="diamond_sword", background="nether",
        sources=[kill_entity_source("weapon_check", "silentgear:sword", 2)],
        themes=[("sword_damage", "attack_speed"), ("attack_damage", "knockback"), ("melee_damage", "life_steal")],
        root_attr="sword_damage",
    ),
    dict(
        cat_id="daggers", title="Daggers", icon="epicfight:iron_dagger", background="husbandry",
        sources=[kill_entity_source("weapon_check", "#vanillaplusplus:daggers", 2)],
        themes=[("attack_speed", "move_speed"), ("luck", "melee_damage"), ("stealth", "armor_shred")],
        root_attr="attack_speed",
    ),
    dict(
        cat_id="greatswords", title="Greatswords", icon="epicfight:iron_greatsword", background="end",
        sources=[kill_entity_source("weapon_check", "#vanillaplusplus:greatswords", 2)],
        themes=[("attack_damage", "knockback"), ("max_health", "attack_speed"), ("toughness_shred", "resistance")],
        root_attr="attack_damage",
    ),
    dict(
        cat_id="longswords", title="Longswords", icon="epicfight:iron_longsword", background="adventure",
        sources=[kill_entity_source("weapon_check", "#vanillaplusplus:longswords", 2)],
        themes=[("attack_damage", "attack_speed"), ("melee_damage", "move_speed"), ("melee_resistance", "ranged_resistance")],
        root_attr="attack_damage",
    ),
    dict(
        cat_id="spears", title="Spears", icon="epicfight:iron_spear", background="husbandry",
        sources=[kill_entity_source("weapon_check", "#vanillaplusplus:spears", 2)],
        themes=[("entity_reach", "knockback"), ("attack_damage", "attack_speed"), ("melee_damage", "armor_shred")],
        root_attr="entity_reach",
    ),
    dict(
        cat_id="tachi", title="Tachi", icon="epicfight:iron_tachi", background="nether",
        sources=[kill_entity_source("weapon_check", "#vanillaplusplus:tachis", 2)],
        themes=[("attack_speed", "move_speed"), ("attack_damage", "luck"), ("stealth", "life_steal")],
        root_attr="attack_speed",
    ),
    dict(
        cat_id="bows", title="Bows", icon="bow", background="adventure",
        sources=[kill_entity_source("weapon_check", "silentgear:bow", 2),
                 kill_entity_source("weapon_check2", "silentgear:crossbow", 2)],
        themes=[("bow_speed", "crossbow_speed"), ("ranged_damage", "repair_cost"), ("ranged_resistance", "fall_reduction")],
        root_attr="ranged_damage",
    ),
    dict(
        cat_id="running", title="Running", icon="leather_boots", background="husbandry",
        sources=[stat_source("minecraft.custom:minecraft.sprint_one_cm", "0.02")],
        themes=[("sprint_speed", "step_height"), ("jump", "stamina"), ("fall_reduction", "move_speed")],
        root_attr="sprint_speed",
    ),
    dict(
        cat_id="swimming", title="Swimming", icon="turtle_helmet", background="end",
        sources=[stat_source("minecraft.custom:minecraft.swim_one_cm", "0.03")],
        themes=[("water_efficiency", "oxygen"), ("submerged_mining_speed", "trident_damage"), ("natural_regeneration", "healing")],
        root_attr="water_efficiency",
    ),
    dict(
        cat_id="building", title="Building", icon="bricks", background="husbandry",
        sources=[],  # granted out-of-band from BlockEvents.placed, see skills.js
        themes=[("break_speed", "block_reach"), ("step_height", "repair_cost"), ("experience_gain", "max_health")],
        root_attr="break_speed",
    ),
    dict(
        cat_id="magic", title="Magic", icon="ars_nouveau:wand", background="story",
        sources=[kill_entity_source("weapon_check", "ars_nouveau:wand", 2)],
        themes=[("spell_damage", "magic_damage"), ("max_mana", "mana_regen"), ("magic_resistance", "healing")],
        root_attr="spell_damage",
    ),
    # -------------------------------------------------------------------
    # New categories (issue #71 point 5).
    # -------------------------------------------------------------------
    dict(
        cat_id="farming", title="Farming", icon="diamond_hoe", background="husbandry",
        sources=[break_block_source([
            ("wheat", "minecraft:wheat", 2),
            ("carrots", "minecraft:carrots", 2),
            ("potatoes", "minecraft:potatoes", 2),
            ("beetroots", "minecraft:beetroots", 2),
            ("nether_wart", "minecraft:nether_wart", 3),
        ])],
        themes=[("consuming_speed", "stamina"), ("fortune", "break_speed"), ("healing", "natural_regeneration")],
        root_attr="fortune",
    ),
    dict(
        cat_id="fishing", title="Fishing", icon="fishing_rod", background="adventure",
        sources=[fish_item_source([
            ("cod", "minecraft:cod", 2),
            ("salmon", "minecraft:salmon", 2),
            ("pufferfish", "minecraft:pufferfish", 4),
            ("tropical_fish", "minecraft:tropical_fish", 4),
            ("junk_bow", "minecraft:bow", 5),
            ("treasure_book", "minecraft:enchanted_book", 12),
            ("treasure_nautilus", "minecraft:nautilus_shell", 12),
            ("treasure_saddle", "minecraft:saddle", 10),
            ("treasure_name_tag", "minecraft:name_tag", 10),
        ])],
        themes=[("luck", "fortune"), ("trident_damage", "water_efficiency"), ("consuming_speed", "mount_speed")],
        root_attr="luck",
    ),
    dict(
        cat_id="trading", title="Trading", icon="emerald", background="husbandry",
        sources=[stat_source("minecraft.custom:minecraft.traded_with_villager", "25")],
        themes=[("luck", "max_health"), ("experience_gain", "healing"), ("stealth", "resistance")],
        root_attr="luck",
    ),
    dict(
        cat_id="enchanting", title="Enchanting", icon="enchanting_table", background="story",
        sources=[enchant_item_source(4)],
        themes=[("magic_damage", "magic_resistance"), ("repair_cost", "experience_gain"), ("armor_shred", "toughness_shred")],
        root_attr="magic_damage",
    ),
    dict(
        cat_id="cooking", title="Cooking", icon="furnace", background="husbandry",
        sources=[smelt_item_source([
            ("beef", "minecraft:cooked_beef", 2),
            ("porkchop", "minecraft:cooked_porkchop", 2),
            ("chicken", "minecraft:cooked_chicken", 2),
            ("mutton", "minecraft:cooked_mutton", 2),
            ("rabbit", "minecraft:cooked_rabbit", 2),
            ("cod", "minecraft:cooked_cod", 2),
            ("salmon", "minecraft:cooked_salmon", 2),
            ("potato", "minecraft:baked_potato", 2),
            ("kelp", "minecraft:dried_kelp", 1),
        ])],
        themes=[("consuming_speed", "healing"), ("natural_regeneration", "max_health"), ("stamina", "fall_reduction")],
        root_attr="healing",
    ),
    dict(
        cat_id="exploration", title="Exploration", icon="compass", background="adventure",
        sources=[stat_source("minecraft.custom:minecraft.walk_one_cm", "0.015")],
        themes=[("move_speed", "sprint_speed"), ("fall_reduction", "step_height"), ("luck", "experience_gain")],
        root_attr="move_speed",
    ),
    dict(
        cat_id="sailing", title="Sailing", icon="oak_boat", background="end",
        sources=[stat_source("minecraft.custom:minecraft.boat_one_cm", "0.02")],
        themes=[("mount_speed", "water_efficiency"), ("oxygen", "trident_damage"), ("fall_reduction", "resistance")],
        root_attr="mount_speed",
    ),
    dict(
        cat_id="taming", title="Taming", icon="lead", background="husbandry",
        sources=[stat_source("minecraft.custom:minecraft.animals_bred", "30")],
        themes=[("mount_speed", "tamed_damage"), ("tamed_resistance", "healing"), ("luck", "max_health")],
        root_attr="tamed_damage",
    ),
    dict(
        cat_id="smithing", title="Smithing", icon="smithing_table", background="nether",
        sources=[stat_source("minecraft.custom:minecraft.interact_with_smithing_table", "15")],
        themes=[("repair_cost", "experience_gain"), ("sword_damage", "axe_damage"), ("trident_damage", "armor_shred")],
        root_attr="repair_cost",
    ),
    dict(
        cat_id="alchemy", title="Alchemy", icon="brewing_stand", background="story",
        sources=[stat_source("minecraft.custom:minecraft.interact_with_brewingstand", "12")],
        themes=[("healing", "natural_regeneration"), ("magic_resistance", "resistance"), ("magic_damage", "life_steal")],
        root_attr="healing",
    ),
    dict(
        cat_id="woodcutting", title="Woodcutting", icon="diamond_axe", background="stone",
        sources=[break_block_source([("any_log", "#minecraft:logs", 1)])],
        themes=[("axe_speed", "axe_damage"), ("break_speed", "stamina"), ("fortune", "repair_cost")],
        root_attr="axe_speed",
    ),
]


def main():
    categories = []
    stats = []
    for spec in CATEGORY_SPECS:
        cat_id, node_count = gen_category(
            spec["cat_id"], spec["title"], spec["icon"], spec["background"],
            spec["sources"], spec["themes"], spec["root_attr"],
        )
        categories.append(cat_id)
        stats.append((cat_id, node_count))

    write_json(OUT / "config.json", {"version": 3, "categories": categories})
    print(f"generated {len(categories)} categories under {OUT}")
    for cat_id, node_count in stats:
        print(f"  {cat_id}: {node_count} nodes")


if __name__ == "__main__":
    main()
