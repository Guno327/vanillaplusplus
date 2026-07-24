package dev.vanillaplusplus.vppquests.quest;

import dev.vanillaplusplus.vppquests.VppQuests;
import net.minecraft.server.level.ServerPlayer;

/**
 * Optional, pack-supplied bridge for granting an {@link QuestReward.XpReward}'s
 * XP into whatever skill/RPG system the surrounding pack uses, without
 * {@code vppquests} taking a hard dependency on that system - the same
 * standalone/Modrinth-publishable constraint {@link GamestageBridge} exists
 * for.
 *
 * <p><b>Why this exists (GitHub #164 item&nbsp;5, xp-routing half).</b> Every
 * quest's {@code xp} reward carries a {@code category} (all 62 quests use
 * {@code "adventurer"}), which is a <em>skill category</em> for this pack's
 * Pufferfish's Skills setup - not vanilla experience. {@link
 * QuestProgressTracker} was granting plain vanilla XP and ignoring the
 * category, so skill-XP rewards silently did the wrong thing. This seam lets
 * the pack route the reward to the right place while keeping the mod jar
 * skill-mod-agnostic.
 *
 * <p><b>Default = vanilla XP.</b> With no granter wired (standalone use, or a
 * pack that doesn't care), the reward falls back to
 * {@link ServerPlayer#giveExperiencePoints(int)} exactly as before - and that
 * same fallback also runs if a wired granter throws, so a player is never
 * shorted their reward by broken pack glue.
 *
 * <p><b>How the Vanilla++ pack wires it.</b> A KubeJS server script
 * ({@code pack/kubejs/server_scripts/vppquests_reward_bridge.js}) calls
 * {@link #setSkillXpGranter} to run
 * {@code puffish_skills experience add <name> <category> <amount>} - the exact
 * command {@code achievements.js}/{@code dailies.js} already use to award
 * skill XP.
 */
public final class QuestRewardBridge {

    /** Grants {@code amount} XP in {@code category} to {@code player}. */
    @FunctionalInterface
    public interface SkillXpGranter {
        void grant(ServerPlayer player, String category, int amount);
    }

    /** The standalone default: plain vanilla experience, category ignored. */
    private static final SkillXpGranter VANILLA = (player, category, amount) -> player.giveExperiencePoints(amount);

    private static volatile SkillXpGranter granter = VANILLA;

    /**
     * Registers the pack's skill-XP granter. Called once from pack glue at
     * server-script load; a {@code null} granter resets to the vanilla-XP
     * default. {@code volatile} so the server tick thread sees what the
     * (KubeJS) registration thread wrote.
     */
    public static void setSkillXpGranter(SkillXpGranter newGranter) {
        granter = (newGranter == null) ? VANILLA : newGranter;
        VppQuests.LOGGER.info("vppquests: skill-xp granter {}",
                (newGranter == null) ? "reset to default (vanilla XP)" : "registered");
    }

    /**
     * Grants a quest {@code xp} reward. Routes through the pack granter if one
     * is wired, else vanilla XP. Any exception from the (foreign, pack-supplied)
     * granter is caught and the reward re-granted as vanilla XP so the quest
     * tick can never crash and the player is never shorted.
     */
    public static void grantSkillXp(ServerPlayer player, String category, int amount) {
        try {
            granter.grant(player, category, amount);
        } catch (Throwable t) {
            VppQuests.LOGGER.error("vppquests: skill-xp granter threw for category '{}' (falling back to vanilla XP): {}",
                    category, t.toString());
            VANILLA.grant(player, category, amount);
        }
    }

    private QuestRewardBridge() {
    }
}
