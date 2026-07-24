// GitHub #166: wire vppquests' `gamestage` quest task type to this pack's
// real progression-stage store.
//
// vppquests is a standalone, Modrinth-publishable mod (mods-src/vppquests/,
// GitHub #67's convention) and so deliberately takes NO compile/runtime
// dependency on any specific stage mod: its QuestProgressTracker leaves every
// `gamestage` task unsatisfiable unless a pack supplies a resolver through
// dev.vanillaplusplus.vppquests.quest.GamestageBridge. Each chapter's `enter`
// quest is a single `gamestage` task ("you have reached this age"), and each
// chapter's other quests depend on that `enter` quest, so with no resolver
// all 9 non-starting chapters were hard-locked (the bug this file fixes).
//
// This is the exact same `player.stages` store every other stage consumer in
// this pack already reads (leaderboard.js, mob_scaling.js, mobility.js) and
// that progression_stage_bridge.js GRANTS into (item/dimension/boss/starting
// triggers). player.getStages() is KubeJS's own dev.latvian.mods.kubejs.core.
// PlayerKJS#getStages() binding (see mobility.js's `player.getStages().has(
// 'starforged_age')`), so this needs no mod beyond KubeJS itself - and the
// GamestageBridge seam keeps the mod jar free of even that.
//
// Rhino note: `let` (never `const`) and declared OUTSIDE the try body, per
// this repo's DECISIONS.md "#8 (Rhino const audit)" - a const/let declared
// directly inside a try{} throws at load. Mirrors progression_stage_bridge.js's
// own PSB_OpenPACServerAPIClass load pattern.

let VppqGamestageBridge = null
try {
    VppqGamestageBridge = Java.loadClass('dev.vanillaplusplus.vppquests.quest.GamestageBridge')
} catch (e) {
    console.error('[vpp vppquests_stage_bridge] GamestageBridge class failed to load - vppquests gamestage tasks (all 9 chapter "enter" quests) will stay unsatisfiable: ' + e)
}

if (VppqGamestageBridge !== null) {
    VppqGamestageBridge.setResolver((player, stage) => {
        try {
            return player.getStages().has(stage)
        } catch (e) {
            console.error('[vpp vppquests_stage_bridge] player.getStages().has("' + stage + '") failed: ' + e)
            return false
        }
    })
    console.info('[vpp vppquests_stage_bridge] vppquests gamestage resolver wired to player.getStages()')
}
