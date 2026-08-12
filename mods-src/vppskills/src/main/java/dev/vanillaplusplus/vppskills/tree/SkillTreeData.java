package dev.vanillaplusplus.vppskills.tree;

import java.util.List;
import java.util.Map;

/**
 * The full ported tree: every {@link SkillTreeCategory} keyed by id, in
 * load order. Immutable once built by {@link SkillTreeLoader} -
 * phase 1 has no live reload/edit path (that's a later-phase concern; see
 * this mod's README "What this phase does NOT include yet").
 */
public record SkillTreeData(Map<String, SkillTreeCategory> categories) {

    public static final SkillTreeData EMPTY = new SkillTreeData(Map.of());

    public List<SkillTreeCategory> categoriesSorted() {
        return categories.values().stream()
                .sorted((a, b) -> a.id().compareTo(b.id()))
                .toList();
    }
}
