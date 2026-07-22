// JEI "how do I get this?" info pages for everything the PACK itself changed
// (GitHub #57). The info-mod wave added alongside this file (JER, Advanced
// Loot Info, JEI WorldGen, Just Enough Breeding/Professions/Effects,
// Enchantment Descriptions) covers what the GAME knows: ore distribution, loot
// tables, breeding, trades, effects. None of them can know what this pack did
// to its own recipes - and that is exactly where a player hits a dead end:
//
//   - Look up minecraft:iron_pickaxe. tool_consolidation_sweep.js (#9) deleted
//     every vanilla and modded tool/weapon recipe to funnel players toward
//     Silent Gear, so JEI shows an item with NO recipe and no hint that Silent
//     Gear is the answer. Silent Gear's own JEI plugin (SGearJeiPlugin, with
//     gear-crafting/alloy/grader/salvage categories) documents the Silent Gear
//     side perfectly - nothing pointed AT it from the item you looked up.
//   - Look up waystones:warp_stone. Its recipe now demands a netherite ingot
//     because tier_gating.js put it there (#49), with nothing saying why.
//   - Look up create:andesite_alloy. Picking one up grants the andesite_age
//     stage, which gates quests - invisible without an info page.
//   - Look up alltheores:zinc_ingot. dedup.js unified it out of c:ingots/zinc;
//     the item still exists but nothing consumes it, which reads as a bug.
//
// KubeJS's own recipe-viewer bridge carries all four. RecipeViewerEvents
// .addInformation is posted with ScriptType.SERVER (javap-confirmed against
// this pack's kubejs-neoforge-2101.7.2-build.368.jar: recipe/viewer/server/
// ItemData posts RecipeViewerEvents.ADD_INFORMATION with ScriptType.SERVER and
// a ServerAddItemInformationKubeEvent, synced from there to the client's
// recipe viewer) - so this belongs in server_scripts, in the SAME shared Rhino
// scope as the tables it reads. That is the design point: three of the four
// lists below are read from the script that owns the behaviour rather than
// hand-copied, so the in-game explanation cannot drift from what the pack
// actually does. selftest.js asserts the wiring.

// Mirrors dedup.js's per-metal tag removals. Unlike the other three sources
// this one IS hand-maintained: dedup.js expresses itself as individual
// event.remove(tag, item) calls with no list to read, and inventing one there
// purely for this file would be a bigger change to a working script than the
// duplication is worth. Declared before the event that reads it, kept in the
// same file as its consumer, and covered by selftest.js.
const JEI_DEDUP_REDIRECTS = [
    {
        metal: 'zinc',
        canonical: 'create:zinc_ingot',
        canonicalName: "Create's zinc",
        deprecated: ['alltheores:zinc_ingot', 'alltheores:zinc_nugget', 'alltheores:zinc_block', 'alltheores:raw_zinc', 'alltheores:raw_zinc_block'],
    },
    {
        metal: 'aluminum',
        canonical: 'tfmg:aluminum_ingot',
        canonicalName: "TFMG's aluminum",
        deprecated: ['alltheores:aluminum_ingot', 'alltheores:aluminum_nugget', 'alltheores:aluminum_block', 'alltheores:aluminum_plate'],
    },
    {
        metal: 'lead',
        canonical: 'tfmg:lead_ingot',
        canonicalName: "TFMG's lead",
        deprecated: ['alltheores:lead_ingot', 'alltheores:lead_nugget', 'alltheores:lead_block', 'alltheores:raw_lead', 'alltheores:raw_lead_block', 'alltheores:lead_plate'],
    },
    {
        metal: 'nickel',
        canonical: 'tfmg:nickel_ingot',
        canonicalName: "TFMG's nickel",
        deprecated: ['alltheores:nickel_ingot', 'alltheores:nickel_nugget', 'alltheores:nickel_block'],
    },
    {
        metal: 'steel',
        canonical: 'tfmg:steel_ingot',
        canonicalName: "TFMG's steel",
        deprecated: ['stellaris:steel_ingot', 'stellaris:steel_block'],
    },
]

// Plain top-level function so selftest.js can call it with a recording stub
// instead of waiting for a real JEI sync - same testability pattern as
// progression_stage_bridge.js's psbApply* functions. Returns the number of
// info pages added, and takes the event so the stub can capture them.
function jeiAddPackInfo(event) {
    let pages = 0

    // --- 1. Tools/weapons whose recipes the consolidation sweep removed ---
    // Read straight from tool_consolidation_sweep.js's own removal pass, so
    // this covers every mod it strips - including mods added later, which a
    // hand-typed list would silently miss.
    if (typeof TCS_REMOVED_TOOL_ITEMS !== 'undefined') {
        for (let i = 0; i < TCS_REMOVED_TOOL_ITEMS.length; i++) {
            event.add(TCS_REMOVED_TOOL_ITEMS[i], [
                Text.gold('Not craftable directly in Vanilla++.'),
                Text.gray('Tools and weapons are built with Silent Gear: assemble a rod,'),
                Text.gray('head and binding at a Gear Crafting Station, which lets you pick'),
                Text.gray('the material and carry its traits.'),
                Text.darkGray('Search JEI for "Gear Crafting" to see the station and its recipes.'),
                Text.darkGray('Epic Fight weapon types have their own Silent-Gear-gated smithing'),
                Text.darkGray('recipes - look the weapon itself up to see them.'),
            ])
            pages++
        }
    }

    // --- 2. Recipes this pack re-gated behind a tier material (#49) -------
    // Table lives in tier_gating.js, next to the recipes it describes.
    if (typeof TG_TIER_INFO !== 'undefined') {
        for (let i = 0; i < TG_TIER_INFO.length; i++) {
            let entry = TG_TIER_INFO[i]
            for (let j = 0; j < entry.items.length; j++) {
                event.add(entry.items[j], [
                    Text.gold('Tier-gated: ' + entry.tierName),
                    Text.gray('Vanilla++ adds ' + entry.materialName + ' to this recipe so it stays'),
                    Text.gray('behind ' + entry.tierName + ' instead of being craftable on day one.'),
                    Text.darkGray(entry.why),
                ])
                pages++
            }
        }
    }

    // --- 3. Items that grant a progression stage -------------------------
    // Read from progression_stage_bridge.js's own trigger table.
    if (typeof PSB_ITEM_STAGE_TRIGGERS !== 'undefined') {
        for (let i = 0; i < PSB_ITEM_STAGE_TRIGGERS.length; i++) {
            let trigger = PSB_ITEM_STAGE_TRIGGERS[i]
            for (let j = 0; j < trigger.items.length; j++) {
                event.add(trigger.items[j], [
                    Text.gold('Progression trigger'),
                    Text.gray('Obtaining this grants the "' + trigger.stage + '" stage, which'),
                    Text.gray('advances the quest book and raises nearby mob difficulty.'),
                    Text.darkGray('Granted automatically within a second of it entering your inventory.'),
                ])
                pages++
            }
        }
    }

    // --- 4. Ore variants this pack unified away --------------------------
    // dedup.js removes these from their c:* tags so recipes resolve to one
    // canonical item per metal. The deduplicated item still exists (worldgen
    // in dimensions the canonical mod does not cover still produces some of
    // them) but nothing consumes it, which looks like a bug from inside JEI.
    for (let i = 0; i < JEI_DEDUP_REDIRECTS.length; i++) {
        let entry = JEI_DEDUP_REDIRECTS[i]
        for (let j = 0; j < entry.deprecated.length; j++) {
            event.add(entry.deprecated[j], [
                Text.gold('Duplicate removed by this pack'),
                Text.gray('Vanilla++ unifies ' + entry.metal + ' on ' + entry.canonicalName + '.'),
                Text.gray('This variant is no longer used by any recipe - look up'),
                Text.gray(entry.canonical + ' instead.'),
            ])
            pages++
        }
    }

    return pages
}

RecipeViewerEvents.addInformation('item', event => {
    try {
        let pages = jeiAddPackInfo(event)
        console.info('[vpp jei_info] added ' + pages + ' pack-specific JEI info page(s)')
    } catch (e) {
        console.error('[vpp jei_info] failed to add pack info pages: ' + e)
    }
})
