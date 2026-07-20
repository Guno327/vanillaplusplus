#!/usr/bin/env python3
"""Fast-tier CI check: Pufferfish's Skills (puffish_skills) datapack
consistency over pack/kubejs/data/puffish_skills/puffish_skills/.

Written for issue #24 ("I have plenty of skill points but am unable to
allocate them") - root-caused by GROUND-TRUTHING the installed jar (javap
against puffish_skills-0.18.1-1.21-neoforge.jar's config/skill parser
classes, not training-data memory):

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
    the player holds. This is exactly issue #24's symptom, and it was true
    of all 12 categories (scripts/gen_skill_tree.py's gen_category() built
    every skills.json entry without ever setting "root").
  - net.puffish.skillsmod.config.skill.SkillConfig.parse also silently
    DROPS (not errors on) a skill node whose "definition" references a
    definitions.json key that didn't load (SkillDefinitionsConfig.isLoaded
    check, returns Result.success(Optional.empty()) on failure) - so a typo'd
    "definition" doesn't fail the datapack load either, it just vanishes the
    node with no diagnostic. Checked here too.

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
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _skills_root(root):
    return root / "pack" / "kubejs" / "data" / "puffish_skills" / "puffish_skills"


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path, root):
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def check_skill_trees(root):
    """Returns (errors, stats) - errors is a list of human-readable
    strings (empty == consistent)."""
    errors = []
    stats = {"categories": 0, "skills": 0, "definitions": 0, "roots": 0}

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

        # ---- category.json (GeneralConfig - unlocked_by_default/title/
        # icon/background/starting_points/exclusive_root/spent_points_limit,
        # per javap against net.puffish.skillsmod.config.GeneralConfig) ----
        category_json = cat_dir / "category.json"
        if not category_json.is_file():
            errors.append(f"{cat_id}: missing category.json")
            continue
        try:
            _load_json(category_json)
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

        root_count = 0
        for skill_id, skill in skills.items():
            if not isinstance(skill, dict):
                errors.append(f"{cat_id}: skills.json entry {skill_id!r} is not an object")
                continue
            if skill.get("root") is True:
                root_count += 1
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

        if root_count == 0:
            errors.append(
                f"{cat_id}: no skill node has \"root\": true - every node is "
                "permanently LOCKED for every player regardless of points held "
                "(net.puffish.skillsmod.server.data.CategoryData.getSkillState "
                "only reaches AVAILABLE/AFFORDABLE via a root node or a `normal` "
                "edge from an already-unlocked node, and unlockedSkills starts "
                "empty) - this is issue #24's exact bug class"
            )
        stats["roots"] += root_count

        # ---- connections.json (SkillConnectionsConfig: normal/exclusive
        # bidirectional/unidirectional pairs of skill ids) ----
        connections_json = cat_dir / "connections.json"
        if connections_json.is_file():
            try:
                connections = _load_json(connections_json)
            except json.JSONDecodeError as e:
                errors.append(f"{_rel(connections_json, root)}: JSON parse error: {e}")
                connections = {}
            for group_name in ("normal", "exclusive"):
                group = connections.get(group_name, {}) if isinstance(connections, dict) else {}
                if not isinstance(group, dict):
                    continue
                for direction in ("bidirectional", "unidirectional"):
                    for pair in group.get(direction, []) or []:
                        if not isinstance(pair, list) or len(pair) != 2:
                            errors.append(
                                f"{cat_id}: connections.json {group_name}.{direction} "
                                f"entry {pair!r} is not a 2-element array"
                            )
                            continue
                        for skill_id in pair:
                            if skill_id not in skills:
                                errors.append(
                                    f"{cat_id}: connections.json {group_name}.{direction} "
                                    f"references skill {skill_id!r}, which is not in skills.json"
                                )

        # ---- points source: either experience.json wires an
        # experience_per_level curve (PointSources.EXPERIENCE - points get
        # derived from accumulated XP), or the category grants points another
        # way (starting_points in category.json / an out-of-band `puffish_
        # skills points add` command elsewhere in this pack). Only the
        # experience.json wiring is checkable statically here; its absence
        # combined with no starting_points is a strong signal points can
        # never be earned at all. ----
        experience_json = cat_dir / "experience.json"
        category_data = _load_json(category_json)
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
        f"{stats['roots']} root node(s), all internally consistent"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
