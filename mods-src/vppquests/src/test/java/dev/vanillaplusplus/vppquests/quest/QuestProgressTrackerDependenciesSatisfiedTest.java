package dev.vanillaplusplus.vppquests.quest;

import dev.vanillaplusplus.vppquests.data.QuestProgressAttachment;
import net.minecraft.resources.ResourceLocation;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit test for {@link QuestProgressTracker#dependenciesSatisfied}, the one
 * piece of {@link QuestProgressTracker} that is pure and
 * {@code ServerPlayer}-free (everything else in that class reads inventory/
 * stats/dimension off a live {@code ServerPlayer} and cannot run under plain
 * JUnit - see the #194 task's DESCOPED section). Made package-private
 * (previously {@code private}) specifically so this AND-gate over a quest's
 * dependency list is directly testable; no other behaviour changed.
 */
class QuestProgressTrackerDependenciesSatisfiedTest {

    private static final ResourceLocation DEP_A = ResourceLocation.parse("vppquests:ch1/dep_a");
    private static final ResourceLocation DEP_B = ResourceLocation.parse("vppquests:ch1/dep_b");

    private static Quest questWithDependencies(List<ResourceLocation> dependencies) {
        return new Quest(
                ResourceLocation.parse("vppquests:ch1/target"),
                ResourceLocation.parse("vppquests:ch1"),
                "title",
                List.of(),
                ResourceLocation.parse("minecraft:stone"),
                Quest.Frame.TASK,
                dependencies,
                List.of(),
                List.of(),
                false);
    }

    @Test
    void questWithNoDependenciesIsAlwaysSatisfied() {
        QuestProgressAttachment progress = new QuestProgressAttachment();

        assertTrue(QuestProgressTracker.dependenciesSatisfied(questWithDependencies(List.of()), progress));
    }

    @Test
    void singleUnmetDependencyIsUnsatisfied() {
        QuestProgressAttachment progress = new QuestProgressAttachment();

        assertFalse(QuestProgressTracker.dependenciesSatisfied(questWithDependencies(List.of(DEP_A)), progress));
    }

    @Test
    void allDependenciesMetIsSatisfied() {
        QuestProgressAttachment progress = new QuestProgressAttachment();
        progress.markComplete(DEP_A);
        progress.markComplete(DEP_B);

        assertTrue(QuestProgressTracker.dependenciesSatisfied(questWithDependencies(List.of(DEP_A, DEP_B)), progress));
    }

    @Test
    void oneOfTwoDependenciesMetIsStillUnsatisfied() {
        QuestProgressAttachment progress = new QuestProgressAttachment();
        progress.markComplete(DEP_A);

        assertFalse(QuestProgressTracker.dependenciesSatisfied(questWithDependencies(List.of(DEP_A, DEP_B)), progress));
    }
}
