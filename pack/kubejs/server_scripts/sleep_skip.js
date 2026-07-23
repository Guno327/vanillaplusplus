// GitHub issue #69 item 2: "25% player sleep skips night" - a fraction of
// the online players sleeping should end the night, rather than requiring
// everyone (or a single player on a solo/low-pop server run) to be in bed.
//
// No new mod needed for this one: Minecraft has shipped exactly this as a
// vanilla gamerule since 1.17 - playersSleepingPercentage (integer 0-100,
// vanilla default 100, i.e. "everyone must sleep"). Setting it to 25 makes
// the night skip once >=25% of the CURRENTLY ONLINE players are in bed
// (vanilla's own SleepStatus computes the threshold against online player
// count each time, not a fixed lobby size), which satisfies the ask with
// zero jar additions and zero new dependency surface - the simplest
// possible fix per this pack's own "prefer removing the dependency, not
// adding one" bias.
//
// A fresh world/server always starts at the vanilla default (100) since
// gamerules are per-world save state, not something server.properties can
// pre-seed for this particular rule. ServerEvents.loaded fires once after
// the server (and its level/world) has fully loaded, so running the
// command there (same run-a-command-on-load pattern used by KubeJS packs
// generally) guarantees the rule is set to our pack default every time a
// fresh world is created, while being a harmless idempotent no-op on every
// subsequent boot of an existing world. runCommandSilent is used (not
// runCommand) so this doesn't spam a chat message on every server start.
ServerEvents.loaded(event => {
    event.server.runCommandSilent('gamerule playersSleepingPercentage 25')
})
