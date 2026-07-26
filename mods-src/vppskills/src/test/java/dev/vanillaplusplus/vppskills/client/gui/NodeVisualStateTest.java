package dev.vanillaplusplus.vppskills.client.gui;

import dev.vanillaplusplus.vppskills.data.SkillProgressAttachment;
import dev.vanillaplusplus.vppskills.tree.SkillTreeCategory;
import dev.vanillaplusplus.vppskills.tree.SkillTreeConnection;
import dev.vanillaplusplus.vppskills.tree.SkillTreeNode;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Unit tests for the pure {@link NodeVisualState#of} classification, per
 * #163 phase-3's hard test requirement (c) - covers the GUI's node-state
 * logic without needing a live {@code GuiGraphics}/{@code Screen}.
 *
 * <p>Same fixture shape as {@code unlock.SkillUnlockValidatorTest}'s chain
 * ({@code root -> mid -> leaf}, plus a disconnected {@code island}), since
 * {@link NodeVisualState#of} is deliberately a thin wrapper over
 * {@code unlock.SkillUnlockValidator#check}.
 */
class NodeVisualStateTest {

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

    private static SkillTreeNode nodeById(SkillTreeCategory category, String id) {
        return category.nodes().stream().filter(n -> n.id().equals(id)).findFirst().orElseThrow();
    }

    @Test
    void unlockedNodeIsAllocated() {
        SkillTreeCategory category = chainCategory();
        SkillProgressAttachment progress = new SkillProgressAttachment();
        progress.grantPoints(1);
        progress.unlock("root", 1);

        assertEquals(NodeVisualState.ALLOCATED, NodeVisualState.of(nodeById(category, "root"), category, progress));
    }

    @Test
    void rootWithSpareUnspentPointsIsAvailable() {
        SkillTreeCategory category = chainCategory();
        SkillProgressAttachment progress = new SkillProgressAttachment();
        progress.grantPoints(1);

        assertEquals(NodeVisualState.AVAILABLE, NodeVisualState.of(nodeById(category, "root"), category, progress));
    }

    @Test
    void rootWithNoPointsIsLocked() {
        SkillTreeCategory category = chainCategory();
        SkillProgressAttachment progress = new SkillProgressAttachment();

        assertEquals(NodeVisualState.LOCKED, NodeVisualState.of(nodeById(category, "root"), category, progress));
    }

    @Test
    void nonAdjacentNodeIsLockedEvenWithPlentyOfPoints() {
        SkillTreeCategory category = chainCategory();
        SkillProgressAttachment progress = new SkillProgressAttachment();
        progress.grantPoints(10);

        assertEquals(NodeVisualState.LOCKED, NodeVisualState.of(nodeById(category, "mid"), category, progress));
    }

    @Test
    void nodeAdjacentToUnlockedWithEnoughPointsIsAvailable() {
        SkillTreeCategory category = chainCategory();
        SkillProgressAttachment progress = new SkillProgressAttachment();
        progress.grantPoints(2);
        progress.unlock("root", 1);

        assertEquals(NodeVisualState.AVAILABLE, NodeVisualState.of(nodeById(category, "mid"), category, progress));
    }

    @Test
    void nodeAdjacentToUnlockedButOutOfPointsIsLocked() {
        SkillTreeCategory category = chainCategory();
        SkillProgressAttachment progress = new SkillProgressAttachment();
        progress.grantPoints(1);
        progress.unlock("root", 1);

        assertEquals(NodeVisualState.LOCKED, NodeVisualState.of(nodeById(category, "mid"), category, progress));
    }

    @Test
    void disconnectedIslandStaysLockedRegardlessOfPoints() {
        SkillTreeCategory category = chainCategory();
        SkillProgressAttachment progress = new SkillProgressAttachment();
        progress.grantPoints(10);
        progress.unlock("root", 1);
        progress.unlock("mid", 1);
        progress.unlock("leaf", 1);

        assertEquals(NodeVisualState.LOCKED, NodeVisualState.of(nodeById(category, "island"), category, progress));
    }
}
