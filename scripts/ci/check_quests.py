#!/usr/bin/env python3
"""Fast-tier CI check: quest-book structural integrity over
pack/kubejs/server_scripts/quests.js.

REWRITTEN for GitHub issue #33 (bespoke quest system replacing FTB Quests -
see scripts/gen_quests.py's own module docstring for the full design
rationale). The quest book no longer lives in
pack/config/ftbquests/quests/ as FTB Quests SNBT; it's generated straight
into a single KubeJS server script as a `const QUEST_CHAPTERS = [...]`
JSON-shaped JS literal followed by the runtime tracker code. This checker
now parses that literal (Python's json.JSONDecoder.raw_decode(), which
reads exactly one JSON value starting at a given offset and hands back
where it ended - no need for a bespoke SNBT-grammar parser the old format
required, since json.dumps() output is always valid, unambiguous JSON) and
validates the same structural invariants the old checker did, adjusted for
the new shape:

  - pack/kubejs/server_scripts/quests.js must exist and contain a
    `const QUEST_CHAPTERS = ` assignment whose value parses as a JSON list.
  - Each chapter: a dict with "id" (string) and "quests" (list).
  - Each quest: a dict with "id" (string), "tasks" (list), "rewards" (list),
    and "dependencies" (list of OTHER QUEST ids - never task/reward ids,
    same namespace rule the old checker enforced, still relevant since
    dependencies are quest-id strings that must resolve).
  - Each task: a dict with "type" in TASK_TYPES ("item", "kill", "dimension",
    "gamestage", "checkmark" - see scripts/gen_quests.py's task builders).
  - Each reward: a dict with "type" in REWARD_TYPES ("item", "xp",
    "command", "gamestage", "toast" - see scripts/gen_quests.py's reward
    builders; "currency" deliberately excluded, same rationale as before -
    Numismatics currency is always granted as literal coin items).

WHAT CHANGED FROM THE OLD SNBT-ERA CHECKER, and why:
  - Tasks/rewards no longer carry their own "id" field at all - the old
    FTB-Quests-era id scheme (every task/reward needing a globally-unique
    hex id) doesn't apply to a plain JS data literal with no SNBT
    id-uniqueness constraint to satisfy. Uniqueness is therefore now
    checked over chapter ids and quest ids only (still the two namespaces
    that matter: dependencies resolve against quest ids, and quest->chapter
    membership is implicit in nesting rather than a filename lookup).
  - "item"/"icon" sub-object "id" fields (e.g. a task's "item": "some:id")
    are plain strings now, not nested {"id":..., "count":...} compounds -
    still never fed into the id-uniqueness registry, for the same reason
    the old checker excluded them (different namespace entirely).
  - chapter_groups.snbt / quest_links (FTB-Quests-specific GUI concepts)
    have no equivalent in this format and are not checked - there is
    nothing there to be inconsistent with anymore.

Usage: python3 scripts/ci/check_quests.py [root]
Exit code: 0 if the quest book is internally consistent, 1 otherwise.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

QUESTS_JS_REL = Path("pack") / "kubejs" / "server_scripts" / "quests.js"
ASSIGNMENT_MARKER = "const QUEST_CHAPTERS = "

TASK_TYPES = {"item", "kill", "dimension", "gamestage", "checkmark"}
REWARD_TYPES = {"item", "xp", "command", "gamestage", "toast"}


class QuestsJsError(Exception):
    pass


def _extract_quest_chapters(text):
    """Find `const QUEST_CHAPTERS = ` and parse exactly the JSON value that
    follows it (via json.JSONDecoder.raw_decode, which parses one value
    starting at an offset and returns how far it read - robust to whatever
    trailing code/whitespace follows, unlike a naive regex on the whole
    rest of the file). Raises QuestsJsError with a human-readable message
    on any failure."""
    idx = text.find(ASSIGNMENT_MARKER)
    if idx == -1:
        raise QuestsJsError(f"could not find {ASSIGNMENT_MARKER!r} assignment")
    start = idx + len(ASSIGNMENT_MARKER)
    try:
        value, _end = json.JSONDecoder().raw_decode(text, start)
    except json.JSONDecodeError as e:
        raise QuestsJsError(f"QUEST_CHAPTERS value did not parse as JSON: {e}")
    if not isinstance(value, list):
        raise QuestsJsError("QUEST_CHAPTERS did not parse to a JSON list")
    return value


def check_quests(root):
    """Returns (errors, stats) - errors is a list of human-readable
    strings (empty == consistent)."""
    errors = []
    stats = {"chapters": 0, "quests": 0, "tasks": 0, "rewards": 0, "ids": 0, "dependencies": 0}

    quests_js = root / QUESTS_JS_REL
    if not quests_js.is_file():
        return ([f"quests script not found: {quests_js}"], stats)

    text = quests_js.read_text(encoding="utf-8")
    try:
        chapters = _extract_quest_chapters(text)
    except QuestsJsError as e:
        return ([f"{QUESTS_JS_REL}: {e}"], stats)

    ids_registry = {}  # id -> [(kind, chapter_id_context), ...]
    quest_ids = set()
    dependency_refs = []  # (dep_id, quest_id)

    def register(id_value, kind, context):
        if not isinstance(id_value, str) or not id_value:
            errors.append(f"{context}: {kind} has a missing/empty 'id'")
            return
        ids_registry.setdefault(id_value, []).append((kind, context))

    for chapter in chapters:
        if not isinstance(chapter, dict):
            errors.append("a QUEST_CHAPTERS entry is not an object")
            continue

        chapter_id = chapter.get("id")
        register(chapter_id, "chapter", f"chapter {chapter_id!r}")
        if isinstance(chapter_id, str):
            stats["chapters"] += 1

        quests = chapter.get("quests")
        if not isinstance(quests, list):
            errors.append(f"chapter {chapter_id!r}: 'quests' is not a list")
            continue

        for quest in quests:
            if not isinstance(quest, dict):
                errors.append(f"chapter {chapter_id!r}: a 'quests' entry is not an object")
                continue
            qid = quest.get("id")
            register(qid, "quest", f"quest {qid!r} (chapter {chapter_id!r})")
            if isinstance(qid, str):
                quest_ids.add(qid)
                stats["quests"] += 1

            tasks = quest.get("tasks")
            if not isinstance(tasks, list):
                errors.append(f"quest {qid!r}: 'tasks' is not a list")
            else:
                if len(tasks) == 0:
                    errors.append(f"quest {qid!r}: has zero tasks (every quest needs >= 1)")
                for task in tasks:
                    if not isinstance(task, dict):
                        errors.append(f"quest {qid!r}: a task entry is not an object")
                        continue
                    ttype = task.get("type")
                    if ttype not in TASK_TYPES:
                        errors.append(f"quest {qid!r}: task has unknown type {ttype!r} (expected one of {sorted(TASK_TYPES)})")
                    stats["tasks"] += 1

            rewards = quest.get("rewards")
            if not isinstance(rewards, list):
                errors.append(f"quest {qid!r}: 'rewards' is not a list")
            else:
                for reward in rewards:
                    if not isinstance(reward, dict):
                        errors.append(f"quest {qid!r}: a reward entry is not an object")
                        continue
                    rtype = reward.get("type")
                    if rtype not in REWARD_TYPES:
                        errors.append(f"quest {qid!r}: reward has unknown type {rtype!r} (expected one of {sorted(REWARD_TYPES)})")
                    if rtype == "currency":
                        errors.append(f"quest {qid!r}: reward uses the deliberately-excluded 'currency' type - coins must be granted as literal items")
                    stats["rewards"] += 1

            deps = quest.get("dependencies", [])
            if not isinstance(deps, list):
                errors.append(f"quest {qid!r}: 'dependencies' is not a list")
            else:
                for dep in deps:
                    if isinstance(dep, str):
                        dependency_refs.append((dep, qid))
                        stats["dependencies"] += 1
                    else:
                        errors.append(f"quest {qid!r}: has a non-string dependency entry {dep!r}")

    # 1. Duplicate ids across chapters/quests.
    for id_value, occurrences in sorted(ids_registry.items()):
        if len(occurrences) > 1:
            locations = ", ".join(f"{kind} ({ctx})" for kind, ctx in occurrences)
            errors.append(f"duplicate id {id_value!r} used by {len(occurrences)} entries: {locations}")
    stats["ids"] = len(ids_registry)

    # 2. Dangling dependency references (dependencies point at quest ids).
    for dep_id, qid in dependency_refs:
        if dep_id not in quest_ids:
            errors.append(f"quest {qid!r} depends on {dep_id!r}, which is not the id of any quest")

    return errors, stats


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else REPO_ROOT

    errors, stats = check_quests(root)

    if errors:
        print(f"check_quests: FAIL - {len(errors)} issue(s):")
        for err in errors:
            print(f"  {err}")
        return 1

    print(
        "check_quests: PASS - "
        f"{stats['chapters']} chapter(s), {stats['quests']} quest(s), "
        f"{stats['tasks']} task(s), {stats['rewards']} reward(s), "
        f"{stats['ids']} unique id(s), {stats['dependencies']} dependenc"
        f"{'y' if stats['dependencies'] == 1 else 'ies'} all resolved"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
