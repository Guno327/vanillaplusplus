package dev.vanillaplusplus.vppintegration.mixin;

import dev.vanillaplusplus.vppintegration.gear.PaxelHeadRecipe;
import dev.vanillaplusplus.vppintegration.quality.PaxelQualityBridge;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.Container;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.silentchaos512.gear.gear.material.MaterialInstance;
import net.silentchaos512.gear.setup.SgDataComponents;
import net.stirdrem.overgeared.ForgingQuality;
import net.stirdrem.overgeared.block.entity.AbstractSmithingAnvilBlockEntity;
import net.stirdrem.overgeared.components.ModComponents;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.ArrayList;
import java.util.List;

/**
 * GitHub #67 Phase 3 "Paxel": combines 3 same-material Silent Gear tool heads
 * (pickaxe/axe/shovel heads - the exact parts this pack's Phase 1/2 forging
 * recipes already produce, across every material tier) into a {@code
 * silentgear:paxel_head}, forged through the same Overgeared anvil flow as every
 * other part, with the resulting head's Overgeared quality = the forge roll x the
 * 3 input heads' own already-rolled quality (see {@code
 * dev.vanillaplusplus.vppintegration.quality.PaxelQualityMath}/{@code
 * PaxelQualityBridge} for the math). {@code
 * data/overgeared/recipe/forging/paxel_head_silentgear.json} is the one recipe
 * this targets - unlike Phase 2's one-recipe-per-material-tier ladder, a single
 * recipe covers every tier here because {@code silentgear:pickaxe_head}/{@code
 * axe_head}/{@code shovel_head} are each a single item id regardless of
 * material (material lives in a data component, not the item id) - see {@link
 * PaxelHeadRecipe}'s class doc for the full reasoning.
 *
 * <p>This is a deliberately SEPARATE mixin class from {@link
 * AbstractSmithingAnvilBlockEntityMixin} (both target the same {@code
 * AbstractSmithingAnvilBlockEntity} - Mixin supports multiple mixin classes on
 * one target in the same config, each with its own {@code @Inject}, which is
 * exactly what's used here), rather than adding a second branch to that class's
 * existing injection, for one reason worth flagging loudly: this feature does
 * NOT reuse that mixin's {@code instanceof GearItem} + {@code
 * GearData.recalculateGearData(...)} correction path, because bytecode evidence
 * (via {@code javap} against {@code server/mods/silent-gear-1.21.1-neoforge-
 * 4.2.1.1.jar}) shows that path cannot apply to a freshly-forged PART item at
 * all:
 * <ul>
 *   <li>{@code silentgear:pickaxe_head}/{@code axe_head}/{@code shovel_head}/
 *   {@code paxel_head} are all {@code MainPartItem} (which extends {@code
 *   CompoundPartItem}, which extends plain {@code Item}) - none of that chain
 *   implements {@code net.silentchaos512.gear.api.item.GearItem} (confirmed via
 *   {@code javap -p} on all three classes: no {@code implements} clause
 *   mentions {@code GearItem}). Only the fully-assembled tool items (e.g. {@code
 *   GearPickaxeItem}, {@code GearPaxelItem}) implement it. So an {@code
 *   instanceof GearItem} check - the exact filter {@link
 *   AbstractSmithingAnvilBlockEntityMixin} uses to find "the resulting Silent
 *   Gear part stack" - never matches any of this pack's *_head/blade results,
 *   Paxel included.</li>
 *   <li>Separately, {@code GearData.recalculateGearData(ItemStack, Player)}
 *   (confirmed via {@code javap -c} on {@code GearData}) reads {@code
 *   SgDataComponents.GEAR_CONSTRUCTION} first and returns immediately if it's
 *   null - and a bare part/head stack (as opposed to an assembled gear item
 *   built from a {@code PartList}) never has that component, so the call is a
 *   guaranteed no-op on a head stack regardless of the {@code instanceof}
 *   question above.</li>
 * </ul>
 * Both are pre-existing conditions in already-merged Phase 1/2 code, not
 * something this Phase 3 change introduces or is in scope to fix - flagged here,
 * and in this mod's PR report, so it's visible rather than silently worked
 * around. What this mixin does instead, which does not depend on either broken
 * assumption: match on the real class (any {@code CompoundPartItem}, via item id
 * rather than an {@code instanceof} on an interface it doesn't implement) and
 * write {@code MATERIAL_LIST}/{@code FORGING_QUALITY} directly via {@code
 * ItemStack.set(...)} with no recalculation call - sufficient because {@code
 * CompoundPartItem.getMaterials(ItemStack)}/{@code getPrimaryMaterial(ItemStack)}
 * (confirmed via {@code javap}) read those components directly off the stack on
 * demand; a part item has no separately-cached "computed" state to refresh.
 */
@Mixin(AbstractSmithingAnvilBlockEntity.class)
public abstract class PaxelHeadForgingMixin {

    @Shadow
    protected Player player;

    @Inject(method = "craftItem", at = @At("TAIL"))
    private void vppintegration$assemblePaxelHead(CallbackInfo ci) {
        Container self = (Container) (Object) this;

        ItemStack paxelHead = null;
        List<ItemStack> headInputs = new ArrayList<>(PaxelHeadRecipe.REQUIRED_HEAD_ITEM_IDS.size());

        for (int i = 0; i < self.getContainerSize(); i++) {
            ItemStack slotStack = self.getItem(i);
            if (slotStack.isEmpty()) continue;

            String itemId = itemIdOf(slotStack);
            if (itemId.equals(PaxelHeadRecipe.PAXEL_HEAD_ITEM_ID)) {
                paxelHead = slotStack;
            } else if (PaxelHeadRecipe.REQUIRED_HEAD_ITEM_IDS.contains(itemId)) {
                headInputs.add(slotStack);
            }
        }

        if (paxelHead == null || headInputs.size() != PaxelHeadRecipe.REQUIRED_HEAD_ITEM_IDS.size()) {
            // Not a paxel-head assembly craft (or the pattern only partially
            // matched, which the recipe's own matcher should already prevent) -
            // nothing for this mixin to do.
            return;
        }

        List<String> materialIds = new ArrayList<>(headInputs.size());
        List<MaterialInstance> materials = new ArrayList<>(headInputs.size());
        List<ForgingQuality> inputQualities = new ArrayList<>(headInputs.size());
        for (ItemStack head : headInputs) {
            MaterialInstance material = MaterialInstance.from(head);
            if (material == null) {
                // A head with no resolvable material somehow reached the anvil -
                // bail without touching the result rather than guess.
                return;
            }
            materials.add(material);
            materialIds.add(material.getId().toString());
            inputQualities.add(head.getOrDefault(ModComponents.FORGING_QUALITY.get(), ForgingQuality.NONE));
        }

        if (!PaxelHeadRecipe.sameMaterial(materialIds)) {
            // Mismatched materials: leave the placeholder head's default/empty
            // material and quality alone rather than guess which input "wins" -
            // an obviously-wrong paxel head is a clearer signal to the player
            // than a silently-incorrect one.
            return;
        }

        paxelHead.set(SgDataComponents.MATERIAL_LIST.get(), List.of(materials.get(0)));

        ForgingQuality forgeRoll = paxelHead.getOrDefault(ModComponents.FORGING_QUALITY.get(), ForgingQuality.NONE);
        ForgingQuality combinedQuality = PaxelQualityBridge.combineQuality(forgeRoll, inputQualities);
        paxelHead.set(ModComponents.FORGING_QUALITY.get(), combinedQuality);
    }

    private static String itemIdOf(ItemStack stack) {
        ResourceLocation id = BuiltInRegistries.ITEM.getKey(stack.getItem());
        return id.toString();
    }
}
