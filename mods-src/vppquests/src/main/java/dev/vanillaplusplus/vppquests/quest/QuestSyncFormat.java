package dev.vanillaplusplus.vppquests.quest;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.resources.ResourceLocation;

import java.util.HashMap;
import java.util.Map;

/**
 * Common (loaded on both physical sides) wire format for
 * {@code QuestDefinitionsSyncPayload}: wraps the registry's raw per-id JSON
 * (see {@link QuestRegistry#rawQuests()}/{@link QuestRegistry#rawChapters()})
 * into one JSON blob, and unwraps it back into typed records using the
 * exact same {@link Quest#fromJson}/{@link QuestChapter#fromJson} parsing
 * the server's datapack reload path already uses - so server and client
 * always agree on how a quest/chapter JSON object turns into a record,
 * without a second hand-written serializer to keep in sync.
 */
public final class QuestSyncFormat {

    public record Parsed(Map<ResourceLocation, Quest> quests, Map<ResourceLocation, QuestChapter> chapters) {
    }

    public static String serialize(QuestRegistry registry) {
        JsonObject root = new JsonObject();

        JsonObject chaptersJson = new JsonObject();
        registry.rawChapters().forEach((id, json) -> chaptersJson.add(id.toString(), json));
        root.add("chapters", chaptersJson);

        JsonObject questsJson = new JsonObject();
        registry.rawQuests().forEach((id, json) -> questsJson.add(id.toString(), json));
        root.add("quests", questsJson);

        return root.toString();
    }

    public static Parsed parse(String json) {
        JsonObject root = JsonParser.parseString(json).getAsJsonObject();

        Map<ResourceLocation, QuestChapter> chapters = new HashMap<>();
        JsonObject chaptersJson = root.getAsJsonObject("chapters");
        if (chaptersJson != null) {
            for (String key : chaptersJson.keySet()) {
                ResourceLocation id = ResourceLocation.parse(key);
                chapters.put(id, QuestChapter.fromJson(id, chaptersJson.getAsJsonObject(key)));
            }
        }

        Map<ResourceLocation, Quest> quests = new HashMap<>();
        JsonObject questsJson = root.getAsJsonObject("quests");
        if (questsJson != null) {
            for (String key : questsJson.keySet()) {
                ResourceLocation id = ResourceLocation.parse(key);
                quests.put(id, Quest.fromJson(id, questsJson.getAsJsonObject(key)));
            }
        }

        return new Parsed(quests, chapters);
    }

    private QuestSyncFormat() {
    }
}
