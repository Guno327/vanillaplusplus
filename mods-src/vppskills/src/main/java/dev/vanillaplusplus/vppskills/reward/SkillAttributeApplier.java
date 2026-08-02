package dev.vanillaplusplus.vppskills.reward;

import dev.vanillaplusplus.vppskills.VppSkills;
import dev.vanillaplusplus.vppskills.server.ServerSkillTreeState;
import dev.vanillaplusplus.vppskills.tree.SkillTreeCategory;
import dev.vanillaplusplus.vppskills.tree.SkillTreeNode;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.Attribute;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;

import java.util.Collection;
import java.util.List;

/**
 * The live-game half of {@link AttributeOperationTranslator}: takes the pure
 * {@link AttributeModifierSpec}s it produces and actually applies/removes
 * them on a real {@link LivingEntity}. Split out of the translator
 * deliberately (see {@link AttributeModifierSpec}'s doc) - resolving an
 * attribute id string to a live {@code Holder<Attribute>} needs
 * {@link BuiltInRegistries#ATTRIBUTE}, which only exists in a booted game,
 * so this class is NOT unit-tested here (there is nothing pure left to
 * assert once a real registry/entity is involved) - {@link
 * AttributeOperationTranslator}'s unit tests already cover the actual
 * op-mapping logic this class relies on.
 *
 * <p>{@code Registry<Attribute>.getHolder(ResourceLocation)} returning
 * {@code Optional<Holder.Reference<Attribute>>} (a {@code Holder<Attribute>}
 * subtype) was ground-truthed via {@code javap} against the resolved
 * NeoForge jar, same as {@link AttributeOperationTranslator}'s own
 * ground-truthing - see that class's doc.
 *
 * <p><b>Not wired to anything yet.</b> Per #163 phase-2 scope, node-click
 * -&gt; unlock -&gt; reward application is NOT connected end-to-end this
 * phase; a future phase's server-side unlock packet handler calls
 * {@link #apply} after {@link dev.vanillaplusplus.vppskills.unlock.SkillUnlockValidator#tryUnlock}
 * succeeds, and a future respec command calls {@link #clear}.
 */
public final class SkillAttributeApplier {

    private SkillAttributeApplier() {
    }

    /** Applies every spec as a permanent modifier on {@code entity}. Unresolvable attribute ids are logged and skipped. */
    public static void apply(LivingEntity entity, List<AttributeModifierSpec> specs) {
        for (AttributeModifierSpec spec : specs) {
            AttributeInstance instance = resolveInstance(entity, spec);
            if (instance != null) {
                instance.addOrReplacePermanentModifier(spec.modifier());
            }
        }
    }

    /** Reverses {@link #apply} - the respec path. Removing a modifier id that isn't present is a harmless no-op. */
    public static void clear(LivingEntity entity, List<AttributeModifierSpec> specs) {
        for (AttributeModifierSpec spec : specs) {
            AttributeInstance instance = resolveInstance(entity, spec);
            if (instance != null) {
                instance.removeModifier(spec.modifier().id());
            }
        }
    }

    /**
     * The full-respec counterpart to {@link #clear}: for every node id in
     * {@code nodeIds}, looks it up in {@code data.ServerSkillTreeState}
     * (mirrors how {@code server.ServerSkillEvents#applyNodeRewards} already
     * finds a node's reward list to APPLY), re-derives the same deterministic
     * {@code vppskills:node/<nodeId>/<index>} modifier specs via
     * {@link AttributeOperationTranslator#translate} (see that method's doc
     * on why those ids are stable/reproducible), and removes them. Node ids
     * that aren't found in the current tree (e.g. stale save data from a
     * removed node) or have no reward list are silently skipped - nothing to
     * clear.
     */
    public static void clearAll(LivingEntity entity, Collection<String> nodeIds) {
        if (nodeIds.isEmpty()) {
            return;
        }
        for (SkillTreeCategory category : ServerSkillTreeState.get().categories().values()) {
            for (SkillTreeNode node : category.nodes()) {
                if (nodeIds.contains(node.id()) && !node.rewards().isEmpty()) {
                    clear(entity, AttributeOperationTranslator.translate(node.id(), node.rewards()));
                }
            }
        }
    }

    private static AttributeInstance resolveInstance(LivingEntity entity, AttributeModifierSpec spec) {
        Holder<Attribute> holder = BuiltInRegistries.ATTRIBUTE.getHolder(spec.attributeId()).orElse(null);
        if (holder == null) {
            VppSkills.LOGGER.warn("vppskills: unknown attribute id {} in a node reward - skipping", spec.attributeId());
            return null;
        }
        return entity.getAttribute(holder);
    }
}
