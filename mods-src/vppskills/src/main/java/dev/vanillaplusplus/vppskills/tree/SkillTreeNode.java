package dev.vanillaplusplus.vppskills.tree;

import dev.vanillaplusplus.vppskills.reward.AttributeRewardData;

import java.util.List;

/**
 * One node of a skill tree, ported 1:1 from a puffish_skills
 * {@code categories/<id>/skills.json} entry (see
 * {@link SkillTreeLoader#parseCategory}): an id, a position in the
 * category's own coordinate space, whether it's the tree's root, and the
 * id of its {@code definitions.json} entry (title/icon/rewards).
 *
 * <p>Phase 1/2 only carried {@link #title()}/{@link #iconItem()} forward
 * from that definition. #163 phase 3 adds {@link #rewards()} (this node's
 * {@code puffish_skills:attribute} reward list, parsed by
 * {@link SkillTreeLoader#extractRewards} from the same definition) so the
 * GUI's hover tooltip can show a reward summary - see
 * {@code client.gui.SkillTreeScreen}. Still modeled as
 * {@code reward.AttributeRewardData} rather than a bespoke type, per that
 * class's doc ("the seam a later phase's loader extension plugs into").
 */
public record SkillTreeNode(
        String id,
        String categoryId,
        double x,
        double y,
        boolean root,
        String definitionId,
        String title,
        String iconItem,
        List<AttributeRewardData> rewards) {

    /**
     * Back-compat constructor for callers built before phase 3 added
     * {@link #rewards()} (existing test fixtures in particular) - defaults
     * to no rewards.
     */
    public SkillTreeNode(String id, String categoryId, double x, double y, boolean root,
                          String definitionId, String title, String iconItem) {
        this(id, categoryId, x, y, root, definitionId, title, iconItem, List.of());
    }
}
