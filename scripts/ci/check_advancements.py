#!/usr/bin/env python3
"""Fast-tier CI check: vanilla advancement tree integrity over
pack/kubejs/data/vanillaplusplus/advancement/quests/*.json.

GitHub issue #36 (vanilla advancement tree as a free, no-new-mod GUI layer
over the KubeJS quest tracker - see scripts/gen_quests.py's own
write_advancements()/build_advancement() for the full design rationale,
ground-truthed against the real vanilla 1.21.1 client jar's own
data/minecraft/advancement/*.json). One file per quest id; every non-root
file has a "parent" pointing at another quest's advancement id
(vanillaplusplus:quests/<id>) - this checker validates that graph is
internally consistent: every advancement file corresponds to a real quest
id from quests.js, every parent reference resolves to another advancement
file that actually exists, there is exactly one root (no parent - matches
quests.js's own single true root, rootborn__welcome, since chapters chain
end to end), and the root (and only the root) carries display.background
(required for a tree-root tab in the real vanilla advancement screen,
confirmed via the ground-truth jar read above).

Usage: python3 scripts/ci/check_advancements.py [root]
Exit code: 0 if the advancement tree is internally consistent, 1 otherwise.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

ADVANCEMENTS_DIR_REL = Path("pack") / "kubejs" / "data" / "vanillaplusplus" / "advancement" / "quests"
QUESTS_JS_REL = Path("pack") / "kubejs" / "server_scripts" / "quests.js"
ASSIGNMENT_MARKER = "const QUEST_CHAPTERS = "
PARENT_PREFIX = "vanillaplusplus:quests/"


def _load_quest_ids(root):
    """Pull the real quest id set out of quests.js, the single source of
    truth both this generator's outputs are derived from."""
    path = root / QUESTS_JS_REL
    if not path.exists():
        return None
    text = path.read_text()
    idx = text.find(ASSIGNMENT_MARKER)
    if idx < 0:
        return None
    start = idx + len(ASSIGNMENT_MARKER)
    decoder = json.JSONDecoder()
    chapters, _ = decoder.raw_decode(text, start)
    return {quest["id"] for chapter in chapters for quest in chapter["quests"]}


def check_advancements(root=REPO_ROOT):
    errors = []
    stats = {"files": 0, "roots": 0}

    quest_ids = _load_quest_ids(root)
    if quest_ids is None:
        return [f"could not load quest ids from {QUESTS_JS_REL}"], stats

    adv_dir = root / ADVANCEMENTS_DIR_REL
    if not adv_dir.is_dir():
        return [f"{ADVANCEMENTS_DIR_REL} does not exist"], stats

    files = sorted(adv_dir.glob("*.json"))
    stats["files"] = len(files)
    file_ids = {f.stem for f in files}

    if file_ids != quest_ids:
        missing = quest_ids - file_ids
        extra = file_ids - quest_ids
        if missing:
            errors.append(f"{len(missing)} quest(s) have no advancement file: {sorted(missing)}")
        if extra:
            errors.append(f"{len(extra)} advancement file(s) don't correspond to any quest: {sorted(extra)}")

    for f in files:
        try:
            data = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            errors.append(f"{f.name}: invalid JSON: {e}")
            continue

        has_background = "background" in data.get("display", {})
        parent = data.get("parent")

        if parent is None:
            stats["roots"] += 1
            if not has_background:
                errors.append(f"{f.name}: root advancement (no parent) is missing display.background")
        else:
            if has_background:
                errors.append(f"{f.name}: non-root advancement should not set display.background")
            if not parent.startswith(PARENT_PREFIX):
                errors.append(f"{f.name}: parent {parent!r} doesn't start with {PARENT_PREFIX!r}")
            else:
                parent_id = parent[len(PARENT_PREFIX):]
                if parent_id not in file_ids:
                    errors.append(f"{f.name}: parent {parent!r} does not resolve to an existing advancement file")

        if data.get("criteria", {}).get("impossible", {}).get("trigger") != "minecraft:impossible":
            errors.append(f"{f.name}: missing the command-only minecraft:impossible criterion")

    if stats["roots"] != 1:
        errors.append(f"expected exactly 1 root advancement (no parent), found {stats['roots']}")

    return errors, stats


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else REPO_ROOT

    errors, stats = check_advancements(root)

    if errors:
        print(f"check_advancements: FAIL - {len(errors)} issue(s):")
        for err in errors:
            print(f"  {err}")
        return 1

    print(f"check_advancements: PASS - {stats['files']} advancement file(s), {stats['roots']} root")
    return 0


if __name__ == "__main__":
    sys.exit(main())
