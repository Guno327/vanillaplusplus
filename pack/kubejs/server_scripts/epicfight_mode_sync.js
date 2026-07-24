// GitHub #69/#84 follow-up - epic-tweaks REMOVED, replaced with a native
// KubeJS re-implementation of its one still-load-bearing feature.
//
// BACKGROUND: epic-tweaks 1.2.0 (the only NeoForge 1.21.1 build Modrinth has
// ever shipped - re-checked via the version-metadata API on this pass, still
// nothing newer than 1.2.0/2025-09-09) hard-crashes the client with
// `java.lang.NoSuchFieldError: combatPreferredItems` the moment
// `autoswitch_mode` is enabled, because its LocalPlayerPatchMixin reads
// `ClientConfig.combatPreferredItems`, a field Epic Fight itself renamed to
// `COMBAT_CATEGORIZED_ITEMS` sometime after epic-tweaks' last release
// (javap-confirmed against the installed epic-fight-21.17.3.1 jar - see the
// old pack/config/epictweaks-client.toml history in git log / DECISIONS.md
// for the full bytecode evidence trail). The v0.5.x hotfix shipped that
// config with all three flags forced false as an emergency stop-gap - but
// that leaves a live footgun: epic-tweaks ships its own in-game Cloth Config
// screen, so a player who flips `autoswitch_mode` back on themselves still
// crashes their own client. Root-causing this properly means removing the
// broken dependency entirely, not just neutering its config - which is what
// this pass does (epic-tweaks dropped from pack/manifest.json).
//
// That drops two of epic-tweaks' three features, and both are FINE to lose
// outright now that the addon itself is gone (not just disabled):
//   - `enforce_mode` was epic-tweaks' OWN mixin
//     (PlayerPatchMixin#onToggleMode) that canceled the player's manual
//     "Switch Mode" keypress while holding a combat-preferred item - the
//     actual #84 lock-in bug was THIS mixin combined with autoswitch_mode,
//     not anything native to Epic Fight. With epic-tweaks gone, nothing
//     cancels the switch keybind at all - Epic Fight's own native "Switch
//     Mode" key always works (its own separate ~1s post-combat-input lock,
//     ControlEngine#isSwitchOrDropBlocked(), is unrelated, self-clearing,
//     and applies identically with or without epic-tweaks ever installed -
//     not a regression this change introduces). #84 is fully resolved by
//     removal alone, no replacement code needed for it.
//   - `filter_animation_first_person` was a pure first-person rendering
//     nicety (forces vanilla animation while not holding a combat item, in
//     first person only) with no gameplay effect and no config-free
//     equivalent found in Epic Fight's own ClientConfig/CommonConfig/
//     ServerConfig (full bytecode string dump, same audit as the original
//     #69/#84 investigation) - accepted as a disclosed, minor cosmetic
//     regression. Not worth a mixin of our own for a first-person-only
//     rendering polish item.
//
// `autoswitch_mode` is the one feature #69's ladder-animation fix actually
// depended on (auto-enter Vanilla Mode when not holding a "combat preferred"
// item, so climbing/exploring gets vanilla's own non-clunky ladder/movement
// animations instead of Epic Fight's combat-animation pipeline) - THIS is
// reimplemented below, server-side, using Epic Fight's own public,
// version-stable API instead of epic-tweaks' broken client mixin:
//
//   - yesman.epicfight.world.capabilities.EpicFightCapabilities
//         .getItemCapability(ItemStack): Optional<CapabilityItem>
//     (javap-confirmed public static method on the installed
//     epic-fight-21.17.3.1 jar) - the exact same capability lookup
//     epic-tweaks' own combatPreferredItems sweep was built on
//     (DESIGN.md: "every item whose Epic Fight item-stack capability is
//     instanceof WeaponCapability").
//   - yesman.epicfight.world.capabilities.item.WeaponCapability - the class
//     epic-tweaks checked `instanceof` against; confirmed present in the
//     jar's class list (`jar tf` on the installed jar).
//   - The server-authoritative mode switch is Epic Fight's OWN
//     `/epicfight mode <vanilla|epicfight> [target]` command
//     (yesman.epicfight.server.commands.PlayerModeCommand, registered
//     unconditionally by the mod itself - not epic-tweaks) which requires
//     only `CommandSourceStack.hasPermission(2)` (javap-confirmed on the
//     command's `requires` predicate, lambda$register$0) - trivially
//     satisfied by `player.server.runCommandSilent(...)`, the exact idiom
//     already used throughout this pack (skills.js/dailies.js/quests.js) to
//     run server-permission commands from a script. This is MORE robust
//     than epic-tweaks' own client-side mixin approach: it is
//     server-authoritative (no client/server mode desync risk) and reads
//     directly from Epic Fight's own stable capability API instead of an
//     internal config field a third-party addon can fall out of sync with.
//
// `instanceof` against a `Java.loadClass`-obtained class is an established,
// working pattern in this codebase (tick_accelerator.js's
// `block instanceof EntityBlockClass` / `blockEntity instanceof
// KineticBlockEntityClass`) - same idiom reused here.
//
// DESIGN-SENSITIVE CHOICE, flagged for owner review: this polls on a tick
// cadence (every 10 ticks / 0.5s, event.server.players) rather than reacting
// to an item-held-changed event, because KubeJS/NeoForge expose no
// built-in "held item changed" server event and Epic Fight's own
// LocalPlayerPatchMixin#updateHeldItem (what epic-tweaks hooked) is a
// CLIENT-side per-tick poll with no server equivalent to hook instead - so
// this reimplementation polls too, just server-side and 10x less often
// (twice a second is imperceptible for a mode that only gates animation
// choice, not combat timing). `PlayerPatch#toMode` no-ops if the player is
// already in the requested mode (javap-confirmed: toVanillaMode/
// toEpicFightMode both early-return on `playerMode == target`), so redundant
// command dispatches when nothing changed are cheap, but this still tracks
// last-known state per player (persistentData) to skip the command dispatch
// entirely on the common no-change tick. Needs a live playtest to confirm
// the 0.5s cadence feels as responsive as epic-tweaks' every-tick original -
// verify-in-game, not just a boot-test concern.

let EFMS_CapabilitiesClass = null
let EFMS_WeaponCapabilityClass = null
try {
    EFMS_CapabilitiesClass = Java.loadClass('yesman.epicfight.world.capabilities.EpicFightCapabilities')
    EFMS_WeaponCapabilityClass = Java.loadClass('yesman.epicfight.world.capabilities.item.WeaponCapability')
} catch (e) {
    console.error('[vpp epicfight_mode_sync] Epic Fight capability API failed to load - auto mode-switch (#69) will be unavailable: ' + e)
}

const EFMS_STATE_KEY = 'vpp_epicfight_combat_mode'

function efmsIsCombatItem(stack) {
    if (!EFMS_CapabilitiesClass || !EFMS_WeaponCapabilityClass) return false
    try {
        let capOpt = EFMS_CapabilitiesClass.getItemCapability(stack)
        if (!capOpt.isPresent()) return false
        return capOpt.get() instanceof EFMS_WeaponCapabilityClass
    } catch (e) {
        return false
    }
}

function efmsReconcile(player) {
    if (!EFMS_CapabilitiesClass || !EFMS_WeaponCapabilityClass) return
    try {
        // `let`, not `const`, for bindings declared directly inside this try
        // block - this pack's installed Rhino build throws "redeclaration of
        // const/var" for a const/var declared directly in a try body
        // (GitHub #8's audit; see skill_respec.js/selftest.js for the same
        // workaround already established in this codebase).
        let data = player.persistentData
        let wasCombat = data.contains(EFMS_STATE_KEY) ? data.getBoolean(EFMS_STATE_KEY) : null
        let isCombat = efmsIsCombatItem(player.getMainHandItem())
        if (wasCombat !== null && wasCombat === isCombat) return // already in the right mode, skip the command dispatch

        player.server.runCommandSilent(`epicfight mode ${isCombat ? 'epicfight' : 'vanilla'} ${player.username}`)
        data.putBoolean(EFMS_STATE_KEY, isCombat)
    } catch (e) {
        console.error(`[vpp epicfight_mode_sync] mode reconcile failed for ${player.username}: ${e}`)
    }
}

PlayerEvents.loggedIn(event => {
    efmsReconcile(event.player)
})

let efmsTickCounter = 0
ServerEvents.tick(event => {
    efmsTickCounter++
    if (efmsTickCounter % 10 !== 0) return

    for (const player of event.server.players) {
        efmsReconcile(player)
    }
})
