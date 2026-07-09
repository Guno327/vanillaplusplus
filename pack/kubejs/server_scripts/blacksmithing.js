// instructions.md: "Instead of making metal tools normally have some kinds
// of blacksmithing." Phase 7 only removed iron-tier tool recipes as a
// starting point (see DESIGN.md). The gear overhaul that followed Phase 9
// goes all the way: instructions.md's own words, "all combat weapons are
// either earned through defeating bosses or directly through whatever
// smithing system you have designed... this should apply for tools/armour
// as well" and "remove all other forms of gear progression other than
// this directly expected route." So every vanilla tool/weapon/armor
// recipe across every material tier is removed here, plus Allthemodium's
// own native smithing-upgrade recipes (we only want its raw materials,
// not its parallel gear-progression track - see DESIGN.md's gear overhaul
// section and scripts/gen_gear_materials.py).
//
// Bows/crossbows/armor are new to this removal pass; Silent Gear supports
// all of them natively (GearSwordItem/GearCrossbowItem/GearArmorItem,
// confirmed by reading the installed jar) - only the 5 Epic Fight weapon
// types (dagger/greatsword/longsword/spear/tachi) need a different route,
// handled separately in weapon_smithing.js since Silent Gear has no gear
// type for them.
const VANILLA_TOOL_TIERS = ['wooden', 'stone', 'iron', 'golden', 'diamond']
const VANILLA_TOOL_TYPES = ['pickaxe', 'axe', 'shovel', 'hoe', 'sword']
const VANILLA_ARMOR_TIERS = ['leather', 'iron', 'golden', 'diamond']
const VANILLA_ARMOR_PIECES = ['helmet', 'chestplate', 'leggings', 'boots']
const NETHERITE_SMITHING_TYPES = ['pickaxe', 'axe', 'shovel', 'hoe', 'sword', 'helmet', 'chestplate', 'leggings', 'boots']

const ALLTHEMODIUM_MATERIALS = ['allthemodium', 'vibranium', 'unobtainium']
const ALLTHEMODIUM_SMITHING_TYPES = ['axe', 'boots', 'chestplate', 'helmet', 'hoe', 'leggings', 'mace', 'pickaxe', 'shovel', 'sword']

ServerEvents.recipes(event => {
    for (const tier of VANILLA_TOOL_TIERS) {
        for (const type of VANILLA_TOOL_TYPES) {
            event.remove({ id: `minecraft:${tier}_${type}` })
        }
    }
    for (const tier of VANILLA_ARMOR_TIERS) {
        for (const piece of VANILLA_ARMOR_PIECES) {
            event.remove({ id: `minecraft:${tier}_${piece}` })
        }
    }
    for (const type of NETHERITE_SMITHING_TYPES) {
        event.remove({ id: `minecraft:netherite_${type}_smithing` })
    }
    event.remove({ id: 'minecraft:netherite_upgrade_smithing_template' })
    event.remove({ id: 'minecraft:bow' })
    event.remove({ id: 'minecraft:crossbow' })

    // Recipe ids mirror their full datapack file path including the
    // "smithing/" subfolder (data/allthemodium/recipe/smithing/*.json) -
    // confirmed by reading the actual recipe json after a first attempt
    // without the subfolder silently matched nothing (event.remove()
    // doesn't error on a non-matching id, it just no-ops).
    for (const material of ALLTHEMODIUM_MATERIALS) {
        for (const type of ALLTHEMODIUM_SMITHING_TYPES) {
            event.remove({ id: `allthemodium:smithing/${material}_${type}_smithing` })
        }
        event.remove({ id: `allthemodium:smithing/${material}_upgrade_smithing_template` })
    }
})
