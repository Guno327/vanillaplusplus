package dev.vanillaplusplus.vppskills.reward;

import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;

/**
 * A fully-built, real NeoForge {@link AttributeModifier} paired with the id
 * of the vanilla/modded attribute it targets - the output of
 * {@link AttributeOperationTranslator#translate}.
 *
 * <p>Deliberately does NOT hold a resolved {@code Holder<Attribute>}:
 * resolving {@link #attributeId} to a live attribute requires the running
 * game's {@code BuiltInRegistries.ATTRIBUTE} registry (ground-truthed via
 * {@code javap} - see {@link AttributeOperationTranslator}'s class doc),
 * which isn't available in a unit test's plain JVM. Keeping that resolution
 * out of this record is what makes {@link AttributeOperationTranslator}
 * itself pure and unit-testable without booting the game; the live-registry
 * lookup lives in {@link SkillAttributeApplier} instead, which IS only
 * reachable from a running client/server and is intentionally not
 * unit-tested here.
 */
public record AttributeModifierSpec(ResourceLocation attributeId, AttributeModifier modifier) {
}
