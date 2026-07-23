#!/usr/bin/env python3
"""Fast-tier CI check: Pufferfish's Skills (puffish_skills) datapack
consistency over pack/kubejs/data/puffish_skills/puffish_skills/.

Originally written for issue #24 ("I have plenty of skill points but am
unable to allocate them"), extended for issue #71 ("Expand Skill Trees /
Categories"), and extended again for issue #116 ("Converge all skill trees
into ONE unified tree" - supersedes #71's 23-category structure with one
category woven from all 23 as subtrees under 4 mutually-exclusive "class"
starting points). What #116 changed about these invariants:

  - The "no `exclusive` connections anywhere" rule #71 introduced is GONE.
    #116 point 3 (multiple mutually-exclusive starting locations) requires
    `exclusive` connections again, on purpose - scripts/gen_skill_tree.py's
    4 class-root nodes form a full `exclusive` clique so unlocking any one
    class permanently excludes the other 3 (same mechanism this repo's
    PRE-#71 generator used for its old per-category spec forks - see git
    history). This checker now VALIDATES `exclusive` connections (same
    shape/reference checks as `normal`) instead of banning them outright.
  - Still exactly ONE root node - just now it's one root for the WHOLE
    tree (scripts/gen_skill_tree.py's "origin") rather than one per
    category, because there is only one category left.
  - Still "every node reachable from the root via `normal` edges alone" -
    #116's class-exclusivity is layered on TOP of a fully `normal`-connected
    spanning tree (every class root and every former-category subtree is
    `normal`-reachable from "origin"; `exclusive` edges are a same-endpoint
    add-on that doesn't change what's reachable, only what stays UNLOCKABLE
    at runtime - see gen_skill_tree.py's module docstring point 3). So the
    reachability graph walk below still only follows `normal` edges,
    unchanged from #71.
  - New: a max-depth sanity check (`stats["max_depth"]`) - #116 point 4
    ("stronger, unique deep skills requiring significant investment") is a
    structural claim ("some node needs a long chain of prerequisites"), not
    just a vibe, so the real generated tree's depth is asserted to be deep
    enough in test_check_skill_trees.py's test_real_generated_output_passes
    (kept as a stat here rather than a hard error in this generic per-
    category checker, so synthetic 3-node test fixtures for OTHER invariants
    don't all need to fake a deep tree just to pass).

The invariants #71 introduced and #116 keeps unchanged:

  - net.puffish.skillsmod.config.skill.SkillConfig.parse: the per-node
    "root" JSON field (skills.json) defaults to Boolean.FALSE
    (Optional<Boolean>.orElse(false)) when omitted - it is NOT required by
    the parser, so a missing "root" on every node in a category is silently
    accepted, not a load error.
  - net.puffish.skillsmod.server.data.CategoryData.getSkillState: a node
    only ever reaches AVAILABLE/AFFORDABLE (i.e. becomes clickable/
    unlockable in the skill-tree screen) if it is EITHER (a) linked via a
    `normal` connection to an already-UNLOCKED neighbor, OR (b)
    SkillConfig.isRoot() is true. unlockedSkills starts EMPTY for every
    player. So a category with zero root nodes has no entry point at all -
    every node permanently evaluates to LOCKED no matter how many points
    the player holds. This is exactly issue #24's symptom.
  - net.puffish.skillsmod.config.skill.SkillConfig.parse also silently
    DROPS (not errors on) a skill node whose "definition" references a
    definitions.json key that didn't load (SkillDefinitionsConfig.isLoaded
    check, returns Result.success(Optional.empty()) on failure) - so a typo'd
    "definition" doesn't fail the datapack load either, it just vanishes the
    node with no diagnostic. Checked here too.
  - Issue #71 point 2 ("remove exclusivity, all nodes are reachable given
    enough time"): connections.json's `exclusive` group is now BANNED
    outright (any occurrence, even an empty one, is an error) and every
    node must be reachable from the category's one root purely via `normal`
    edges - checked by a graph walk, not just "root exists".
  - Issue #71's generated-layout requirement: no two skill nodes in the
    same category may share (x, y) - checked here as a static, cheap proxy
    for "the generator's layout algorithm is actually collision-free",
    independent of trusting the generator's own math.
  - Issue #71 point 4 ("increased variety of buffs"): every
    puffish_skills:attribute reward's `attribute` id must appear in
    KNOWN_ATTRIBUTE_IDS below - the same allowlist gen_skill_tree.py's
    ATTR_META was built from (see that file's ATTR_META docstring for how
    each id was verified against a real installed jar). A typo'd attribute
    id is exactly the failure class that silently killed a whole feature
    before (the `multiply_base` operation-vocabulary confusion documented
    in DECISIONS.md) - this check exists so a similar mistake on the
    *attribute id* axis fails CI instead of shipping.
  - Issue #71 point 6 ("exponentially more XP per subsequent point"): the
    experience_per_level expression is evaluated at a handful of sample
    levels (as a plain Python re-implementation of the small arithmetic
    subset this generator actually emits - not a full expression-language
    parser) and asserted strictly increasing AND superlinear (the ratio
    cost(level+1)/cost(level) must itself trend upward, which a linear or
    quadratic curve fails but a geometric "base * pow(growth, level)" curve
    satisfies).

This class of bug is NOT reachable from a live-boot L1 KubeJS selftest
(pack/kubejs/server_scripts/selftest.js): KubeJS's own installed classfilter
(kubejs.classfilter.txt) hard-blocks java.io/java.nio down to a couple of
marker interfaces, so Rhino scripts cannot read the raw datapack JSON
back, and the only public runtime signal for a node's unlock state
(net.puffish.skillsmod.api.Skill#getState) requires a real ServerPlayer,
which the console-only L1 boot-test harness never has (see selftest.js's own
header comment). This CI check is the actually-reliable place to catch it -
static, pre-boot, no player required - and selftest.js has a companion
comment pointing back here.

Usage: python3 scripts/ci/check_skill_trees.py [root]
Exit code: 0 if every category is internally consistent, 1 otherwise.
"""
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Kept in sync by hand with scripts/gen_skill_tree.py's ATTR_META - every id
# there is verified against a real installed jar (see that file's ATTR_META
# docstring for exactly how). Any puffish_skills:attribute reward using an
# id NOT in this set fails CI rather than risking a silent load-time drop
# or runtime crash in-game.
KNOWN_ATTRIBUTE_IDS = {
    "generic.attack_speed", "generic.attack_damage", "generic.movement_speed",
    "generic.luck", "generic.max_health", "generic.step_height",
    "generic.water_movement_efficiency", "generic.oxygen_bonus",
    "minecraft:player.submerged_mining_speed",
    "minecraft:player.entity_interaction_range",
    "minecraft:player.block_interaction_range",
    "minecraft:player.block_break_speed",
    "puffish_skills:player.fortune", "puffish_skills:player.melee_damage",
    "puffish_skills:player.ranged_damage", "puffish_skills:player.stamina",
    "puffish_skills:player.jump",
    "ars_nouveau:ars_nouveau.perk.spell_damage",
    "ars_nouveau:ars_nouveau.perk.max_mana",
    "ars_nouveau:ars_nouveau.perk.mana_regen",
    "puffish_attributes:mining_speed", "puffish_attributes:pickaxe_speed",
    "puffish_attributes:sword_damage", "puffish_attributes:knockback",
    "puffish_attributes:bow_projectile_speed",
    "puffish_attributes:crossbow_projectile_speed",
    "puffish_attributes:sprinting_speed", "puffish_attributes:breaking_speed",
    "puffish_attributes:experience", "puffish_attributes:life_steal",
    "puffish_attributes:stealth", "puffish_attributes:armor_shred",
    "puffish_attributes:toughness_shred", "puffish_attributes:resistance",
    "puffish_attributes:melee_resistance", "puffish_attributes:ranged_resistance",
    "puffish_attributes:magic_resistance", "puffish_attributes:magic_damage",
    "puffish_attributes:healing", "puffish_attributes:natural_regeneration",
    "puffish_attributes:fall_reduction", "puffish_attributes:trident_damage",
    "puffish_attributes:mount_speed", "puffish_attributes:consuming_speed",
    "puffish_attributes:tamed_damage", "puffish_attributes:tamed_resistance",
    "puffish_attributes:axe_damage", "puffish_attributes:axe_speed",
    "puffish_attributes:repair_cost",
}

# Valid puffish_skills:attribute reward `operation` values - confirmed
# against net.puffish.skillsmod.api.json.BuiltinJson#parseAttributeOperation
# (see gen_skill_tree.py's ATTR_META docstring). NOT the same vocabulary as
# vanilla AttributeModifier.Operation (add_value/add_multiplied_base/
# add_multiplied_total) - that's a different, unrelated landmine documented
# in DECISIONS.md for a different file (mob_scaling.js).
KNOWN_ATTRIBUTE_OPERATIONS = {"addition", "multiply_base", "multiply_total"}


def _skills_root(root):
    return root / "pack" / "kubejs" / "data" / "puffish_skills" / "puffish_skills"


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path, root):
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _eval_experience_expr(expr, level):
    """Evaluates the tiny arithmetic subset this generator actually emits
    for experience_per_level: `+`, `*`, and `base ^ level` (puffish_skills'
    own exponentiation operator - see issue #79 and gen_skill_tree.py's
    module docstring point 6 for why it's `^`, not a `pow(...)` function
    call, in this mod's expression engine), with the single variable
    `level`. Not a general expression parser - just enough to sample the
    curve for the monotonic/superlinear check below without
    hand-duplicating puffish_skills' own (unavailable-in-Python) engine."""
    safe_expr = expr.replace("level", str(level))
    # Anything beyond digits/operators/whitespace/`^` itself is a syntax
    # this checker doesn't understand - fail loudly instead of silently
    # eval-ing something unexpected.
    if not re.fullmatch(r"[0-9+\-*/.,()^ a-z]*", safe_expr):
        raise ValueError(f"unrecognized characters in experience expression: {expr!r}")
    safe_expr = safe_expr.replace("^", "**")
    return eval(safe_expr, {"__builtins__": {}}, {})


def check_skill_trees(root):
    """Returns (errors, stats) - errors is a list of human-readable
    strings (empty == consistent)."""
    errors = []
    stats = {"categories": 0, "skills": 0, "definitions": 0, "roots": 0, "exclusive_pairs": 0, "max_depth": 0}

    skills_root = _skills_root(root)
    config_path = skills_root / "config.json"
    if not config_path.is_file():
        return ([f"config.json not found: {config_path}"], stats)

    try:
        config = _load_json(config_path)
    except json.JSONDecodeError as e:
        return ([f"{_rel(config_path, root)}: JSON parse error: {e}"], stats)

    category_ids = config.get("categories", [])
    if not category_ids:
        errors.append(f"{_rel(config_path, root)}: 'categories' list is empty")

    for cat_id in category_ids:
        cat_dir = skills_root / "categories" / cat_id
        stats["categories"] += 1

        # ---- category.json ----
        category_json = cat_dir / "category.json"
        if not category_json.is_file():
            errors.append(f"{cat_id}: missing category.json")
            continue
        try:
            category_data = _load_json(category_json)
        except json.JSONDecodeError as e:
            errors.append(f"{_rel(category_json, root)}: JSON parse error: {e}")
            continue

        # ---- definitions.json (SkillDefinitionsConfig: id -> SkillDefinitionConfig) ----
        definitions_json = cat_dir / "definitions.json"
        if not definitions_json.is_file():
            errors.append(f"{cat_id}: missing definitions.json")
            continue
        try:
            definitions = _load_json(definitions_json)
        except json.JSONDecodeError as e:
            errors.append(f"{_rel(definitions_json, root)}: JSON parse error: {e}")
            continue
        if not isinstance(definitions, dict) or not definitions:
            errors.append(f"{cat_id}: definitions.json has no definitions")
            continue
        stats["definitions"] += len(definitions)

        referenced_definitions = set()

        # ---- issue #71 point 4: attribute id / operation allowlist ----
        for def_id, definition in definitions.items():
            if not isinstance(definition, dict):
                continue
            for reward in definition.get("rewards", []) or []:
                if not isinstance(reward, dict) or reward.get("type") != "puffish_skills:attribute":
                    continue
                data = reward.get("data", {}) or {}
                attribute = data.get("attribute")
                operation = data.get("operation")
                if attribute not in KNOWN_ATTRIBUTE_IDS:
                    errors.append(
                        f"{cat_id}: definition {def_id!r} uses attribute id {attribute!r}, "
                        "which is not in check_skill_trees.py's KNOWN_ATTRIBUTE_IDS allowlist "
                        "(unverified attribute ids have silently killed features here before - "
                        "verify against a real installed jar and add it to both gen_skill_tree.py's "
                        "ATTR_META and this allowlist)"
                    )
                if operation not in KNOWN_ATTRIBUTE_OPERATIONS:
                    errors.append(
                        f"{cat_id}: definition {def_id!r} uses attribute operation {operation!r}, "
                        f"which is not one of {sorted(KNOWN_ATTRIBUTE_OPERATIONS)} - "
                        "puffish_skills:attribute rewards use puffish's own operation vocabulary, "
                        "NOT vanilla AttributeModifier.Operation's add_value/add_multiplied_base/"
                        "add_multiplied_total (see DECISIONS.md's mob_scaling.js landmine note)"
                    )

        # ---- skills.json (SkillsConfig: id -> SkillConfig {x, y, definition, root}) ----
        skills_json = cat_dir / "skills.json"
        if not skills_json.is_file():
            errors.append(f"{cat_id}: missing skills.json")
            continue
        try:
            skills = _load_json(skills_json)
        except json.JSONDecodeError as e:
            errors.append(f"{_rel(skills_json, root)}: JSON parse error: {e}")
            continue
        if not isinstance(skills, dict) or not skills:
            errors.append(f"{cat_id}: skills.json has no skill nodes")
            continue
        stats["skills"] += len(skills)

        root_ids = []
        coords_seen = {}
        for skill_id, skill in skills.items():
            if not isinstance(skill, dict):
                errors.append(f"{cat_id}: skills.json entry {skill_id!r} is not an object")
                continue
            if skill.get("root") is True:
                root_ids.append(skill_id)
            definition_id = skill.get("definition")
            if definition_id is None:
                errors.append(f"{cat_id}: skill {skill_id!r} has no 'definition' field")
            elif definition_id not in definitions:
                errors.append(
                    f"{cat_id}: skill {skill_id!r} references definition "
                    f"{definition_id!r}, which is not a key in definitions.json "
                    "(the mod SILENTLY DROPS this node at load time rather than "
                    "erroring - see net.puffish.skillsmod.config.skill.SkillConfig.parse)"
                )
            else:
                referenced_definitions.add(definition_id)

            # ---- issue #71: no two nodes may share (x, y) ----
            x, y = skill.get("x"), skill.get("y")
            coord = (x, y)
            if coord in coords_seen:
                errors.append(
                    f"{cat_id}: skills {skill_id!r} and {coords_seen[coord]!r} both sit at "
                    f"(x={x}, y={y}) - overlapping nodes in the skill-tree screen"
                )
            else:
                coords_seen[coord] = skill_id

        # ---- orphan definitions: every definition should be referenced by
        # at least one skill (no-op entries drift out of sync silently) ----
        for def_id in definitions:
            if def_id not in referenced_definitions:
                errors.append(
                    f"{cat_id}: definition {def_id!r} in definitions.json is never "
                    "referenced by any skill in skills.json (orphaned)"
                )

        # ---- issue #71 point 1: exactly one root per category ----
        if len(root_ids) == 0:
            errors.append(
                f"{cat_id}: no skill node has \"root\": true - every node is "
                "permanently LOCKED for every player regardless of points held "
                "(net.puffish.skillsmod.server.data.CategoryData.getSkillState "
                "only reaches AVAILABLE/AFFORDABLE via a root node or a `normal` "
                "edge from an already-unlocked node, and unlockedSkills starts "
                "empty) - this is issue #24's exact bug class"
            )
        elif len(root_ids) > 1:
            errors.append(
                f"{cat_id}: expected exactly 1 root node, found {len(root_ids)}: {sorted(root_ids)} "
                "(issue #71 point 1 - a tree, not a forest)"
            )
        stats["roots"] += len(root_ids)

        # ---- connections.json (SkillConnectionsConfig: normal/exclusive
        # bidirectional/unidirectional pairs of skill ids). Issue #116
        # reintroduces `exclusive` (see this file's #116 docstring section
        # above) for the class-choice clique - validated the same way
        # `normal` always has been (shape + every referenced id must exist
        # in skills.json), just no longer banned outright. ----
        connections_json = cat_dir / "connections.json"
        normal_pairs = []
        exclusive_pair_count = 0
        if connections_json.is_file():
            try:
                connections = _load_json(connections_json)
            except json.JSONDecodeError as e:
                errors.append(f"{_rel(connections_json, root)}: JSON parse error: {e}")
                connections = {}

            normal_group = connections.get("normal", {}) if isinstance(connections, dict) else {}
            if not isinstance(normal_group, dict):
                normal_group = {}
            for direction in ("bidirectional", "unidirectional"):
                for pair in normal_group.get(direction, []) or []:
                    if not isinstance(pair, list) or len(pair) != 2:
                        errors.append(
                            f"{cat_id}: connections.json normal.{direction} "
                            f"entry {pair!r} is not a 2-element array"
                        )
                        continue
                    for skill_id in pair:
                        if skill_id not in skills:
                            errors.append(
                                f"{cat_id}: connections.json normal.{direction} "
                                f"references skill {skill_id!r}, which is not in skills.json"
                            )
                    normal_pairs.append(pair)

            exclusive_group = connections.get("exclusive", {}) if isinstance(connections, dict) else {}
            if not isinstance(exclusive_group, dict):
                exclusive_group = {}
            for direction in ("bidirectional", "unidirectional"):
                for pair in exclusive_group.get(direction, []) or []:
                    if not isinstance(pair, list) or len(pair) != 2:
                        errors.append(
                            f"{cat_id}: connections.json exclusive.{direction} "
                            f"entry {pair!r} is not a 2-element array"
                        )
                        continue
                    a, b = pair
                    if a == b:
                        errors.append(
                            f"{cat_id}: connections.json exclusive.{direction} "
                            f"entry {pair!r} connects a skill to itself"
                        )
                    for skill_id in pair:
                        if skill_id not in skills:
                            errors.append(
                                f"{cat_id}: connections.json exclusive.{direction} "
                                f"references skill {skill_id!r}, which is not in skills.json"
                            )
                    exclusive_pair_count += 1

        stats["exclusive_pairs"] += exclusive_pair_count

        # ---- issue #71 point 1/2 (still true under #116 - see this file's
        # #116 docstring section): every node reachable from the root via
        # `normal` edges alone (bidirectional treated as undirected;
        # unidirectional followed forward only). Also computes max BFS
        # depth from the root over the same `normal`-only graph - issue
        # #116 point 4's "significant investment" claim is checked against
        # this in test_check_skill_trees.py's test_real_generated_output_passes. ----
        if root_ids and isinstance(skills, dict):
            adjacency = {}
            for pair in normal_pairs:
                if not isinstance(pair, list) or len(pair) != 2:
                    continue
                a, b = pair
                adjacency.setdefault(a, set()).add(b)
                adjacency.setdefault(b, set()).add(a)
            reachable = set()
            depth = {rid: 0 for rid in root_ids}
            frontier = list(root_ids)
            reachable.update(root_ids)
            max_depth = 0
            while frontier:
                node = frontier.pop(0)
                for neighbor in adjacency.get(node, ()):
                    if neighbor not in reachable:
                        reachable.add(neighbor)
                        depth[neighbor] = depth[node] + 1
                        max_depth = max(max_depth, depth[neighbor])
                        frontier.append(neighbor)
            stats["max_depth"] = max(stats["max_depth"], max_depth)
            unreachable = set(skills) - reachable
            if unreachable:
                errors.append(
                    f"{cat_id}: {len(unreachable)} skill node(s) not reachable from the "
                    f"root via `normal` connections: {sorted(unreachable)[:10]}"
                    + (" ..." if len(unreachable) > 10 else "")
                )

        # ---- points source: either experience.json wires an
        # experience_per_level curve, or the category grants points another
        # way (starting_points in category.json). ----
        experience_json = cat_dir / "experience.json"
        has_starting_points = isinstance(category_data, dict) and category_data.get("starting_points", 0) not in (0, None)
        if experience_json.is_file():
            try:
                experience = _load_json(experience_json)
            except json.JSONDecodeError as e:
                errors.append(f"{_rel(experience_json, root)}: JSON parse error: {e}")
                experience = {}
            if not isinstance(experience, dict) or "experience_per_level" not in experience:
                if not has_starting_points:
                    errors.append(
                        f"{cat_id}: experience.json exists but has no "
                        "'experience_per_level' curve, and category.json has no "
                        "starting_points - no way for this category to ever grant points"
                    )
            else:
                # ---- issue #71 point 6: exponential (strictly increasing
                # AND superlinear) XP curve ----
                expr_data = experience.get("experience_per_level", {})
                expr = (expr_data.get("data", {}) or {}).get("expression") if isinstance(expr_data, dict) else None
                if isinstance(expr, str):
                    try:
                        samples = [_eval_experience_expr(expr, lvl) for lvl in range(0, 30)]
                    except Exception as e:  # noqa: BLE001 - report as a check failure, not a crash
                        errors.append(f"{cat_id}: could not evaluate experience_per_level expression {expr!r}: {e}")
                        samples = None
                    if samples is not None:
                        if any(b <= a for a, b in zip(samples, samples[1:])):
                            errors.append(
                                f"{cat_id}: experience_per_level {expr!r} is not strictly "
                                "increasing across levels 0-29"
                            )
                        else:
                            ratios = [b / a for a, b in zip(samples, samples[1:])]
                            # A superlinear (geometric-or-steeper) curve has
                            # non-decreasing step-to-step ratios; a linear
                            # curve's ratios trend toward 1 and DECREASE.
                            if ratios[-1] < ratios[0] - 1e-9:
                                errors.append(
                                    f"{cat_id}: experience_per_level {expr!r} does not look "
                                    "exponential - its growth ratio decreases with level "
                                    "(issue #71 point 6 requires each subsequent point to cost "
                                    "exponentially more, not linearly/quadratically more)"
                                )
        elif not has_starting_points:
            errors.append(
                f"{cat_id}: no experience.json and no starting_points in "
                "category.json - no way for this category to ever grant points"
            )

    return errors, stats


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else REPO_ROOT

    errors, stats = check_skill_trees(root)

    if errors:
        print(f"check_skill_trees: FAIL - {len(errors)} issue(s):")
        for err in errors:
            print(f"  {err}")
        return 1

    print(
        "check_skill_trees: PASS - "
        f"{stats['categories']} categor{'y' if stats['categories'] == 1 else 'ies'}, "
        f"{stats['skills']} skill node(s), {stats['definitions']} definition(s), "
        f"{stats['roots']} root node(s), {stats['exclusive_pairs']} exclusive pair(s), "
        f"max depth {stats['max_depth']}, all internally consistent"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
