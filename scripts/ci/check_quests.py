#!/usr/bin/env python3
"""Fast-tier CI check: FTB Quests integrity over
pack/config/ftbquests/quests/.

Ground-truthed against the actual tree (pack/config/ftbquests/quests/) and
scripts/gen_quests.py (the generator that produces it) before writing this
check:

  - Chapter files live at pack/config/ftbquests/quests/chapters/*.snbt. Each
    is a single compound with: "id" (the chapter's own id), "filename",
    "quests" (list of quest objects), "quest_links" (list, empty in this
    repo), plus cosmetic fields (order_index, icon, ...).
  - Each quest object has "id", optionally "dependencies" (a list of OTHER
    QUEST ids - never task/reward ids), "tasks" (list of task objects, each
    with its own "id"), and "rewards" (list of reward objects, each with
    its own "id").
  - IMPORTANT: task/reward objects frequently carry a nested "item": {"id":
    "some:item", "count": N} (and icons carry "icon": {"id": ...}) - these
    "id" fields are ITEM/BLOCK ids, a completely different namespace from
    quest/chapter/task/reward ids, and must NOT be checked for uniqueness
    or used to satisfy a dependency reference. This check only ever reads
    "id" from the specific structural positions listed above (chapter
    itself; each entry of "quests"; each entry of a quest's "tasks"; each
    entry of a quest's "rewards"; each entry of a chapter's "quest_links"),
    never from "item"/"icon" sub-objects.
  - pack/config/ftbquests/quests/chapter_groups.snbt in this repo is
    `{"chapter_groups": []}` - empty, so it references no chapters. If it's
    ever populated, FTB Quests' own convention is for group entries to list
    chapter ids under a "chapters" key; this check honors that if present
    (see _chapter_ids_referenced_by_groups below) but there is currently
    nothing to ground-truth that shape against in this repo.
  - There is no pack/config/ftbquests/quests/reward_tables/ (or similar)
    directory in this repo, so reward-table ids are not currently exercised
    by real data; the check still scans such a directory generically if one
    ever appears (each file's own top-level "id" is registered into the
    same global id namespace), documented here since it's untested against
    real data.

Uses validate_snbt.parse_snbt() (from #2) rather than a second parser, per
the issue's instruction to build this on top of that parser.

Usage: python3 scripts/ci/check_quests.py [root]
Exit code: 0 if the quest tree is internally consistent, 1 otherwise.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_snbt import SNBTError, parse_snbt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _quests_root(root):
    return root / "pack" / "config" / "ftbquests" / "quests"


def _load(path):
    return parse_snbt(Path(path).read_text(encoding="utf-8"))


def _register(ids_registry, id_value, kind, source_file, errors):
    if not isinstance(id_value, str) or not id_value:
        errors.append(f"{source_file}: {kind} has a missing/empty 'id'")
        return
    ids_registry.setdefault(id_value, []).append((kind, source_file))


def _chapter_ids_referenced_by_groups(chapter_groups_data):
    """FTB Quests chapter_groups.snbt convention: {"chapter_groups": [{"id":
    ..., "chapters": ["<chapter id>", ...]}, ...]}. Returns the set of
    chapter ids referenced this way (empty if the file references none, as
    is currently the case in this repo)."""
    referenced = set()
    groups = chapter_groups_data.get("chapter_groups", [])
    if not isinstance(groups, list):
        return referenced
    for group in groups:
        if not isinstance(group, dict):
            continue
        for cid in group.get("chapters", []) or []:
            if isinstance(cid, str):
                referenced.add(cid)
    return referenced


def check_quests(root):
    """Returns (errors, stats) - errors is a list of human-readable
    strings (empty == consistent)."""
    errors = []
    stats = {"chapters": 0, "quests": 0, "tasks": 0, "rewards": 0, "ids": 0, "dependencies": 0}

    quests_root = _quests_root(root)
    if not quests_root.is_dir():
        return ([f"quests directory not found: {quests_root}"], stats)

    chapters_dir = quests_root / "chapters"
    chapter_files = sorted(chapters_dir.glob("*.snbt")) if chapters_dir.is_dir() else []
    if not chapter_files:
        errors.append(f"no chapter *.snbt files found under {chapters_dir}")

    ids_registry = {}  # id -> [(kind, source_file), ...]
    quest_ids = set()
    dependency_refs = []  # (dep_id, source_file, quest_id)
    chapter_ids = set()
    chapter_filenames = {}  # filename (stem) -> chapter id, for chapter_groups cross-check

    for path in chapter_files:
        rel = str(path.relative_to(root)) if _is_relative(path, root) else str(path)
        try:
            data = _load(path)
        except SNBTError as e:
            errors.append(f"{rel}: SNBT parse error: {e}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{rel}: chapter file did not parse to a compound")
            continue

        chapter_id = data.get("id")
        _register(ids_registry, chapter_id, "chapter", rel, errors)
        if isinstance(chapter_id, str):
            chapter_ids.add(chapter_id)
            stats["chapters"] += 1
            chapter_filenames[data.get("filename", path.stem)] = chapter_id

        for quest in data.get("quests", []) or []:
            if not isinstance(quest, dict):
                errors.append(f"{rel}: a 'quests' entry is not a compound")
                continue
            qid = quest.get("id")
            _register(ids_registry, qid, "quest", rel, errors)
            if isinstance(qid, str):
                quest_ids.add(qid)
                stats["quests"] += 1

            for task in quest.get("tasks", []) or []:
                if not isinstance(task, dict):
                    errors.append(f"{rel}: quest {qid!r} has a non-compound task entry")
                    continue
                _register(ids_registry, task.get("id"), "task", rel, errors)
                stats["tasks"] += 1

            for reward in quest.get("rewards", []) or []:
                if not isinstance(reward, dict):
                    errors.append(f"{rel}: quest {qid!r} has a non-compound reward entry")
                    continue
                _register(ids_registry, reward.get("id"), "reward", rel, errors)
                stats["rewards"] += 1

            for dep in quest.get("dependencies", []) or []:
                if isinstance(dep, str):
                    dependency_refs.append((dep, rel, qid))
                    stats["dependencies"] += 1
                else:
                    errors.append(f"{rel}: quest {qid!r} has a non-string dependency entry {dep!r}")

        for ql in data.get("quest_links", []) or []:
            if isinstance(ql, dict) and "id" in ql:
                _register(ids_registry, ql.get("id"), "quest_link", rel, errors)

    # Reward tables, if this repo ever gains a directory of them (see
    # module docstring - currently ungrounded, no real data exists).
    reward_tables_dir = quests_root / "reward_tables"
    if reward_tables_dir.is_dir():
        for path in sorted(reward_tables_dir.glob("*.snbt")):
            rel = str(path.relative_to(root))
            try:
                data = _load(path)
            except SNBTError as e:
                errors.append(f"{rel}: SNBT parse error: {e}")
                continue
            if isinstance(data, dict):
                _register(ids_registry, data.get("id"), "reward_table", rel, errors)

    # 1. Duplicate ids across the whole tree.
    for id_value, occurrences in sorted(ids_registry.items()):
        if len(occurrences) > 1:
            locations = ", ".join(f"{kind} in {src}" for kind, src in occurrences)
            errors.append(f"duplicate id {id_value!r} used by {len(occurrences)} entries: {locations}")
    stats["ids"] = len(ids_registry)

    # 2. Dangling dependency references (dependencies point at quest ids).
    for dep_id, rel, qid in dependency_refs:
        if dep_id not in quest_ids:
            errors.append(
                f"{rel}: quest {qid!r} depends on {dep_id!r}, which is not the id of any quest")

    # 3. chapter_groups.snbt cross-check, if it references chapters.
    chapter_groups_path = quests_root / "chapter_groups.snbt"
    if chapter_groups_path.is_file():
        rel = str(chapter_groups_path.relative_to(root))
        try:
            cg_data = _load(chapter_groups_path)
        except SNBTError as e:
            errors.append(f"{rel}: SNBT parse error: {e}")
            cg_data = {}
        if isinstance(cg_data, dict):
            referenced = _chapter_ids_referenced_by_groups(cg_data)
            for cid in sorted(referenced):
                if cid not in chapter_ids:
                    errors.append(
                        f"{rel}: references chapter id {cid!r}, which no chapter file declares")

    return errors, stats


def _is_relative(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


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
