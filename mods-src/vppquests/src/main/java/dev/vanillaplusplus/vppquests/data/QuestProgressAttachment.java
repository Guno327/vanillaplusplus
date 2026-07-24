package dev.vanillaplusplus.vppquests.data;

import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import com.mojang.serialization.Codec;
import com.mojang.serialization.JsonOps;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import dev.vanillaplusplus.vppquests.VppQuests;
import net.minecraft.resources.ResourceLocation;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Per-player (or per-party, once a future {@code getPartyKey(player)} seam
 * is wired up) quest progress: completed quest ids plus in-progress task
 * counters, persisted via a NeoForge data attachment (the modern
 * capability-system replacement) on the player entity, per DESIGN.md's
 * #109 design-proposal section ("Progress tracking/persistence").
 *
 * <p><b>Scope note:</b> progress is attached to the player entity directly
 * (solo-player semantics only). A party-shared-completion mode (any
 * teammate finishing a task marks it done for the whole team, but rewards
 * stay strictly per-player) would need a {@code getPartyKey(player)} seam
 * calling Open Parties and Claims' {@code getPartyByMember(UUID)} - not
 * wired in yet (no party/gameplay-system code has been in scope for any
 * #109 milestone so far); {@link #completed} keyed per-player is the
 * foundation a later phase can re-key onto a party id without changing
 * this class's shape.
 */
public final class QuestProgressAttachment {

    private final Set<ResourceLocation> completed = new HashSet<>();
    /** Keyed by {@code questId + "#" + taskIndex} -> progress count toward that task's target. */
    private final Map<String, Integer> taskProgress = new HashMap<>();

    public boolean isComplete(ResourceLocation questId) {
        return completed.contains(questId);
    }

    public void markComplete(ResourceLocation questId) {
        completed.add(questId);
    }

    public Set<ResourceLocation> completedQuests() {
        return Set.copyOf(completed);
    }

    public int taskProgress(ResourceLocation questId, int taskIndex) {
        return taskProgress.getOrDefault(taskKey(questId, taskIndex), 0);
    }

    public void setTaskProgress(ResourceLocation questId, int taskIndex, int count) {
        taskProgress.put(taskKey(questId, taskIndex), count);
    }

    private static String taskKey(ResourceLocation questId, int taskIndex) {
        return questId + "#" + taskIndex;
    }

    public static final Codec<QuestProgressAttachment> CODEC = RecordCodecBuilder.create(instance -> instance.group(
            ResourceLocation.CODEC.listOf().fieldOf("completed").forGetter(a -> List.copyOf(a.completed)),
            Codec.unboundedMap(Codec.STRING, Codec.INT).fieldOf("taskProgress").forGetter(a -> Map.copyOf(a.taskProgress))
    ).apply(instance, (completedList, progressMap) -> {
        QuestProgressAttachment attachment = new QuestProgressAttachment();
        attachment.completed.addAll(completedList);
        attachment.taskProgress.putAll(progressMap);
        return attachment;
    }));

    /**
     * Re-uses {@link #CODEC} (already the source of truth for this
     * attachment's NBT persistence) to produce the JSON string
     * {@code QuestProgressSyncPayload} sends to the owning client, so the
     * network wire format and the save-data format can never drift apart.
     */
    public String toJson() {
        return CODEC.encodeStart(JsonOps.INSTANCE, this)
                .resultOrPartial(error -> VppQuests.LOGGER.error("vppquests: failed to encode quest progress: {}", error))
                .map(JsonElement::toString)
                .orElse("{}");
    }

    public static QuestProgressAttachment fromJson(String json) {
        JsonElement element = JsonParser.parseString(json);
        return CODEC.parse(JsonOps.INSTANCE, element)
                .resultOrPartial(error -> VppQuests.LOGGER.error("vppquests: failed to decode quest progress: {}", error))
                .orElseGet(QuestProgressAttachment::new);
    }
}
