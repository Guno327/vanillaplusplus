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

// GitHub #32: FTB Teams + FTB Chunks dropped (CurseForge-exclusive, no
// redistribution permission - #28) in favor of Open Parties and Claims
// (Modrinth, LGPL-3.0). Under FTB Teams, progressivestages.toml's
// `team_mode = "ftb_teams"` meant ProgressiveStages' OWN backend shared one
// canonical per-team stage store - player.stages.has(id) on any online team
// member already reflected the whole team, no KubeJS involved (see
// leaderboard.js's TEAMS header comment for the pre-#32 mechanism).
// ProgressiveStages has NO equivalent native OPAC hook - confirmed via javap
// against the actually-resolved progressivestages jar (both the previously-
// pinned 2.1 and the 3.0.1 resolve_mods.py picked up this session):
// com.enviouse.progressivestages.common.team.TeamProvider only implements
// SoloIntegration and ReflectiveFTBTeamsIntegration (reflection against FTB
// Teams' own API, guarded by config/StageConfig.isFtbTeamsIntegrationEnabled()
// -> ftb_teams/solo are the only two literal teamMode strings the mod's
// StageConfig.isFtbTeamsMode()/isSoloMode() ever compare against) - no
// xaero.pac class or string appears anywhere in either jar. So
// progressivestages.toml now sets `team_mode = "solo"` and this file takes
// over party-wide tier-stage sharing as a KubeJS-level bridge, same spirit
// as the crafted-item workaround above but syncing between party members
// instead of granting from an inventory scan.
//
// Ground-truthed OPAC API (javap against open-parties-and-claims-neoforge-
// 1.21.1-0.27.8.jar, cross-checked against its Modrinth-published sources
// jar for clarity - see manifest.json's note for the exact confirmed
// signatures): xaero.pac.common.server.api.OpenPACServerAPI.get(server) ->
// instance; .getPartyManager() -> IPartyManagerAPI; .getAllStream() ->
// Stream<IServerPartyAPI> (every party actually formed via /party create -
// confirmed via PlayerLogInPartyAssigner.java in the sources jar that OPAC,
// unlike FTB Teams, does NOT auto-create a personal solo party for every
// player, so solo players simply never appear here and are correctly
// skipped). IServerPartyAPI.getMemberInfoStream() -> Stream<IPartyMemberAPI>
// (confirmed via Party.java's getTypedMemberInfoStream() - includes the
// owner, Stream.concat(Stream.of(owner), memberInfo.values().stream())).
// IPartyMemberAPI.getUUID() -> UUID.
//
// Mirrors leaderboard.js's/selftest.js's own TIER_IDS/ST_TIER_IDS constant
// (same "duplicate + keep in sync" trade-off already accepted twice in this
// pack, restated in each file's own header) rather than importing across
// server_scripts files, which KubeJS's shared Rhino scope makes unnecessary
// anyway but this project's existing files don't rely on for constants.
const PSB_PARTY_TIER_IDS = [
    'rootborn', 'andesite_age', 'brass_age', 'precision_age', 'induction_age',
    'starforged_age', 'lunar_frontier', 'martian_frontier', 'inner_system', 'jovian_frontier',
]

let PSB_OpenPACServerAPIClass = null
try {
    PSB_OpenPACServerAPIClass = Java.loadClass('xaero.pac.common.server.api.OpenPACServerAPI')
} catch (e) {
    console.error('[vpp progression_stage_bridge] Open Parties and Claims API (xaero.pac.common.server.api.OpenPACServerAPI) failed to load - party-wide tier-stage sharing will be unavailable: ' + e)
}

// Plain top-level function (not buried in the tick closure), same reasoning
// as psbApplyItemStageTriggers above - lets selftest.js call it directly and
// deterministically. For every OPAC party with 2+ ONLINE members (nothing to
// sync with 0 or 1 - offline members have no live ServerPlayer to read/write
// player.stages on, the same fundamental limitation every other player.stages
// consumer in this pack already has), computes the union of
// PSB_PARTY_TIER_IDS every online member currently holds and grants any
// missing ones to every other online member. Only ever ADDS stages, never
// removes - a player who leaves a party keeps whatever tier stages they
// already picked up, same permanence model as every other stage grant in
// this pack (item-trigger stages, tier quest stages themselves - none of
// them are revocable). Idempotent (player.stages.add() on an already-held
// stage is a no-op) and safe to call every tick, though it only runs on the
// same 20-tick cadence as the item-trigger scan above to match. Returns the
// number of individual stage grants actually made this call, for the
// selftest round-trip below.
function psbSyncPartyStages(server) {
    if (!PSB_OpenPACServerAPIClass) return 0
    let partyManager
    try {
        partyManager = PSB_OpenPACServerAPIClass.get(server).getPartyManager()
    } catch (e) {
        console.error('[vpp progression_stage_bridge] Open Parties and Claims party manager read failed: ' + e)
        return 0
    }
    let grants = 0
    let parties = partyManager.getAllStream().toArray()
    for (let i = 0; i < parties.length; i++) {
        let members = parties[i].getMemberInfoStream().toArray() // IPartyMemberAPI[], includes the owner
        let onlinePlayers = []
        let unionStages = {}
        for (let j = 0; j < members.length; j++) {
            let sp = server.getPlayerList().getPlayer(members[j].getUUID())
            if (!sp) continue
            onlinePlayers.push(sp)
            for (let k = 0; k < PSB_PARTY_TIER_IDS.length; k++) {
                if (sp.stages.has(PSB_PARTY_TIER_IDS[k])) unionStages[PSB_PARTY_TIER_IDS[k]] = true
            }
        }
        if (onlinePlayers.length < 2) continue // nobody else online to sync with
        let unionIds = Object.keys(unionStages)
        for (let j = 0; j < onlinePlayers.length; j++) {
            let sp = onlinePlayers[j]
            for (let k = 0; k < unionIds.length; k++) {
                if (!sp.stages.has(unionIds[k])) {
                    sp.stages.add(unionIds[k])
                    grants++
                }
            }
        }
    }
    return grants
}

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

    try {
        psbSyncPartyStages(event.server)
    } catch (e) {
        console.error('[vpp progression_stage_bridge] party-wide tier-stage sync failed: ' + e)
    }
})
