package dev.vanillaplusplus.vppquests.quest;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.resources.ResourceLocation;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit tests for {@link QuestSyncFormat}'s serialize -> parse round-trip: the
 * registry's raw per-id quest/chapter JSON survives being wrapped into one
 * blob and unwrapped back into typed {@link Quest}/{@link QuestChapter}
 * records via the exact same {@code fromJson} parsing the server's datapack
 * reload path uses.
 */
class QuestSyncFormatTest {

    private static final ResourceLocation CH1 = ResourceLocation.parse("vppquests:ch1");
    private static final ResourceLocation ENTER = ResourceLocation.parse("vppquests:ch1/enter");

    @AfterEach
    void resetRegistry() {
        QuestRegistry.reload(Map.of(), Map.of(), Map.of(), Map.of());
    }

    private static JsonObject parse(String json) {
        return JsonParser.parseString(json).getAsJsonObject();
    }

    @Test
    void serializeThenParseRoundTripsQuestsAndChapters() {
        JsonObject rawQuest = parse("""
                {
                  "chapter": "vppquests:ch1",
                  "title": "Enter the Stone Age",
                  "icon": "minecraft:stone",
                  "tasks": [{"type": "checkmark"}]
                }
                """);
        JsonObject rawChapter = parse("""
                {
                  "title": "Stone Age",
                  "icon": "minecraft:stone",
                  "order": 1
                }
                """);
        QuestRegistry.reload(Map.of(), Map.of(), Map.of(ENTER, rawQuest), Map.of(CH1, rawChapter));

        String serialized = QuestSyncFormat.serialize(QuestRegistry.get());
        QuestSyncFormat.Parsed parsed = QuestSyncFormat.parse(serialized);

        assertEquals(1, parsed.quests().size());
        assertEquals(1, parsed.chapters().size());
        Quest quest = parsed.quests().get(ENTER);
        assertEquals("Enter the Stone Age", quest.title());
        assertEquals(1, quest.tasks().size());
        QuestChapter chapter = parsed.chapters().get(CH1);
        assertEquals("Stone Age", chapter.title());
        assertEquals(1, chapter.order());
    }

    @Test
    void serializeOfEmptyRegistryParsesBackToEmptyMaps() {
        QuestRegistry.reload(Map.of(), Map.of(), Map.of(), Map.of());

        String serialized = QuestSyncFormat.serialize(QuestRegistry.get());
        QuestSyncFormat.Parsed parsed = QuestSyncFormat.parse(serialized);

        assertTrue(parsed.quests().isEmpty());
        assertTrue(parsed.chapters().isEmpty());
    }
}
