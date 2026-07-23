// Client half of the client/server version-mismatch notice - see
// pack/kubejs/server_scripts/version_check.js for the full design writeup
// and its COVERAGE section (this only fires for clients that could
// actually connect in the first place; a mod-list mismatch is rejected by
// NeoForge's own handshake before any of this runs, and is only visible
// via the server's MOTD instead).
//
// Receives the server's version (sent once per login, see the server-side
// script) and compares it to this client's own build-time-baked
// global.VPP_PACK_VERSION (from generated_version.js, written by
// scripts/build_mrpack.py - see scripts/version_kubejs.py). On a mismatch:
// a persistent chat line, using this pack's existing player.tell() idiom
// (see quests.js) - guaranteed to render, since it's plain chat - naming
// both versions, which one to install, and the releases page. Also a
// best-effort toast via KubeJS's own player.notify()/NotificationToastData:
// this is not exercised anywhere else in this pack, and there is no live
// client in this build sandbox to confirm its exact layout/argument order
// renders as intended, so it's wrapped defensively and flagged
// verify-in-game - the chat lines above are the guaranteed-to-work path
// regardless of whether the toast renders correctly.
const VPP_RELEASES_URL = 'https://github.com/Guno327/vanillaplusplus/releases'

NetworkEvents.dataReceived('vanillaplusplus:version', event => {
    const serverVersion = event.data.getString('version')
    const clientVersion = global.VPP_PACK_VERSION
    if (!serverVersion || !clientVersion || serverVersion === clientVersion) return

    const player = event.player
    player.tell(`[Vanilla++] Version mismatch! This server is running v${serverVersion}, you have v${clientVersion} installed.`)
    player.tell(`[Vanilla++] Download the matching client (v${serverVersion}) from ${VPP_RELEASES_URL}`)

    // Best-effort toast on top of the guaranteed chat lines above -
    // verify-in-game, see header comment.
    try {
        let ComponentClass = Java.loadClass('net.minecraft.network.chat.Component')
        let ToastDataClass = Java.loadClass('dev.latvian.mods.kubejs.util.NotificationToastData')
        let title = ComponentClass.literal('Vanilla++ version mismatch')
        let subtitle = ComponentClass.literal(`Install v${serverVersion} - see releases page`)
        player.notify(ToastDataClass.ofTitle(title, subtitle))
    } catch (e) {
        console.error('vanillaplusplus:version toast failed (chat notice above still applies): ' + e)
    }
})
