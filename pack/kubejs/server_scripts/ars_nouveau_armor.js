// Gear overhaul Part 4: Ars Nouveau's 3 mage-armor pieces (Sorcerer's Wrap,
// Arcanist's Robes, Battlemage's Gambeson) redirected off vanilla gold/iron/
// diamond chestplate reagents onto a Silent Gear chestplate (any material -
// going through Silent Gear's own blueprint+template+workbench process is
// what satisfies "the same smithing process"). Each robe's own defense value
// is fixed regardless of reagent material, so the actual difficulty/tier
// gating is enforced by directly locking each robe ITEM in ProgressiveStages
// (andesite_age.toml/precision_age.toml/starforged_age.toml) rather than by
// requiring a specific material tier as reagent.
const ROBE_IDS = [
    'ars_nouveau:sorcerer_robes',
    'ars_nouveau:arcanist_robes',
    'ars_nouveau:battlemage_robes',
]

ServerEvents.recipes(event => {
    for (const id of ROBE_IDS) {
        event.remove({ id: id })
        event.custom({
            type: 'ars_nouveau:enchanting_apparatus',
            keepNbtOfReagent: true,
            pedestalItems: [
                { item: 'ars_nouveau:magebloom_fiber' },
                { item: 'ars_nouveau:magebloom_fiber' },
                { item: 'ars_nouveau:magebloom_fiber' },
                { item: 'ars_nouveau:magebloom_fiber' },
            ],
            reagent: { item: 'silentgear:chestplate' },
            result: { id: id, count: 1 },
            sourceCost: 0,
        }).id(id)
    }
})
