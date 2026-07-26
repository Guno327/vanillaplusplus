package dev.vanillaplusplus.vppintegration.gear;

import dev.vanillaplusplus.vppintegration.VppIntegration;
import net.minecraft.world.item.Item;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredItem;
import net.neoforged.neoforge.registries.DeferredRegister;

/**
 * Heated-ingot items for the Vanilla++ material tiers beyond copper/iron
 * (GitHub issue #67 Phase 2 - see this mod's README.md, "Extending to the
 * pack's full material ladder").
 *
 * <p>Overgeared ships its own native {@code heated_iron_ingot}/
 * {@code heated_copper_ingot} items (confirmed via {@code javap} against the
 * installed jar's {@code net.stirdrem.overgeared.item.ModItems}: both are
 * registered as plain, property-less items via {@code ITEMS.registerSimpleItem
 * (String)} - not a bespoke {@code HeatedItem} subclass; "heated" behaviour
 * (the tongs/cooldown mechanic in {@code
 * net.stirdrem.overgeared.heateditem.HeatedItem#isHeated}) is driven purely by
 * tag membership in {@code overgeared:heated_metals}, confirmed via the same
 * javap read: {@code isHeated()} short-circuits true as soon as
 * {@code ItemStack.is(ModTags.Items.HEATED_METALS)} is true, before it ever
 * looks at the item's {@code HEATED_COMPONENT}) plus a
 * {@code minecraft:blasting} recipe from the plain ingot (mirroring
 * {@code data/overgeared/recipe/heated_iron_ingot_from_blasting_iron_ingot.json}
 * in the installed Overgeared jar exactly - see this mod's own
 * {@code data/overgeared/recipe/heated_*.json} files).
 *
 * <p>Overgeared has no native heated item for any of this pack's own material
 * tiers (Create's andesite alloy/brass/refined radiance, or Allthemodium's
 * allthemodium/vibranium/unobtainium/star-alloy chain - see
 * {@code scripts/gen_gear_materials.py}'s {@code MATERIALS} list, the pack's
 * own ground-truth source for "the pack's full metal ladder" beyond vanilla
 * copper/iron), so this mod registers one plain {@link Item} per tier here,
 * exactly the same {@code registerSimpleItem} idiom Overgeared's own
 * {@code ModItems} uses for its native heated ingots. Each is also added to
 * {@code overgeared:heated_metals} (this mod's own
 * {@code data/overgeared/tags/item/heated_metals.json}, which additively
 * merges with Overgeared's own same-id tag file the normal datapack way - not
 * a {@code "replace": true} override) so the tongs/cooldown mechanic works on
 * these items exactly like it does on the native ones.
 *
 * <p>Item ids intentionally do NOT always mirror the raw ingot's own item path
 * 1:1 - {@code vppintegration:heated_star_alloy} (not the much longer
 * {@code heated_unobtainium_vibranium_alloy_ingot}) matches this pack's own
 * short material key ({@code vpp_star_alloy} in {@code gen_gear_materials.py}),
 * the same simplification the rest of that generator already applies.
 */
public final class HeatedMetals {
    private HeatedMetals() {}

    public static final DeferredRegister.Items ITEMS =
            DeferredRegister.createItems(VppIntegration.MODID);

    // Tier index 1 (~iron-equivalent stat curve, see gen_gear_materials.py) -
    // raw ingredient create:andesite_alloy.
    public static final DeferredItem<Item> HEATED_ANDESITE_ALLOY =
            ITEMS.registerSimpleItem("heated_andesite_alloy");

    // Tier index 2 (~diamond-equivalent) - raw ingredient create:brass_ingot.
    public static final DeferredItem<Item> HEATED_BRASS_INGOT =
            ITEMS.registerSimpleItem("heated_brass_ingot");

    // Tier index 3 (post-diamond) - raw ingredient create:refined_radiance.
    public static final DeferredItem<Item> HEATED_REFINED_RADIANCE =
            ITEMS.registerSimpleItem("heated_refined_radiance");

    // Tier index 4 - raw ingredient allthemodium:allthemodium_ingot.
    public static final DeferredItem<Item> HEATED_ALLTHEMODIUM_INGOT =
            ITEMS.registerSimpleItem("heated_allthemodium_ingot");

    // Tier index 5 - raw ingredient allthemodium:vibranium_ingot.
    public static final DeferredItem<Item> HEATED_VIBRANIUM_INGOT =
            ITEMS.registerSimpleItem("heated_vibranium_ingot");

    // Tier index 6 - raw ingredient allthemodium:unobtainium_ingot.
    public static final DeferredItem<Item> HEATED_UNOBTAINIUM_INGOT =
            ITEMS.registerSimpleItem("heated_unobtainium_ingot");

    // Tier index 7 (top of the ladder) - raw ingredient
    // allthemodium:unobtainium_vibranium_alloy_ingot.
    public static final DeferredItem<Item> HEATED_STAR_ALLOY =
            ITEMS.registerSimpleItem("heated_star_alloy");

    /** Wire this registry onto this mod's event bus. Call from the mod constructor. */
    public static void register(IEventBus modEventBus) {
        ITEMS.register(modEventBus);
    }
}
