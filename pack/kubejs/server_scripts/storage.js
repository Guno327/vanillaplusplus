// Tom's Storage is our Tier 1 "dumb storage" (see DESIGN.md): link chests into
// a browsable terminal using iron-tier resources only. Its stock recipes need
// a diamond + ender pearl (Inventory Connector) and Nether glowstone (Storage
// Terminal) - both unavailable at Andesite Age. Patch them down to iron-tier
// substitutes, keeping the same shape/slot layout. Use minecraft:repeater
// (stone + redstone torches + redstone dust, all iron-tier-obtainable)
// instead of minecraft:comparator, since a comparator needs Nether quartz
// and the Nether isn't open until a later tier - a comparator here would
// soft-lock the dumb storage quest.
//
// Refined Storage needs no equivalent patch: it's unlocked at Brass Age now,
// where diamond (for its Advanced Processor) and the Nether (for its Quartz
// chain) are already open.
ServerEvents.recipes(event => {
    event.remove({ id: 'toms_storage:inventory_connector' })
    event.shaped('toms_storage:inventory_connector', [
        'PCP',
        'cIc',
        'PRP'
    ], {
        P: '#minecraft:planks',
        c: '#c:chests',
        C: 'minecraft:repeater',
        I: '#c:ingots/iron',
        R: '#c:dusts/redstone'
    }).id('vanillaplusplus:inventory_connector_early_tier')

    event.remove({ id: 'toms_storage:storage_terminal' })
    event.shaped('toms_storage:storage_terminal', [
        'PCP',
        'cRg',
        'PCP'
    ], {
        P: '#minecraft:planks',
        c: '#c:chests',
        C: 'minecraft:repeater',
        R: '#c:dusts/redstone',
        g: '#c:glass_blocks/colorless'
    }).id('vanillaplusplus:storage_terminal_early_tier')
})
