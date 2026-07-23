package dev.vanillaplusplus.vppintegration.mixin;

import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.Container;
import net.minecraft.world.item.ItemStack;
import net.silentchaos512.gear.api.item.GearItem;
import net.silentchaos512.gear.api.material.Material;
import net.silentchaos512.gear.gear.material.MaterialInstance;
import net.silentchaos512.gear.setup.SgDataComponents;
import net.silentchaos512.gear.util.GearData;
import net.stirdrem.overgeared.block.entity.AbstractSmithingAnvilBlockEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.List;

/**
 * Corrects the material assignment on a Silent Gear part just forged at an
 * Overgeared anvil, then asks Silent Gear to recompute its stats.
 *
 * <p>Why this exists (see {@code VppIntegration}'s class doc for the full
 * picture): Overgeared's own forging recipes are static, one-recipe-per-material
 * JSON with a single fixed result item - they cannot express "whichever material
 * tier the player actually forged with", so this mod's own
 * {@code data/overgeared/recipe/forging/*.json} entries ship a placeholder
 * result (a Silent Gear part item with Silent Gear's own default/empty material
 * assignment). This mixin fixes that placeholder up at craft time using Silent
 * Gear's real material-detection API - not a guessed codec:
 * {@code MaterialInstance.fromItem(ItemStack) -> Material} (confirmed present in
 * the installed jar via its class file), which is the exact same "what material
 * is this ingot" lookup Silent Gear's own {@code compound_part} recipe uses
 * internally.
 *
 * <p>Injection point: {@code AbstractSmithingAnvilBlockEntity.craftItem
 * (ServerPlayer)}, confirmed to exist by name in the installed Overgeared jar
 * (this class is where {@code ForgingQualityHelper.applyForgingQuality} is
 * called from, per that helper's own use in the decompiled strings table).
 * TODO(real-build, needs javap/a real compile - no JDK was available in the
 * sandbox this mod was authored in): confirm the exact method descriptor
 * (parameter type - {@code ServerPlayer} vs {@code Player}) and that {@code TAIL}
 * is reachable on every code path (i.e. the method doesn't return early before
 * the result item is placed in its output container).
 */
@Mixin(AbstractSmithingAnvilBlockEntity.class)
public abstract class AbstractSmithingAnvilBlockEntityMixin {

    @Inject(method = "craftItem", at = @At("TAIL"))
    private void vppintegration$correctForgedGearMaterial(ServerPlayer player, CallbackInfo ci) {
        // AbstractSmithingAnvilBlockEntity implements WorldlyContainer (confirmed
        // via the installed jar's own class file), so this cast is safe - it's
        // the standard Mixin idiom for reaching a real interface the merged
        // target class implements without redeclaring it (and its abstract
        // methods) on this mixin class itself.
        Container self = (Container) (Object) this;

        // The freshly-forged ingot is somewhere in this block entity's slots
        // (Overgeared's own slot layout is internal - scanning by content type
        // rather than a hardcoded index is deliberately more resilient to a
        // version bump changing slot indices). We look for the single ingot
        // Silent Gear itself recognizes as a material, and the single
        // resulting Silent Gear part stack, independently.
        Material forgedMaterial = null;
        for (int i = 0; i < self.getContainerSize(); i++) {
            ItemStack slotStack = self.getItem(i);
            if (slotStack.isEmpty()) continue;
            Material candidate = MaterialInstance.fromItem(slotStack);
            if (candidate != null) {
                forgedMaterial = candidate;
                break;
            }
        }
        if (forgedMaterial == null) return;

        for (int i = 0; i < self.getContainerSize(); i++) {
            ItemStack slotStack = self.getItem(i);
            if (slotStack.isEmpty() || !(slotStack.getItem() instanceof GearItem)) continue;

            // TODO(real-build): confirm MaterialInstance.of(Material, ItemStack)
            // (or the Material-only overload) is the right factory - both
            // descriptors are present in the installed jar's MaterialInstance
            // class file, matched here to the overload that also takes the
            // ingot stack (used by Silent Gear's own recipes to capture e.g.
            // per-item material modifiers/NBT, not just the base Material).
            MaterialInstance instance = MaterialInstance.of(forgedMaterial);
            slotStack.set(SgDataComponents.MATERIAL_LIST.get(), List.of(instance));

            // Recompute GearPropertiesData/ItemAttributeModifiers from the
            // corrected material - the exact same call Silent Gear's own
            // GearItem default methods make after any part change.
            GearData.recalculateGearData(slotStack, player);
        }
    }
}
