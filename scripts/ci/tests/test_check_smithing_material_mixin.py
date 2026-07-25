import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_smithing_material_mixin  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

MIXIN_REL = check_smithing_material_mixin.MIXIN_REL

# The pre-#171-fix source: GitHub #171's actual dead-code idiom - filters
# result slots with `instanceof GearItem` (never matches a forged head) and
# calls GearData.recalculateGearData (a guaranteed no-op on a bare part
# stack). This fixture must FAIL the check.
BUGGY_MIXIN_SOURCE = """package dev.vanillaplusplus.vppintegration.mixin;

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

@Mixin(AbstractSmithingAnvilBlockEntity.class)
public abstract class AbstractSmithingAnvilBlockEntityMixin {

    @Shadow
    protected Player player;

    @Inject(method = "craftItem", at = @At("TAIL"))
    private void vppintegration$correctForgedGearMaterial(CallbackInfo ci) {
        Container self = (Container) (Object) this;
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

            GearData.recalculateGearData(slotStack, this.player);
        }
    }
}
"""

# The post-#171-fix source (matches the real fixed file's shape): matches by
# CompoundPartItem, writes MATERIAL_LIST directly, no recalculateGearData
# call, no GearData import. This fixture must PASS the check.
FIXED_MIXIN_SOURCE = """package dev.vanillaplusplus.vppintegration.mixin;

import net.minecraft.world.Container;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.silentchaos512.gear.gear.material.MaterialInstance;
import net.silentchaos512.gear.item.CompoundPartItem;
import net.silentchaos512.gear.setup.SgDataComponents;
import net.stirdrem.overgeared.block.entity.AbstractSmithingAnvilBlockEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

import java.util.List;

@Mixin(AbstractSmithingAnvilBlockEntity.class)
public abstract class AbstractSmithingAnvilBlockEntityMixin {

    @Shadow
    protected Player player;

    @Inject(method = "craftItem", at = @At("TAIL"))
    private void vppintegration$correctForgedGearMaterial(CallbackInfo ci) {
        Container self = (Container) (Object) this;
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
            if (slotStack.isEmpty() || !(slotStack.getItem() instanceof CompoundPartItem)) continue;

            slotStack.set(SgDataComponents.MATERIAL_LIST.get(), List.of(forgedMaterial));
        }
    }
}
"""


class TestCheckSmithingMaterialMixin(unittest.TestCase):
    def _write_fixture(self, tmp, source):
        root = Path(tmp)
        mixin_path = root / MIXIN_REL
        mixin_path.parent.mkdir(parents=True, exist_ok=True)
        mixin_path.write_text(source, encoding="utf-8")
        return root

    def test_buggy_idiom_fails(self):
        # Proves the check would have caught #171 before the fix: the old
        # `instanceof GearItem` + recalculateGearData idiom must FAIL.
        with tempfile.TemporaryDirectory() as tmp:
            root = self._write_fixture(tmp, BUGGY_MIXIN_SOURCE)
            self.assertEqual(check_smithing_material_mixin.main([str(root)]), 1)

    def test_fixed_idiom_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._write_fixture(tmp, FIXED_MIXIN_SOURCE)
            self.assertEqual(check_smithing_material_mixin.main([str(root)]), 0)

    def test_missing_file_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(check_smithing_material_mixin.main([str(root)]), 1)

    def test_gear_item_instanceof_alone_fails_even_without_recalculate(self):
        # Reinstating just the dead filter (without the recalculate call)
        # should still fail - the filter alone is the actual bug.
        source = FIXED_MIXIN_SOURCE.replace(
            "instanceof CompoundPartItem", "instanceof GearItem"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = self._write_fixture(tmp, source)
            self.assertEqual(check_smithing_material_mixin.main([str(root)]), 1)

    def test_recalculate_call_alone_fails_even_with_compoundpartitem_filter(self):
        source = FIXED_MIXIN_SOURCE.replace(
            "slotStack.set(SgDataComponents.MATERIAL_LIST.get(), List.of(forgedMaterial));",
            "slotStack.set(SgDataComponents.MATERIAL_LIST.get(), List.of(forgedMaterial));\n"
            "            GearData.recalculateGearData(slotStack, this.player);",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = self._write_fixture(tmp, source)
            self.assertEqual(check_smithing_material_mixin.main([str(root)]), 1)


class TestCheckSmithingMaterialMixinRealRepo(unittest.TestCase):
    def test_real_repo_passes(self):
        mixin_path = REPO_ROOT / MIXIN_REL
        if not mixin_path.is_file():
            self.skipTest(f"not running inside the repo (no mixin at {mixin_path})")
        self.assertEqual(check_smithing_material_mixin.main([str(REPO_ROOT)]), 0)


if __name__ == "__main__":
    unittest.main()
