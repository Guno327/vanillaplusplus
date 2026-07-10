// TODO.md item 4 ("Personal mobility progression: jetpack -> persistent
// creative flight") - Starforged Age flight capstone. Recorded decision:
// item-free persistent creative-style flight, granted the moment a player
// reaches the starforged_age ProgressiveStages stage (Tier 5 - the gateway
// out of the overworld/Nether/End loop into space travel), landing well
// before the full Tier 6-9 planet grind per TODO.md item 4's "Progression
// shape" decision.
//
// Mechanism: this is a straight `abilities.mayfly` grant/revoke keyed off
// stage membership, not an item/effect/attribute - matches the recorded
// "toggleable, no-fuel/no-duration-limit... vanilla abilities.mayfly-
// equivalent state" decision. mayfly (not flying) is what's set: granting
// mayfly=true just makes the double-jump-to-fly toggle available, the same
// as switching to creative mode does - it does NOT yank the player into the
// air immediately, which forcing flying=true on grant would do.
//
// PERSISTENCE ACROSS DEATH: TODO.md item 4 flagged this pack's own
// `keepInventory: false` gamerule as a real risk for a "persistent" flight
// capstone that's trivially lost on death. Since the grant here is driven
// entirely by stage membership (not an item, not a status effect - neither
// of which would be safe under keepInventory:false), and ProgressiveStages
// stages are player-persistent data independent of inventory/gamerules, the
// capstone survives death by construction: the player keeps the
// starforged_age stage after respawning, and PlayerEvents.respawned below
// re-asserts abilities.mayfly from that stage on every respawn regardless
// of whether vanilla would have carried the raw Abilities fields across on
// its own.
//
// EVENT SIGNATURES - re-verified directly against the installed KubeJS
// 2101.7.2 jar (javap), not assumed from the brief:
//   - PlayerEvents.STAGE_ADDED / STAGE_REMOVED are TargetedEventHandler
//     <String> (dev.latvian.mods.kubejs.plugin.builtin.event.PlayerEvents)
//     -> PlayerEvents.stageAdded('starforged_age', event => ...) fires a
//     dev.latvian.mods.kubejs.player.StageChangedEvent, which exposes
//     .player (getPlayer()) and .stage (getStage()).
//   - PlayerEvents.LOGGED_IN / RESPAWNED are plain EventHandlers ->
//     PlayerEvents.loggedIn(event => ...) / .respawned(event => ...), both
//     firing events implementing KubePlayerEvent (.player accessor).
//   - Player.getAbilities() returns net.minecraft.world.entity.player.
//     Abilities, a plain data class with PUBLIC fields `mayfly`/`flying`/
//     `instabuild` (no setter methods for these - confirmed via javap: only
//     setFlyingSpeed()/setWalkingSpeed() exist, for the two float fields -
//     so direct field assignment from JS is the only way in, and it works
//     fine through Rhino's Java interop for public fields).
//   - Player.onUpdateAbilities() exists on Player and is separately
//     overridden on ServerPlayer (confirmed both classes declare it) - the
//     ServerPlayer override is what actually sends the abilities sync
//     packet to the client, so calling it (not just mutating the fields)
//     is required for the client to see the change.
//   - Player.isCreative() / isSpectator() are abstract vanilla Player
//     methods (implemented on ServerPlayer), used to guard the revoke path
//     below - safe to call directly, no KubeJS wrapper needed.
//   - player.getStages().has('starforged_age') - dev.latvian.mods.kubejs.
//     core.PlayerKJS#kjs$getStages() (-> Stages, a default-method interface
//     with .has(String)) is how the loggedIn/respawned handlers below check
//     stage membership without waiting for a stageAdded/stageRemoved event.
//
// BOOT-TEST-ONLY UNKNOWNS (can't be verified from a decompile alone, flagged
// for whoever boot-tests this):
//   1. Per-tick reassertion: this script only re-asserts mayfly on login/
//      respawn/stage-change, not every tick. If some other system in this
//      pack (or a mod interaction) silently clears a player's mayfly flag
//      mid-session, that clear won't be caught until the player's next
//      login/respawn/stage change. Left this way deliberately (a
//      PlayerEvents.tick handler firing every tick for every online player
//      is a real cost for a check that should almost never actually need
//      to fire) but worth watching for in practice.
//   2. Client ability-packet sync timing: onUpdateAbilities() sends the
//      packet, but whether the client-side flight toggle (double-tap jump)
//      responds instantly or needs a reconnect/respawn to "feel" the change
//      the same tick it's granted (e.g. right as the stageAdded event fires
//      mid-session) is not verifiable without an actual client attached -
//      confirm on first boot test.

const STAGE = 'starforged_age'

function setMayfly(player, enabled) {
    const abilities = player.getAbilities()
    if (abilities.mayfly === enabled) return // already correct, skip the sync packet
    abilities.mayfly = enabled
    if (!enabled) abilities.flying = false // don't leave them mid-air with the toggle gone
    player.onUpdateAbilities()
}

// Shared reconcile step for loggedIn/respawned: brings mayfly back in line
// with current stage membership + gamemode without touching anything if
// it's already correct.
function reconcile(player) {
    if (player.getStages().has(STAGE)) {
        setMayfly(player, true)
    } else if (!player.isCreative() && !player.isSpectator()) {
        // Defensive revoke path (see TODO.md item 4's "Open" section): if a
        // player somehow loses the stage, strip the grant - but never touch
        // mayfly for a player whose current gamemode already grants it
        // natively (creative/spectator), since revoking there would break
        // their normal gamemode-driven flight instead of just undoing this
        // capstone's own grant.
        setMayfly(player, false)
    }
}

PlayerEvents.stageAdded(STAGE, event => {
    const player = event.player
    setMayfly(player, true)
    player.tell('Persistent flight unlocked - press your jump key twice to toggle flight, no fuel or duration limit.')
})

PlayerEvents.stageRemoved(STAGE, event => {
    const player = event.player
    if (!player.isCreative() && !player.isSpectator()) {
        setMayfly(player, false)
    }
})

PlayerEvents.loggedIn(event => reconcile(event.player))
PlayerEvents.respawned(event => reconcile(event.player))
