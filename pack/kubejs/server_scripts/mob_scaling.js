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

const STAR_COLORS = ['gray', 'green', 'yellow', 'gold', 'red', 'dark_red']

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

EntityEvents.spawned(event => {
    const entity = event.entity
    if (!MONSTER_TYPES.has(entity.type)) return

    const spawnPos = entity.level.getSharedSpawnPos()
    const dimFactor = DIMENSION_FACTOR[String(entity.level.dimension)] || 1.0
    const distFactor = distanceFactor(entity.blockPosition(), spawnPos)
    const playerFactor = nearestPlayerTierFactor(entity.server.players, entity.blockPosition())
    const difficulty = dimFactor * distFactor * playerFactor

    if (difficulty <= 1.01) return // baseline mob, leave it alone - no nametag clutter

    // multiply_base: finalValue = base * (1 + sum of multiply_base modifiers),
    // same semantics puffish_skills' attr_reward "multiply_base" operation
    // uses (Phase 3) - passing (difficulty - 1) here scales base by `difficulty`.
    entity.modifyAttribute('minecraft:generic.max_health', 'vanillaplusplus:mob_scaling_health', difficulty - 1, 'multiply_base')
    entity.modifyAttribute('minecraft:generic.attack_damage', 'vanillaplusplus:mob_scaling_damage', difficulty - 1, 'multiply_base')
    entity.setHealth(entity.getMaxHealth())

    entity.persistentData.putDouble('vpp_difficulty', difficulty)

    const starCount = Math.min(Math.floor((difficulty - 1) / 0.3) + 1, STAR_COLORS.length)
    const color = STAR_COLORS[starCount - 1]
    entity.setCustomName(Text.of('*'.repeat(starCount)).color(color))
    entity.setCustomNameVisible(true)
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
