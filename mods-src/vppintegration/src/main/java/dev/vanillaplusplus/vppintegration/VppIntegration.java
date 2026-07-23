package dev.vanillaplusplus.vppintegration;

import dev.vanillaplusplus.vppintegration.network.PackVersionGate;
import dev.vanillaplusplus.vppintegration.quality.OvergearedSilentGearBridge;
import dev.vanillaplusplus.vppintegration.quality.QualityBridgeConfig;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.config.ModConfig;
import net.neoforged.neoforge.common.NeoForge;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Vanilla++ Overgeared &lt;-&gt; Silent Gear quality bridge (GitHub issue #67).
 *
 * <p>Why this mod exists: Overgeared's per-item "ForgingQuality" (poor..master) is
 * pure data ({@code net.stirdrem.overgeared.ForgingQuality}, stored as a generic
 * {@code DataComponentType} any item stack can carry) and its stat-bonus layer
 * ({@code QualityAttributeHandler}) already applies transparently to any item's
 * vanilla attribute modifiers via {@code ItemAttributeModifierEvent} at LOWEST
 * priority. What Overgeared has NO way to do on its own is (a) forge a Silent Gear
 * tool/weapon/armor PART with the correct material assignment - its own forging
 * recipes are static, one-recipe-per-material JSON with a fixed result item id, and
 * Silent Gear's material assignment is a data component
 * ({@code SgDataComponents.MATERIAL_LIST}) that only Silent Gear's own recipe/stat
 * code populates and interprets correctly - and (b) feed the quality grade into
 * Silent Gear's own non-vanilla-attribute stat properties (durability, harvest
 * speed), which live in Silent Gear's own property/event system, not the vanilla
 * attribute system Overgeared's handler touches.
 *
 * <p>This mod closes both gaps with real Java code against each mod's public/
 * semi-public API surface, not by hand-authoring a guess at Silent Gear's private
 * codec in JSON:
 * <ul>
 *   <li>{@link dev.vanillaplusplus.vppintegration.mixin.AbstractSmithingAnvilBlockEntityMixin}
 *   hooks {@code AbstractSmithingAnvilBlockEntity.craftItem()} (confirmed via a
 *   real build/javap: it's a no-arg method on the block entity itself, not a
 *   separate {@code ForgingQualityHelper} class as an earlier draft of this doc
 *   assumed - {@code applyForgingQuality(ItemStack, ForgingQuality)} is a public
 *   static method on {@code AbstractSmithingAnvilBlockEntity}). When the item
 *   just placed in the anvil's output is a Silent Gear {@code GearItem} whose
 *   part list still holds the placeholder material this mod's forging recipes
 *   ship (see below), the mixin rebuilds the item's real material assignment
 *   from whichever ingot the player actually forged with, using Silent Gear's
 *   own {@code SgDataComponents.MATERIAL_LIST} component and
 *   {@code GearData.recalculateGearData} to recompute stats the same way Silent
 *   Gear's own recipes do.</li>
 *   <li>{@code data/overgeared/recipe/forging/*.json} (one per Silent Gear part
 *   type x this pack's material tier) gives the Overgeared anvil a forging recipe
 *   for every Silent Gear part, with a placeholder result the mixin above
 *   corrects at craft time - Overgeared's own static, single-item-result recipe
 *   format cannot express "whichever material tier was actually forged", so the
 *   correction has to happen in Java regardless of the JSON shape.</li>
 *   <li>{@link OvergearedSilentGearBridge} listens on Silent Gear's own public
 *   {@code GearRecalculateEvent.Post} - fired right after Silent Gear finishes
 *   writing an item's computed stats into its {@code GEAR_PROPERTIES} data
 *   component (confirmed via javap-read bytecode ordering in {@code GearData}) -
 *   to (a) rewrite that data component, adding a quality-derived bonus to Silent
 *   Gear's DURABILITY/HARVEST_SPEED properties (reusing Overgeared's own
 *   per-quality config bonus values for symmetry with its native items; an
 *   earlier draft of this bridge instead hooked {@code
 *   GetPropertyModifiersEvent}, but a real build proved that event's modifiers
 *   list is immutable for NumberProperty-backed properties - see that class's
 *   doc for the full javap evidence), and (b) stamp a fixed default quality onto
 *   any Silent Gear item that reaches a finished state without ever touching the
 *   Overgeared anvil (pattern-crafted parts, non-metal/non-forged
 *   assemblies) - so the attribute-bonus layer above is meaningful for every
 *   Silent Gear item this pack can produce, not only forged ones. Combat stats
 *   (attack damage, armor, attack speed) need NO code here at all: Silent Gear
 *   already writes its computed values into the item's vanilla
 *   {@code ItemAttributeModifiers} component, so Overgeared's own
 *   {@code QualityAttributeHandler} (LOWEST-priority
 *   {@code ItemAttributeModifierEvent} listener, already shipped in the jar,
 *   nothing added here) layers the quality bonus on top for free, exactly the
 *   mechanism the #67 investigation identified as "genuinely pure data".</li>
 * </ul>
 *
 * <p>See this mod's README.md for the full design writeup, confidence levels per
 * hook, and exactly what a real build + in-game session must verify.
 *
 * <p>This mod also carries an unrelated second feature, {@link PackVersionGate}
 * (GitHub issue #94's "before the crash" follow-up): a connection-time
 * client/server pack-version check that runs during NeoForge's CONFIGURATION
 * protocol phase, strictly before a mismatched client ever reaches the PLAY
 * phase/world. See that class's doc for the full feasibility writeup and
 * exactly which mismatch class it can and cannot cover.
 */
@Mod(VppIntegration.MODID)
public final class VppIntegration {
    public static final String MODID = "vppintegration";
    public static final Logger LOGGER = LoggerFactory.getLogger(MODID);

    public VppIntegration(IEventBus modEventBus, ModContainer modContainer) {
        modContainer.registerConfig(ModConfig.Type.SERVER, QualityBridgeConfig.SPEC);
        NeoForge.EVENT_BUS.register(new OvergearedSilentGearBridge());
        modEventBus.addListener(PackVersionGate::registerPayloads);
        modEventBus.addListener(PackVersionGate::registerConfigurationTask);
        LOGGER.info("vppintegration loaded: Overgeared quality <-> Silent Gear stats bridge active");
    }
}
