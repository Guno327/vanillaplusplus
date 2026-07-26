package dev.vanillaplusplus.vppintegration.gear;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class PaxelHeadRecipeTest {

    @Test
    void sameMaterial_trueWhenAllThreeMatch() {
        assertTrue(PaxelHeadRecipe.sameMaterial(
                List.of("silentgear:iron", "silentgear:iron", "silentgear:iron")));
    }

    @Test
    void sameMaterial_falseWhenOneDiffers() {
        assertFalse(PaxelHeadRecipe.sameMaterial(
                List.of("silentgear:iron", "silentgear:iron", "silentgear:copper")));
    }

    @Test
    void sameMaterial_falseWhenAllThreeDiffer() {
        assertFalse(PaxelHeadRecipe.sameMaterial(
                List.of("silentgear:iron", "silentgear:copper", "silentgear:brass")));
    }

    @Test
    void sameMaterial_falseWhenWrongCount() {
        assertFalse(PaxelHeadRecipe.sameMaterial(List.of("silentgear:iron", "silentgear:iron")));
        assertFalse(PaxelHeadRecipe.sameMaterial(
                List.of("silentgear:iron", "silentgear:iron", "silentgear:iron", "silentgear:iron")));
        assertFalse(PaxelHeadRecipe.sameMaterial(List.of()));
    }

    @Test
    void sameMaterial_falseWhenNullList() {
        assertFalse(PaxelHeadRecipe.sameMaterial(null));
    }

    @Test
    void sameMaterial_falseWhenAnyEntryNullOrBlank() {
        List<String> withNull = new java.util.ArrayList<>();
        withNull.add("silentgear:iron");
        withNull.add(null);
        withNull.add("silentgear:iron");
        assertFalse(PaxelHeadRecipe.sameMaterial(withNull));

        assertFalse(PaxelHeadRecipe.sameMaterial(List.of("silentgear:iron", "  ", "silentgear:iron")));
    }

    @Test
    void hasAllRequiredHeads_trueWhenAllThreeItemIdsPresent() {
        assertTrue(PaxelHeadRecipe.hasAllRequiredHeads(
                Set.of("silentgear:pickaxe_head", "silentgear:axe_head", "silentgear:shovel_head")));
    }

    @Test
    void hasAllRequiredHeads_trueWithExtraUnrelatedIds() {
        assertTrue(PaxelHeadRecipe.hasAllRequiredHeads(Set.of(
                "silentgear:pickaxe_head", "silentgear:axe_head", "silentgear:shovel_head",
                "silentgear:sword_blade")));
    }

    @Test
    void hasAllRequiredHeads_falseWhenOneMissing() {
        assertFalse(PaxelHeadRecipe.hasAllRequiredHeads(
                Set.of("silentgear:pickaxe_head", "silentgear:axe_head")));
    }

    @Test
    void hasAllRequiredHeads_falseWhenNull() {
        assertFalse(PaxelHeadRecipe.hasAllRequiredHeads(null));
    }

    @Test
    void requiredHeadItemIds_isExactlyPickaxeAxeShovel() {
        assertTrue(PaxelHeadRecipe.REQUIRED_HEAD_ITEM_IDS.containsAll(
                List.of("silentgear:pickaxe_head", "silentgear:axe_head", "silentgear:shovel_head")));
        assertTrue(PaxelHeadRecipe.REQUIRED_HEAD_ITEM_IDS.size() == 3);
    }
}
