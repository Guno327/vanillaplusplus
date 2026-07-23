#!/usr/bin/env python3
"""GitHub issue #109 Phase A/D-labeled-but-really-Phase-A content port: emits
the existing 62-quest book (`scripts/gen_quests.py`'s own `CHAPTER_DEFS`/
`build_*` functions - the single source of truth for this content, reused
directly rather than re-transcribed by hand) as data-driven JSON under
`pack/kubejs/data/vanillaplusplus/vppquests/{quest,chapter}/**`, in the
`vppquests` mod's own schema (see `mods-src/vppquests/src/main/java/.../
quest/Quest.java`, `QuestChapter.java`, `QuestTask.java`, `QuestReward.java`
for the exact JSON shape each `fromJson()` expects).

WHY THIS LOCATION (not baked into the mod jar's own resources): `vppquests`'
`QuestReloadListener` reads `data/<namespace>/vppquests/quest/**` off the
live `ResourceManager` - the same merged-datapack view every other reload
listener in this pack sees (recipes, advancements, loot tables) - not just
its own jar's bundled resources. `pack/kubejs/data/vanillaplusplus/` is
already this pack's live datapack tree (see `advancement/quests/` written by
`gen_quests.py` itself), so quest content belongs there, generated the same
"generate, don't hand-type, reload like everything else" way every other
pack-content path in this repo already works - not shipped as a mod
resource, which would require a mod rebuild to reflect a content-only
change.

DESIGN.md's own phasing calls this the deferred half of PHASE A ("port
today's 62 quests unchanged... so the mod itself gets validated against
known-good content"), NOT Phase D (Phase D is the all-new, much larger
questline REBUILD, ~150-250 quests, gated on owner sign-off - see
DESIGN.md's "Questline rebuild" subsection). This script does not touch
`criticalPath` (left `false`/absent for every ported quest) since that flag
is specifically for Phase D's new critical-path spine, not this verbatim
port.

IDENTITY MAPPING (dependencies): `gen_quests.py`'s quest ids are
`"<chapter>__<slug>"` strings (double-underscore join - verified no
chapter id or slug itself contains "__", so this is an unambiguous,
lossless transform); `vppquests`' ids are `<chapter>/<slug>` file-derived
ResourceLocations. This script rewrites every `dependencies` entry through
that same transform so the ported DAG's edges point at the right sibling
quest files.

FRAME: reuses `gen_quests.py`'s own `advancement_frame()` (challenge for
the 4 hardest late-game quests, goal for gate/gamestage quests, task for
everything else) so `vppquests`' GUI keeps the same visual vocabulary the
advancement-based GUI already established, rather than inventing a new
rule.

Idempotent/regeneratable: deletes and rewrites both output directories on
every run, same convention `gen_quests.py`'s own `write_advancements()`
already uses.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import gen_quests  # noqa: E402 - local sibling module, path inserted above

NAMESPACE = "vanillaplusplus"
QUEST_OUT_DIR = ROOT / "pack" / "kubejs" / "data" / NAMESPACE / "vppquests" / "quest"
CHAPTER_OUT_DIR = ROOT / "pack" / "kubejs" / "data" / NAMESPACE / "vppquests" / "chapter"


def legacy_id_to_path(legacy_id):
    """"<chapter>__<slug>" -> "<chapter>/<slug>" - see module docstring's
    "IDENTITY MAPPING" section for why this split is safe."""
    chapter_id, slug = legacy_id.split("__", 1)
    return f"{chapter_id}/{slug}"


def convert_task(task):
    # Task dict shapes are already identical to QuestTask.fromJson()'s
    # expected fields (see gen_quests.py's item_task/kill_task/etc.
    # builders) - passed through unchanged.
    return dict(task)


def convert_reward(reward):
    # Same for rewards - QuestReward.fromJson() expects the exact fields
    # gen_quests.py's item_reward/skill_xp_reward/etc. already emit.
    return dict(reward)


def convert_quest(quest, chapter_id):
    path = legacy_id_to_path(quest["id"])
    _, slug = path.split("/", 1)
    frame = gen_quests.advancement_frame(quest)
    doc = {
        "chapter": f"{NAMESPACE}:{chapter_id}",
        "title": quest["title"],
        "description": list(quest["desc"]),
        "icon": quest["icon"],
        "frame": frame,
        "dependencies": [f"{NAMESPACE}:{legacy_id_to_path(dep)}" for dep in quest["dependencies"]],
        "tasks": [convert_task(t) for t in quest["tasks"]],
        "rewards": [convert_reward(r) for r in quest["rewards"]],
    }
    return slug, doc


def convert_chapter(chapter):
    return {
        "title": chapter["title"],
        "subtitle": list(chapter["subtitle"]),
        "icon": chapter["icon"],
        "order": chapter["order"],
    }


def main():
    chapters = []
    for i, (chapter_id, title, subtitle, builder, chap_icon) in enumerate(gen_quests.CHAPTER_DEFS):
        chapter = gen_quests.make_chapter(chapter_id, title, subtitle, builder, order_index=i, chapter_icon=chap_icon)
        chapters.append(chapter)

    if QUEST_OUT_DIR.exists():
        shutil.rmtree(QUEST_OUT_DIR)
    if CHAPTER_OUT_DIR.exists():
        shutil.rmtree(CHAPTER_OUT_DIR)
    QUEST_OUT_DIR.mkdir(parents=True)
    CHAPTER_OUT_DIR.mkdir(parents=True)

    quest_count = 0
    for chapter in chapters:
        chapter_id = chapter["id"]

        chapter_doc = convert_chapter(chapter)
        chapter_file = CHAPTER_OUT_DIR / f"{chapter_id}.json"
        chapter_file.write_text(json.dumps(chapter_doc, indent=2) + "\n")

        chapter_quest_dir = QUEST_OUT_DIR / chapter_id
        chapter_quest_dir.mkdir(parents=True, exist_ok=True)
        for quest in chapter["quests"]:
            slug, quest_doc = convert_quest(quest, chapter_id)
            quest_file = chapter_quest_dir / f"{slug}.json"
            quest_file.write_text(json.dumps(quest_doc, indent=2) + "\n")
            quest_count += 1

    print(
        f"wrote {len(chapters)} chapter file(s) to {CHAPTER_OUT_DIR}, "
        f"{quest_count} quest file(s) to {QUEST_OUT_DIR}"
    )


if __name__ == "__main__":
    main()
