package dev.vanillaplusplus.vppskills.unlock;

import dev.vanillaplusplus.vppskills.data.SkillProgressAttachment;
import dev.vanillaplusplus.vppskills.tree.SkillTreeCategory;
import dev.vanillaplusplus.vppskills.tree.SkillTreeConnection;
import dev.vanillaplusplus.vppskills.tree.SkillTreeNode;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.HashSet;
import java.util.Optional;
import java.util.Set;

/**
 * Pure, server-authoritative single-node refund validator - the mirror
 * image of {@link SkillUnlockValidator} for the "undo one unlock" direction
 * (per-node refund, as opposed to {@code SkillProgressAttachment#fullRespec}'s
 * "clear everything" respec).
 *
 * <p>{@link SkillUnlockValidator} only ever lets a node be unlocked if it is
 * a root, or adjacent to a node that is ALREADY unlocked. Applied
 * repeatedly, that rule establishes an invariant over the whole unlocked
 * set: every unlocked node is reachable from some unlocked root through a
 * path of other unlocked nodes (that's exactly how it got unlocked in the
 * first place - one hop at a time from something already reachable).
 *
 * <p>A naive single-node refund (just remove the node and refund its cost,
 * the way {@link SkillProgressAttachment#respec} does the bookkeeping in
 * isolation) can break that invariant: if the removed node was the only
 * link between an unlocked root and some other still-unlocked node further
 * out in the tree, that far node is left "orphaned" - unlocked in save data
 * with no legal path back to a root. Worse, it opens an exploit: a player
 * could refund a cheap trunk node while keeping an expensive branch beyond
 * it unlocked, then re-unlock the trunk for another {@link
 * SkillUnlockValidator#NODE_COST} - getting the branch's rewards twice for
 * one trunk node's worth of net spend.
 *
 * <p>This class closes that hole: {@link #check} simulates removing the
 * node from the unlocked set, then re-derives reachability from every
 * unlocked root using only connections between nodes that are STILL
 * unlocked after the removal (a breadth-first search from the roots, not a
 * naive "is a neighbor of the removed node still unlocked" check - that
 * shortcut gets both disconnected multi-root subgraphs and diamond/cycle
 * topologies wrong, see this class's test suite). If any unlocked node
 * (other than the one being removed) is left unreachable, the refund is
 * rejected as {@link Result#WOULD_ORPHAN} and nothing mutates.
 */
public final class SkillRefundValidator {

    public enum Result {
        OK,
        NODE_NOT_FOUND,
        NOT_UNLOCKED,
        WOULD_ORPHAN
    }

    private SkillRefundValidator() {
    }

    /** Read-only check - does not mutate {@code unlockedNodeIds}. */
    public static Result check(SkillTreeCategory category, String nodeId, Set<String> unlockedNodeIds) {
        Optional<SkillTreeNode> node = findNode(category, nodeId);
        if (node.isEmpty()) {
            return Result.NODE_NOT_FOUND;
        }
        if (!unlockedNodeIds.contains(nodeId)) {
            return Result.NOT_UNLOCKED;
        }

        Set<String> remaining = new HashSet<>(unlockedNodeIds);
        remaining.remove(nodeId);

        if (!allReachableFromRoots(category, remaining)) {
            return Result.WOULD_ORPHAN;
        }
        return Result.OK;
    }

    /**
     * Validates the request against {@code progress}'s current state and,
     * only if it passes, refunds {@link SkillUnlockValidator#NODE_COST}
     * points and removes {@code nodeId} from the unlocked set (via {@link
     * SkillProgressAttachment#respec}). Returns the same {@link Result}
     * {@link #check} would have, so a caller (e.g. the
     * {@code /vppskills refund} command) can tell the requesting player
     * exactly why a refund was rejected.
     */
    public static Result tryRefund(SkillTreeCategory category, String nodeId, SkillProgressAttachment progress) {
        Result result = check(category, nodeId, progress.unlockedNodeIds());
        if (result == Result.OK) {
            progress.respec(nodeId, SkillUnlockValidator.NODE_COST);
        }
        return result;
    }

    /**
     * Breadth-first search from every unlocked root, following only
     * connections whose both endpoints are in {@code unlockedNodeIds}.
     * Returns whether every id in {@code unlockedNodeIds} ended up visited.
     * Deliberately graph-general (handles disconnected multi-root subgraphs
     * and cycles/diamonds correctly) rather than a parent-pointer/tree
     * shortcut, since the underlying data is a general graph - see class doc.
     */
    private static boolean allReachableFromRoots(SkillTreeCategory category, Set<String> unlockedNodeIds) {
        if (unlockedNodeIds.isEmpty()) {
            return true;
        }

        Set<String> visited = new HashSet<>();
        Deque<String> frontier = new ArrayDeque<>();
        for (SkillTreeNode node : category.nodes()) {
            if (node.root() && unlockedNodeIds.contains(node.id()) && visited.add(node.id())) {
                frontier.add(node.id());
            }
        }

        while (!frontier.isEmpty()) {
            String current = frontier.poll();
            for (SkillTreeConnection connection : category.connections()) {
                String next = null;
                if (connection.fromId().equals(current)) {
                    next = connection.toId();
                } else if (connection.toId().equals(current)) {
                    next = connection.fromId();
                }
                if (next != null && unlockedNodeIds.contains(next) && visited.add(next)) {
                    frontier.add(next);
                }
            }
        }

        return visited.containsAll(unlockedNodeIds);
    }

    private static Optional<SkillTreeNode> findNode(SkillTreeCategory category, String nodeId) {
        return category.nodes().stream().filter(n -> n.id().equals(nodeId)).findFirst();
    }
}
