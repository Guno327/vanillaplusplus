#!/usr/bin/env python3
"""GitHub issue #33 ("Replace FTB Quests with a bespoke quest system") -
full rewrite of the quest book generator: was pack/config/ftbquests/quests/
(FTB Quests SNBT), now pack/kubejs/server_scripts/quests.js (plain KubeJS).

WHY: FTB Quests (2101.1.27) is CurseForge-exclusive - this project has no
redistribution permission for it (see DESIGN.md's Phase 4 section for the
original CurseForge-CDN resolution workaround, which was always a stopgap,
not a rights grant). Scale of the existing content is preserved exactly:
10 chapters, 62 quests, ~87 dependency edges - see scripts/ci/check_quests.py
for the counts this generator is expected to reproduce. Every chapter/quest/
task/reward/dependency below is a verbatim carry-over of the previous
scripts/gen_quests.py's actual content (item ids, entity ids, dimension ids,
xp/spur amounts, dependency wiring) - only the OUTPUT FORMAT changed, from
FTB Quests' SNBT grammar to a plain JS data table + a hand-written KubeJS
runtime that ticks/tracks/rewards it directly. See DESIGN.md's "Quest
system (Phase 4)" and "Quest-book overhaul" sections, and this repo's
pack/manifest.json ftb-quests entry note ("Tier Progression preset-track
chapter"), for the design history this book is replacing.

PRECEDENT this generator follows (same shape as the two chapters Phase 6
already moved out of FTB Quests for an unrelated reason - see
scripts/gen_achievements.py's own docstring): a Python generator writes a
KubeJS server script that ticks (ServerEvents.tick), tracks progress in
persistentData, and grants rewards directly via command execution / KubeJS
bindings, plus a player.tell() chat notification. No GUI, no separate mod
dependency - chat commands only (/quests, /quests <chapter>, /quest check
<id>), matching this pack's established leaderboard.js/economy.js/
dailies.js UX convention.

TEAM-SHARED PROGRESS, PER-PLAYER REWARDS (instructions.md line 41: "Players
should share progress (but not rewards) for preset track quests"). This
book IS the preset track (DESIGN.md's "Tier Progression" chapter, later
expanded 1 chapter/tier), so quest COMPLETION state is stored keyed by
team/party id (see quests.js's getProgressKey() - falls back to a per-player
key for solo players) so any teammate satisfying a quest's tasks marks it
done for the whole team (unlocking dependents for everyone) - but the
REWARD grant (items/xp/commands) goes ONLY to the player whose live state
actually satisfied the task at the moment the tick scan (or /quest check)
fired, never broadcast to the rest of the team. This is a literal
requirement, not a judgment call - flagged here because it's easy to
misread "team-shared" as "team-shared rewards too" (the opposite of what
was asked), and because Phase 4's own FTB-Quests-era open issue (DESIGN.md)
was about exactly this per-progress-type granularity problem.

PARTY-ID SEAM (GitHub #32, landed and integrated alongside this issue at
merge time): party ids come from Open Parties and Claims
(xaero.pac.common.server.api.OpenPACServerAPI - FTB Teams and FTB Chunks
are both fully removed, along with FTB Library once they were its only
remaining consumers, see #32's own PR for the full evidence trail).
quests.js's getProgressKey() was written as the ONE function that seam
needed to change - every other function in the file keys exclusively off
the string it returns, so integrating #32 was a one-function edit, not a
redesign, exactly as planned when this generator was first written.
Ground truth: xaero.pac...IPartyManagerAPI.getPartyByMember(UUID) ->
IServerPartyAPI (@Nullable); IServerPartyAPI.getId() -> UUID - confirmed by
reading the real interface source, decompiled from the actually-resolved
open-parties-and-claims-neoforge-1.21.1-0.27.8.jar's Modrinth-published
sources jar.

MOD REMOVAL - ftb-quests ONLY, NOT ftb-library (deviation from the issue's
literal "remove ftb-quests and ftb-library" instruction, ground-truthed,
not guessed): decompiling every installed mod's own META-INF/
neoforge.mods.toml (jar xf + read, PATH=.../jdk-21.0.11+10/bin) shows
ftb-teams-neoforge-2101.1.10.jar AND ftb-chunks-neoforge-2101.1.20.jar both
declare a "required" (not optional) dependency on ftblibrary >=2101.1.30.
Both of those mods stay installed (FTB Teams backs this file's own
progress-sharing seam above and ProgressiveStages' tier-stage sharing;
FTB Chunks is the pack's claims system and is entirely out of this issue's
scope) - removing ftb-library out from under them would hard-crash the
server at mod-loading time, not just leave the quest book broken.
ProgressiveStages' own dependency on ftbquests (progressivestages-2.1.jar's
neoforge.mods.toml) IS declared optional, so removing ftb-quests alone is
safe. See pack/manifest.json's ftb-library entry (its own note literally
says "required by FTB Teams and FTB Quests" - now stale in the "and FTB
Quests" half, updated alongside this change) and this issue's own PM-facing
summary for the full evidence trail.

REWARD-BUDGET POLICY carried over verbatim from the previous generator
(same anchoring to gen_economy.py's TIER_PRICE table, same late-game
disclosed-non-canonical extrapolation past Starforged Age, same "never
reward a creative/duplication-risk item" rule for the three Jovian
capstones) - see the GATE_SPURS/GATE_XP/SIDE_SPURS/SIDE_XP tables below for
the actual numbers, unchanged from the SNBT-era version.

DELIBERATE CONTENT-FIDELITY SIMPLIFICATIONS (disclosed, not silent - see
quests.js's own header comment for the runtime side of each):
  - only_from_crafting is preserved as descriptive metadata on item tasks
    (shown in /quests <chapter> output) but is NOT enforced as "must have
    been freshly crafted, not already held" the way FTB Quests' own
    crafting-event tracker did - the runtime checks "does the player
    currently hold >= N of this item", full stop. This mirrors an argument
    already made and boot-verified in this exact codebase
    (progression_stage_bridge.js's GitHub #23 fix: "does the player
    currently HOLD the item is a strictly more robust trigger condition
    than did we catch the one specific acquisition event") rather than
    inventing a new crafting-event hook this port has no way to boot-test.
  - Reward types item/xp are the only ones any of the 62 quests actually
    use (verbatim carry-over from the SNBT-era content - it never used
    FTB Quests' "gamestage" or "toast" reward types either). quests.js's
    runtime still implements "command" (arbitrary, {p}-templated, same
    convention FTB Quests itself used), "gamestage" (player.stages.add),
    and "toast" reward types for completeness/future content, since the
    issue text lists them as supported reward types - they're simply
    unexercised by this book's actual 62 quests, exactly as before.
  - Numeric hex quest/task/reward ids (FTB Quests' own id scheme) are
    replaced with human-readable string ids ("<chapter>__<slug>", e.g.
    "rootborn__welcome") - there is no SNBT id-uniqueness constraint to
    satisfy anymore, and readable ids make quests.js's generated data
    directly greppable/debuggable.
  - GUI grid (x, y) quest-map coordinates are dropped entirely - this port
    has no map GUI to place them on.
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # repo root
OUT_FILE = ROOT / "pack" / "kubejs" / "server_scripts" / "quests.js"
ADVANCEMENTS_DIR = ROOT / "pack" / "kubejs" / "data" / "vanillaplusplus" / "advancement" / "quests"

# GitHub #36: vanilla advancement tree as a free, no-new-mod GUI layer over
# the KubeJS quest tracker above - see this module's own advancement-writing
# code near main() for the full design rationale (ground-truthed against the
# real vanilla 1.21.1 client jar's own data/minecraft/advancement/*.json,
# not guessed: parent/criteria/display schema, the minecraft:impossible
# command-only-grant trick, and the display.background root-tab
# requirement). "challenge" frame for the four hardest, latest-gated quests;
# "goal" for every tier-gate quest (gamestage task); "task" for everything
# else - matches FTB Quests' own visual vocabulary this book used to use.
CHALLENGE_QUEST_IDS = {
    "jovian_frontier__storage_infinity",
    "jovian_frontier__energy_infinity",
    "jovian_frontier__resource_infinity",
    "jovian_frontier__journeys_end",
}
ADVANCEMENT_ROOT_BACKGROUND = "minecraft:textures/gui/advancements/backgrounds/stone.png"


# ---------------------------------------------------------------------------
# Task builders - dict shape consumed directly by quests.js's checkTask().
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
# Reward builders - dict shape consumed directly by quests.js's applyReward().
# ---------------------------------------------------------------------------
def item_reward(item_id, count=1):
    return {"type": "item", "item": item_id, "count": count}


def skill_xp_reward(category, amount):
    """puffish_skills XP reward. Previously an FTB Quests "command" reward
    templating `puffish_skills experience add {p} <category> <amount>`
    with permission_level 2 (FTB Quests ran reward commands AS the claiming
    player, needing the permission bump - net.puffish.skillsmod.commands.
    ExperienceCommand, confirmed via javap in the original SNBT-era
    generator). quests.js instead calls player.server.runCommandSilent(...)
    directly from the server's own command source (already full-permission,
    same proven pattern as achievements.js/dailies.js's identical
    puffish_skills calls) - no permission_level field needed, so this
    reward is now first-class "xp" rather than a disguised "command"."""
    return {"type": "xp", "category": category, "amount": amount}


def command_reward(command, silent=True):
    """Arbitrary command reward, {p} templated to the granting player's
    username at grant time (same convention FTB Quests itself used for its
    own command rewards). Unused by this book's actual 62 quests (verbatim
    carry-over from the SNBT-era content, which never used this either) -
    kept for parity with the issue's listed reward-type surface."""
    return {"type": "command", "command": command, "silent": silent}


def gamestage_reward(stage_id):
    """Grants a ProgressiveStages stage directly via player.stages.add().
    Unused by this book's actual 62 quests, same as command_reward() above -
    every gate quest deliberately does NOT grant tiers this way (see the
    build_* functions below): ProgressiveStages' own triggers do that, and
    this chapter is a read-only quest-book VIEW of tier progress, matching
    the original SNBT-era design intent verbatim."""
    return {"type": "gamestage", "stage": stage_id}


def toast_reward(message):
    """A distinguished chat announcement (no toast-popup GUI exists in a
    chat-command-only redesign - see quests.js's applyReward() for how this
    renders). Unused by this book's actual 62 quests, same as the two
    reward builders above."""
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
    that fit, exactly mirroring economy.js's own payCoins() greedy algorithm
    (and quests.js's own copy of the same algorithm) - a quest reward of
    e.g. 1024 spurs shows up as a single Sun coin, not 1024 individual Spur
    items. Deliberately never a "currency" reward type - Numismatics
    currency has always been granted as literal coin ITEMS in this pack,
    matching economy.js's own established convention (there is no
    registered FTB-style currency provider to hand this off to, and none is
    needed - see the SNBT-era generator's own now-removed note on this)."""
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
# Reward-budget tables (see module docstring for the full anchoring
# rationale) - unchanged from the SNBT-era generator.
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
        rewards=[skill_xp_reward("mining", 10)],
        quest_icon="minecraft:crafting_table",
    )
    stone_age = make_quest(
        quests, cid, "stone_age", "Stone Age",
        desc=["Craft your first pickaxe through Silent Gear (any material) - "
              "the first real tool upgrade."],
        tasks=[item_task("silentgear:pickaxe", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[0])],
        dependencies=[welcome],
        quest_icon="minecraft:stone_pickaxe",
    )
    first_hunt = make_quest(
        quests, cid, "first_hunt", "First Blood",
        desc=["Kill a zombie. Combat matters from here on - Swords XP feeds "
              "directly into the RPG skill tree."],
        tasks=[kill_task("minecraft:zombie", 1)],
        rewards=[skill_xp_reward("swords", SIDE_XP[0])],
        dependencies=[welcome],
        quest_icon="minecraft:iron_sword",
    )
    gather_andesite = make_quest(
        quests, cid, "gather_andesite", "Into Create's Material Chain",
        desc=["Craft or pick up Andesite Alloy - Create's own entry material, "
              "and the trigger for Andesite Age."],
        tasks=[item_task("create:andesite_alloy", only_from_crafting=True)],
        rewards=[*spur_rewards(GATE_SPURS[0]), skill_xp_reward("mining", GATE_XP[0])],
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
        rewards=[skill_xp_reward("mining", GATE_XP[1]), item_reward("create:andesite_alloy")],
        dependencies=[ROOTBORN_Q["gather_andesite"]],
        quest_icon="create:andesite_alloy",
    )
    iron_tools = make_quest(
        quests, cid, "iron_tools", "Iron Tools",
        desc=["Craft another Silent Gear pickaxe with this tier's material - "
              "the real mining-speed upgrade this tier unlocks."],
        tasks=[item_task("silentgear:pickaxe", only_from_crafting=True)],
        rewards=[skill_xp_reward("mining", SIDE_XP[1]), *spur_rewards(SIDE_SPURS[1])],
        dependencies=[enter], quest_icon="minecraft:iron_pickaxe",
    )
    dumb_storage = make_quest(
        quests, cid, "dumb_storage", "Dumb Storage",
        desc=["Craft a Tom's Storage Inventory Connector - link your chests "
              "into one browsable network. No power, no autocrafting yet."],
        tasks=[item_task("toms_storage:inventory_connector", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[1]), *spur_rewards(SIDE_SPURS[1])],
        dependencies=[enter], quest_icon="toms_storage:inventory_connector",
    )
    jetpack_1 = make_quest(
        quests, cid, "jetpack_1", "Copper Jetpack",
        desc=["Craft the Copper Jetpack - the first rung of the personal "
              "mobility ladder (Create Stuff & Additions)."],
        tasks=[item_task("create_sa:copper_jetpack_chestplate", only_from_crafting=True)],
        rewards=[skill_xp_reward("running", SIDE_XP[1]), *spur_rewards(SIDE_SPURS[1])],
        dependencies=[enter], quest_icon="create_sa:copper_jetpack_chestplate",
    )
    chunk_loader_1 = make_quest(
        quests, cid, "chunk_loader_1", "Andesite Chunk Loader",
        desc=["Craft the Andesite Chunk Loader (Create: Power Loader). It "
              "only force-loads chunks while spun under real kinetic power."],
        tasks=[item_task("create_power_loader:andesite_chunk_loader", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[1]), *spur_rewards(SIDE_SPURS[1])],
        dependencies=[enter], quest_icon="create_power_loader:andesite_chunk_loader",
    )
    vein_hunting = make_quest(
        quests, cid, "vein_hunting", "Vein Hunting",
        desc=["Craft a Vein Finder (Create Ore Excavation) - the entry-level "
              "scouting tool for this pack's ore-vein system."],
        tasks=[item_task("createoreexcavation:vein_finder", only_from_crafting=True)],
        rewards=[skill_xp_reward("mining", SIDE_XP[1]), *spur_rewards(SIDE_SPURS[1])],
        dependencies=[enter], quest_icon="createoreexcavation:vein_finder",
    )
    ars_wand = make_quest(
        quests, cid, "ars_wand", "The Mage's Path",
        desc=["Craft an Ars Nouveau wand - the entry point into this pack's "
              "spell-crafting magic system."],
        tasks=[item_task("ars_nouveau:wand", only_from_crafting=True)],
        rewards=[skill_xp_reward("magic", SIDE_XP[1]), *spur_rewards(SIDE_SPURS[1])],
        dependencies=[enter], quest_icon="ars_nouveau:wand",
    )
    make_quest(
        quests, cid, "curious_find", "A Curious Find (optional)",
        desc=["Find any Artifacts curio - they're pure exploration payoffs "
              "with no tier lock, hidden in structure loot at every rarity "
              "tier. This one just confirms you've found the umbrella."],
        tasks=[item_task("artifacts:umbrella", consume_items=False, only_from_crafting=False)],
        rewards=[skill_xp_reward("magic", SIDE_XP[1])],
        dependencies=[enter], quest_icon="artifacts:umbrella",
    )
    into_brass = make_quest(
        quests, cid, "into_brass", "Into the Brass Age",
        desc=["Craft or pick up a Brass Ingot - Create's mid-game alloy, and "
              "the trigger for Brass Age."],
        tasks=[item_task("create:brass_ingot", only_from_crafting=True)],
        rewards=[*spur_rewards(GATE_SPURS[1]), skill_xp_reward("mining", GATE_XP[1])],
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
        rewards=[skill_xp_reward("building", GATE_XP[2]), item_reward("create:brass_ingot")],
        dependencies=[ANDESITE_Q["into_brass"]],
        quest_icon="create:brass_ingot",
    )
    diamond_gear = make_quest(
        quests, cid, "diamond_gear", "Diamond Gear",
        desc=["Craft another Silent Gear pickaxe with Brass Age's material - "
              "the tool-tier milestone for this age."],
        tasks=[item_task("silentgear:pickaxe", only_from_crafting=True)],
        rewards=[skill_xp_reward("daggers", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="minecraft:diamond_pickaxe",
    )
    real_network = make_quest(
        quests, cid, "real_network", "A Real Network",
        desc=["Craft a Refined Storage Controller - the heart of the powered "
              "network that replaces Tom's Storage from here on."],
        tasks=[item_task("refinedstorage:controller", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="refinedstorage:controller",
    )
    alternator = make_quest(
        quests, cid, "alternator", "Power the Network",
        desc=["Craft a Create Crafts & Additions Alternator - turns Create's "
              "own rotational power into the FE that runs Refined Storage."],
        tasks=[item_task("createaddition:alternator", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="createaddition:alternator",
    )
    automation_arm = make_quest(
        quests, cid, "automation_arm", "First Automation",
        desc=["Craft a Mechanical Arm - Create's own first crafting-automation "
              "block, feeding Refined Storage's Importer/Exporter."],
        tasks=[item_task("create:mechanical_arm", only_from_crafting=True)],
        rewards=[skill_xp_reward("spears", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="create:mechanical_arm",
    )
    jetpack_2 = make_quest(
        quests, cid, "jetpack_2", "Andesite Jetpack",
        desc=["Craft the Andesite Jetpack - fuel-fired propellers, rung 2 of "
              "the mobility ladder."],
        tasks=[item_task("create_sa:andesite_jetpack_chestplate", only_from_crafting=True)],
        rewards=[skill_xp_reward("running", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="create_sa:andesite_jetpack_chestplate",
    )
    chunk_loader_2 = make_quest(
        quests, cid, "chunk_loader_2", "Brass Chunk Loader",
        desc=["Craft the Brass Chunk Loader - the second and final Power "
              "Loader rung."],
        tasks=[item_task("create_power_loader:brass_chunk_loader", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="create_power_loader:brass_chunk_loader",
    )
    tiab = make_quest(
        quests, cid, "tiab", "Time in a Bottle",
        desc=["Craft the Time in a Bottle tick accelerator - one per player, "
              "and it won't speed up spawners."],
        tasks=[item_task("tiab:time_in_a_bottle", only_from_crafting=True)],
        rewards=[skill_xp_reward("mining", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="tiab:time_in_a_bottle",
    )
    trains = make_quest(
        quests, cid, "trains", "Train Control",
        desc=["Craft a Track Station - Create's own Trains are a full Brass "
              "Age package now."],
        tasks=[item_task("create:track_station", only_from_crafting=True)],
        rewards=[skill_xp_reward("running", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="create:track_station",
    )
    diet_upgrade = make_quest(
        quests, cid, "diet_upgrade", "Sharper Knives",
        desc=["Craft a Farmer's Delight diamond knife - this is the real "
              "tier this pack's food-diet knife line reaches Brass Age "
              "(gold/diamond both unlock here; iron was Andesite Age, "
              "netherite is Precision Age)."],
        tasks=[item_task("farmersdelight:diamond_knife", only_from_crafting=True)],
        rewards=[skill_xp_reward("bows", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="farmersdelight:diamond_knife",
    )
    master_alloy = make_quest(
        quests, cid, "master_alloy", "The Master Alloy",
        desc=["Craft a Sturdy Sheet from Refined Radiance or Shadow Steel - "
              "Create's own top-tier alloy, and the door to Precision Age."],
        tasks=[item_task("create:sturdy_sheet", only_from_crafting=True)],
        rewards=[*spur_rewards(GATE_SPURS[2]), skill_xp_reward("mining", GATE_XP[2])],
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
        rewards=[skill_xp_reward("swords", GATE_XP[3]), item_reward("create:sturdy_sheet")],
        dependencies=[BRASS_Q["master_alloy"]],
        quest_icon="create:sturdy_sheet",
    )
    netherite_gear = make_quest(
        quests, cid, "netherite_gear", "Netherite Gear",
        desc=["Craft another Silent Gear pickaxe with Precision Age's material - "
              "the tool-tier milestone for this age."],
        tasks=[item_task("silentgear:pickaxe", only_from_crafting=True)],
        rewards=[skill_xp_reward("greatswords", SIDE_XP[3]), *spur_rewards(SIDE_SPURS[3])],
        dependencies=[enter], quest_icon="minecraft:netherite_pickaxe",
    )
    wireless = make_quest(
        quests, cid, "wireless", "Cut the Cables",
        desc=["Craft a Wireless Grid - manage your Refined Storage network "
              "from anywhere in range."],
        tasks=[item_task("refinedstorage:wireless_grid", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[3]), *spur_rewards(SIDE_SPURS[3])],
        dependencies=[enter], quest_icon="refinedstorage:wireless_grid",
    )
    jetpack_3 = make_quest(
        quests, cid, "jetpack_3", "Brass Jetpack",
        desc=["Craft the Brass Jetpack - steam-fired, rung 3 of the mobility "
              "ladder, and the base item the Induction Age netherite jetpack "
              "smiths from."],
        tasks=[item_task("create_sa:brass_jetpack_chestplate", only_from_crafting=True)],
        rewards=[skill_xp_reward("running", SIDE_XP[3]), *spur_rewards(SIDE_SPURS[3])],
        dependencies=[enter], quest_icon="create_sa:brass_jetpack_chestplate",
    )
    elytra = make_quest(
        quests, cid, "elytra", "Wings",
        desc=["Find an Elytra in an End City - it's not craftable, just "
              "gated behind reaching this tier and finding one."],
        tasks=[item_task("minecraft:elytra", consume_items=False, only_from_crafting=False)],
        rewards=[skill_xp_reward("longswords", SIDE_XP[3]), *spur_rewards(SIDE_SPURS[3])],
        dependencies=[enter], quest_icon="minecraft:elytra",
    )
    diet_upgrade = make_quest(
        quests, cid, "diet_upgrade", "The Netherite Knife",
        desc=["Craft a Farmer's Delight netherite knife (a smithing upgrade "
              "from the diamond knife) - the ceiling of this pack's food-"
              "diet knife line, keeping your bonus-hearts diet variety topped "
              "up through Precision Age's grind."],
        tasks=[item_task("farmersdelight:netherite_knife", only_from_crafting=True)],
        rewards=[skill_xp_reward("bows", SIDE_XP[3]), *spur_rewards(SIDE_SPURS[3])],
        dependencies=[enter], quest_icon="farmersdelight:netherite_knife",
    )
    vein_ceiling = make_quest(
        quests, cid, "vein_ceiling", "The Netherite Drill",
        desc=["Craft the Netherite Drill - Create Ore Excavation's own tool "
              "ceiling, and what it takes to pull allthemodium/vibranium/"
              "unobtainium out of the ground."],
        tasks=[item_task("createoreexcavation:netherite_drill", only_from_crafting=True)],
        rewards=[skill_xp_reward("mining", SIDE_XP[3]), *spur_rewards(SIDE_SPURS[3])],
        dependencies=[enter], quest_icon="createoreexcavation:netherite_drill",
    )
    final_ingot = make_quest(
        quests, cid, "final_ingot", "The Final Ingot",
        desc=["Craft or pick up a Netherite Ingot - the temporary trigger for "
              "Induction Age, until a real narrative trigger replaces it."],
        tasks=[item_task("minecraft:netherite_ingot", only_from_crafting=True)],
        rewards=[*spur_rewards(GATE_SPURS[3]), skill_xp_reward("mining", GATE_XP[3])],
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
        rewards=[skill_xp_reward("bows", GATE_XP[4]), item_reward("minecraft:netherite_ingot")],
        dependencies=[PRECISION_Q["final_ingot"]],
        quest_icon="minecraft:netherite_ingot",
    )
    autocrafting = make_quest(
        quests, cid, "autocrafting", "Native Autocrafting",
        desc=["Craft an Autocrafting Upgrade - Refined Storage's own "
              "pattern-based autocrafter, no more Mechanical Arm needed for "
              "storage automation."],
        tasks=[item_task("refinedstorage:autocrafting_upgrade", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[4]), *spur_rewards(SIDE_SPURS[4])],
        dependencies=[enter], quest_icon="refinedstorage:autocrafting_upgrade",
    )
    storage_ceiling = make_quest(
        quests, cid, "storage_ceiling", "64k Storage",
        desc=["Craft a 64k Storage Part - the ceiling of this pack's Refined "
              "Storage capacity chase (until the Jovian Frontier capstone)."],
        tasks=[item_task("refinedstorage:64k_storage_part", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[4]), *spur_rewards(SIDE_SPURS[4])],
        dependencies=[enter], quest_icon="refinedstorage:64k_storage_part",
    )
    jetpack_ceiling = make_quest(
        quests, cid, "jetpack_ceiling", "Netherite Jetpack",
        desc=["Craft the Netherite Jetpack - the final rung before "
              "Starforged Age grants true persistent flight outright."],
        tasks=[item_task("create_sa:netherite_jetpack_chestplate", only_from_crafting=True)],
        rewards=[skill_xp_reward("running", SIDE_XP[4]), *spur_rewards(SIDE_SPURS[4])],
        dependencies=[enter], quest_icon="create_sa:netherite_jetpack_chestplate",
    )
    teleport = make_quest(
        quests, cid, "teleport", "Teleportation",
        desc=["Craft a Waystone - intra-world teleportation, gated all the "
              "way to this tier on purpose."],
        tasks=[item_task("waystones:waystone", only_from_crafting=True)],
        rewards=[skill_xp_reward("running", SIDE_XP[4]), *spur_rewards(SIDE_SPURS[4])],
        dependencies=[enter], quest_icon="waystones:waystone",
    )
    steam_flight = make_quest(
        quests, cid, "steam_flight", "Steam-Powered Flight",
        desc=["Craft a Steam Vent (Create Aeronautics) - the passive, "
              "industrial-scale heat source for sustained airship lift."],
        tasks=[item_task("aeronautics:steam_vent", only_from_crafting=True)],
        rewards=[skill_xp_reward("tachi", SIDE_XP[4]), *spur_rewards(SIDE_SPURS[4])],
        dependencies=[enter], quest_icon="aeronautics:steam_vent",
    )
    gear_ceiling = make_quest(
        quests, cid, "gear_ceiling", "Allthemodium",
        desc=["Smelt an Allthemodium Ingot - this pack's own post-netherite "
              "Silent Gear material floor, carrying gear progression into "
              "the space tiers."],
        tasks=[item_task("allthemodium:allthemodium_ingot", only_from_crafting=True)],
        rewards=[skill_xp_reward("mining", SIDE_XP[4]), *spur_rewards(SIDE_SPURS[4])],
        dependencies=[enter], quest_icon="allthemodium:allthemodium_ingot",
    )
    dragon = make_quest(
        quests, cid, "dragon", "Conquer the End",
        desc=["Kill the Ender Dragon. The overworld, Nether, and End are "
              "done - this is the real trigger for Starforged Age."],
        tasks=[kill_task("minecraft:ender_dragon", 1)],
        rewards=[*spur_rewards(GATE_SPURS[4]), skill_xp_reward("swords", GATE_XP[4])],
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
        rewards=[skill_xp_reward("swimming", GATE_XP[5]), item_reward("minecraft:nether_star")],
        dependencies=[INDUCTION_Q["dragon"]],
        quest_icon="minecraft:nether_star",
    )
    make_quest(
        quests, cid, "flight_ack", "True Flight",
        desc=["Double-tap jump to toggle flight - it's granted the instant "
              "you reached this tier, no item or fuel required, and it "
              "survives death."],
        tasks=[checkmark_task()],
        rewards=[skill_xp_reward("running", SIDE_XP[5])],
        dependencies=[enter], quest_icon="minecraft:elytra",
    )
    make_quest(
        quests, cid, "leaderboard_check", "Check Your Rank (optional)",
        desc=["Run /leaderboard wealth, /leaderboard tier, or /leaderboard "
              "level to see how you and your team stack up."],
        tasks=[checkmark_task()],
        rewards=[skill_xp_reward("mining", SIDE_XP[5])],
        dependencies=[enter], quest_icon="numismatics:sun",
    )
    aluminum_age = make_quest(
        quests, cid, "aluminum_age", "The Aluminum Age",
        desc=["Smelt a TFMG Aluminum Ingot - the first rung of the endgame "
              "automation ladder that carries all the way to Jupiter."],
        tasks=[item_task("tfmg:aluminum_ingot", only_from_crafting=True)],
        rewards=[skill_xp_reward("mining", SIDE_XP[5]), *spur_rewards(SIDE_SPURS[5])],
        dependencies=[enter], quest_icon="tfmg:aluminum_ingot",
    )
    rocket_parts = make_quest(
        quests, cid, "rocket_parts", "Rocket Parts",
        desc=["Craft a Rocket Engine (Stellaris) - one of the core "
              "components of your first rocket."],
        tasks=[item_task("stellaris:rocket_engine", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[5]), *spur_rewards(SIDE_SPURS[5])],
        dependencies=[aluminum_age], quest_icon="stellaris:rocket_engine",
    )
    launch = make_quest(
        quests, cid, "launch", "Liftoff",
        desc=["Launch your rocket and reach Earth orbit - the real trigger "
              "for Lunar Frontier."],
        tasks=[dimension_task("stellaris:earth_orbit")],
        rewards=[*spur_rewards(GATE_SPURS[5]), skill_xp_reward("running", GATE_XP[5])],
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
        rewards=[skill_xp_reward("mining", GATE_XP[6]), item_reward("allthemodium:unobtainium_ingot")],
        dependencies=[STARFORGED_Q["launch"]],
        quest_icon="stellaris:rocket",
    )
    steel_age = make_quest(
        quests, cid, "steel_age", "The Steel Age",
        desc=["Smelt a TFMG Steel Ingot - the mod's own core metallurgy "
              "chain, rung 2 of the endgame automation ladder."],
        tasks=[item_task("tfmg:steel_ingot", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[6]), *spur_rewards(SIDE_SPURS[6])],
        dependencies=[enter], quest_icon="tfmg:steel_ingot",
    )
    moon_landing = make_quest(
        quests, cid, "moon_landing", "One Small Step",
        desc=["Travel to the Moon - the real trigger for Martian Frontier."],
        tasks=[dimension_task("stellaris:moon")],
        rewards=[*spur_rewards(GATE_SPURS[6]), skill_xp_reward("running", GATE_XP[6])],
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
        rewards=[skill_xp_reward("mining", GATE_XP[7]), item_reward("tfmg:diesel_bucket")],
        dependencies=[LUNAR_Q["moon_landing"]],
        quest_icon="minecraft:redstone",
    )
    petrochemical = make_quest(
        quests, cid, "petrochemical", "The Petrochemical Age",
        desc=["Refine a bucket of Diesel (TFMG) - rung 3 of the endgame "
              "automation ladder."],
        tasks=[item_task("tfmg:diesel_bucket", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[7]), *spur_rewards(SIDE_SPURS[7])],
        dependencies=[enter], quest_icon="tfmg:diesel_bucket",
    )
    mars_landing = make_quest(
        quests, cid, "mars_landing", "Red Planet",
        desc=["Travel to Mars - the real trigger for Inner System."],
        tasks=[dimension_task("stellaris:mars")],
        rewards=[*spur_rewards(GATE_SPURS[7]), skill_xp_reward("running", GATE_XP[7])],
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
        rewards=[skill_xp_reward("mining", GATE_XP[8]), item_reward("tfmg:electric_motor")],
        dependencies=[MARTIAN_Q["mars_landing"]],
        quest_icon="minecraft:magma_block",
    )
    electrical_age = make_quest(
        quests, cid, "electrical_age", "The Electrical Age",
        desc=["Craft a TFMG Converter - bridges TFMG's own power grid into "
              "Create/FE, rung 4 of the endgame automation ladder."],
        tasks=[item_task("tfmg:converter", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[8]), *spur_rewards(SIDE_SPURS[8])],
        dependencies=[enter], quest_icon="tfmg:converter",
    )
    make_quest(
        quests, cid, "venus_landing", "Morning Star (optional)",
        desc=["Travel to Venus - either inner planet triggers Jovian "
              "Frontier, so this and Mercury are both optional."],
        tasks=[dimension_task("stellaris:venus")],
        rewards=[skill_xp_reward("running", SIDE_XP[8]), *spur_rewards(SIDE_SPURS[8])],
        dependencies=[electrical_age], quest_icon="minecraft:magma_block",
    )
    make_quest(
        quests, cid, "mercury_landing", "Swift Planet (optional)",
        desc=["Travel to Mercury - either inner planet triggers Jovian "
              "Frontier, so this and Venus are both optional."],
        tasks=[dimension_task("stellaris:mercury")],
        rewards=[skill_xp_reward("running", SIDE_XP[8]), *spur_rewards(SIDE_SPURS[8])],
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
        rewards=[skill_xp_reward("mining", GATE_XP[9]),
                 item_reward("allthemodium:unobtainium_vibranium_alloy_ingot")],
        dependencies=[INNER_Q["electrical_age"]],
        quest_icon="minecraft:end_crystal",
    )
    combustion_age = make_quest(
        quests, cid, "combustion_age", "The Combustion Age",
        desc=["Craft a TFMG Engine Cylinder - the final rung of the endgame "
              "automation ladder."],
        tasks=[item_task("tfmg:engine_cylinder", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[9]), *spur_rewards(SIDE_SPURS[9])],
        dependencies=[enter], quest_icon="tfmg:engine_cylinder",
    )
    storage_infinity = make_quest(
        quests, cid, "storage_infinity", "Infinite Storage",
        desc=["Craft a Refined Storage Creative Storage Block - genuinely "
              "infinite item capacity, the true ceiling of the storage "
              "chase started back at Andesite Age."],
        tasks=[item_task("refinedstorage:creative_storage_block", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[9] + 50), *spur_rewards(SIDE_SPURS[9])],
        dependencies=[combustion_age], quest_icon="refinedstorage:creative_storage_block",
    )
    energy_infinity = make_quest(
        quests, cid, "energy_infinity", "Infinite Energy",
        desc=["Craft a Create Creative Motor - a genuinely endless source of "
              "Rotational Force, bridged to FE the same way every earlier "
              "power step in this pack has been."],
        tasks=[item_task("create:creative_motor", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[9] + 50), *spur_rewards(SIDE_SPURS[9])],
        dependencies=[combustion_age], quest_icon="create:creative_motor",
    )
    resource_infinity = make_quest(
        quests, cid, "resource_infinity", "Infinite Resources",
        desc=["Craft a Create Creative Crate - an endless supply of any one "
              "item you configure. This is the hardest, latest-gated craft "
              "in the entire pack for a reason - guard it accordingly."],
        tasks=[item_task("create:creative_crate", only_from_crafting=True)],
        rewards=[skill_xp_reward("mining", SIDE_XP[9] + 50), *spur_rewards(SIDE_SPURS[9])],
        dependencies=[combustion_age], quest_icon="create:creative_crate",
    )
    make_quest(
        quests, cid, "journeys_end", "Journey's End",
        desc=["Every tier from Rootborn to Jupiter, done. Future updates may "
              "extend the ladder further out into the solar system - this "
              "book will grow to meet them."],
        tasks=[checkmark_task()],
        rewards=[*spur_rewards(GATE_SPURS[9]), skill_xp_reward("mining", GATE_XP[9])],
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


# ---------------------------------------------------------------------------
# JSON -> embedded JS literal. Plain json.dumps is valid JS for this data
# shape (no NaN/Infinity/non-string keys anywhere in it), so there is no
# need for a bespoke serializer the way the old SNBT format required.
# ---------------------------------------------------------------------------
RUNTIME_TEMPLATE = r"""
// ---------------------------------------------------------------------------
// Runtime: bespoke quest tracker (GitHub #33), replacing FTB Quests.
//
// Team-shared PROGRESS, per-player REWARDS (instructions.md line 41: "Players
// should share progress (but not rewards) for preset track quests" - this IS
// the preset track, formerly FTB Quests' "Tier Progression" chapter). Quest
// completion is stored keyed by getProgressKey(player) below (a team/party id
// when the player is in a real multi-member party, else a per-player key) -
// so any teammate satisfying a quest's tasks marks it done for the whole
// team, unlocking dependents for everyone - but the reward grant (items/xp/
// commands) goes ONLY to the player whose live state the tick scan (or
// /quest check) actually found satisfying, never broadcast to teammates.
//
// PARTY-ID SEAM for GitHub #32 (Open Parties and Claims, replacing FTB
// Teams) - LANDED, integrated alongside #33 at merge time. getProgressKey()
// below was written as the ONE function that seam needed to change - every
// other function in this file keys exclusively off the string it returns,
// so this was a one-function edit, not a redesign, exactly as planned.
// Ground truth for the OPAC-based lookup, confirmed by reading the real
// interface source (decompiled from the actually-resolved
// open-parties-and-claims-neoforge-1.21.1-0.27.8.jar's Modrinth-published
// sources jar, xaero.pac.common.server.parties.party.api package):
// xaero.pac.common.server.api.OpenPACServerAPI.get(server) -> instance;
// .getPartyManager() -> IPartyManagerAPI; .getPartyByMember(UUID) ->
// IServerPartyAPI (@Nullable, null if the player has no party) - a direct
// player->party lookup, unlike the getAllStream()-based aggregation
// leaderboard.js's collectTeamEntries()/progression_stage_bridge.js's
// psbSyncPartyStages use (those iterate every party for a different
// purpose - building a full leaderboard / syncing every party's members -
// this just needs one player's own party). IServerPartyAPI.getId() -> UUID
// is the progress key. OPAC does NOT auto-create a solo party per player
// the way FTB Teams did, so a solo player's lookup returns null and falls
// through to the per-player key below, same as before.
//
// Task checking: item tasks are a live inventory-count check (same
// container-scanning shape as leaderboard.js's countCoins(), generalized to
// any item id) with optional consume-on-complete - NOT an FTB-Quests-style
// "must have been freshly crafted" event tracker (see gen_quests.py's own
// docstring for why this simplification is deliberate and precedented by
// progression_stage_bridge.js's GitHub #23 fix). Kill tasks read the
// vanilla per-entity-type kill stat directly (dev.latvian.mods.kubejs.
// player.PlayerStatsJS.getKilled(EntityType<?>) - confirmed via javap
// against the installed kubejs jar; net.minecraft.world.entity.EntityType.
// byString(String) resolves the configured entity id to the EntityType
// instance that method needs, confirmed via javap against the installed
// server jar's SRG-named class dump under net/minecraft/world/entity/
// EntityType.class). Dimension tasks compare String(player.level.dimension)
// against the configured dimension id (same accessor mob_scaling.js already
// uses for DIMENSION_FACTOR lookups). Gamestage tasks read player.stages.has
// (id) (same binding leaderboard.js/progression_stage_bridge.js/selftest.js
// already use). Checkmark tasks are never tick-completed - they require the
// player to run /quest check <id> themselves, since there is no self-check
// GUI to click in a chat-command-only redesign.

const QuestsCompoundTagClass = Java.loadClass('net.minecraft.nbt.CompoundTag')
const QuestsEntityTypeClass = Java.loadClass('net.minecraft.world.entity.EntityType')

let QuestsOpenPACServerAPIClass = null
try {
    QuestsOpenPACServerAPIClass = Java.loadClass('xaero.pac.common.server.api.OpenPACServerAPI')
} catch (e) {
    console.error('[vpp quests] Open Parties and Claims API (xaero.pac.common.server.api.OpenPACServerAPI) failed to load - quest progress will always be per-player: ' + e)
}

// ---- progress-key seam (see header comment - the one function GitHub #32 needed to change) ----

function getProgressKey(player) {
    if (QuestsOpenPACServerAPIClass) {
        try {
            let partyManager = QuestsOpenPACServerAPIClass.get(player.server).getPartyManager()
            let party = partyManager.getPartyByMember(player.uuid)
            if (party) {
                return 'team:' + party.getId()
            }
        } catch (e) {
            console.error('[vpp quests] party lookup failed for ' + player.username + ', falling back to a per-player key: ' + e)
        }
    }
    return 'player:' + player.uuid
}

// ---- persistent progress storage (server.persistentData, same pattern leaderboard.js's cache uses) ----

function questsEnsureCompound(parent, key) {
    if (!parent.contains(key, 10)) { // 10 = NBT compound-tag type id
        parent.put(key, new QuestsCompoundTagClass())
    }
    return parent.getCompound(key)
}

const QUESTS_PROGRESS_ROOT_KEY = 'vpp_quests_progress'

function questsProgressCompound(server, progressKey) {
    let root = questsEnsureCompound(server.persistentData, QUESTS_PROGRESS_ROOT_KEY)
    return questsEnsureCompound(root, progressKey)
}

function isQuestComplete(server, progressKey, questId) {
    return questsProgressCompound(server, progressKey).getBoolean(questId)
}

function markQuestComplete(server, progressKey, questId) {
    questsProgressCompound(server, progressKey).putBoolean(questId, true)
}

function dependenciesSatisfied(server, progressKey, quest) {
    for (let i = 0; i < quest.dependencies.length; i++) {
        if (!isQuestComplete(server, progressKey, quest.dependencies[i])) return false
    }
    return true
}

function hasCheckmarkTask(quest) {
    for (let i = 0; i < quest.tasks.length; i++) {
        if (quest.tasks[i].type === 'checkmark') return true
    }
    return false
}

// ---- task checking ----

function questsCountItem(player, itemId) {
    let total = 0
    let inv = player.getInventory()
    let size = inv.getContainerSize()
    for (let i = 0; i < size; i++) {
        let stack = inv.getItem(i)
        if (!stack || stack.isEmpty()) continue
        if (stack.id === itemId) total += stack.getCount()
    }
    return total
}

function questsConsumeItem(player, itemId, count) {
    let remaining = count
    let inv = player.getInventory()
    let size = inv.getContainerSize()
    for (let i = 0; i < size && remaining > 0; i++) {
        let stack = inv.getItem(i)
        if (!stack || stack.isEmpty() || stack.id !== itemId) continue
        let take = Math.min(remaining, stack.getCount())
        stack.setCount(stack.getCount() - take)
        remaining -= take
    }
}

function checkTask(player, task) {
    switch (task.type) {
        case 'item':
            return questsCountItem(player, task.item) >= task.count
        case 'kill': {
            let opt = QuestsEntityTypeClass.byString(task.entity)
            if (!opt.isPresent()) return false
            return player.stats.getKilled(opt.get()) >= task.count
        }
        case 'dimension':
            return String(player.level.dimension) === task.dimension
        case 'gamestage':
            return player.stages.has(task.stage)
        case 'checkmark':
            return false // player-invoked only, via /quest check
        default:
            console.error('[vpp quests] unknown task type: ' + task.type)
            return false
    }
}

function questSatisfied(player, quest) {
    for (let i = 0; i < quest.tasks.length; i++) {
        if (!checkTask(player, quest.tasks[i])) return false
    }
    return true
}

// ---- rewards (same COINS/payCoins convention as economy.js) ----

const QUESTS_COINS = [
    ['numismatics:sun', 4096], ['numismatics:crown', 512], ['numismatics:cog', 64],
    ['numismatics:sprocket', 16], ['numismatics:bevel', 8], ['numismatics:spur', 1],
]

function applyReward(player, reward) {
    switch (reward.type) {
        case 'item':
            player.give(Item.of(reward.item, reward.count))
            break
        case 'xp':
            player.server.runCommandSilent(`puffish_skills experience add ${player.username} ${reward.category} ${reward.amount}`)
            break
        case 'command':
            player.server.runCommandSilent(reward.command.split('{p}').join(player.username))
            break
        case 'gamestage':
            player.stages.add(reward.stage)
            break
        case 'toast':
            player.tell(`*** ${reward.message} ***`)
            break
        default:
            console.error('[vpp quests] unknown reward type: ' + reward.type)
    }
}

function grantRewards(player, quest) {
    for (let i = 0; i < quest.rewards.length; i++) {
        try {
            applyReward(player, quest.rewards[i])
        } catch (e) {
            console.error('[vpp quests] reward grant failed for ' + player.username + ' on quest ' + quest.id + ': ' + e)
        }
    }
}

function notifyTeammates(server, progressKey, completer, quest) {
    for (const p of server.players) { // KubeJS EntityArrayList, proven for-of target (mob_scaling.js/leaderboard.js)
        if (String(p.uuid) === String(completer.uuid)) continue
        if (getProgressKey(p) === progressKey) {
            p.tell(`Team quest complete: ${quest.title} (completed by ${completer.username})`)
        }
    }
}

// ---- GitHub #36: vanilla advancement tree, granted via command (the
// advancements themselves use a minecraft:impossible criterion - see
// scripts/gen_quests.py's write_advancements() - so this command is the
// ONLY way any of them are ever granted). Re-granting an already-held
// advancement is a harmless vanilla no-op, so none of the call sites below
// need to check possession first. ----

function grantAdvancement(player, questId) {
    try {
        player.server.runCommandSilent(`advancement grant ${player.username} only vanillaplusplus:quests/${questId}`)
    } catch (e) {
        console.error('[vpp quests] advancement grant failed for ' + player.username + ' on quest ' + questId + ': ' + e)
    }
}

// The advancement is a visual mirror of team-shared PROGRESS (same sharing
// model as quest completion itself), not of per-player REWARDS - granted to
// every online teammate, not just whichever player's live state actually
// satisfied the task.
function grantAdvancementToTeam(server, progressKey, quest) {
    for (const p of server.players) {
        if (getProgressKey(p) === progressKey) grantAdvancement(p, quest.id)
    }
}

function completeQuest(server, player, progressKey, quest) {
    for (let i = 0; i < quest.tasks.length; i++) {
        let task = quest.tasks[i]
        if (task.type === 'item' && task.consume) questsConsumeItem(player, task.item, task.count)
    }
    markQuestComplete(server, progressKey, quest.id)
    grantRewards(player, quest)
    player.tell(`Quest complete: ${quest.title}`)
    notifyTeammates(server, progressKey, player, quest)
    grantAdvancementToTeam(server, progressKey, quest)
}

// Catch-up sync on login: a player who joins a party mid-progress, or just
// reconnects, gets every already-completed team quest's advancement
// granted silently - no reward re-grant (rewards were already handled at
// original completion time), no chat spam, just the visual layer catching
// up. Same event hook leaderboard.js already uses for loggedOut.
PlayerEvents.loggedIn(event => {
    let player = event.player
    if (!player || !player.server) return
    try {
        let server = player.server
        let progressKey = getProgressKey(player)
        for (const questId of Object.keys(QUEST_BY_ID)) {
            if (isQuestComplete(server, progressKey, questId)) grantAdvancement(player, questId)
        }
    } catch (e) {
        console.error('[vpp quests] login advancement catch-up failed for ' + player.username + ': ' + e)
    }
})

// ---- tick scan ----

const QUESTS_TICK_INTERVAL = 100 // 5s, matches achievements.js's own cadence

let questsTickCounter = 0
ServerEvents.tick(event => {
    questsTickCounter++
    if (questsTickCounter % QUESTS_TICK_INTERVAL !== 0) return

    for (const player of event.server.players) {
        try {
            scanQuestsForPlayer(player)
        } catch (e) {
            console.error('[vpp quests] tick scan failed for ' + player.username + ': ' + e)
        }
    }
})

function scanQuestsForPlayer(player) {
    let server = player.server
    let progressKey = getProgressKey(player)
    for (const chapter of QUEST_CHAPTERS) {
        for (const quest of chapter.quests) {
            if (hasCheckmarkTask(quest)) continue
            if (isQuestComplete(server, progressKey, quest.id)) continue
            if (!dependenciesSatisfied(server, progressKey, quest)) continue
            if (!questSatisfied(player, quest)) continue
            completeQuest(server, player, progressKey, quest)
        }
    }
}

// ---- flattened lookups ----

const QUEST_BY_ID = {}
const CHECKMARK_QUEST_IDS = []
for (const chapter of QUEST_CHAPTERS) {
    for (const quest of chapter.quests) {
        QUEST_BY_ID[quest.id] = quest
        if (hasCheckmarkTask(quest)) CHECKMARK_QUEST_IDS.push(quest.id)
    }
}

// ---- manual checkmark completion ----

function runCheckmarkCheck(player, questId) {
    let server = player.server
    let quest = QUEST_BY_ID[questId]
    if (!quest) { player.tell('Unknown quest id: ' + questId); return }
    let progressKey = getProgressKey(player)
    if (isQuestComplete(server, progressKey, questId)) {
        player.tell(`Already complete: ${quest.title}`)
        return
    }
    if (!dependenciesSatisfied(server, progressKey, quest)) {
        player.tell(`Locked - complete its prerequisites first: ${quest.title}`)
        return
    }
    completeQuest(server, player, progressKey, quest)
}

// ---- describe helpers for /quests <chapter> ----

function describeTask(task) {
    switch (task.type) {
        case 'item':
            return `${task.consume ? 'Turn in' : 'Have'} ${task.count}x ${task.item}` + (task.onlyFromCrafting ? ' (crafted)' : '')
        case 'kill':
            return `Kill ${task.count}x ${task.entity}`
        case 'dimension':
            return `Travel to ${task.dimension}`
        case 'gamestage':
            return `Reach stage: ${task.stage}`
        case 'checkmark':
            return 'Self-check (/quest check ' + '<id>)'
        default:
            return task.type
    }
}

function describeReward(reward) {
    switch (reward.type) {
        case 'item':
            return `${reward.count}x ${reward.item}`
        case 'xp':
            return `${reward.amount} ${reward.category} XP`
        case 'command':
            return 'command reward'
        case 'gamestage':
            return `stage: ${reward.stage}`
        case 'toast':
            return 'announcement'
        default:
            return reward.type
    }
}

function describeTasks(quest) {
    return quest.tasks.map(describeTask).join('; ')
}

function describeRewards(quest) {
    return quest.rewards.map(describeReward).join(', ')
}

// ---- chat command family ----

function showQuestsOverview(player) {
    let server = player.server
    let progressKey = getProgressKey(player)
    player.tell('--- Quests ---')
    let current = null
    for (const chapter of QUEST_CHAPTERS) {
        let total = chapter.quests.length
        let done = chapter.quests.filter(q => isQuestComplete(server, progressKey, q.id)).length
        player.tell(`${chapter.title}: ${done}/${total}`)
        if (!current && done < total) current = chapter
    }
    if (!current) current = QUEST_CHAPTERS[QUEST_CHAPTERS.length - 1]
    player.tell(`Current chapter: ${current.title} - run /quests ${current.id} for details.`)
}

function showChapterDetail(player, chapter) {
    let server = player.server
    let progressKey = getProgressKey(player)
    player.tell(`--- ${chapter.title} ---`)
    for (const line of chapter.subtitle) player.tell(line)
    for (const quest of chapter.quests) {
        let complete = isQuestComplete(server, progressKey, quest.id)
        let locked = !complete && !dependenciesSatisfied(server, progressKey, quest)
        let status = complete ? 'DONE' : (locked ? 'LOCKED' : 'OPEN')
        player.tell(`[${status}] ${quest.title} - ${describeTasks(quest)} -> ${describeRewards(quest)}`)
    }
}

ServerEvents.commandRegistry(event => {
    const { commands: Commands } = event

    // /quests [chapter] - one literal subcommand per chapter id (10, a
    // small fixed set), NOT a Commands.argument(...)/Arguments.STRING
    // interop call - same reasoning skill_respec.js's own /respec command
    // already documented: no script in this pack has ever registered a
    // string ArgumentType and this cannot be boot-tested here to find out
    // if that guess would be right, so literal chaining (already proven
    // via economy.js/dailies.js/leaderboard.js) is used throughout instead.
    let questsCmd = Commands.literal('quests')
        .executes(ctx => { showQuestsOverview(ctx.source.playerOrException); return 1 })
    for (const chapter of QUEST_CHAPTERS) {
        questsCmd = questsCmd.then(
            Commands.literal(chapter.id).executes(ctx => {
                showChapterDetail(ctx.source.playerOrException, chapter)
                return 1
            })
        )
    }
    event.register(questsCmd)

    // /quest check <id> - one literal subcommand per checkmark quest (a
    // small fixed set - 4 in this book's actual content), same reasoning.
    let checkCmd = Commands.literal('check')
        .executes(ctx => {
            ctx.source.playerOrException.tell('Usage: /quest check <id>. Checkmark quests: ' + CHECKMARK_QUEST_IDS.join(', '))
            return 0
        })
    for (const qid of CHECKMARK_QUEST_IDS) {
        checkCmd = checkCmd.then(
            Commands.literal(qid).executes(ctx => {
                runCheckmarkCheck(ctx.source.playerOrException, qid)
                return 1
            })
        )
    }
    event.register(Commands.literal('quest').then(checkCmd))
})
""".strip("\n")


# ---------------------------------------------------------------------------
# GitHub #36: vanilla advancement generation. One JSON file per quest under
# pack/kubejs/data/vanillaplusplus/advancement/quests/, built from the exact same
# quest dicts quests.js is generated from - the two can never drift out of
# sync since there is only one source of truth (the CHAPTER_DEFS/builder
# functions above).
# ---------------------------------------------------------------------------
def advancement_frame(quest):
    if quest["id"] in CHALLENGE_QUEST_IDS:
        return "challenge"
    if any(t["type"] == "gamestage" for t in quest["tasks"]):
        return "goal"
    return "task"


def build_advancement(quest, is_root):
    display = {
        "icon": {"id": quest["icon"], "count": 1},
        "title": quest["title"],
        "description": " ".join(quest["desc"]),
        "frame": advancement_frame(quest),
        "show_toast": True,
        "announce_to_chat": False,
    }
    if is_root:
        display["background"] = ADVANCEMENT_ROOT_BACKGROUND
    advancement = {
        "criteria": {"impossible": {"trigger": "minecraft:impossible"}},
        "requirements": [["impossible"]],
        "display": display,
    }
    if not is_root:
        # Vanilla advancements are single-parent trees, not DAGs - a quest
        # with multiple dependencies only gets one tree edge drawn (its
        # first listed dependency); the real multi-dependency AND-gate for
        # when the quest actually completes is entirely quests.js's own
        # dependenciesSatisfied(), unaffected by this simplification.
        advancement["parent"] = "vanillaplusplus:quests/" + quest["dependencies"][0]
    return advancement


def write_advancements(chapters):
    if ADVANCEMENTS_DIR.exists():
        shutil.rmtree(ADVANCEMENTS_DIR)
    ADVANCEMENTS_DIR.mkdir(parents=True)
    count = 0
    for chapter in chapters:
        for quest in chapter["quests"]:
            is_root = len(quest["dependencies"]) == 0
            advancement = build_advancement(quest, is_root)
            out = ADVANCEMENTS_DIR / f"{quest['id']}.json"
            out.write_text(json.dumps(advancement, indent=2) + "\n")
            count += 1
    return count


def main():
    chapters = []
    for i, (chapter_id, title, subtitle, builder, chap_icon) in enumerate(CHAPTER_DEFS):
        chapter = make_chapter(chapter_id, title, subtitle, builder, order_index=i, chapter_icon=chap_icon)
        chapters.append(chapter)

    total_quests = sum(len(c["quests"]) for c in chapters)
    total_deps = sum(len(q["dependencies"]) for c in chapters for q in c["quests"])

    lines = []
    lines.append("// GENERATED by scripts/gen_quests.py - do not hand-edit, re-run the script instead.")
    lines.append("// Bespoke quest tracker replacing FTB Quests (GitHub #33) - see scripts/gen_quests.py's")
    lines.append("// own module docstring for the full design rationale (team-shared progress / per-player")
    lines.append("// rewards, the #32 party-id seam, the mod-removal evidence trail, and every disclosed")
    lines.append("// content-fidelity simplification).")
    lines.append(f"// {len(chapters)} chapters, {total_quests} quests, {total_deps} dependency edges.")
    lines.append("const QUEST_CHAPTERS = " + json.dumps(chapters, indent=2) + "")
    lines.append("")
    lines.append(RUNTIME_TEMPLATE)

    OUT_FILE.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT_FILE} ({len(chapters)} chapters, {total_quests} quests, {total_deps} dependency edges)")

    advancement_count = write_advancements(chapters)
    print(f"wrote {advancement_count} advancement file(s) to {ADVANCEMENTS_DIR}")


if __name__ == "__main__":
    main()
