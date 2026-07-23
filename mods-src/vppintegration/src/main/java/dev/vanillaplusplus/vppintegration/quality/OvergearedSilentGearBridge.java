package dev.vanillaplusplus.vppintegration.quality;

import net.minecraft.world.item.ItemStack;
import net.neoforged.bus.api.SubscribeEvent;
import net.silentchaos512.gear.api.event.GearRecalculateEvent;
import net.silentchaos512.gear.api.item.GearItem;
import net.silentchaos512.gear.api.property.GearProperty;
import net.silentchaos512.gear.api.property.GearPropertyValue;
import net.silentchaos512.gear.api.property.NumberProperty;
import net.silentchaos512.gear.api.property.NumberPropertyValue;
import net.silentchaos512.gear.core.component.GearPropertiesData;
import net.silentchaos512.gear.setup.SgDataComponents;
import net.silentchaos512.gear.setup.gear.GearProperties;
import net.stirdrem.overgeared.ForgingQuality;
import net.stirdrem.overgeared.components.ModComponents;
import net.stirdrem.overgeared.config.ServerConfig;

import java.util.HashMap;
import java.util.Map;

/**
 * The Silent-Gear-side hook of the quality bridge.
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
 * own durability/harvest-speed properties (its {@code GearPropertyMap}/{@code
 * GearPropertiesData}, a separate system from vanilla Attributes). Those are
 * handled directly here in {@link #onGearRecalculate}.
 *
 * <p><b>Real-build correction (the single biggest finding from actually compiling
 * this mod):</b> the original design hooked {@code
 * net.silentchaos512.gear.api.event.GetPropertyModifiersEvent} and called {@code
 * event.getModifiers().add(...)} to inject a quality bonus per (part, property)
 * pair. javap against the real jar (server/mods/silent-gear-1.21.1-neoforge-4.2.1.1.jar)
 * proves that list is NOT mutable in the general case: {@code CoreGearPart}'s
 * property-computation call site builds the event's {@code modifiers} list via
 * {@code GearProperty.reduce(context, collection)}, whose base implementation is
 * {@code List.copyOf(collection)} - an immutable list - and {@code NumberProperty}
 * (the concrete type behind {@code GearProperties.DURABILITY}/{@code
 * HARVEST_SPEED}) does not override {@code reduce()}. Calling {@code .add(...)}
 * on that event's list would compile fine but throw {@code
 * UnsupportedOperationException} at runtime the first time any Silent Gear item
 * recalculates. (Separately, {@code event.getPropertyKey()} returns a {@code
 * PropertyKey<T, V>} wrapper, not the raw {@code GearProperty} - comparing it
 * directly against {@code GearProperties.DURABILITY.get()} is also a compile
 * error; the unwrap is {@code PropertyKey.property()}.)
 *
 * <p>The fix applied here instead reads and rewrites the item's already-computed
 * {@code SgDataComponents.GEAR_PROPERTIES} data component directly, in {@code
 * GearRecalculateEvent.Post} - AFTER Silent Gear's own {@code
 * GearData.recalculateGearData} has already {@code .set()} that component (confirmed
 * via javap on {@code GearData}: {@code GearRecalculateEvent.Post} is posted after
 * the data component write, not before). This is the same "read/replace a data
 * component directly" idiom {@link
 * dev.vanillaplusplus.vppintegration.mixin.AbstractSmithingAnvilBlockEntityMixin}
 * already uses for {@code MATERIAL_LIST}, uses only stable public API
 * ({@code GearPropertiesData}'s public record accessor/constructor,
 * {@code ItemStack.set}), and does not re-trigger recalculation (setting a data
 * component is a plain write, not an event in itself), so there is no re-entrancy
 * risk.
 */
public final class OvergearedSilentGearBridge {

    /**
     * Fires after Silent Gear finishes recomputing an item's stats and has
     * already written the result into the item's {@code GEAR_PROPERTIES} data
     * component ({@code GearRecalculateEvent.Post}, confirmed public event via
     * the installed jar, confirmed-by-javap ordering relative to the data
     * component write - see this class's doc). Used for two things:
     *
     * <p><b>Real-boot correction (found by the mandatory L0 boot smoke test, not
     * static analysis):</b> {@code GearRecalculateEvent.Post} does not only fire
     * during real gameplay - KubeJS's own recipe-manager reload lazily constructs
     * a {@code ShapelessGearRecipe}'s result item (to test its output against
     * script-side recipe filters, see {@code ShapelessGearRecipe.getResultItem}/
     * {@code UnknownKubeRecipe.hasOutput}) during the SAME datapack-reload pass
     * that loads server configs, and can run before either {@code
     * QualityBridgeConfig.SPEC} or Overgeared's own {@code ServerConfig
     * .SERVER_CONFIG} has finished loading. Calling {@code ModConfigSpec
     * .ConfigValue.get()} before that point throws {@code IllegalStateException}
     * ("Cannot get config value before config is loaded"), which NeoForge wraps
     * into a fatal {@code ReportedException} that aborted this exact recipe
     * reload in the first real boot test. Both config reads below now check
     * {@code ModConfigSpec.isLoaded()} first and fall back to the documented
     * defaults (same values the config declares) when it isn't - correct
     * indefinitely, not just during that early reload: once configs finish
     * loading, {@code isLoaded()} stays true and every subsequent call reads the
     * real (possibly player-edited) value.
     *
     * <ol>
     *   <li>Adding this quality grade's durability/harvest-speed bonus directly
     *   to the just-computed {@code GearPropertiesData} (see this class's doc
     *   for why this replaced the original {@code GetPropertyModifiersEvent}
     *   hook).</li>
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

        ForgingQuality quality = gear.getOrDefault(ModComponents.FORGING_QUALITY.get(), ForgingQuality.NONE);
        if (quality == ForgingQuality.NONE) {
            // See this method's class doc "Real-boot correction": this event can
            // fire before QualityBridgeConfig.SPEC has loaded (KubeJS's recipe-
            // manager reload lazily constructs gear recipe results during the
            // same pass that loads configs). isLoaded() false -> use the spec's
            // own documented default (ForgingQuality.WELL) instead of crashing;
            // once configs load, every later recalculation reads the real value.
            quality = QualityBridgeConfig.SPEC.isLoaded()
                    ? QualityBridgeConfig.DEFAULT_UNFORGED_QUALITY.get()
                    : ForgingQuality.WELL;
            gear.set(ModComponents.FORGING_QUALITY.get(), quality);
        }

        applyQualityToGearProperties(gear, quality);
    }

    /**
     * Rewrites {@code gear}'s {@code GEAR_PROPERTIES} data component, adding
     * this quality grade's durability/harvest-speed bonus on top of whatever
     * Silent Gear already computed. No-op if the item has no computed
     * properties yet (shouldn't happen this late in {@code GearRecalculateEvent
     * .Post}, but Silent Gear items can theoretically lack the component before
     * their first successful recalculation).
     */
    private static void applyQualityToGearProperties(ItemStack gear, ForgingQuality quality) {
        if (quality == ForgingQuality.NONE) return;

        GearPropertiesData data = gear.get(SgDataComponents.GEAR_PROPERTIES.get());
        if (data == null) return;

        Map<GearProperty<?, ?>, GearPropertyValue<?>> updated = new HashMap<>(data.properties());
        boolean changed = false;
        changed |= bumpNumberProperty(data, updated, GearProperties.DURABILITY.get(), quality);
        changed |= bumpNumberProperty(data, updated, GearProperties.HARVEST_SPEED.get(), quality);

        if (changed) {
            gear.set(SgDataComponents.GEAR_PROPERTIES.get(), new GearPropertiesData(updated));
        }
    }

    private static boolean bumpNumberProperty(
            GearPropertiesData data,
            Map<GearProperty<?, ?>, GearPropertyValue<?>> updated,
            NumberProperty property,
            ForgingQuality quality) {
        double bonus = bonusFor(property, quality);
        if (bonus == 0.0) return false;

        float current = data.getNumber(property);
        updated.put(property, new NumberPropertyValue(current + (float) bonus, NumberProperty.Operation.ADD));
        return true;
    }

    /**
     * Mirrors Overgeared's own per-quality durability/mining-speed config bonus
     * values ({@code ServerConfig.POOR_DURABILITY_BONUS} .. {@code
     * MASTER_DURABILITY_BONUS}, {@code *_MINING_SPEED_BONUS}, all confirmed
     * present in the installed jar via ForgingQuality's own class file) so a
     * quality grade means the same thing whether it landed on an Overgeared-
     * native tool or a Silent Gear one.
     *
     * <p>Same "Real-boot correction" as {@link #onGearRecalculate} applies here:
     * Overgeared's own {@code ServerConfig.SERVER_CONFIG} can likewise be
     * unloaded at the point this fires. Returns 0 (no bonus applied yet) rather
     * than crash - harmless, since Silent Gear recalculates {@code
     * GEAR_PROPERTIES} again on the item's next real recalculation (repair,
     * reforge, etc.), by which point configs have always finished loading.
     */
    private static double bonusFor(NumberProperty property, ForgingQuality quality) {
        if (!ServerConfig.SERVER_CONFIG.isLoaded()) return 0.0;
        boolean durability = property == GearProperties.DURABILITY.get();
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
