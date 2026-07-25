package dev.vanillaplusplus.vppskills.tree;

/**
 * One node of a skill tree, ported 1:1 from a puffish_skills
 * {@code categories/<id>/skills.json} entry (see
 * {@link SkillTreeLoader#parseCategory}): an id, a position in the
 * category's own coordinate space, whether it's the tree's root, and the
 * id of its {@code definitions.json} entry (title/icon/rewards - phase 1
 * only carries {@link #title()}/{@link #iconItem()} forward; rewards are a
 * later-phase concern per GitHub #163's scope).
 */
public record SkillTreeNode(
        String id,
        String categoryId,
        double x,
        double y,
        boolean root,
        String definitionId,
        String title,
        String iconItem) {
}
