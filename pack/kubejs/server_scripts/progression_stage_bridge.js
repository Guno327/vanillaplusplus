// GitHub issue #23 (owner-reported, progression-locking): crafting the
// first create:andesite_alloy completed rootborn's final quest
// (000000000002000B, an "only_from_crafting" item task - FTB Quests' own
// crafting tracker) but did NOT grant the andesite_age stage, so
// andesite_age's first quest (0000000000020010, a "gamestage" task
// requiring stage "andesite_age") could never complete - hard-locking all
// progression behind it. The exact same mechanism gates brass_age,
// induction_age, and precision_age too (every [items] entry and the one
// item-typed [[multi]] entry in config/ProgressiveStages/triggers.toml).
//
// ROOT CAUSE (ground-truth verified this session via javap against the
// actually-installed jars, PATH=/home/ubuntu/vanilla++/.tools/
// jdk-21.0.11+10/bin, decompiled dumps under /tmp/e23/):
//
//  - FTB Quests' "gamestage" task type (dev.ftb.mods.ftbquests.quest.task.
//    StageTask.canSubmit, non-team_stage branch) reads dev.ftb.mods.
//    ftblibrary.integration.stages.StageHelper.INSTANCE.getProvider()
//    .has(player, stage) and is auto-submitted every 20 ticks
//    (StageTask.autoSubmitOnPlayerTick() returns 20) - so it's not simply
//    "never rechecked".
//  - ProgressiveStages DOES install itself as that FTB Library stage
//    provider: com.enviouse.progressivestages.compat.ftbquests.
//    FtbQuestsHooks.registerStageProvider() builds a java.lang.reflect.
//    Proxy implementing dev.ftb.mods.ftblibrary.integration.stages.
//    StageProvider and installs it via StageHelper.setProviderImpl(...),
//    called from FTBQuestsCompat.init() (plus a late-registration retry on
//    ServerStartingEvent and on the mod's own stage-change events). This
//    is gated by config/ProgressiveStages/progressivestages.toml's
//    [integration.ftbquests] enabled = true, which is ON in this pack. The
//    proxy's has()/add()/remove() call straight into ProgressiveStagesAPI.
//    hasStage()/StageManager.grantStageBypassDependencies() - i.e. the
//    FTB Quests <-> ProgressiveStages bridge itself is correctly wired and
//    is NOT the broken link.
//  - The actual break is one layer upstream of that bridge: triggers.toml's
//    [items] section (and precision_age's [[multi]] any_of "item:" entries)
//    is only ever enforced by com.enviouse.progressivestages.server.
//    triggers.ItemPickupStageGrants.onItemPickup(), which is registered
//    (via ServerEventHandler.onServerStarting -> NeoForge.EVENT_BUS.
//    register(ItemPickupStageGrants.class)) against exactly one event:
//    net.neoforged.neoforge.event.entity.player.ItemEntityPickupEvent$Pre
//    - fired when a player picks an ItemEntity up off the ground. The only
//    other code path that consults the same ITEM_STAGES map is
//    scanInventoryForStages(), which runs once, on PlayerLoggedInEvent
//    (login) - not on crafting. com.enviouse.progressivestages.server.
//    triggers.MultiTriggerManager (which backs precision_age's [[multi]]
//    any_of) has its own onItemPickup() listening to the identical
//    ItemEntityPickupEvent$Pre for its item sub-type, plus login/
//    advancement/dimension/death listeners - nothing crafting-related.
//    Crafting an item at a crafting table, or extracting one from a
//    Create Basin/Mixer, delivers it straight into a Container/player
//    inventory - it is never spawned as a world ItemEntity, so
//    ItemEntityPickupEvent$Pre never fires and the stage is never granted,
//    no matter how correctly the FTB Quests bridge itself is wired.
//    (Reproduce the finding: `javap -p -c com/enviouse/progressivestages/
//    server/triggers/ItemPickupStageGrants.class` shows exactly one
//    @SubscribeEvent-style listener method, onItemPickup(ItemEntityPickup
//    Event$Pre); there is no ItemCraftedEvent, container-slot-change, or
//    periodic inventory-tick listener anywhere in progressivestages-2.1.jar.)
//
// FIX: grant the same triggers.toml [items]/[[multi]] mapping through
// KubeJS's player.stages bridge instead of relying on ItemPickupStageGrants
// - the identical, already-proven backend leaderboard.js/mob_scaling.js/
// selftest.js already read from (dev.latvian.mods.kubejs.stages.
// StageEvents.create(player), populated at player-join by com.enviouse.
// progressivestages.compat.kubejs.KubeJSStagesCompat.onStageCreation() ->
// a ProgressiveStagesBridge whose addNoUpdate()/has() call straight into
// com.enviouse.progressivestages.common.stage.StageManager - the exact
// same underlying grant path every OTHER, working, trigger type in this
// mod already uses; javap-confirmed on KubeJSStagesCompat$
// ProgressiveStagesBridge.addNoUpdate). This runs as a periodic per-player
// inventory scan (every 20 ticks - matching StageTask's own auto-submit
// cadence, so the gamestage quest task lights up within ~1 second either
// way) rather than trying to hook Create's non-vanilla Basin/Mixer
// extraction path directly: "does the player currently HOLD the item" is a
// strictly more robust trigger condition than "did we catch the one
// specific acquisition event" - it also self-heals any player who already
// has the item sitting in inventory from before this fix shipped, with no
// relog required (unlike ProgressiveStages' own login-only inventory scan).
//
// KEEP IN SYNC with config/ProgressiveStages/triggers.toml's [items]
// section and precision_age's [[multi]] any_of list - this mirrors that
// data rather than parsing the TOML at runtime (same duplication trade-off
// this pack already accepts for leaderboard.js's TIER_IDS / selftest.js's
// ST_TIER_IDS; KubeJS's Rhino sandbox has no low-risk way to reach
// ProgressiveStages' own NightConfig-based TOML loader, which is exactly
// the code path already proven insufficiently reactive here).
//
// GitHub #33 AUDIT (does this file need FTB Library present?): the two
// "ftblibrary.integration.stages.StageHelper" / "FTB Quests' gamestage task
// type" references above are historical bug-analysis narrative only (why
// the #23 regression happened in the FIRST PLACE, back when FTB Quests
// still owned that task type) - no code below this comment block ever
// loads or calls an FTB Library/FTB Quests class. The actual fix
// (psbApplyItemStageTriggers/the tick handler) only ever touches
// player.stages (KubeJS's own ProgressiveStages binding) and
// player.inventory.find() - both already independent of FTB Library, since
// the whole point of this file's fix was routing around FTB Quests/FTB
// Library entirely. Confirmed safe to remove ftb-quests from the pack
// (done as part of #33) with zero changes needed here. (ftb-library itself
// stays installed regardless - see scripts/gen_quests.py's own module
// docstring for why: it's still a required, not optional, dependency of
// FTB Teams and FTB Chunks, both still in the pack.)
const PSB_ITEM_STAGE_TRIGGERS = [
    { stage: 'andesite_age', items: ['create:andesite_alloy'] },
    { stage: 'brass_age', items: ['create:brass_ingot'] },
    { stage: 'induction_age', items: ['minecraft:netherite_ingot'] },
    { stage: 'precision_age', items: ['create:refined_radiance', 'create:shadow_steel'] },
]

// Plain top-level function (not buried in the tick closure) so selftest.js
// can call it directly and deterministically instead of waiting on the
// real tick loop. Idempotent and a no-op per trigger once the player (or,
// under team_mode = "ftb_teams", their team - ProgressiveStages' own
// backend already shares stage state team-wide, see leaderboard.js's
// header comment) already holds that stage. Returns the list of stage ids
// actually granted this call, for the selftest round-trip below.
function psbApplyItemStageTriggers(player) {
    let granted = []
    for (let i = 0; i < PSB_ITEM_STAGE_TRIGGERS.length; i++) {
        let trigger = PSB_ITEM_STAGE_TRIGGERS[i]
        if (player.stages.has(trigger.stage)) continue
        let holds = false
        for (let j = 0; j < trigger.items.length; j++) {
            if (player.inventory.find(trigger.items[j]) >= 0) {
                holds = true
                break
            }
        }
        if (holds) {
            player.stages.add(trigger.stage)
            granted.push(trigger.stage)
        }
    }
    return granted
}

let psbTickCounter = 0
ServerEvents.tick(event => {
    psbTickCounter++
    if (psbTickCounter % 20 !== 0) return // matches FTB Quests' own StageTask autoSubmitOnPlayerTick() cadence

    for (const player of event.server.players) {
        try {
            psbApplyItemStageTriggers(player)
        } catch (e) {
            console.error('[vpp progression_stage_bridge] tick scan failed for ' + player.username + ': ' + e)
        }
    }
})
