package dev.vanillaplusplus.vppintegration.gear;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Objects;

/**
 * Pure validation/constants for the GitHub #67 Phase 3 "Paxel" assembly: combining
 * 3 same-material Silent Gear tool heads (this pack's Phase 1/2 forging recipes
 * already produce these) into a {@code silentgear:paxel_head}, through the
 * Overgeared anvil.
 *
 * <p>Deliberately has ZERO Minecraft/Silent Gear/Overgeared imports so it can be
 * unit tested on a plain JVM classpath - the mixin that actually performs the
 * craft-time correction ({@code dev.vanillaplusplus.vppintegration.mixin
 * .PaxelHeadForgingMixin}) is the only caller that touches real game types, and
 * it delegates all the "is this a valid combination" logic here.
 *
 * <p><b>Why pickaxe + axe + shovel heads, specifically:</b> a paxel functionally
 * replaces exactly those 3 tools (mines like a pickaxe, chops like an axe, digs
 * like a shovel), and this pack's Phase 1/2 forging recipes already produce all
 * three as {@code silentgear:pickaxe_head}/{@code axe_head}/{@code shovel_head}
 * across every material tier - no new part types or forging recipes needed, only
 * a way to combine 3 already-forgeable heads.
 *
 * <p><b>Why one recipe/validation covers every material tier</b> (unlike Phase 2's
 * one-recipe-per-material-tier ladder for ingots): {@code silentgear:pickaxe_head}/
 * {@code axe_head}/{@code shovel_head} are each a single registered item id
 * regardless of material - Silent Gear stores the material assignment in a data
 * component ({@code SgDataComponents.MATERIAL_LIST}), not in the item id. So a
 * single Overgeared forging recipe keyed on these 3 item ids matches a copper
 * pickaxe head exactly the same as an unobtainium one; this class's {@link
 * #sameMaterial(List)} check is what actually enforces "same material tier" at
 * craft time (the recipe's own {@code Ingredient} matching cannot see the
 * material component at all - confirmed via {@code javap} on Overgeared's
 * {@code ForgingRecipe.ForgingIngredient.test(ItemStack)}, which only calls the
 * plain vanilla {@code Ingredient.test}).
 */
public final class PaxelHeadRecipe {
    private PaxelHeadRecipe() {}

    /** The Silent Gear item id this assembly produces. */
    public static final String PAXEL_HEAD_ITEM_ID = "silentgear:paxel_head";

    /**
     * The 3 Silent Gear tool-head item ids this assembly consumes, in no
     * particular order. Real Silent Gear item ids (see {@code
     * silentgear:pickaxe_head}/{@code axe_head}/{@code shovel_head} - the same
     * ids this pack's own Phase 1/2 {@code data/overgeared/recipe/forging/
     * *_silentgear.json} recipes already produce, ground-truthed against
     * {@code server/mods/silent-gear-*.jar}'s own {@code data/silentgear/recipe/
     * gear/*.json}).
     */
    public static final List<String> REQUIRED_HEAD_ITEM_IDS =
            List.of("silentgear:pickaxe_head", "silentgear:axe_head", "silentgear:shovel_head");

    /**
     * True iff {@code presentItemIds} contains every id in {@link
     * #REQUIRED_HEAD_ITEM_IDS} (duplicates/extra ids/ordering don't matter - the
     * caller is expected to have already narrowed the collection down to "item
     * stacks found in the anvil's slots").
     */
    public static boolean hasAllRequiredHeads(Collection<String> presentItemIds) {
        if (presentItemIds == null) return false;
        return presentItemIds.containsAll(REQUIRED_HEAD_ITEM_IDS);
    }

    /**
     * True iff {@code materialIds} has exactly 3 entries, none null/blank, and
     * all equal - the "3 same-material heads" validation this feature requires.
     * {@code materialIds} is expected to be one material id per input head (e.g.
     * a Silent Gear material's {@code ResourceLocation.toString()}), in any order.
     */
    public static boolean sameMaterial(List<String> materialIds) {
        if (materialIds == null || materialIds.size() != REQUIRED_HEAD_ITEM_IDS.size()) return false;

        List<String> nonBlank = new ArrayList<>(materialIds.size());
        for (String id : materialIds) {
            if (id == null || id.isBlank()) return false;
            nonBlank.add(id);
        }

        String first = nonBlank.get(0);
        for (String id : nonBlank) {
            if (!Objects.equals(first, id)) return false;
        }
        return true;
    }
}
