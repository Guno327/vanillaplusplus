package dev.vanillaplusplus.vppskills.reward;

/**
 * One {@code puffish_skills:attribute} reward entry as it appears in a
 * ported {@code definitions.json} node (see that file's
 * {@code rewards[].data} shape - {@code {"attribute": "...", "value": ...,
 * "operation": "..."}}). Kept as its own tiny record, independent of
 * {@link dev.vanillaplusplus.vppskills.tree.SkillTreeNode}, since phase 1's
 * loader deliberately does not carry rewards forward yet (see that class's
 * doc - "rewards are a later-phase concern"); this record is the seam a
 * later phase's loader extension plugs into without this translator needing
 * to change.
 *
 * @param attributeId the puffish/vanilla attribute id string exactly as it
 *                     appears in JSON, e.g. {@code "generic.max_health"}
 *                     (implicitly {@code minecraft} namespace - see
 *                     {@link AttributeOperationTranslator#resolveAttributeId})
 *                     or {@code "puffish_attributes:sword_damage"}
 *                     (explicitly namespaced).
 * @param value        the raw reward magnitude, copied verbatim into the
 *                     resulting {@code AttributeModifier}'s amount.
 * @param operation    puffish_skills' operation vocabulary string -
 *                     {@code "addition"}, {@code "multiply_base"}, or
 *                     {@code "multiply_total"} (see
 *                     {@link AttributeOperationTranslator#toNeoForgeOperation}).
 */
public record AttributeRewardData(String attributeId, double value, String operation) {
}
