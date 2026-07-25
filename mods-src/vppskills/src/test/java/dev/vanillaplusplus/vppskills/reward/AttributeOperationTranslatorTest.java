package dev.vanillaplusplus.vppskills.reward;

import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

/**
 * Unit tests for {@link AttributeOperationTranslator}: each puffish_skills
 * operation string maps to the expected real {@code AttributeModifier.Operation}
 * (ground-truthed via {@code javap} - see that class's doc) with the value
 * copied through unchanged, per #163 phase-2's hard test requirement (b).
 */
class AttributeOperationTranslatorTest {

    @Test
    void additionMapsToAddValue() {
        assertEquals(AttributeModifier.Operation.ADD_VALUE,
                AttributeOperationTranslator.toNeoForgeOperation("addition"));
    }

    @Test
    void multiplyBaseMapsToAddMultipliedBase() {
        assertEquals(AttributeModifier.Operation.ADD_MULTIPLIED_BASE,
                AttributeOperationTranslator.toNeoForgeOperation("multiply_base"));
    }

    @Test
    void multiplyTotalMapsToAddMultipliedTotal() {
        assertEquals(AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL,
                AttributeOperationTranslator.toNeoForgeOperation("multiply_total"));
    }

    @Test
    void unknownOperationThrowsRatherThanGuessing() {
        assertThrows(IllegalArgumentException.class,
                () -> AttributeOperationTranslator.toNeoForgeOperation("set_value_percent"));
    }

    @Test
    void unnamespacedAttributeIdDefaultsToMinecraft() {
        ResourceLocation resolved = AttributeOperationTranslator.resolveAttributeId("generic.max_health");
        assertEquals(ResourceLocation.fromNamespaceAndPath("minecraft", "generic.max_health"), resolved);
    }

    @Test
    void namespacedAttributeIdIsPreserved() {
        ResourceLocation resolved = AttributeOperationTranslator.resolveAttributeId("puffish_attributes:sword_damage");
        assertEquals(ResourceLocation.fromNamespaceAndPath("puffish_attributes", "sword_damage"), resolved);
    }

    @Test
    void translateProducesOneSpecPerRewardWithMatchingValueAndOperation() {
        List<AttributeRewardData> rewards = List.of(
                new AttributeRewardData("generic.max_health", 0.006, "multiply_total"),
                new AttributeRewardData("generic.attack_damage", 0.007, "multiply_base"),
                new AttributeRewardData("puffish_attributes:sword_damage", 0.007, "multiply_base"));

        List<AttributeModifierSpec> specs = AttributeOperationTranslator.translate("warrior_swords_t0_1", rewards);

        assertEquals(3, specs.size());

        assertEquals(ResourceLocation.fromNamespaceAndPath("minecraft", "generic.max_health"), specs.get(0).attributeId());
        assertEquals(0.006, specs.get(0).modifier().amount());
        assertEquals(AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL, specs.get(0).modifier().operation());

        assertEquals(ResourceLocation.fromNamespaceAndPath("minecraft", "generic.attack_damage"), specs.get(1).attributeId());
        assertEquals(0.007, specs.get(1).modifier().amount());
        assertEquals(AttributeModifier.Operation.ADD_MULTIPLIED_BASE, specs.get(1).modifier().operation());

        assertEquals(ResourceLocation.fromNamespaceAndPath("puffish_attributes", "sword_damage"), specs.get(2).attributeId());
        assertEquals(0.007, specs.get(2).modifier().amount());
        assertEquals(AttributeModifier.Operation.ADD_MULTIPLIED_BASE, specs.get(2).modifier().operation());
    }

    @Test
    void translateProducesDeterministicDistinctModifierIdsForRespec() {
        List<AttributeRewardData> rewards = List.of(
                new AttributeRewardData("generic.max_health", 1.0, "addition"),
                new AttributeRewardData("generic.armor", 1.0, "addition"));

        List<AttributeModifierSpec> first = AttributeOperationTranslator.translate("node_a", rewards);
        List<AttributeModifierSpec> second = AttributeOperationTranslator.translate("node_a", rewards);

        // Same node + same reward list -> identical modifier ids every time (needed so a later
        // respec can removeModifier(id) and actually find what apply() added).
        assertEquals(first.get(0).modifier().id(), second.get(0).modifier().id());
        assertEquals(first.get(1).modifier().id(), second.get(1).modifier().id());
        // Distinct rewards on the same node never collide with each other.
        assertNotEquals(first.get(0).modifier().id(), first.get(1).modifier().id());
    }
}
