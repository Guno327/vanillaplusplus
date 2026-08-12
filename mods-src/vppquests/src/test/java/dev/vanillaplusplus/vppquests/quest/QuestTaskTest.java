package dev.vanillaplusplus.vppquests.quest;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.resources.ResourceLocation;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit tests for {@link QuestTask#fromJson} (all 5 task types), each type's
 * {@code describeProgress}/{@code targetCount}, and - via {@code Item}'s
 * {@code displayName()}, the only public entry point into the private
 * {@code prettifyPath} helper - the title-casing of an unresolved id's path
 * segment ({@code "andesite_alloy"} -> {@code "Andesite Alloy"}).
 */
class QuestTaskTest {

    private static JsonObject parse(String json) {
        return JsonParser.parseString(json).getAsJsonObject();
    }

    @Test
    void itemFromJsonParsesFieldsAndDefaults() {
        QuestTask task = QuestTask.fromJson(parse("{\"type\":\"item\",\"item\":\"minecraft:diamond\",\"count\":3}"));

        assertEquals("item", task.type());
        QuestTask.Item item = (QuestTask.Item) task;
        assertEquals(ResourceLocation.parse("minecraft:diamond"), item.item());
        assertEquals(3, item.count());
        assertTrue(item.consume(), "consume defaults to true when absent");
        assertFalse(item.onlyFromCrafting(), "onlyFromCrafting defaults to false when absent");
        assertFalse(item.tag());
        assertEquals(3, item.targetCount());
    }

    @Test
    void itemFromJsonDetectsTagPrefixAndStripsIt() {
        QuestTask task = QuestTask.fromJson(parse("{\"type\":\"item\",\"item\":\"#minecraft:logs\"}"));

        QuestTask.Item item = (QuestTask.Item) task;
        assertTrue(item.tag());
        assertEquals(ResourceLocation.parse("minecraft:logs"), item.item());
        assertEquals(1, item.count(), "count defaults to 1 when absent");
    }

    @Test
    void itemFromJsonHonorsExplicitConsumeAndOnlyFromCrafting() {
        QuestTask task = QuestTask.fromJson(
                parse("{\"type\":\"item\",\"item\":\"minecraft:diamond\",\"consume\":false,\"onlyFromCrafting\":true}"));

        QuestTask.Item item = (QuestTask.Item) task;
        assertFalse(item.consume());
        assertTrue(item.onlyFromCrafting());
    }

    @Test
    void itemDescribeProgressCapsAtTargetAndIncludesTagMarker() {
        QuestTask.Item item = new QuestTask.Item(ResourceLocation.parse("minecraft:logs"), 5, true, false, true);

        assertEquals("5/5 #minecraft:logs", item.describeProgress(999));
        assertEquals("0/5 #minecraft:logs", item.describeProgress(0));
    }

    @Test
    void itemDisplayNameForTagPrettifiesPathAndPrefixesAny() {
        QuestTask.Item item = new QuestTask.Item(ResourceLocation.parse("minecraft:andesite_alloy"), 1, true, false, true);

        assertEquals("Any Andesite Alloy", item.displayName().getString());
    }

    // NOTE: Item#displayName()'s non-tag branch resolves through
    // BuiltInRegistries.ITEM, whose static initializer refuses to run
    // ("Not bootstrapped") outside a real game/Bootstrap.bootStrap() call -
    // not something plain JUnit can do without pulling in a much heavier,
    // fragile headless-bootstrap setup that no other test in this repo
    // relies on. The tag branch (tested above) never touches the registry,
    // so it - and prettifyPath, exercised transitively through it - is
    // covered without that dependency; the registry-resolution branch itself
    // is left untested here (see #194's DESCOPED reporting).

    @Test
    void killFromJsonParsesFieldsAndDefaults() {
        QuestTask task = QuestTask.fromJson(parse("{\"type\":\"kill\",\"entity\":\"minecraft:zombie\"}"));

        assertEquals("kill", task.type());
        QuestTask.Kill kill = (QuestTask.Kill) task;
        assertEquals(ResourceLocation.parse("minecraft:zombie"), kill.entity());
        assertEquals(1, kill.count());
        assertEquals(1, kill.targetCount());
    }

    @Test
    void killDescribeProgressCapsAtTarget() {
        QuestTask.Kill kill = new QuestTask.Kill(ResourceLocation.parse("minecraft:zombie"), 3);

        assertEquals("3/3 minecraft:zombie killed", kill.describeProgress(10));
        assertEquals("1/3 minecraft:zombie killed", kill.describeProgress(1));
    }

    @Test
    void dimensionFromJsonParsesFieldAndHasTargetCountOne() {
        QuestTask task = QuestTask.fromJson(parse("{\"type\":\"dimension\",\"dimension\":\"minecraft:the_nether\"}"));

        assertEquals("dimension", task.type());
        QuestTask.Dimension dimension = (QuestTask.Dimension) task;
        assertEquals(ResourceLocation.parse("minecraft:the_nether"), dimension.dimension());
        assertEquals(1, dimension.targetCount());
        assertEquals("Not yet visited minecraft:the_nether", dimension.describeProgress(0));
        assertEquals("Visited minecraft:the_nether", dimension.describeProgress(1));
    }

    @Test
    void gamestageFromJsonParsesFieldAndHasTargetCountOne() {
        QuestTask task = QuestTask.fromJson(parse("{\"type\":\"gamestage\",\"stage\":\"iron_age\"}"));

        assertEquals("gamestage", task.type());
        QuestTask.Gamestage gamestage = (QuestTask.Gamestage) task;
        assertEquals("iron_age", gamestage.stage());
        assertEquals(1, gamestage.targetCount());
        assertEquals("Stage not yet reached: iron_age", gamestage.describeProgress(0));
        assertEquals("Stage reached: iron_age", gamestage.describeProgress(1));
    }

    @Test
    void checkmarkFromJsonHasTargetCountOne() {
        QuestTask task = QuestTask.fromJson(parse("{\"type\":\"checkmark\"}"));

        assertEquals("checkmark", task.type());
        assertEquals(1, task.targetCount());
        assertEquals("Not yet acknowledged", task.describeProgress(0));
        assertEquals("Acknowledged", task.describeProgress(1));
    }

    @Test
    void unknownTaskTypeThrows() {
        assertThrows(IllegalArgumentException.class,
                () -> QuestTask.fromJson(parse("{\"type\":\"not_a_type\"}")));
    }
}
