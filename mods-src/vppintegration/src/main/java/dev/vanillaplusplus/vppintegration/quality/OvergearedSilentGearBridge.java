package dev.vanillaplusplus.vppintegration.quality;

import net.minecraft.world.item.ItemStack;
import net.neoforged.bus.api.SubscribeEvent;
import net.silentchaos512.gear.api.event.GearRecalculateEvent;
import net.silentchaos512.gear.api.event.GetPropertyModifiersEvent;
import net.silentchaos512.gear.api.item.GearItem;
import net.silentchaos512.gear.api.property.NumberProperty;
import net.silentchaos512.gear.api.property.NumberPropertyValue;
import net.silentchaos512.gear.setup.gear.GearProperties;
import net.stirdrem.overgeared.ForgingQuality;
import net.stirdrem.overgeared.components.ModComponents;
import net.stirdrem.overgeared.config.ServerConfig;

/**
 * The two Silent-Gear-side hooks of the quality bridge.
 *
 * <p>Combat attributes (attack damage, armor, attack speed, etc.) need NOTHING
 * here: Silent Gear writes its computed values into the item's vanilla
 * {@code ItemAttributeModifiers} data component, and Overgeared's own
 * {@code QualityAttributeHandler} (LOWEST-priority {@code
 * net.neoforged.neoforge.event.ItemAttributeModifierEvent} listener, already
 * shipped in the Overgeared jar) layers the quality bonus on top of whatever
 * attribute list is already present - transparently, for any item, Silent Gear or
 * not. That is the "genuinely pure data" half of the #67 investigation and
 * required zero new code; ship a {@code quality_attributes} JSON targeting Silent
 * Gear's gear tags (see this mod's {@code data/overgeared/quality_attributes/}).
 *
 * <p>What Silent Gear does NOT expose through the vanilla attribute system is its
 * own durability/harvest-speed properties (its {@code GearPropertyMap}, a
 * separate system from vanilla Attributes). Those need this class's first
 * listener, {@link #onGetPropertyModifiers}.
 */
public final class OvergearedSilentGearBridge {

    /**
     * Fires once per (part, property) pair while Silent Gear recomputes an
     * item's stats ({@code net.silentchaos512.gear.api.event.GetPropertyModifiersEvent},
     * confirmed public/generic event via the installed jar's own class file - the
     * event does not carry the parent ItemStack directly, only the
     * {@code PartInstance}; TODO(real-build): confirm PartInstance exposes (or
     * {@code GetPropertyModifiersEvent} should be extended with) a back-reference
     * to the gear ItemStack being computed, since that's where the
     * FORGING_QUALITY component lives - if it doesn't, the alternative is reading
     * quality off Silent Gear's per-gear "computing" context via
     * {@code GearRecalculateEvent.Pre}, capturing it in a thread-local for the
     * duration of the recalculation, matching the pattern Overgeared's own
     * QualityAttributeHandler doesn't need only because ItemAttributeModifierEvent
     * DOES carry the stack directly).
     */
    @SubscribeEvent
    public void onGetPropertyModifiers(GetPropertyModifiersEvent<?, ?> event) {
        if (event.getPropertyKey() != GearProperties.DURABILITY.get()
                && event.getPropertyKey() != GearProperties.HARVEST_SPEED.get()) {
            return;
        }

        ForgingQuality quality = currentlyRecalculatingQuality.get();
        if (quality == null || quality == ForgingQuality.NONE) {
            return;
        }

        double bonus = quality == ForgingQuality.NONE ? 0.0 : bonusFor(event.getPropertyKey(), quality);
        if (bonus == 0.0) return;

        // TODO(real-build): confirm GetPropertyModifiersEvent<T, V>.getModifiers()
        // is a mutable List<V> as its class file suggests (a plain getter with no
        // separate "addModifier" method), so adding directly to it is honored by
        // Silent Gear's own property-computation caller.
        @SuppressWarnings("unchecked")
        var modifiers = (java.util.List<NumberPropertyValue>) event.getModifiers();
        modifiers.add(new NumberPropertyValue((float) bonus, NumberProperty.Operation.ADD));
    }

    /**
     * Fires after Silent Gear finishes recomputing an item's stats
     * ({@code GearRecalculateEvent.Post}, confirmed public event via the
     * installed jar). Used for two things:
     * <ol>
     *   <li>Tracking which {@link ForgingQuality} is "in scope" for the
     *   {@link #onGetPropertyModifiers} listener above during this
     *   recalculation (see the TODO there).</li>
     *   <li>Stamping a fixed default quality (config: {@code
     *   defaultQualityForUnforgedGear}, WELL unless overridden) onto any Silent
     *   Gear item that reaches a finished state without ever touching the
     *   Overgeared anvil - pattern-crafted parts, non-metal assemblies, and any
     *   other Silent Gear crafting path this pack keeps open. Only applies if
     *   the item has no quality yet, so it never overwrites a real
     *   anvil-forged roll.</li>
     * </ol>
     */
    @SubscribeEvent
    public void onGearRecalculate(GearRecalculateEvent.Post event) {
        ItemStack gear = event.getGear();
        if (!(gear.getItem() instanceof GearItem)) return;

        ForgingQuality existing = gear.getOrDefault(ModComponents.FORGING_QUALITY.get(), ForgingQuality.NONE);
        if (existing == ForgingQuality.NONE) {
            gear.set(ModComponents.FORGING_QUALITY.get(), QualityBridgeConfig.DEFAULT_UNFORGED_QUALITY.get());
        }
    }

    @SubscribeEvent
    public void onGearRecalculatePre(GearRecalculateEvent.Pre event) {
        ItemStack gear = event.getGear();
        currentlyRecalculatingQuality.set(
                gear.getOrDefault(ModComponents.FORGING_QUALITY.get(), ForgingQuality.NONE));
    }

    private static final ThreadLocal<ForgingQuality> currentlyRecalculatingQuality = new ThreadLocal<>();

    /**
     * Mirrors Overgeared's own per-quality durability/mining-speed config bonus
     * values ({@code ServerConfig.POOR_DURABILITY_BONUS} .. {@code
     * MASTER_DURABILITY_BONUS}, {@code *_MINING_SPEED_BONUS}, all confirmed
     * present in the installed jar via ForgingQuality's own class file) so a
     * quality grade means the same thing whether it landed on an Overgeared-
     * native tool or a Silent Gear one.
     */
    private static double bonusFor(Object propertyKey, ForgingQuality quality) {
        boolean durability = propertyKey == GearProperties.DURABILITY.get();
        return switch (quality) {
            case POOR -> durability ? ServerConfig.POOR_DURABILITY_BONUS.get() : ServerConfig.POOR_MINING_SPEED_BONUS.get();
            case WELL -> durability ? ServerConfig.WELL_DURABILITY_BONUS.get() : ServerConfig.WELL_MINING_SPEED_BONUS.get();
            case EXPERT -> durability ? ServerConfig.EXPERT_DURABILITY_BONUS.get() : ServerConfig.EXPERT_MINING_SPEED_BONUS.get();
            case PERFECT -> durability ? ServerConfig.PERFECT_DURABILITY_BONUS.get() : ServerConfig.PERFECT_MINING_SPEED_BONUS.get();
            case MASTER -> durability ? ServerConfig.MASTER_DURABILITY_BONUS.get() : ServerConfig.MASTER_MINING_SPEED_BONUS.get();
            case NONE -> 0.0;
        };
    }
}
