package dev.vanillaplusplus.vppskills.tree;

import java.util.List;

/**
 * One puffish_skills category (ported from {@code category.json}), plus the
 * nodes/connections it owns. As of this writing the pack has collapsed to a
 * single unified category ({@code adventurer} - see {@code skills.js}'s
 * {@code SKILLS_UNIFIED_CATEGORY_ID}, GitHub #116), but the loader and this
 * model stay multi-category so a future pack change (or a second tree) needs
 * no rework here.
 */
public record SkillTreeCategory(
        String id,
        String title,
        String iconItem,
        List<SkillTreeNode> nodes,
        List<SkillTreeConnection> connections) {
}
