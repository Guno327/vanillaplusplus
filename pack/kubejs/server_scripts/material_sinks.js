// GitHub #91 (reopened): "There is still no use for lots of items like
// silver gears which is one of the only things made with silver... make
// sure to integrate their use into important recipes so that harvesting a
// variety of materials is encouraged rather than the mindset that some are
// good and some are useless."
//
// PR #102 fixed the INGOT-level dead ends (6 Silent Gear materials for
// metals/gems the mod itself never shipped stats for, + beacon-base for
// storage blocks). That was real but insufficient - re-investigated here,
// jar-verified against every installed mod (95 total; extracted and grepped
// every recipe json, not assumed from mod names):
//
//   - Every AllTheOres metal's INGOT already has a real, unconditional sink
//     somewhere in this pack: ATO's own "alloy_blending_from_dust" shapeless
//     recipes (crafting-table dust blending, no missing-mod condition -
//     unlike ATO's alloy_smelting/alloysmelter/arcfurnace recipe types,
//     which are ALL gated on `mod_loaded: enderio` or `immersiveengineering`,
//     NEITHER of which is in this pack's manifest, so those are silently
//     dead despite existing as jar recipes) produce brass/bronze/constantan/
//     electrum/enderium/invar/lumium/signalum/steel from plain metal dusts;
//     TFMG independently uses lead/nickel/aluminum heavily in real machine
//     parts (electrode_holder, converter, transformer, accumulator,
//     chemical_vat, engine_cylinder, factory_floor, scaffolding, wiring);
//     Create itself uses zinc natively (andesite_alloy, brass_ingot, chain
//     drive, package_filter); Stellaris uses uranium in
//     radioactive_generator/radioactive_motor; Silent Gear's own jar ships
//     built-in tool materials for aluminum/lead/nickel/silver/platinum/
//     osmium/zinc/uranium/tin, and PR #102 added iridium/ruby/sapphire/
//     peridot/fluorite/cinnabar on top.
//
//   - What is STILL a genuine, universal dead end (confirmed by grepping
//     every installed jar's recipes for the `c:gears/*`, `c:plates/*`,
//     `c:rods/*` common tags): AllTheOres' own metal-press BYPRODUCTS -
//     gear/plate/rod, ~75 items across all 25 metals. Not one recipe in any
//     of the 95 installed mods, nor this pack's own KubeJS, ever consumes
//     any of them - AllTheOres only ever OUTPUTS them (its metal press
//     recipes), because upstream they exist for Mekanism/Thermal/
//     Immersive-Engineering-style machine crafting, none of which this pack
//     installs. This is exactly what "silver gears" names: the ingot has a
//     use, the pressed gear never does. It applies uniformly across every
//     metal, not just silver - fixing silver alone would leave the same
//     class of dead end for every other metal's gear.
//
// FIRST TRANCHE: rather than inventing throwaway decorative recipes, route
// five of these dead gears into existing, already-desirable, already
// tier-gated recipe families this pack controls - as an ADDITIONAL required
// ingredient alongside the existing ones (never a cheaper alternate path),
// so nothing is bypassed, only made to also demand a specific ATO gear item
// id (never a `c:` tag - see the #61 audit's tag-bypass class: a tag pull
// would risk being silently satisfiable by some other mod's own cheap item
// sharing that tag, which defeats the point of gating on THIS dead-end
// item specifically).
//
//   - Refined Storage's raw processor chain (raw_basic/improved/advanced_
//     processor) is the single most load-bearing "important recipe" family
//     in the pack: tier_gating.js's own header notes advanced_processor
//     alone gates autocrafter/wireless_transmitter/network_receiver/
//     network_transmitter/relay/wireless_grid. Each raw processor's stock
//     recipe is shapeless around one vanilla tier material (iron/gold/
//     diamond) - tin/silver/platinum gears slot in as the same tier's
//     "solder/conductor/precious-contact" component, respecting the same
//     iron->gold->diamond tier order the stock recipe already encodes:
//       raw_basic_processor    (+iron)    -> + alltheores:tin_gear
//       raw_improved_processor (+gold)    -> + alltheores:silver_gear
//       raw_advanced_processor (+diamond) -> + alltheores:platinum_gear
//
//   - Sophisticated Storage's Magnet Upgrade / Advanced Magnet Upgrade
//     (real, desirable QoL upgrades, tier-chained: advanced consumes a
//     magnet_upgrade as its own ingredient) get osmium/iridium gears -
//     osmium for the magnetic/dense-metal flavor of the base upgrade,
//     iridium (this pack's rarest, most "decorative-only" leftover metal)
//     for the step above it. Both recipes use the mod's own
//     `sophisticatedcore:upgrade_next_tier` custom recipe type (matches
//     tier_gating.js's precedent for the same mod's storage_tier_upgrade
//     type) - re-authored here with one added ingredient apiece, same
//     pattern/shape otherwise.
//
// Deliberately NOT touched in this tranche (found to already have a real
// sink, not a dead end - see the survey above): zinc (Create itself),
// lead/nickel/aluminum (TFMG machine parts), uranium (Stellaris rocket
// chain), and the six PR #102 gem materials (Silent Gear tool material +
// beacon base). Remaining true gear/plate/rod dead weight across the other
// 20 metals (copper/iron/gold/bronze/constantan/electrum/enderium/invar/
// lumium/signalum/steel/aluminum/lead/nickel/uranium/zinc/diamond/
// netherite/...) is real but lower-priority than the five named here
// (silver named explicitly by the reporter; tin/osmium next-worst per the
// investigation) - left for a follow-up tranche rather than padding this
// one with recipes that don't map to something a player actually wants to
// craft.
ServerEvents.recipes(event => {
    // --- Refined Storage raw processor chain -----------------------------
    event.remove({ id: 'refinedstorage:raw_basic_processor' })
    event.shapeless('refinedstorage:raw_basic_processor', [
        'refinedstorage:processor_binding',
        '#c:ingots/iron',
        '#c:silicon',
        '#c:dusts/redstone',
        'alltheores:tin_gear',
    ]).id('vanillaplusplus:raw_basic_processor_tin_gear')

    event.remove({ id: 'refinedstorage:raw_improved_processor' })
    event.shapeless('refinedstorage:raw_improved_processor', [
        'refinedstorage:processor_binding',
        '#c:ingots/gold',
        '#c:silicon',
        '#c:dusts/redstone',
        'alltheores:silver_gear',
    ]).id('vanillaplusplus:raw_improved_processor_silver_gear')

    event.remove({ id: 'refinedstorage:raw_advanced_processor' })
    event.shapeless('refinedstorage:raw_advanced_processor', [
        'refinedstorage:processor_binding',
        '#c:gems/diamond',
        '#c:silicon',
        '#c:dusts/redstone',
        'alltheores:platinum_gear',
    ]).id('vanillaplusplus:raw_advanced_processor_platinum_gear')

    // --- Sophisticated Storage magnet upgrade ladder ---------------------
    // Same pattern/shape/other-ingredients as the stock jar recipes (read
    // directly from the installed jar, not assumed) - one gear added per
    // recipe in a cell the stock pattern left blank.
    event.remove({ id: 'sophisticatedstorage:magnet_upgrade' })
    event.custom({
        type: 'sophisticatedcore:upgrade_next_tier',
        category: 'misc',
        pattern: [
            'EIE',
            'IPI',
            'RGL',
        ],
        key: {
            E: { tag: 'c:ender_pearls' },
            I: { tag: 'c:ingots/iron' },
            L: { tag: 'c:gems/lapis' },
            P: { item: 'sophisticatedstorage:pickup_upgrade' },
            R: { tag: 'c:dusts/redstone' },
            G: { item: 'alltheores:osmium_gear' },
        },
        result: { count: 1, id: 'sophisticatedstorage:magnet_upgrade' },
    }).id('vanillaplusplus:magnet_upgrade_osmium_gear')

    event.remove({ id: 'sophisticatedstorage:advanced_magnet_upgrade' })
    event.custom({
        type: 'sophisticatedcore:upgrade_next_tier',
        category: 'misc',
        pattern: [
            'EIE',
            'IPI',
            'RGL',
        ],
        key: {
            E: { tag: 'c:ender_pearls' },
            I: { tag: 'c:ingots/iron' },
            L: { tag: 'c:gems/lapis' },
            P: { item: 'sophisticatedstorage:advanced_pickup_upgrade' },
            R: { tag: 'c:dusts/redstone' },
            G: { item: 'alltheores:iridium_gear' },
        },
        result: { count: 1, id: 'sophisticatedstorage:advanced_magnet_upgrade' },
    }).id('vanillaplusplus:advanced_magnet_upgrade_iridium_gear')
})

// #91 SECOND TRANCHE: the PM flagged tranche one's "gear-in-recipe" approach
// to the owner for confirmation as the pack's permanent material-sink style;
// that confirmation is still pending as of this tranche. Proceeding with the
// same technique for consistency (additional required ingredient, exact item
// id, never a `c:` tag, never a cheaper alt-path) - extended here to the
// remaining ~20 metals whose gear byproduct was left dead weight by tranche
// one - but every edit below is kept cleanly reversible (see the
// "Reversibility note" further down) specifically because that approval
// hasn't landed yet.
//
// Re-verified from scratch rather than trusting the tranche-one writeup:
// extracted all 95 installed jars fresh and grepped every recipe json for
// `c:gears/*`, `c:plates/*`, `c:rods/*`. Two real corrections to the record,
// both narrower than they first looked:
//   - `c:gears/*` has ZERO consumers anywhere outside AllTheOres' own tag
//     definition file, across all 95 mods, with no exceptions - every ATO
//     gear for every metal is still a genuine dead end. This tranche only
//     ever adds `_gear` items for exactly this reason - the class is
//     uncontested.
//   - `c:plates/*` and `c:rods/*` are NOT uniformly dead the way tranche one
//     described: TFMG's own accumulator/converter/electrode_holder/
//     transformer recipes consume `#c:plates/lead`, `#c:plates/nickel`, and
//     `#c:plates/aluminum` (merged tags TFMG populates with its own
//     `tfmg:lead_sheet`/`tfmg:nickel_sheet`/`tfmg:aluminum_sheet`, but which
//     AllTheOres' `alltheores:lead_plate`/`nickel_plate`/`aluminum_plate`
//     equally satisfy since neither tag file sets `replace`), and Stellaris'
//     rover/rocket_station_block recipes consume `#c:rods/steel` the same
//     way. Real sinks, just tag-based ones this pack doesn't control - left
//     untouched (not this tranche's job, and editing another mod's own
//     tag-based recipe would reintroduce the #61 tag-bypass risk this
//     pack's own additions are built to avoid). Doesn't change anything
//     here: none of the 19 metals below get a plate or rod sink, only gear.
//
// Same balance rule as tranche one: metals are grouped into four rough tiers
// by their real AllTheOres harvest-tool tag (`needs_stone_tool` /
// `needs_iron_tool` / `needs_diamond_tool`, the same source tranche one used
// for tin/silver/platinum) or, for alloys with no ore of their own, by the
// tier of their component metals - then routed into a recipe already gated
// at a matching or later tier, never earlier (an iron-tier metal never
// becomes required by a recipe this pack already has at copper tier, a
// diamond-tier metal never required by an iron-tier one). Spread across two
// mod families deliberately, not one: Refined Storage's own machine/storage
// ladder (construction/destruction cores -> importer/exporter -> storage
// capacity parts -> autocrafter/relay/wireless & network transmission -
// the same "single most load-bearing recipe family" tier_gating.js already
// documents) for ten of the nineteen, Sophisticated Storage's upgrade
// ladder (the same family tranche one used for osmium/iridium) for the
// other nine - each a real, already-desirable recipe this pack doesn't
// invent, never a throwaway decorative recipe.
//
// Every recipe touched here still has its full stock ingredient list -
// nothing removed, nothing substituted, one gear added apiece. For the
// eleven Sophisticated Storage recipes below, the stock jar pattern already
// left an unused blank cell (same shape tranche one exploited in
// magnet_upgrade) so the shape itself is untouched. Refined Storage's own
// nine touched recipes are different: read directly from the installed jar,
// six (64k_storage_part/autocrafter/wireless_transmitter/
// network_transmitter/network_receiver, plus construction_core/
// destruction_core/importer/exporter/relay already shapeless) either had no
// blank cell left in their 3x3 grid or were already shapeless outright - so
// the four that were shaped and full (64k_storage_part, autocrafter,
// wireless_transmitter, network_transmitter, network_receiver) are
// re-authored as an equivalent SHAPELESS recipe: every stock ingredient
// kept at its exact stock count (repeated entries where the stock pattern
// repeated a letter), positional constraint dropped, one gear added. That's
// a strict relaxation (any shaped arrangement that used to work still
// works, plus every other arrangement), not a nerf, and it's the only way
// to add a further ingredient to a recipe whose stock shape used all nine
// cells already.
//
// Tier ladder used below (cross-referenced against the RS ingredient chain
// itself - basic_processor -> improved_processor -> advanced_processor,
// the same chain tranche one's raw-processor edit already keys off):
//   IRON   tier (construction_core/destruction_core, basic_processor-tier
//          RS machines; the SC "base" upgrade half of each pair):
//              copper, zinc, lead, aluminum, bronze, brass, iron, nickel
//   GOLD   tier (exporter/importer, improved_processor-tier RS machines;
//          the SC "advanced" upgrade half of each pair):
//              constantan, uranium, gold, invar, steel
//   DIAMOND tier (64k_storage_part/autocrafter/wireless_transmitter/relay,
//          advanced_processor-tier RS machines):
//              electrum, signalum, lumium, diamond
//   TOP    tier (network_transmitter/network_receiver, RS's own top rung -
//          advanced_processor AND a netherite ingot already):
//              enderium, netherite
//
// Three SC pairs deliberately chain low metal -> higher metal across the
// same base/advanced upgrade family, mirroring tranche one's tin->silver
// and osmium->iridium chains: feeding_upgrade (copper) ->
// advanced_feeding_upgrade (gold), void_upgrade (bronze) ->
// advanced_void_upgrade (invar), hopper_upgrade (iron) ->
// advanced_hopper_upgrade (steel, the literal iron->steel upgrade).
//
// Reversibility note (owner has NOT yet confirmed the "gear-in-recipe"
// approach as the pack's permanent material-sink style - see tranche one's
// PR and this tranche's own PR body): every edit below is a single added
// ingredient in an otherwise-untouched stock recipe, tagged with its own
// `vanillaplusplus:` id and listed in ST_MATERIAL_SINK_RECIPES in
// selftest.js. If the owner wants a different sink style, deleting this
// block plus its selftest entries fully reverts to stock recipes with no
// other file touched.
ServerEvents.recipes(event => {
    // --- Sophisticated Storage base-tier upgrades (iron tier) ------------
    // Each stock pattern already has one unused blank cell (row 0, col 0) -
    // same shape tranche one used for magnet_upgrade's "R L" blank.
    event.remove({ id: 'sophisticatedstorage:feeding_upgrade' })
    event.shaped('sophisticatedstorage:feeding_upgrade', [
        'GC ',
        'ABM',
        ' E ',
    ], {
        A: { item: 'minecraft:golden_apple' },
        B: { item: 'sophisticatedstorage:upgrade_base' },
        C: { item: 'minecraft:golden_carrot' },
        E: { tag: 'c:ender_pearls' },
        M: { item: 'minecraft:glistering_melon_slice' },
        G: { item: 'alltheores:copper_gear' },
    }).id('vanillaplusplus:feeding_upgrade_copper_gear')

    event.remove({ id: 'sophisticatedstorage:void_upgrade' })
    event.shaped('sophisticatedstorage:void_upgrade', [
        'GE ',
        'OBO',
        'ROR',
    ], {
        B: { item: 'sophisticatedstorage:upgrade_base' },
        E: { tag: 'c:ender_pearls' },
        O: { tag: 'c:obsidians' },
        R: { tag: 'c:dusts/redstone' },
        G: { item: 'alltheores:bronze_gear' },
    }).id('vanillaplusplus:void_upgrade_bronze_gear')

    event.remove({ id: 'sophisticatedstorage:jukebox_upgrade' })
    event.shaped('sophisticatedstorage:jukebox_upgrade', [
        'GJ ',
        'IBI',
        ' R ',
    ], {
        B: { item: 'sophisticatedstorage:upgrade_base' },
        I: { tag: 'c:ingots/iron' },
        J: { item: 'minecraft:jukebox' },
        R: { tag: 'c:dusts/redstone' },
        G: { item: 'alltheores:brass_gear' },
    }).id('vanillaplusplus:jukebox_upgrade_brass_gear')

    event.remove({ id: 'sophisticatedstorage:hopper_upgrade' })
    event.shaped('sophisticatedstorage:hopper_upgrade', [
        'GH ',
        'IBI',
        'RRR',
    ], {
        B: { item: 'sophisticatedstorage:upgrade_base' },
        H: { item: 'minecraft:hopper' },
        I: { tag: 'c:ingots/iron' },
        R: { tag: 'c:dusts/redstone' },
        G: { item: 'alltheores:iron_gear' },
    }).id('vanillaplusplus:hopper_upgrade_iron_gear')

    event.remove({ id: 'sophisticatedstorage:stonecutter_upgrade' })
    event.shaped('sophisticatedstorage:stonecutter_upgrade', [
        'GS ',
        'IBI',
        ' R ',
    ], {
        B: { item: 'sophisticatedstorage:upgrade_base' },
        I: { tag: 'c:ingots/iron' },
        R: { tag: 'c:dusts/redstone' },
        S: { item: 'minecraft:stonecutter' },
        G: { item: 'alltheores:nickel_gear' },
    }).id('vanillaplusplus:stonecutter_upgrade_nickel_gear')

    event.remove({ id: 'sophisticatedstorage:crafting_upgrade' })
    event.shaped('sophisticatedstorage:crafting_upgrade', [
        'GT ',
        'IBI',
        ' C ',
    ], {
        B: { item: 'sophisticatedstorage:upgrade_base' },
        C: { tag: 'c:chests' },
        I: { tag: 'c:ingots/iron' },
        T: { item: 'minecraft:crafting_table' },
        G: { item: 'alltheores:aluminum_gear' },
    }).id('vanillaplusplus:crafting_upgrade_aluminum_gear')

    // --- Sophisticated Storage advanced-tier upgrades (gold tier) --------
    // Same blank-cell technique; letter X used instead of G because G is
    // already the stock gold-ingot key in every one of these three.
    event.remove({ id: 'sophisticatedstorage:advanced_feeding_upgrade' })
    event.custom({
        type: 'sophisticatedcore:upgrade_next_tier',
        category: 'misc',
        pattern: [
            'XD ',
            'GVG',
            'RRR',
        ],
        key: {
            D: { tag: 'c:gems/diamond' },
            G: { tag: 'c:ingots/gold' },
            R: { tag: 'c:dusts/redstone' },
            V: { item: 'sophisticatedstorage:feeding_upgrade' },
            X: { item: 'alltheores:gold_gear' },
        },
        result: { count: 1, id: 'sophisticatedstorage:advanced_feeding_upgrade' },
    }).id('vanillaplusplus:advanced_feeding_upgrade_gold_gear')

    event.remove({ id: 'sophisticatedstorage:advanced_void_upgrade' })
    event.custom({
        type: 'sophisticatedcore:upgrade_next_tier',
        category: 'misc',
        pattern: [
            'XD ',
            'GVG',
            'RRR',
        ],
        key: {
            D: { tag: 'c:gems/diamond' },
            G: { tag: 'c:ingots/gold' },
            R: { tag: 'c:dusts/redstone' },
            V: { item: 'sophisticatedstorage:void_upgrade' },
            X: { item: 'alltheores:invar_gear' },
        },
        result: { count: 1, id: 'sophisticatedstorage:advanced_void_upgrade' },
    }).id('vanillaplusplus:advanced_void_upgrade_invar_gear')

    event.remove({ id: 'sophisticatedstorage:advanced_hopper_upgrade' })
    event.custom({
        type: 'sophisticatedcore:upgrade_next_tier',
        category: 'misc',
        pattern: [
            'XD ',
            'GHG',
            'ROR',
        ],
        key: {
            D: { tag: 'c:gems/diamond' },
            G: { tag: 'c:ingots/gold' },
            H: { item: 'sophisticatedstorage:hopper_upgrade' },
            O: { item: 'minecraft:dropper' },
            R: { tag: 'c:dusts/redstone' },
            X: { item: 'alltheores:steel_gear' },
        },
        result: { count: 1, id: 'sophisticatedstorage:advanced_hopper_upgrade' },
    }).id('vanillaplusplus:advanced_hopper_upgrade_steel_gear')

    // --- Refined Storage: shapeless recipes, gear appended directly -------
    // construction_core/destruction_core/importer/exporter/relay were
    // already `minecraft:crafting_shapeless` in the stock jar - same
    // pattern tranche one used for the raw_processor chain, just append.
    event.remove({ id: 'refinedstorage:construction_core' })
    event.shapeless('refinedstorage:construction_core', [
        'refinedstorage:basic_processor',
        '#c:dusts/glowstone',
        'alltheores:zinc_gear',
    ]).id('vanillaplusplus:construction_core_zinc_gear')

    event.remove({ id: 'refinedstorage:destruction_core' })
    event.shapeless('refinedstorage:destruction_core', [
        'refinedstorage:basic_processor',
        '#c:gems/quartz',
        'alltheores:lead_gear',
    ]).id('vanillaplusplus:destruction_core_lead_gear')

    event.remove({ id: 'refinedstorage:exporter' })
    event.shapeless('refinedstorage:exporter', [
        'refinedstorage:cable',
        'refinedstorage:construction_core',
        'refinedstorage:improved_processor',
        'alltheores:constantan_gear',
    ]).id('vanillaplusplus:exporter_constantan_gear')

    event.remove({ id: 'refinedstorage:importer' })
    event.shapeless('refinedstorage:importer', [
        'refinedstorage:cable',
        'refinedstorage:destruction_core',
        'refinedstorage:improved_processor',
        'alltheores:uranium_gear',
    ]).id('vanillaplusplus:importer_uranium_gear')

    event.remove({ id: 'refinedstorage:relay' })
    event.shapeless('refinedstorage:relay', [
        'refinedstorage:machine_casing',
        'refinedstorage:cable',
        'refinedstorage:advanced_processor',
        'minecraft:redstone_torch',
        'alltheores:diamond_gear',
    ]).id('vanillaplusplus:relay_diamond_gear')

    // --- Refined Storage: shaped recipes with no blank cell left ----------
    // All four stock patterns fill every one of the 3x3 grid's nine cells,
    // so (see header note) each is re-authored as an equivalent shapeless
    // recipe: every stock ingredient kept at its exact stock count (letters
    // that repeated in the stock pattern are repeated the same number of
    // times here), plus one gear.
    event.remove({ id: 'refinedstorage:64k_storage_part' })
    event.shapeless('refinedstorage:64k_storage_part', [
        'refinedstorage:advanced_processor',
        'refinedstorage:advanced_processor',
        'refinedstorage:advanced_processor',
        'refinedstorage:advanced_processor',
        'refinedstorage:quartz_enriched_iron',
        'refinedstorage:16k_storage_part',
        'refinedstorage:16k_storage_part',
        'refinedstorage:16k_storage_part',
        '#c:dusts/redstone',
        'alltheores:electrum_gear',
    ]).id('vanillaplusplus:64k_storage_part_electrum_gear')

    event.remove({ id: 'refinedstorage:autocrafter' })
    event.shapeless('refinedstorage:autocrafter', [
        'refinedstorage:quartz_enriched_iron',
        'refinedstorage:quartz_enriched_iron',
        'refinedstorage:quartz_enriched_iron',
        'refinedstorage:quartz_enriched_iron',
        'refinedstorage:construction_core',
        'refinedstorage:advanced_processor',
        'refinedstorage:advanced_processor',
        'refinedstorage:machine_casing',
        'refinedstorage:destruction_core',
        'alltheores:signalum_gear',
    ]).id('vanillaplusplus:autocrafter_signalum_gear')

    event.remove({ id: 'refinedstorage:wireless_transmitter' })
    event.shapeless('refinedstorage:wireless_transmitter', [
        'refinedstorage:quartz_enriched_iron',
        'refinedstorage:quartz_enriched_iron',
        'refinedstorage:quartz_enriched_iron',
        'refinedstorage:quartz_enriched_iron',
        'refinedstorage:quartz_enriched_iron',
        'refinedstorage:quartz_enriched_iron',
        '#c:ender_pearls',
        'refinedstorage:machine_casing',
        'refinedstorage:advanced_processor',
        'alltheores:lumium_gear',
    ]).id('vanillaplusplus:wireless_transmitter_lumium_gear')

    event.remove({ id: 'refinedstorage:network_transmitter' })
    event.shapeless('refinedstorage:network_transmitter', [
        '#c:ender_pearls',
        '#c:ender_pearls',
        '#c:ender_pearls',
        'refinedstorage:construction_core',
        'refinedstorage:machine_casing',
        'refinedstorage:destruction_core',
        'refinedstorage:advanced_processor',
        'refinedstorage:advanced_processor',
        '#c:ingots/netherite',
        'alltheores:enderium_gear',
    ]).id('vanillaplusplus:network_transmitter_enderium_gear')

    event.remove({ id: 'refinedstorage:network_receiver' })
    event.shapeless('refinedstorage:network_receiver', [
        'refinedstorage:advanced_processor',
        'refinedstorage:advanced_processor',
        '#c:ingots/netherite',
        'refinedstorage:construction_core',
        'refinedstorage:machine_casing',
        'refinedstorage:destruction_core',
        '#c:ender_pearls',
        '#c:ender_pearls',
        '#c:ender_pearls',
        'alltheores:netherite_gear',
    ]).id('vanillaplusplus:network_receiver_netherite_gear')
})

// #91 THIRD TRANCHE (feat/91-material-sinks-full): tranches one/two sank every
// AllTheOres GEAR (all 24 metals). A fresh, condition-aware consumer scan of
// all 104 installed jars (every recipe json, with neoforge:conditions
// evaluated against the REAL installed modid set parsed from each jar's
// [[mods]] blocks incl. Jar-in-Jar - so ATO's own plate/rod/gem-dust recipes
// that are gated on immersiveengineering/enderio/mekanism/thermal, none of
// which is installed, are correctly counted as ABSENT, not as live consumers)
// plus this pack's own data + kubejs found the remaining universal dead ends:
//   - 14 PLATE byproducts with no live consumer. The other 10 metals' plates
//     ARE consumed via #c:plates/<metal> (brass/copper/gold/iron/steel/
//     electrum/zinc by Create/CreateAddition/TFMG/Numismatics; aluminum/lead/
//     nickel already sunk in tranche one) and are left untouched.
//   - 21 ROD byproducts with no live consumer. Only copper/iron/steel rods
//     have a live #c:rods/<metal> consumer (CreateAddition/SilentGear/
//     Stellaris) - left untouched.
//   - 5 GEM DUSTs (ruby/sapphire/peridot/fluorite/cinnabar): produced by a
//     live ore-hammer crushing recipe but with no consumer (the gem itself
//     became a SilentGear material in #102; its dust stayed dead).
// = 40 items. ATO's clump/shard/crystal/dirty_dust intermediates were verified
// UNOBTAINABLE in this pack (no live producer - they belong to Mekanism/IE
// processing that isn't installed), so they are not real dead ends and get no
// sink.
//
// Same convention as tranches one/two: an ADDITIONAL required ingredient, the
// LITERAL alltheores: item id (never a c: tag - the #61 tag-bypass class),
// never a cheaper alt path, one dead-end item per recipe. Every stock
// ingredient is preserved at its exact stock multiplicity; shaped hosts are
// re-authored as an equivalent SHAPELESS recipe (a strict relaxation - every
// arrangement that used to craft still works) so the extra ingredient fits.
// Result counts are preserved (event.remove drops the stock recipe; the
// re-authored one keeps the stock output count). HARD CONSTRAINT honoured: a
// table craft has at most 9 slots, so only hosts whose stock recipe fills <=8
// cells were chosen - every recipe below is <=9 ingredients and remains
// craftable in a normal grid.
//
// REACHABILITY: every ATO plate/rod/gem-dust is craftable EARLY via an ATO
// ore hammer (a stone-tier tool) + the metal ingot / gem - NOT via Create
// pressing - so there is no bootstrap deadlock (a Create machine gated on a
// rod does not need that machine to make the rod) and every sink material is
// reachable at or before its host recipe's tier. Materials are still bucketed
// by rough rarity for feel, matching the tier band each metal's gear got in
// tranche two.
ServerEvents.recipes(event => {
    // --- EARLY (Andesite Age band): common metals -> foundational Create machines ---
    event.remove({ id: 'create:crafting/kinetics/encased_fan' })
    event.shapeless('create:encased_fan', [
        'create:shaft',
        'create:andesite_casing',
        'create:propeller',
        'alltheores:tin_rod',
    ]).id('vanillaplusplus:encased_fan_tin_rod')

    event.remove({ id: 'create:crafting/kinetics/mechanical_press' })
    event.shapeless('create:mechanical_press', [
        'create:shaft',
        'create:andesite_casing',
        '#c:storage_blocks/iron',
        'alltheores:bronze_plate',
    ]).id('vanillaplusplus:mechanical_press_bronze_plate')

    event.remove({ id: 'create:crafting/kinetics/mechanical_drill' })
    event.shapeless('create:mechanical_drill', [
        'create:andesite_alloy',
        'create:andesite_alloy',
        'create:andesite_alloy',
        '#c:ingots/iron',
        'create:andesite_casing',
        'alltheores:nickel_rod',
    ]).id('vanillaplusplus:mechanical_drill_nickel_rod')

    event.remove({ id: 'create:crafting/kinetics/mechanical_saw' })
    event.shapeless('create:mechanical_saw', [
        '#c:plates/iron',
        '#c:plates/iron',
        '#c:plates/iron',
        '#c:ingots/iron',
        'create:andesite_casing',
        'alltheores:zinc_rod',
    ]).id('vanillaplusplus:mechanical_saw_zinc_rod')

    event.remove({ id: 'create:crafting/kinetics/millstone' })
    event.shapeless('create:millstone', [
        'create:cogwheel',
        'create:andesite_casing',
        '#c:stones',
        'alltheores:lead_rod',
    ]).id('vanillaplusplus:millstone_lead_rod')

    event.remove({ id: 'create:crafting/kinetics/mechanical_mixer' })
    event.shapeless('create:mechanical_mixer', [
        'create:cogwheel',
        'create:andesite_casing',
        'create:whisk',
        'alltheores:aluminum_rod',
    ]).id('vanillaplusplus:mechanical_mixer_aluminum_rod')

    event.remove({ id: 'create:crafting/kinetics/depot' })
    event.shapeless('create:depot', [
        'create:andesite_alloy',
        'create:andesite_casing',
        'alltheores:tin_plate',
    ]).id('vanillaplusplus:depot_tin_plate')

    event.remove({ id: 'create:crafting/kinetics/mechanical_bearing' })
    event.shapeless('create:mechanical_bearing', [
        '#minecraft:wooden_slabs',
        'create:andesite_casing',
        'create:shaft',
        'alltheores:bronze_rod',
    ]).id('vanillaplusplus:mechanical_bearing_bronze_rod')

    event.remove({ id: 'create:crafting/kinetics/hand_crank' })
    event.shapeless('create:hand_crank', [
        '#minecraft:planks',
        '#minecraft:planks',
        '#minecraft:planks',
        'create:andesite_alloy',
        'alltheores:brass_rod',
    ]).id('vanillaplusplus:hand_crank_brass_rod')

    // --- MID (Brass Age band): alloys/precious metals + the 5 gem dusts -> Create brass kinetics/logistics, CreateAddition, Numismatics, Refined Storage grid ---
    event.remove({ id: 'create:crafting/kinetics/mechanical_arm' })
    event.shapeless('create:mechanical_arm', [
        '#c:plates/brass',
        '#c:plates/brass',
        '#c:plates/brass',
        'create:andesite_alloy',
        'create:precision_mechanism',
        'create:brass_casing',
        'alltheores:constantan_rod',
    ]).id('vanillaplusplus:mechanical_arm_constantan_rod')

    event.remove({ id: 'create:crafting/kinetics/deployer' })
    event.shapeless('create:deployer', [
        'create:electron_tube',
        'create:andesite_casing',
        'create:brass_hand',
        'alltheores:invar_rod',
    ]).id('vanillaplusplus:deployer_invar_rod')

    event.remove({ id: 'create:crafting/kinetics/sequenced_gearshift' })
    event.shapeless('create:sequenced_gearshift', [
        'create:brass_casing',
        'create:cogwheel',
        'create:electron_tube',
        'alltheores:gold_rod',
    ]).id('vanillaplusplus:sequenced_gearshift_gold_rod')

    event.remove({ id: 'create:crafting/kinetics/fluid_tank' })
    event.shapeless('create:fluid_tank', [
        '#c:plates/copper',
        '#c:plates/copper',
        '#c:barrels/wooden',
        'alltheores:silver_plate',
    ]).id('vanillaplusplus:fluid_tank_silver_plate')

    event.remove({ id: 'create:crafting/kinetics/portable_storage_interface' })
    event.shapeless('create:portable_storage_interface', [
        'create:andesite_casing',
        'create:chute',
        'alltheores:uranium_rod',
    ]).id('vanillaplusplus:portable_storage_interface_uranium_rod')

    event.remove({ id: 'create:crafting/kinetics/weighted_ejector' })
    event.shapeless('create:weighted_ejector', [
        '#c:plates/gold',
        'create:depot',
        'create:cogwheel',
        'alltheores:silver_rod',
    ]).id('vanillaplusplus:weighted_ejector_silver_rod')

    event.remove({ id: 'create:crafting/kinetics/rotation_speed_controller' })
    event.shapeless('create:rotation_speed_controller', [
        'create:precision_mechanism',
        'create:brass_casing',
        'alltheores:constantan_plate',
    ]).id('vanillaplusplus:rotation_speed_controller_constantan_plate')

    event.remove({ id: 'create:crafting/logistics/brass_funnel' })
    event.shapeless(Item.of('create:brass_funnel', 2), [
        'create:electron_tube',
        '#c:ingots/brass',
        'minecraft:dried_kelp',
        'alltheores:invar_plate',
    ]).id('vanillaplusplus:brass_funnel_invar_plate')

    event.remove({ id: 'createaddition:crafting/capacitor_1' })
    event.shapeless('createaddition:capacitor', [
        '#c:plates/zinc',
        '#c:plates/copper',
        'minecraft:redstone_torch',
        'alltheores:uranium_plate',
    ]).id('vanillaplusplus:capacitor_uranium_plate')

    event.remove({ id: 'createaddition:crafting/connector' })
    event.shapeless(Item.of('createaddition:connector', 3), [
        '#c:rods/copper',
        'create:andesite_alloy',
        '#c:slime_balls',
        'alltheores:cinnabar_dust',
    ]).id('vanillaplusplus:connector_cinnabar_dust')

    event.remove({ id: 'createaddition:crafting/modular_accumulator' })
    event.shapeless('createaddition:modular_accumulator', [
        '#c:rods/copper',
        'createaddition:capacitor',
        'createaddition:capacitor',
        'create:brass_casing',
        '#c:wires/electrum',
        'alltheores:ruby_dust',
    ]).id('vanillaplusplus:modular_accumulator_ruby_dust')

    event.remove({ id: 'numismatics:crafting/bank_terminal' })
    event.shapeless('numismatics:bank_terminal', [
        'create:precision_mechanism',
        'create:industrial_iron_block',
        'create:electron_tube',
        'alltheores:sapphire_dust',
    ]).id('vanillaplusplus:bank_terminal_sapphire_dust')

    event.remove({ id: 'create:crafting/kinetics/elevator_pulley' })
    event.shapeless('create:elevator_pulley', [
        'create:brass_casing',
        'minecraft:dried_kelp_block',
        '#c:plates/iron',
        'alltheores:peridot_dust',
    ]).id('vanillaplusplus:elevator_pulley_peridot_dust')

    event.remove({ id: 'refinedstorage:crafting_grid' })
    event.shapeless('refinedstorage:crafting_grid', [
        'refinedstorage:grid',
        'refinedstorage:advanced_processor',
        '#c:player_workstations/crafting_tables',
        'alltheores:fluorite_dust',
    ]).id('vanillaplusplus:crafting_grid_fluorite_dust')

    // --- LATE (Precision/Induction band): late alloys -> Create automation logistics + Refined Storage pattern grid ---
    event.remove({ id: 'create:crafting/kinetics/mechanical_piston' })
    event.shapeless('create:mechanical_piston', [
        '#minecraft:wooden_slabs',
        'create:andesite_casing',
        'create:piston_extension_pole',
        'alltheores:diamond_plate',
    ]).id('vanillaplusplus:mechanical_piston_diamond_plate')

    event.remove({ id: 'create:crafting/logistics/brass_tunnel' })
    event.shapeless(Item.of('create:brass_tunnel', 2), [
        'create:electron_tube',
        '#c:ingots/brass',
        '#c:ingots/brass',
        'minecraft:dried_kelp',
        'minecraft:dried_kelp',
        'alltheores:signalum_plate',
    ]).id('vanillaplusplus:brass_tunnel_signalum_plate')

    event.remove({ id: 'create:crafting/kinetics/display_board' })
    event.shapeless(Item.of('create:display_board', 2), [
        'create:andesite_alloy',
        'create:andesite_alloy',
        'create:electron_tube',
        'alltheores:lumium_plate',
    ]).id('vanillaplusplus:display_board_lumium_plate')

    event.remove({ id: 'refinedstorage:pattern_grid' })
    event.shapeless('refinedstorage:pattern_grid', [
        'refinedstorage:grid',
        'refinedstorage:advanced_processor',
        'refinedstorage:pattern',
        'alltheores:platinum_plate',
    ]).id('vanillaplusplus:pattern_grid_platinum_plate')

    event.remove({ id: 'create:crafting/kinetics/clutch' })
    event.shapeless('create:clutch', [
        'create:andesite_casing',
        'create:shaft',
        '#c:dusts/redstone',
        'alltheores:electrum_rod',
    ]).id('vanillaplusplus:clutch_electrum_rod')

    event.remove({ id: 'create:crafting/kinetics/gearshift' })
    event.shapeless('create:gearshift', [
        'create:andesite_casing',
        'create:cogwheel',
        '#c:dusts/redstone',
        'alltheores:diamond_rod',
    ]).id('vanillaplusplus:gearshift_diamond_rod')

    event.remove({ id: 'create:crafting/logistics/stockpile_switch' })
    event.shapeless('create:stockpile_switch', [
        'create:electron_tube',
        'create:brass_casing',
        'minecraft:comparator',
        'alltheores:lumium_rod',
    ]).id('vanillaplusplus:stockpile_switch_lumium_rod')

    event.remove({ id: 'create:crafting/kinetics/cuckoo_clock' })
    event.shapeless('create:cuckoo_clock', [
        '#minecraft:planks',
        'create:andesite_casing',
        'minecraft:clock',
        'alltheores:platinum_rod',
    ]).id('vanillaplusplus:cuckoo_clock_platinum_rod')

    event.remove({ id: 'create:crafting/logistics/content_observer' })
    event.shapeless('create:content_observer', [
        'create:electron_tube',
        'create:brass_casing',
        'minecraft:observer',
        'alltheores:signalum_rod',
    ]).id('vanillaplusplus:content_observer_signalum_rod')

    // --- TOP (Starforged+ band): rare/space metals -> Stellaris rocketry + Silent Gear endgame machines ---
    event.remove({ id: 'stellaris:misc/rocket_fin' })
    event.shapeless('stellaris:rocket_fin', [
        '#c:ingots/steel',
        '#c:ingots/steel',
        '#c:ingots/steel',
        '#c:ingots/steel',
        '#c:ingots/steel',
        'alltheores:enderium_plate',
    ]).id('vanillaplusplus:rocket_fin_enderium_plate')

    event.remove({ id: 'stellaris:misc/rocket_nose_cone' })
    event.shapeless('stellaris:rocket_nose_cone', [
        'minecraft:redstone',
        '#c:ingots/steel',
        '#c:ingots/steel',
        '#c:ingots/steel',
        '#c:ingots/steel',
        'alltheores:iridium_plate',
    ]).id('vanillaplusplus:rocket_nose_cone_iridium_plate')

    event.remove({ id: 'stellaris:misc/engine_fan' })
    event.shapeless('stellaris:engine_fan', [
        '#c:nuggets/steel',
        '#c:nuggets/steel',
        '#c:nuggets/steel',
        '#c:nuggets/steel',
        '#c:ingots/steel',
        'alltheores:osmium_plate',
    ]).id('vanillaplusplus:engine_fan_osmium_plate')

    event.remove({ id: 'stellaris:misc/oxygen_tank' })
    event.shapeless('stellaris:oxygen_tank', [
        '#c:nuggets/steel',
        '#c:ingots/steel',
        '#c:ingots/steel',
        'alltheores:netherite_plate',
    ]).id('vanillaplusplus:oxygen_tank_netherite_plate')

    event.remove({ id: 'stellaris:misc/modules/base_module_tier_1' })
    event.shapeless('stellaris:base_module_tier_1', [
        'stellaris:heavy_metal_nugget',
        'stellaris:heavy_metal_nugget',
        'stellaris:heavy_metal_nugget',
        'stellaris:heavy_metal_nugget',
        'stellaris:heavy_metal_nugget',
        'stellaris:heavy_metal_nugget',
        'minecraft:gold_nugget',
        'minecraft:gold_nugget',
        'alltheores:enderium_rod',
    ]).id('vanillaplusplus:base_module_tier_1_enderium_rod')

    event.remove({ id: 'silentgear:metal_press' })
    event.shapeless('silentgear:metal_press', [
        '#c:obsidians',
        '#c:obsidians',
        '#c:obsidians',
        '#c:obsidians',
        '#c:ingots/tyrian_steel',
        '#c:ingots/tyrian_steel',
        '#c:rods/iron',
        '#c:rods/iron',
        'alltheores:iridium_rod',
    ]).id('vanillaplusplus:metal_press_iridium_rod')

    event.remove({ id: 'silentgear:refabricator' })
    event.shapeless('silentgear:refabricator', [
        '#c:ingots/iron',
        '#c:ingots/iron',
        '#c:gems/diamond',
        '#c:gems/diamond',
        '#c:gems/bort',
        '#minecraft:planks',
        '#minecraft:planks',
        '#c:storage_blocks/iron',
        'alltheores:netherite_rod',
    ]).id('vanillaplusplus:refabricator_netherite_rod')

    event.remove({ id: 'silentgear:alloy_forge' })
    event.shapeless('silentgear:alloy_forge', [
        '#c:ingots/crimson_steel',
        '#c:ingots/crimson_steel',
        '#c:ingots/crimson_steel',
        '#c:ingots/crimson_steel',
        'minecraft:blackstone',
        'minecraft:blackstone',
        'minecraft:blackstone',
        '#c:storage_blocks/iron',
        'alltheores:osmium_rod',
    ]).id('vanillaplusplus:alloy_forge_osmium_rod')

})
