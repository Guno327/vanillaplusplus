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
"""
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "pack" / "kubejs" / "data" / "minecraft" / "loot_table"


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


# Bonus pool per tier - one extra guaranteed roll (rolls: 1, bonus_rolls: 0)
# appended alongside whatever the vanilla pools already grant. Currency scale
# mirrors gen_economy.py's own coin denominations (spur=1 ... sun=4096);
# material bonuses mirror the tier ladder's own unlock-trigger items.
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
            empty_entry(4),
        ],
    },
}


def main():
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
