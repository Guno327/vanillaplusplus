package dev.vanillaplusplus.vppquests.quest;

import com.google.gson.JsonObject;
import net.minecraft.resources.ResourceLocation;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit tests for {@link QuestRegistry}: lookups against an empty registry,
 * {@code reload} swapping the whole static instance, chapter sort order, and
 * {@link QuestRegistry#dependentsOf}'s reverse-adjacency map (built once at
 * construction from every quest's forward {@code dependencies} list).
 *
 * <p>{@link QuestRegistry#INSTANCE} is a static singleton swapped by
 * {@code reload}, so every test resets it to empty in {@link #resetRegistry()}
 * to avoid leaking quests/chapters between tests.
 */
class QuestRegistryTest {

    private static final ResourceLocation CH1 = ResourceLocation.parse("vppquests:ch1");
    private static final ResourceLocation CH2 = ResourceLocation.parse("vppquests:ch2");
    private static final ResourceLocation ENTER = ResourceLocation.parse("vppquests:ch1/enter");
    private static final ResourceLocation TASK_A = ResourceLocation.parse("vppquests:ch1/task_a");
    private static final ResourceLocation TASK_B = ResourceLocation.parse("vppquests:ch1/task_b");

    @AfterEach
    void resetRegistry() {
        QuestRegistry.reload(Map.of(), Map.of(), Map.of(), Map.of());
    }

    private static Quest quest(ResourceLocation id, ResourceLocation chapter, List<ResourceLocation> dependencies) {
        return new Quest(id, chapter, "title", List.of(), ResourceLocation.parse("minecraft:stone"),
                Quest.Frame.TASK, dependencies, List.of(), List.of(), false);
    }

    @Test
    void emptyRegistryReturnsEmptyLookupsNotNulls() {
        assertTrue(QuestRegistry.get().quest(ENTER).isEmpty());
        assertTrue(QuestRegistry.get().allQuests().isEmpty());
        assertTrue(QuestRegistry.get().allChaptersSorted().isEmpty());
        assertTrue(QuestRegistry.get().chapter(CH1).isEmpty());
        assertTrue(QuestRegistry.get().dependentsOf(ENTER).isEmpty());
        assertTrue(QuestRegistry.get().questsInChapter(CH1).isEmpty());
    }

    @Test
    void reloadReplacesPriorState() {
        Quest first = quest(ENTER, CH1, List.of());
        QuestRegistry.reload(Map.of(ENTER, first), Map.of(), Map.of(), Map.of());
        assertTrue(QuestRegistry.get().quest(ENTER).isPresent());

        // A second reload with a disjoint quest set must fully replace the
        // first, not merge with it.
        Quest second = quest(TASK_A, CH1, List.of());
        QuestRegistry.reload(Map.of(TASK_A, second), Map.of(), Map.of(), Map.of());

        assertTrue(QuestRegistry.get().quest(ENTER).isEmpty(), "prior reload's quest must not survive a new reload");
        assertTrue(QuestRegistry.get().quest(TASK_A).isPresent());
    }

    @Test
    void questsInChapterFiltersByChapterId() {
        Quest ch1Quest = quest(ENTER, CH1, List.of());
        Quest ch2Quest = quest(ResourceLocation.parse("vppquests:ch2/enter"), CH2, List.of());
        QuestRegistry.reload(Map.of(ENTER, ch1Quest, ch2Quest.id(), ch2Quest), Map.of(), Map.of(), Map.of());

        List<Quest> ch1Quests = QuestRegistry.get().questsInChapter(CH1);

        assertEquals(1, ch1Quests.size());
        assertEquals(ENTER, ch1Quests.get(0).id());
    }

    @Test
    void allChaptersSortedOrdersByOrderFieldAscending() {
        QuestChapter chapterA = new QuestChapter(CH1, "A", List.of(), ResourceLocation.parse("minecraft:stone"), 5);
        QuestChapter chapterB = new QuestChapter(CH2, "B", List.of(), ResourceLocation.parse("minecraft:stone"), 1);
        QuestRegistry.reload(Map.of(), Map.of(CH1, chapterA, CH2, chapterB), Map.of(), Map.of());

        List<QuestChapter> sorted = QuestRegistry.get().allChaptersSorted();

        assertEquals(List.of(chapterB, chapterA), sorted);
    }

    @Test
    void dependentsOfReturnsQuestsThatDeclareTheGivenDependency() {
        Quest enter = quest(ENTER, CH1, List.of());
        Quest taskA = quest(TASK_A, CH1, List.of(ENTER));
        Quest taskB = quest(TASK_B, CH1, List.of(ENTER));
        QuestRegistry.reload(Map.of(ENTER, enter, TASK_A, taskA, TASK_B, taskB), Map.of(), Map.of(), Map.of());

        List<ResourceLocation> dependents = QuestRegistry.get().dependentsOf(ENTER);

        assertEquals(2, dependents.size());
        assertTrue(dependents.contains(TASK_A));
        assertTrue(dependents.contains(TASK_B));
    }

    @Test
    void dependentsOfUnknownOrLeafQuestIsEmpty() {
        Quest enter = quest(ENTER, CH1, List.of());
        QuestRegistry.reload(Map.of(ENTER, enter), Map.of(), Map.of(), Map.of());

        assertTrue(QuestRegistry.get().dependentsOf(ENTER).isEmpty(), "nothing depends on ENTER in this fixture");
        assertTrue(QuestRegistry.get().dependentsOf(ResourceLocation.parse("vppquests:does_not_exist")).isEmpty());
    }

    @Test
    void rawQuestsAndRawChaptersAreExposedVerbatim() {
        JsonObject rawQuestJson = new JsonObject();
        rawQuestJson.addProperty("title", "raw");
        QuestRegistry.reload(Map.of(), Map.of(), Map.of(ENTER, rawQuestJson), Map.of());

        assertEquals(rawQuestJson, QuestRegistry.get().rawQuests().get(ENTER));
    }
}
