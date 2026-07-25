package dev.vanillaplusplus.vppintegration.gear;

import java.util.HashSet;
import java.util.Set;
import java.util.function.Function;

import dev.vanillaplusplus.vppintegration.VppIntegration;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.TagKey;
import net.minecraft.world.item.Item;
import net.minecraft.world.level.block.Block;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.common.ItemAbilities;
import net.neoforged.neoforge.common.ItemAbility;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.silentchaos512.gear.api.item.GearType;
import net.silentchaos512.gear.item.GearItemSet;
import net.silentchaos512.gear.setup.SgRegistries;
import net.silentchaos512.gear.setup.gear.GearTypes;

/**
 * Registration for the Vanilla++ "Drill" - a Silent Gear combo tool that is a
 * hammer AND an excavator at once (GitHub issue #154).
 *
 * <p>Everything here is registered into Silent Gear's own registries via NeoForge
 * {@link DeferredRegister}s from this add-on mod, so nothing in Silent Gear is
 * forked or patched:
 * <ul>
 *   <li>a new {@link GearType} {@code vppintegration:drill}, parented to
 *   {@code silentgear:harvest_tool} (so it inherits the harvest-tool trait pool and
 *   the {@code widen} trait), whose tool-action set is the union of the default
 *   pickaxe and shovel actions;</li>
 *   <li>the four items every Silent Gear tool needs - the gear item
 *   ({@code vppintegration:drill}), its main part ({@code vppintegration:drill_head}),
 *   and its blueprint + template - built by Silent Gear's own {@link GearItemSet}
 *   helper exactly the way its built-in tools are.</li>
 * </ul>
 * The recipes, part definition, tags, models and lang that make it craftable live
 * in this mod's {@code resources/data|assets/vppintegration/} tree.
 */
public final class DrillGear {
    private DrillGear() {}

    public static final DeferredRegister<GearType> GEAR_TYPES =
            DeferredRegister.create(SgRegistries.GEAR_TYPE_KEY, VppIntegration.MODID);

    public static final DeferredRegister.Items ITEMS =
            DeferredRegister.createItems(VppIntegration.MODID);

    /**
     * Block set the drill is the correct tool for. Backed by
     * {@code data/vppintegration/tags/block/mineable_with_drill.json}, which unions
     * {@code #minecraft:mineable/pickaxe} and {@code #minecraft:mineable/shovel}.
     */
    public static final TagKey<Block> MINEABLE_WITH_DRILL = TagKey.create(
            Registries.BLOCK,
            ResourceLocation.fromNamespaceAndPath(VppIntegration.MODID, "mineable_with_drill"));

    /** Pickaxe actions ∪ shovel actions, so the drill both digs and paths/strips like each parent. */
    private static Set<ItemAbility> drillActions() {
        Set<ItemAbility> actions = new HashSet<>(ItemAbilities.DEFAULT_PICKAXE_ACTIONS);
        actions.addAll(ItemAbilities.DEFAULT_SHOVEL_ACTIONS);
        return Set.copyOf(actions);
    }

    public static final DeferredHolder<GearType, GearType> DRILL = GEAR_TYPES.register(
            "drill",
            () -> GearType.Builder.of(GearTypes.HARVEST_TOOL)
                    .toolActions(drillActions())
                    .build());

    @SuppressWarnings({"rawtypes", "unchecked"})
    public static final GearItemSet DRILL_SET = new GearItemSet(
            DRILL,
            "drill_head",
            (Function) (holder -> new GearDrillItem(DRILL)));

    /** Wire the drill's registries onto this mod's event bus. Call from the mod constructor. */
    public static void register(IEventBus modEventBus) {
        DRILL_SET.registerGearItem(ITEMS);
        DRILL_SET.registerMainPartItem(ITEMS);
        DRILL_SET.registerBlueprintItem(ITEMS);
        DRILL_SET.registerTemplateItem(ITEMS);
        GEAR_TYPES.register(modEventBus);
        ITEMS.register(modEventBus);
    }
}
