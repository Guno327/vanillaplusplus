#!/usr/bin/env python3
"""Generate FTB Quests' on-disk quest book into pack/config/ftbquests/quests/.

Like Phase 3's gen_skill_tree.py, this is generated rather than hand-typed:
FTB Quests' file format has a lot of interlocking required fields across
chapters/quests/tasks/rewards/translations, and hand-authoring three
chapters' worth by hand would be extremely error prone.

IMPORTANT lesson learned while building this: FTB Quests' file format is
NOT one stable thing across versions. The mod's GitHub default branch (and
its CHANGELOG) is on a JSON5-based rewrite for a much newer Minecraft
version - but our installed jar is version 2101.1.27 for MC 1.21.1, which
predates that rewrite and uses the OLD SNBT/CompoundTag-based format
(".snbt" files, real Minecraft NBT-ish text syntax, not JSON). The first
draft of this generator was written against the wrong (default) branch,
produced JSON files that FTB Quests silently ignored (0 chapters loaded,
zero errors logged - the file extension just didn't match, so nothing even
looked at the content), and had to be rewritten from scratch after cloning
github.com/FTBTeam/FTB-Quests specifically at the `1.21.1/main` branch and
re-deriving every field from *that* branch's writeData/readData methods,
plus FTBLibrary's `1.21.1/main` SNBTParser.java for the actual text grammar.
Ground truth is always the branch matching the exact shipped jar version
(check its mods.toml/manifest) - never the repo's default branch.

Key format facts (see DESIGN.md's "Quest system" section for the full
writeup):
- Every quest object (chapter/quest/task/reward/...) shares ONE id
  namespace, so ids must be globally unique across everything this script
  emits. IDs are always written as a "%016X"-padded hex STRING (matching
  QuestObjectBase#getCodeString) - the reader also accepts a raw number in
  some places, but "dependencies" list entries are read as strings and
  parsed as hex specifically (BaseQuestFile#getID(String)), so hex-string
  everywhere is the one format that's safe in all positions.
- Titles/descriptions are NOT inline fields - they live in ONE flat file
  `lang/<locale>.snbt` (e.g. lang/en_us.snbt - a single file directly in
  the lang/ folder, NOT a per-locale subdirectory - that per-subdirectory
  layout is itself a JSON5-era change), keyed
  "<objectType>.<%016X of id>.<title|quest_desc|chapter_subtitle>".
- SNBT here means actual stringified NBT (FTBLibrary's own hand-written
  parser, SNBTParser.java) - `{key: value, ...}` compounds, `[v1, v2]`
  lists, quoted strings, bare `true`/`false`. Minecraft's NumericTag
  cross-coercion (getInt()/getLong()/getDouble() all convert between
  underlying numeric tag widths) means plain unsuffixed numbers work
  everywhere here regardless of whether the Java field is int/long/double -
  no need to emit type suffixes like `5L` or `5d`.
- StatTask reads a LIFETIME, monotonically-increasing value from Minecraft's
  vanilla `minecraft:custom` stat registry directly off the player - it's
  only safe for one-time, non-repeating milestone quests. If used on a
  repeatable quest, completing it once means the underlying stat is already
  past the threshold, so it snaps to "complete" again the instant the repeat
  cooldown clears. KillTask/consuming-ItemTask instead call addProgress(+1)
  per event, so they correctly restart from 0 after a repeat reset - those
  are what the daily chapter uses.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUESTS_DIR = ROOT / "pack" / "config" / "ftbquests" / "quests"

# ---------------------------------------------------------------------------
# Minimal SNBT serializer (FTBLibrary's SNBTParser.java grammar - see the
# module docstring). Always double-quotes strings/keys and never emits type
# suffixes; both are always-safe choices per that grammar.
# ---------------------------------------------------------------------------
def _snbt_string(s):
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def snbt(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value) if isinstance(value, float) else str(value)
    if isinstance(value, str):
        return _snbt_string(value)
    if isinstance(value, list):
        return "[" + ", ".join(snbt(v) for v in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{_snbt_string(k)}: {snbt(v)}" for k, v in value.items()) + "}"
    raise TypeError(f"unsupported SNBT value: {value!r}")


# ---------------------------------------------------------------------------
# ID allocation + translation collection
# ---------------------------------------------------------------------------
_next_id = [0x10000]


def new_id():
    _next_id[0] += 1
    return _next_id[0]


def hexid(n):
    return "%016X" % n


translations = {}


def set_title(obj_type, oid, text):
    translations[f"{obj_type}.{hexid(oid)}.title"] = text


def set_quest_desc(oid, lines):
    translations[f"quest.{hexid(oid)}.quest_desc"] = lines


def set_chapter_subtitle(oid, lines):
    translations[f"chapter.{hexid(oid)}.chapter_subtitle"] = lines


def item_stack(item_id, count=1):
    d = {"id": item_id, "count": count}
    return d


# ---------------------------------------------------------------------------
# Task/reward builders (field names/shapes from Task.java/Reward.java subclasses
# on the FTB-Quests `1.21.1/main` branch). Only `gamestage` is used now that
# Tier Progression is the sole remaining chapter (Phase 6 moved the
# item/kill/stat-based chapters to vanilla advancements + KubeJS instead -
# see the note further down).
# ---------------------------------------------------------------------------
def stage_task(stage_id):
    return "gamestage", {"stage": stage_id}


def item_reward(item_id, count=1):
    return "item", {"item": item_stack(item_id, count)}


def skill_xp_reward(category, amount):
    """Grants puffish_skills category XP via its /puffish_skills experience add
    command (net.puffish.skillsmod.commands.ExperienceCommand, registered as a
    direct child of the "puffish_skills" root alongside "skills"/"category"/
    "points"/"open" - NOT nested under the "skills" subcommand, despite the
    similar name; confirmed by reading SkillsMod#onCommandsRegister. Matches
    the command already used and working in
    pack/kubejs/server_scripts/skills.js's Building-category XP grant - an
    earlier draft of this function used "skills experience add ..." (missing
    the mod-id root and wrongly nesting under "skills"), which would have
    silently failed as an unknown command the first time a reward claimed).
    Requires Commands.LEVEL_GAMEMASTERS (permission level 2), so
    permission_level must be bumped since the reward otherwise runs as the
    claiming player."""
    return "command", {
        "command": f"puffish_skills experience add {{p}} {category} {amount}",
        "permission_level": 2,
        "silent": True,
    }


# ---------------------------------------------------------------------------
# Quest/chapter builders
# ---------------------------------------------------------------------------
def make_quest(quests_list, x, y, title, tasks, rewards, dependencies=None,
               can_repeat=False, repeat_cooldown=0, desc=None, quest_icon=None):
    qid = new_id()
    set_title("quest", qid, title)
    if desc:
        set_quest_desc(qid, desc)

    q = {"id": hexid(qid), "x": float(x), "y": float(y)}
    if quest_icon:
        q["icon"] = item_stack(quest_icon)
    if dependencies:
        q["dependencies"] = [hexid(d) for d in dependencies]
    if can_repeat:
        q["can_repeat"] = True
        if repeat_cooldown:
            q["repeat_cooldown"] = repeat_cooldown

    q["tasks"] = []
    for ttype, tdata in tasks:
        tid = new_id()
        q["tasks"].append({"id": hexid(tid), "type": ttype, **tdata})

    q["rewards"] = []
    for rtype, rdata in rewards:
        rid = new_id()
        q["rewards"].append({"id": hexid(rid), "type": rtype, **rdata})

    quests_list.append(q)
    return qid


def make_chapter(filename, title, subtitle_lines, quests_builder_fn, order_index,
                  chapter_icon=None):
    cid = new_id()
    set_title("chapter", cid, title)
    if subtitle_lines:
        set_chapter_subtitle(cid, subtitle_lines)

    quests = []
    quests_builder_fn(quests)

    chapter = {
        "id": hexid(cid),
        "filename": filename,
        "order_index": order_index,
        "default_quest_shape": "",
        "quests": quests,
        "quest_links": [],
    }
    if chapter_icon:
        chapter["icon"] = item_stack(chapter_icon)
    return chapter


# ---------------------------------------------------------------------------
# Chapter 1: Tier Progression (the preset track) - one quest per
# ProgressiveStages tier, gated by gamestage tasks that read the SAME stage
# ids as pack/config/ProgressiveStages/*.toml (confirmed via boot log:
# ProgressiveStagesStageProvider replaces FTB Library's own stage backend, so
# "stage" here checks real tier attainment, not a separate FTB Quests-only
# concept). This chapter doesn't grant tiers - ProgressiveStages' own
# triggers still do that - it's a quest-book VIEW of tier progress with RPG
# XP as a bonus layered on top, avoiding any assumption about whether
# writing back through the replaced stage provider is even supported.
# team_stage is left at its default (false, i.e. the task checks the
# individual player) even now that Phase 6 flipped team_mode to "ftb_teams" -
# sharing already happens one layer down, at the ProgressiveStages config
# level: when its own team_mode is "ftb_teams", ProgressiveStages shares
# stage *state itself* across a party, so checking any one party member's
# stage already reflects the whole party's progress. Not independently
# verifiable in this sandbox (no in-game client to actually form a party and
# check a second member's view) - see DESIGN.md's Team mode section.
# ---------------------------------------------------------------------------
TIERS = [
    ("rootborn", "Rootborn", "mining", 40, "minecraft:wooden_pickaxe"),
    ("andesite_age", "Andesite Age", "mining", 80, "create:andesite_alloy"),
    ("brass_age", "Brass Age", "building", 150, "create:brass_ingot"),
    ("precision_age", "Precision Age", "swords", 300, "minecraft:diamond"),
    ("induction_age", "Induction Age", "bows", 600, "minecraft:netherite_ingot"),
    ("starforged_age", "Starforged Age", "swimming", 1200, "minecraft:nether_star"),
]


def build_tier_chapter(quests):
    prev = None
    for i, (stage_id, label, category, xp, item_id) in enumerate(TIERS):
        deps = [prev] if prev is not None else None
        prev = make_quest(
            quests, x=i * 2, y=0,
            title=f"Reach {label}",
            desc=[f"Advance to the {label} through Create's own progression - see the tier ladder in the guidebook." if i == 0
                  else f"Keep progressing through Create's material chain to reach {label}."],
            tasks=[stage_task(stage_id)],
            rewards=[skill_xp_reward(category, xp), item_reward(item_id)],
            dependencies=deps,
            quest_icon=item_id,
        )


# ---------------------------------------------------------------------------
# Chapters 2/3 (Lifetime Achievements, Daily Bounties) used to live here too,
# but Phase 6 moved them OUT of FTB Quests entirely: FTB Quests tracks all
# progress at the FTB Teams level with no per-chapter override, so once real
# multi-member parties exist (Phase 6 flips team_mode to "ftb_teams"), these
# would become party-shared too - which instructions.md explicitly says they
# should NOT be. Rather than accept that deviation, they're rebuilt as
# genuinely per-player systems: Lifetime Achievements as vanilla datapack
# advancements (scripts/gen_achievements.py - advancements are per-player by
# definition in vanilla, with their own native UI/persistence, no FTB Quests
# or Teams involvement at all), and Daily Bounties as a KubeJS script using
# per-player persistentData for the 24h cooldown (pack/kubejs/server_scripts/
# dailies.js, generated by scripts/gen_dailies.py). See DESIGN.md's Phase 6
# section for the full reasoning.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Assemble + write
# ---------------------------------------------------------------------------
def main():
    chapters_dir = QUESTS_DIR / "chapters"
    lang_dir = QUESTS_DIR / "lang"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    lang_dir.mkdir(parents=True, exist_ok=True)

    chapter_defs = [
        ("tier_progression", "Tier Progression", ["Follow Create's own material chain from Rootborn to the stars."], build_tier_chapter, "minecraft:nether_star"),
    ]

    for i, (filename, title, subtitle, builder, chap_icon) in enumerate(chapter_defs):
        chapter = make_chapter(filename, title, subtitle, builder, order_index=i, chapter_icon=chap_icon)
        (chapters_dir / f"{filename}.snbt").write_text(snbt(chapter) + "\n")
        print(f"wrote chapters/{filename}.snbt ({len(chapter['quests'])} quests)")

    data = {
        "version": 13,
        "default_reward_team": False,
        "default_consume_items": False,
        "default_autoclaim_rewards": "disabled",
        "default_quest_shape": "",
        "default_quest_disable_jei": False,
        "emergency_items_cooldown": 300,
        "drop_loot_crates": False,
        "disable_gui": False,
        "grid_scale": 0.5,
        "pause_game": False,
        "lock_message": "",
        "progression_mode": "linear",
        "detection_delay": 20,
        "show_lock_icons": True,
        "drop_book_on_death": False,
        "hide_excluded_quests": False,
        "fallback_locale": "en_us",
        "verify_on_load": False,
    }
    (QUESTS_DIR / "data.snbt").write_text(snbt(data) + "\n")

    (QUESTS_DIR / "chapter_groups.snbt").write_text(snbt({"chapter_groups": []}) + "\n")

    (lang_dir / "en_us.snbt").write_text(snbt(translations) + "\n")

    print(f"wrote data.snbt, chapter_groups.snbt, lang/en_us.snbt ({len(translations)} keys)")


if __name__ == "__main__":
    main()
