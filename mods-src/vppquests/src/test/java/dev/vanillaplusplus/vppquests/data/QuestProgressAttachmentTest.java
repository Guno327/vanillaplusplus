package dev.vanillaplusplus.vppquests.data;

import net.minecraft.resources.ResourceLocation;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit tests for {@link QuestProgressAttachment}'s {@code toJson}/{@code
 * fromJson} codec round-trip (the same technique {@code
 * QuestProgressSyncPayload} relies on to keep the NBT save format and the
 * network wire format from drifting apart - see that class's doc), covering
 * completed quest ids and per-task progress counters.
 */
class QuestProgressAttachmentTest {

    private static final ResourceLocation ENTER = ResourceLocation.parse("vppquests:ch1/enter");
    private static final ResourceLocation TASK_A = ResourceLocation.parse("vppquests:ch1/task_a");

    @Test
    void roundTripPreservesCompletedQuestsAndTaskProgress() {
        QuestProgressAttachment original = new QuestProgressAttachment();
        original.markComplete(ENTER);
        original.setTaskProgress(TASK_A, 0, 3);
        original.setTaskProgress(TASK_A, 1, 1);

        QuestProgressAttachment restored = QuestProgressAttachment.fromJson(original.toJson());

        assertEquals(original.completedQuests(), restored.completedQuests());
        assertTrue(restored.isComplete(ENTER));
        assertEquals(3, restored.taskProgress(TASK_A, 0));
        assertEquals(1, restored.taskProgress(TASK_A, 1));
    }

    @Test
    void roundTripOfFreshAttachmentIsEmpty() {
        QuestProgressAttachment original = new QuestProgressAttachment();

        QuestProgressAttachment restored = QuestProgressAttachment.fromJson(original.toJson());

        assertTrue(restored.completedQuests().isEmpty());
        assertFalse(restored.isComplete(ENTER));
        assertEquals(0, restored.taskProgress(TASK_A, 0));
    }

    @Test
    void taskProgressForUnsetTaskDefaultsToZero() {
        QuestProgressAttachment attachment = new QuestProgressAttachment();

        assertEquals(0, attachment.taskProgress(TASK_A, 0));
    }

    @Test
    void malformedJsonFallsBackToEmptyAttachmentRatherThanThrowing() {
        QuestProgressAttachment restored = QuestProgressAttachment.fromJson("{\"not\":\"valid\"}");

        assertTrue(restored.completedQuests().isEmpty());
        assertEquals(0, restored.taskProgress(TASK_A, 0));
    }

    @Test
    void completedQuestsReturnsSnapshotNotLiveView() {
        QuestProgressAttachment attachment = new QuestProgressAttachment();
        attachment.markComplete(ENTER);

        var snapshot = attachment.completedQuests();
        attachment.markComplete(TASK_A);

        assertEquals(1, snapshot.size(), "snapshot taken before the second markComplete must not grow");
        assertTrue(attachment.completedQuests().contains(TASK_A));
    }
}
