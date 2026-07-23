#!/usr/bin/env python3
"""Fast-tier CI check: structural integrity of the `vppquests` mod's
data-driven quest tree at `pack/kubejs/data/<namespace>/vppquests/
{chapter,quest}/**` (GitHub #109 Phase A/D-labeled-but-really-Phase-A
content port - see `scripts/gen_vppquests_data.py`'s own module docstring
for why this content lives here and not baked into the mod jar).

Mirrors `check_quests.py`'s validation of the legacy `quests.js` book
(same TASK_TYPES/REWARD_TYPES vocabulary - both systems implement the same
5 task/5 reward types, by design, so a future migration/port never needs a
second vocabulary), adjusted for `vppquests`' actual on-disk shape: one
JSON file per chapter (`chapter/<id>.json`) and one per quest
(`quest/<chapter>/<slug>.json`), instead of one big JS literal.

Checks:
  - Every `chapter/*.json` has "title" (str), "subtitle" (list),
    "icon" (str), "order" (int).
  - Every `quest/<chapter>/<slug>.json` has "chapter" (a
    "<namespace>:<chapter>" string matching the file's own containing
    chapter directory and an existing chapter file), "title" (str),
    "icon" (str), "tasks" (non-empty list of valid task dicts),
    "rewards" (list of valid reward dicts), and "dependencies" (list of
    "<namespace>:<chapter>/<slug>" strings that must each resolve to
    another quest file that actually exists).
  - No duplicate quest ids (derived from path, so this mostly catches
    accidental case-sensitivity collisions across filesystems) and no
    duplicate chapter ids.

Usage: python3 scripts/ci/check_vppquests.py [root]
Exit code: 0 if internally consistent (including the trivial case of no
vppquests data existing yet at all - this mod's content is optional pack
data, not a hard requirement), 1 otherwise.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DATA_ROOT_REL = Path("pack") / "kubejs" / "data"
TASK_TYPES = {"item", "kill", "dimension", "gamestage", "checkmark"}
REWARD_TYPES = {"item", "xp", "command", "gamestage", "toast"}
FRAME_TYPES = {"task", "goal", "challenge"}


def _iter_namespaces(data_root):
    if not data_root.is_dir():
        return
    for ns_dir in sorted(data_root.iterdir()):
        if (ns_dir / "vppquests").is_dir():
            yield ns_dir.name, ns_dir / "vppquests"


def check_vppquests(root):
    """Returns (errors, stats) - errors is a list of human-readable
    strings (empty == consistent, including the "no data at all" case)."""
    errors = []
    stats = {"chapters": 0, "quests": 0, "tasks": 0, "rewards": 0, "dependencies": 0}

    data_root = root / DATA_ROOT_REL
    chapter_ids = set()  # "<namespace>:<chapter>"
    quest_ids = set()  # "<namespace>:<chapter>/<slug>"
    dependency_refs = []  # (dep_id, quest_id)

    for namespace, vppquests_dir in _iter_namespaces(data_root):
        chapter_dir = vppquests_dir / "chapter"
        if chapter_dir.is_dir():
            for chapter_file in sorted(chapter_dir.glob("*.json")):
                chapter_id = f"{namespace}:{chapter_file.stem}"
                try:
                    doc = json.loads(chapter_file.read_text(encoding="utf-8"))
                except json.JSONDecodeError as e:
                    errors.append(f"{chapter_file}: invalid JSON: {e}")
                    continue
                if not isinstance(doc, dict):
                    errors.append(f"{chapter_file}: top-level value is not an object")
                    continue
                if chapter_id in chapter_ids:
                    errors.append(f"duplicate chapter id {chapter_id!r}")
                chapter_ids.add(chapter_id)
                stats["chapters"] += 1
                if not isinstance(doc.get("title"), str):
                    errors.append(f"{chapter_file}: 'title' is missing/not a string")
                if not isinstance(doc.get("subtitle", []), list):
                    errors.append(f"{chapter_file}: 'subtitle' is not a list")
                if not isinstance(doc.get("icon"), str):
                    errors.append(f"{chapter_file}: 'icon' is missing/not a string")
                if not isinstance(doc.get("order", 0), int):
                    errors.append(f"{chapter_file}: 'order' is not an int")

        quest_dir = vppquests_dir / "quest"
        if quest_dir.is_dir():
            for quest_file in sorted(quest_dir.rglob("*.json")):
                rel = quest_file.relative_to(quest_dir)
                quest_id = f"{namespace}:{rel.with_suffix('').as_posix()}"
                try:
                    doc = json.loads(quest_file.read_text(encoding="utf-8"))
                except json.JSONDecodeError as e:
                    errors.append(f"{quest_file}: invalid JSON: {e}")
                    continue
                if not isinstance(doc, dict):
                    errors.append(f"{quest_file}: top-level value is not an object")
                    continue
                if quest_id in quest_ids:
                    errors.append(f"duplicate quest id {quest_id!r}")
                quest_ids.add(quest_id)
                stats["quests"] += 1

                chapter_ref = doc.get("chapter")
                expected_chapter_ref = f"{namespace}:{rel.parts[0]}"
                if chapter_ref != expected_chapter_ref:
                    errors.append(
                        f"quest {quest_id!r}: 'chapter' is {chapter_ref!r}, "
                        f"expected {expected_chapter_ref!r} (its own containing directory)"
                    )

                if not isinstance(doc.get("title"), str):
                    errors.append(f"quest {quest_id!r}: 'title' is missing/not a string")
                if not isinstance(doc.get("icon"), str):
                    errors.append(f"quest {quest_id!r}: 'icon' is missing/not a string")

                frame = doc.get("frame", "task")
                if frame not in FRAME_TYPES:
                    errors.append(f"quest {quest_id!r}: 'frame' has unknown value {frame!r} (expected one of {sorted(FRAME_TYPES)})")

                tasks = doc.get("tasks")
                if not isinstance(tasks, list):
                    errors.append(f"quest {quest_id!r}: 'tasks' is not a list")
                else:
                    if len(tasks) == 0:
                        errors.append(f"quest {quest_id!r}: has zero tasks (every quest needs >= 1)")
                    for task in tasks:
                        if not isinstance(task, dict):
                            errors.append(f"quest {quest_id!r}: a task entry is not an object")
                            continue
                        ttype = task.get("type")
                        if ttype not in TASK_TYPES:
                            errors.append(f"quest {quest_id!r}: task has unknown type {ttype!r} (expected one of {sorted(TASK_TYPES)})")
                        stats["tasks"] += 1

                rewards = doc.get("rewards", [])
                if not isinstance(rewards, list):
                    errors.append(f"quest {quest_id!r}: 'rewards' is not a list")
                else:
                    for reward in rewards:
                        if not isinstance(reward, dict):
                            errors.append(f"quest {quest_id!r}: a reward entry is not an object")
                            continue
                        rtype = reward.get("type")
                        if rtype not in REWARD_TYPES:
                            errors.append(f"quest {quest_id!r}: reward has unknown type {rtype!r} (expected one of {sorted(REWARD_TYPES)})")
                        stats["rewards"] += 1

                deps = doc.get("dependencies", [])
                if not isinstance(deps, list):
                    errors.append(f"quest {quest_id!r}: 'dependencies' is not a list")
                else:
                    for dep in deps:
                        if isinstance(dep, str):
                            dependency_refs.append((dep, quest_id))
                            stats["dependencies"] += 1
                        else:
                            errors.append(f"quest {quest_id!r}: has a non-string dependency entry {dep!r}")

    for dep_id, quest_id in dependency_refs:
        if dep_id not in quest_ids:
            errors.append(f"quest {quest_id!r} depends on {dep_id!r}, which is not the id of any quest file")

    return errors, stats


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else REPO_ROOT

    errors, stats = check_vppquests(root)

    if errors:
        print(f"check_vppquests: FAIL - {len(errors)} issue(s):")
        for err in errors:
            print(f"  {err}")
        return 1

    print(
        "check_vppquests: PASS - "
        f"{stats['chapters']} chapter(s), {stats['quests']} quest(s), "
        f"{stats['tasks']} task(s), {stats['rewards']} reward(s), "
        f"{stats['dependencies']} dependenc"
        f"{'y' if stats['dependencies'] == 1 else 'ies'} all resolved"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
