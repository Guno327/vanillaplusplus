// instructions.md: "Instead of making metal tools normally have some kinds
// of blacksmithing" - Tier 1 previously just unlocked vanilla iron tools
// outright as a placeholder (see DESIGN.md). Silent Gear's own modular
// process (Stone Anvil -> parts -> Gear Workbench assembly) is the intended
// replacement, so the flat crafting-table recipes for iron tools/weapons are
// removed here, forcing players through Silent Gear instead. Scoped to iron
// only for now, not diamond/netherite - those stay on vanilla recipes (still
// tier-gated via ProgressiveStages) rather than assuming Silent Gear's own
// higher-tier materials are equivalently balanced without further testing.
ServerEvents.recipes(event => {
    event.remove({ id: 'minecraft:iron_pickaxe' })
    event.remove({ id: 'minecraft:iron_sword' })
    event.remove({ id: 'minecraft:iron_axe' })
    event.remove({ id: 'minecraft:iron_shovel' })
    event.remove({ id: 'minecraft:iron_hoe' })
})
