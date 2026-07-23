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
