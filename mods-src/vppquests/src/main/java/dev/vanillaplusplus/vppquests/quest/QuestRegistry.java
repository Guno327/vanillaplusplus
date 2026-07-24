package dev.vanillaplusplus.vppquests.quest;

import com.google.gson.JsonObject;
import net.minecraft.resources.ResourceLocation;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * In-memory quest/chapter registry, rebuilt on every
 * {@link QuestReloadListener} reload (datapack load or {@code /reload}),
 * same "generate, don't hand-type, reload like everything else" discipline
 * this pack's other systems already follow.
 *
 * <p>Held as a single mutable static instance swapped atomically on reload
 * (matches how {@link net.minecraft.world.item.crafting.RecipeManager} and
 * similar vanilla registries are consumed elsewhere) rather than exposed as
 * an injected service, since Phase A has exactly one registry and no need
 * for multiple instances.
 */
public final class QuestRegistry {

    private static volatile QuestRegistry INSTANCE = new QuestRegistry(Map.of(), Map.of(), Map.of(), Map.of());

    private final Map<ResourceLocation, Quest> quests;
    private final Map<ResourceLocation, QuestChapter> chapters;
    private final Map<ResourceLocation, JsonObject> rawQuests;
    private final Map<ResourceLocation, JsonObject> rawChapters;
    private final Map<ResourceLocation, List<ResourceLocation>> dependents;

    private QuestRegistry(
            Map<ResourceLocation, Quest> quests,
            Map<ResourceLocation, QuestChapter> chapters,
            Map<ResourceLocation, JsonObject> rawQuests,
            Map<ResourceLocation, JsonObject> rawChapters) {
        this.quests = quests;
        this.chapters = chapters;
        this.rawQuests = rawQuests;
        this.rawChapters = rawChapters;
        this.dependents = buildDependents(quests);
    }

    private static Map<ResourceLocation, List<ResourceLocation>> buildDependents(Map<ResourceLocation, Quest> quests) {
        Map<ResourceLocation, List<ResourceLocation>> result = new HashMap<>();
        for (Quest quest : quests.values()) {
            for (ResourceLocation dep : quest.dependencies()) {
                result.computeIfAbsent(dep, k -> new ArrayList<>()).add(quest.id());
            }
        }
        return result;
    }

    public static void reload(
            Map<ResourceLocation, Quest> quests,
            Map<ResourceLocation, QuestChapter> chapters,
            Map<ResourceLocation, JsonObject> rawQuests,
            Map<ResourceLocation, JsonObject> rawChapters) {
        INSTANCE = new QuestRegistry(Map.copyOf(quests), Map.copyOf(chapters), Map.copyOf(rawQuests), Map.copyOf(rawChapters));
    }

    public static QuestRegistry get() {
        return INSTANCE;
    }

    /** Raw on-disk JSON per quest id - used only by {@code QuestNetworkSync} to build the sync payload. */
    public Map<ResourceLocation, JsonObject> rawQuests() {
        return rawQuests;
    }

    /** Raw on-disk JSON per chapter id - used only by {@code QuestNetworkSync} to build the sync payload. */
    public Map<ResourceLocation, JsonObject> rawChapters() {
        return rawChapters;
    }

    public Optional<Quest> quest(ResourceLocation id) {
        return Optional.ofNullable(quests.get(id));
    }

    public List<Quest> questsInChapter(ResourceLocation chapterId) {
        return quests.values().stream()
                .filter(q -> q.chapter().equals(chapterId))
                .toList();
    }

    public List<Quest> allQuests() {
        return List.copyOf(quests.values());
    }

    public List<QuestChapter> allChaptersSorted() {
        List<QuestChapter> sorted = new ArrayList<>(chapters.values());
        sorted.sort((a, b) -> Integer.compare(a.order(), b.order()));
        return Collections.unmodifiableList(sorted);
    }

    public Optional<QuestChapter> chapter(ResourceLocation id) {
        return Optional.ofNullable(chapters.get(id));
    }

    /** Quests whose {@code dependencies} include the given quest id. */
    public List<ResourceLocation> dependentsOf(ResourceLocation questId) {
        return dependents.getOrDefault(questId, List.of());
    }
}
