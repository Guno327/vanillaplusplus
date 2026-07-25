package dev.vanillaplusplus.vppskills.reward;

import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;

import java.util.ArrayList;
import java.util.List;

/**
 * Pure translator from puffish_skills' {@code puffish_skills:attribute}
 * reward operation vocabulary (as seen in the ported {@code
 * definitions.json} - see {@link AttributeRewardData}) to NeoForge/vanilla's
 * real {@link AttributeModifier.Operation} enum, per #163 phase-2 scope
 * item 3.
 *
 * <p><b>Ground-truthing.</b> {@code AttributeModifier}/{@code
 * AttributeModifier.Operation} were decompiled/{@code javap}'d against the
 * resolved {@code neoforge-21.1.235-merged.jar} (same jar this pack's other
 * mods build against) rather than assumed from training-data memory. Two
 * facts that check confirmed and this class depends on:
 * <ul>
 *   <li>{@code AttributeModifier.Operation} has exactly three constants:
 *       {@code ADD_VALUE}, {@code ADD_MULTIPLIED_BASE},
 *       {@code ADD_MULTIPLIED_TOTAL} (in that declared order) - there is no
 *       {@code MULTIPLY}/{@code SET} or similar.</li>
 *   <li>{@code AttributeModifier}'s constructor is
 *       {@code (ResourceLocation id, double amount, Operation operation)} -
 *       it does NOT need a resolved {@code Holder<Attribute>} at
 *       construction time, only when later attached to a real
 *       {@code AttributeInstance} (see {@link AttributeModifierSpec}'s doc
 *       for why that split is exactly what keeps this class unit-testable
 *       without booting the game).</li>
 * </ul>
 *
 * <p><b>Operation mapping</b> (all three of puffish_skills' operations found
 * in this pack's real {@code definitions.json} map cleanly - none needed to
 * be "faked"):
 * <ul>
 *   <li>{@code "addition"} -&gt; {@code ADD_VALUE} (flat add to the
 *       attribute's base+modified value).</li>
 *   <li>{@code "multiply_base"} -&gt; {@code ADD_MULTIPLIED_BASE} (percentage
 *       of the attribute's BASE value only - vanilla's "additive-percentage
 *       of base" tier).</li>
 *   <li>{@code "multiply_total"} -&gt; {@code ADD_MULTIPLIED_TOTAL}
 *       (percentage of the running total after all
 *       {@code ADD_MULTIPLIED_BASE}/{@code ADD_VALUE} modifiers - vanilla's
 *       final multiplicative tier).</li>
 * </ul>
 * Any other operation string is NOT silently mapped to the closest-looking
 * constant - {@link #toNeoForgeOperation} throws {@link IllegalArgumentException}
 * so an unrecognized op fails loudly instead of applying the wrong math.
 */
public final class AttributeOperationTranslator {

    private AttributeOperationTranslator() {
    }

    /**
     * @throws IllegalArgumentException if {@code puffishOperation} isn't one
     *                                   of the three ops documented on this
     *                                   class - there is no vanilla
     *                                   equivalent to "fake" for anything
     *                                   else, so this fails loudly rather
     *                                   than guessing.
     */
    public static AttributeModifier.Operation toNeoForgeOperation(String puffishOperation) {
        return switch (puffishOperation) {
            case "addition" -> AttributeModifier.Operation.ADD_VALUE;
            case "multiply_base" -> AttributeModifier.Operation.ADD_MULTIPLIED_BASE;
            case "multiply_total" -> AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL;
            default -> throw new IllegalArgumentException(
                    "vppskills: no NeoForge AttributeModifier.Operation equivalent for puffish_skills operation \""
                            + puffishOperation + "\" - known ops are addition/multiply_base/multiply_total");
        };
    }

    /**
     * {@code "generic.max_health"} (no namespace in puffish's JSON - implicit
     * vanilla) or {@code "puffish_attributes:sword_damage"} (explicit,
     * modded) -&gt; a real {@link ResourceLocation}, via
     * {@code ResourceLocation.parse} (ground-truthed via {@code javap}'s
     * decompiled bytecode against the resolved jar - see this class's doc).
     * {@code parse} delegates to {@code bySeparator(str, ':')}, which splits
     * on the first {@code ':'} and defaults the namespace to
     * {@code minecraft} only when none is present - precisely puffish's own
     * two attribute-id shapes.
     *
     * <p><b>Ground-truthing correction:</b> {@code ResourceLocation.withDefaultNamespace}
     * was tried first since its name reads like exactly this method's
     * contract, but decompiling it showed it unconditionally hardcodes the
     * {@code minecraft} namespace and treats its ENTIRE argument as the path
     * - it does not split on {@code ':'} at all, so it threw
     * {@code ResourceLocationException} on {@code "puffish_attributes:sword_damage"}
     * (caught by this class's own unit tests, not assumed away).
     * {@code parse}/{@code bySeparator} is the one that actually implements
     * "namespace if present, else default to minecraft".
     */
    public static ResourceLocation resolveAttributeId(String rawAttributeId) {
        return ResourceLocation.parse(rawAttributeId);
    }

    /**
     * Produces one concrete {@link AttributeModifierSpec} per reward,
     * deterministically id'd as {@code vppskills:node/<nodeId>/<index>} so
     * the same node+reward-list always produces the same modifier id
     * (required for {@link net.minecraft.world.entity.ai.attributes.AttributeInstance#removeModifier(ResourceLocation)}
     * to find and remove it again later - the respec/"clear" path; see
     * {@link SkillAttributeApplier#clear}).
     *
     * @param nodeId  the owning node's id (used only to build a stable,
     *                unique modifier id - see above).
     * @param rewards this node's attribute rewards, in the order they should
     *                be applied (order doesn't affect the produced specs
     *                themselves, only matters once actually applied to an
     *                {@code AttributeInstance}, which sums same-operation
     *                modifiers order-independently anyway).
     */
    public static List<AttributeModifierSpec> translate(String nodeId, List<AttributeRewardData> rewards) {
        List<AttributeModifierSpec> specs = new ArrayList<>(rewards.size());
        for (int i = 0; i < rewards.size(); i++) {
            AttributeRewardData reward = rewards.get(i);
            ResourceLocation modifierId = ResourceLocation.fromNamespaceAndPath(
                    "vppskills", "node/" + nodeId + "/" + i);
            AttributeModifier.Operation operation = toNeoForgeOperation(reward.operation());
            AttributeModifier modifier = new AttributeModifier(modifierId, reward.value(), operation);
            specs.add(new AttributeModifierSpec(resolveAttributeId(reward.attributeId()), modifier));
        }
        return specs;
    }
}
