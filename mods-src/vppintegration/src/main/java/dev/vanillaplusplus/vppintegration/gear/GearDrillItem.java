package dev.vanillaplusplus.vppintegration.gear;

import java.util.function.Supplier;

import net.minecraft.tags.TagKey;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.phys.HitResult;
import net.neoforged.neoforge.common.ItemAbility;
import net.silentchaos512.gear.api.item.GearType;
import net.silentchaos512.gear.core.component.GearPropertiesData;
import net.silentchaos512.gear.item.gear.GearPickaxeItem;
import net.silentchaos512.gear.util.IAoeTool;

/**
 * The Vanilla++ "Drill" gear (GitHub issue #154): a single Silent Gear tool that
 * combines the hammer's 3x3 pickaxe-AOE with the excavator's 3x3 shovel-AOE.
 *
 * <p>How the combination is achieved without touching Silent Gear itself:
 * <ul>
 *   <li><b>3x3 area mining</b> comes purely from implementing {@link IAoeTool}.
 *   Silent Gear's {@code IAoeTool.BreakHandler} is a global {@code
 *   BlockEvent.BreakEvent} listener that fires for <em>any</em> held item that is
 *   {@code instanceof IAoeTool} (verified against the 4.2.1.1 jar), so this tool
 *   inherits the exact same neighbour-gathering logic the hammer/excavator use -
 *   including the {@code silentgear:widen} trait scaling the radius to 5x5/7x7/9x9.</li>
 *   <li><b>Which neighbours get broken</b> is decided by {@code
 *   IAoeTool.isEffectiveOnBlock}, whose default implementation calls
 *   {@code stack.getItem().isCorrectToolForDrops(stack, state)}. That correctness
 *   is driven, for every Silent Gear digger, by the {@link TagKey} returned from
 *   {@link #getToolBlockSet} (Silent Gear's {@code GearDiggerTool.createToolProperties}
 *   builds the vanilla {@code Tool} component from it). By overriding it to a tag
 *   that unions {@code #minecraft:mineable/pickaxe} and {@code #minecraft:mineable/shovel}
 *   (see {@code data/vppintegration/tags/block/mineable_with_drill.json}), the drill
 *   is the correct tool for - and therefore AOE-breaks - both stone-family and
 *   dirt-family blocks. This is the hammer-union-excavator behaviour #154 asks for.</li>
 *   <li><b>Tool actions</b> (stripping/pathing gating, {@code canPerformAction}) are
 *   delegated wholesale to the drill {@link GearType}, whose tool-action set is the
 *   union of the default pickaxe and shovel actions (see {@link DrillGear}).</li>
 * </ul>
 *
 * <p>Extending {@link GearPickaxeItem} (rather than composing from scratch) reuses
 * all of Silent Gear's gear machinery - stat/property computation, durability bar,
 * repair, tooltips, harvest-tier component - unchanged; only the three methods below
 * differ from a plain pickaxe.
 */
public class GearDrillItem extends GearPickaxeItem implements IAoeTool {
    public GearDrillItem(Supplier<GearType> gearType) {
        super(gearType);
    }

    @Override
    public boolean canPerformAction(ItemStack stack, ItemAbility ability) {
        // Mirror GearHammerItem/GearExcavatorItem: the gear TYPE owns the action set
        // (here, pickaxe actions unioned with shovel actions).
        return getGearType().canPerformAction(ability);
    }

    @Override
    public TagKey<Block> getToolBlockSet(GearPropertiesData properties) {
        // Union of mineable/pickaxe + mineable/shovel - the whole point of the drill.
        return DrillGear.MINEABLE_WITH_DRILL;
    }

    @Override
    public HitResult rayTraceBlocks(Level level, Player player) {
        // Same as the hammer/excavator: target solid blocks, never fluids, so the
        // AOE origin face is the block the player is actually mining.
        return getPlayerPOVHitResult(level, player, ClipContext.Fluid.NONE);
    }
}
