package dev.vanillaplusplus.vppskills.unlock;

import dev.vanillaplusplus.vppskills.data.SkillProgressAttachment;
import dev.vanillaplusplus.vppskills.tree.SkillTreeCategory;
import dev.vanillaplusplus.vppskills.tree.SkillTreeConnection;
import dev.vanillaplusplus.vppskills.tree.SkillTreeNode;

import java.util.Optional;
import java.util.Set;

/**
 * Pure, server-authoritative node-unlock validator - the #163 phase-2 piece
 * that decides whether an unlock request is legal, independent of any
 * network/GUI plumbing (server-side only; the client never gets to decide
 * this, it only mirrors whatever the server ends up doing via
 * {@code SkillProgressSyncPayload}).
 *
 * <p>A request is accepted iff, in order:
 * <ol>
 *   <li>the node id exists in the given category;</li>
 *   <li>it is not already unlocked;</li>
 *   <li>it is either a root node, or adjacent (via any
 *       {@link SkillTreeConnection}, which this pack's data models as
 *       bidirectional - see that class's doc) to a node that IS already
 *       unlocked;</li>
 *   <li>the player has at least {@link #NODE_COST} available points.</li>
 * </ol>
 *
 * <p><b>Cost rule (deliberately simple):</b> every node costs a flat
 * {@link #NODE_COST} point, regardless of tier/definition. puffish_skills'
 * own {@code experience.json}/per-node cost rules are NOT ported by this
 * phase - #163's phase-2 scope explicitly excludes "XP-source
 * point-granting" and real cost design. This flat rule exists only so the
 * validator and {@link SkillProgressAttachment}'s debit/credit bookkeeping
 * have something concrete to unit-test against; a later phase replacing it
 * only needs to change {@link #NODE_COST} (or thread a real per-node cost
 * lookup through {@link #check}) without touching the adjacency/ordering
 * logic below.
 */
public final class SkillUnlockValidator {

    /** See class doc "Cost rule" - flat, placeholder, real economy is a later phase. */
    public static final int NODE_COST = 1;

    public enum Result {
        OK,
        NODE_NOT_FOUND,
        ALREADY_UNLOCKED,
        NOT_ADJACENT,
        INSUFFICIENT_POINTS
    }

    private SkillUnlockValidator() {
    }

    /** Read-only check - does not mutate {@code unlockedNodeIds}/points. */
    public static Result check(SkillTreeCategory category, String nodeId, Set<String> unlockedNodeIds, int availablePoints) {
        Optional<SkillTreeNode> node = findNode(category, nodeId);
        if (node.isEmpty()) {
            return Result.NODE_NOT_FOUND;
        }
        if (unlockedNodeIds.contains(nodeId)) {
            return Result.ALREADY_UNLOCKED;
        }
        if (!node.get().root() && !isAdjacentToUnlocked(category, nodeId, unlockedNodeIds)) {
            return Result.NOT_ADJACENT;
        }
        if (availablePoints < NODE_COST) {
            return Result.INSUFFICIENT_POINTS;
        }
        return Result.OK;
    }

    /**
     * Validates the request against {@code progress}'s current state and,
     * only if it passes, debits {@link #NODE_COST} points and adds
     * {@code nodeId} to the unlocked set (via
     * {@link SkillProgressAttachment#unlock}). Returns the same
     * {@link Result} {@link #check} would have, so a caller (a future
     * server-side packet handler - not wired in this phase, see #163's
     * scope note on click-to-unlock) can tell the requesting client exactly
     * why an unlock was rejected.
     */
    public static Result tryUnlock(SkillTreeCategory category, String nodeId, SkillProgressAttachment progress) {
        Result result = check(category, nodeId, progress.unlockedNodeIds(), progress.availablePoints());
        if (result == Result.OK) {
            progress.unlock(nodeId, NODE_COST);
        }
        return result;
    }

    private static Optional<SkillTreeNode> findNode(SkillTreeCategory category, String nodeId) {
        return category.nodes().stream().filter(n -> n.id().equals(nodeId)).findFirst();
    }

    private static boolean isAdjacentToUnlocked(SkillTreeCategory category, String nodeId, Set<String> unlockedNodeIds) {
        for (SkillTreeConnection connection : category.connections()) {
            if (connection.fromId().equals(nodeId) && unlockedNodeIds.contains(connection.toId())) {
                return true;
            }
            if (connection.toId().equals(nodeId) && unlockedNodeIds.contains(connection.fromId())) {
                return true;
            }
        }
        return false;
    }
}
