// Refined Storage's stock Disk Drive recipe requires an Advanced Processor,
// which needs a diamond — locked until Brass Age (Tier 2). That makes a
// working network impossible at Andesite Age (Tier 1), where the design
// calls for a tiny-but-browsable storage interface. Patch it down to an
// Improved Processor (gold-tier, never locked) instead. See DESIGN.md's
// storage section for the full reasoning and the rest of the tier mapping.
ServerEvents.recipes(event => {
    event.remove({ id: 'refinedstorage:disk_drive' })
    event.shaped('refinedstorage:disk_drive', [
        'ECE',
        'EME',
        'EPE'
    ], {
        E: 'refinedstorage:quartz_enriched_iron',
        C: '#c:chests',
        M: 'refinedstorage:machine_casing',
        P: 'refinedstorage:improved_processor'
    }).id('vanillaplusplus:disk_drive_early_tier')
})
