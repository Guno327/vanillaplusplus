package dev.vanillaplusplus.vppquests.quest;

import dev.vanillaplusplus.vppquests.VppQuests;
import net.minecraft.server.level.ServerPlayer;

/**
 * Optional, pack-supplied bridge that lets {@link QuestTask.Gamestage} tasks
 * resolve against whatever progression-stage system the surrounding pack
 * actually uses, without {@code vppquests} taking a hard compile/runtime
 * dependency on any specific stage mod (the standalone,
 * Modrinth-publishable-mod constraint this mod is built under - see
 * {@link QuestProgressTracker}'s class doc and the mod's README).
 *
 * <p><b>Why this exists (GitHub #166).</b> Every chapter's {@code enter}
 * quest is a single {@code gamestage} task ("you have reached this age").
 * With no resolver wired, {@link QuestProgressTracker} treated every
 * {@code gamestage} task as permanently unsatisfiable, so those 9 entry
 * quests could never complete - and because each chapter's other quests
 * depend on its {@code enter} quest, that hard-locked all 9 chapters. This
 * seam lets the pack point {@code gamestage} tasks at its live stage store
 * so the entry quests complete the moment the player reaches the stage.
 *
 * <p><b>How the Vanilla++ pack wires it.</b> A KubeJS server script
 * ({@code pack/kubejs/server_scripts/vppquests_stage_bridge.js}) calls
 * {@link #setResolver} with {@code (player, stage) -> player.getStages().has(stage)}
 * - KubeJS's own {@code dev.latvian.mods.kubejs.core.PlayerKJS#getStages()}
 * binding, the exact same {@code player.stages} store every other stage
 * consumer in the pack (leaderboard.js, mob_scaling.js, mobility.js, the
 * progression_stage_bridge.js granter) already reads. A pack that ships
 * {@code vppquests} without wiring a resolver simply gets the safe default
 * (no {@code gamestage} task ever auto-completes), exactly as before.
 */
public final class GamestageBridge {

    /** Resolves whether {@code player} currently holds the named stage. */
    @FunctionalInterface
    public interface StageResolver {
        boolean hasStage(ServerPlayer player, String stage);
    }

    private static final StageResolver NONE = (player, stage) -> false;

    private static volatile StageResolver resolver = NONE;

    /**
     * Registers the pack's stage resolver. Called once from pack glue at
     * server-script load; a {@code null} resolver resets to the safe default.
     * {@code volatile} so the server tick thread sees the value the
     * (KubeJS) registration thread wrote.
     */
    public static void setResolver(StageResolver newResolver) {
        resolver = (newResolver == null) ? NONE : newResolver;
        VppQuests.LOGGER.info("vppquests: gamestage resolver {}",
                (newResolver == null) ? "reset to default (no stage tasks resolve)" : "registered");
    }

    /**
     * True if the pack's resolver reports {@code player} has {@code stage}.
     * Any exception from the (foreign, pack-supplied) resolver is swallowed to
     * false so a bad bridge can never crash the quest tick.
     */
    public static boolean hasStage(ServerPlayer player, String stage) {
        try {
            return resolver.hasStage(player, stage);
        } catch (Throwable t) {
            VppQuests.LOGGER.error("vppquests: gamestage resolver threw for stage '{}': {}", stage, t.toString());
            return false;
        }
    }

    private GamestageBridge() {
    }
}
