// GitHub #164 item 5 (xp-routing half): grant vppquests `xp` quest rewards as
// Pufferfish's Skills XP instead of vanilla experience.
//
// Every vppquests `xp` reward carries a `category` (all 62 quests use
// "adventurer"), which is a puffish SKILL category - not vanilla XP. The mod
// stays skill-mod-agnostic (standalone/Modrinth, GitHub #67), so its
// QuestProgressTracker grants vanilla XP by default and exposes
// dev.vanillaplusplus.vppquests.quest.QuestRewardBridge for a pack to route
// the reward. This wires it to the exact `puffish_skills experience add
// <name> <category> <amount>` command achievements.js/dailies.js already use.
//
// The granter runs at server permission (server.createCommandSourceStack(),
// level 4) with suppressed output - same effect as KubeJS's runCommandSilent,
// but via vanilla ServerPlayer/MinecraftServer methods that are guaranteed
// present on the raw ServerPlayer the Java bridge hands us (mirrors
// vppquests_stage_bridge.js's use of player.getStages()). If this throws, the
// mod's QuestRewardBridge catches it and falls back to vanilla XP, so a player
// is never shorted.
//
// Rhino note: `let` (never `const`), declared OUTSIDE the try body, per this
// repo's DECISIONS.md "#8 (Rhino const audit)".

let VppqRewardBridge = null
try {
    VppqRewardBridge = Java.loadClass('dev.vanillaplusplus.vppquests.quest.QuestRewardBridge')
} catch (e) {
    console.error('[vpp vppquests_reward_bridge] QuestRewardBridge class failed to load - vppquests xp rewards will grant vanilla XP instead of skill XP: ' + e)
}

if (VppqRewardBridge !== null) {
    VppqRewardBridge.setSkillXpGranter((player, category, amount) => {
        let server = player.getServer()
        server.getCommands().performPrefixedCommand(
            server.createCommandSourceStack().withSuppressedOutput(),
            'puffish_skills experience add ' + player.getGameProfile().getName() + ' ' + category + ' ' + amount)
    })
    console.info('[vpp vppquests_reward_bridge] vppquests xp rewards routed to puffish_skills skill XP')
}
