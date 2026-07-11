// GitHub issue #9: "Some tools are still craftable" (filed against v0.1.0 by
// the repo admin, reporter examples: Create-adjacent aluminum/lead/copper
// tools).
//
// ROOT CAUSE: blacksmithing.js (Phase 9's gear overhaul) and
// weapon_smithing.js (Epic Fight's Silent-Gear-gated smithing) only ever
// enumerated vanilla + Allthemodium + Epic Fight tool/weapon recipes via a
// hand-typed tier x type cross product (VANILLA_TOOL_TIERS x
// VANILLA_TOOL_TYPES, ALLTHEMODIUM_MATERIALS x ALLTHEMODIUM_SMITHING_TYPES,
// the 6 Epic Fight built-in tiers). Every OTHER mod shipping its own native
// tool/weapon recipes was never touched - exactly what the reporter hit.
//
// FIX: a systematic, pattern-based sweep instead of yet another hand-typed
// id list, so future mod additions stay covered without a repeat bug
// report. At boot, walk every recipe actually registered
// (event.forEachRecipe - javap-verified against this pack's installed
// kubejs-neoforge-2101.7.2-build.368.jar:
// RecipesKubeEvent.forEachRecipe(Context, RecipeFilter, Consumer<KubeRecipe>)),
// resolve each recipe's real output item via
// KubeRecipe.getOriginalRecipeResult() (works for any recipe type that
// implements the standard vanilla Recipe interface - shaped/shapeless/
// smithing_transform/mechanical_crafting/sized_upgrade_recipe all do), and
// remove any recipe whose output item's path matches a tool/weapon name
// pattern - unless the recipe's namespace or specific item id is on the
// exceptions lists below. This deliberately does NOT touch armor - that's
// already fully handled by blacksmithing.js's own vanilla armor tier
// removal and was outside the scope of this bug report.
//
// EXCEPTIONS RULING (ground-truthed against the actual installed jars,
// 2026-07-11 - see DECISIONS.md for the dated entry with full reasoning):
//
//   Namespace-exempt (whole mod, either the sanctioned route itself, or
//   already fully handled elsewhere so re-matching here would just be a
//   harmless no-op that muddies this script's own boot-log count):
//     - silentgear: the one sanctioned tool/weapon source this entire
//       design point exists to funnel players toward.
//     - vanillaplusplus / epicfight: weapon_smithing.js's own Silent-Gear-
//       gated Epic Fight replacement recipes, and Epic Fight's base-tier
//       recipes it removes - already handled there.
//     - allthemodium: already handled by blacksmithing.js's own
//       ALLTHEMODIUM_SMITHING_TYPES loop.
//     - farmersdelight / ends_delight / extradelight: DESIGN.md's food
//       overhaul (TODO.md item 9) explicitly tier-locked Farmer's
//       Delight's and End's Delight's knives (flint/iron/golden/diamond/
//       netherite, dragon egg shell/tooth, end stone, purpur) as
//       legitimate KITCHEN tools for the cutting-board/Saw-automation food
//       chain - priced and gated at Andesite/Brass/Precision Age alongside
//       spoons, a deliberate documented exception, not a gap. ExtraDelight's
//       "gingerbread_pickaxe"/"sugar_cookie_sword"/etc. are actually EDIBLE
//       FOOD ITEMS (tagged c:foods/cookie/*, part of the same ~820-item
//       food pool, baked via campfire/oven/smoking) that merely borrow a
//       tool's name/shape - not functional tools.
//
//   Item-exempt (specific ids, real tool-shaped name match but not an
//   actual player-progression tool/weapon):
//     - create:cardboard_sword: Create's own joke/novelty item (tooltip:
//       "Bonk. A mostly harmless, yet powerful weapon of choice.") -
//       cosmetic flavor text, not a progression tool.
//     - apothic_enchanting:pickaxe_tome: not a tool at all - a "Tome of
//       the Miners" ("Accepts pickaxe enchantments"), used within
//       Apotheosis/Apothic Enchanting's own gem-enchanting system.
//     - tfmg:oil_hammer / tfmg:pumpjack_hammer /
//       tfmg:pumpjack_hammer_connector / tfmg:large_pumpjack_hammer_connector:
//       TFMG oil-pumpjack MULTIBLOCK MACHINE components (3 of the 4 are
//       placeable blocks, confirmed via the jar's own blockstate files),
//       matched only by the "hammer" substring - not handheld tools.
//
//   Genuinely removed by this sweep (verified via a real boot + a
//   temporary per-id log, see DECISIONS.md's dated entry): TFMG aluminum/
//   lead axe/hoe/pickaxe/shovel/sword (10 - the reporter's own example;
//   TFMG's 5 steel tools ship conditionally DISABLED upstream as type
//   "minecraft:empty" and never register at all - the pre-existing
//   known-noise "Skipping recipe tfmg:..." baseline lines, so nothing to
//   remove there), Create Stuff & Additions brass/copper/zinc/rose_quartz/
//   experience/blazing tools + the Blazing Cleaver + the Portable Drill
//   (27 - also matches the reporter's "copper" example), Stellaris steel
//   axe/hoe/pickaxe/shovel/sword (5), AllTheOres bronze/copper/invar/iron/
//   platinum ore hammers (5 - a real tiered mining-tool ladder, the same
//   category of alternate progression this design forbids), Apotheosis'
//   own stone->iron->golden->diamond vanilla-tool smithing-upgrade ladder
//   (15 - a second, previously-missed bypass of blacksmithing.js's vanilla
//   tool removal, using Apotheosis' own smithing templates instead of
//   vanilla's), Apothic Enchanting's craftable Inert Trident + its
//   infusion into a REAL minecraft:trident (2 - a full crafting route to a
//   vanilla combat weapon that isn't even craftable in vanilla), Ars
//   Nouveau's Enchanter's Sword, Spell Bow and Spell Crossbow (4 recipes -
//   real combat weapons craftable outside Silent Gear; DESIGN.md's gear
//   overhaul Part 4 already redirected Ars Nouveau's mage ARMOR through
//   Silent Gear smithing, so its weapons being left native was the same
//   oversight class, not a documented exception - casting wands/books are
//   NOT touched, see below), Born in Chaos' 16 unique named combat weapons
//   (12 sword/axe/dagger/hammer/scythe pattern hits + shell_mace +
//   soul_cutlass + 2 summoning staffs; TODO.md item 6 already decided
//   "unique weapons/armor/charms stripped" from this mod's mob loot -
//   leaving their crafting recipes live, fed by the same mobs'
//   still-dropped crafting materials, was the actual hole left open),
//   vanilla's own minecraft:mace (1 - the 1.21 weapon blacksmithing.js's
//   pre-mace tier x type table never knew about), and Epic Fight's own
//   separate diamond->netherite smithing-template upgrade recipes
//   registered under "minecraft:netherite_<type>_smithing" (5 - a bypass
//   of weapon_smithing.js's own Silent-Gear-gated netherite tier,
//   discovered only by walking every recipe rather than trusting the
//   epicfight namespace alone to be exhaustive).
//
//   Deliberately NOT swept (rulings): wands (Ars Nouveau's casting wand/
//   dominion wand are the mage archetype's class mechanic, Building Wands'
//   are construction utilities - both already tier-locked where needed,
//   e.g. wands:netherite_wand at Precision Age); "drill"-named MACHINES
//   (create:mechanical_drill, createoreexcavation's vein-mining drill
//   components, stellaris:pumpjack_drill - kinetic machine parts, not
//   handheld tools; the one genuine handheld, create_sa:portable_drill,
//   is removed via EXTRA_REMOVE_RECIPE_IDS above); enchanting tomes
//   (apothic_enchanting:pickaxe_tome/bow_tome); ExtraDelight's decorative
//   ribbon_bow_* items (namespace-exempt anyway).

const TOOL_EXEMPT_NAMESPACES = [
    'silentgear', 'vanillaplusplus', 'epicfight', 'allthemodium',
    'farmersdelight', 'ends_delight', 'extradelight'
]

const TOOL_EXEMPT_ITEM_IDS = [
    'create:cardboard_sword',
    'apothic_enchanting:pickaxe_tome',
    'apothic_enchanting:bow_tome', // enchanting tome ("Accepts bow enchantments"), not a bow
    'tfmg:oil_hammer',
    'tfmg:pumpjack_hammer',
    'tfmg:pumpjack_hammer_connector',
    'tfmg:large_pumpjack_hammer_connector',
]

// Oddball removals the name pattern can't safely express: items that ARE
// genuine player tools/weapons but whose name token would drag in a pile
// of machine blocks if added to TOOL_NAME_RE wholesale.
//   - create_sa:portable_drill: a real HANDHELD mining gadget ("Can destroy
//     most known blocks", enchantable with Digging for 3x3 mining) - but
//     the "drill" token overwhelmingly names MACHINES in this pack
//     (create:mechanical_drill, createoreexcavation's 4 vein-mining drill
//     machine components, stellaris:pumpjack_drill), so it's removed by
//     explicit recipe id instead of by pattern.
const EXTRA_REMOVE_RECIPE_IDS = [
    'create_sa:portable_drill_recipe',
]

// Matches pickaxe/axe/shovel/hoe/sword/paxel/hammer/etc. as a whole
// underscore-delimited word segment, case-insensitive - deliberately loose
// so future mods stay covered; false positives are handled via the
// exceptions lists above and the structural-part guard below, not by
// narrowing this pattern.
const TOOL_NAME_RE = /(^|_)(pickaxe|axe|shovel|spade|hoe|sword|paxel|hammer|excavator|mattock|scythe|sickle|dagger|greatsword|longsword|spear|tachi|katana|knife|machete|cleaver|mace|cutlass|saber|sabre|staff|trident|bow|crossbow|battleaxe|warhammer|claymore|rapier|halberd|glaive)(s?)($|_)/i

// Extra structural-part guard, on top of the specific TFMG item-exempt
// list above: catches the general shape of multiblock-machine-component
// naming (connector/part/head/handle/template/blueprint pieces) so a
// future mod's own "whatever_hammer_connector"-style block doesn't need a
// hand-added exemption every time.
const STRUCTURAL_PART_RE = /(_connector|_part|_head|_handle|template|blueprint|schematic)$/i

ServerEvents.recipes(event => {
    let removedCount = 0
    let skippedCount = 0
    let removedByNamespace = {}

    event.forEachRecipe({}, recipe => {
        let recipeId = ''
        try {
            recipeId = recipe.getId()
        } catch (e) {
            skippedCount++
            return
        }
        let colonIndex = recipeId.indexOf(':')
        let namespace = colonIndex >= 0 ? recipeId.substring(0, colonIndex) : ''
        if (TOOL_EXEMPT_NAMESPACES.includes(namespace)) {
            return
        }

        let stack
        try {
            stack = recipe.getOriginalRecipeResult()
        } catch (e) {
            skippedCount++
            return
        }
        if (!stack || stack.isEmpty()) {
            return
        }

        let outputId
        try {
            outputId = String(stack.id)
        } catch (e) {
            skippedCount++
            return
        }
        if (!outputId || outputId === 'minecraft:air') {
            return
        }
        if (TOOL_EXEMPT_ITEM_IDS.includes(outputId)) {
            return
        }

        let itemPath = outputId.includes(':') ? outputId.substring(outputId.indexOf(':') + 1) : outputId
        if (STRUCTURAL_PART_RE.test(itemPath)) {
            return
        }
        if (!TOOL_NAME_RE.test(itemPath)) {
            return
        }

        event.remove({ id: recipeId })
        removedCount++
        removedByNamespace[namespace] = (removedByNamespace[namespace] || 0) + 1
    })

    for (const extraId of EXTRA_REMOVE_RECIPE_IDS) {
        event.remove({ id: extraId })
        removedCount++
        let extraNs = extraId.substring(0, extraId.indexOf(':'))
        removedByNamespace[extraNs] = (removedByNamespace[extraNs] || 0) + 1
    }

    // Per-namespace breakdown makes every future boot self-auditing: a NEW
    // namespace appearing here means a newly-added mod shipped craftable
    // tools and this sweep caught them (working as intended, but worth a
    // look at whether any of its matches deserve an exemption); a namespace
    // DISAPPEARING means a mod was removed or its recipes moved.
    let breakdown = Object.keys(removedByNamespace).sort().map(ns => `${ns}=${removedByNamespace[ns]}`).join(' ')
    // Sanity guard for the sanctioned route: if this count ever hits 0,
    // something upstream of this script broke Silent Gear's own recipes and
    // the pack has NO tool source at all - far worse than issue #9.
    let sgCount = event.countRecipes({ mod: 'silentgear' })
    console.info(`[vpp tool sweep / GitHub #9] removed ${removedCount} non-Silent-Gear tool/weapon recipe(s): ${breakdown}${skippedCount > 0 ? ` | ${skippedCount} recipe(s) skipped, output not resolvable` : ''} | silentgear recipes still registered: ${sgCount}`)
})
