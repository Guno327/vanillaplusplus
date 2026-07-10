// TODO.md item 9 (food overhaul, diet variety): Create Central Kitchen's Saw
// conversion is real (verified: create-central-kitchen 2.5.0's
// CuttingBoardRecipeConverters builds a synthetic CuttingBoardRecipeInput
// using `new ItemStack(ModItems.IRON_KNIFE)` as the "held tool" and matches
// it against every farmersdelight:cutting recipe's own `tool` Ingredient -
// only recipes whose tool accepts a plain Iron Knife get exposed on the Saw).
// This is the pack's own automation bar for item 9: "every food chain must
// be fully Create-automatable end-to-end; any station that can't be driven
// by Create gets patched, or the gap gets disclosed."
//
// Enumerating every farmersdelight:cutting recipe shipped by farmersdelight
// 1.3.2 + ends-delight 2.6.1 + extradelight 2.6.6 (222 total across the
// three jars) and classifying by `tool` field found exactly TWO
// FOOD-PRODUCING recipes whose tool is neither the c:tools/knife tag (Saw-
// automatable as-is) NOR one of the standard axe/hoe/pickaxe/shovel/shears
// ability tags (Deployer-automatable by holding the matching tool, since
// those tags are all real members of Create's own `create:
// handheld_in_deployer_use` tag = `#c:tools` minus bow/crossbow/shield, so
// the Deployer treats them as a durable held tool, not a consumed item):
//
//   1. ends_delight:crack_non_hatchable_dragon_egg - tool is a LITERAL
//      `{"item": "minecraft:nether_star"}`, not a tag. Nether Star carries no
//      `c:tools` membership (confirmed: not present in any item tag in
//      ends-delight, extradelight, or the base game/NeoForge tag set this
//      pack ships) - so a Deployer holding one would NOT be recognized as
//      "holding a durable tool" and would very likely treat the Nether Star
//      as a consumed/applied item instead (Create's own convention for any
//      item outside `handheld_in_deployer_use`), burning one irreplaceable
//      boss-drop item per crack. This is the sole entry point into End's
//      Delight's entire Fried Dragon Egg dish line (feeds
//      food_smelting/food_smoking/food_campfire_cooking's fried_dragon_egg,
//      itself gated behind the "Dragon Egg Shell Feast" advancement) - a
//      real food chain, not a decorative/utility recipe.
//
//   2. extradelight's 8 grater-tool recipes (grated_ginger, grate_bread,
//      grate_carrot, grate_garlic, grate_potato, lemon_zest_grater,
//      lime_zest_grater, orange_zest_grater) - tool is a LITERAL
//      `{"item": "extradelight:grater"}`. Confirmed via extradelight's own
//      shipped item tags: the Grater is not a member of ANY item tag
//      (unlike its Spoon line, which IS tagged `c:spoons` -> `c:tools` ->
//      `handheld_in_deployer_use`, so spoon_ginger IS genuinely Deployer-
//      automatable as-is, no patch needed there). Same non-renewable-tool-
//      consumption risk as the dragon egg case above, just with a cheap
//      renewable tool instead of a boss drop - still not "fully Create-
//      automatable" in the spirit of the automation bar, since a Deployer
//      would (probably) eat a Grater per grate rather than holding one
//      indefinitely like a knife/axe/hoe.
//
// FIX: rather than gamble on exactly how CCK's Deployer integration treats
// an untagged tool item (no javap/decompiler available in this pack's
// sandbox to confirm Create's ItemApplicationRecipe consumption logic with
// certainty), add an ADDITIONAL farmersdelight:cutting recipe for each of
// these 9 cases with the exact same ingredients/result but
// `tool: {"tag": "c:tools/knife"}` instead - this is the exact same
// tool-tag CCK's Saw conversion already proves out for 47+78 other recipes
// in this pack (farmersdelight + extradelight's own knife-tool recipes), so
// it inherits that same, already-verified Saw automation path instead of
// depending on Deployer/tag-consumption behavior. The ORIGINAL recipes are
// left untouched (not removed) - hand-crafting with an actual Nether Star or
// Grater still works exactly as the mod authors intended, this just adds a
// second, automation-friendly path alongside it.
ServerEvents.recipes(event => {
    let patched = 0

    // ---- (1) End's Delight: dragon egg cracking ----
    event.custom({
        type: 'farmersdelight:cutting',
        ingredients: [{ item: 'ends_delight:non_hatchable_dragon_egg' }],
        tool: { tag: 'c:tools/knife' },
        result: [
            { item: { count: 1, id: 'ends_delight:liquid_dragon_egg' } },
            { item: { count: 1, id: 'ends_delight:half_dragon_egg_shell' } },
        ],
    }).id('vanillaplusplus:food_cck_gap/crack_non_hatchable_dragon_egg_knife')
    patched++

    // ---- (2) ExtraDelight: 8 grater recipes ----
    const GRATER_RECIPES = [
        { id: 'grated_ginger', ingredients: [{ item: 'extradelight:peeled_ginger' }], result: [{ item: { count: 4, id: 'extradelight:grated_ginger' } }] },
        { id: 'grate_bread', ingredients: [{ tag: 'c:foods/bread' }], result: [{ item: { count: 4, id: 'extradelight:breadcrumbs' } }] },
        { id: 'grate_carrot', ingredients: [{ tag: 'c:crops/carrot' }], result: [{ item: { count: 4, id: 'extradelight:grated_carrot' } }] },
        { id: 'grate_garlic', ingredients: [{ item: 'extradelight:garlic_clove' }], result: [{ item: { count: 1, id: 'extradelight:grated_garlic' } }] },
        { id: 'grate_potato', ingredients: [{ tag: 'c:crops/potato' }], result: [{ item: { count: 4, id: 'extradelight:grated_potato' } }] },
        { id: 'lemon_zest_grater', ingredients: [{ tag: 'c:crops/lemon' }], result: [{ item: { count: 2, id: 'extradelight:lemon_zest' } }] },
        { id: 'lime_zest_grater', ingredients: [{ tag: 'c:crops/lime' }], result: [{ item: { count: 2, id: 'extradelight:lime_zest' } }] },
        { id: 'orange_zest_grater', ingredients: [{ tag: 'c:crops/orange' }], result: [{ item: { count: 2, id: 'extradelight:orange_zest' } }] },
    ]
    for (let i = 0; i < GRATER_RECIPES.length; i++) {
        let r = GRATER_RECIPES[i]
        event.custom({
            type: 'farmersdelight:cutting',
            ingredients: r.ingredients,
            tool: { tag: 'c:tools/knife' },
            result: r.result,
        }).id('vanillaplusplus:food_cck_gap/' + r.id + '_knife')
        patched++
    }

    console.info(`[vpp food_cck_gap_patch] added ${patched} knife-tool alternate farmersdelight:cutting recipe(s) so Create's Saw (via Central Kitchen's iron-knife impersonation) can automate the dragon-egg-cracking and all 8 grater recipes, closing the only 2 food-producing CCK Saw-automation gaps found across FD+ends-delight+extradelight's 222 combined cutting-board recipes. Originals left in place as manual-crafting alternatives.`)
})
