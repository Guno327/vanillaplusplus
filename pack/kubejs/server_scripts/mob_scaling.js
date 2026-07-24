// instructions.md: "Mobs should scale" - areas farther from spawn/harder
// dimensions should spawn tougher monsters, the player should be able to
// tell by looking, rewards should scale with difficulty, and the
// player(s) responsible for the spawn should influence base difficulty via
// their own progression. Apotheosis' Elites/Invaders (installed this phase)
// give visually-distinct "boosted" mobs with scaled loot, but their spawn
// chance is flat/random everywhere (confirmed via its own in-game
// documentation - "these mobs will appear randomly in place of their
// normal counterparts") - not zone-scaled. This script is a separate,
// independent layer on top of vanilla mob attributes (not hooking into
// Apotheosis' own internal chance system, which would be far more fragile
// to integrate with reliably) that specifically covers the zone/
// player-progression-scaling half of the requirement.
const MONSTER_TYPES = new Set([
    'minecraft:zombie', 'minecraft:husk', 'minecraft:drowned', 'minecraft:skeleton',
    'minecraft:stray', 'minecraft:spider', 'minecraft:cave_spider', 'minecraft:creeper',
    'minecraft:enderman', 'minecraft:witch', 'minecraft:phantom', 'minecraft:pillager',
    'minecraft:vindicator', 'minecraft:evoker', 'minecraft:ravager', 'minecraft:blaze',
    'minecraft:wither_skeleton', 'minecraft:magma_cube', 'minecraft:ghast',
    'minecraft:piglin_brute', 'minecraft:hoglin', 'minecraft:zoglin',
    'minecraft:guardian', 'minecraft:elder_guardian', 'minecraft:shulker',
    'minecraft:silverfish', 'minecraft:endermite', 'minecraft:vex',

    // Creeper Overhaul 4.0.6 - 16 biome-flavored creeper variants (all
    // wild-spawning, confirmed via the mod's own neoforge/biome_modifier
    // add_spawns entries; drops are 100% vanilla so no loot override was
    // needed for this mod - see TODO.md item 6).
    'creeperoverhaul:badlands_creeper', 'creeperoverhaul:bamboo_creeper',
    'creeperoverhaul:beach_creeper', 'creeperoverhaul:birch_creeper',
    'creeperoverhaul:cave_creeper', 'creeperoverhaul:dark_oak_creeper',
    'creeperoverhaul:desert_creeper', 'creeperoverhaul:dripstone_creeper',
    'creeperoverhaul:hills_creeper', 'creeperoverhaul:jungle_creeper',
    'creeperoverhaul:mushroom_creeper', 'creeperoverhaul:ocean_creeper',
    'creeperoverhaul:savannah_creeper', 'creeperoverhaul:snowy_creeper',
    'creeperoverhaul:spruce_creeper', 'creeperoverhaul:swamp_creeper',

    // Born in Chaos 1.7.6 - 45 wild-spawning hostiles (confirmed via the
    // mod's own neoforge/biome_modifier add_spawns entries; note the
    // mod's real namespace is "born_in_chaos_v1", not "borninchaos" - the
    // Modrinth slug doesn't match the jar's registered namespace). Loot
    // tables were normalized to a vanilla-canonical set in
    // pack/kubejs/data/born_in_chaos_v1/loot_table/entities/** per
    // TODO.md item 6; unique weapon/armor drops were stripped.
    'born_in_chaos_v1:baby_skeleton', 'born_in_chaos_v1:baby_spider',
    'born_in_chaos_v1:barrel_zombie', 'born_in_chaos_v1:bloody_gadfly',
    'born_in_chaos_v1:bone_imp', 'born_in_chaos_v1:bonescaller',
    'born_in_chaos_v1:corpse_fish', 'born_in_chaos_v1:corpse_fly',
    'born_in_chaos_v1:dark_vortex', 'born_in_chaos_v1:decaying_zombie',
    'born_in_chaos_v1:decrepit_skeleton', 'born_in_chaos_v1:dire_hound_leader',
    'born_in_chaos_v1:door_knight', 'born_in_chaos_v1:dread_hound',
    'born_in_chaos_v1:fallen_chaos_knight', 'born_in_chaos_v1:firelight',
    'born_in_chaos_v1:glutton_fish', 'born_in_chaos_v1:krampus',
    'born_in_chaos_v1:krampus_henchman', 'born_in_chaos_v1:lifestealer',
    'born_in_chaos_v1:missioner', 'born_in_chaos_v1:mother_spider',
    'born_in_chaos_v1:mr_pumpkin', 'born_in_chaos_v1:mrs_pumpkin',
    'born_in_chaos_v1:nightmare_stalker', 'born_in_chaos_v1:phantom_creeper',
    'born_in_chaos_v1:pumpkin_bruiser', 'born_in_chaos_v1:pumpkin_dunce',
    'born_in_chaos_v1:restless_spirit', 'born_in_chaos_v1:seared_spirit',
    'born_in_chaos_v1:senor_pumpkin', 'born_in_chaos_v1:siamese_skeletons',
    'born_in_chaos_v1:sir_pumpkinhead', 'born_in_chaos_v1:skeleton_demoman',
    'born_in_chaos_v1:skeleton_thrasher', 'born_in_chaos_v1:spirit_guide',
    'born_in_chaos_v1:spirit_guide_assistant', 'born_in_chaos_v1:spiritof_chaos',
    'born_in_chaos_v1:supreme_bonescaller', 'born_in_chaos_v1:swarmer',
    'born_in_chaos_v1:thornshell_crab', 'born_in_chaos_v1:zombie_bruiser',
    'born_in_chaos_v1:zombie_clown', 'born_in_chaos_v1:zombie_fisherman',
    'born_in_chaos_v1:zombie_lumberjack',
])

const DIMENSION_FACTOR = {
    'minecraft:overworld': 1.0,
    'minecraft:the_nether': 1.5,
    'minecraft:the_end': 2.0,
}

// Every this many blocks from world spawn (horizontal distance) adds
// another step of difficulty, capped so it doesn't run away to absurdity.
const DISTANCE_STEP_BLOCKS = 500
const DISTANCE_STEP_BONUS = 0.15
const MAX_DISTANCE_FACTOR = 2.5
const NEARBY_PLAYER_RANGE = 64

// #101 (2nd pass, 2026-07-23): owner re-tested the star-suffix fix from
// #110 in-game on v0.5.2 and reported it still reads badly - "a randomly
// long string of asterisks" after the name (1-6 raw '*' chars depending on
// starCount looks like noise, not a rating). Requested a simpler scheme
// instead: leave the mob's real name alone and just COLOR it by relative
// difficulty - no appended text at all. Four tiers per the owner's own
// wording: green = weaker than you, yellow = similar strength, red =
// harder, purple = much harder/probably impossible. "purple" isn't one of
// vanilla's ChatFormatting color names (dark_purple/light_purple are), so
// dark_purple is used as the closest match.
const DIFFICULTY_TIERS = [
    { max: 1.15, color: 'green' },   // weaker than you
    { max: 1.6, color: 'yellow' },   // similar strength to you
    { max: 2.2, color: 'red' },      // harder than you
    { max: Infinity, color: 'dark_purple' }, // much harder, probably impossible
]

function difficultyColor(difficulty) {
    for (const tier of DIFFICULTY_TIERS) {
        if (difficulty <= tier.max) return tier.color
    }
    return DIFFICULTY_TIERS[DIFFICULTY_TIERS.length - 1].color
}

function distanceFactor(pos, spawnPos) {
    const dx = pos.getX() - spawnPos.getX()
    const dz = pos.getZ() - spawnPos.getZ()
    const dist = Math.sqrt(dx * dx + dz * dz)
    const steps = Math.floor(dist / DISTANCE_STEP_BLOCKS)
    return Math.min(1 + steps * DISTANCE_STEP_BONUS, MAX_DISTANCE_FACTOR)
}

function nearestPlayerTierFactor(players, pos) {
    let best = null
    let bestDist = NEARBY_PLAYER_RANGE
    for (const player of players) {
        const d = Math.sqrt(player.blockPosition().distSqr(pos))
        if (d < bestDist) {
            bestDist = d
            best = player
        }
    }
    if (!best) return 1.0
    // ProgressiveStages tiers reached (0-5 rootborn..starforged_age) as a
    // coarse proxy for "player level/progression" - every tier reached adds
    // a further 10% to spawned-mob difficulty near that player. player.stages
    // is KubeJS's own generic game-stages binding (dev.latvian.mods.kubejs.
    // stages.Stages) - ProgressiveStages plugs into it as its implementation
    // (confirmed via decompiling KubeJSStagesCompat$ProgressiveStagesBridge),
    // so .has(id) is KubeJS's own documented API, not ProgressiveStages-specific.
    const tiers = ['rootborn', 'andesite_age', 'brass_age', 'precision_age', 'induction_age', 'starforged_age']
    let reached = 0
    for (const t of tiers) {
        if (best.stages.has(t)) reached++
    }
    return 1 + reached * 0.1
}

// Vanilla AttributeModifier.Operation id, NOT puffish_skills' vocabulary -
// see the trap note at its use site below. selftest.js pins it to the three
// ids the vanilla enum actually accepts.
const MS_SCALING_OPERATION = 'add_multiplied_base'

EntityEvents.spawned(event => {
    const entity = event.entity
    if (!MONSTER_TYPES.has(entity.type)) return

    const spawnPos = entity.level.getSharedSpawnPos()
    const dimFactor = DIMENSION_FACTOR[String(entity.level.dimension)] || 1.0
    const distFactor = distanceFactor(entity.blockPosition(), spawnPos)
    const playerFactor = nearestPlayerTierFactor(entity.server.players, entity.blockPosition())
    const difficulty = dimFactor * distFactor * playerFactor

    entity.persistentData.putDouble('vpp_difficulty', difficulty)

    // Color the mob's own, untouched name by relative difficulty - see the
    // DIFFICULTY_TIERS comment above for why (replaces #110's star suffix).
    // Applied to every monster, including baseline ones (green), so the
    // color itself is the "look at it and tell" signal instead of only
    // showing a nametag once a mob crosses the scaling threshold.
    entity.setCustomName(Text.of(entity.getName()).color(difficultyColor(difficulty)))
    entity.setCustomNameVisible(true)

    if (difficulty <= 1.01) return // baseline mob: name is colored green above, no attribute scaling needed

    // add_multiplied_base: finalValue = base * (1 + sum of these modifiers), so
    // passing (difficulty - 1) scales base by `difficulty`.
    //
    // TRAP, and the bug this line used to be (found 2026-07-22 by L3's new
    // post-join stage-grant probe, which is the first test in this suite that
    // ever put a real player with a real tier stage next to a real spawn):
    // puffish_skills' attr_reward vocabulary calls this same semantic
    // "multiply_base" - see scripts/gen_skill_tree.py, where that spelling is
    // correct because it feeds Puffish's OWN json - but KubeJS's
    // entity.modifyAttribute() coerces to vanilla's
    // AttributeModifier.Operation enum, whose only valid ids are add_value,
    // add_multiplied_base and add_multiplied_total. Passing 'multiply_base'
    // threw IllegalArgumentException on EVERY scaled spawn, before setHealth
    // ran - so the health/damage scaling silently did nothing at all (the
    // vpp_difficulty tag and colored name above are set earlier and were
    // unaffected, but the death-reward bonus that reads that tag never paid
    // out either). Nothing outside a server-log ERROR line said so.
    entity.modifyAttribute('minecraft:generic.max_health', 'vanillaplusplus:mob_scaling_health', difficulty - 1, MS_SCALING_OPERATION)
    entity.modifyAttribute('minecraft:generic.attack_damage', 'vanillaplusplus:mob_scaling_damage', difficulty - 1, MS_SCALING_OPERATION)
    entity.setHealth(entity.getMaxHealth())
})

// Reward scaling: bonus currency proportional to how much tougher than
// baseline the killed mob was (on top of whatever Apotheosis/vanilla loot
// already grants).
EntityEvents.death(event => {
    const killer = event.source.entity
    if (!killer || killer.type !== 'minecraft:player') return
    const difficulty = event.entity.persistentData.contains('vpp_difficulty')
        ? event.entity.persistentData.getDouble('vpp_difficulty')
        : 1.0
    if (difficulty <= 1.01) return
    const bonusSpurs = Math.round((difficulty - 1) * 20)
    if (bonusSpurs > 0) {
        killer.give(Item.of('numismatics:spur', bonusSpurs))
    }
})
