package dev.vanillaplusplus.vppquests.client;

import dev.vanillaplusplus.vppquests.data.QuestProgressAttachment;
import dev.vanillaplusplus.vppquests.network.ClaimQuestRewardPayload;
import dev.vanillaplusplus.vppquests.quest.Quest;
import dev.vanillaplusplus.vppquests.quest.QuestChapter;
import dev.vanillaplusplus.vppquests.quest.QuestSyncFormat;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.neoforge.network.PacketDistributor;

import java.util.List;
import java.util.Map;

/**
 * Client-side mirror of the server's quest registry + the local player's
 * progress, kept up to date by {@code ModNetworking}'s payload handlers.
 * {@link dev.vanillaplusplus.vppquests.client.gui.QuestScreen} reads
 * exclusively from here - never round-trips to the server per frame - per
 * DESIGN.md's #109 design-proposal section ("GUI/HUD render client-side off
 * a live mirror").
 */
public final class ClientQuestState {

    private static volatile Map<ResourceLocation, Quest> quests = Map.of();
    private static volatile Map<ResourceLocation, QuestChapter> chapters = Map.of();
    private static volatile QuestProgressAttachment progress = new QuestProgressAttachment();

    public static void applyDefinitions(String questsJson) {
        QuestSyncFormat.Parsed parsed = QuestSyncFormat.parse(questsJson);
        quests = parsed.quests();
        chapters = parsed.chapters();
    }

    public static void applyProgress(String progressJson) {
        progress = QuestProgressAttachment.fromJson(progressJson);
    }

    public static List<QuestChapter> chaptersSorted() {
        return chapters.values().stream()
                .sorted((a, b) -> Integer.compare(a.order(), b.order()))
                .toList();
    }

    public static List<Quest> questsInChapter(ResourceLocation chapterId) {
        return quests.values().stream()
                .filter(q -> q.chapter().equals(chapterId))
                .toList();
    }

    public static boolean isComplete(ResourceLocation questId) {
        return progress.isComplete(questId);
    }

    /** Whether {@code questId}'s rewards have already been claimed (GitHub #164 item 5). */
    public static boolean isClaimed(ResourceLocation questId) {
        return progress.isClaimed(questId);
    }

    public static int taskProgress(ResourceLocation questId, int taskIndex) {
        return progress.taskProgress(questId, taskIndex);
    }

    /**
     * Sends the Claim button's request to the server (GitHub #164 item 5).
     * Purely a request - the server ({@code QuestProgressTracker#claimReward})
     * re-validates completion/not-already-claimed before granting anything and
     * pushes back an updated {@code QuestProgressSyncPayload}, so this class's
     * local {@link #progress} mirror updates itself the normal way rather than
     * being mutated optimistically here.
     */
    public static void requestClaim(ResourceLocation questId) {
        PacketDistributor.sendToServer(new ClaimQuestRewardPayload(questId));
    }

    private ClientQuestState() {
    }
}
