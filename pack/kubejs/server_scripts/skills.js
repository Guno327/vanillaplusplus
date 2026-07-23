// Pufferfish's Skills has no built-in experience source for block placement
// (only mine_block/kill_entity/craft_item/fish_item/enchant_item/smelt_item/
// increase_stat - verified by inspecting the mod jar directly), so the
// Building sub-tree's XP is granted through a plain player-issued command
// instead. Throttled per player so mass-placing (e.g. dumping a full
// shulker) doesn't spam the command queue.
//
// Issue #116 ("Converge all skill trees into ONE unified tree") SUPERSEDES
// issue #71's 23-category structure with one puffish_skills category
// (scripts/gen_skill_tree.py's UNIFIED_CATEGORY_ID) - the "building"
// category id this command used to target no longer exists as a
// puffish_skills category (Building is now just one of 23 former-category
// subtrees woven into the one unified tree), so this now grants XP into
// the unified category directly. Building XP still only ever came from here
// (the mod has no native block-placement source), and it now feeds the
// SAME shared level as every other action, per issue #116 point 2.
const SKILLS_UNIFIED_CATEGORY_ID = 'adventurer'

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

    player.server.runCommandSilent(`puffish_skills experience add ${player.username} ${SKILLS_UNIFIED_CATEGORY_ID} 1`)
})
