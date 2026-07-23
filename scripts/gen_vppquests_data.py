#!/usr/bin/env python3
"""GitHub issue #109 cutover: generates `vppquests`' data-driven quest/
chapter JSON under `pack/kubejs/data/vanillaplusplus/vppquests/
{quest,chapter}/**` (see `mods-src/vppquests/src/main/java/.../quest/
Quest.java`, `QuestChapter.java`, `QuestTask.java`, `QuestReward.java` for
the exact JSON shape each `fromJson()` expects).

HISTORY (why this file looks the way it does): the 62-quest/10-chapter
content below originated in the now-REMOVED `scripts/gen_quests.py`
(GitHub #33's KubeJS `quests.js` tracker + its #36/#66 vanilla-advancement
GUI layer). The owner reported in 0.5.2 that the legacy quest system was
broken end to end (progress wasn't recognized at all) and, once `vppquests`
was ready to actually load in the pack (#109 Phase C), directed a full
cutover: remove the broken legacy system entirely rather than keep
migrating dead code forward. The CONTENT itself (which chapters/quests/
tasks/rewards exist) was not what was broken and is kept - only the old
delivery mechanism (KubeJS tracker + vanilla-advancement bolt-on) is gone.
So the task/reward builder functions and the `build_*`/`CHAPTER_DEFS`
chapter data below are copied in verbatim from the last version of
`gen_quests.py` (not re-transcribed - same item/entity ids, same xp/spur
amounts, same dependency wiring) and this module is now the single,
self-contained source of truth for this content - there is no more
`gen_quests.py` to import from.

DATA MODEL NOTE: the task/reward dict shapes below (`"type"`, `"item"`,
`"count"`, `"consume"`, `"onlyFromCrafting"`, etc.) are already identical
to what `vppquests`' `QuestTask.fromJson()`/`QuestReward.fromJson()`
expect - no field renaming needed, only the container format changed
(one JSON file per quest/chapter, not one big JS literal).

IDENTITY-STYLE ID MAPPING (kept from the old id scheme, not because
anything is being migrated - just because these are still perfectly good,
readable ids): each quest was built with a `"<chapter>__<slug>"` string id
(double-underscore join - no chapter id or slug itself contains "__", so
this is an unambiguous, lossless transform); `vppquests`' own ids are
`<chapter>/<slug>` file-derived ResourceLocations, so `dependencies`
entries get rewritten through that same transform.

FRAME: `quest_frame()` (renamed from the old `advancement_frame()` - no
advancements exist anymore, but the same "challenge" for the 4 hardest
late-game quests / "goal" for gate quests / "task" for everything else
vocabulary carries over unchanged) drives `vppquests`' own GUI framing.

`criticalPath` is left `false`/absent for every quest here - that flag is
for a future critical-path-spine questline redesign, not this content.

Idempotent/regeneratable: deletes and rewrites both output directories on
every run.

Usage: python3 scripts/gen_vppquests_data.py
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAMESPACE = "vanillaplusplus"
QUEST_OUT_DIR = ROOT / "pack" / "kubejs" / "data" / NAMESPACE / "vppquests" / "quest"
CHAPTER_OUT_DIR = ROOT / "pack" / "kubejs" / "data" / NAMESPACE / "vppquests" / "chapter"

# ---------------------------------------------------------------------------
# "challenge" frame for the four hardest, latest-gated quests; "goal" for
# every tier-gate quest (gamestage task); "task" for everything else -
# matches FTB Quests' own visual vocabulary this book used to use, carried
# over unchanged (see quest_frame() below).
# ---------------------------------------------------------------------------
CHALLENGE_QUEST_IDS = {
    "jovian_frontier__storage_infinity",
    "jovian_frontier__energy_infinity",
    "jovian_frontier__resource_infinity",
    "jovian_frontier__journeys_end",
}


# ---------------------------------------------------------------------------
# Task builders - dict shape consumed directly by QuestTask.fromJson().
# ---------------------------------------------------------------------------
def item_task(item_id, count=1, consume_items=True, only_from_crafting=False):
    return {
        "type": "item",
        "item": item_id,
        "count": count,
        "consume": consume_items,
        "onlyFromCrafting": only_from_crafting,
    }


def kill_task(entity_id, value=1):
    return {"type": "kill", "entity": entity_id, "count": value}


def dimension_task(dimension_id):
    return {"type": "dimension", "dimension": dimension_id}


def stage_task(stage_id):
    return {"type": "gamestage", "stage": stage_id}


def checkmark_task():
    return {"type": "checkmark"}


# ---------------------------------------------------------------------------
# Reward builders - dict shape consumed directly by QuestReward.fromJson().
# ---------------------------------------------------------------------------
def item_reward(item_id, count=1):
    return {"type": "item", "item": item_id, "count": count}


def skill_xp_reward(category, amount):
    """puffish_skills XP reward. Issue #116 ("Converge all skill trees into
    ONE unified tree") supersedes issue #71's 23-category structure with a
    single puffish_skills category (scripts/gen_skill_tree.py's
    UNIFIED_CATEGORY_ID) - every call site below passes "adventurer" (the
    old per-topic category ids are no longer real puffish_skills categories
    and would fail the `puffish_skills experience add` command at
    runtime)."""
    return {"type": "xp", "category": category, "amount": amount}


def command_reward(command, silent=True):
    """Arbitrary command reward, {p} templated to the granting player's
    username at grant time. Unused by this book's actual 62 quests - kept
    for parity with the issue's listed reward-type surface."""
    return {"type": "command", "command": command, "silent": silent}


def gamestage_reward(stage_id):
    """Grants a ProgressiveStages stage directly. Unused by this book's
    actual 62 quests, same as command_reward() above - every gate quest
    deliberately does NOT grant tiers this way: ProgressiveStages' own
    triggers do that, and this chapter is a read-only quest-book VIEW of
    tier progress."""
    return {"type": "gamestage", "stage": stage_id}


def toast_reward(message):
    """A distinguished announcement. Unused by this book's actual 62
    quests, same as the two reward builders above."""
    return {"type": "toast", "message": message}


# Coin denominations in spurs, largest first - copied verbatim from
# pack/kubejs/server_scripts/economy.js's own COINS table (Numismatics'
# Coin enum: spur=1, bevel=8, sprocket=16, cog=64, crown=512, sun=4096).
COINS = [
    ("numismatics:sun", 4096),
    ("numismatics:crown", 512),
    ("numismatics:cog", 64),
    ("numismatics:sprocket", 16),
    ("numismatics:bevel", 8),
    ("numismatics:spur", 1),
]


def spur_rewards(total_spurs):
    """Break a spur total into the largest-denomination coin ITEM rewards
    that fit, mirroring economy.js's own payCoins() greedy algorithm - a
    quest reward of e.g. 1024 spurs shows up as a single Sun coin, not 1024
    individual Spur items."""
    rewards = []
    remaining = total_spurs
    for item_id, value in COINS:
        count = remaining // value
        if count > 0:
            rewards.append(item_reward(item_id, count))
            remaining -= count * value
    return rewards


# ---------------------------------------------------------------------------
# Quest/chapter builders.
# ---------------------------------------------------------------------------
def make_quest(quests_list, chapter_id, slug, title, tasks, rewards,
                dependencies=None, desc=None, quest_icon=None):
    qid = f"{chapter_id}__{slug}"
    q = {
        "id": qid,
        "title": title,
        "desc": list(desc) if desc else [],
        "icon": quest_icon,
        "dependencies": list(dependencies) if dependencies else [],
        "tasks": tasks,
        "rewards": rewards,
    }
    quests_list.append(q)
    return qid


def make_chapter(chapter_id, title, subtitle_lines, quests_builder_fn, order_index,
                  chapter_icon=None):
    quests = []
    quests_builder_fn(quests, chapter_id)
    return {
        "id": chapter_id,
        "title": title,
        "subtitle": list(subtitle_lines) if subtitle_lines else [],
        "icon": chapter_icon,
        "order": order_index,
        "quests": quests,
    }


# ---------------------------------------------------------------------------
# Reward-budget tables.
# ---------------------------------------------------------------------------
# index: 0 rootborn, 1 andesite, 2 brass, 3 precision, 4 induction, 5 starforged,
#        6 lunar, 7 martian, 8 inner_system, 9 jovian
GATE_SPURS = [2, 4, 16, 64, 256, 1024, 1024, 1152, 1280, 1536]
GATE_XP =    [20, 80, 150, 300, 600, 1200, 1500, 1800, 2100, 2400]
# intra-tier walkthrough quests: modest fraction of the SAME tier's gate budget
SIDE_SPURS = [1, 2, 4, 16, 64, 256, 256, 320, 384, 448]
SIDE_XP =    [10, 30, 50, 90, 150, 100, 150, 180, 200, 250]


# ===========================================================================
# Chapter 0 - Rootborn (starter chapter).
# ===========================================================================
ROOTBORN_Q = {}


def build_rootborn(quests, cid):
    welcome = make_quest(
        quests, cid, "welcome", "Welcome to Vanilla++",
        desc=["Punch some trees, then check this book after every tier-up - "
              "each chapter is a checklist for that tier's real progression."],
        tasks=[checkmark_task()],
        rewards=[skill_xp_reward("adventurer", 10)],
        quest_icon="minecraft:crafting_table",
    )
    stone_age = make_quest(
        quests, cid, "stone_age", "Stone Age",
        desc=["Craft your first pickaxe through Silent Gear (any material) - "
              "the first real tool upgrade."],
        tasks=[item_task("silentgear:pickaxe", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[0])],
        dependencies=[welcome],
        quest_icon="minecraft:stone_pickaxe",
    )
    first_hunt = make_quest(
        quests, cid, "first_hunt", "First Blood",
        desc=["Kill a zombie. Combat matters from here on - Swords XP feeds "
              "directly into the RPG skill tree."],
        tasks=[kill_task("minecraft:zombie", 1)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[0])],
        dependencies=[welcome],
        quest_icon="minecraft:iron_sword",
    )
    gather_andesite = make_quest(
        quests, cid, "gather_andesite", "Into Create's Material Chain",
        desc=["Craft or pick up Andesite Alloy - Create's own entry material, "
              "and the trigger for Andesite Age."],
        tasks=[item_task("create:andesite_alloy", only_from_crafting=True)],
        rewards=[*spur_rewards(GATE_SPURS[0]), skill_xp_reward("adventurer", GATE_XP[0])],
        dependencies=[stone_age, first_hunt],
        quest_icon="create:andesite_alloy",
    )
    ROOTBORN_Q["gather_andesite"] = gather_andesite


# ===========================================================================
# Chapter 1 - Andesite Age (Tier 1).
# ===========================================================================
ANDESITE_Q = {}


def build_andesite(quests, cid):
    enter = make_quest(
        quests, cid, "enter", "Enter the Andesite Age",
        desc=["Iron tools and Create's own machinery are open. This chapter "
              "is your Andesite Age checklist."],
        tasks=[stage_task("andesite_age")],
        rewards=[skill_xp_reward("adventurer", GATE_XP[1]), item_reward("create:andesite_alloy")],
        dependencies=[ROOTBORN_Q["gather_andesite"]],
        quest_icon="create:andesite_alloy",
    )
    iron_tools = make_quest(
        quests, cid, "iron_tools", "Iron Tools",
        desc=["Craft another Silent Gear pickaxe with this tier's material - "
              "the real mining-speed upgrade this tier unlocks."],
        tasks=[item_task("silentgear:pickaxe", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[1]), *spur_rewards(SIDE_SPURS[1])],
        dependencies=[enter], quest_icon="minecraft:iron_pickaxe",
    )
    dumb_storage = make_quest(
        quests, cid, "dumb_storage", "Dumb Storage",
        desc=["Craft a Tom's Storage Inventory Connector - link your chests "
              "into one browsable network. No power, no autocrafting yet."],
        tasks=[item_task("toms_storage:inventory_connector", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[1]), *spur_rewards(SIDE_SPURS[1])],
        dependencies=[enter], quest_icon="toms_storage:inventory_connector",
    )
    jetpack_1 = make_quest(
        quests, cid, "jetpack_1", "Copper Jetpack",
        desc=["Craft the Copper Jetpack - the first rung of the personal "
              "mobility ladder (Create Stuff & Additions)."],
        tasks=[item_task("create_sa:copper_jetpack_chestplate", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[1]), *spur_rewards(SIDE_SPURS[1])],
        dependencies=[enter], quest_icon="create_sa:copper_jetpack_chestplate",
    )
    chunk_loader_1 = make_quest(
        quests, cid, "chunk_loader_1", "Andesite Chunk Loader",
        desc=["Craft the Andesite Chunk Loader (Create: Power Loader). It "
              "only force-loads chunks while spun under real kinetic power."],
        tasks=[item_task("create_power_loader:andesite_chunk_loader", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[1]), *spur_rewards(SIDE_SPURS[1])],
        dependencies=[enter], quest_icon="create_power_loader:andesite_chunk_loader",
    )
    vein_hunting = make_quest(
        quests, cid, "vein_hunting", "Vein Hunting",
        desc=["Craft a Vein Finder (Create Ore Excavation) - the entry-level "
              "scouting tool for this pack's ore-vein system."],
        tasks=[item_task("createoreexcavation:vein_finder", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[1]), *spur_rewards(SIDE_SPURS[1])],
        dependencies=[enter], quest_icon="createoreexcavation:vein_finder",
    )
    ars_wand = make_quest(
        quests, cid, "ars_wand", "The Mage's Path",
        desc=["Craft an Ars Nouveau wand - the entry point into this pack's "
              "spell-crafting magic system."],
        tasks=[item_task("ars_nouveau:wand", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[1]), *spur_rewards(SIDE_SPURS[1])],
        dependencies=[enter], quest_icon="ars_nouveau:wand",
    )
    make_quest(
        quests, cid, "curious_find", "A Curious Find (optional)",
        desc=["Find any Artifacts curio - they're pure exploration payoffs "
              "with no tier lock, hidden in structure loot at every rarity "
              "tier. This one just confirms you've found the umbrella."],
        tasks=[item_task("artifacts:umbrella", consume_items=False, only_from_crafting=False)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[1])],
        dependencies=[enter], quest_icon="artifacts:umbrella",
    )
    into_brass = make_quest(
        quests, cid, "into_brass", "Into the Brass Age",
        desc=["Craft or pick up a Brass Ingot - Create's mid-game alloy, and "
              "the trigger for Brass Age."],
        tasks=[item_task("create:brass_ingot", only_from_crafting=True)],
        rewards=[*spur_rewards(GATE_SPURS[1]), skill_xp_reward("adventurer", GATE_XP[1])],
        dependencies=[iron_tools, dumb_storage, jetpack_1, chunk_loader_1, vein_hunting, ars_wand],
        quest_icon="create:brass_ingot",
    )
    ANDESITE_Q["into_brass"] = into_brass


# ===========================================================================
# Chapter 2 - Brass Age (Tier 2).
# ===========================================================================
BRASS_Q = {}


def build_brass(quests, cid):
    enter = make_quest(
        quests, cid, "enter", "Enter the Brass Age",
        desc=["Automation begins in earnest. Diamond gear, the Nether, and a "
              "real powered storage network are all open now."],
        tasks=[stage_task("brass_age")],
        rewards=[skill_xp_reward("adventurer", GATE_XP[2]), item_reward("create:brass_ingot")],
        dependencies=[ANDESITE_Q["into_brass"]],
        quest_icon="create:brass_ingot",
    )
    diamond_gear = make_quest(
        quests, cid, "diamond_gear", "Diamond Gear",
        desc=["Craft another Silent Gear pickaxe with Brass Age's material - "
              "the tool-tier milestone for this age."],
        tasks=[item_task("silentgear:pickaxe", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="minecraft:diamond_pickaxe",
    )
    real_network = make_quest(
        quests, cid, "real_network", "A Real Network",
        desc=["Craft a Refined Storage Controller - the heart of the powered "
              "network that replaces Tom's Storage from here on."],
        tasks=[item_task("refinedstorage:controller", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="refinedstorage:controller",
    )
    alternator = make_quest(
        quests, cid, "alternator", "Power the Network",
        desc=["Craft a Create Crafts & Additions Alternator - turns Create's "
              "own rotational power into the FE that runs Refined Storage."],
        tasks=[item_task("createaddition:alternator", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="createaddition:alternator",
    )
    automation_arm = make_quest(
        quests, cid, "automation_arm", "First Automation",
        desc=["Craft a Mechanical Arm - Create's own first crafting-automation "
              "block, feeding Refined Storage's Importer/Exporter."],
        tasks=[item_task("create:mechanical_arm", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="create:mechanical_arm",
    )
    jetpack_2 = make_quest(
        quests, cid, "jetpack_2", "Andesite Jetpack",
        desc=["Craft the Andesite Jetpack - fuel-fired propellers, rung 2 of "
              "the mobility ladder."],
        tasks=[item_task("create_sa:andesite_jetpack_chestplate", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="create_sa:andesite_jetpack_chestplate",
    )
    chunk_loader_2 = make_quest(
        quests, cid, "chunk_loader_2", "Brass Chunk Loader",
        desc=["Craft the Brass Chunk Loader - the second and final Power "
              "Loader rung."],
        tasks=[item_task("create_power_loader:brass_chunk_loader", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="create_power_loader:brass_chunk_loader",
    )
    tiab = make_quest(
        quests, cid, "tiab", "Time in a Bottle",
        desc=["Craft the Time in a Bottle tick accelerator - one per player, "
              "and it won't speed up spawners."],
        tasks=[item_task("tiab:time_in_a_bottle", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="tiab:time_in_a_bottle",
    )
    trains = make_quest(
        quests, cid, "trains", "Train Control",
        desc=["Craft a Track Station - Create's own Trains are a full Brass "
              "Age package now."],
        tasks=[item_task("create:track_station", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="create:track_station",
    )
    diet_upgrade = make_quest(
        quests, cid, "diet_upgrade", "Sharper Knives",
        desc=["Craft a Farmer's Delight diamond knife - this is the real "
              "tier this pack's food-diet knife line reaches Brass Age "
              "(gold/diamond both unlock here; iron was Andesite Age, "
              "netherite is Precision Age)."],
        tasks=[item_task("farmersdelight:diamond_knife", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="farmersdelight:diamond_knife",
    )
    master_alloy = make_quest(
        quests, cid, "master_alloy", "The Master Alloy",
        desc=["Craft a Sturdy Sheet from Refined Radiance or Shadow Steel - "
              "Create's own top-tier alloy, and the door to Precision Age."],
        tasks=[item_task("create:sturdy_sheet", only_from_crafting=True)],
        rewards=[*spur_rewards(GATE_SPURS[2]), skill_xp_reward("adventurer", GATE_XP[2])],
        dependencies=[diamond_gear, real_network, alternator, automation_arm,
                      jetpack_2, chunk_loader_2, tiab, trains, diet_upgrade],
        quest_icon="create:sturdy_sheet",
    )
    BRASS_Q["master_alloy"] = master_alloy


# ===========================================================================
# Chapter 3 - Precision Age (Tier 3).
# ===========================================================================
PRECISION_Q = {}


def build_precision(quests, cid):
    enter = make_quest(
        quests, cid, "enter", "Enter the Precision Age",
        desc=["Create's own endgame alloys are done. Netherite gear and The "
              "End are open."],
        tasks=[stage_task("precision_age")],
        rewards=[skill_xp_reward("adventurer", GATE_XP[3]), item_reward("create:sturdy_sheet")],
        dependencies=[BRASS_Q["master_alloy"]],
        quest_icon="create:sturdy_sheet",
    )
    netherite_gear = make_quest(
        quests, cid, "netherite_gear", "Netherite Gear",
        desc=["Craft another Silent Gear pickaxe with Precision Age's material - "
              "the tool-tier milestone for this age."],
        tasks=[item_task("silentgear:pickaxe", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[3]), *spur_rewards(SIDE_SPURS[3])],
        dependencies=[enter], quest_icon="minecraft:netherite_pickaxe",
    )
    wireless = make_quest(
        quests, cid, "wireless", "Cut the Cables",
        desc=["Craft a Wireless Grid - manage your Refined Storage network "
              "from anywhere in range."],
        tasks=[item_task("refinedstorage:wireless_grid", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[3]), *spur_rewards(SIDE_SPURS[3])],
        dependencies=[enter], quest_icon="refinedstorage:wireless_grid",
    )
    jetpack_3 = make_quest(
        quests, cid, "jetpack_3", "Brass Jetpack",
        desc=["Craft the Brass Jetpack - steam-fired, rung 3 of the mobility "
              "ladder, and the base item the Induction Age netherite jetpack "
              "smiths from."],
        tasks=[item_task("create_sa:brass_jetpack_chestplate", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[3]), *spur_rewards(SIDE_SPURS[3])],
        dependencies=[enter], quest_icon="create_sa:brass_jetpack_chestplate",
    )
    elytra = make_quest(
        quests, cid, "elytra", "Wings",
        desc=["Find an Elytra in an End City - it's not craftable, just "
              "gated behind reaching this tier and finding one."],
        tasks=[item_task("minecraft:elytra", consume_items=False, only_from_crafting=False)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[3]), *spur_rewards(SIDE_SPURS[3])],
        dependencies=[enter], quest_icon="minecraft:elytra",
    )
    diet_upgrade = make_quest(
        quests, cid, "diet_upgrade", "The Netherite Knife",
        desc=["Craft a Farmer's Delight netherite knife (a smithing upgrade "
              "from the diamond knife) - the ceiling of this pack's food-"
              "diet knife line, keeping your bonus-hearts diet variety topped "
              "up through Precision Age's grind."],
        tasks=[item_task("farmersdelight:netherite_knife", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[3]), *spur_rewards(SIDE_SPURS[3])],
        dependencies=[enter], quest_icon="farmersdelight:netherite_knife",
    )
    vein_ceiling = make_quest(
        quests, cid, "vein_ceiling", "The Netherite Drill",
        desc=["Craft the Netherite Drill - Create Ore Excavation's own tool "
              "ceiling, and what it takes to pull allthemodium/vibranium/"
              "unobtainium out of the ground."],
        tasks=[item_task("createoreexcavation:netherite_drill", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[3]), *spur_rewards(SIDE_SPURS[3])],
        dependencies=[enter], quest_icon="createoreexcavation:netherite_drill",
    )
    final_ingot = make_quest(
        quests, cid, "final_ingot", "The Final Ingot",
        desc=["Craft or pick up a Netherite Ingot - the temporary trigger for "
              "Induction Age, until a real narrative trigger replaces it."],
        tasks=[item_task("minecraft:netherite_ingot", only_from_crafting=True)],
        rewards=[*spur_rewards(GATE_SPURS[3]), skill_xp_reward("adventurer", GATE_XP[3])],
        dependencies=[netherite_gear, wireless, jetpack_3, elytra, diet_upgrade, vein_ceiling],
        quest_icon="minecraft:netherite_ingot",
    )
    PRECISION_Q["final_ingot"] = final_ingot


# ===========================================================================
# Chapter 4 - Induction Age (Tier 4).
# ===========================================================================
INDUCTION_Q = {}


def build_induction(quests, cid):
    enter = make_quest(
        quests, cid, "enter", "Enter the Induction Age",
        desc=["Full storage-network automation: 64k capacity and native "
              "pattern-based autocrafting are online."],
        tasks=[stage_task("induction_age")],
        rewards=[skill_xp_reward("adventurer", GATE_XP[4]), item_reward("minecraft:netherite_ingot")],
        dependencies=[PRECISION_Q["final_ingot"]],
        quest_icon="minecraft:netherite_ingot",
    )
    autocrafting = make_quest(
        quests, cid, "autocrafting", "Native Autocrafting",
        desc=["Craft an Autocrafting Upgrade - Refined Storage's own "
              "pattern-based autocrafter, no more Mechanical Arm needed for "
              "storage automation."],
        tasks=[item_task("refinedstorage:autocrafting_upgrade", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[4]), *spur_rewards(SIDE_SPURS[4])],
        dependencies=[enter], quest_icon="refinedstorage:autocrafting_upgrade",
    )
    storage_ceiling = make_quest(
        quests, cid, "storage_ceiling", "64k Storage",
        desc=["Craft a 64k Storage Part - the ceiling of this pack's Refined "
              "Storage capacity chase (until the Jovian Frontier capstone)."],
        tasks=[item_task("refinedstorage:64k_storage_part", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[4]), *spur_rewards(SIDE_SPURS[4])],
        dependencies=[enter], quest_icon="refinedstorage:64k_storage_part",
    )
    jetpack_ceiling = make_quest(
        quests, cid, "jetpack_ceiling", "Netherite Jetpack",
        desc=["Craft the Netherite Jetpack - the final rung before "
              "Starforged Age grants true persistent flight outright."],
        tasks=[item_task("create_sa:netherite_jetpack_chestplate", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[4]), *spur_rewards(SIDE_SPURS[4])],
        dependencies=[enter], quest_icon="create_sa:netherite_jetpack_chestplate",
    )
    teleport = make_quest(
        quests, cid, "teleport", "Teleportation",
        desc=["Craft a Waystone - intra-world teleportation, gated all the "
              "way to this tier on purpose."],
        tasks=[item_task("waystones:waystone", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[4]), *spur_rewards(SIDE_SPURS[4])],
        dependencies=[enter], quest_icon="waystones:waystone",
    )
    steam_flight = make_quest(
        quests, cid, "steam_flight", "Steam-Powered Flight",
        desc=["Craft a Steam Vent (Create Aeronautics) - the passive, "
              "industrial-scale heat source for sustained airship lift."],
        tasks=[item_task("aeronautics:steam_vent", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[4]), *spur_rewards(SIDE_SPURS[4])],
        dependencies=[enter], quest_icon="aeronautics:steam_vent",
    )
    gear_ceiling = make_quest(
        quests, cid, "gear_ceiling", "Allthemodium",
        desc=["Smelt an Allthemodium Ingot - this pack's own post-netherite "
              "Silent Gear material floor, carrying gear progression into "
              "the space tiers."],
        tasks=[item_task("allthemodium:allthemodium_ingot", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[4]), *spur_rewards(SIDE_SPURS[4])],
        dependencies=[enter], quest_icon="allthemodium:allthemodium_ingot",
    )
    dragon = make_quest(
        quests, cid, "dragon", "Conquer the End",
        desc=["Kill the Ender Dragon. The overworld, Nether, and End are "
              "done - this is the real trigger for Starforged Age."],
        tasks=[kill_task("minecraft:ender_dragon", 1)],
        rewards=[*spur_rewards(GATE_SPURS[4]), skill_xp_reward("adventurer", GATE_XP[4])],
        dependencies=[autocrafting, storage_ceiling, jetpack_ceiling, teleport,
                      steam_flight, gear_ceiling],
        quest_icon="minecraft:dragon_head",
    )
    INDUCTION_Q["dragon"] = dragon


# ===========================================================================
# Chapter 5 - Starforged Age (Tier 5).
# ===========================================================================
STARFORGED_Q = {}


def build_starforged(quests, cid):
    enter = make_quest(
        quests, cid, "enter", "Enter the Starforged Age",
        desc=["The overworld, Nether, and End are conquered. Space travel "
              "begins - and you can now toggle persistent flight outright."],
        tasks=[stage_task("starforged_age")],
        rewards=[skill_xp_reward("adventurer", GATE_XP[5]), item_reward("minecraft:nether_star")],
        dependencies=[INDUCTION_Q["dragon"]],
        quest_icon="minecraft:nether_star",
    )
    make_quest(
        quests, cid, "flight_ack", "True Flight",
        desc=["Double-tap jump to toggle flight - it's granted the instant "
              "you reached this tier, no item or fuel required, and it "
              "survives death."],
        tasks=[checkmark_task()],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[5])],
        dependencies=[enter], quest_icon="minecraft:elytra",
    )
    make_quest(
        quests, cid, "leaderboard_check", "Check Your Rank (optional)",
        desc=["Run /leaderboard wealth, /leaderboard tier, or /leaderboard "
              "level to see how you and your team stack up."],
        tasks=[checkmark_task()],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[5])],
        dependencies=[enter], quest_icon="numismatics:sun",
    )
    aluminum_age = make_quest(
        quests, cid, "aluminum_age", "The Aluminum Age",
        desc=["Smelt a TFMG Aluminum Ingot - the first rung of the endgame "
              "automation ladder that carries all the way to Jupiter."],
        tasks=[item_task("tfmg:aluminum_ingot", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[5]), *spur_rewards(SIDE_SPURS[5])],
        dependencies=[enter], quest_icon="tfmg:aluminum_ingot",
    )
    rocket_parts = make_quest(
        quests, cid, "rocket_parts", "Rocket Parts",
        desc=["Craft a Rocket Engine (Stellaris) - one of the core "
              "components of your first rocket."],
        tasks=[item_task("stellaris:rocket_engine", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[5]), *spur_rewards(SIDE_SPURS[5])],
        dependencies=[aluminum_age], quest_icon="stellaris:rocket_engine",
    )
    launch = make_quest(
        quests, cid, "launch", "Liftoff",
        desc=["Launch your rocket and reach Earth orbit - the real trigger "
              "for Lunar Frontier."],
        tasks=[dimension_task("stellaris:earth_orbit")],
        rewards=[*spur_rewards(GATE_SPURS[5]), skill_xp_reward("adventurer", GATE_XP[5])],
        dependencies=[rocket_parts],
        quest_icon="stellaris:rocket",
    )
    STARFORGED_Q["launch"] = launch


# ===========================================================================
# Chapter 6 - Lunar Frontier (Tier 6).
# ===========================================================================
LUNAR_Q = {}


def build_lunar(quests, cid):
    enter = make_quest(
        quests, cid, "enter", "Enter the Lunar Frontier",
        desc=["You've reached orbit. The Moon is next."],
        tasks=[stage_task("lunar_frontier")],
        rewards=[skill_xp_reward("adventurer", GATE_XP[6]), item_reward("allthemodium:unobtainium_ingot")],
        dependencies=[STARFORGED_Q["launch"]],
        quest_icon="stellaris:rocket",
    )
    steel_age = make_quest(
        quests, cid, "steel_age", "The Steel Age",
        desc=["Smelt a TFMG Steel Ingot - the mod's own core metallurgy "
              "chain, rung 2 of the endgame automation ladder."],
        tasks=[item_task("tfmg:steel_ingot", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[6]), *spur_rewards(SIDE_SPURS[6])],
        dependencies=[enter], quest_icon="tfmg:steel_ingot",
    )
    moon_landing = make_quest(
        quests, cid, "moon_landing", "One Small Step",
        desc=["Travel to the Moon - the real trigger for Martian Frontier."],
        tasks=[dimension_task("stellaris:moon")],
        rewards=[*spur_rewards(GATE_SPURS[6]), skill_xp_reward("adventurer", GATE_XP[6])],
        dependencies=[steel_age], quest_icon="minecraft:end_crystal",
    )
    LUNAR_Q["moon_landing"] = moon_landing


# ===========================================================================
# Chapter 7 - Martian Frontier (Tier 7).
# ===========================================================================
MARTIAN_Q = {}


def build_martian(quests, cid):
    enter = make_quest(
        quests, cid, "enter", "Enter the Martian Frontier",
        desc=["The Moon is conquered. Mars is next."],
        tasks=[stage_task("martian_frontier")],
        rewards=[skill_xp_reward("adventurer", GATE_XP[7]), item_reward("tfmg:diesel_bucket")],
        dependencies=[LUNAR_Q["moon_landing"]],
        quest_icon="minecraft:redstone",
    )
    petrochemical = make_quest(
        quests, cid, "petrochemical", "The Petrochemical Age",
        desc=["Refine a bucket of Diesel (TFMG) - rung 3 of the endgame "
              "automation ladder."],
        tasks=[item_task("tfmg:diesel_bucket", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[7]), *spur_rewards(SIDE_SPURS[7])],
        dependencies=[enter], quest_icon="tfmg:diesel_bucket",
    )
    mars_landing = make_quest(
        quests, cid, "mars_landing", "Red Planet",
        desc=["Travel to Mars - the real trigger for Inner System."],
        tasks=[dimension_task("stellaris:mars")],
        rewards=[*spur_rewards(GATE_SPURS[7]), skill_xp_reward("adventurer", GATE_XP[7])],
        dependencies=[petrochemical], quest_icon="minecraft:redstone_block",
    )
    MARTIAN_Q["mars_landing"] = mars_landing


# ===========================================================================
# Chapter 8 - Inner System (Tier 8).
# ===========================================================================
INNER_Q = {}


def build_inner(quests, cid):
    enter = make_quest(
        quests, cid, "enter", "Enter the Inner System",
        desc=["Mars is conquered. Venus and Mercury - both extreme, "
              "comparably hostile - are next."],
        tasks=[stage_task("inner_system")],
        rewards=[skill_xp_reward("adventurer", GATE_XP[8]), item_reward("tfmg:electric_motor")],
        dependencies=[MARTIAN_Q["mars_landing"]],
        quest_icon="minecraft:magma_block",
    )
    electrical_age = make_quest(
        quests, cid, "electrical_age", "The Electrical Age",
        desc=["Craft a TFMG Converter - bridges TFMG's own power grid into "
              "Create/FE, rung 4 of the endgame automation ladder."],
        tasks=[item_task("tfmg:converter", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[8]), *spur_rewards(SIDE_SPURS[8])],
        dependencies=[enter], quest_icon="tfmg:converter",
    )
    make_quest(
        quests, cid, "venus_landing", "Morning Star (optional)",
        desc=["Travel to Venus - either inner planet triggers Jovian "
              "Frontier, so this and Mercury are both optional."],
        tasks=[dimension_task("stellaris:venus")],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[8]), *spur_rewards(SIDE_SPURS[8])],
        dependencies=[electrical_age], quest_icon="minecraft:magma_block",
    )
    make_quest(
        quests, cid, "mercury_landing", "Swift Planet (optional)",
        desc=["Travel to Mercury - either inner planet triggers Jovian "
              "Frontier, so this and Venus are both optional."],
        tasks=[dimension_task("stellaris:mercury")],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[8]), *spur_rewards(SIDE_SPURS[8])],
        dependencies=[electrical_age], quest_icon="minecraft:magma_block",
    )
    INNER_Q["electrical_age"] = electrical_age


# ===========================================================================
# Chapter 9 - Jovian Frontier (Tier 9, final).
# ===========================================================================
def build_jovian(quests, cid):
    enter = make_quest(
        quests, cid, "enter", "Enter the Jovian Frontier",
        desc=["The inner system is conquered. Jupiter - the current edge of "
              "Stellaris' explorable system - is the final frontier."],
        tasks=[stage_task("jovian_frontier")],
        rewards=[skill_xp_reward("adventurer", GATE_XP[9]),
                 item_reward("allthemodium:unobtainium_vibranium_alloy_ingot")],
        dependencies=[INNER_Q["electrical_age"]],
        quest_icon="minecraft:end_crystal",
    )
    combustion_age = make_quest(
        quests, cid, "combustion_age", "The Combustion Age",
        desc=["Craft a TFMG Engine Cylinder - the final rung of the endgame "
              "automation ladder."],
        tasks=[item_task("tfmg:engine_cylinder", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[9]), *spur_rewards(SIDE_SPURS[9])],
        dependencies=[enter], quest_icon="tfmg:engine_cylinder",
    )
    storage_infinity = make_quest(
        quests, cid, "storage_infinity", "Infinite Storage",
        desc=["Craft a Refined Storage Creative Storage Block - genuinely "
              "infinite item capacity, the true ceiling of the storage "
              "chase started back at Andesite Age."],
        tasks=[item_task("refinedstorage:creative_storage_block", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[9] + 50), *spur_rewards(SIDE_SPURS[9])],
        dependencies=[combustion_age], quest_icon="refinedstorage:creative_storage_block",
    )
    energy_infinity = make_quest(
        quests, cid, "energy_infinity", "Infinite Energy",
        desc=["Craft a Create Creative Motor - a genuinely endless source of "
              "Rotational Force, bridged to FE the same way every earlier "
              "power step in this pack has been."],
        tasks=[item_task("create:creative_motor", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[9] + 50), *spur_rewards(SIDE_SPURS[9])],
        dependencies=[combustion_age], quest_icon="create:creative_motor",
    )
    resource_infinity = make_quest(
        quests, cid, "resource_infinity", "Infinite Resources",
        desc=["Craft a Create Creative Crate - an endless supply of any one "
              "item you configure. This is the hardest, latest-gated craft "
              "in the entire pack for a reason - guard it accordingly."],
        tasks=[item_task("create:creative_crate", only_from_crafting=True)],
        rewards=[skill_xp_reward("adventurer", SIDE_XP[9] + 50), *spur_rewards(SIDE_SPURS[9])],
        dependencies=[combustion_age], quest_icon="create:creative_crate",
    )
    make_quest(
        quests, cid, "journeys_end", "Journey's End",
        desc=["Every tier from Rootborn to Jupiter, done. Future updates may "
              "extend the ladder further out into the solar system - this "
              "book will grow to meet them."],
        tasks=[checkmark_task()],
        rewards=[*spur_rewards(GATE_SPURS[9]), skill_xp_reward("adventurer", GATE_XP[9])],
        dependencies=[storage_infinity, energy_infinity, resource_infinity],
        quest_icon="minecraft:nether_star",
    )


CHAPTER_DEFS = [
    ("rootborn", "Rootborn", ["The world is still just the world - for now."],
     build_rootborn, "minecraft:stone_pickaxe"),
    ("andesite_age", "Andesite Age", ["Iron enters the world. Create's own machinery begins."],
     build_andesite, "create:andesite_alloy"),
    ("brass_age", "Brass Age", ["Automation begins in earnest."],
     build_brass, "create:brass_ingot"),
    ("precision_age", "Precision Age", ["Create's own endgame alloys, and netherite gear."],
     build_precision, "create:sturdy_sheet"),
    ("induction_age", "Induction Age", ["Full storage-network automation."],
     build_induction, "refinedstorage:advanced_processor"),
    ("starforged_age", "Starforged Age", ["The overworld, Nether, and End are conquered. Space travel begins."],
     build_starforged, "minecraft:nether_star"),
    ("lunar_frontier", "Lunar Frontier", ["You've reached orbit. The Moon is next."],
     build_lunar, "stellaris:rocket"),
    ("martian_frontier", "Martian Frontier", ["The Moon is conquered. Mars is next."],
     build_martian, "minecraft:redstone"),
    ("inner_system", "Inner System", ["Mars is conquered. Venus and Mercury are next."],
     build_inner, "minecraft:magma_block"),
    ("jovian_frontier", "Jovian Frontier", ["The inner system is conquered. Jupiter is the final frontier."],
     build_jovian, "minecraft:end_crystal"),
]


def legacy_id_to_path(legacy_id):
    """"<chapter>__<slug>" -> "<chapter>/<slug>" - see module docstring's
    "IDENTITY-STYLE ID MAPPING" section for why this split is safe."""
    chapter_id, slug = legacy_id.split("__", 1)
    return f"{chapter_id}/{slug}"


def quest_frame(quest):
    if quest["id"] in CHALLENGE_QUEST_IDS:
        return "challenge"
    if any(t["type"] == "gamestage" for t in quest["tasks"]):
        return "goal"
    return "task"


def convert_task(task):
    # Task dict shapes are already identical to QuestTask.fromJson()'s
    # expected fields - passed through unchanged.
    return dict(task)


def convert_reward(reward):
    # Same for rewards - QuestReward.fromJson() expects the exact fields
    # the builders above already emit.
    return dict(reward)


def convert_quest(quest, chapter_id):
    path = legacy_id_to_path(quest["id"])
    _, slug = path.split("/", 1)
    frame = quest_frame(quest)
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
    for i, (chapter_id, title, subtitle, builder, chap_icon) in enumerate(CHAPTER_DEFS):
        chapter = make_chapter(chapter_id, title, subtitle, builder, order_index=i, chapter_icon=chap_icon)
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
