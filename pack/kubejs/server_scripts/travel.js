// Travel overhaul Part 2 (revised): Create Aeronautics, replacing Immersive
// Aircraft per user request. Unlike every other gate in this pack's travel
// overhaul (boats, trains, Waystones - all explicit ProgressiveStages item
// locks because their source mods use only vanilla/Tier-0 materials with
// nothing to naturally piggyback on), Create Aeronautics' own recipes
// already lean on Create's material chain. So instead of adding explicit
// locks, these patches swap/add ingredients that this pack ALREADY tier-
// locks in ProgressiveStages (see brass_age.toml/precision_age.toml/
// induction_age.toml), so the existing raw-material locks transitively gate
// these recipes too - per the user's explicit request to gate air travel
// through recipe ingredients rather than direct item locks.
//
// Two recipes need no patch at all and are left untouched:
// - aeronautics:propeller_bearing already requires create:brass_casing
//   (Brass Age).
// - aeronautics:levitite_blend (create:mixing) already requires crushed
//   minecraft:end_stone, and the only practical source of end_stone in this
//   pack is the End itself, locked until Precision Age.
ServerEvents.recipes(event => {
    // Brass Age: pairs with Propeller Bearing so burner/balloon-based flight
    // opens on the same tier as propeller-driven flight. The stock recipe
    // has one open slot (top-center) in an otherwise full 3x3 shape.
    event.remove({ id: 'aeronautics:adjustable_burner' })
    event.shaped('aeronautics:adjustable_burner', [
        'SBS',
        'SCS',
        'ARA'
    ], {
        S: 'create:iron_sheet',
        B: 'create:brass_sheet',
        C: '#aeronautics:burner_fire',
        A: 'create:andesite_alloy',
        R: 'minecraft:redstone'
    }).id('vanillaplusplus:adjustable_burner_brass_gated')

    // Precision Age: self-leveling gyroscopic flight. Swaps the stock wood
    // slab for Precision Age's own Sturdy Sheet - thematically an upgrade
    // anyway (a gyroscope assembly built from a plain wood slab always felt
    // like a placeholder).
    event.remove({ id: 'aeronautics:gyroscopic_propeller_bearing' })
    event.shaped('aeronautics:gyroscopic_propeller_bearing', [
        ' A ',
        ' G ',
        ' B '
    ], {
        A: 'create:sturdy_sheet',
        G: 'simulated:gyroscopic_mechanism',
        B: 'create:brass_casing'
    }).id('vanillaplusplus:gyroscopic_propeller_bearing_precision_gated')

    event.remove({ id: 'aeronautics:smart_propeller' })
    event.shaped('2x aeronautics:smart_propeller', [
        'PS',
        'G ',
        'B '
    ], {
        P: 'create:propeller',
        S: 'create:sturdy_sheet',
        G: 'simulated:gyroscopic_mechanism',
        B: 'create:brass_casing'
    }).id('vanillaplusplus:smart_propeller_precision_gated')

    // Induction Age: Steam Vent is the passive/industrial heat source (vs.
    // the Brass Age Adjustable Burner's manual redstone-toggled one), sized
    // for the big sustained-lift envelope clusters that make sense as the
    // ceiling right before the Tier 5 space gateway. Reuses this pack's
    // existing Induction Age material rather than inventing a new one.
    event.remove({ id: 'aeronautics:steam_vent' })
    event.shaped('aeronautics:steam_vent', [
        'G',
        'C',
        'A'
    ], {
        G: '#c:plates/gold',
        C: 'minecraft:copper_block',
        A: 'allthemodium:allthemodium_ingot'
    }).id('vanillaplusplus:steam_vent_induction_gated')
})
