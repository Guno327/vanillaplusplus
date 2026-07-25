package dev.vanillaplusplus.vppskills.unlock;

import dev.vanillaplusplus.vppskills.data.SkillProgressAttachment;
import dev.vanillaplusplus.vppskills.tree.SkillTreeCategory;
import dev.vanillaplusplus.vppskills.tree.SkillTreeConnection;
import dev.vanillaplusplus.vppskills.tree.SkillTreeNode;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit tests for {@link SkillUnlockValidator}: adjacency, already-unlocked
 * rejection, and cost/point-sufficiency checks, plus the mutating
 * {@link SkillUnlockValidator#tryUnlock} debiting points and adding the node
 * only on success, per #163 phase-2's hard test requirement (a).
 *
 * <p>Fixture tree: {@code root} -> {@code mid} -> {@code leaf}, a simple
 * three-node chain, plus a disconnected {@code island} node to exercise
 * "exists but not adjacent to anything unlocked".
 */
class SkillUnlockValidatorTest {

    private static SkillTreeCategory chainCategory() {
        List<SkillTreeNode> nodes = List.of(
                new SkillTreeNode("root", "cat", 0, 0, true, null, "Root", null),
                new SkillTreeNode("mid", "cat", 1, 0, false, null, "Mid", null),
                new SkillTreeNode("leaf", "cat", 2, 0, false, null, "Leaf", null),
                new SkillTreeNode("island", "cat", 5, 5, false, null, "Island", null));
        List<SkillTreeConnection> connections = List.of(
                new SkillTreeConnection("root", "mid", "normal"),
                new SkillTreeConnection("mid", "leaf", "normal"));
        return new SkillTreeCategory("cat", "Category", null, nodes, connections);
    }

    @Test
    void rootIsAlwaysUnlockableWithEnoughPoints() {
        SkillTreeCategory category = chainCategory();
        assertEquals(SkillUnlockValidator.Result.OK,
                SkillUnlockValidator.check(category, "root", Set.of(), 1));
    }

    @Test
    void nonRootRejectedWhenNoAdjacentNodeUnlocked() {
        SkillTreeCategory category = chainCategory();
        // "mid" needs "root" unlocked first; nothing is unlocked yet.
        assertEquals(SkillUnlockValidator.Result.NOT_ADJACENT,
                SkillUnlockValidator.check(category, "mid", Set.of(), 1));
    }

    @Test
    void disconnectedIslandNodeRejectedEvenWithUnrelatedUnlocks() {
        SkillTreeCategory category = chainCategory();
        assertEquals(SkillUnlockValidator.Result.NOT_ADJACENT,
                SkillUnlockValidator.check(category, "island", Set.of("root", "mid", "leaf"), 10));
    }

    @Test
    void adjacentNodeAcceptedViaEitherConnectionDirection() {
        SkillTreeCategory category = chainCategory();
        // connection is stored as (root -> mid); unlocking "mid" from "root" being unlocked...
        assertEquals(SkillUnlockValidator.Result.OK,
                SkillUnlockValidator.check(category, "mid", Set.of("root"), 1));
        // ...and "leaf" adjacent to "mid" via the same (fromId, toId) shape, checked from the "toId" side.
        assertEquals(SkillUnlockValidator.Result.OK,
                SkillUnlockValidator.check(category, "leaf", Set.of("mid"), 1));
    }

    @Test
    void alreadyUnlockedNodeRejected() {
        SkillTreeCategory category = chainCategory();
        assertEquals(SkillUnlockValidator.Result.ALREADY_UNLOCKED,
                SkillUnlockValidator.check(category, "root", Set.of("root"), 10));
    }

    @Test
    void unknownNodeIdRejected() {
        SkillTreeCategory category = chainCategory();
        assertEquals(SkillUnlockValidator.Result.NODE_NOT_FOUND,
                SkillUnlockValidator.check(category, "does_not_exist", Set.of(), 10));
    }

    @Test
    void insufficientPointsRejectedEvenWhenAdjacencyIsFine() {
        SkillTreeCategory category = chainCategory();
        assertEquals(SkillUnlockValidator.Result.INSUFFICIENT_POINTS,
                SkillUnlockValidator.check(category, "root", Set.of(), 0));
    }

    @Test
    void tryUnlockDebitsPointsAndAddsNodeOnSuccess() {
        SkillTreeCategory category = chainCategory();
        SkillProgressAttachment progress = new SkillProgressAttachment();
        progress.grantPoints(3);

        SkillUnlockValidator.Result result = SkillUnlockValidator.tryUnlock(category, "root", progress);

        assertEquals(SkillUnlockValidator.Result.OK, result);
        assertTrue(progress.isUnlocked("root"));
        assertEquals(3 - SkillUnlockValidator.NODE_COST, progress.availablePoints());
        assertEquals(SkillUnlockValidator.NODE_COST, progress.spentPoints());
    }

    @Test
    void tryUnlockLeavesAttachmentUntouchedOnRejection() {
        SkillTreeCategory category = chainCategory();
        SkillProgressAttachment progress = new SkillProgressAttachment();
        progress.grantPoints(3);

        // "mid" is not adjacent to anything unlocked yet - must be rejected without mutating state.
        SkillUnlockValidator.Result result = SkillUnlockValidator.tryUnlock(category, "mid", progress);

        assertEquals(SkillUnlockValidator.Result.NOT_ADJACENT, result);
        assertTrue(progress.unlockedNodeIds().isEmpty());
        assertEquals(3, progress.availablePoints());
        assertEquals(0, progress.spentPoints());
    }
}
