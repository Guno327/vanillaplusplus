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

GitHub issue #66 ("new quests do not show in advancements") added three more
invariants, all ground-truthed by decompiling
net.minecraft.server.advancements.AdvancementVisibilityEvaluator and
net.minecraft.server.PlayerAdvancements out of the real 1.21.1 official-mapped
server jar (server-1.21.1-20240808.144430-srg.jar under this repo's
server/libraries/):

  - The root's own criterion must be self-granting (minecraft:tick, exactly
    like vanilla's own recipes/decorations/crafting_table.json
    "unlock_right_away" criterion - CriteriaTriggers.class shows
    minecraft:tick is registered as a bare `new PlayerTrigger()`,
    unconditionally satisfied on the player's next tick). A root gated on
    minecraft:impossible is never granted, and PlayerAdvancements never
    sends an entire tree to the client unless evaluateVisibility() finds at
    least one visible node in it - so an eternally-ungranted, non-hidden
    root with no visible descendant is invisible forever and the whole tab
    never appears. This was the root cause of #66.
  - Every non-root advancement's parent chain must reach that root within
    VISIBILITY_DEPTH (=2, the literal private static final int in
    AdvancementVisibilityEvaluator.class) hops. Past that depth,
    evaluateVisiblityForUnfinishedNode() only peeks 3 stack frames (self +
    2 ancestors) looking for a SHOW state, so an undone, displayed,
    non-hidden descendant more than 2 parents below the self-granted root
    is invisible until something at or below it is independently granted -
    the same "list of quests is not displayed" symptom as #66, just pushed
    a couple of tiers deeper instead of fixed. (This is why
    scripts/gen_quests.py's build_advancement() parents every non-root
    quest directly to the root - depth 1 for all of them - instead of to
    its first quests.js dependency: this pack's real dependency graph
    chains up to 30 quests deep.)
  - No cycles in the parent graph (a cycle would make every node in it
    unreachable from the root and AdvancementTree.root() would misbehave).

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

# net.minecraft.server.advancements.AdvancementVisibilityEvaluator.VISIBILITY_DEPTH,
# decompiled straight out of the 1.21.1 official-mapped server jar (see the
# module docstring above) - the number of ancestor generations past which an
# undone, non-hidden descendant of a granted root stops being visible.
VISIBILITY_DEPTH = 2

ROOT_TRIGGER = "minecraft:tick"
NON_ROOT_TRIGGER = "minecraft:impossible"


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

    parent_of = {}  # quest id -> parent quest id, non-root entries only
    root_ids = []

    for f in files:
        try:
            data = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            errors.append(f"{f.name}: invalid JSON: {e}")
            continue

        has_background = "background" in data.get("display", {})
        parent = data.get("parent")
        is_root = parent is None

        if is_root:
            stats["roots"] += 1
            root_ids.append(f.stem)
            if not has_background:
                errors.append(f"{f.name}: root advancement (no parent) is missing display.background")
        else:
            if has_background:
                errors.append(f"{f.name}: non-root advancement should not set display.background")
            if not parent.startswith(PARENT_PREFIX):
                errors.append(f"{f.name}: parent {parent!r} doesn't start with {PARENT_PREFIX!r}")
            else:
                parent_id = parent[len(PARENT_PREFIX):]
                parent_of[f.stem] = parent_id
                if parent_id not in file_ids:
                    errors.append(f"{f.name}: parent {parent!r} does not resolve to an existing advancement file")

        # GitHub #66: the root must be self-granting (minecraft:tick) or the
        # whole tab is never visible; every non-root quest must stay gated on
        # minecraft:impossible - only quests.js's "advancement grant ... only
        # ..." command may ever grant it. See the module docstring for the
        # decompiled evidence.
        criteria = data.get("criteria", {})
        triggers = {c.get("trigger") for c in criteria.values()}
        expected = ROOT_TRIGGER if is_root else NON_ROOT_TRIGGER
        if len(criteria) != 1 or triggers != {expected}:
            role = "root" if is_root else "non-root"
            errors.append(
                f"{f.name}: {role} advancement should have exactly one {expected!r} criterion, "
                f"found {criteria!r}"
            )

    if stats["roots"] != 1:
        errors.append(f"expected exactly 1 root advancement (no parent), found {stats['roots']}")

    # GitHub #66: no cycles, and every non-root node must reach the (unique)
    # root within VISIBILITY_DEPTH hops or it can never be shown to a player
    # who hasn't already completed something below it - see the module
    # docstring's decompiled-evidence writeup.
    if stats["roots"] == 1:
        (root_id,) = root_ids
        for qid in file_ids:
            if qid == root_id:
                continue
            seen = {qid}
            cur = qid
            depth = 0
            cycle = False
            while cur in parent_of:
                cur = parent_of[cur]
                depth += 1
                if cur == root_id:
                    break
                if cur in seen:
                    cycle = True
                    break
                seen.add(cur)
            if cycle:
                errors.append(f"{qid}.json: parent chain forms a cycle (via {cur!r})")
            elif cur != root_id:
                # Dangling parent reference already reported above; don't
                # double-report a depth violation for an unreachable chain.
                pass
            elif depth > VISIBILITY_DEPTH:
                errors.append(
                    f"{qid}.json: {depth} hops from root {root_id!r}, exceeds "
                    f"AdvancementVisibilityEvaluator's VISIBILITY_DEPTH={VISIBILITY_DEPTH} - "
                    "this quest can never be shown to a player who hasn't already "
                    "completed something at or below it"
                )

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
