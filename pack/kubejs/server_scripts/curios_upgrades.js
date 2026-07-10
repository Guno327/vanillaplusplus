// TODO.md item 5 ("Curios as a discoverable/upgradeable player-ability
// system") - duplicate-combine upgrade mechanic. Recorded decision:
// combining 2x the same Artifacts (13.2.1) trinket found while exploring
// produces 1x the same trinket with a bonus stat, via a data component set
// on the crafted result. This is deliberately generic - one rule per Curios
// SLOT TYPE (see SLOT_BONUS below), not a bespoke recipe per item - so it
// works across all of Artifacts' Java-coded abilities without touching a
// single one of their internals: every artifact is component-free by
// default, so stamping a component on a shapeless recipe's OUTPUT can't
// collide with anything the item's own ability code reads.
//
// The task brief said "47 Java-coded abilities" - counting Artifacts
// 13.2.1's own data/artifacts/tags/item/artifacts.json master tag
// programmatically (not guessed) puts the real number at 48. Every one of
// the 48 is accounted for below: 45 across the 6 ARTIFACT_SLOTS groups + 1
// HELD_ITEMS (umbrella) + 2 deliberately excluded (see EXCLUDED ON PURPOSE).
// Same 48-item ground truth used in scripts/gen_structure_loot.py's own
// curation table for the loot-drop side of this feature.
//
// GROUND-TRUTH DEVIATION FROM THE LITERAL BRIEF: the orchestrator's brief
// said to use the vanilla `minecraft:attribute_modifiers` component. That
// can't be literal for most of these items, verified by decompiling the
// actually-installed jars rather than assuming:
//   - Vanilla's `minecraft:attribute_modifiers` component only applies
//     while an item sits in one of the vanilla EquipmentSlotGroup slots
//     (mainhand/offhand/head/chest/legs/feet/body/any) - confirmed via
//     javap on net.minecraft.world.item.component.ItemAttributeModifiers
//     and its Entry record in the installed 1.21.1 server jar.
//   - Artifacts trinkets are worn in *Curios* slots, a separate inventory
//     capability vanilla equipment-slot modifiers never see.
//   - Curios 9.5.1 ships a parallel, purpose-built data component for
//     exactly this - top.theillusivec4.curios.api.CurioAttributeModifiers,
//     registered as its own DataComponentType `curios:attribute_modifiers`
//     in top.theillusivec4.curios.common.CuriosRegistry (confirmed via
//     javap + class-file string-pool inspection of the installed jar).
//     Its JSON shape is FIELD-FOR-FIELD IDENTICAL to vanilla's - same flat
//     {modifiers:[{type,id,amount,operation,slot}], show_in_tooltip} shape,
//     same AttributeModifier.MAP_CODEC reused directly for the flattened
//     id/amount/operation - just with `slot` being a free-form Curios
//     slot-type string ("head"/"necklace"/"hands"/"feet"/"belt"/"curio")
//     instead of an EquipmentSlotGroup enum value.
// So: curio-worn items below get `curios:attribute_modifiers`; the one
// exception, artifacts:umbrella (held in mainhand/offhand, not worn as a
// curio at all - see HELD_ITEMS), gets the literal vanilla
// `minecraft:attribute_modifiers` component the brief asked for, since
// that's the component that actually governs a held item.
//
// EXCLUDED ON PURPOSE: artifacts:everlasting_beef and artifacts:eternal_
// steak. Both are food items consumed instantly on use, not equipped/held
// persistently, so an attribute-modifier bonus on the stack would never get
// a chance to apply. Artifacts already ships its own upgrade path for this
// exact pair (smelting/smoking/campfire-cooking everlasting_beef into
// eternal_steak - see data/artifacts/recipe/eternal_steak_*.json in the
// installed jar), so nothing is lost by leaving them out of this mechanic.
//
// CAP ON REPEAT COMBINES: task brief asked for a second combine on an
// already-upgraded artifact to either no-op or be capped. Chose: capped,
// implicitly, with no extra guard code. Each recipe's output component set
// is a FIXED single-entry modifier list (not derived from the two input
// stacks' own components), and a shapeless recipe here matches on item id
// only (KubeJS's default ingredient match ignores components) - so feeding
// two already-upgraded copies back through the same recipe just produces
// the exact same capped result again, not a stacking +2. No separate
// "is this already upgraded" check needed.
//
// ITEM -> CURIOS SLOT mapping below is transcribed verbatim from the
// installed Artifacts 13.2.1 jar's data/artifacts/tags/item/slot/{belt,
// feet,hands,head,face,necklace,all}.json (ground-truthed by extracting the
// jar, not guessed). "face" items (snorkel, night_vision_goggles) fold into
// the "head" Curios slot per Artifacts' own data/curios/tags/item/head.json,
// which lists both #artifacts:slot/head and #artifacts:slot/face as sources
// for the same Curios "head" slot tag.
const ARTIFACT_SLOTS = {
    belt: [
        'cloud_in_a_bottle', 'obsidian_skull', 'antidote_vessel',
        'universal_attractor', 'crystal_heart', 'helium_flamingo',
        'chorus_totem', 'warp_drive',
    ],
    feet: [
        'aqua_dashers', 'bunny_hoppers', 'kitty_slippers', 'running_shoes',
        'snowshoes', 'steadfast_spikes', 'flippers', 'rooted_boots',
        'strider_shoes',
    ],
    hands: [
        'digging_claws', 'feral_claws', 'power_glove', 'fire_gauntlet',
        'pocket_piston', 'vampiric_glove', 'golden_hook', 'onion_ring',
        'pickaxe_heater', 'withered_bracelet',
    ],
    head: [
        'plastic_drinking_hat', 'novelty_drinking_hat', 'villager_hat',
        'superstitious_hat', 'cowboy_hat', 'anglers_hat',
        'snorkel', 'night_vision_goggles', // "face" items, folded into head
    ],
    necklace: [
        'lucky_scarf', 'scarf_of_invisibility', 'cross_necklace',
        'panic_necklace', 'shock_pendant', 'flame_pendant', 'thorn_pendant',
        'charm_of_sinking', 'charm_of_shrinking',
    ],
    curio: ['whoopee_cushion'], // Curios' own generic catch-all slot
}
// Held in mainhand/offhand, not a Curios item at all (see the umbrella
// exception in the deviation note above).
const HELD_ITEMS = ['umbrella']
// Deliberately excluded - see EXCLUDED ON PURPOSE above: everlasting_beef,
// eternal_steak (food, consumed on use, no persistent equip slot).

// One bonus stat per Curios slot type - keeps this generic (a rule per
// slot, not per item) while still giving each slot a thematically sensible
// bonus. All modest per-combine amounts per the brief ("a lucky exploration
// find, not a guaranteed power spike").
const SLOT_BONUS = {
    head: { attribute: 'minecraft:generic.armor', amount: 1.0, operation: 'add_value' }, // +1 armor
    necklace: { attribute: 'minecraft:generic.max_health', amount: 2.0, operation: 'add_value' }, // +1 heart
    hands: { attribute: 'minecraft:generic.attack_speed', amount: 0.02, operation: 'add_multiplied_total' }, // +2% attack speed
    feet: { attribute: 'minecraft:generic.movement_speed', amount: 0.04, operation: 'add_multiplied_total' }, // +4% movement speed
    belt: { attribute: 'minecraft:generic.armor_toughness', amount: 1.0, operation: 'add_value' }, // +1 armor toughness
    curio: { attribute: 'minecraft:generic.luck', amount: 1.0, operation: 'add_value' }, // +1 luck (whoopee_cushion only)
}
const HELD_BONUS = { attribute: 'minecraft:generic.armor', amount: 1.0, operation: 'add_value' } // umbrella: +1 armor while held

ServerEvents.recipes(event => {
    // Curio-worn items: curios:attribute_modifiers, slot = the item's own
    // Curios slot-type string.
    for (const slot in ARTIFACT_SLOTS) {
        const bonus = SLOT_BONUS[slot]
        for (const name of ARTIFACT_SLOTS[slot]) {
            const itemId = `artifacts:${name}`
            const modifierId = `vanillaplusplus:artifact_upgrade_${name}`
            const components = `{modifiers:[{type:"${bonus.attribute}",id:"${modifierId}",amount:${bonus.amount},operation:"${bonus.operation}",slot:"${slot}"}],show_in_tooltip:true}`
            const output = Item.of(`${itemId}[curios:attribute_modifiers=${components}]`)
            event.shapeless(output, [itemId, itemId]).id(`vanillaplusplus:artifact_upgrade/${name}`)
        }
    }

    // Held items (umbrella): vanilla minecraft:attribute_modifiers, slot
    // group "hand" (covers both mainhand and offhand).
    for (const name of HELD_ITEMS) {
        const itemId = `artifacts:${name}`
        const modifierId = `vanillaplusplus:artifact_upgrade_${name}`
        const components = `{modifiers:[{type:"${HELD_BONUS.attribute}",id:"${modifierId}",amount:${HELD_BONUS.amount},operation:"${HELD_BONUS.operation}",slot:"hand"}],show_in_tooltip:true}`
        const output = Item.of(`${itemId}[minecraft:attribute_modifiers=${components}]`)
        event.shapeless(output, [itemId, itemId]).id(`vanillaplusplus:artifact_upgrade/${name}`)
    }
})
