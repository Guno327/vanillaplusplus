#!/usr/bin/env python3
"""GitHub issue #10 ("Quest Book is Too Minimal") - full rewrite of
pack/config/ftbquests/quests/ from the current one-chapter/one-quest-per-tier
book into ONE FULL CHAPTER PER TIER (10 tiers, rootborn -> jovian_frontier),
each chapter a 1-to-1 walkthrough of that tier's REAL progression steps
(verified against pack/config/ProgressiveStages/*.toml, DESIGN.md, and
TODO.md - every item id used below appears in one of those files already, so
none are guessed).

Format/serializer ground truth: copied verbatim from the installed
scripts/gen_quests.py (same repo, same pack) - see that file's own docstring
for the full FTB Quests 2101.1.27 (MC 1.21.1, pre-JSON5-rewrite) SNBT grammar
research trail. Re-verified independently this pass by decompiling the
installed ftb-quests-neoforge-2101.1.27.jar's TaskTypes/RewardTypes/*Task/
*Reward classes (task ids: item/custom/xp/dimension/stat/kill/location/
checkmark/advancement/observation/biome/structure/gamestage/fluid; reward ids:
item/choice/all_table/random/command/custom/xp/xp_levels/advancement/toast/
gamestage/currency). ItemTask fields: item{id,count}, count, consume_items,
only_from_crafting. KillTask: entity, value. DimensionTask: dimension.
CheckmarkTask: no extra fields needed.

Deliberately NOT using the "currency" reward type - it requires a registered
FTB currency provider (FTB Money/Ranks bridge), which this pack never
installed; Numismatics currency is instead granted as literal coin ITEMS
(numismatics:spur/bevel/sprocket/cog/crown/sun), matching economy.js's own
established "coins are plain items" convention exactly.

Reward-budget policy (see DESIGN_SUMMARY.md for the full rationale):
- Spur amounts are anchored to scripts/gen_economy.py's own TIER_PRICE table
  for tiers this pack's real economy actually prices (rootborn..starforged_age:
  1/4/16/64/256/1024). gen_economy.py has NO pricing signal past starforged_age
  (anything not tier-priced there falls back to 1 spur) - rather than invent a
  fictitious continued-doubling economy for tiers 6-9 that the real /sell
  command could never match (a real "unbalanced exploit" per instructions.md's
  own ask), late-game gate-quest rewards are capped just above the starforged
  ceiling with modest, disclosed, hand-picked bumps (1024/1152/1280/1408/1536),
  not another doubling.
- Every "enter <tier>" gate quest reward reuses the ORIGINAL single-chapter
  book's own skill-xp table for tiers 0-5 verbatim (mining 40->emitted as the
  Rootborn chapter's own capstone.../ mining 80/building 150/swords 300/
  bows 600/swimming 1200) so this rewrite doesn't silently re-balance rewards
  players may already be relying on; tiers 6-9 continue the same +300 cadence
  (1500/1800/2100/2400) as a disclosed, non-canonical extrapolation.
- Intra-tier walkthrough quests get ~1/4 of that tier's gate-quest spur value
  and a smaller, roughly-halved xp amount - "meaningful but not overpowered."
- No quest ever rewards a creative/duplication-risk item. create:creative_crate
  (and the other 3 "infinite" capstones) appear ONLY as required TASKS in the
  Jovian Frontier capstone quests, never as a reward - satisfies the explicit
  "don't hand it out early" instruction by not handing it out at all; the
  player must build it themselves, at the one tier it's gated to.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # repo root
QUESTS_DIR = ROOT / "pack" / "config" / "ftbquests" / "quests"


# ---------------------------------------------------------------------------
# Minimal SNBT serializer - identical grammar/behavior to the installed
# scripts/gen_quests.py (always double-quotes strings/keys, never emits type
# suffixes; both always-safe per FTBLibrary's SNBTParser.java + Minecraft's
# NumericTag cross-coercion on read).
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
# ID allocation + translation collection. Start well above the OLD chapter's
# own id range (0x10000-0x10019) so both books' ids never collide if the old
# file is ever left in place transiently during integration.
# ---------------------------------------------------------------------------
_next_id = [0x20000]


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
    return {"id": item_id, "count": count}


# ---------------------------------------------------------------------------
# Task builders
# ---------------------------------------------------------------------------
def stage_task(stage_id):
    return "gamestage", {"stage": stage_id}


def item_task(item_id, count=1, consume_items=True, only_from_crafting=False):
    d = {"item": item_stack(item_id, 1), "count": count}
    if not consume_items:
        d["consume_items"] = False
    if only_from_crafting:
        d["only_from_crafting"] = True
    return "item", d


def kill_task(entity_id, value=1):
    return "kill", {"entity": entity_id, "value": value}


def dimension_task(dimension_id):
    return "dimension", {"dimension": dimension_id}


def checkmark_task():
    return "checkmark", {}


# ---------------------------------------------------------------------------
# Reward builders
# ---------------------------------------------------------------------------
def item_reward(item_id, count=1):
    return "item", {"item": item_stack(item_id, count)}


def skill_xp_reward(category, amount):
    """See scripts/gen_quests.py's own skill_xp_reward() docstring for the
    full command-path research trail (net.puffish.skillsmod.commands.
    ExperienceCommand is a direct child of the "puffish_skills" root, NOT
    nested under "skills" - a real bug this exact command string already
    fixed once in this pack). permission_level 2 required (Commands.
    LEVEL_GAMEMASTERS) since the reward runs as the claiming player otherwise."""
    return "command", {
        "command": f"puffish_skills experience add {{p}} {category} {amount}",
        "permission_level": 2,
        "silent": True,
    }


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
    """Break a spur total into the largest-denomination coin ITEM rewards that
    fit, exactly mirroring economy.js's own payCoins() greedy algorithm - so a
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
# Quest/chapter builders (copied from scripts/gen_quests.py, extended with an
# optional "hide_deps" passthrough left unused - kept 1:1 with the proven
# original so this generator's core plumbing carries zero new risk).
# ---------------------------------------------------------------------------
def make_quest(quests_list, x, y, title, tasks, rewards, dependencies=None,
               desc=None, quest_icon=None):
    qid = new_id()
    set_title("quest", qid, title)
    if desc:
        set_quest_desc(qid, desc)

    q = {"id": hexid(qid), "x": float(x), "y": float(y)}
    if quest_icon:
        q["icon"] = item_stack(quest_icon)
    if dependencies:
        q["dependencies"] = [hexid(d) for d in dependencies]

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
# Reward-budget tables (see module docstring for the full anchoring rationale)
# ---------------------------------------------------------------------------
# index: 0 rootborn, 1 andesite, 2 brass, 3 precision, 4 induction, 5 starforged,
#        6 lunar, 7 martian, 8 inner_system, 9 jovian
GATE_SPURS = [2, 4, 16, 64, 256, 1024, 1024, 1152, 1280, 1536]
GATE_XP =    [20, 80, 150, 300, 600, 1200, 1500, 1800, 2100, 2400]
# intra-tier walkthrough quests: modest fraction of the SAME tier's gate budget
SIDE_SPURS = [1, 2, 4, 16, 64, 256, 256, 320, 384, 448]
SIDE_XP =    [10, 30, 50, 90, 150, 100, 150, 180, 200, 250]


# ===========================================================================
# Chapter 0 - Rootborn (starter chapter). Trivial by design (Tier 0 has no
# locks at all - rootborn.toml's own header: "wood, stone, and a furnace"),
# but still a real 1-to-1 walkthrough: get a stone tool, survive one fight,
# then push into Create's own material chain (andesite_alloy is the literal
# andesite_age trigger per triggers.toml).
# ===========================================================================
ROOTBORN_Q = {}


def build_rootborn(quests):
    welcome = make_quest(
        quests, 0, 0, "Welcome to Vanilla++",
        desc=["Punch some trees, then check this book after every tier-up - "
              "each chapter is a checklist for that tier's real progression."],
        tasks=[checkmark_task()],
        rewards=[skill_xp_reward("mining", 10)],
        quest_icon="minecraft:crafting_table",
    )
    stone_age = make_quest(
        quests, 2, -1, "Stone Age",
        desc=["Craft your first pickaxe through Silent Gear (any material) - "
              "the first real tool upgrade."],
        tasks=[item_task("silentgear:pickaxe", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[0])],
        dependencies=[welcome],
        quest_icon="minecraft:stone_pickaxe",
    )
    first_hunt = make_quest(
        quests, 2, 1, "First Blood",
        desc=["Kill a zombie. Combat matters from here on - Swords XP feeds "
              "directly into the RPG skill tree."],
        tasks=[kill_task("minecraft:zombie", 1)],
        rewards=[skill_xp_reward("swords", SIDE_XP[0])],
        dependencies=[welcome],
        quest_icon="minecraft:iron_sword",
    )
    gather_andesite = make_quest(
        quests, 4, 0, "Into Create's Material Chain",
        desc=["Craft or pick up Andesite Alloy - Create's own entry material, "
              "and the trigger for Andesite Age."],
        tasks=[item_task("create:andesite_alloy", only_from_crafting=True)],
        rewards=[*spur_rewards(GATE_SPURS[0]), skill_xp_reward("mining", GATE_XP[0])],
        dependencies=[stone_age, first_hunt],
        quest_icon="create:andesite_alloy",
    )
    ROOTBORN_Q["gather_andesite"] = gather_andesite


# ===========================================================================
# Chapter 1 - Andesite Age (Tier 1). Real content per andesite_age.toml +
# DESIGN.md: iron tools/armor, Tom's Storage "dumb storage", Ars Nouveau
# wand entry, jetpack rung 1, Power Loader rung 1, Ore Excavation entry kit,
# an optional Artifacts curio find (item 5 - deliberately NOT gated/required,
# a pure exploration bonus), then push into Brass Age via create:brass_ingot.
# ===========================================================================
ANDESITE_Q = {}


def build_andesite(quests):
    enter = make_quest(
        quests, 0, 0, "Enter the Andesite Age",
        desc=["Iron tools and Create's own machinery are open. This chapter "
              "is your Andesite Age checklist."],
        tasks=[stage_task("andesite_age")],
        rewards=[skill_xp_reward("mining", GATE_XP[1]), item_reward("create:andesite_alloy")],
        dependencies=[ROOTBORN_Q["gather_andesite"]],
        quest_icon="create:andesite_alloy",
    )
    iron_tools = make_quest(
        quests, 2, -2, "Iron Tools",
        desc=["Craft another Silent Gear pickaxe with this tier's material - "
              "the real mining-speed upgrade this tier unlocks."],
        tasks=[item_task("silentgear:pickaxe", only_from_crafting=True)],
        rewards=[skill_xp_reward("mining", SIDE_XP[1]), *spur_rewards(SIDE_SPURS[1])],
        dependencies=[enter], quest_icon="minecraft:iron_pickaxe",
    )
    dumb_storage = make_quest(
        quests, 2, -1, "Dumb Storage",
        desc=["Craft a Tom's Storage Inventory Connector - link your chests "
              "into one browsable network. No power, no autocrafting yet."],
        tasks=[item_task("toms_storage:inventory_connector", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[1]), *spur_rewards(SIDE_SPURS[1])],
        dependencies=[enter], quest_icon="toms_storage:inventory_connector",
    )
    jetpack_1 = make_quest(
        quests, 2, 0, "Copper Jetpack",
        desc=["Craft the Copper Jetpack - the first rung of the personal "
              "mobility ladder (Create Stuff & Additions)."],
        tasks=[item_task("create_sa:copper_jetpack_chestplate", only_from_crafting=True)],
        rewards=[skill_xp_reward("running", SIDE_XP[1]), *spur_rewards(SIDE_SPURS[1])],
        dependencies=[enter], quest_icon="create_sa:copper_jetpack_chestplate",
    )
    chunk_loader_1 = make_quest(
        quests, 2, 1, "Andesite Chunk Loader",
        desc=["Craft the Andesite Chunk Loader (Create: Power Loader). It "
              "only force-loads chunks while spun under real kinetic power."],
        tasks=[item_task("create_power_loader:andesite_chunk_loader", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[1]), *spur_rewards(SIDE_SPURS[1])],
        dependencies=[enter], quest_icon="create_power_loader:andesite_chunk_loader",
    )
    vein_hunting = make_quest(
        quests, 2, 2, "Vein Hunting",
        desc=["Craft a Vein Finder (Create Ore Excavation) - the entry-level "
              "scouting tool for this pack's ore-vein system."],
        tasks=[item_task("createoreexcavation:vein_finder", only_from_crafting=True)],
        rewards=[skill_xp_reward("mining", SIDE_XP[1]), *spur_rewards(SIDE_SPURS[1])],
        dependencies=[enter], quest_icon="createoreexcavation:vein_finder",
    )
    ars_wand = make_quest(
        quests, 2, 3, "The Mage's Path",
        desc=["Craft an Ars Nouveau wand - the entry point into this pack's "
              "spell-crafting magic system."],
        tasks=[item_task("ars_nouveau:wand", only_from_crafting=True)],
        rewards=[skill_xp_reward("magic", SIDE_XP[1]), *spur_rewards(SIDE_SPURS[1])],
        dependencies=[enter], quest_icon="ars_nouveau:wand",
    )
    curious_find = make_quest(
        quests, 2, 4, "A Curious Find (optional)",
        desc=["Find any Artifacts curio - they're pure exploration payoffs "
              "with no tier lock, hidden in structure loot at every rarity "
              "tier. This one just confirms you've found the umbrella."],
        tasks=[item_task("artifacts:umbrella", consume_items=False, only_from_crafting=False)],
        rewards=[skill_xp_reward("magic", SIDE_XP[1])],
        dependencies=[enter], quest_icon="artifacts:umbrella",
    )
    into_brass = make_quest(
        quests, 4, 0, "Into the Brass Age",
        desc=["Craft or pick up a Brass Ingot - Create's mid-game alloy, and "
              "the trigger for Brass Age."],
        tasks=[item_task("create:brass_ingot", only_from_crafting=True)],
        rewards=[*spur_rewards(GATE_SPURS[1]), skill_xp_reward("mining", GATE_XP[1])],
        dependencies=[iron_tools, dumb_storage, jetpack_1, chunk_loader_1, vein_hunting, ars_wand],
        quest_icon="create:brass_ingot",
    )
    ANDESITE_Q["into_brass"] = into_brass


# ===========================================================================
# Chapter 2 - Brass Age (Tier 2). Real automation begins: diamond gear, the
# Refined Storage network + its Create Crafts & Additions Alternator power
# bridge, the Mechanical Arm as first crafting automation, jetpack rung 2,
# Power Loader rung 2, Time in a Bottle (item 10), Create's own Trains, then
# push into Precision Age via create:sturdy_sheet.
# ===========================================================================
BRASS_Q = {}


def build_brass(quests):
    enter = make_quest(
        quests, 0, 0, "Enter the Brass Age",
        desc=["Automation begins in earnest. Diamond gear, the Nether, and a "
              "real powered storage network are all open now."],
        tasks=[stage_task("brass_age")],
        rewards=[skill_xp_reward("building", GATE_XP[2]), item_reward("create:brass_ingot")],
        dependencies=[ANDESITE_Q["into_brass"]],
        quest_icon="create:brass_ingot",
    )
    diamond_gear = make_quest(
        quests, 2, -3, "Diamond Gear",
        desc=["Craft another Silent Gear pickaxe with Brass Age's material - "
              "the tool-tier milestone for this age."],
        tasks=[item_task("silentgear:pickaxe", only_from_crafting=True)],
        rewards=[skill_xp_reward("daggers", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="minecraft:diamond_pickaxe",
    )
    real_network = make_quest(
        quests, 2, -2, "A Real Network",
        desc=["Craft a Refined Storage Controller - the heart of the powered "
              "network that replaces Tom's Storage from here on."],
        tasks=[item_task("refinedstorage:controller", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="refinedstorage:controller",
    )
    alternator = make_quest(
        quests, 2, -1, "Power the Network",
        desc=["Craft a Create Crafts & Additions Alternator - turns Create's "
              "own rotational power into the FE that runs Refined Storage."],
        tasks=[item_task("createaddition:alternator", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="createaddition:alternator",
    )
    automation_arm = make_quest(
        quests, 2, 0, "First Automation",
        desc=["Craft a Mechanical Arm - Create's own first crafting-automation "
              "block, feeding Refined Storage's Importer/Exporter."],
        tasks=[item_task("create:mechanical_arm", only_from_crafting=True)],
        rewards=[skill_xp_reward("spears", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="create:mechanical_arm",
    )
    jetpack_2 = make_quest(
        quests, 2, 1, "Andesite Jetpack",
        desc=["Craft the Andesite Jetpack - fuel-fired propellers, rung 2 of "
              "the mobility ladder."],
        tasks=[item_task("create_sa:andesite_jetpack_chestplate", only_from_crafting=True)],
        rewards=[skill_xp_reward("running", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="create_sa:andesite_jetpack_chestplate",
    )
    chunk_loader_2 = make_quest(
        quests, 2, 2, "Brass Chunk Loader",
        desc=["Craft the Brass Chunk Loader - the second and final Power "
              "Loader rung."],
        tasks=[item_task("create_power_loader:brass_chunk_loader", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="create_power_loader:brass_chunk_loader",
    )
    tiab = make_quest(
        quests, 2, 3, "Time in a Bottle",
        desc=["Craft the Time in a Bottle tick accelerator - one per player, "
              "and it won't speed up spawners."],
        tasks=[item_task("tiab:time_in_a_bottle", only_from_crafting=True)],
        rewards=[skill_xp_reward("mining", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="tiab:time_in_a_bottle",
    )
    trains = make_quest(
        quests, 2, 4, "Train Control",
        desc=["Craft a Track Station - Create's own Trains are a full Brass "
              "Age package now."],
        tasks=[item_task("create:track_station", only_from_crafting=True)],
        rewards=[skill_xp_reward("running", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="create:track_station",
    )
    diet_upgrade = make_quest(
        quests, 2, 5, "Sharper Knives",
        desc=["Craft a Farmer's Delight diamond knife - this is the real "
              "tier this pack's food-diet knife line reaches Brass Age "
              "(gold/diamond both unlock here; iron was Andesite Age, "
              "netherite is Precision Age)."],
        tasks=[item_task("farmersdelight:diamond_knife", only_from_crafting=True)],
        rewards=[skill_xp_reward("bows", SIDE_XP[2]), *spur_rewards(SIDE_SPURS[2])],
        dependencies=[enter], quest_icon="farmersdelight:diamond_knife",
    )
    master_alloy = make_quest(
        quests, 4, 0, "The Master Alloy",
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
# Chapter 3 - Precision Age (Tier 3). Netherite gear, wireless RS devices,
# jetpack rung 3, Elytra (found, not crafted), Farmer's Delight diamond knife
# (item 9), the Ore Excavation ceiling drill, then push into Induction Age
# via the netherite ingot pickup (this pack's own temporary Induction trigger).
# ===========================================================================
PRECISION_Q = {}


def build_precision(quests):
    enter = make_quest(
        quests, 0, 0, "Enter the Precision Age",
        desc=["Create's own endgame alloys are done. Netherite gear and The "
              "End are open."],
        tasks=[stage_task("precision_age")],
        rewards=[skill_xp_reward("swords", GATE_XP[3]), item_reward("create:sturdy_sheet")],
        dependencies=[BRASS_Q["master_alloy"]],
        quest_icon="create:sturdy_sheet",
    )
    netherite_gear = make_quest(
        quests, 2, -2, "Netherite Gear",
        desc=["Craft another Silent Gear pickaxe with Precision Age's material - "
              "the tool-tier milestone for this age."],
        tasks=[item_task("silentgear:pickaxe", only_from_crafting=True)],
        rewards=[skill_xp_reward("greatswords", SIDE_XP[3]), *spur_rewards(SIDE_SPURS[3])],
        dependencies=[enter], quest_icon="minecraft:netherite_pickaxe",
    )
    wireless = make_quest(
        quests, 2, -1, "Cut the Cables",
        desc=["Craft a Wireless Grid - manage your Refined Storage network "
              "from anywhere in range."],
        tasks=[item_task("refinedstorage:wireless_grid", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[3]), *spur_rewards(SIDE_SPURS[3])],
        dependencies=[enter], quest_icon="refinedstorage:wireless_grid",
    )
    jetpack_3 = make_quest(
        quests, 2, 0, "Brass Jetpack",
        desc=["Craft the Brass Jetpack - steam-fired, rung 3 of the mobility "
              "ladder, and the base item the Induction Age netherite jetpack "
              "smiths from."],
        tasks=[item_task("create_sa:brass_jetpack_chestplate", only_from_crafting=True)],
        rewards=[skill_xp_reward("running", SIDE_XP[3]), *spur_rewards(SIDE_SPURS[3])],
        dependencies=[enter], quest_icon="create_sa:brass_jetpack_chestplate",
    )
    elytra = make_quest(
        quests, 2, 1, "Wings",
        desc=["Find an Elytra in an End City - it's not craftable, just "
              "gated behind reaching this tier and finding one."],
        tasks=[item_task("minecraft:elytra", consume_items=False, only_from_crafting=False)],
        rewards=[skill_xp_reward("longswords", SIDE_XP[3]), *spur_rewards(SIDE_SPURS[3])],
        dependencies=[enter], quest_icon="minecraft:elytra",
    )
    diet_upgrade = make_quest(
        quests, 2, 2, "The Netherite Knife",
        desc=["Craft a Farmer's Delight netherite knife (a smithing upgrade "
              "from the diamond knife) - the ceiling of this pack's food-"
              "diet knife line, keeping your bonus-hearts diet variety topped "
              "up through Precision Age's grind."],
        tasks=[item_task("farmersdelight:netherite_knife", only_from_crafting=True)],
        rewards=[skill_xp_reward("bows", SIDE_XP[3]), *spur_rewards(SIDE_SPURS[3])],
        dependencies=[enter], quest_icon="farmersdelight:netherite_knife",
    )
    vein_ceiling = make_quest(
        quests, 2, 3, "The Netherite Drill",
        desc=["Craft the Netherite Drill - Create Ore Excavation's own tool "
              "ceiling, and what it takes to pull allthemodium/vibranium/"
              "unobtainium out of the ground."],
        tasks=[item_task("createoreexcavation:netherite_drill", only_from_crafting=True)],
        rewards=[skill_xp_reward("mining", SIDE_XP[3]), *spur_rewards(SIDE_SPURS[3])],
        dependencies=[enter], quest_icon="createoreexcavation:netherite_drill",
    )
    final_ingot = make_quest(
        quests, 4, 0, "The Final Ingot",
        desc=["Craft or pick up a Netherite Ingot - the temporary trigger for "
              "Induction Age, until a real narrative trigger replaces it."],
        tasks=[item_task("minecraft:netherite_ingot", only_from_crafting=True)],
        rewards=[*spur_rewards(GATE_SPURS[3]), skill_xp_reward("mining", GATE_XP[3])],
        dependencies=[netherite_gear, wireless, jetpack_3, elytra, diet_upgrade, vein_ceiling],
        quest_icon="minecraft:netherite_ingot",
    )
    PRECISION_Q["final_ingot"] = final_ingot


# ===========================================================================
# Chapter 4 - Induction Age (Tier 4). The Refined Storage ceiling (64k +
# native autocrafting), the final jetpack rung, Waystones teleportation,
# Create Aeronautics' top tier, the Silent Gear Allthemodium material floor,
# then the REAL trigger for Starforged Age: killing the Ender Dragon.
# ===========================================================================
INDUCTION_Q = {}


def build_induction(quests):
    enter = make_quest(
        quests, 0, 0, "Enter the Induction Age",
        desc=["Full storage-network automation: 64k capacity and native "
              "pattern-based autocrafting are online."],
        tasks=[stage_task("induction_age")],
        rewards=[skill_xp_reward("bows", GATE_XP[4]), item_reward("minecraft:netherite_ingot")],
        dependencies=[PRECISION_Q["final_ingot"]],
        quest_icon="minecraft:netherite_ingot",
    )
    autocrafting = make_quest(
        quests, 2, -2, "Native Autocrafting",
        desc=["Craft an Autocrafting Upgrade - Refined Storage's own "
              "pattern-based autocrafter, no more Mechanical Arm needed for "
              "storage automation."],
        tasks=[item_task("refinedstorage:autocrafting_upgrade", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[4]), *spur_rewards(SIDE_SPURS[4])],
        dependencies=[enter], quest_icon="refinedstorage:autocrafting_upgrade",
    )
    storage_ceiling = make_quest(
        quests, 2, -1, "64k Storage",
        desc=["Craft a 64k Storage Part - the ceiling of this pack's Refined "
              "Storage capacity chase (until the Jovian Frontier capstone)."],
        tasks=[item_task("refinedstorage:64k_storage_part", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[4]), *spur_rewards(SIDE_SPURS[4])],
        dependencies=[enter], quest_icon="refinedstorage:64k_storage_part",
    )
    jetpack_ceiling = make_quest(
        quests, 2, 0, "Netherite Jetpack",
        desc=["Craft the Netherite Jetpack - the final rung before "
              "Starforged Age grants true persistent flight outright."],
        tasks=[item_task("create_sa:netherite_jetpack_chestplate", only_from_crafting=True)],
        rewards=[skill_xp_reward("running", SIDE_XP[4]), *spur_rewards(SIDE_SPURS[4])],
        dependencies=[enter], quest_icon="create_sa:netherite_jetpack_chestplate",
    )
    teleport = make_quest(
        quests, 2, 1, "Teleportation",
        desc=["Craft a Waystone - intra-world teleportation, gated all the "
              "way to this tier on purpose."],
        tasks=[item_task("waystones:waystone", only_from_crafting=True)],
        rewards=[skill_xp_reward("running", SIDE_XP[4]), *spur_rewards(SIDE_SPURS[4])],
        dependencies=[enter], quest_icon="waystones:waystone",
    )
    steam_flight = make_quest(
        quests, 2, 2, "Steam-Powered Flight",
        desc=["Craft a Steam Vent (Create Aeronautics) - the passive, "
              "industrial-scale heat source for sustained airship lift."],
        tasks=[item_task("aeronautics:steam_vent", only_from_crafting=True)],
        rewards=[skill_xp_reward("tachi", SIDE_XP[4]), *spur_rewards(SIDE_SPURS[4])],
        dependencies=[enter], quest_icon="aeronautics:steam_vent",
    )
    gear_ceiling = make_quest(
        quests, 2, 3, "Allthemodium",
        desc=["Smelt an Allthemodium Ingot - this pack's own post-netherite "
              "Silent Gear material floor, carrying gear progression into "
              "the space tiers."],
        tasks=[item_task("allthemodium:allthemodium_ingot", only_from_crafting=True)],
        rewards=[skill_xp_reward("mining", SIDE_XP[4]), *spur_rewards(SIDE_SPURS[4])],
        dependencies=[enter], quest_icon="allthemodium:allthemodium_ingot",
    )
    dragon = make_quest(
        quests, 4, 0, "Conquer the End",
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
# Chapter 5 - Starforged Age (Tier 5). The space-travel gateway: persistent
# creative flight (stage-granted, nothing to craft - acknowledged with a
# checkmark), the first TFMG milestone (Aluminum Age), rocket parts, then
# launching into Earth orbit - the real trigger for Lunar Frontier.
# ===========================================================================
STARFORGED_Q = {}


def build_starforged(quests):
    enter = make_quest(
        quests, 0, 0, "Enter the Starforged Age",
        desc=["The overworld, Nether, and End are conquered. Space travel "
              "begins - and you can now toggle persistent flight outright."],
        tasks=[stage_task("starforged_age")],
        rewards=[skill_xp_reward("swimming", GATE_XP[5]), item_reward("minecraft:nether_star")],
        dependencies=[INDUCTION_Q["dragon"]],
        quest_icon="minecraft:nether_star",
    )
    flight_ack = make_quest(
        quests, 2, -1, "True Flight",
        desc=["Double-tap jump to toggle flight - it's granted the instant "
              "you reached this tier, no item or fuel required, and it "
              "survives death."],
        tasks=[checkmark_task()],
        rewards=[skill_xp_reward("running", SIDE_XP[5])],
        dependencies=[enter], quest_icon="minecraft:elytra",
    )
    leaderboard_check = make_quest(
        quests, 2, 0, "Check Your Rank (optional)",
        desc=["Run /leaderboard wealth, /leaderboard tier, or /leaderboard "
              "level to see how you and your team stack up."],
        tasks=[checkmark_task()],
        rewards=[skill_xp_reward("mining", SIDE_XP[5])],
        dependencies=[enter], quest_icon="numismatics:sun",
    )
    aluminum_age = make_quest(
        quests, 2, 1, "The Aluminum Age",
        desc=["Smelt a TFMG Aluminum Ingot - the first rung of the endgame "
              "automation ladder that carries all the way to Jupiter."],
        tasks=[item_task("tfmg:aluminum_ingot", only_from_crafting=True)],
        rewards=[skill_xp_reward("mining", SIDE_XP[5]), *spur_rewards(SIDE_SPURS[5])],
        dependencies=[enter], quest_icon="tfmg:aluminum_ingot",
    )
    rocket_parts = make_quest(
        quests, 2, 2, "Rocket Parts",
        desc=["Craft a Rocket Engine (Stellaris) - one of the core "
              "components of your first rocket."],
        tasks=[item_task("stellaris:rocket_engine", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[5]), *spur_rewards(SIDE_SPURS[5])],
        dependencies=[aluminum_age], quest_icon="stellaris:rocket_engine",
    )
    launch = make_quest(
        quests, 4, 0, "Liftoff",
        desc=["Launch your rocket and reach Earth orbit - the real trigger "
              "for Lunar Frontier."],
        tasks=[dimension_task("stellaris:earth_orbit")],
        rewards=[*spur_rewards(GATE_SPURS[5]), skill_xp_reward("running", GATE_XP[5])],
        dependencies=[rocket_parts],
        quest_icon="stellaris:rocket",
    )
    STARFORGED_Q["launch"] = launch


# ===========================================================================
# Chapter 6 - Lunar Frontier (Tier 6). First space tier: the shared
# Unobtainium Silent Gear floor, TFMG's Steel Age milestone, then landing on
# the Moon (the real trigger for Martian Frontier).
# ===========================================================================
LUNAR_Q = {}


def build_lunar(quests):
    enter = make_quest(
        quests, 0, 0, "Enter the Lunar Frontier",
        desc=["You've reached orbit. The Moon is next."],
        tasks=[stage_task("lunar_frontier")],
        rewards=[skill_xp_reward("mining", GATE_XP[6]), item_reward("allthemodium:unobtainium_ingot")],
        dependencies=[STARFORGED_Q["launch"]],
        quest_icon="stellaris:rocket",
    )
    steel_age = make_quest(
        quests, 2, 0, "The Steel Age",
        desc=["Smelt a TFMG Steel Ingot - the mod's own core metallurgy "
              "chain, rung 2 of the endgame automation ladder."],
        tasks=[item_task("tfmg:steel_ingot", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[6]), *spur_rewards(SIDE_SPURS[6])],
        dependencies=[enter], quest_icon="tfmg:steel_ingot",
    )
    moon_landing = make_quest(
        quests, 4, 0, "One Small Step",
        desc=["Travel to the Moon - the real trigger for Martian Frontier."],
        tasks=[dimension_task("stellaris:moon")],
        rewards=[*spur_rewards(GATE_SPURS[6]), skill_xp_reward("running", GATE_XP[6])],
        dependencies=[steel_age], quest_icon="minecraft:end_crystal",
    )
    LUNAR_Q["moon_landing"] = moon_landing


# ===========================================================================
# Chapter 7 - Martian Frontier (Tier 7). TFMG's Petrochemical Age milestone,
# then landing on Mars (the real trigger for Inner System).
# ===========================================================================
MARTIAN_Q = {}


def build_martian(quests):
    enter = make_quest(
        quests, 0, 0, "Enter the Martian Frontier",
        desc=["The Moon is conquered. Mars is next."],
        tasks=[stage_task("martian_frontier")],
        rewards=[skill_xp_reward("mining", GATE_XP[7]), item_reward("tfmg:diesel_bucket")],
        dependencies=[LUNAR_Q["moon_landing"]],
        quest_icon="minecraft:redstone",
    )
    petrochemical = make_quest(
        quests, 2, 0, "The Petrochemical Age",
        desc=["Refine a bucket of Diesel (TFMG) - rung 3 of the endgame "
              "automation ladder."],
        tasks=[item_task("tfmg:diesel_bucket", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[7]), *spur_rewards(SIDE_SPURS[7])],
        dependencies=[enter], quest_icon="tfmg:diesel_bucket",
    )
    mars_landing = make_quest(
        quests, 4, 0, "Red Planet",
        desc=["Travel to Mars - the real trigger for Inner System."],
        tasks=[dimension_task("stellaris:mars")],
        rewards=[*spur_rewards(GATE_SPURS[7]), skill_xp_reward("running", GATE_XP[7])],
        dependencies=[petrochemical], quest_icon="minecraft:redstone_block",
    )
    MARTIAN_Q["mars_landing"] = mars_landing


# ===========================================================================
# Chapter 8 - Inner System (Tier 8). TFMG's Electrical Age milestone, then
# two OPTIONAL parallel landings (Venus / Mercury - either alone triggers
# Jovian Frontier per triggers.toml, so neither is a required dependency of
# the next chapter's gate quest).
# ===========================================================================
INNER_Q = {}


def build_inner(quests):
    enter = make_quest(
        quests, 0, 0, "Enter the Inner System",
        desc=["Mars is conquered. Venus and Mercury - both extreme, "
              "comparably hostile - are next."],
        tasks=[stage_task("inner_system")],
        rewards=[skill_xp_reward("mining", GATE_XP[8]), item_reward("tfmg:electric_motor")],
        dependencies=[MARTIAN_Q["mars_landing"]],
        quest_icon="minecraft:magma_block",
    )
    electrical_age = make_quest(
        quests, 2, 0, "The Electrical Age",
        desc=["Craft a TFMG Converter - bridges TFMG's own power grid into "
              "Create/FE, rung 4 of the endgame automation ladder."],
        tasks=[item_task("tfmg:converter", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[8]), *spur_rewards(SIDE_SPURS[8])],
        dependencies=[enter], quest_icon="tfmg:converter",
    )
    venus_landing = make_quest(
        quests, 4, -1, "Morning Star (optional)",
        desc=["Travel to Venus - either inner planet triggers Jovian "
              "Frontier, so this and Mercury are both optional."],
        tasks=[dimension_task("stellaris:venus")],
        rewards=[skill_xp_reward("running", SIDE_XP[8]), *spur_rewards(SIDE_SPURS[8])],
        dependencies=[electrical_age], quest_icon="minecraft:magma_block",
    )
    mercury_landing = make_quest(
        quests, 4, 1, "Swift Planet (optional)",
        desc=["Travel to Mercury - either inner planet triggers Jovian "
              "Frontier, so this and Venus are both optional."],
        tasks=[dimension_task("stellaris:mercury")],
        rewards=[skill_xp_reward("running", SIDE_XP[8]), *spur_rewards(SIDE_SPURS[8])],
        dependencies=[electrical_age], quest_icon="minecraft:magma_block",
    )
    INNER_Q["electrical_age"] = electrical_age


# ===========================================================================
# Chapter 9 - Jovian Frontier (Tier 9, final). TFMG's Combustion Age
# milestone (ladder ceiling), then the three real "infinite" capstones - each
# a required CRAFTING TASK here, never a reward, so create:creative_crate is
# never handed out early, only ever earned by building it yourself at the one
# tier it's meant for.
# ===========================================================================
def build_jovian(quests):
    enter = make_quest(
        quests, 0, 0, "Enter the Jovian Frontier",
        desc=["The inner system is conquered. Jupiter - the current edge of "
              "Stellaris' explorable system - is the final frontier."],
        tasks=[stage_task("jovian_frontier")],
        rewards=[skill_xp_reward("mining", GATE_XP[9]),
                 item_reward("allthemodium:unobtainium_vibranium_alloy_ingot")],
        dependencies=[INNER_Q["electrical_age"]],
        quest_icon="minecraft:end_crystal",
    )
    combustion_age = make_quest(
        quests, 2, 0, "The Combustion Age",
        desc=["Craft a TFMG Engine Cylinder - the final rung of the endgame "
              "automation ladder."],
        tasks=[item_task("tfmg:engine_cylinder", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[9]), *spur_rewards(SIDE_SPURS[9])],
        dependencies=[enter], quest_icon="tfmg:engine_cylinder",
    )
    storage_infinity = make_quest(
        quests, 4, -1, "Infinite Storage",
        desc=["Craft a Refined Storage Creative Storage Block - genuinely "
              "infinite item capacity, the true ceiling of the storage "
              "chase started back at Andesite Age."],
        tasks=[item_task("refinedstorage:creative_storage_block", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[9] + 50), *spur_rewards(SIDE_SPURS[9])],
        dependencies=[combustion_age], quest_icon="refinedstorage:creative_storage_block",
    )
    energy_infinity = make_quest(
        quests, 4, 0, "Infinite Energy",
        desc=["Craft a Create Creative Motor - a genuinely endless source of "
              "Rotational Force, bridged to FE the same way every earlier "
              "power step in this pack has been."],
        tasks=[item_task("create:creative_motor", only_from_crafting=True)],
        rewards=[skill_xp_reward("building", SIDE_XP[9] + 50), *spur_rewards(SIDE_SPURS[9])],
        dependencies=[combustion_age], quest_icon="create:creative_motor",
    )
    resource_infinity = make_quest(
        quests, 4, 1, "Infinite Resources",
        desc=["Craft a Create Creative Crate - an endless supply of any one "
              "item you configure. This is the hardest, latest-gated craft "
              "in the entire pack for a reason - guard it accordingly."],
        tasks=[item_task("create:creative_crate", only_from_crafting=True)],
        rewards=[skill_xp_reward("mining", SIDE_XP[9] + 50), *spur_rewards(SIDE_SPURS[9])],
        dependencies=[combustion_age], quest_icon="create:creative_crate",
    )
    make_quest(
        quests, 6, 0, "Journey's End",
        desc=["Every tier from Rootborn to Jupiter, done. Future updates may "
              "extend the ladder further out into the solar system - this "
              "book will grow to meet them."],
        tasks=[checkmark_task()],
        rewards=[*spur_rewards(GATE_SPURS[9]), skill_xp_reward("mining", GATE_XP[9])],
        dependencies=[storage_infinity, energy_infinity, resource_infinity],
        quest_icon="minecraft:nether_star",
    )


# ---------------------------------------------------------------------------
# Assemble + write
# ---------------------------------------------------------------------------
def main():
    chapters_dir = QUESTS_DIR / "chapters"
    lang_dir = QUESTS_DIR / "lang"
    chapters_dir.mkdir(parents=True, exist_ok=True)
    lang_dir.mkdir(parents=True, exist_ok=True)

    chapter_defs = [
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

    written = []
    for i, (filename, title, subtitle, builder, chap_icon) in enumerate(chapter_defs):
        chapter = make_chapter(filename, title, subtitle, builder, order_index=i, chapter_icon=chap_icon)
        (chapters_dir / f"{filename}.snbt").write_text(snbt(chapter) + "\n")
        written.append((filename, len(chapter["quests"])))
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

    total_quests = sum(n for _, n in written)
    print(f"wrote data.snbt, chapter_groups.snbt, lang/en_us.snbt ({len(translations)} translation keys)")
    print(f"TOTAL: {len(written)} chapters, {total_quests} quests")


if __name__ == "__main__":
    main()
