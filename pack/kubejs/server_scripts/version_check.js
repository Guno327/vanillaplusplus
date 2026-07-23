// Client/server version-mismatch notice (GitHub issue: notify a player when
// their modpack version doesn't match the server's, and tell them which
// version to use).
//
// pack/VERSION is baked into a `global.VPP_PACK_VERSION` constant on BOTH
// sides at build time - see scripts/version_kubejs.py, written directly
// into the client .mrpack's overrides/kubejs/startup_scripts/
// generated_version.js and the server bundle's own kubejs/startup_scripts/
// generated_version.js by build_mrpack.py and build_server.py respectively.
// startup_scripts run on both physical sides before the client/server
// split happens (same as this pack's existing shared startup_scripts,
// boss_weapons.js/weapon_items.js), so that constant is visible here too.
//
// On login, this server sends ITS OWN version to the joining client over a
// KubeJS custom data channel (NetworkEvents.dataReceived on the client
// side - see pack/kubejs/client_scripts/version_check.js). The client then
// compares that to its own baked VPP_PACK_VERSION and shows the mismatch
// notice locally. The comparison intentionally happens client-side, not
// here: the server has no reliable way to learn a client's version without
// the client reporting it first, and "server announces its own version,
// client decides whether that's a mismatch" needs only one packet instead
// of a round trip.
//
// COVERAGE / HARD LIMIT: this only ever reaches a client NeoForge's own
// connection handshake actually let onto the server in the first place.
// NeoForge rejects a client whose *mod list* doesn't match the server's at
// the handshake, before PlayerEvents.loggedIn - or any other KubeJS event -
// ever fires, so this mechanism cannot help a client in that state (e.g. a
// genuinely older/newer build with a different mod set). That case has no
// in-game channel at all; the only place a rejected client can see
// anything is the server's MOTD (pack/server.properties' `motd` field,
// e.g. "Vanilla++ - a Create-centric RPG modpack (server: vX.Y.Z)" -
// visible in the multiplayer server list before ever attempting to
// connect). This script only covers the OTHER case: a client that CAN
// connect (same mod list) but is running a different pack version/config/
// recipe revision than the server.
const VersionCheckCompoundTagClass = Java.loadClass('net.minecraft.nbt.CompoundTag')

PlayerEvents.loggedIn(event => {
    const player = event.player
    const serverVersion = global.VPP_PACK_VERSION
    if (!serverVersion) return // generated_version.js missing (dev sandbox not rebuilt) - don't crash a login over it

    const tag = new VersionCheckCompoundTagClass()
    tag.putString('version', serverVersion)
    player.sendData('vanillaplusplus:version', tag)
})
