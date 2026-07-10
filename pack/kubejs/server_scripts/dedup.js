// TODO.md item 3: duplicate-resource consolidation. ~40 installed mods meant
// several add their own competing copy of the same underlying material -
// found by a jar-by-jar audit (javap/jar tf against server/mods/*.jar, see
// the session's own report for the full verification trail). Every
// duplicate is hard-consolidated to one canonical item (vanilla first, then
// whichever mod is most central to this pack's material chain - Create and
// its addons like TFMG beat incidental mods like AllTheOres/Stellaris),
// exactly like Phase 10 did for Allthemodium's tools/armor via Silent Gear.
//
// The recipe/loot-table side of each consolidation lives as raw datapack
// overrides under pack/kubejs/data/<modid>/... (same JSON-override pattern
// used throughout this pack) - each override keeps the original recipe's
// id/ingredient but redirects its *output* to the canonical item. This
// script only handles the piece overrides can't: c: tags. Overriding a tag
// JSON file fully replaces it (no merge, per this project's own datapack
// rule), which would silently drop every OTHER mod's entry in that tag too
// - so tag cleanup goes through KubeJS's additive remove() API instead.
//
// Only entries for items that are now genuinely unobtainable (no recipe or
// worldgen produces them anymore) are removed. Where a duplicated metal's
// ore still generates in a dimension the canonical mod doesn't cover
// (nether/end zinc/lead/nickel/aluminum ore - see the report for why), the
// ore items stay in their c:ores/* tag since the tag-based smelting
// recipe still needs to resolve them to the canonical ingot.
ServerEvents.tags('item', event => {
    // --- zinc: create:zinc_ingot is canonical over alltheores:zinc_ingot ---
    event.remove('c:ingots/zinc', 'alltheores:zinc_ingot')
    event.remove('c:nuggets/zinc', 'alltheores:zinc_nugget')
    event.remove('c:storage_blocks/zinc', 'alltheores:zinc_block')
    event.remove('c:raw_materials/zinc', 'alltheores:raw_zinc')
    event.remove('c:storage_blocks/raw_zinc', 'alltheores:raw_zinc_block')
    // zinc_ore/deepslate_zinc_ore no longer generate anywhere (Create's own
    // overworld zinc ore covers that dimension); nether/end/other_zinc_ore
    // still generate and still need to resolve via c:ores/zinc, so they stay.
    event.remove('c:ores/zinc', 'alltheores:zinc_ore')
    event.remove('c:ores/zinc', 'alltheores:deepslate_zinc_ore')

    // --- aluminum: tfmg:aluminum_ingot is canonical over alltheores:aluminum_ingot ---
    // (TFMG's aluminum comes from a completely different bauxite->vat chain
    // with no "raw ore" stage at all, so alltheores:raw_aluminum and
    // alltheores:raw_aluminum_block have no tfmg counterpart to redirect to -
    // left alone, they remain legitimate ATO-native intermediates feeding
    // into the now-redirected ingot smelting recipes.)
    event.remove('c:ingots/aluminum', 'alltheores:aluminum_ingot')
    event.remove('c:nuggets/aluminum', 'alltheores:aluminum_nugget')
    event.remove('c:storage_blocks/aluminum', 'alltheores:aluminum_block')
    event.remove('c:plates/aluminum', 'alltheores:aluminum_plate')
    event.remove('c:ores/aluminum', 'alltheores:aluminum_ore')
    event.remove('c:ores/aluminum', 'alltheores:deepslate_aluminum_ore')

    // --- lead: tfmg:lead_ingot is canonical over alltheores:lead_ingot ---
    event.remove('c:ingots/lead', 'alltheores:lead_ingot')
    event.remove('c:nuggets/lead', 'alltheores:lead_nugget')
    event.remove('c:storage_blocks/lead', 'alltheores:lead_block')
    event.remove('c:raw_materials/lead', 'alltheores:raw_lead')
    event.remove('c:storage_blocks/raw_lead', 'alltheores:raw_lead_block')
    event.remove('c:plates/lead', 'alltheores:lead_plate')
    event.remove('c:ores/lead', 'alltheores:lead_ore')
    event.remove('c:ores/lead', 'alltheores:deepslate_lead_ore')

    // --- nickel: tfmg:nickel_ingot is canonical over alltheores:nickel_ingot ---
    event.remove('c:ingots/nickel', 'alltheores:nickel_ingot')
    event.remove('c:nuggets/nickel', 'alltheores:nickel_nugget')
    event.remove('c:storage_blocks/nickel', 'alltheores:nickel_block')
    event.remove('c:raw_materials/nickel', 'alltheores:raw_nickel')
    event.remove('c:storage_blocks/raw_nickel', 'alltheores:raw_nickel_block')
    event.remove('c:plates/nickel', 'alltheores:nickel_plate')
    event.remove('c:ores/nickel', 'alltheores:nickel_ore')
    event.remove('c:ores/nickel', 'alltheores:deepslate_nickel_ore')

    // --- steel: tfmg:steel_ingot is canonical over stellaris:steel_ingot ---
    // tfmg:steel_ingot is this pack's Tier 6 TFMG milestone lock (see
    // DESIGN.md's "Post-Tier-4 endgame automation deepening" section);
    // stellaris shipped a fully parallel ore->ingot chain for its own
    // steel_ingot that had no ProgressiveStages lock at all, bypassing the
    // milestone. Its steel-ore worldgen is fully removed (see the
    // stellaris neoforge/biome_modifier overrides) since vanilla iron - the
    // real feedstock for TFMG's iron->steel industrial chain - already
    // covers every dimension stellaris placed steel ore in, so nothing is
    // stranded without a source.
    event.remove('c:ingots/steel', 'stellaris:steel_ingot')
    event.remove('c:nuggets/steel', 'stellaris:steel_nugget')
    event.remove('c:storage_blocks/steel', 'stellaris:steel_block')
    event.remove('c:raw_materials/steel', 'stellaris:raw_steel_ingot')
    event.remove('c:storage_blocks/raw_steel', 'stellaris:raw_steel_block')
    event.remove('c:ores/steel', 'stellaris:steel_ore')
    event.remove('c:ores/steel', 'stellaris:deepslate_steel_ore')
    event.remove('c:ores/steel', 'stellaris:moon_steel_ore')
})

// --- TODO.md item 4 wave-1 finding, folded into this pattern at wave 2:
// create_nj (Create: Stuff & Netherite Additions) ships its own SECOND
// netherite jetpack (create_nj:netherite_jetpack_chestplate) that fully
// duplicates create_sa:netherite_jetpack_chestplate (Create Stuff &
// Additions' native top rung of this pack's copper->andesite->brass->
// netherite jetpack ladder) - same chestplate slot, same functional item,
// different recipe. Unlike the metal dedups above, there's no shared c:
// tag to clean up here (jetpacks aren't tagged together), so the redirect
// is a pure recipe-output override: pack/kubejs/data/create_nj/recipe/
// netherite_jetpack_recipe.json keeps create_nj's own mechanical_crafting
// pattern/ingredients (diamond + create:encased_fan + create_nj:
// nether_engine + netherite_ingot, verified byte-for-byte against the
// installed create_sna-1.2-neoforge-1.21.1.jar's data/create_nj/recipe/
// netherite_jetpack_recipe.json) but changes result.id to
// create_sa:netherite_jetpack_chestplate - crafting the create_nj recipe
// now hands the player the canonical item instead of a duplicate one.
// create_nj:netherite_jetpack_chestplate itself becomes unobtainable
// through normal survival play (no recipe produces it, nothing drops it),
// but per the recorded decision its induction_age.toml tier lock stays in
// place anyway (defense in depth, matching this pack's existing practice
// of not trusting "unobtainable" alone to close a tier-bypass hole - see
// the aluminum precedent above). create_nj stays installed and unaffected
// for its other reason for being here: the Netherite Exoskeleton.
