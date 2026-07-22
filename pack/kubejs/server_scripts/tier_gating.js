// Material tier gating - the replacement for ProgressiveStages' item locks
// (GitHub #49, owner decision 2026-07-22).
//
// WHY THIS FILE EXISTS. Until #49 this pack gated progression twice: recipes
// needed the right materials AND ProgressiveStages held a per-player lock list
// (pack/config/ProgressiveStages/*.toml) that refused the craft/use/pickup
// outright. That mod is gone - its JEI plugin fed its own ingredient-refresh
// notifications back into itself and froze every client (see DECISIONS.md) -
// and progression is now gated by ingredients alone: an item is reachable
// exactly when its ingredient chain is reachable.
//
// Most of the old lock list needed nothing to survive that change, which is
// why this file is short. Create/TFMG/Stellaris/AllTheModium chains gate
// themselves (brass needs zinc, railway casing needs brass, a rocket needs
// steel); Refined Storage gates itself through its own basic -> improved ->
// advanced processor chain (verified: refinedstorage:autocrafter needs an
// advanced_processor, wireless_transmitter needs one too, 16k_storage_part
// needs an improved_processor); and several families were already re-authored
// by this pack's own recipe scripts, whose gates are unaffected -
// weapon_smithing.js (Epic Fight weapons -> tier raw material), storage.js
// (Tom's Storage, deliberately pulled DOWN to iron tier), ars_nouveau_armor.js
// (robes -> enchanting apparatus), tick_accelerator.js (Time in a Bottle).
//
// What remains are the families whose vanilla recipes use only early
// materials, so the lock was the only thing holding them back. Each gets ONE
// ingredient from its intended tier, keeping the original recipe shape and
// type. The tier materials used here are this pack's own tier markers - the
// same items progression_stage_bridge.js grants stages from:
//
//     andesite_age   -> create:andesite_alloy
//     brass_age      -> create:brass_ingot
//     induction_age  -> minecraft:netherite_ingot
//
// Tier assignments come from the pre-#49 lock lists, preserved as pack design
// data in pack/progression/*.toml - that file set is still the tier manifest
// (scripts/gen_economy.py prices off it), it just no longer drives a runtime
// lock. Recipe ids are namespaced vanillaplusplus: like storage.js's, so a
// `/kubejs hand` lookup in game points at this file rather than the mod's.

// Read by jei_info.js to explain each gate in JEI (#57). Kept here, beside
// the recipes it describes, so an edit below without a matching entry here is
// obvious in review; selftest.js asserts every id listed is one this file
// actually re-authors.
const TG_TIER_INFO = [
    {
        tierName: 'Induction Age',
        materialName: 'a Netherite Ingot',
        why: 'Every waystone, sharestone and portstone recipe consumes a Warp Stone, so gating the stone gates teleportation as a whole.',
        items: ['waystones:warp_stone'],
    },
    {
        tierName: 'Andesite Age',
        materialName: 'an Andesite Alloy',
        why: 'Backpack and stack-upgrade tiers chain upward, so gating the early step gates everything above it.',
        items: ['sophisticatedbackpacks:iron_backpack', 'sophisticatedbackpacks:stack_upgrade_starter_tier'],
    },
    {
        tierName: 'Brass Age',
        materialName: 'a Brass Ingot',
        why: 'Backpack and stack-upgrade tiers chain upward, so gating this step gates everything above it.',
        items: ['sophisticatedbackpacks:gold_backpack', 'sophisticatedbackpacks:stack_upgrade_tier_2'],
    },
    {
        tierName: 'Andesite Age',
        materialName: 'an Andesite Alloy',
        why: 'Stock wand recipes are one ingot plus two sticks, so the ingot alone decided the tier.',
        items: ['wands:copper_wand', 'wands:iron_wand', 'wands:magic_bag_1'],
    },
    {
        tierName: 'Brass Age',
        materialName: 'a Brass Ingot',
        why: 'Stock wand recipes are one ingot plus two sticks, so the ingot alone decided the tier.',
        items: ['wands:diamond_wand', 'wands:magic_bag_2'],
    },
    {
        tierName: 'Brass Age',
        materialName: 'a Brass Ingot',
        why: "The base Storage Terminal stays at iron tier on purpose - it is this pack's Tier 1 storage - so only the upper terminals are gated.",
        items: ['toms_storage:crafting_terminal', 'toms_storage:wireless_terminal'],
    },
    {
        tierName: 'Andesite Age',
        materialName: 'an Andesite Alloy',
        why: 'Higher drill tiers chain off this one, so gating it keeps the whole family behind Andesite Age.',
        items: ['createoreexcavation:drill'],
    },
]

ServerEvents.recipes(event => {
    // --- Waystones -> induction_age -------------------------------------
    // Its own recipes use nothing this pack tiers (amethyst + ender pearl +
    // emerald), which is exactly why the manifest recorded its gating as
    // "entirely explicit ProgressiveStages item locks at induction_age".
    //
    // ONE edit covers the whole 10-id family: every waystone/sharestone/
    // portstone block recipe in the jar consumes waystones:warp_stone
    // (checked across all 54 of its recipe jsons). The three scrolls do NOT,
    // but they are inert without a placed waystone to bind or return to, so
    // gating the stone gates the feature. Netherite in the middle slot -
    // induction_age is this pack's automation ceiling before the space
    // gateway, and netherite_ingot is already its stage trigger item.
    event.remove({ output: 'waystones:warp_stone' })
    event.shaped('waystones:warp_stone', [
        'DED',
        'ENE',
        'DED'
    ], {
        D: 'minecraft:amethyst_shard',
        E: 'minecraft:ender_pearl',
        N: 'minecraft:netherite_ingot'
    }).id('vanillaplusplus:warp_stone_induction_tier')

    // --- Sophisticated Backpacks -> andesite_age / brass_age -------------
    // The backpack tiers chain (backpack -> iron -> gold -> diamond ->
    // netherite), so gating the iron and gold steps gates everything above
    // them; diamond/netherite then need no edit of their own. Same for the
    // stack upgrades (starter -> tier_1 -> tier_2 -> ...).
    //
    // These keep type sophisticatedbackpacks:backpack_upgrade via
    // event.custom() rather than being re-authored as plain shaped recipes:
    // that custom type is what carries the old backpack's stored CONTENTS
    // into the upgraded one. A vanilla shaped recipe would quietly delete a
    // player's inventory on upgrade.
    event.remove({ output: 'sophisticatedbackpacks:iron_backpack' })
    event.custom({
        type: 'sophisticatedbackpacks:backpack_upgrade',
        category: 'misc',
        pattern: [
            'IAI',
            'IBI',
            'III'
        ],
        key: {
            B: { item: 'sophisticatedbackpacks:backpack' },
            I: { tag: 'c:ingots/iron' },
            A: { item: 'create:andesite_alloy' }
        },
        result: { count: 1, id: 'sophisticatedbackpacks:iron_backpack' }
    }).id('vanillaplusplus:iron_backpack_andesite_tier')

    event.remove({ output: 'sophisticatedbackpacks:gold_backpack' })
    event.custom({
        type: 'sophisticatedbackpacks:backpack_upgrade',
        category: 'misc',
        pattern: [
            'GRG',
            'GBG',
            'GGG'
        ],
        key: {
            B: { item: 'sophisticatedbackpacks:iron_backpack' },
            G: { tag: 'c:ingots/gold' },
            R: { item: 'create:brass_ingot' }
        },
        result: { count: 1, id: 'sophisticatedbackpacks:gold_backpack' }
    }).id('vanillaplusplus:gold_backpack_brass_tier')

    event.remove({ output: 'sophisticatedbackpacks:stack_upgrade_starter_tier' })
    event.shaped('sophisticatedbackpacks:stack_upgrade_starter_tier', [
        'CAC',
        'CBC',
        'CCC'
    ], {
        B: 'sophisticatedbackpacks:upgrade_base',
        C: '#c:storage_blocks/copper',
        A: 'create:andesite_alloy'
    }).id('vanillaplusplus:stack_upgrade_starter_andesite_tier')

    event.remove({ output: 'sophisticatedbackpacks:stack_upgrade_tier_2' })
    event.shaped('sophisticatedbackpacks:stack_upgrade_tier_2', [
        'GRG',
        'GSG',
        'GGG'
    ], {
        G: '#c:storage_blocks/gold',
        S: 'sophisticatedbackpacks:stack_upgrade_tier_1',
        R: 'create:brass_ingot'
    }).id('vanillaplusplus:stack_upgrade_tier_2_brass_tier')

    // --- Building Wands -> andesite_age / brass_age ----------------------
    // Stock recipes are literally "one ingot + two sticks", with the ingot
    // being the only thing separating the copper/iron/diamond tiers. The
    // netherite wand and magic_bag_3 need no edit - netherite gates itself.
    // The tier material goes in a slot the original left empty, so the
    // recognisable diagonal-wand shape survives.
    const WAND_TIERS = [
        { id: 'wands:copper_wand', tip: 'minecraft:copper_ingot', tier: 'create:andesite_alloy', suffix: 'andesite' },
        { id: 'wands:iron_wand', tip: 'minecraft:iron_ingot', tier: 'create:andesite_alloy', suffix: 'andesite' },
        { id: 'wands:diamond_wand', tip: 'minecraft:diamond', tier: 'create:brass_ingot', suffix: 'brass' },
    ]
    WAND_TIERS.forEach(wand => {
        event.remove({ output: wand.id })
        event.shaped(wand.id, [
            'A #',
            ' / ',
            '/  '
        ], {
            '#': wand.tip,
            '/': 'minecraft:stick',
            A: wand.tier
        }).id('vanillaplusplus:' + wand.id.split(':')[1] + '_' + wand.suffix + '_tier')
    })

    // Magic bags: one rabbit hide swapped for the tier material, same shape.
    const MAGIC_BAG_TIERS = [
        { id: 'wands:magic_bag_1', dye: 'minecraft:purple_dye', gem: 'minecraft:ender_pearl', tier: 'create:andesite_alloy', suffix: 'andesite' },
        { id: 'wands:magic_bag_2', dye: 'minecraft:orange_dye', gem: 'minecraft:ender_eye', tier: 'create:brass_ingot', suffix: 'brass' },
    ]
    MAGIC_BAG_TIERS.forEach(bag => {
        event.remove({ output: bag.id })
        event.shaped(bag.id, [
            '#P#',
            'RER',
            'RAR'
        ], {
            '#': 'minecraft:string',
            P: bag.dye,
            R: 'minecraft:rabbit_hide',
            E: bag.gem,
            A: bag.tier
        }).id('vanillaplusplus:' + bag.id.split(':')[1] + '_' + bag.suffix + '_tier')
    })

    // --- Tom's Storage upper tiers -> brass_age --------------------------
    // storage.js deliberately pulls the BASE terminal down to iron tier (it
    // is this pack's Tier 1 "dumb storage"); these two upper-tier terminals
    // are the ones the old lock list put at brass_age, and their stock
    // recipes are diamond/plank-cheap. Not touched by storage.js - see its
    // header, which only patches inventory_connector + storage_terminal.
    event.remove({ output: 'toms_storage:crafting_terminal' })
    event.shaped('toms_storage:crafting_terminal', [
        'cRc',
        'dtd',
        'cdc'
    ], {
        d: '#c:gems/diamond',
        c: 'minecraft:crafting_table',
        t: 'toms_storage:storage_terminal',
        R: 'create:brass_ingot'
    }).id('vanillaplusplus:crafting_terminal_brass_tier')

    event.remove({ output: 'toms_storage:wireless_terminal' })
    event.shaped('toms_storage:wireless_terminal', [
        'RCP',
        'aGg',
        'PEP'
    ], {
        P: '#minecraft:planks',
        a: 'minecraft:spyglass',
        C: 'minecraft:comparator',
        E: '#c:ender_pearls',
        G: '#c:dusts/glowstone',
        g: '#c:glass_blocks/colorless',
        R: 'create:brass_ingot'
    }).id('vanillaplusplus:wireless_terminal_brass_tier')

    // --- Create Ore Excavation -> andesite_age ---------------------------
    // A Create addon whose entry-level drill is plain iron. Its higher tiers
    // (diamond/netherite drill, drilling machine, extractor) chain off this
    // drill or off materials that already gate themselves, so this one edit
    // is enough to keep the family behind Andesite Age.
    event.remove({ output: 'createoreexcavation:drill' })
    event.shaped('createoreexcavation:drill', [
        'bA ',
        'ibi',
        ' ii'
    ], {
        b: '#c:storage_blocks/iron',
        i: '#c:ingots/iron',
        A: 'create:andesite_alloy'
    }).id('vanillaplusplus:ore_excavation_drill_andesite_tier')
})
