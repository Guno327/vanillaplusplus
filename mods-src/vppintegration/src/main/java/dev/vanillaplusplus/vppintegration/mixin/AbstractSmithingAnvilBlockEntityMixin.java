package dev.vanillaplusplus.vppintegration.mixin;

import net.minecraft.world.Container;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.silentchaos512.gear.api.item.GearItem;
import net.silentchaos512.gear.gear.material.MaterialInstance;
import net.silentchaos512.gear.setup.SgDataComponents;
import net.silentchaos512.gear.util.GearData;
import net.stirdrem.overgeared.block.entity.AbstractSmithingAnvilBlockEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
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
 * Gear's real material-detection API: {@code MaterialInstance.from(ItemStack)}
 * (confirmed via javap against the real jar this pack ships,
 * server/mods/silent-gear-1.21.1-neoforge-4.2.1.1.jar - the previous sandbox
 * build guessed a nonexistent {@code MaterialInstance.fromItem(ItemStack)
 * -> Material} that does not exist; the real method is {@code from(ItemStack)
 * -> MaterialInstance}, which internally does exactly
 * {@code SgRegistries.MATERIAL.fromItem(stack)} then
 * {@code MaterialInstance.of(Material, ItemStack)} - i.e. it already returns
 * the fully-built {@link MaterialInstance} in one call, so no separate
 * {@code Material} lookup + {@code MaterialInstance.of(Material)} step is
 * needed at all), which is the exact same "what material is this ingot"
 * lookup Silent Gear's own {@code compound_part} recipe uses internally.
 *
 * <p>Injection point: {@code AbstractSmithingAnvilBlockEntity.craftItem()}.
 * Confirmed via javap against the resolved {@code maven.modrinth:overgeared}
 * artifact (MC 1.21.1-1.6.16): the real method takes NO parameters (not
 * {@code craftItem(ServerPlayer)} as the previous sandbox build guessed from
 * decompiled strings) - the acting player is read off the block entity's own
 * {@code player} field (also confirmed present, type {@code Player}) via
 * {@code @Shadow} instead. {@code TAIL} is reachable and the freshly-forged
 * result item is present in this block entity's slots by then.
 */
@Mixin(AbstractSmithingAnvilBlockEntity.class)
public abstract class AbstractSmithingAnvilBlockEntityMixin {

    @Shadow
    protected Player player;

    @Inject(method = "craftItem", at = @At("TAIL"))
    private void vppintegration$correctForgedGearMaterial(CallbackInfo ci) {
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
        MaterialInstance forgedMaterial = null;
        for (int i = 0; i < self.getContainerSize(); i++) {
            ItemStack slotStack = self.getItem(i);
            if (slotStack.isEmpty()) continue;
            MaterialInstance candidate = MaterialInstance.from(slotStack);
            if (candidate != null) {
                forgedMaterial = candidate;
                break;
            }
        }
        if (forgedMaterial == null) return;

        for (int i = 0; i < self.getContainerSize(); i++) {
            ItemStack slotStack = self.getItem(i);
            if (slotStack.isEmpty() || !(slotStack.getItem() instanceof GearItem)) continue;

            slotStack.set(SgDataComponents.MATERIAL_LIST.get(), List.of(forgedMaterial));

            // Recompute GearPropertiesData/ItemAttributeModifiers from the
            // corrected material - the exact same call Silent Gear's own
            // GearItem default methods make after any part change.
            GearData.recalculateGearData(slotStack, this.player);
        }
    }
}
