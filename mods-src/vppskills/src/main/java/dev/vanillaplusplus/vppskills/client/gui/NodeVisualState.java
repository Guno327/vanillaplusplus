package dev.vanillaplusplus.vppskills.client.gui;

import dev.vanillaplusplus.vppskills.data.SkillProgressAttachment;
import dev.vanillaplusplus.vppskills.tree.SkillTreeCategory;
import dev.vanillaplusplus.vppskills.tree.SkillTreeNode;
import dev.vanillaplusplus.vppskills.unlock.SkillUnlockValidator;

/**
 * Pure, client-side-only "how should this node be drawn/clickable right
 * now" classification - the #163 phase-3 piece that lets
 * {@link SkillTreeScreen} render three distinct node states without burying
 * the logic in {@code render}'s loop body (so it's unit-testable without a
 * live {@code GuiGraphics}, per the phase-3 brief's hard test requirement).
 *
 * <p>Deliberately reuses {@link SkillUnlockValidator#check} (the exact same
 * server-authoritative decision the server will make for a real unlock
 * request) rather than re-deriving adjacency/affordability rules here - this
 * class only ever mirrors what the server would say "yes" to, it never
 * invents a looser or stricter client-side notion of "available". The
 * client's copy of {@link SkillProgressAttachment} it reads
 * ({@code client.ClientSkillTreeState#progress()}) is only ever a
 * last-synced mirror, so this classification can be briefly stale until the
 * next {@code SkillProgressSyncPayload} arrives - acceptable here since a
 * click still round-trips through the real server check either way (see
 * {@code server.ServerSkillEvents#handleUnlockRequest}).
 */
public enum NodeVisualState {
    /** Already unlocked - {@link SkillProgressAttachment#isUnlocked}. */
    ALLOCATED,
    /** Not yet unlocked, but a server-side unlock request for it would currently succeed. */
    AVAILABLE,
    /** Not yet unlocked, and not currently unlockable (not adjacent to an unlocked node/root, or unaffordable). */
    LOCKED;

    public static NodeVisualState of(SkillTreeNode node, SkillTreeCategory category, SkillProgressAttachment progress) {
        if (progress.isUnlocked(node.id())) {
            return ALLOCATED;
        }
        SkillUnlockValidator.Result check = SkillUnlockValidator.check(
                category, node.id(), progress.unlockedNodeIds(), progress.availablePoints());
        return check == SkillUnlockValidator.Result.OK ? AVAILABLE : LOCKED;
    }
}
