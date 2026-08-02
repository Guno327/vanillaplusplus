package dev.vanillaplusplus.vppskills.tree;

/**
 * One edge between two {@link SkillTreeNode}s, ported from a puffish_skills
 * {@code categories/<id>/connections.json} entry. puffish_skills' schema
 * groups edges under a {@code group} ({@code "normal"} - ordinary
 * prerequisite links - or {@code "exclusive"} - pick-one-of-many branch
 * points) each holding only {@code bidirectional} pairs in this pack's data
 * (no {@code unidirectional} arrays are present today, so this phase's
 * loader doesn't model that shape - see
 * {@link SkillTreeLoader#parseCategory}).
 */
public record SkillTreeConnection(String fromId, String toId, String group) {
}
