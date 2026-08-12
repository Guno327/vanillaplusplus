package dev.vanillaplusplus.vppquests.quest;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.resources.ResourceLocation;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Unit tests for {@link QuestChapter#fromJson}'s field parsing and optional-field defaults. */
class QuestChapterTest {

    private static JsonObject parse(String json) {
        return JsonParser.parseString(json).getAsJsonObject();
    }

    @Test
    void fromJsonParsesAllFieldsWhenPresent() {
        JsonObject json = parse("""
                {
                  "title": "Stone Age",
                  "subtitle": ["The beginning"],
                  "icon": "minecraft:stone",
                  "order": 3
                }
                """);
        ResourceLocation id = ResourceLocation.parse("vppquests:ch1");

        QuestChapter chapter = QuestChapter.fromJson(id, json);

        assertEquals(id, chapter.id());
        assertEquals("Stone Age", chapter.title());
        assertEquals(List.of("The beginning"), chapter.subtitle());
        assertEquals(ResourceLocation.parse("minecraft:stone"), chapter.icon());
        assertEquals(3, chapter.order());
    }

    @Test
    void fromJsonAppliesDefaultsWhenOptionalFieldsAbsent() {
        JsonObject json = parse("""
                {
                  "title": "Stone Age",
                  "icon": "minecraft:stone"
                }
                """);
        ResourceLocation id = ResourceLocation.parse("vppquests:ch1");

        QuestChapter chapter = QuestChapter.fromJson(id, json);

        assertTrue(chapter.subtitle().isEmpty());
        assertEquals(0, chapter.order());
    }
}
