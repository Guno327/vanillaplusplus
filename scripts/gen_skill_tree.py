#!/usr/bin/env python3
"""Generate Pufferfish's Skills datapack content (category/experience/definitions/
skills/connections JSON) from a compact Python spec, writing into
pack/kubejs/data/puffish_skills/puffish_skills/ (KubeJS's raw-datapack folder).

Issue #116 ("Converge all skill trees into ONE unified tree") SUPERSEDES
issue #71's 23-category structure with a single category. What changed and
why, point by point against the issue's asks:

  1. ONE unified tree, not 23 tabs. There is now exactly one puffish_skills
     category (UNIFIED_CATEGORY_ID = "adventurer"). Every one of #71's 23
     categories (mining, swords, bows, ... woodcutting) survives as a
     34-node SUBTREE woven into this one tree (FORMER_SPECS below, verbatim
     copies of #71's CATEGORY_SPECS `sources`/`themes`/`root_attr` columns -
     the XP wiring and per-node buffs from #71 are reused unchanged, only
     the *shape* they're assembled into is new). A single shared
     `definitions.json` keyed by ATTR_META attribute id is used everywhere
     (an accidental but welcome side effect: the same "+0.7% Mining Speed"
     definition object is now reused by every former-category that touches
     mining_speed, instead of 23 duplicate copies).
  2. Unified XP -> one puffish_skills category has exactly one
     experience_per_level curve and one player-visible level. Every
     former-category's `sources` list (mine_block/kill_entity/fish_item/
     smelt_item/enchant_item/increase_stat - unchanged from #71) is
     concatenated into this ONE category's experience.json, so every action
     from running to killing a wither feeds the SAME level - satisfying
     "unified XP: all actions award skill XP weighted by difficulty" and
     "one unified player level" directly via puffish_skills' own native
     per-category level (net.puffish.skillsmod.api.SkillsAPI.getCategory(...)
     .getExperience().getLevel(player)), not a hand-rolled sum across
     categories the way pack/kubejs/server_scripts/leaderboard.js used to
     add up 23 category levels.
     Difficulty weighting (kept from #71, now load-bearing across the WHOLE
     tree instead of just within one category): passive movement stats
     (running/swimming/sailing/exploration) are worth a small fraction of a
     point per game unit (0.015-0.03 XP/cm); ore/log/crop breaking is a flat
     few points per block, tiered by real rarity (stone=1 up to
     diamond/emerald=14); weapon kills are `base_xp + dropped_xp` where
     `dropped_xp` is the vanilla XP orb amount for that specific entity -
     this is what makes "killing a strong enemy" worth more than a zombie
     with NO extra bookkeeping: a wither or ender dragon's vanilla XP drop
     is already an order of magnitude bigger than a zombie's, and
     kill_entity_source's `expression` (`f"{base_xp} + dropped_xp"`) passes
     that straight through.
     EXPERIENCE_EXPR's base constant is raised from #71's 70 to 900 (same
     "70 * pow(1.13, level)"-shaped curve otherwise, still spelled with `^`
     per issue #79 - see point 6 below) because #71's 70-per-level curve was
     tuned for ONE category filled by ONE family of actions; this tree now
     pours in XP from all 23 former sources' worth of actions simultaneously,
     so the per-level cost is scaled up to keep early levels from trivializing.
     This constant is a provisional first-order estimate (documented as such,
     same as skill_respec.js's "respec is free for now" call) - actual
     leveling pace needs a live playtest to tune further; see DESIGN.md's
     #116 section and this repo's Verification section (verify-in-game).
  3. Multiple mutually-exclusive starting locations -> a "class" structure.
     Every former-category is now grouped under exactly one of 4 CLASS_SPECS
     (Warrior/Ranger/Mystic/Artisan - see that table below for which former
     ids land in which class and why). The shared root node ("origin",
     "root": true - THE only root in the whole tree) connects via `normal`
     edges to all 4 class-root nodes (so all 4 are visible/AFFORDABLE from
     the start), but the 4 class-root nodes are ALSO pairwise linked via
     `exclusive` edges (a full clique, all 6 pairs). This is the exact
     mechanism this codebase used for its OLD per-category exclusive forks
     before #71 removed them (see git history's pre-#71 gen_skill_tree.py:
     "trunk -> normal edges to BOTH a0 and b0, PLUS one exclusive edge
     [a0, b0]" - net.puffish.skillsmod.server.data.CategoryData.getSkillState
     excludes a skill once >=1 of its declared exclusive neighbors is
     unlocked, `required_exclusions` defaulting to 1). A full clique among 4
     nodes (not just one pair) generalizes that mechanism cleanly: unlocking
     any one class root immediately excludes the other 3, because each
     carries an exclusive edge to every sibling. Once a class is chosen, its
     whole former-category subtree hangs off that class root via ordinary
     `normal` edges - nothing inside a chosen class is ever exclusive, matching
     #71's point 2 ("no exclusivity" WITHIN a tree) while reintroducing
     exclusivity only at the class-choice fork itself, per issue #116.
     check_skill_trees.py was updated to allow (and structurally validate)
     `exclusive` connections again instead of banning them outright - see
     that file's own #116 docstring section.
  4. Stronger, unique deep skills requiring significant investment -> one
     CAPSTONE node per class, attached one hop past a specific deep leaf of
     that class's LAST former-category's LAST theme-branch (7 edges from
     "origin": origin -> class root -> former root -> theme root -> depth1
     -> depth2 -> depth3 leaf -> capstone). Each capstone's definition
     combines TWO attribute rewards in one node (CAPSTONE_DEFS below) at
     roughly 5-7x a single regular node's magnitude - a real "worth grinding
     for" payoff only reachable after fully committing to one class and
     descending one of its longest chains, not something reachable early
     from any other path.

Layout is still fully generated, never hand-typed, and still collision-free
BY CONSTRUCTION (see layout_tree()'s docstring for the underlying per-tree
guarantee) - but now needs a second, OUTER layer of translation math since
every former-category's 34-node subtree and every class's single root node
all have to coexist in ONE shared (x, y) space instead of 23 independent
per-category spaces. See BAND_HEIGHT / _place_former() below for exactly how
that translation is constructed to guarantee zero cross-subtree collisions
without brute-force collision detection. scripts/ci/check_skill_trees.py
still asserts this holds (no two nodes in the whole tree share coordinates)
as a belt-and-suspenders check, not just trusting the algorithm - see that
file for the #116 update to its invariants (one root total, `exclusive`
allowed+validated, still-fully-reachable-via-`normal`-alone, plus a new
max-depth sanity check for point 4 above).
"""
import json
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "pack" / "kubejs" / "data" / "puffish_skills" / "puffish_skills"

UNIFIED_CATEGORY_ID = "adventurer"

X_SPACING = 32
Y_SPACING = 40
# Vertical gap reserved per former-category's private "band" in the shared
# coordinate space - see _place_former()'s docstring. Each former-category's
# own local layout_tree() call never produces a y-extent wider than roughly
# 12 slots * Y_SPACING (~480, see build_tree()'s BRANCH_SHAPE docstring: at
# most 4 leaves * 3 themes = 12 nodes share the deepest local depth), so
# BAND_HEIGHT=2000 leaves a wide, cheap-to-reason-about margin - collision-
# free by construction, not by testing.
BAND_HEIGHT = 2000

# Every former-category's tree: 1 local root -> 3 theme branches, each theme
# branch built by build_tree() with this per-depth branch-factor list
# (unchanged from issue #71 - see build_tree()'s docstring for the exact
# shape). Node count per theme = 1 + 2 + 4 + 4 = 11; former-category total =
# 1 (former root) + 3*11 = 34.
BRANCH_SHAPE = [2, 2, 1]

# Exponential per-level XP cost (issue #71 point 6, still true here - see
# this file's module docstring point 2 for why the base constant changed
# from 70 to 900 under issue #116's unification). Issue #79: written as
# "900 * (1.13 ^ level)", NOT "900 * pow(1.13, level)" - puffish_skills'
# expression engine (net.puffish.skillsmod.expression.DefaultParser) has no
# `pow` function; `^` is its own right-associative exponentiation binary
# operator (see scripts/ci/check_skill_expressions.py's vocabulary list for
# the full javap'd inventory this session verified once and reuses).
EXPERIENCE_EXPR = "900 * (1.13 ^ level)"


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent="\t") + "\n")


# ---------------------------------------------------------------------------
# Tree building + layout (generic - reused by every former-category's
# subtree, unchanged from issue #71).
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
    """Layered layout, collision-free BY CONSTRUCTION within this one tree:
    x = depth * X_SPACING (different depths never share a position), y =
    slot-index-within-that-depth * Y_SPACING, centered around 0 (nodes at
    the SAME depth get strictly increasing, evenly-spaced y). Visitation is
    pre-order DFS, so siblings within one branch land in contiguous y slots.

    Returns {node_id: (x, y)}. Outer callers translate these local
    coordinates into the shared whole-tree space - see _place_former()."""
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
# Experience source helpers - byte-for-byte unchanged from issue #71 (every
# `type` string and bare operation id here was confirmed against
# puffish_skills-0.18.1-1.21-neoforge.jar's ExperienceSource classes; see
# git history's pre-#116 gen_skill_tree.py for the full verification trail).
# Issue #116 doesn't touch any of this - it only changes how many of a
# category's `sources` lists get concatenated into ONE experience.json
# (see gen_unified_tree() below) instead of one list per category.
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
    (get_levels operation). Gated on `levels > 0` (a real comparison against
    a declared variable) since this engine's grammar has no confirmed
    boolean-literal constant."""
    return {
        "type": "puffish_skills:enchant_item",
        "data": {
            "variables": {"levels": {"operations": [{"type": "get_levels"}]}},
            "experience": [{"condition": "levels > 0", "expression": f"levels * {xp_per_level}"}],
        },
    }


def stat_source(stat_id, xp_per_unit):
    """stat_id: e.g. "minecraft.custom:minecraft.sprint_one_cm" - packs
    StatType(namespace.path):Stat(namespace.path) into one string
    (BuiltinJson#parseStat, confirmed against the real
    github.com/pufmat/skillsmod source)."""
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
# ATTR_META - the buff-variety allowlist (issue #71 point 4, unchanged by
# #116 - see scripts/ci/check_skill_trees.py's KNOWN_ATTRIBUTE_IDS, kept in
# sync with this table by hand). Every id here was verified against a real
# installed jar - see git history's pre-#116 gen_skill_tree.py for the full
# per-id verification trail (lang-file keys for puffish_attributes:*,
# javap for the rest).
# ---------------------------------------------------------------------------
ATTR_META = {
    # vanilla generic./player.
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
    # puffish_skills:player.*
    "fortune": ("puffish_skills:player.fortune", "addition", 0.02, "diamond", "item", "Fortune"),
    "melee_damage": ("puffish_skills:player.melee_damage", "multiply_total", 0.006, "strength", "effect", "Melee Damage"),
    "ranged_damage": ("puffish_skills:player.ranged_damage", "multiply_total", 0.006, "bow", "item", "Ranged Damage"),
    "stamina": ("puffish_skills:player.stamina", "multiply_total", 0.01, "saturation", "effect", "Stamina"),
    "jump": ("puffish_skills:player.jump", "multiply_total", 0.008, "jump_boost", "effect", "Jump"),
    # ars_nouveau perk attributes
    "spell_damage": ("ars_nouveau:ars_nouveau.perk.spell_damage", "multiply_base", 0.007, "ars_nouveau:wand", "item", "Spell Damage"),
    "max_mana": ("ars_nouveau:ars_nouveau.perk.max_mana", "addition", 3, "ars_nouveau:source_gem", "item", "Max Mana"),
    "mana_regen": ("ars_nouveau:ars_nouveau.perk.mana_regen", "multiply_base", 0.02, "ars_nouveau:amulet_of_mana_regen", "item", "Mana Regen"),
    # puffish_attributes
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
# FORMER_SPECS - issue #71's 23 categories, kept verbatim as subtrees woven
# into the one unified tree (issue #116). `sources`/`themes`/`root_attr`
# columns are byte-for-byte what CATEGORY_SPECS used to hold; the old
# `title`/`icon`/`background` columns are gone because there is no longer a
# per-former category.json - only ONE category.json for the whole tree (see
# gen_unified_tree()). Order matters for two things only: it's the order
# former subtrees are laid out into bands (see _place_former()) and the
# order their `sources` lists get concatenated into the one experience.json
# (cosmetic - order never affects which conditions can fire).
# ---------------------------------------------------------------------------
FORMER_SPECS = {
    "mining": dict(
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
    "swords": dict(
        sources=[kill_entity_source("weapon_check", "silentgear:sword", 2)],
        themes=[("sword_damage", "attack_speed"), ("attack_damage", "knockback"), ("melee_damage", "life_steal")],
        root_attr="sword_damage",
    ),
    "daggers": dict(
        sources=[kill_entity_source("weapon_check", "#vanillaplusplus:daggers", 2)],
        themes=[("attack_speed", "move_speed"), ("luck", "melee_damage"), ("stealth", "armor_shred")],
        root_attr="attack_speed",
    ),
    "greatswords": dict(
        sources=[kill_entity_source("weapon_check", "#vanillaplusplus:greatswords", 2)],
        themes=[("attack_damage", "knockback"), ("max_health", "attack_speed"), ("toughness_shred", "resistance")],
        root_attr="attack_damage",
    ),
    "longswords": dict(
        sources=[kill_entity_source("weapon_check", "#vanillaplusplus:longswords", 2)],
        themes=[("attack_damage", "attack_speed"), ("melee_damage", "move_speed"), ("melee_resistance", "ranged_resistance")],
        root_attr="attack_damage",
    ),
    "spears": dict(
        sources=[kill_entity_source("weapon_check", "#vanillaplusplus:spears", 2)],
        themes=[("entity_reach", "knockback"), ("attack_damage", "attack_speed"), ("melee_damage", "armor_shred")],
        root_attr="entity_reach",
    ),
    "tachi": dict(
        sources=[kill_entity_source("weapon_check", "#vanillaplusplus:tachis", 2)],
        themes=[("attack_speed", "move_speed"), ("attack_damage", "luck"), ("stealth", "life_steal")],
        root_attr="attack_speed",
    ),
    "bows": dict(
        sources=[kill_entity_source("weapon_check", "silentgear:bow", 2),
                 kill_entity_source("weapon_check2", "silentgear:crossbow", 2)],
        themes=[("bow_speed", "crossbow_speed"), ("ranged_damage", "repair_cost"), ("ranged_resistance", "fall_reduction")],
        root_attr="ranged_damage",
    ),
    "running": dict(
        sources=[stat_source("minecraft.custom:minecraft.sprint_one_cm", "0.02")],
        themes=[("sprint_speed", "step_height"), ("jump", "stamina"), ("fall_reduction", "move_speed")],
        root_attr="sprint_speed",
    ),
    "swimming": dict(
        sources=[stat_source("minecraft.custom:minecraft.swim_one_cm", "0.03")],
        themes=[("water_efficiency", "oxygen"), ("submerged_mining_speed", "trident_damage"), ("natural_regeneration", "healing")],
        root_attr="water_efficiency",
    ),
    "building": dict(
        sources=[],  # granted out-of-band from BlockEvents.placed, see skills.js
        themes=[("break_speed", "block_reach"), ("step_height", "repair_cost"), ("experience_gain", "max_health")],
        root_attr="break_speed",
    ),
    "magic": dict(
        sources=[kill_entity_source("weapon_check", "ars_nouveau:wand", 2)],
        themes=[("spell_damage", "magic_damage"), ("max_mana", "mana_regen"), ("magic_resistance", "healing")],
        root_attr="spell_damage",
    ),
    "farming": dict(
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
    "fishing": dict(
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
    "trading": dict(
        sources=[stat_source("minecraft.custom:minecraft.traded_with_villager", "25")],
        themes=[("luck", "max_health"), ("experience_gain", "healing"), ("stealth", "resistance")],
        root_attr="luck",
    ),
    "enchanting": dict(
        sources=[enchant_item_source(4)],
        themes=[("magic_damage", "magic_resistance"), ("repair_cost", "experience_gain"), ("armor_shred", "toughness_shred")],
        root_attr="magic_damage",
    ),
    "cooking": dict(
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
    "exploration": dict(
        sources=[stat_source("minecraft.custom:minecraft.walk_one_cm", "0.015")],
        themes=[("move_speed", "sprint_speed"), ("fall_reduction", "step_height"), ("luck", "experience_gain")],
        root_attr="move_speed",
    ),
    "sailing": dict(
        sources=[stat_source("minecraft.custom:minecraft.boat_one_cm", "0.02")],
        themes=[("mount_speed", "water_efficiency"), ("oxygen", "trident_damage"), ("fall_reduction", "resistance")],
        root_attr="mount_speed",
    ),
    "taming": dict(
        sources=[stat_source("minecraft.custom:minecraft.animals_bred", "30")],
        themes=[("mount_speed", "tamed_damage"), ("tamed_resistance", "healing"), ("luck", "max_health")],
        root_attr="tamed_damage",
    ),
    "smithing": dict(
        sources=[stat_source("minecraft.custom:minecraft.interact_with_smithing_table", "15")],
        themes=[("repair_cost", "experience_gain"), ("sword_damage", "axe_damage"), ("trident_damage", "armor_shred")],
        root_attr="repair_cost",
    ),
    "alchemy": dict(
        sources=[stat_source("minecraft.custom:minecraft.interact_with_brewingstand", "12")],
        themes=[("healing", "natural_regeneration"), ("magic_resistance", "resistance"), ("magic_damage", "life_steal")],
        root_attr="healing",
    ),
    "woodcutting": dict(
        sources=[break_block_source([("any_log", "#minecraft:logs", 1)])],
        themes=[("axe_speed", "axe_damage"), ("break_speed", "stamina"), ("fortune", "repair_cost")],
        root_attr="axe_speed",
    ),
}

# ---------------------------------------------------------------------------
# CLASS_SPECS - issue #116 point 3: mutually-exclusive starting locations.
# Every one of FORMER_SPECS' 23 ids is assigned to exactly ONE class below
# (grouping chosen by real thematic fit - melee weapon families under
# Warrior, ranged/mobility/nature under Ranger, arcane/brewing/commerce
# under Mystic, gathering/industry/sustenance under Artisan). `root_attr` is
# the attribute on the class's own single root node (a small taste of that
# class's identity, available the instant it's chosen).
# ---------------------------------------------------------------------------
CLASS_SPECS = [
    dict(
        class_id="warrior", title="Warrior", icon="diamond_sword", background="nether",
        root_attr="attack_damage",
        formers=["swords", "daggers", "greatswords", "longswords", "spears", "tachi"],
    ),
    dict(
        class_id="ranger", title="Ranger", icon="bow", background="adventure",
        root_attr="move_speed",
        formers=["bows", "running", "swimming", "exploration", "sailing", "fishing", "taming"],
    ),
    dict(
        class_id="mystic", title="Mystic", icon="ars_nouveau:wand", background="story",
        root_attr="magic_damage",
        formers=["magic", "enchanting", "alchemy", "trading"],
    ),
    dict(
        class_id="artisan", title="Artisan", icon="diamond_pickaxe", background="stone",
        root_attr="mining_speed",
        formers=["mining", "building", "woodcutting", "farming", "smithing", "cooking"],
    ),
]

assert sorted(f for c in CLASS_SPECS for f in c["formers"]) == sorted(FORMER_SPECS), (
    "every FORMER_SPECS id must be assigned to exactly one CLASS_SPECS entry"
)

# Issue #116 point 4: one capstone per class, attached past a deep leaf of
# that class's LAST former's LAST theme-branch. Each combines TWO attribute
# rewards at roughly 5-7x a regular node's magnitude - deliberately far
# stronger than anything reachable without descending a full 7-edge chain
# from "origin" (see _place_former()/main() for exactly which leaf).
CAPSTONE_DEFS = {
    "warrior": {
        "title": "Duelist's Resolve (+5% Attack Damage, +5% Sword Damage)",
        "icon": {"type": "item", "data": {"item": "netherite_sword"}},
        "rewards": [
            {"type": "puffish_skills:attribute", "data": {"attribute": "generic.attack_damage", "value": 0.05, "operation": "multiply_base"}},
            {"type": "puffish_skills:attribute", "data": {"attribute": "puffish_attributes:sword_damage", "value": 0.05, "operation": "multiply_base"}},
        ],
    },
    "ranger": {
        "title": "Wind's Favor (+5% Movement Speed, +8% Fall Reduction)",
        "icon": {"type": "item", "data": {"item": "elytra"}},
        "rewards": [
            {"type": "puffish_skills:attribute", "data": {"attribute": "generic.movement_speed", "value": 0.05, "operation": "multiply_base"}},
            {"type": "puffish_skills:attribute", "data": {"attribute": "puffish_attributes:fall_reduction", "value": 0.08, "operation": "addition"}},
        ],
    },
    "mystic": {
        "title": "Archmage's Insight (+5% Magic Damage, +5% Magic Resistance)",
        "icon": {"type": "item", "data": {"item": "ars_nouveau:source_gem"}},
        "rewards": [
            {"type": "puffish_skills:attribute", "data": {"attribute": "puffish_attributes:magic_damage", "value": 0.05, "operation": "multiply_base"}},
            {"type": "puffish_skills:attribute", "data": {"attribute": "puffish_attributes:magic_resistance", "value": 0.05, "operation": "multiply_base"}},
        ],
    },
    "artisan": {
        "title": "Master Craftsman (+5% Mining Speed, +0.75 Fortune)",
        "icon": {"type": "item", "data": {"item": "netherite_pickaxe"}},
        "rewards": [
            {"type": "puffish_skills:attribute", "data": {"attribute": "puffish_attributes:mining_speed", "value": 0.05, "operation": "multiply_base"}},
            {"type": "puffish_skills:attribute", "data": {"attribute": "puffish_skills:player.fortune", "value": 0.75, "operation": "addition"}},
        ],
    },
}

ORIGIN_ROOT_ATTR = "max_health"  # a small, universal taste of vitality - free the instant the datapack loads


def _place_former(prefix, spec, band_index, class_x, skills_out, definitions_out, normal_pairs_out):
    """Builds one former-category's 34-node subtree (former root + 3 theme
    branches, exactly issue #71's per-category shape) and writes its nodes
    directly into the shared skills_out/definitions_out/normal_pairs_out,
    with (x, y) translated into this former's own private BAND_HEIGHT-tall
    horizontal band so it can never collide with any other former's nodes -
    see this file's module docstring for the collision-free-by-construction
    argument. Returns (former_root_id, deepest_leaf_id) - the latter is
    where a class's capstone (if any) gets attached.
    """
    themes = spec["themes"]
    assert len(themes) == 3, f"{prefix}: expected exactly 3 themes, got {len(themes)}"

    used_attrs = [spec["root_attr"]] + [attr for pair in themes for attr in pair]
    for attr_key in used_attrs:
        if attr_key not in definitions_out:
            definitions_out[attr_key] = attr_definition(attr_key)

    former_root = f"{prefix}root"
    children_map = {}
    local_skills = {former_root: {"definition": spec["root_attr"]}}

    theme_roots = []
    deepest_leaf = None  # first depth-3 leaf seen, deterministic (theme 0 first)
    for theme_idx, (attr_a, attr_b) in enumerate(themes):
        tprefix = f"{prefix}t{theme_idx}_"
        troot, order, tchildren, depth_map = build_tree(tprefix, BRANCH_SHAPE)
        theme_roots.append(troot)
        children_map.update(tchildren)
        for node in order:
            attr_key = attr_a if depth_map[node] % 2 == 0 else attr_b
            local_skills[node] = {"definition": attr_key}
            if deepest_leaf is None and depth_map[node] == len(BRANCH_SHAPE):
                deepest_leaf = node
        for parent, kids in tchildren.items():
            for kid in kids:
                normal_pairs_out.append([parent, kid])

    children_map[former_root] = theme_roots
    for troot in theme_roots:
        normal_pairs_out.append([former_root, troot])

    positions = layout_tree(former_root, children_map)
    band_y = band_index * BAND_HEIGHT
    for node_id, (lx, ly) in positions.items():
        skills_out[node_id] = local_skills[node_id]
        skills_out[node_id]["x"] = class_x + lx
        skills_out[node_id]["y"] = band_y + ly

    deepest_leaf_x, deepest_leaf_y = skills_out[deepest_leaf]["x"], skills_out[deepest_leaf]["y"]
    return former_root, (deepest_leaf, deepest_leaf_x, deepest_leaf_y)


def gen_unified_tree():
    skills = {}
    definitions = {}
    normal_pairs = []
    exclusive_pairs = []
    all_sources = []

    origin_id = "origin"
    definitions[ORIGIN_ROOT_ATTR] = attr_definition(ORIGIN_ROOT_ATTR)
    skills[origin_id] = {"definition": ORIGIN_ROOT_ATTR, "root": True, "x": 0, "y": 0}

    class_root_ids = []
    band_index = 0
    for class_spec in CLASS_SPECS:
        class_id = class_spec["class_id"]
        class_root = f"class_{class_id}_root"
        class_root_ids.append(class_root)
        # Class root sits at depth 1 (x=X_SPACING), y = its first former's
        # band baseline - a distinct (x, y) from every other node by
        # construction (no other class root, and no former subtree, ever
        # reuses x=X_SPACING once band_index differs per class).
        class_x = X_SPACING
        class_y = band_index * BAND_HEIGHT
        if class_spec["root_attr"] not in definitions:
            definitions[class_spec["root_attr"]] = attr_definition(class_spec["root_attr"])
        skills[class_root] = {"definition": class_spec["root_attr"], "x": class_x, "y": class_y}
        normal_pairs.append([origin_id, class_root])

        last_deep_leaf = None
        for former_id in class_spec["formers"]:
            spec = FORMER_SPECS[former_id]
            all_sources.extend(spec["sources"])
            former_root, deep_leaf_info = _place_former(
                f"{class_id}_{former_id}_", spec, band_index,
                class_x=2 * X_SPACING,  # former subtrees start one depth further out than the class root
                skills_out=skills, definitions_out=definitions, normal_pairs_out=normal_pairs,
            )
            normal_pairs.append([class_root, former_root])
            last_deep_leaf = deep_leaf_info
            band_index += 1

        # Issue #116 point 4: capstone attached one hop past this class's
        # LAST former's deepest leaf.
        leaf_id, leaf_x, leaf_y = last_deep_leaf
        capstone_id = f"class_{class_id}_capstone"
        definitions[f"capstone_{class_id}"] = CAPSTONE_DEFS[class_id]
        skills[capstone_id] = {"definition": f"capstone_{class_id}", "x": leaf_x + X_SPACING, "y": leaf_y}
        normal_pairs.append([leaf_id, capstone_id])

    # Issue #116 point 3: full exclusive clique among the class-root nodes -
    # unlocking any one excludes every other, per
    # net.puffish.skillsmod.server.data.CategoryData.getSkillState's
    # `required_exclusions` default of 1 (see module docstring point 3).
    for a, b in combinations(class_root_ids, 2):
        exclusive_pairs.append([a, b])

    cat_dir = OUT / "categories" / UNIFIED_CATEGORY_ID
    write_json(cat_dir / "category.json", {
        "unlocked_by_default": True,
        "title": "Adventurer",
        "icon": {"type": "item", "data": {"item": "nether_star"}},
        "background": "textures/gui/advancements/backgrounds/end.png",
    })
    write_json(cat_dir / "experience.json", {
        "experience_per_level": {"type": "expression", "data": {"expression": EXPERIENCE_EXPR}},
        "sources": all_sources,
    })
    write_json(cat_dir / "definitions.json", definitions)
    write_json(cat_dir / "skills.json", skills)
    write_json(cat_dir / "connections.json", {
        "normal": {"bidirectional": normal_pairs},
        "exclusive": {"bidirectional": exclusive_pairs},
    })

    return len(skills), len(definitions), len(exclusive_pairs)


def main():
    write_json(OUT / "config.json", {"version": 3, "categories": [UNIFIED_CATEGORY_ID]})
    node_count, def_count, exclusive_count = gen_unified_tree()
    print(f"generated 1 unified category ({UNIFIED_CATEGORY_ID}) under {OUT}")
    print(f"  {UNIFIED_CATEGORY_ID}: {node_count} nodes, {def_count} definitions, {exclusive_count} exclusive pair(s)")


if __name__ == "__main__":
    main()
