// Pufferfish's Skills has no built-in experience source for block placement
// (only mine_block/kill_entity/craft_item/fish_item/enchant_item/smelt_item/
// increase_stat - verified by inspecting the mod jar directly), so the
// Building category is granted through a plain player-issued command instead.
// Throttled per player so mass-placing (e.g. dumping a full shulker) doesn't
// spam the command queue.
const lastBuildingXpTick = {}
const BUILDING_XP_COOLDOWN_TICKS = 4

BlockEvents.placed(event => {
    const player = event.player
    if (!player || !player.server) return

    const uuid = player.uuid
    const now = event.block.level.server.tickCount
    if (lastBuildingXpTick[uuid] !== undefined && now - lastBuildingXpTick[uuid] < BUILDING_XP_COOLDOWN_TICKS) {
        return
    }
    lastBuildingXpTick[uuid] = now

    player.server.runCommandSilent(`puffish_skills experience add ${player.username} building 1`)
})
