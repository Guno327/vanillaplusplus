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
    {
        tierName: 'Andesite Age',
        materialName: 'an Andesite Alloy',
        why: "#70: Sophisticated Storage's barrel/chest/shulker tiers chain upward (iron -> gold -> diamond -> netherite), so gating the iron step gates everything above it. Its own Stack Upgrade Tier 1 has no natural gate at all (just logs), so it gets the same treatment. The portable basic_to_iron/copper_to_iron tier-upgrade items are a second, independent way to reach the same iron-tier result (applied to an existing container instead of crafted fresh), so they need the identical gate or they'd bypass it.",
        items: [
            'sophisticatedstorage:iron_barrel',
            'sophisticatedstorage:iron_chest',
            'sophisticatedstorage:iron_shulker_box',
            'sophisticatedstorage:stack_upgrade_tier_1',
            'sophisticatedstorage:basic_to_iron_tier_upgrade',
            'sophisticatedstorage:copper_to_iron_tier_upgrade',
        ],
    },
    {
        tierName: 'Brass Age',
        materialName: 'a Brass Ingot',
        why: "#70: Sophisticated Storage's gold step gates diamond/netherite above it, same chain-gate reasoning as the iron step. basic_to_gold/iron_to_gold tier-upgrade items need the same gate as gold_barrel/gold_chest/gold_shulker_box for the same reason iron's did. copper_to_gold_tier_upgrade is included even though it never touches copper directly in its own recipe - unpatched, its only ingredient is copper_to_iron_tier_upgrade (Andesite-gated), so it would let a rootborn-tier copper container jump straight to gold on Andesite Age materials alone, silently skipping this tier (found by reading the jar's own recipe json, not assumed).",
        items: [
            'sophisticatedstorage:gold_barrel',
            'sophisticatedstorage:gold_chest',
            'sophisticatedstorage:gold_shulker_box',
            'sophisticatedstorage:stack_upgrade_tier_3',
            'sophisticatedstorage:basic_to_gold_tier_upgrade',
            'sophisticatedstorage:iron_to_gold_tier_upgrade',
            'sophisticatedstorage:copper_to_gold_tier_upgrade',
        ],
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

    // --- Sophisticated Storage -> andesite_age / brass_age (#70) ---------
    // Base wood barrel/chest (sophisticatedstorage:barrel/chest, one
    // registry name shared by every wood color via a data component - not
    // touched here, stays this pack's Tier 0 baseline alongside Tom's
    // Storage's own dumb-storage tier). Copper tier is left on its stock
    // recipe too (copper is never locked in this pack, same as every other
    // copper item here).
    //
    // The tier ladder itself (copper -> iron -> gold -> diamond ->
    // netherite) is one shared recipe TYPE
    // (sophisticatedstorage:storage_tier_upgrade) across barrel/chest/
    // shulker_box, each upgrade consuming the previous tier's block as its
    // center ingredient - so, same as the backpack family above, gating the
    // iron and gold steps gates every tier above them; diamond and
    // netherite need no edit of their own (netherite_barrel's own recipe
    // already requires the diamond tier as an ingredient, which by then
    // already required gold, which already required iron - the chain does
    // the rest). event.custom() (not event.shaped()) is required for the
    // same reason it was for sophisticatedbackpacks:backpack_upgrade above:
    // this recipe type is what carries a storage block's CONTENTS into its
    // upgraded tier - a plain shaped recipe would delete them on upgrade.
    //
    // The stock jar also ships an alternate "upgrade directly from copper"
    // recipe for barrel and shulker_box (iron_barrel_from_copper_barrel,
    // iron_shulker_box_from_copper_shulker_box - no chest equivalent exists
    // in the jar) that would bypass the Andesite Alloy requirement below
    // entirely; both are removed so the iron step has exactly one path.
    const SOPH_STORAGE_TYPES = ['barrel', 'chest', 'shulker_box']

    SOPH_STORAGE_TYPES.forEach(type => {
        if (type !== 'chest') {
            event.remove({ id: `sophisticatedstorage:iron_${type}_from_copper_${type}` })
        }
        event.remove({ id: `sophisticatedstorage:iron_${type}` })
        event.custom({
            type: 'sophisticatedstorage:storage_tier_upgrade',
            category: 'misc',
            key: {
                I: { tag: 'c:ingots/iron' },
                A: { item: 'create:andesite_alloy' },
                S: { item: `sophisticatedstorage:${type}` }
            },
            pattern: [
                'IAI',
                'ISI',
                'III'
            ],
            result: { count: 1, id: `sophisticatedstorage:iron_${type}` }
        }).id(`vanillaplusplus:iron_${type}_andesite_tier`)

        event.remove({ id: `sophisticatedstorage:gold_${type}` })
        event.custom({
            type: 'sophisticatedstorage:storage_tier_upgrade',
            category: 'misc',
            key: {
                G: { tag: 'c:ingots/gold' },
                R: { item: 'create:brass_ingot' },
                S: { item: `sophisticatedstorage:iron_${type}` }
            },
            pattern: [
                'GRG',
                'GSG',
                'GGG'
            ],
            result: { count: 1, id: `sophisticatedstorage:gold_${type}` }
        }).id(`vanillaplusplus:gold_${type}_brass_tier`)
    })

    // Stack Upgrade Tier 1 (sophisticatedstorage's own, distinct item from
    // sophisticatedbackpacks:stack_upgrade_starter_tier above) has no
    // natural gate at all - stock recipe is just logs + an Upgrade Base -
    // so it gets the same Andesite Alloy treatment as that backpack item.
    // Tier 1 Plus/Tier 2 chain off Tier 1 as their own center ingredient
    // and need no edit. Tier 3 is this ladder's gold step (chains off
    // Tier 2), gated the same way as the barrel/chest/shulker gold step
    // above; Tier 4/5/Omega chain off Tier 3 and need no edit of their own.
    // Both keep their stock recipe TYPE (minecraft:crafting_shaped, unlike
    // the barrel/chest/shulker ladder above) since a stack upgrade item
    // carries no contents of its own to lose on re-craft.
    event.remove({ id: 'sophisticatedstorage:stack_upgrade_tier_1' })
    event.shaped('sophisticatedstorage:stack_upgrade_tier_1', [
        'LAL',
        'LBL',
        'LLL'
    ], {
        B: 'sophisticatedstorage:upgrade_base',
        L: '#minecraft:logs',
        A: 'create:andesite_alloy'
    }).id('vanillaplusplus:storage_stack_upgrade_tier_1_andesite_tier')

    event.remove({ id: 'sophisticatedstorage:stack_upgrade_tier_3' })
    event.shaped('sophisticatedstorage:stack_upgrade_tier_3', [
        'GRG',
        'GSG',
        'BGB'
    ], {
        B: '#c:storage_blocks/gold',
        G: '#c:ingots/gold',
        S: 'sophisticatedstorage:stack_upgrade_tier_2',
        R: 'create:brass_ingot'
    }).id('vanillaplusplus:storage_stack_upgrade_tier_3_brass_tier')

    // Sophisticated Storage also ships a second, independent way to reach
    // the same iron/gold tiers: portable "tier upgrade" items
    // (basic_to_iron_tier_upgrade etc) that get applied to an EXISTING
    // container in the mod's own UI instead of being crafted as a whole new
    // block via the storage_tier_upgrade recipes above. Their own recipes
    // use plain minecraft:crafting_shaped (no contents to preserve - they
    // carry no inventory of their own), and left unpatched they bypass the
    // gate above entirely: basic_to_iron_tier_upgrade/copper_to_iron_tier_
    // upgrade need just iron ingots, and applying either to a rootborn-tier
    // basic/copper container reaches iron tier with no Andesite Age
    // material at all. basic_to_gold_tier_upgrade/iron_to_gold_tier_upgrade
    // are the matching gold-step gate.
    //
    // copper_to_gold_tier_upgrade needs the same Brass Ingot treatment for a
    // less obvious reason, found by reading its actual recipe json rather
    // than assuming the ladder is symmetric: its own ingredient is
    // copper_to_iron_tier_upgrade (an item, gated at Andesite Age above),
    // NOT a gold-tier source or anything Brass-Age-gated. Left alone, a
    // player could craft copper_to_iron_tier_upgrade (Andesite Age), then
    // copper_to_gold_tier_upgrade straight after it using nothing but a
    // plain gold ingot, and apply the result to a still-rootborn-tier copper
    // container to reach gold tier without ever touching Brass Age -
    // silently undercutting Refined Storage's own placement there. diamond/
    // netherite-reaching upgrade items (basic_to_diamond, gold_to_diamond,
    // *_to_netherite, etc) all consume one of the five items gated below as
    // their own ingredient (or, for gold_to_diamond/diamond_to_netherite,
    // are only useful applied to a gold/diamond-tier container that itself
    // now requires this gate), so none of them need an edit of their own.
    const SOPH_STORAGE_UPGRADE_ITEMS = [
        { id: 'sophisticatedstorage:basic_to_iron_tier_upgrade', pattern: ['III', 'ILI', 'III'], key: { I: { tag: 'c:ingots/iron' }, L: { item: 'minecraft:lever' } }, tierLetter: 'A', tier: 'create:andesite_alloy', suffix: 'andesite_tier' },
        { id: 'sophisticatedstorage:copper_to_iron_tier_upgrade', pattern: [' I ', 'ILI', ' I '], key: { I: { tag: 'c:ingots/iron' }, L: { item: 'minecraft:lever' } }, tierLetter: 'A', tier: 'create:andesite_alloy', suffix: 'andesite_tier' },
        { id: 'sophisticatedstorage:basic_to_gold_tier_upgrade', pattern: ['GGG', 'GTG', 'GGG'], key: { G: { tag: 'c:ingots/gold' }, T: { item: 'sophisticatedstorage:basic_to_iron_tier_upgrade' } }, tierLetter: 'R', tier: 'create:brass_ingot', suffix: 'brass_tier' },
        { id: 'sophisticatedstorage:iron_to_gold_tier_upgrade', pattern: ['GGG', 'GLG', 'GGG'], key: { G: { tag: 'c:ingots/gold' }, L: { item: 'minecraft:lever' } }, tierLetter: 'R', tier: 'create:brass_ingot', suffix: 'brass_tier' },
        { id: 'sophisticatedstorage:copper_to_gold_tier_upgrade', pattern: ['GGG', 'GTG', 'GGG'], key: { G: { tag: 'c:ingots/gold' }, T: { item: 'sophisticatedstorage:copper_to_iron_tier_upgrade' } }, tierLetter: 'R', tier: 'create:brass_ingot', suffix: 'brass_tier' },
    ]
    SOPH_STORAGE_UPGRADE_ITEMS.forEach(entry => {
        event.remove({ id: entry.id })
        let newPattern = [entry.pattern[0].replace(/[A-Z]/, entry.tierLetter), entry.pattern[1], entry.pattern[2]]
        let newKey = Object.assign({}, entry.key)
        newKey[entry.tierLetter] = { item: entry.tier }
        event.custom({
            type: 'minecraft:crafting_shaped',
            category: 'misc',
            pattern: newPattern,
            key: newKey,
            result: { count: 1, id: entry.id }
        }).id('vanillaplusplus:' + entry.id.split(':')[1] + '_' + entry.suffix)
    })

    // --- Sophisticated Storage "double chest" upgrades -> andesite_age /
    // brass_age (#127, GAP CONFIRMED LIVE by the #61 audit) ----------------
    // A THIRD, independent path to the same iron/gold/diamond chest tiers,
    // missed by #70: sophisticatedstorage:double_iron_chest/double_gold_
    // chest/double_diamond_chest upgrade a plain sophisticatedstorage:chest
    // (or, for double_iron_chest_from_copper_chest, a copper_chest) straight
    // into the double-wide chest variant using only that tier's plain metal
    // ingot - no Andesite Alloy/Brass Ingot anywhere (checked against the
    // jar's own recipe json, not assumed - the #70 postmortem's exact
    // failure mode, "one crafting route per gated item", recurring one
    // recipe family later). Barrels/shulker boxes have no double-container
    // equivalent so aren't affected. double_diamond_chest chains off
    // gold_chest (either recipe reaching it) and needs no edit of its own,
    // same chain-gate reasoning as the rest of this file; double_copper_
    // chest and double_netherite_chest are untouched for the same reason
    // copper/netherite never need one elsewhere in this ladder.
    event.remove({ id: 'sophisticatedstorage:double_iron_chest' })
    event.custom({
        type: 'sophisticatedstorage:double_chest_tier_upgrade',
        category: 'misc',
        key: {
            B: { tag: 'c:storage_blocks/iron' },
            I: { tag: 'c:ingots/iron' },
            S: { item: 'sophisticatedstorage:chest' },
            A: { item: 'create:andesite_alloy' }
        },
        pattern: [
            'IAI',
            'ISI',
            'IBI'
        ],
        result: { count: 1, id: 'sophisticatedstorage:iron_chest' }
    }).id('vanillaplusplus:double_iron_chest_andesite_tier')

    event.remove({ id: 'sophisticatedstorage:double_iron_chest_from_copper_chest' })
    event.custom({
        type: 'sophisticatedstorage:double_chest_tier_upgrade',
        category: 'misc',
        key: {
            I: { tag: 'c:ingots/iron' },
            S: { item: 'sophisticatedstorage:copper_chest' },
            A: { item: 'create:andesite_alloy' }
        },
        pattern: [
            'IAI',
            'ISI',
            'III'
        ],
        result: { count: 1, id: 'sophisticatedstorage:iron_chest' }
    }).id('vanillaplusplus:double_iron_chest_from_copper_chest_andesite_tier')

    event.remove({ id: 'sophisticatedstorage:double_gold_chest' })
    event.custom({
        type: 'sophisticatedstorage:double_chest_tier_upgrade',
        category: 'misc',
        key: {
            G: { tag: 'c:ingots/gold' },
            B: { tag: 'c:storage_blocks/gold' },
            S: { item: 'sophisticatedstorage:iron_chest' },
            R: { item: 'create:brass_ingot' }
        },
        pattern: [
            'GRG',
            'GSG',
            'GBG'
        ],
        result: { count: 1, id: 'sophisticatedstorage:gold_chest' }
    }).id('vanillaplusplus:double_gold_chest_brass_tier')

    // --- Refined Storage's core network chain -> brass_age (#127, GAP
    // CONFIRMED LIVE by the #61 audit) --------------------------------------
    // #49's dimension-travel removal (Nether open from world start) plus
    // diamond never being recipe-gated in this pack means RS's own Nether
    // Quartz + Advanced Processor requirement no longer implies Brass Age -
    // controller/disk_drive/grid (and everything else built from it) had NO
    // tier material anywhere in their recipe chains, verified against the
    // pinned jar's own recipe jsons. All three (plus 21 further RS block
    // recipes - autocrafter, storage blocks, interface, wireless_transmitter,
    // relay, etc, checked against the jar) share exactly one common
    // ingredient: refinedstorage:machine_casing. Gating that single
    // chokepoint, the same "gate the chain's first crossing" pattern used
    // for Sophisticated Backpacks/Storage above, closes the whole family
    // with one edit instead of patching each block recipe individually.
    // Original recipe fills the full 3x3 with quartz_enriched_iron around a
    // plain c:stones center; the center is swapped for the tier material
    // (stone is trivial and ungated everywhere else in this pack, so
    // dropping it costs nothing) - same "material replaces a plain filler
    // slot" shape-preserving convention as warp_stone's netherite center
    // above.
    event.remove({ id: 'refinedstorage:machine_casing' })
    event.shaped('refinedstorage:machine_casing', [
        'EEE',
        'EAE',
        'EEE'
    ], {
        E: 'refinedstorage:quartz_enriched_iron',
        A: 'create:brass_ingot'
    }).id('vanillaplusplus:machine_casing_brass_tier')

    // --- create:brass_casing -> the LITERAL brass ingot, not the tag
    // (#127, GAP CONFIRMED LIVE by the #61 audit) ---------------------------
    // create:railway_casing (and everything built from it, including
    // create:track_station) is only reachable through create:brass_casing,
    // whose own two recipes (from_log/from_wood) key off the tag
    // c:ingots/brass rather than the literal create:brass_ingot item.
    // AllTheOres registers its own alltheores:brass_ingot into that same
    // common tag via a plain from-dust recipe with no tier material of its
    // own, so a player can reach railway_casing/track_station with zero
    // Create-brass in their inventory at all - a real cross-mod bypass of
    // the Brass Age gate. Fixed at the narrowest point: re-author these two
    // recipes to require the literal create:brass_ingot item instead of the
    // tag, rather than gating alltheores:brass_ingot itself (which would
    // reach into AllTheOres' whole brass sub-economy - gears, plates, rods,
    // blocks - for a bypass that only actually matters here). Anyone still
    // wants to use AllTheOres brass for its own tools/gear/etc is unaffected;
    // only this one Create recipe stops accepting it as a substitute.
    event.remove({ id: 'create:item_application/brass_casing_from_log' })
    event.custom({
        type: 'create:item_application',
        ingredients: [
            { tag: 'c:stripped_logs' },
            { item: 'create:brass_ingot' }
        ],
        results: [{ id: 'create:brass_casing' }]
    }).id('vanillaplusplus:brass_casing_from_log_true_brass_tier')

    event.remove({ id: 'create:item_application/brass_casing_from_wood' })
    event.custom({
        type: 'create:item_application',
        ingredients: [
            { tag: 'c:stripped_woods' },
            { item: 'create:brass_ingot' }
        ],
        results: [{ id: 'create:brass_casing' }]
    }).id('vanillaplusplus:brass_casing_from_wood_true_brass_tier')
})
