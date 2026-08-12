package dev.vanillaplusplus.vppquests.quest;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.resources.ResourceLocation;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit tests for {@link Quest#fromJson}: field parsing including the
 * optional-field defaults ({@code description}, {@code dependencies},
 * {@code frame}, {@code criticalPath} all have documented fallbacks when
 * absent from the JSON), plus {@link Quest.Frame#fromJson}'s case-insensitive
 * enum parsing.
 */
class QuestTest {

    private static JsonObject parse(String json) {
        return JsonParser.parseString(json).getAsJsonObject();
    }

    @Test
    void fromJsonParsesAllFieldsWhenPresent() {
        JsonObject json = parse("""
                {
                  "chapter": "vppquests:ch1",
                  "title": "Enter the Stone Age",
                  "description": ["line one", "line two"],
                  "icon": "minecraft:stone",
                  "frame": "challenge",
                  "dependencies": ["vppquests:ch0/finale"],
                  "tasks": [{"type": "checkmark"}],
                  "rewards": [{"type": "xp", "category": "adventurer", "amount": 10}],
                  "criticalPath": true
                }
                """);
        ResourceLocation id = ResourceLocation.parse("vppquests:ch1/enter");

        Quest quest = Quest.fromJson(id, json);

        assertEquals(id, quest.id());
        assertEquals(ResourceLocation.parse("vppquests:ch1"), quest.chapter());
        assertEquals("Enter the Stone Age", quest.title());
        assertEquals(List.of("line one", "line two"), quest.description());
        assertEquals(ResourceLocation.parse("minecraft:stone"), quest.icon());
        assertEquals(Quest.Frame.CHALLENGE, quest.frame());
        assertEquals(List.of(ResourceLocation.parse("vppquests:ch0/finale")), quest.dependencies());
        assertEquals(1, quest.tasks().size());
        assertEquals(1, quest.rewards().size());
        assertTrue(quest.criticalPath());
    }

    @Test
    void fromJsonAppliesDefaultsWhenOptionalFieldsAbsent() {
        JsonObject json = parse("""
                {
                  "chapter": "vppquests:ch1",
                  "title": "Bare Minimum",
                  "icon": "minecraft:stone"
                }
                """);
        ResourceLocation id = ResourceLocation.parse("vppquests:ch1/bare");

        Quest quest = Quest.fromJson(id, json);

        assertTrue(quest.description().isEmpty());
        assertEquals(Quest.Frame.TASK, quest.frame());
        assertTrue(quest.dependencies().isEmpty());
        assertTrue(quest.tasks().isEmpty());
        assertTrue(quest.rewards().isEmpty());
        assertFalse(quest.criticalPath());
    }

    @Test
    void frameFromJsonIsCaseInsensitive() {
        assertEquals(Quest.Frame.GOAL, Quest.Frame.fromJson(parse("{\"frame\":\"GOAL\"}")));
        assertEquals(Quest.Frame.GOAL, Quest.Frame.fromJson(parse("{\"frame\":\"goal\"}")));
    }

    @Test
    void frameFromJsonRejectsUnknownValue() {
        assertThrows(IllegalArgumentException.class,
                () -> Quest.Frame.fromJson(parse("{\"frame\":\"not_a_frame\"}")));
    }
}
