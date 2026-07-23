package dev.vanillaplusplus.vppquests.client;

import dev.vanillaplusplus.vppquests.data.QuestProgressAttachment;
import dev.vanillaplusplus.vppquests.quest.Quest;
import dev.vanillaplusplus.vppquests.quest.QuestChapter;
import dev.vanillaplusplus.vppquests.quest.QuestSyncFormat;
import net.minecraft.resources.ResourceLocation;

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

    public static int taskProgress(ResourceLocation questId, int taskIndex) {
        return progress.taskProgress(questId, taskIndex);
    }

    private ClientQuestState() {
    }
}
