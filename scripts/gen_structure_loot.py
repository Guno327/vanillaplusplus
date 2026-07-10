#!/usr/bin/env python3
"""Generate reward-scaling overrides for vanilla structure chest loot tables
into pack/kubejs/data/minecraft/loot_table/chests/**.json (KubeJS's raw
datapack injection folder, same mechanism already used for the boss loot
overrides in pack/kubejs/data/apotheosis/loot_table/ and
pack/kubejs/data/minecraft/loot_table/entities/).

instructions.md: "Structures should have rewards that scale with their
probability of being discovered." Dungeons and Taverns (Phase 8) already
reworks loot *variety* across most vanilla structures but explicitly did not
tune reward *scaling* by structure rarity/danger (see DESIGN.md's Phase 8
notes) - this script is that missing half.

Approach: each target structure is bucketed into one of four tiers (COMMON /
UNCOMMON / RARE / EPIC, judged by real danger + vanilla structure_set spacing
- see TIERS below) and gets one extra loot pool *appended* on top of its full
vanilla loot table (not a replacement - NeoForge's datapack loading has no
merge semantics for loot tables, a KubeJS data/ override fully replaces the
target id, so the vanilla pools are copied byte-for-byte from the actual
installed vanilla data jar and the bonus pool is added alongside them).

The bonus pool's contents are deliberately drawn from this pack's OWN
progression signals rather than invented flavor items: Numismatics currency
(scaling tier-for-tier with gen_economy.py's own denominations), the tier
ladder's own trigger materials (create:brass_ingot for Brass Age,
create:refined_radiance/shadow_steel for Precision Age, allthemodium for
Induction Age - picking one up legitimately advances a player's stage, same
"pick up" trigger the tier ladder table already documents), and Apotheosis
gems restricted to a rising Purity floor for the two upper tiers (purity
enum values/JSON field confirmed by decompiling GemLootPoolEntry.class and
Purity.class in the installed Apotheosis jar, not guessed - the "quality"
field already used elsewhere in this pack's apotheosis loot overrides is a
different, vanilla-standard field (weight-vs-luck interaction), not a
rarity floor).

Re-run this after any Minecraft version bump (vanilla loot tables may change)
or after editing TIERS/bonus pool contents below. Requires a synced server/
(python3 scripts/build_server.py, then boot at least once so NeoForge's
installer has downloaded the vanilla data jar) - see HANDOFF.md's boot-test
recipe.

--------------------------------------------------------------------------
TODO.md item 5 ("Curios as a discoverable/upgradeable player-ability
system") - Artifacts 13.2.1 integration
--------------------------------------------------------------------------
Decision: curios (Artifacts mod trinkets) hook into these SAME four rarity
tiers rather than getting a separate discovery system - see TODO.md item 5's
"Discovery mechanism" decision. Artifacts' own native loot injection (GLMs
under data/artifacts/loot_modifiers/inject/**, rolling the per-structure
tables under data/artifacts/loot_table/inject/**) was silenced entirely via
empty-pool overrides in pack/kubejs/data/artifacts/loot_table/inject/**
(verified against the actually-installed 13.2.1 jar: 35 inject tables, 30
chests + 5 archaeology; its 2 entity-drop GLMs, cow/mooshroom -> Everlasting
Beef, were left native since they're trivial and off this script's structure-
loot mechanism entirely) so this script becomes artifacts' ONLY placement
path, keeping one rarity system instead of two competing ones.

CURATION TABLE (all 48 items in Artifacts 13.2.1's own data/artifacts/tags/
item/artifacts.json master tag, ground-truthed by extracting the jar and
counting programmatically - not guessed from item names; the task brief's
"47 items" was off by one against this actual tag, see curios_upgrades.js's
matching deviation note). Judged from each item's actual effect, read out of
the mod's assets/artifacts/lang/en_us.json config-description strings (e.g.
"artifacts.config.items.crystal_heart.healthBonus.description") plus its
Curios equip-slot tag (data/artifacts/tags/item/slot/*.json), since a few
items are genuinely borderline and the equip slot was a useful tie-breaker
(a permanent worn stat item reads as more "build-defining" than a proc-on-
hit trinket in the same slot). Weights stay modest per TODO.md item 5's
"usable immediately on pickup, no tier lock, but shouldn't trivialize early
game" tension - see ARTIFACT_BUCKET_WEIGHT below for exactly how modest.

  COMMON (18) - pure minor trinkets, cosmetic, or basic one-note QoL:
    everlasting_beef, eternal_steak  (infinite food; eternal_steak is
      Artifacts' own smelted upgrade of everlasting_beef, not itself found
      in a chest, but a fine direct loot roll for this pack's own pool)
    plastic_drinking_hat, novelty_drinking_hat  (eating/drinking speed)
    snorkel, night_vision_goggles  (basic single-effect utility)
    villager_hat  (trade discount)            cowboy_hat  (mount speed)
    anglers_hat  (fishing luck/lure)          charm_of_shrinking  (scale)
    antidote_vessel  (shorter negative effects)
    universal_attractor  (item magnetism)     onion_ring  (haste on eat)
    pocket_piston  (knockback, weak)          snowshoes  (snow speed)
    kitty_slippers  (repels creepers/phantoms, mostly cosmetic)
    whoopee_cushion  (pure joke item)         flippers  (swim speed)

  UNCOMMON (19) - moderate utility or situational (chance/proc-based)
  combat perks - stronger than COMMON but not a build-around:
    superstitious_hat  (looting)              lucky_scarf  (fortune)
    cross_necklace  (post-hit invincibility)  panic_necklace  (post-hit speed)
    shock_pendant  (retaliate lightning)      flame_pendant  (retaliate fire)
    thorn_pendant  (retaliate damage)         charm_of_sinking  (no water collision)
    obsidian_skull  (post-fire fire resist)   golden_hook  (bonus XP)
    withered_bracelet  (retaliate wither)     aqua_dashers  (sprint on water)
    bunny_hoppers  (fall damage/jump)         running_shoes  (sprint speed)
    steadfast_spikes  (knockback resist)      rooted_boots  (hunger regen)
    strider_shoes  (lava-safe sneaking)       pickaxe_heater  (auto-smelt QoL)
    fire_gauntlet  (melee attacks set target on fire, moderate combat proc)

  RARE (8) - strong combat/mobility per the task's own split rule, plus one
  explicit utility exception (digging_claws - a tool-tier bypass is
  genuinely powerful, not a minor trinket, even though it's neither combat
  nor mobility):
    cloud_in_a_bottle  (double jump)          helium_flamingo  (temp flight)
    warp_drive  (free/harmless ender pearls)  digging_claws  (mining speed +
      tool-tier upgrade - utility exception, see above)
    feral_claws  (attack speed)               power_glove  (attack damage)
    vampiric_glove  (lifesteal)                umbrella  (glide/shield,
      held not worn - see curios_upgrades.js's HELD_ITEMS note)

  EPIC (3) - genuinely build-defining, capstone-tier finds:
    crystal_heart  (permanent +health, a heart-container equivalent)
    chorus_totem  (death-protection teleport, a totem-of-undying analog)
    scarf_of_invisibility  (full invisibility while worn)

Mechanism: rather than inlining 48 items into TIERS' bonus_pool lambdas
directly (which would force every tier's pool to enumerate its whole
artifact list inline), each bucket is written out as its own small nested
loot table under pack/kubejs/data/artifacts/loot_table/vpp_bucket/<tier>.json
(uniform weight-1 per item + its own empty-weight backstop, same "weighted
entries with an empty-weight backstop" pattern the rest of this script
already uses) and each tier's top-level bonus pool gets ONE new entry - a
`minecraft:loot_table` reference to that nested table - at a modest weight
(see ARTIFACT_BUCKET_WEIGHT). Two independent backstops (top-level pool AND
the nested bucket table) compound multiplicatively, landing every tier at a
roughly similar ~5-6% chance of finding *some* artifact per chest visit
(deliberately tier-flat) while the *quality* of what you might find still
scales hard with tier (COMMON-bucket items in a COMMON-tier chest, EPIC-
bucket items only in the 4 rarest structures in the game) - "an artifact is
a lucky find, not a guaranteed drop" per TODO.md item 5's own wording.
"""
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "pack" / "kubejs" / "data" / "minecraft" / "loot_table"
ARTIFACTS_OUT_DIR = ROOT / "pack" / "kubejs" / "data" / "artifacts" / "loot_table" / "vpp_bucket"


def find_vanilla_data_jar():
    candidates = sorted(
        (ROOT / "server" / "libraries" / "net" / "minecraft" / "server").glob("*/*-extra.jar")
    )
    if not candidates:
        raise SystemExit(
            "no vanilla '*-extra.jar' found under server/libraries/net/minecraft/server/ - "
            "boot the server at least once first (see HANDOFF.md's boot-test recipe) so "
            "NeoForge's installer has downloaded it."
        )
    return candidates[-1]


def load_vanilla_loot_table(jar_path, relative_id):
    with zipfile.ZipFile(jar_path) as z:
        return json.loads(z.read(f"data/minecraft/loot_table/{relative_id}.json"))


def uniform_count(min_v, max_v):
    return {"function": "minecraft:set_count", "add": False, "count": {"type": "minecraft:uniform", "min": min_v, "max": max_v}}


def item_entry(item_id, weight, count=None):
    entry = {"type": "minecraft:item", "name": item_id, "weight": weight}
    if count:
        entry["functions"] = [uniform_count(*count)]
    return entry


def gem_entry(weight, purities):
    return {"type": "apotheosis:random_gem", "weight": weight, "quality": 1, "purities": purities}


def empty_entry(weight):
    return {"type": "minecraft:empty", "weight": weight}


def artifact_bucket_entry(tier_name, weight):
    """Nested-table reference into pack/kubejs/data/artifacts/loot_table/
    vpp_bucket/<tier>.json (written by write_artifact_buckets() below) -
    the module docstring's "Mechanism" section explains why this is a
    nested table rather than 48 items inlined into TIERS directly."""
    return {
        "type": "minecraft:loot_table",
        "value": f"artifacts:vpp_bucket/{tier_name.lower()}",
        "weight": weight,
    }


# See the module docstring's CURATION TABLE for the reasoning behind each
# item's bucket. Ids are bare (no "artifacts:" prefix) - write_artifact_
# buckets() qualifies them. Order within each tier is cosmetic (loot weight
# is uniform per item within a bucket - see ARTIFACT_BUCKET_BACKSTOP).
ARTIFACT_BUCKETS = {
    "COMMON": [
        "everlasting_beef", "eternal_steak", "plastic_drinking_hat",
        "novelty_drinking_hat", "snorkel", "night_vision_goggles",
        "villager_hat", "cowboy_hat", "anglers_hat", "charm_of_shrinking",
        "antidote_vessel", "universal_attractor", "onion_ring",
        "pocket_piston", "snowshoes", "kitty_slippers", "whoopee_cushion",
        "flippers",
    ],
    "UNCOMMON": [
        "superstitious_hat", "lucky_scarf", "cross_necklace",
        "panic_necklace", "shock_pendant", "flame_pendant", "thorn_pendant",
        "charm_of_sinking", "obsidian_skull", "golden_hook",
        "withered_bracelet", "aqua_dashers", "bunny_hoppers",
        "running_shoes", "steadfast_spikes", "rooted_boots",
        "strider_shoes", "pickaxe_heater", "fire_gauntlet",
    ],
    "RARE": [
        "cloud_in_a_bottle", "helium_flamingo", "warp_drive",
        "digging_claws", "feral_claws", "power_glove", "vampiric_glove",
        "umbrella",
    ],
    "EPIC": [
        "crystal_heart", "chorus_totem", "scarf_of_invisibility",
    ],
}

# Empty-weight backstop *within* each nested bucket table (independent of,
# and multiplicative with, the top-level empty_entry() backstop each tier's
# bonus_pool already has) - see the docstring's "Mechanism" section for the
# resulting ~5-6%-per-chest-visit math. Roughly: COMMON/RARE = 50/50 odds
# once you've rolled into the bucket at all, UNCOMMON a bit better, EPIC
# deliberately worse since these are the 3 capstone-tier items.
ARTIFACT_BUCKET_BACKSTOP = {
    "COMMON": 18,
    "UNCOMMON": 14,
    "RARE": 8,
    "EPIC": 5,
}

# Weight of the artifact_bucket_entry() reference inside each tier's own
# top-level bonus pool (out of that pool's total weight, existing entries
# included) - kept low on purpose, same "lucky find" reasoning as above.
ARTIFACT_BUCKET_WEIGHT = 2


def write_artifact_buckets():
    """Write the 4 nested artifacts loot tables this script's bonus pools
    reference via artifact_bucket_entry(). Separate from OUT_DIR/main()'s
    per-structure loop since these aren't structure overrides - they're new
    standalone tables, written once regardless of how many structures end
    up referencing them."""
    for tier_name, item_ids in ARTIFACT_BUCKETS.items():
        entries = [item_entry(f"artifacts:{item_id}", 1) for item_id in item_ids]
        entries.append(empty_entry(ARTIFACT_BUCKET_BACKSTOP[tier_name]))
        table = {"pools": [{"rolls": 1.0, "bonus_rolls": 0.0, "entries": entries}]}
        out_path = ARTIFACTS_OUT_DIR / f"{tier_name.lower()}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(table, indent=2) + "\n")
    print(f"wrote {len(ARTIFACT_BUCKETS)} artifact bucket tables to {ARTIFACTS_OUT_DIR}")


# Bonus pool per tier - one extra guaranteed roll (rolls: 1, bonus_rolls: 0)
# appended alongside whatever the vanilla pools already grant. Currency scale
# mirrors gen_economy.py's own coin denominations (spur=1 ... sun=4096);
# material bonuses mirror the tier ladder's own unlock-trigger items; the
# artifact_bucket_entry() call in each pool is this script's TODO.md item 5
# hookup - see the module docstring for the curation/weighting rationale.
TIERS = {
    "COMMON": {
        # early-game, low-danger structures: dense spacing, reachable on foot
        # with wood/stone gear.
        "loot_tables": [
            "chests/abandoned_mineshaft",
            "chests/desert_pyramid",
            "chests/jungle_temple",
            "chests/jungle_temple_dispenser",
            "chests/igloo_chest",
            "chests/ruined_portal",
            "chests/pillager_outpost",
            "chests/simple_dungeon",
            "chests/village/village_armorer",
            "chests/village/village_butcher",
            "chests/village/village_cartographer",
            "chests/village/village_desert_house",
            "chests/village/village_fisher",
            "chests/village/village_fletcher",
            "chests/village/village_mason",
            "chests/village/village_plains_house",
            "chests/village/village_savanna_house",
            "chests/village/village_shepherd",
            "chests/village/village_snowy_house",
            "chests/village/village_taiga_house",
            "chests/village/village_tannery",
            "chests/village/village_temple",
            "chests/village/village_toolsmith",
            "chests/village/village_weaponsmith",
        ],
        "bonus_pool": lambda: [
            item_entry("numismatics:spur", 6, (4, 10)),
            item_entry("numismatics:bevel", 3, (1, 3)),
            item_entry("minecraft:iron_ingot", 3, (1, 4)),
            artifact_bucket_entry("COMMON", ARTIFACT_BUCKET_WEIGHT),
            empty_entry(6),
        ],
    },
    "UNCOMMON": {
        # Nether/ocean structures: real travel + combat risk to reach.
        "loot_tables": [
            "chests/nether_bridge",
            "chests/bastion_bridge",
            "chests/bastion_hoglin_stable",
            "chests/bastion_other",
            "chests/shipwreck_map",
            "chests/shipwreck_supply",
            "chests/shipwreck_treasure",
            "chests/underwater_ruin_small",
            "chests/underwater_ruin_big",
            "chests/buried_treasure",
            "chests/trial_chambers/corridor",
            "chests/trial_chambers/entrance",
            "chests/trial_chambers/intersection",
            "chests/trial_chambers/intersection_barrel",
            "chests/trial_chambers/supply",
        ],
        "bonus_pool": lambda: [
            item_entry("numismatics:bevel", 4, (2, 5)),
            item_entry("numismatics:sprocket", 3, (1, 3)),
            item_entry("create:brass_ingot", 2, (1, 3)),
            item_entry("minecraft:diamond", 2, (1, 2)),
            artifact_bucket_entry("UNCOMMON", ARTIFACT_BUCKET_WEIGHT),
            empty_entry(5),
        ],
    },
    "RARE": {
        # endgame overworld/Nether danger: strongholds, bastion treasure
        # rooms, ancient cities, deep trial chamber vaults.
        "loot_tables": [
            "chests/bastion_treasure",
            "chests/stronghold_corridor",
            "chests/stronghold_crossing",
            "chests/stronghold_library",
            "chests/ancient_city",
            "chests/ancient_city_ice_box",
            "chests/trial_chambers/reward",
            "chests/trial_chambers/reward_common",
            "chests/trial_chambers/reward_rare",
            "chests/trial_chambers/reward_ominous",
            "chests/trial_chambers/reward_ominous_common",
            "chests/trial_chambers/reward_ominous_rare",
        ],
        "bonus_pool": lambda: [
            item_entry("numismatics:sprocket", 3, (2, 4)),
            item_entry("numismatics:cog", 3, (1, 2)),
            item_entry("create:refined_radiance", 1, (1, 1)),
            item_entry("create:shadow_steel", 1, (1, 1)),
            gem_entry(2, ["normal", "flawless"]),
            artifact_bucket_entry("RARE", ARTIFACT_BUCKET_WEIGHT),
            empty_entry(6),
        ],
    },
    "EPIC": {
        # the rarest, most dangerous structures in the game.
        "loot_tables": [
            "chests/end_city_treasure",
            "chests/woodland_mansion",
            "chests/trial_chambers/reward_unique",
            "chests/trial_chambers/reward_ominous_unique",
        ],
        "bonus_pool": lambda: [
            item_entry("numismatics:cog", 3, (2, 3)),
            item_entry("numismatics:crown", 2, (1, 2)),
            item_entry("allthemodium:allthemodium_ingot", 1, (1, 1)),
            gem_entry(2, ["flawless", "perfect"]),
            artifact_bucket_entry("EPIC", ARTIFACT_BUCKET_WEIGHT),
            empty_entry(4),
        ],
    },
}


def main():
    write_artifact_buckets()
    jar_path = find_vanilla_data_jar()
    written = 0
    for tier_name, tier in TIERS.items():
        bonus_entries = tier["bonus_pool"]()
        for relative_id in tier["loot_tables"]:
            table = load_vanilla_loot_table(jar_path, relative_id)
            table["pools"].append({"rolls": 1.0, "bonus_rolls": 0.0, "entries": bonus_entries})
            out_path = OUT_DIR / f"{relative_id}.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(table, indent=2) + "\n")
            written += 1
        print(f"{tier_name}: {len(tier['loot_tables'])} loot tables")
    print(f"wrote {written} loot table overrides to {OUT_DIR} (source: {jar_path.name})")


if __name__ == "__main__":
    main()
