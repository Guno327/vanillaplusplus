package dev.vanillaplusplus.vppskills.unlock;

import dev.vanillaplusplus.vppskills.data.SkillProgressAttachment;
import dev.vanillaplusplus.vppskills.tree.SkillTreeCategory;
import dev.vanillaplusplus.vppskills.tree.SkillTreeConnection;
import dev.vanillaplusplus.vppskills.tree.SkillTreeNode;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Unit tests for {@link SkillRefundValidator}: the connectivity-safe
 * per-node refund that must preserve {@link SkillUnlockValidator}'s
 * invariant - every unlocked node reachable from an unlocked root through
 * other unlocked nodes - by rejecting any single-node refund that would
 * orphan a still-unlocked descendant, per #205.
 *
 * <p>Uses several fixture shapes: a simple three-node chain (mirrors
 * {@code SkillUnlockValidatorTest}'s fixture), a bridged two-root graph, and
 * a diamond/cycle graph, specifically to catch two classes of naive-but-wrong
 * implementation: (1) one that only checks whether a node was locally
 * adjacent to the refunded node, missing that it has an alternate path to a
 * DIFFERENT root; and (2) one that walks a single parent-pointer/tree path
 * per node instead of doing a real reachability search, missing that a
 * diamond's other arm still connects a node back to its root.
 */
class SkillRefundValidatorTest {

    private static SkillTreeCategory chainCategory() {
        List<SkillTreeNode> nodes = List.of(
                new SkillTreeNode("root", "cat", 0, 0, true, null, "Root", null),
                new SkillTreeNode("mid", "cat", 1, 0, false, null, "Mid", null),
                new SkillTreeNode("leaf", "cat", 2, 0, false, null, "Leaf", null));
        List<SkillTreeConnection> connections = List.of(
                new SkillTreeConnection("root", "mid", "normal"),
                new SkillTreeConnection("mid", "leaf", "normal"));
        return new SkillTreeCategory("cat", "Category", null, nodes, connections);
    }

    /** Two roots bridged through a shared node: root1 -> a -> b <- root2. */
    private static SkillTreeCategory bridgedTwoRootCategory() {
        List<SkillTreeNode> nodes = List.of(
                new SkillTreeNode("root1", "cat", 0, 0, true, null, "Root1", null),
                new SkillTreeNode("a", "cat", 1, 0, false, null, "A", null),
                new SkillTreeNode("b", "cat", 2, 0, false, null, "B", null),
                new SkillTreeNode("root2", "cat", 3, 0, true, null, "Root2", null));
        List<SkillTreeConnection> connections = List.of(
                new SkillTreeConnection("root1", "a", "normal"),
                new SkillTreeConnection("a", "b", "normal"),
                new SkillTreeConnection("root2", "b", "normal"));
        return new SkillTreeCategory("cat", "Category", null, nodes, connections);
    }

    /** Diamond: root -> a -> c, root -> b -> c (two arms converge on c). */
    private static SkillTreeCategory diamondCategory() {
        List<SkillTreeNode> nodes = List.of(
                new SkillTreeNode("root", "cat", 0, 0, true, null, "Root", null),
                new SkillTreeNode("a", "cat", 1, 0, false, null, "A", null),
                new SkillTreeNode("b", "cat", 1, 1, false, null, "B", null),
                new SkillTreeNode("c", "cat", 2, 0, false, null, "C", null));
        List<SkillTreeConnection> connections = List.of(
                new SkillTreeConnection("root", "a", "normal"),
                new SkillTreeConnection("root", "b", "normal"),
                new SkillTreeConnection("a", "c", "normal"),
                new SkillTreeConnection("b", "c", "normal"));
        return new SkillTreeCategory("cat", "Category", null, nodes, connections);
    }

    // --- basic OK/removal ---

    @Test
    void leafRefundOkAndMovesPointsSpentToAvailable() {
        SkillTreeCategory category = chainCategory();
        SkillProgressAttachment progress = new SkillProgressAttachment();
        progress.grantPoints(5);
        progress.unlock("root", SkillUnlockValidator.NODE_COST);
        progress.unlock("mid", SkillUnlockValidator.NODE_COST);
        progress.unlock("leaf", SkillUnlockValidator.NODE_COST);

        int availableBefore = progress.availablePoints();
        int spentBefore = progress.spentPoints();

        SkillRefundValidator.Result result = SkillRefundValidator.tryRefund(category, "leaf", progress);

        assertEquals(SkillRefundValidator.Result.OK, result);
        assertFalse(progress.isUnlocked("leaf"));
        assertTrue(progress.isUnlocked("root"));
        assertTrue(progress.isUnlocked("mid"));
        assertEquals(availableBefore + SkillUnlockValidator.NODE_COST, progress.availablePoints());
        assertEquals(spentBefore - SkillUnlockValidator.NODE_COST, progress.spentPoints());
    }

    // --- mid-path orphaning ---

    @Test
    void midPathRefundWithUnlockedDescendantOrphansAndDoesNotMutate() {
        SkillTreeCategory category = chainCategory();
        SkillProgressAttachment progress = new SkillProgressAttachment();
        progress.grantPoints(5);
        progress.unlock("root", SkillUnlockValidator.NODE_COST);
        progress.unlock("mid", SkillUnlockValidator.NODE_COST);
        progress.unlock("leaf", SkillUnlockValidator.NODE_COST);

        Set<String> unlockedBefore = progress.unlockedNodeIds();
        int availableBefore = progress.availablePoints();
        int spentBefore = progress.spentPoints();

        SkillRefundValidator.Result result = SkillRefundValidator.tryRefund(category, "mid", progress);

        assertEquals(SkillRefundValidator.Result.WOULD_ORPHAN, result);
        assertEquals(unlockedBefore, progress.unlockedNodeIds());
        assertEquals(availableBefore, progress.availablePoints());
        assertEquals(spentBefore, progress.spentPoints());
    }

    // --- root refunds ---

    @Test
    void rootRefundWithUnlockedDependentOrphans() {
        SkillTreeCategory category = chainCategory();
        SkillProgressAttachment progress = new SkillProgressAttachment();
        progress.grantPoints(5);
        progress.unlock("root", SkillUnlockValidator.NODE_COST);
        progress.unlock("mid", SkillUnlockValidator.NODE_COST);

        assertEquals(SkillRefundValidator.Result.WOULD_ORPHAN,
                SkillRefundValidator.check(category, "root", progress.unlockedNodeIds()));
    }

    @Test
    void loneRootWithNoDependentsRefundsOk() {
        SkillTreeCategory category = chainCategory();
        assertEquals(SkillRefundValidator.Result.OK,
                SkillRefundValidator.check(category, "root", Set.of("root")));
    }

    // --- not-unlocked / unknown ---

    @Test
    void notCurrentlyUnlockedNodeRejectedWithoutMutation() {
        SkillTreeCategory category = chainCategory();
        SkillProgressAttachment progress = new SkillProgressAttachment();
        progress.grantPoints(5);
        progress.unlock("root", SkillUnlockValidator.NODE_COST);

        int availableBefore = progress.availablePoints();
        int spentBefore = progress.spentPoints();

        SkillRefundValidator.Result result = SkillRefundValidator.tryRefund(category, "mid", progress);

        assertEquals(SkillRefundValidator.Result.NOT_UNLOCKED, result);
        assertFalse(progress.isUnlocked("mid"));
        assertEquals(availableBefore, progress.availablePoints());
        assertEquals(spentBefore, progress.spentPoints());
    }

    @Test
    void unknownNodeIdRejectedWithoutMutation() {
        SkillTreeCategory category = chainCategory();
        SkillProgressAttachment progress = new SkillProgressAttachment();
        progress.grantPoints(5);
        progress.unlock("root", SkillUnlockValidator.NODE_COST);

        int availableBefore = progress.availablePoints();
        int spentBefore = progress.spentPoints();

        SkillRefundValidator.Result result = SkillRefundValidator.tryRefund(category, "does_not_exist", progress);

        assertEquals(SkillRefundValidator.Result.NODE_NOT_FOUND, result);
        assertEquals(availableBefore, progress.availablePoints());
        assertEquals(spentBefore, progress.spentPoints());
    }

    // --- multi-root / disconnected subgraph ---

    @Test
    void nodeStillReachableFromDifferentRootIsNotOrphaned() {
        SkillTreeCategory category = bridgedTwoRootCategory();
        // root1 -> a -> b <- root2, all unlocked. "b" was adjacent to "a",
        // but a naive check that only asks "was this node adjacent to the
        // refunded node?" would wrongly flag "b" as orphaned here - it's
        // still reachable through root2 directly.
        Set<String> unlocked = Set.of("root1", "a", "b", "root2");

        assertEquals(SkillRefundValidator.Result.OK,
                SkillRefundValidator.check(category, "a", unlocked));
    }

    @Test
    void bridgingNodeRefundOrphansSideWithNoOtherRoot() {
        SkillTreeCategory category = bridgedTwoRootCategory();
        // Same shape, but root2 is NOT unlocked this time, so "b" only has
        // "a" keeping it connected to a root.
        Set<String> unlocked = Set.of("root1", "a", "b");

        assertEquals(SkillRefundValidator.Result.WOULD_ORPHAN,
                SkillRefundValidator.check(category, "a", unlocked));
    }

    // --- diamond / cycle ---

    @Test
    void refundingOneArmOfADiamondDoesNotOrphanTheOtherArm() {
        SkillTreeCategory category = diamondCategory();
        // root -> a -> c and root -> b -> c. "c" was adjacent to "a", but
        // it's still reachable via "b" - a naive parent-pointer/tree
        // implementation that only remembers a single path per node would
        // wrongly orphan "c" here.
        Set<String> unlocked = Set.of("root", "a", "b", "c");

        assertEquals(SkillRefundValidator.Result.OK,
                SkillRefundValidator.check(category, "a", unlocked));
    }

    @Test
    void refundingBothArmsOfADiamondOrphansTheConvergedNode() {
        SkillTreeCategory category = diamondCategory();
        SkillProgressAttachment progress = new SkillProgressAttachment();
        progress.grantPoints(10);
        progress.unlock("root", SkillUnlockValidator.NODE_COST);
        progress.unlock("a", SkillUnlockValidator.NODE_COST);
        progress.unlock("b", SkillUnlockValidator.NODE_COST);
        progress.unlock("c", SkillUnlockValidator.NODE_COST);

        assertEquals(SkillRefundValidator.Result.OK, SkillRefundValidator.tryRefund(category, "a", progress));
        // Now only "b" keeps "c" connected; refunding "b" too must orphan "c".
        assertEquals(SkillRefundValidator.Result.WOULD_ORPHAN,
                SkillRefundValidator.check(category, "b", progress.unlockedNodeIds()));
    }

    // --- round trip ---

    @Test
    void refundThenReUnlockRestoresExactStartingState() {
        SkillTreeCategory category = chainCategory();
        SkillProgressAttachment progress = new SkillProgressAttachment();
        progress.grantPoints(5);
        progress.unlock("root", SkillUnlockValidator.NODE_COST);
        progress.unlock("mid", SkillUnlockValidator.NODE_COST);

        Set<String> unlockedBefore = progress.unlockedNodeIds();
        int availableBefore = progress.availablePoints();
        int spentBefore = progress.spentPoints();

        assertEquals(SkillRefundValidator.Result.OK, SkillRefundValidator.tryRefund(category, "mid", progress));
        assertEquals(SkillUnlockValidator.Result.OK, SkillUnlockValidator.tryUnlock(category, "mid", progress));

        assertEquals(unlockedBefore, progress.unlockedNodeIds());
        assertEquals(availableBefore, progress.availablePoints());
        assertEquals(spentBefore, progress.spentPoints());
    }
}
