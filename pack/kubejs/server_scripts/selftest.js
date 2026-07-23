// Release L1 layer: `/vpp_selftest` - a data/parse/count/resolve assertion
// suite covering the pack's major systems, run against the actually-booted
// server (not a mock). Companion runner: scripts/tests/l1_selftest.py
// (issues the command via cmd_fifo, greps the final machine-readable
// summary line, exits nonzero on FAIL).
//
// Design note per DECISIONS.md's L1 caveat: there is no pre-existing
// concrete 20-assertion list committed anywhere in this repo (DECISIONS.md/
// HANDOFF.md only describe the *shape* - "data/parse/count/resolve
// assertions + sell/leaderboard round-trips" - the actual research brief
// that would have enumerated them was never captured to a durable file).
// This assertion set was authored fresh against this pack's real systems,
// using API surfaces already proven reachable from Rhino elsewhere in this
// codebase (economy.js/leaderboard.js/curios_upgrades.js precedent) or
// verified directly against the installed jars via javap this session.
// Every check is wrapped so one failure can't take down the rest.
//
// CONSOLE-SAFE BY DESIGN: this command is driven via cmd_fifo (server
// console), which has no attached ServerPlayer - the standing boot-test
// methodology in this project never has a real client connected. The
// small number of genuinely player-dependent checks (economy give/sell
// round-trip, per-player stage/bank lookups) detect that and report SKIP
// rather than a fake pass or a hard fail; PASS/FAIL is computed over the
// executed (non-skipped) checks only, with skip count disclosed separately
// in the summary line. Driving those under a real player is exactly the
// L2/L3 boundary this pack's test architecture already draws (headless
// client smoke / live join), not something console-only L1 can honestly
// claim to cover.
//
// Vanilla registry/recipe access goes through ctx.source.server (a plain
// net.minecraft.server.MinecraftServer via CommandSourceStack.getServer())
// rather than guessing at KubeJS convenience globals, using the same
// "Java.loadClass + call the real vanilla method" pattern leaderboard.js
// already established. Top-level names are ST_-prefixed to avoid
// redeclaration collisions with other server_scripts files - KubeJS loads
// all server_scripts into one shared Rhino scope (confirmed the hard way:
// an earlier draft of this file collided with leaderboard.js's own
// ResourceLocationClass/TIER_IDS/SKILL_CATEGORIES/SkillsAPIClass/
// NumismaticsClass/OpenPACServerAPIClass names and threw
// "TypeError: redeclaration of const" at boot, caught by this same L0/L1
// boot-test loop).

const ST_TIER_IDS = [
    'rootborn', 'andesite_age', 'brass_age', 'precision_age', 'induction_age',
    'starforged_age', 'lunar_frontier', 'martian_frontier', 'inner_system', 'jovian_frontier',
]
// Issue #71 ("Expand Skill Trees / Categories"): 12 -> 23 categories - kept
// in sync by hand with gen_skill_tree.py's CATEGORY_SPECS ids.
const ST_SKILL_CATEGORIES = [
    'alchemy', 'bows', 'building', 'cooking', 'daggers', 'enchanting',
    'exploration', 'farming', 'fishing', 'greatswords', 'longswords',
    'magic', 'mining', 'running', 'sailing', 'smithing', 'spears',
    'swimming', 'swords', 'tachi', 'taming', 'trading', 'woodcutting',
]
// Issue #71 also expanded 15 -> 34 skill nodes per category - kept in sync
// by hand with gen_skill_tree.py's per-category node count (12 -> 23
// categories x 15 -> 34 nodes = 782 total, per
// pack/kubejs/data/puffish_skills/puffish_skills/categories/*/skills.json).
// Issue #77: this drifted out of sync with the actual shipped node count
// once before (asserted 15 for two release cycles after #71 shipped 34) -
// scripts/ci/check_selftest_skill_sync.py now cross-checks both this
// constant and ST_SKILL_CATEGORIES above against the real generated data on
// every fast-tier CI run so that can't happen silently again.
const ST_SKILL_NODE_COUNT_PER_CATEGORY = 34
const ST_COIN_ITEM_IDS = [
    'numismatics:spur', 'numismatics:bevel', 'numismatics:sprocket',
    'numismatics:cog', 'numismatics:crown', 'numismatics:sun',
]
const ST_SAMPLE_ARTIFACT_UPGRADE_RECIPE = 'vanillaplusplus:artifact_upgrade/umbrella'
const ST_EXPECTED_ARTIFACT_UPGRADE_RECIPE_COUNT = 46
const ST_ARTIFACTS_MASTER_TAG_MIN_SIZE = 48
// storage.js patches these two down to iron-tier for Andesite Age (see
// pack/kubejs/server_scripts/storage.js header) - a minecraft:comparator
// here would need Nether quartz and soft-lock the dumb storage quest
// (issue #25), so this asserts the fix stays in place.
// NOTE: storage.js REMOVES the stock toms_storage:* recipe ids and re-adds
// the patched recipes under vanillaplusplus:*_early_tier ids - query those.
const ST_STORAGE_EARLY_TIER_RECIPE_IDS = ['vanillaplusplus:inventory_connector_early_tier', 'vanillaplusplus:storage_terminal_early_tier']

const ST_ResourceLocationClass = Java.loadClass('net.minecraft.resources.ResourceLocation')
const ST_RegistriesClass = Java.loadClass('net.minecraft.core.registries.Registries')
const ST_TagKeyClass = Java.loadClass('net.minecraft.tags.TagKey')
const ST_ComponentClass = Java.loadClass('net.minecraft.network.chat.Component')

let ST_SkillsAPIClass = null
try {
    ST_SkillsAPIClass = Java.loadClass('net.puffish.skillsmod.api.SkillsAPI')
} catch (e) {
    console.error('[vpp selftest] SkillsAPI class failed to load: ' + e)
}
let ST_NumismaticsClass = null
try {
    ST_NumismaticsClass = Java.loadClass('dev.ithundxr.createnumismatics.Numismatics')
} catch (e) {
    console.error('[vpp selftest] Numismatics class failed to load: ' + e)
}
// javap-confirmed (dev.ithundxr.createnumismatics.content.backend.
// GlobalBankManager, CreateNumismatics-1.0.20+neoforge-mc1.21.1.jar):
// getAccount(UUID) is a bare accounts.get(uuid) - it returns null for a
// player with no bank account yet (ground-truthed via a real L3 run: a
// fresh test player throws "Cannot call method getBalance of null").
// getAccount(Player) is the one that actually get-or-creates
// (getOrCreateAccount(player.getUUID(), Type.PLAYER)), but calling it
// directly from Rhino with a real ServerPlayer throws "InternalError: ...
// is ambiguous" against the UUID overload. Calling getOrCreateAccount(UUID,
// Type) directly sidesteps both problems: unambiguous (single overload) and
// really get-or-create.
let ST_BankAccountTypeClass = null
try {
    ST_BankAccountTypeClass = Java.loadClass('dev.ithundxr.createnumismatics.content.backend.BankAccount$Type')
} catch (e) {
    console.error('[vpp selftest] Numismatics BankAccount$Type failed to load: ' + e)
}
let ST_OpenPACServerAPIClass = null
try {
    ST_OpenPACServerAPIClass = Java.loadClass('xaero.pac.common.server.api.OpenPACServerAPI')
} catch (e) {
    console.error('[vpp selftest] OpenPACServerAPI class failed to load: ' + e)
}

function stRl(id) {
    return ST_ResourceLocationClass.parse(id)
}

function stItemRegistry(server) {
    return server.registryAccess().registryOrThrow(ST_RegistriesClass.ITEM)
}

// Each check: (server, player|null) -> { pass, detail } or { skip, detail }.
// Throwing is caught by the runner and counted as a fail with the
// exception text as detail - never silently swallowed.
const ST_CHECKS = []
function stCheck(name, fn) { ST_CHECKS.push({ name: name, fn: fn }) }

stCheck('server reachable', server => {
    return { pass: server != null, detail: 'ok' }
})

stCheck('overworld level reachable', server => {
    // .dimension() is a zero-arg accessor that Rhino/KubeJS's bean-property
    // convention exposes as a pre-resolved property (not callable) - use
    // ServerLevel's own toString() (already human-readable, e.g.
    // "ServerLevel[world]") rather than chaining further accessors.
    let overworld = server.overworld()
    return { pass: overworld != null, detail: overworld ? String(overworld) : 'null' }
})

stCheck('ProgressiveStages: 10 tier ids resolve on player.stages without throwing', (server, player) => {
    if (!player) return { skip: true, detail: 'no player online (console-only L1 run)' }
    for (let i = 0; i < ST_TIER_IDS.length; i++) {
        player.stages.has(ST_TIER_IDS[i]) // boolean; throwing is the failure mode under test
    }
    return { pass: true, detail: ST_TIER_IDS.length + ' ids resolved' }
})

stCheck('SkillsAPI: 23 skill categories all present', () => {
    if (!ST_SkillsAPIClass) return { pass: false, detail: 'SkillsAPI class unavailable' }
    let missing = []
    for (let i = 0; i < ST_SKILL_CATEGORIES.length; i++) {
        let catRl = ST_ResourceLocationClass.fromNamespaceAndPath('puffish_skills', ST_SKILL_CATEGORIES[i])
        let opt = ST_SkillsAPIClass.getCategory(catRl)
        if (!opt.isPresent()) missing.push(ST_SKILL_CATEGORIES[i])
    }
    return { pass: missing.length === 0, detail: missing.length === 0 ? 'all 23 present' : 'missing: ' + missing.join(',') }
})

stCheck('SkillsAPI: all 23 skill categories have an Experience/level source (points wiring)', () => {
    if (!ST_SkillsAPIClass) return { pass: false, detail: 'SkillsAPI class unavailable' }
    let missing = []
    for (let i = 0; i < ST_SKILL_CATEGORIES.length; i++) {
        let catRl = ST_ResourceLocationClass.fromNamespaceAndPath('puffish_skills', ST_SKILL_CATEGORIES[i])
        let catOpt = ST_SkillsAPIClass.getCategory(catRl)
        if (!catOpt.isPresent()) { missing.push(ST_SKILL_CATEGORIES[i] + '(category missing)'); continue }
        if (!catOpt.get().getExperience().isPresent()) missing.push(ST_SKILL_CATEGORIES[i])
    }
    return { pass: missing.length === 0, detail: missing.length === 0 ? 'all 23 wired' : 'missing Experience: ' + missing.join(',') }
})

// issue #24 ("plenty of skill points but unable to allocate them") ground-
// truthed root cause: every one of the 12 categories' skills.json had ZERO
// nodes with "root": true (scripts/gen_skill_tree.py never set it). Per
// javap against the installed puffish_skills-0.18.1-1.21-neoforge.jar,
// net.puffish.skillsmod.server.data.CategoryData.getSkillState only reaches
// AVAILABLE/AFFORDABLE (clickable) via a root node or a `normal` edge from
// an already-unlocked node - with unlockedSkills starting empty for every
// player and zero roots, every node in every category was permanently
// LOCKED regardless of points held. Fixed in scripts/gen_skill_tree.py
// (n0 now carries "root": true) + regenerated pack/kubejs/data/
// puffish_skills/puffish_skills/categories/*/skills.json.
//
// This exact invariant ("at least one root node per category") is NOT
// re-checked here at L1: the public net.puffish.skillsmod.api surface only
// exposes per-node unlock STATE via Skill#getState(ServerPlayer), which
// needs a real connected player - this command runs over cmd_fifo with no
// attached ServerPlayer (see this file's own header comment), so that check
// would always SKIP under the L1 harness and never actually catch a
// regression. There is also no way to read the raw skills.json "root" field
// from KubeJS/Rhino directly - java.io/java.nio are hard-blocked by this
// pack's installed KubeJS's own kubejs.classfilter.txt (ground-truthed the
// same way food_selftest.js's config/solonion.json check documents; see
// that file's comment for the extraction). The static, always-reliable,
// pre-boot check for this invariant lives instead in
// scripts/ci/check_skill_trees.py (run via scripts/ci/run_all.py) - it
// parses skills.json directly and asserts every category has >=1 root node
// plus that every "definition" reference resolves, catching this bug class
// (and the silent-node-drop variant) well before a boot is ever attempted.
// What L1 CAN and does check here instead: that every category's skill
// node count survived config parsing intact (34/34) - a bad "definition"
// reference doesn't fail the datapack load, it silently drops just that
// node (net.puffish.skillsmod.config.skill.SkillConfig.parse), which would
// show up here as a category with fewer than 34 skills reachable through
// the API.
stCheck('SkillsAPI: all 23 skill categories retained their full 34-node skill count after parsing', () => {
    if (!ST_SkillsAPIClass) return { pass: false, detail: 'SkillsAPI class unavailable' }
    let bad = []
    for (let i = 0; i < ST_SKILL_CATEGORIES.length; i++) {
        let catRl = ST_ResourceLocationClass.fromNamespaceAndPath('puffish_skills', ST_SKILL_CATEGORIES[i])
        let catOpt = ST_SkillsAPIClass.getCategory(catRl)
        if (!catOpt.isPresent()) { bad.push(ST_SKILL_CATEGORIES[i] + '(category missing)'); continue }
        let count = catOpt.get().streamSkills().toArray().length
        if (count !== ST_SKILL_NODE_COUNT_PER_CATEGORY) bad.push(ST_SKILL_CATEGORIES[i] + '=' + count)
    }
    return { pass: bad.length === 0, detail: bad.length === 0 ? ('all 23 have ' + ST_SKILL_NODE_COUNT_PER_CATEGORY + '/' + ST_SKILL_NODE_COUNT_PER_CATEGORY + ' nodes') : 'bad counts: ' + bad.join(',') }
})

stCheck('Numismatics: bank account/balance reachable for a player', (server, player) => {
    if (!ST_NumismaticsClass) return { pass: false, detail: 'Numismatics class unavailable' }
    if (!ST_BankAccountTypeClass) return { pass: false, detail: 'Numismatics BankAccount$Type class unavailable' }
    if (!player) return { skip: true, detail: 'no player online (console-only L1 run)' }
    // getOrCreateAccount(player.uuid, Type.PLAYER), not getAccount(player) or
    // getAccount(player.uuid) - see ST_BankAccountTypeClass's own comment
    // above for the full javap-verified reasoning: getAccount(Player) is
    // ambiguous for Rhino against a real ServerPlayer, and getAccount(UUID)
    // is a bare map lookup that returns null for a player with no account
    // yet (both ground-truthed against real L3 runs). getOrCreateAccount is
    // the single unambiguous overload that actually creates one. `.uuid`
    // (a property on KubeJS's ServerPlayer wrapper), not `.getUUID()` - the
    // latter is not callable from Rhino on this wrapper.
    let account = ST_NumismaticsClass.BANK.getOrCreateAccount(player.uuid, ST_BankAccountTypeClass.PLAYER)
    let balance = account.getBalance()
    return { pass: typeof balance === 'number' && balance >= 0, detail: 'balance=' + balance }
})

stCheck('OpenPACServerAPI: party manager reachable', server => {
    if (!ST_OpenPACServerAPIClass) return { pass: false, detail: 'OpenPACServerAPI class unavailable' }
    let partyManager = ST_OpenPACServerAPIClass.get(server).getPartyManager()
    let parties = partyManager.getAllStream().toArray()
    return { pass: parties != null, detail: (parties ? parties.length : 0) + ' parties' }
})

stCheck('coin items (6 denominations) all resolve to a real item', server => {
    let registry = stItemRegistry(server)
    let missing = []
    for (let i = 0; i < ST_COIN_ITEM_IDS.length; i++) {
        if (!registry.containsKey(stRl(ST_COIN_ITEM_IDS[i]))) missing.push(ST_COIN_ITEM_IDS[i])
    }
    return { pass: missing.length === 0, detail: missing.length === 0 ? 'all 6 resolve' : 'missing: ' + missing.join(',') }
})

stCheck('sample cross-mod items resolve (dedup canonical + tier-gate items)', server => {
    let ids = [
        'create:zinc_ingot', 'tfmg:aluminum_ingot', 'tfmg:steel_ingot',
        'minecraft:elytra', 'minecraft:totem_of_undying',
        'create_sa:netherite_jetpack_chestplate', 'waystones:waystone',
    ]
    let registry = stItemRegistry(server)
    let missing = []
    for (let i = 0; i < ids.length; i++) {
        if (!registry.containsKey(stRl(ids[i]))) missing.push(ids[i])
    }
    return { pass: missing.length === 0, detail: missing.length === 0 ? 'all ' + ids.length + ' resolve' : 'missing: ' + missing.join(',') }
})

stCheck('recipe manager: total recipe count is sane (> 1000)', server => {
    let count = server.getRecipeManager().getRecipes().size()
    return { pass: count > 1000, detail: count + ' recipes' }
})

stCheck('recipe count: vanillaplusplus:artifact_upgrade/* == 46', server => {
    let recipes = server.getRecipeManager().getRecipes().toArray()
    let n = 0
    for (let i = 0; i < recipes.length; i++) {
        if (String(recipes[i].id()).indexOf('vanillaplusplus:artifact_upgrade/') === 0) n++
    }
    return { pass: n === ST_EXPECTED_ARTIFACT_UPGRADE_RECIPE_COUNT, detail: n + '/' + ST_EXPECTED_ARTIFACT_UPGRADE_RECIPE_COUNT }
})

stCheck('sample recipe resolves: ' + ST_SAMPLE_ARTIFACT_UPGRADE_RECIPE, server => {
    let opt = server.getRecipeManager().byKey(stRl(ST_SAMPLE_ARTIFACT_UPGRADE_RECIPE))
    return { pass: opt.isPresent(), detail: opt.isPresent() ? 'found' : 'not found' }
})

stCheck('storage.js early-tier patch: inventory_connector/storage_terminal resolve and use no comparator', server => {
    // NOTE: found empirically in L1 - Rhino cannot call Ingredient's own
    // members here (TypeError "Cannot find function getItems" /
    // "...kjs$getStackArray" despite both being public at runtime): KubeJS's
    // class shutter hides net.minecraft.world.item.crafting.Ingredient, so
    // Rhino only exposes members of its visible supertypes (Object +
    // java.util.function.Predicate). Predicate#test(ItemStack) is therefore
    // the one reliable probe: ask each ingredient whether it would accept a
    // comparator.
    let comparatorStack = Item.of('minecraft:comparator')
    let bad = []
    for (let i = 0; i < ST_STORAGE_EARLY_TIER_RECIPE_IDS.length; i++) {
        let id = ST_STORAGE_EARLY_TIER_RECIPE_IDS[i]
        let opt = server.getRecipeManager().byKey(stRl(id))
        if (!opt.isPresent()) { bad.push(id + ':missing'); continue }
        let ingredients = opt.get().value().getIngredients().toArray()
        for (let j = 0; j < ingredients.length; j++) {
            if (ingredients[j].test(comparatorStack)) bad.push(id + ':accepts-comparator')
        }
    }
    return { pass: bad.length === 0, detail: bad.length === 0 ? 'both resolve, no comparator' : bad.join(',') }
})

// #49 (ProgressiveStages dropped): tier_gating.js is now the ONLY thing
// keeping these families behind their tier - the mod's lock lists are gone,
// so if one of these recipes silently stops applying (a mod renames an item,
// an upstream recipe id changes and the event.remove() no-ops), the item
// quietly becomes craftable on day one with no error anywhere. Asserts each
// gated recipe both resolves AND actually demands its tier material, using
// the same Predicate#test probe as the storage.js check above (KubeJS's
// class shutter hides Ingredient's own members - see that note).
const ST_TIER_GATED_RECIPES = [
    { id: 'vanillaplusplus:warp_stone_induction_tier', tier: 'minecraft:netherite_ingot' },
    { id: 'vanillaplusplus:iron_backpack_andesite_tier', tier: 'create:andesite_alloy' },
    { id: 'vanillaplusplus:gold_backpack_brass_tier', tier: 'create:brass_ingot' },
    { id: 'vanillaplusplus:stack_upgrade_starter_andesite_tier', tier: 'create:andesite_alloy' },
    { id: 'vanillaplusplus:stack_upgrade_tier_2_brass_tier', tier: 'create:brass_ingot' },
    { id: 'vanillaplusplus:copper_wand_andesite_tier', tier: 'create:andesite_alloy' },
    { id: 'vanillaplusplus:iron_wand_andesite_tier', tier: 'create:andesite_alloy' },
    { id: 'vanillaplusplus:diamond_wand_brass_tier', tier: 'create:brass_ingot' },
    { id: 'vanillaplusplus:magic_bag_1_andesite_tier', tier: 'create:andesite_alloy' },
    { id: 'vanillaplusplus:magic_bag_2_brass_tier', tier: 'create:brass_ingot' },
    { id: 'vanillaplusplus:crafting_terminal_brass_tier', tier: 'create:brass_ingot' },
    { id: 'vanillaplusplus:wireless_terminal_brass_tier', tier: 'create:brass_ingot' },
    { id: 'vanillaplusplus:ore_excavation_drill_andesite_tier', tier: 'create:andesite_alloy' },
    // #70: Sophisticated Storage - the container block ladder.
    { id: 'vanillaplusplus:iron_barrel_andesite_tier', tier: 'create:andesite_alloy' },
    { id: 'vanillaplusplus:iron_chest_andesite_tier', tier: 'create:andesite_alloy' },
    { id: 'vanillaplusplus:iron_shulker_box_andesite_tier', tier: 'create:andesite_alloy' },
    { id: 'vanillaplusplus:gold_barrel_brass_tier', tier: 'create:brass_ingot' },
    { id: 'vanillaplusplus:gold_chest_brass_tier', tier: 'create:brass_ingot' },
    { id: 'vanillaplusplus:gold_shulker_box_brass_tier', tier: 'create:brass_ingot' },
    { id: 'vanillaplusplus:storage_stack_upgrade_tier_1_andesite_tier', tier: 'create:andesite_alloy' },
    { id: 'vanillaplusplus:storage_stack_upgrade_tier_3_brass_tier', tier: 'create:brass_ingot' },
    // #70: Sophisticated Storage - the portable tier-upgrade items, a second
    // independent path to the same iron/gold tiers (see tier_gating.js).
    { id: 'vanillaplusplus:basic_to_iron_tier_upgrade_andesite_tier', tier: 'create:andesite_alloy' },
    { id: 'vanillaplusplus:copper_to_iron_tier_upgrade_andesite_tier', tier: 'create:andesite_alloy' },
    { id: 'vanillaplusplus:basic_to_gold_tier_upgrade_brass_tier', tier: 'create:brass_ingot' },
    { id: 'vanillaplusplus:iron_to_gold_tier_upgrade_brass_tier', tier: 'create:brass_ingot' },
    { id: 'vanillaplusplus:copper_to_gold_tier_upgrade_brass_tier', tier: 'create:brass_ingot' },
]

stCheck('tier_gating.js: every gated recipe resolves and demands its tier material (#49)', server => {
    let bad = []
    for (let i = 0; i < ST_TIER_GATED_RECIPES.length; i++) {
        let entry = ST_TIER_GATED_RECIPES[i]
        let opt = server.getRecipeManager().byKey(stRl(entry.id))
        if (!opt.isPresent()) { bad.push(entry.id + ':missing'); continue }
        let tierStack = Item.of(entry.tier)
        let ingredients = opt.get().value().getIngredients().toArray()
        let demands = false
        for (let j = 0; j < ingredients.length; j++) {
            if (ingredients[j].test(tierStack)) { demands = true; break }
        }
        if (!demands) bad.push(entry.id + ':missing-' + entry.tier)
    }
    return {
        pass: bad.length === 0,
        detail: bad.length === 0 ? (ST_TIER_GATED_RECIPES.length + ' gated recipes verified') : bad.join(','),
    }
})

// #61 (recursive recipe-reachability audit) - PM review of PR #106 found the
// offline jar/KubeJS-script scan (scripts/audit_progression.py) cannot see
// what tier_gating.js actually did at runtime (it can only best-effort parse
// the JS source, and imperative loops/mutation are provably unparseable in
// general), so it isn't authoritative and both regressed on the very two
// false positives #61 exists to stop: `create:track_station` (previously
// misidentified via an unrelated recipe/filename match) and
// `refinedstorage:controller` (previously matched against RS's own
// `refinedstorage:recoloring` variant, not its real crafting recipe).
//
// SECOND ROUND (PM review, live boot.yml run against this branch): the
// first version of the track_station check hardcoded recipe id
// `create:track_station` - but Create doesn't key its crafting recipe ids
// after the output item; the real id (confirmed against data/create/recipe/
// crafting/kinetics/track_station.json in the pinned create-6.0.10 jar) is
// `create:crafting/kinetics/track_station`. That hardcoded-id assumption is
// the EXACT bug class #61 exists to eliminate, just surfacing as a hard
// FAIL instead of a false positive this time. Fixed by resolving recipes
// robustly, by OUTPUT item (`stFindRecipesByOutput` below - iterates
// `getRecipeManager().getRecipes()` and keeps whichever recipe(s) actually
// declare the target as their result via `getResultItem(registryAccess())`,
// the same call the #57 TG_TIER_INFO check above already proved works),
// rather than guessing an id scheme. `refinedstorage:controller` keeps its
// `byKey()` lookup below - RS's own ids are flat (`refinedstorage:
// controller`, confirmed against the jar) and NOT vulnerable to this bug,
// and switching it to output-based lookup would reintroduce the ORIGINAL
// #56 false positive: the recoloring recipe's own declared result is also
// literally `refinedstorage:controller` (its "restore to base colour"
// case), so an output-based scan for that id would match it too. Looking
// up the real recipe's own known id sidesteps that; `stFindRecipesByOutput`
// is for cases (like Create's) where the id scheme itself can't be
// guessed.
function stFindRecipesByOutput(server, itemId) {
    let matches = []
    let recipes = server.getRecipeManager().getRecipes().toArray()
    for (let i = 0; i < recipes.length; i++) {
        let holder = recipes[i]
        let result
        try {
            result = holder.value().getResultItem(server.registryAccess())
        } catch (e) {
            continue // recipe type doesn't implement getResultItem() - not this one
        }
        if (result && String(result.id) === itemId) matches.push(holder)
    }
    return matches
}

stCheck('progression audit (#61): create:track_station resolves to its real recipe (needs railway_casing)', server => {
    let matches = stFindRecipesByOutput(server, 'create:track_station')
    if (matches.length === 0) {
        return { pass: false, detail: 'no recipe found with output create:track_station - cannot confirm, re-check upstream (Create version drift?)' }
    }
    let railwayCasingStack = Item.of('create:railway_casing')
    let demandsRailwayCasing = false
    for (let i = 0; i < matches.length && !demandsRailwayCasing; i++) {
        let ingredients
        try { ingredients = matches[i].value().getIngredients().toArray() } catch (e) { continue }
        for (let j = 0; j < ingredients.length; j++) {
            if (ingredients[j].test(railwayCasingStack)) { demandsRailwayCasing = true; break }
        }
    }
    return {
        pass: demandsRailwayCasing,
        detail: demandsRailwayCasing
            ? ('confirmed: ' + matches.length + ' recipe(s) produce create:track_station and at least one requires create:railway_casing (not the unrelated create:track recipe)')
            : ('found ' + matches.length + ' recipe(s) for create:track_station but none require railway_casing - recipe changed upstream, re-verify #61s findings'),
    }
})

stCheck('progression audit (#61): refinedstorage:controller resolves to its real crafting recipe, not a recoloring variant', server => {
    let opt = server.getRecipeManager().byKey(stRl('refinedstorage:controller'))
    if (!opt.isPresent()) return { pass: false, detail: 'recipe missing - id changed upstream?' }
    let ingredients
    try {
        ingredients = opt.get().value().getIngredients().toArray()
    } catch (e) {
        return { pass: false, detail: 'getIngredients() unsupported on this recipe type: ' + e }
    }
    let processorStack = Item.of('refinedstorage:advanced_processor')
    let dyeStack = Item.of('minecraft:blue_dye')
    let demandsProcessor = false
    let acceptsDye = false
    for (let j = 0; j < ingredients.length; j++) {
        if (ingredients[j].test(processorStack)) demandsProcessor = true
        if (ingredients[j].test(dyeStack)) acceptsDye = true
    }
    let pass = demandsProcessor && !acceptsDye
    return {
        pass: pass,
        detail: pass
            ? 'confirmed: real crafting recipe (needs advanced_processor, no dye slot like the recoloring recipes have)'
            : ('demandsProcessor=' + demandsProcessor + ' acceptsDye=' + acceptsDye + ' - re-verify #61s findings'),
    }
})

// #61 diagnostics turned #127 regression gates: the same three genuinely
// under-gated families the corrected offline audit + manual jar
// verification found (confirmed live against the post-KubeJS RecipeManager
// per PM review of PR #106) are now closed by tier_gating.js (#127) - see
// DESIGN.md's "Recipe-reachability audit" section for the fix mechanism
// (Sophisticated Storage: gate the double-chest upgrade recipes directly;
// Refined Storage: gate the shared refinedstorage:machine_casing
// chokepoint; the brass tag: re-author create:brass_casing's two recipes
// off the literal create:brass_ingot item instead of c:ingots/brass). These
// three checks now hard-FAIL if the gap reopens (a future mod update
// changing a recipe id/shape, or a regression re-removing the KubeJS edit),
// same "cannot confirm is never a silent pass" discipline as the two
// checks above - only now `demandsTier`/`!bypassable` is the assertion,
// not just a report.
stCheck('progression audit (#61/#127): sophisticatedstorage double-chest upgrade path is Andesite/Brass Age gated', server => {
    let ids = ['sophisticatedstorage:double_iron_chest', 'sophisticatedstorage:double_gold_chest', 'sophisticatedstorage:double_diamond_chest']
    let tierStacks = [Item.of('create:andesite_alloy'), Item.of('create:brass_ingot')]
    let bypassed = []
    let checked = 0
    for (let i = 0; i < ids.length; i++) {
        let opt = server.getRecipeManager().byKey(stRl(ids[i]))
        if (!opt.isPresent()) continue
        let ingredients
        try { ingredients = opt.get().value().getIngredients().toArray() } catch (e) { continue }
        checked++
        let demandsTier = false
        for (let j = 0; j < ingredients.length; j++) {
            for (let k = 0; k < tierStacks.length; k++) {
                if (ingredients[j].test(tierStacks[k])) demandsTier = true
            }
        }
        // double_diamond_chest chains off gold_chest (itself now gated) and
        // needs no tier material of its own - same chain-gate reasoning as
        // the rest of tier_gating.js, so it's expected to report "no direct
        // tier material" without that meaning it's bypassable.
        if (!demandsTier && ids[i] !== 'sophisticatedstorage:double_diamond_chest') bypassed.push(ids[i])
    }
    if (checked === 0) {
        return { pass: false, detail: 'none of ' + ids.join(',') + ' resolved - cannot confirm, re-check ids (mod version drift?)' }
    }
    return {
        pass: bypassed.length === 0,
        detail: bypassed.length > 0
            ? ('REGRESSION - reaches chest tier with no tier material via: ' + bypassed.join(','))
            : ('gated (' + checked + '/' + ids.length + ' checked) - #127 fix holds'),
    }
})

stCheck('progression audit (#61/#127): refinedstorage pre-Induction-Age chain is Brass Age gated (via machine_casing)', server => {
    let ids = ['refinedstorage:controller', 'refinedstorage:disk_drive', 'refinedstorage:grid']
    let tierStacks = [Item.of('create:andesite_alloy'), Item.of('create:brass_ingot'), Item.of('create:refined_radiance'), Item.of('create:shadow_steel'), Item.of('minecraft:netherite_ingot')]
    let ungated = []
    let checked = 0
    for (let i = 0; i < ids.length; i++) {
        let opt = server.getRecipeManager().byKey(stRl(ids[i]))
        if (!opt.isPresent()) continue
        let ingredients
        try { ingredients = opt.get().value().getIngredients().toArray() } catch (e) { continue }
        checked++
        // #127 gates the shared refinedstorage:machine_casing chokepoint
        // rather than patching controller/disk_drive/grid directly, so the
        // tier material itself won't appear in THEIR ingredient lists - it
        // appears one level down, in machine_casing's own (re-authored)
        // recipe. Resolve that one hop rather than assuming a direct
        // ingredient, the same "don't assume, resolve the real chain" rule
        // #61 exists to enforce.
        let demandsTier = false
        let usesMachineCasing = false
        let machineCasingStack = Item.of('refinedstorage:machine_casing')
        for (let j = 0; j < ingredients.length; j++) {
            for (let k = 0; k < tierStacks.length; k++) {
                if (ingredients[j].test(tierStacks[k])) demandsTier = true
            }
            if (ingredients[j].test(machineCasingStack)) usesMachineCasing = true
        }
        if (!demandsTier && usesMachineCasing) {
            let casingOpt = server.getRecipeManager().byKey(stRl('refinedstorage:machine_casing'))
            if (casingOpt.isPresent()) {
                try {
                    let casingIngredients = casingOpt.get().value().getIngredients().toArray()
                    for (let j = 0; j < casingIngredients.length; j++) {
                        for (let k = 0; k < tierStacks.length; k++) {
                            if (casingIngredients[j].test(tierStacks[k])) demandsTier = true
                        }
                    }
                } catch (e) { /* leave demandsTier false - falls through to ungated below */ }
            }
        }
        if (!demandsTier) ungated.push(ids[i])
    }
    if (checked === 0) {
        return { pass: false, detail: 'none of ' + ids.join(',') + ' resolved - cannot confirm, re-check ids (mod version drift?)' }
    }
    return {
        pass: ungated.length === 0,
        detail: ungated.length > 0
            ? ('REGRESSION - no tier material anywhere in (direct or via machine_casing): ' + ungated.join(','))
            : ('gated (' + checked + '/' + ids.length + ' checked, via refinedstorage:machine_casing) - #127 fix holds'),
    }
})

// Second-round PM review fix: the original version of this check hardcoded
// recipe id `create:brass_casing_from_log`, missing the
// `item_application/` path segment Create's real id includes (confirmed
// against data/create/recipe/item_application/brass_casing_from_log.json
// in the pinned jar - the id is `create:item_application/
// brass_casing_from_log`) - and, worse, reported `pass: true` even though
// the recipe lookup failed and nothing was actually confirmed. Fixed the
// same way as the track_station check above: resolve by OUTPUT item
// (`create:brass_casing`, which both of Create's two alternate recipes for
// it - from_log and from_wood - produce) instead of guessing an id, and
// hard FAIL if no matching recipe is found rather than silently passing.
stCheck('progression audit (#61/#127): create:brass_casing no longer accepts alltheores:brass_ingot via c:ingots/brass', server => {
    let matches = stFindRecipesByOutput(server, 'create:brass_casing')
    if (matches.length === 0) {
        return { pass: false, detail: 'no recipe found with output create:brass_casing - cannot confirm, re-check upstream (Create version drift?)' }
    }
    let bypassRecipeIds = []
    let anyAcceptsCreateBrass = false
    let introspected = 0
    for (let i = 0; i < matches.length; i++) {
        let ingredients
        try { ingredients = matches[i].value().getIngredients().toArray() } catch (e) { continue }
        introspected++
        let acceptsCreateBrass = false
        let acceptsAllTheOresBrass = false
        for (let j = 0; j < ingredients.length; j++) {
            if (ingredients[j].test(Item.of('create:brass_ingot'))) acceptsCreateBrass = true
            if (ingredients[j].test(Item.of('alltheores:brass_ingot'))) acceptsAllTheOresBrass = true
        }
        if (acceptsCreateBrass) anyAcceptsCreateBrass = true
        if (acceptsAllTheOresBrass) bypassRecipeIds.push(String(matches[i].id()))
    }
    if (introspected === 0) {
        return { pass: false, detail: 'found ' + matches.length + ' recipe(s) for create:brass_casing but none exposed getIngredients() - cannot confirm' }
    }
    if (!anyAcceptsCreateBrass && bypassRecipeIds.length === 0) {
        return { pass: false, detail: 'found ' + introspected + ' recipe(s) for create:brass_casing but none accept create:brass_ingot or alltheores:brass_ingot - cannot confirm, ingredient shape may have changed' }
    }
    return {
        pass: bypassRecipeIds.length === 0,
        detail: bypassRecipeIds.length > 0
            ? ('REGRESSION - c:ingots/brass accepts alltheores:brass_ingot (unrelated mod, no tier gate of its own) via: ' + bypassRecipeIds.join(','))
            : ('gated (' + introspected + ' recipe(s) checked, all require the literal create:brass_ingot) - #127 fix holds'),
    }
})

// #91 (reopened): material_sinks.js routes five previously-dead AllTheOres
// gear items into real recipe families - same failure mode as the tier
// gates above (a renamed jar recipe id or removed item would silently
// un-gate/un-sink the material with no error), same Predicate#test probe.
const ST_MATERIAL_SINK_RECIPES = [
    { id: 'vanillaplusplus:raw_basic_processor_tin_gear', sink: 'alltheores:tin_gear' },
    { id: 'vanillaplusplus:raw_improved_processor_silver_gear', sink: 'alltheores:silver_gear' },
    { id: 'vanillaplusplus:raw_advanced_processor_platinum_gear', sink: 'alltheores:platinum_gear' },
    { id: 'vanillaplusplus:magnet_upgrade_osmium_gear', sink: 'alltheores:osmium_gear' },
    { id: 'vanillaplusplus:advanced_magnet_upgrade_iridium_gear', sink: 'alltheores:iridium_gear' },
]

stCheck('material_sinks.js: every #91 sink recipe resolves and demands its gear (#91)', server => {
    let bad = []
    for (let i = 0; i < ST_MATERIAL_SINK_RECIPES.length; i++) {
        let entry = ST_MATERIAL_SINK_RECIPES[i]
        let opt = server.getRecipeManager().byKey(stRl(entry.id))
        if (!opt.isPresent()) { bad.push(entry.id + ':missing'); continue }
        let sinkStack = Item.of(entry.sink)
        let ingredients = opt.get().value().getIngredients().toArray()
        let demands = false
        for (let j = 0; j < ingredients.length; j++) {
            if (ingredients[j].test(sinkStack)) { demands = true; break }
        }
        if (!demands) bad.push(entry.id + ':missing-' + entry.sink)
    }
    return {
        pass: bad.length === 0,
        detail: bad.length === 0 ? (ST_MATERIAL_SINK_RECIPES.length + ' sink recipes verified') : bad.join(','),
    }
})

// #57: the JEI info layer only fires when a recipe viewer syncs, so a
// console-only boot never exercises it - which is exactly how it would rot
// unnoticed (a renamed table, a script that stopped loading, an exception
// swallowed by the try/catch in the event handler). jeiAddPackInfo() is a
// plain function for this reason: call it with a recording stub and assert
// both that it produced pages and that the four sources are each represented.
stCheck('jei_info.js: pack info pages generate for all four sources (#57)', () => {
    if (typeof jeiAddPackInfo !== 'function') {
        return { pass: false, detail: 'jei_info.js did not load into the shared server_scripts scope' }
    }
    let seen = {}
    let stub = { add: (id, lines) => { seen[String(id)] = lines.length } }
    let pages
    try {
        pages = jeiAddPackInfo(stub)
    } catch (e) {
        return { pass: false, detail: 'jeiAddPackInfo threw: ' + e }
    }
    // One representative id per source. The tool id is deliberately checked
    // against the sweep's live output rather than hardcoded - if the sweep
    // stops removing anything, that is itself the regression.
    let problems = []
    if (typeof TCS_REMOVED_TOOL_ITEMS === 'undefined' || TCS_REMOVED_TOOL_ITEMS.length === 0) {
        problems.push('tool sweep removed nothing - no tool info pages possible')
    } else if (!seen[TCS_REMOVED_TOOL_ITEMS[0]]) {
        problems.push('no info page for removed tool ' + TCS_REMOVED_TOOL_ITEMS[0])
    }
    if (!seen['waystones:warp_stone']) problems.push('no tier-gating info page (waystones:warp_stone)')
    if (!seen['create:andesite_alloy']) problems.push('no stage-trigger info page (create:andesite_alloy)')
    if (!seen['alltheores:zinc_ingot']) problems.push('no dedup info page (alltheores:zinc_ingot)')
    return {
        pass: problems.length === 0,
        detail: problems.length === 0 ? (pages + ' info pages across 4 sources') : problems.join('; '),
    }
})

// #57: every id TG_TIER_INFO explains must be one tier_gating.js actually
// re-authors, or the JEI text is describing a gate that isn't there. Checked
// against the outputs of the very recipe ids the gating check above pins,
// rather than by scanning the whole recipe manager (which is both slow and,
// as an earlier revision of this check found the hard way, blocked by KubeJS's
// class shutter: ItemStack#getItem() exposes no kjs$getId to Rhino).
stCheck('tier_gating.js: TG_TIER_INFO only describes recipes this pack really gates (#57)', server => {
    if (typeof TG_TIER_INFO === 'undefined') {
        return { pass: false, detail: 'TG_TIER_INFO missing from the shared scope' }
    }
    let gatedOutputs = {}
    for (let i = 0; i < ST_TIER_GATED_RECIPES.length; i++) {
        let opt = server.getRecipeManager().byKey(stRl(ST_TIER_GATED_RECIPES[i].id))
        if (!opt.isPresent()) continue
        let result
        try { result = opt.get().value().getResultItem(server.registryAccess()) } catch (e) { continue }
        if (result) gatedOutputs[String(result.id)] = true
    }
    let bad = []
    let described = 0
    for (let i = 0; i < TG_TIER_INFO.length; i++) {
        for (let j = 0; j < TG_TIER_INFO[i].items.length; j++) {
            described++
            if (!gatedOutputs[TG_TIER_INFO[i].items[j]]) {
                bad.push(TG_TIER_INFO[i].items[j] + ' is described but not gated by any vanillaplusplus recipe')
            }
        }
    }
    return { pass: bad.length === 0, detail: bad.length === 0 ? (described + ' described items all really gated') : bad.join('; ') }
})

// Regression guard for the mob-scaling operation-id bug (found 2026-07-22):
// puffish_skills' attr_reward calls this semantic "multiply_base", vanilla's
// AttributeModifier.Operation calls it "add_multiplied_base", and passing the
// former to KubeJS's entity.modifyAttribute() threw on every scaled spawn -
// killing health/damage scaling, the star nametag AND the death-reward bonus,
// with nothing but a server-log ERROR to show for it. Static id check: a live
// one would need a real mob spawning next to a real player, which only L3 can
// stage.
stCheck('mob_scaling.js: scaling operation is a real vanilla AttributeModifier id', () => {
    if (typeof MS_SCALING_OPERATION === 'undefined') {
        return { pass: false, detail: 'MS_SCALING_OPERATION missing from the shared scope' }
    }
    const VALID = ['add_value', 'add_multiplied_base', 'add_multiplied_total']
    let ok = VALID.indexOf(MS_SCALING_OPERATION) >= 0
    return {
        pass: ok,
        detail: ok ? MS_SCALING_OPERATION : MS_SCALING_OPERATION + ' is not one of ' + VALID.join('/') + " (puffish_skills' vocabulary is not vanilla's)",
    }
})

stCheck('Artifacts master tag (artifacts:artifacts) has >= 48 items', server => {
    let registry = stItemRegistry(server)
    let tagKey = ST_TagKeyClass.create(ST_RegistriesClass.ITEM, stRl('artifacts:artifacts'))
    let tagOpt = registry.getTag(tagKey)
    if (!tagOpt.isPresent()) return { pass: false, detail: 'tag not present' }
    let size = tagOpt.get().size()
    return { pass: size >= ST_ARTIFACTS_MASTER_TAG_MIN_SIZE, detail: size + ' items' }
})

stCheck('dedup: c:ingots/zinc no longer contains alltheores:zinc_ingot', server => {
    let registry = stItemRegistry(server)
    let tagKey = ST_TagKeyClass.create(ST_RegistriesClass.ITEM, stRl('c:ingots/zinc'))
    let tagOpt = registry.getTag(tagKey)
    if (!tagOpt.isPresent()) return { pass: false, detail: 'tag not present' }
    let items = tagOpt.get()
    let found = false
    let it = items.iterator()
    while (it.hasNext()) {
        let holder = it.next()
        if (String(registry.getKey(holder.value())) === 'alltheores:zinc_ingot') { found = true; break }
    }
    return { pass: !found, detail: found ? 'alltheores:zinc_ingot still present (dedup regression)' : 'redirected, ok' }
})

stCheck('mob variety: born_in_chaos_v1:krampus is a registered entity type', server => {
    let registry = server.registryAccess().registryOrThrow(ST_RegistriesClass.ENTITY_TYPE)
    return { pass: registry.containsKey(stRl('born_in_chaos_v1:krampus')), detail: 'ok' }
})

stCheck('structure loot: a generated vpp_bucket loot table resolves', server => {
    // Actual generated ids (scripts/gen_structure_loot.py) are named after
    // this pack's 4 rarity buckets - common/uncommon/rare/epic - not
    // "tierN" (verified via find on pack/kubejs/data/artifacts/loot_table/
    // vpp_bucket/*.json). Loot tables are NOT in server.registryAccess()
    // (confirmed via a real "Missing registry: minecraft:loot_table"
    // IllegalStateException on this exact check) - they're a reloadable
    // registry reached through server.reloadableRegistries().lookup()
    // .lookupOrThrow(...), which returns a HolderLookup (not a Registry -
    // no containsKey(); use get(ResourceKey) -> Optional instead).
    let ResourceKeyClass = Java.loadClass('net.minecraft.resources.ResourceKey')
    let lootLookup = server.reloadableRegistries().lookup().lookupOrThrow(ST_RegistriesClass.LOOT_TABLE)
    let resourceKey = ResourceKeyClass.create(ST_RegistriesClass.LOOT_TABLE, stRl('artifacts:vpp_bucket/common'))
    let found = lootLookup.get(resourceKey)
    return { pass: found.isPresent(), detail: found.isPresent() ? 'ok' : 'artifacts:vpp_bucket/common not found' }
})

stCheck('leaderboard command node is registered', server => {
    let root = server.getCommands().getDispatcher().getRoot()
    let children = root.getChildren().toArray()
    for (let i = 0; i < children.length; i++) {
        if (String(children[i].getName()) === 'leaderboard') return { pass: true, detail: 'ok' }
    }
    return { pass: false, detail: 'leaderboard command missing' }
})

stCheck('sell command node is registered', server => {
    let root = server.getCommands().getDispatcher().getRoot()
    let children = root.getChildren().toArray()
    for (let i = 0; i < children.length; i++) {
        if (String(children[i].getName()) === 'sell') return { pass: true, detail: 'ok' }
    }
    return { pass: false, detail: 'sell command missing' }
})

stCheck('economy sell round-trip: iron_ingot -> coins, inventory reflects it', (server, player) => {
    if (!player) return { skip: true, detail: 'no player online (console-only L1 run)' }
    let before = stCountCoinValue(player)
    player.give(Item.of('minecraft:iron_ingot', 1))
    let stack = stFindFirstStack(player, 'minecraft:iron_ingot')
    if (!stack) return { pass: false, detail: 'could not find the given iron_ingot in inventory' }
    // Mirrors economy.js's own price table entry (minecraft:iron_ingot = 4
    // spurs) directly rather than dispatching the real /sell command, so
    // this check is independent of command-parser plumbing.
    let unitPrice = 4
    stack.setCount(stack.getCount() - 1)
    stPayCoins(player, unitPrice)
    let after = stCountCoinValue(player)
    return { pass: after === before + unitPrice, detail: 'before=' + before + ' after=' + after + ' expected=' + (before + unitPrice) }
})

stCheck('persistentData round trip on the server', server => {
    let key = 'vpp_selftest_probe'
    server.persistentData.putLong(key, 424242)
    let readBack = server.persistentData.getLong(key)
    server.persistentData.remove(key)
    return { pass: readBack === 424242, detail: 'wrote 424242, read ' + readBack }
})

stCheck('mobility: starforged_age stage id resolves on player.stages without throwing', (server, player) => {
    if (!player) return { skip: true, detail: 'no player online (console-only L1 run)' }
    player.stages.has('starforged_age')
    return { pass: true, detail: 'ok' }
})

// GitHub issue #23 fix: progression_stage_bridge.js compensates for
// ProgressiveStages' ItemPickupStageGrants only listening to
// ItemEntityPickupEvent$Pre (ground pickup), which never fires for items
// crafted straight into inventory. These two checks catch a regression at
// the two levels that matter: (1) the mirrored trigger table actually
// loaded into the shared Rhino scope (a boot-level wiring check - would
// have caught e.g. a typo'd filename or a shared-scope name collision
// silently dropping the whole file), and (2) the table's item->stage
// mapping is still the one this pack's tier table calls for. Until #49
// dropped ProgressiveStages this cross-checked the mod's own
// config/ProgressiveStages/triggers.toml, which the bridge mirrored; that
// file is gone and the bridge's constants ARE the trigger definition now,
// so this check pins them against an independent copy of the expected
// mapping instead - same regression value, one less file to drift.
stCheck('progression_stage_bridge: PSB_ITEM_STAGE_TRIGGERS loaded and matches the tier table', () => {
    if (typeof PSB_ITEM_STAGE_TRIGGERS === 'undefined' || typeof psbApplyItemStageTriggers !== 'function') {
        return { pass: false, detail: 'progression_stage_bridge.js did not load into the shared server_scripts scope' }
    }
    // The three single-item tier triggers plus precision_age's
    // either-of-two entry - see progression_stage_bridge.js's header.
    const expected = {
        andesite_age: ['create:andesite_alloy'],
        brass_age: ['create:brass_ingot'],
        induction_age: ['minecraft:netherite_ingot'],
        precision_age: ['create:refined_radiance', 'create:shadow_steel'],
    }
    const expectedStages = Object.keys(expected)
    let mismatches = []
    for (let i = 0; i < PSB_ITEM_STAGE_TRIGGERS.length; i++) {
        let t = PSB_ITEM_STAGE_TRIGGERS[i]
        let exp = expected[t.stage]
        if (!exp) { mismatches.push('unexpected stage ' + t.stage); continue }
        if (exp.length !== t.items.length || exp.some((id, idx) => id !== t.items[idx])) {
            mismatches.push(t.stage + ': got [' + t.items.join(',') + '] expected [' + exp.join(',') + ']')
        }
    }
    let gotStages = PSB_ITEM_STAGE_TRIGGERS.map(t => t.stage)
    let missingStages = expectedStages.filter(s => gotStages.indexOf(s) < 0)
    missingStages.forEach(s => mismatches.push('missing stage ' + s))
    return { pass: mismatches.length === 0, detail: mismatches.length === 0 ? (PSB_ITEM_STAGE_TRIGGERS.length + ' triggers match the tier table') : mismatches.join('; ') }
})

// #49 (ProgressiveStages dropped): the starting/dimension/boss triggers the
// mod used to own are now this bridge's job, and nothing else in the pack
// would notice if they silently vanished - a player would simply never get
// rootborn, the four Stellaris frontier stages, or starforged_age, and every
// quest gated on them would dead-end with no error anywhere. Pins the three
// constants and asserts the grant functions are callable.
stCheck('progression_stage_bridge: ported starting/dimension/boss triggers are wired (#49)', () => {
    if (typeof PSB_STARTING_STAGES === 'undefined'
        || typeof PSB_DIMENSION_STAGE_TRIGGERS === 'undefined'
        || typeof PSB_BOSS_STAGE_TRIGGERS === 'undefined') {
        return { pass: false, detail: 'one or more ported trigger tables missing from the shared scope' }
    }
    if (typeof psbApplyStartingStages !== 'function'
        || typeof psbApplyDimensionStageTriggers !== 'function'
        || typeof psbApplyBossStageTriggers !== 'function') {
        return { pass: false, detail: 'one or more ported trigger functions missing from the shared scope' }
    }
    let problems = []
    if (PSB_STARTING_STAGES.length !== 1 || PSB_STARTING_STAGES[0] !== 'rootborn') {
        problems.push('starting stages: got [' + PSB_STARTING_STAGES.join(',') + '] expected [rootborn]')
    }
    const expectedDims = {
        'stellaris:earth_orbit': 'lunar_frontier',
        'stellaris:moon': 'martian_frontier',
        'stellaris:mars': 'inner_system',
        'stellaris:venus': 'jovian_frontier',
        'stellaris:mercury': 'jovian_frontier',
    }
    const expectedDimIds = Object.keys(expectedDims)
    if (PSB_DIMENSION_STAGE_TRIGGERS.length !== expectedDimIds.length) {
        problems.push('dimension triggers: got ' + PSB_DIMENSION_STAGE_TRIGGERS.length + ' expected ' + expectedDimIds.length)
    }
    for (let i = 0; i < PSB_DIMENSION_STAGE_TRIGGERS.length; i++) {
        let t = PSB_DIMENSION_STAGE_TRIGGERS[i]
        if (expectedDims[t.dimension] !== t.stage) {
            problems.push('dimension ' + t.dimension + ': got ' + t.stage + ' expected ' + (expectedDims[t.dimension] || 'nothing'))
        }
    }
    if (PSB_BOSS_STAGE_TRIGGERS.length !== 1
        || PSB_BOSS_STAGE_TRIGGERS[0].entity !== 'minecraft:ender_dragon'
        || PSB_BOSS_STAGE_TRIGGERS[0].stage !== 'starforged_age') {
        problems.push('boss trigger is not ender_dragon -> starforged_age')
    }
    return {
        pass: problems.length === 0,
        detail: problems.length === 0
            ? ('1 starting + ' + PSB_DIMENSION_STAGE_TRIGGERS.length + ' dimension + ' + PSB_BOSS_STAGE_TRIGGERS.length + ' boss trigger wired')
            : problems.join('; '),
    }
})

stCheck('progression_stage_bridge: starting stage grants on a live player (#49)', (server, player) => {
    if (!player) return { skip: true, detail: 'no player online (console-only L1 run)' }
    if (typeof psbApplyStartingStages !== 'function') {
        return { pass: false, detail: 'psbApplyStartingStages missing from the shared scope' }
    }
    // Idempotent by construction, so this is safe to run against a real
    // player: it either grants rootborn (fresh player) or no-ops.
    psbApplyStartingStages(player)
    return {
        pass: player.stages.has('rootborn'),
        detail: player.stages.has('rootborn') ? 'player holds rootborn' : 'rootborn not granted',
    }
})

stCheck('progression_stage_bridge: crafted-item trigger grants the stage via player.stages (issue #23 regression guard)', (server, player) => {
    if (!player) return { skip: true, detail: 'no player online (console-only L1 run)' }
    if (typeof PSB_ITEM_STAGE_TRIGGERS === 'undefined' || typeof psbApplyItemStageTriggers !== 'function') {
        return { pass: false, detail: 'progression_stage_bridge.js did not load into the shared server_scripts scope' }
    }
    let trigger = null
    for (let i = 0; i < PSB_ITEM_STAGE_TRIGGERS.length; i++) {
        if (!player.stages.has(PSB_ITEM_STAGE_TRIGGERS[i].stage)) { trigger = PSB_ITEM_STAGE_TRIGGERS[i]; break }
    }
    if (!trigger) return { skip: true, detail: 'player already holds every mapped stage, nothing safe to probe without touching real progress' }

    let itemId = trigger.items[0]
    let hadBefore = player.inventory.find(itemId) >= 0
    if (!hadBefore) player.give(Item.of(itemId, 1))
    try {
        let granted = psbApplyItemStageTriggers(player)
        let ok = granted.indexOf(trigger.stage) >= 0 && player.stages.has(trigger.stage)
        return { pass: ok, detail: ok ? ('granted ' + trigger.stage + ' from ' + itemId) : ('did not grant ' + trigger.stage + ' from ' + itemId + ' (granted=' + granted.join(',') + ')') }
    } finally {
        // Restore exactly what we touched: revoke the probe grant, and
        // remove the probe item only if this check is the one that gave it
        // (never touch a copy the player already legitimately had).
        player.stages.remove(trigger.stage)
        if (!hadBefore) {
            let slot = player.inventory.find(itemId)
            if (slot >= 0) player.getInventory().getItem(slot).setCount(0)
        }
    }
})

// GitHub #32: FTB Teams + FTB Chunks replaced with Open Parties and Claims
// (redistribution reasons - #28). progressivestages.toml's team_mode is now
// "solo" (ProgressiveStages has no native OPAC hook, confirmed via javap -
// see progression_stage_bridge.js's header comment), so party-wide
// tier-stage sharing became a KubeJS bridge (psbSyncPartyStages in that same
// file) instead of ProgressiveStages' own backend. These two checks replace
// the old "FTBTeamsAPI: team manager reachable" coverage removed above,
// same two-level shape as the item-trigger checks: (1) the mirrored tier-id
// list actually loaded into the shared Rhino scope and still matches the
// canonical list every other file in this pack keeps in sync
// (ST_TIER_IDS/TIER_IDS), and (2) the real bridge function actually runs
// against OPAC's live API (OpenPACServerAPI.get(server).getPartyManager()
// .getAllStream()...) without throwing - a genuine regression guard against
// an OPAC API-signature change, not just a wiring check. Cannot verify
// actual cross-player stage propagation here (needs 2+ players in a real
// party, console-only L1 has no client) - that's a verify-in-game gap,
// disclosed rather than claimed.
stCheck('progression_stage_bridge: PSB_PARTY_TIER_IDS loaded and matches the canonical 10 tier ids', () => {
    if (typeof PSB_PARTY_TIER_IDS === 'undefined' || typeof psbSyncPartyStages !== 'function') {
        return { pass: false, detail: 'progression_stage_bridge.js did not load into the shared server_scripts scope' }
    }
    let mismatches = []
    if (PSB_PARTY_TIER_IDS.length !== ST_TIER_IDS.length) mismatches.push('length ' + PSB_PARTY_TIER_IDS.length + ' != ' + ST_TIER_IDS.length)
    for (let i = 0; i < Math.min(PSB_PARTY_TIER_IDS.length, ST_TIER_IDS.length); i++) {
        if (PSB_PARTY_TIER_IDS[i] !== ST_TIER_IDS[i]) mismatches.push('index ' + i + ': ' + PSB_PARTY_TIER_IDS[i] + ' != ' + ST_TIER_IDS[i])
    }
    return { pass: mismatches.length === 0, detail: mismatches.length === 0 ? (PSB_PARTY_TIER_IDS.length + ' ids match ST_TIER_IDS') : mismatches.join('; ') }
})

stCheck('progression_stage_bridge: psbSyncPartyStages runs against the real OPAC API without throwing (GitHub #32 regression guard)', server => {
    if (typeof psbSyncPartyStages !== 'function') {
        return { pass: false, detail: 'progression_stage_bridge.js did not load into the shared server_scripts scope' }
    }
    if (!ST_OpenPACServerAPIClass) return { skip: true, detail: 'OpenPACServerAPI class unavailable, nothing to exercise' }
    let grants = psbSyncPartyStages(server) // throwing is the failure mode under test; 0 grants is expected/fine with no real party formed
    return { pass: typeof grants === 'number', detail: grants + ' stage grant(s) made (0 expected with no real party formed in this console-only run)' }
})

// GitHub #33: bespoke quest tracker replacing FTB Quests (pack/kubejs/
// server_scripts/quests.js). NOTE: this repo's existing selftest.js had NO
// coverage at all for the two earlier Phase-6 KubeJS-only quest-style
// systems (achievements.js/dailies.js - grepped this file for "achiev"/
// "dailies"/"bounty" before writing these, found nothing) despite the task
// that produced this file asking for "the same rigor as achievements.js's
// existing selftest coverage" - there is no such coverage to match, so
// these checks instead follow this file's own general house style (guarded
// player checks, boot-level wiring checks, a real regression-guard round
// trip that restores what it touched) - the same shape as the
// progression_stage_bridge checks directly above.
stCheck('quests: QUEST_CHAPTERS loaded with 10 chapters / 62 quests / 87 dependencies', () => {
    if (typeof QUEST_CHAPTERS === 'undefined') {
        return { pass: false, detail: 'quests.js did not load into the shared server_scripts scope' }
    }
    let chapters = QUEST_CHAPTERS.length
    let quests = 0
    let deps = 0
    for (let i = 0; i < QUEST_CHAPTERS.length; i++) {
        quests += QUEST_CHAPTERS[i].quests.length
        for (let j = 0; j < QUEST_CHAPTERS[i].quests.length; j++) {
            deps += QUEST_CHAPTERS[i].quests[j].dependencies.length
        }
    }
    let ok = chapters === 10 && quests === 62 && deps === 87
    return { pass: ok, detail: `chapters=${chapters} quests=${quests} deps=${deps}` }
})

stCheck('quests: progress-storage round trip on a synthetic id (no real quest touched)', server => {
    if (typeof markQuestComplete !== 'function' || typeof isQuestComplete !== 'function'
        || typeof questsEnsureCompound !== 'function' || typeof QUESTS_PROGRESS_ROOT_KEY === 'undefined') {
        return { pass: false, detail: 'quests.js did not load into the shared server_scripts scope' }
    }
    let key = 'vpp_selftest_probe_team'
    let qid = 'vpp_selftest_probe_quest'
    let before = isQuestComplete(server, key, qid)
    markQuestComplete(server, key, qid)
    let after = isQuestComplete(server, key, qid)
    // Clean up: this key/id pair is synthetic and never appears in
    // QUEST_CHAPTERS, but remove it anyway so nothing lingers in
    // persistentData across repeated selftest runs.
    let root = questsEnsureCompound(server.persistentData, QUESTS_PROGRESS_ROOT_KEY)
    if (root.contains(key, 10)) root.remove(key)
    return { pass: !before && after, detail: 'before=' + before + ' after=' + after }
})

stCheck('quests: getProgressKey resolves for a live player without throwing', (server, player) => {
    if (!player) return { skip: true, detail: 'no player online (console-only L1 run)' }
    if (typeof getProgressKey !== 'function') {
        return { pass: false, detail: 'quests.js did not load into the shared server_scripts scope' }
    }
    let key = getProgressKey(player)
    return { pass: typeof key === 'string' && key.length > 0, detail: 'key=' + key }
})

stCheck('quests: checkTask resolves item/kill/dimension/gamestage task types without throwing', (server, player) => {
    if (!player) return { skip: true, detail: 'no player online (console-only L1 run)' }
    if (typeof checkTask !== 'function') {
        return { pass: false, detail: 'quests.js did not load into the shared server_scripts scope' }
    }
    checkTask(player, { type: 'item', item: 'minecraft:stone', count: 1 })
    checkTask(player, { type: 'kill', entity: 'minecraft:zombie', count: 1 })
    checkTask(player, { type: 'dimension', dimension: 'minecraft:overworld' })
    checkTask(player, { type: 'gamestage', stage: 'rootborn' })
    return { pass: true, detail: 'ok' }
})

stCheck('quests command node is registered, with all 10 chapter subcommands', server => {
    let root = server.getCommands().getDispatcher().getRoot()
    let children = root.getChildren().toArray()
    let questsNode = null
    for (let i = 0; i < children.length; i++) {
        if (String(children[i].getName()) === 'quests') { questsNode = children[i]; break }
    }
    if (!questsNode) return { pass: false, detail: 'quests command missing' }
    let subChildren = questsNode.getChildren().toArray()
    let names = []
    for (let i = 0; i < subChildren.length; i++) names.push(String(subChildren[i].getName()))
    let missing = []
    for (let i = 0; i < QUEST_CHAPTERS.length; i++) {
        if (names.indexOf(QUEST_CHAPTERS[i].id) < 0) missing.push(QUEST_CHAPTERS[i].id)
    }
    return { pass: missing.length === 0, detail: missing.length === 0 ? (names.length + ' chapter subcommands present') : ('missing: ' + missing.join(',')) }
})

stCheck('quest check node is registered, with all checkmark-quest subcommands', server => {
    let root = server.getCommands().getDispatcher().getRoot()
    let children = root.getChildren().toArray()
    let questNode = null
    for (let i = 0; i < children.length; i++) {
        if (String(children[i].getName()) === 'quest') { questNode = children[i]; break }
    }
    if (!questNode) return { pass: false, detail: 'quest command missing' }
    let questChildren = questNode.getChildren().toArray()
    let checkNode = null
    for (let i = 0; i < questChildren.length; i++) {
        if (String(questChildren[i].getName()) === 'check') { checkNode = questChildren[i]; break }
    }
    if (!checkNode) return { pass: false, detail: 'quest check subcommand missing' }
    let idChildren = checkNode.getChildren().toArray()
    let names = []
    for (let i = 0; i < idChildren.length; i++) names.push(String(idChildren[i].getName()))
    let missing = []
    for (let i = 0; i < CHECKMARK_QUEST_IDS.length; i++) {
        if (names.indexOf(CHECKMARK_QUEST_IDS[i]) < 0) missing.push(CHECKMARK_QUEST_IDS[i])
    }
    return { pass: missing.length === 0 && CHECKMARK_QUEST_IDS.length === 4, detail: missing.length === 0 ? (names.length + ' checkmark subcommands present, expected 4') : ('missing: ' + missing.join(',')) }
})

// Real end-to-end round trip through runCheckmarkCheck() - same
// disclosed-real-side-effect precedent as the economy sell round-trip
// check above (that one permanently pays out real coins; this one
// permanently grants the "Welcome to Vanilla++" quest's real +10 mining
// XP reward the first time this runs for a given player/team - both are
// small, disclosed, and the only way to prove the actual completion path
// works end to end rather than just its individual pieces in isolation).
stCheck('quests: checkmark completion round-trip via runCheckmarkCheck (rootborn__welcome)', (server, player) => {
    if (!player) return { skip: true, detail: 'no player online (console-only L1 run)' }
    if (typeof runCheckmarkCheck !== 'function' || typeof CHECKMARK_QUEST_IDS === 'undefined' || CHECKMARK_QUEST_IDS.length === 0) {
        return { pass: false, detail: 'quests.js did not load into the shared server_scripts scope' }
    }
    let qid = CHECKMARK_QUEST_IDS[0] // 'rootborn__welcome' - no dependencies, always eligible
    let progressKey = getProgressKey(player)
    if (isQuestComplete(server, progressKey, qid)) {
        return { skip: true, detail: qid + ' already complete for this player/team - nothing safe to probe without a duplicate grant' }
    }
    runCheckmarkCheck(player, qid)
    let ok = isQuestComplete(server, progressKey, qid)
    return { pass: ok, detail: ok ? (qid + ' completed and recorded (real, permanent - see check header comment)') : (qid + ' did not record as complete') }
})

// ---- helpers ----

function stCountCoinValue(player) {
    let values = { 'numismatics:spur': 1, 'numismatics:bevel': 8, 'numismatics:sprocket': 16, 'numismatics:cog': 64, 'numismatics:crown': 512, 'numismatics:sun': 4096 }
    let total = 0
    let inv = player.getInventory()
    for (let i = 0; i < inv.getContainerSize(); i++) {
        let s = inv.getItem(i)
        if (!s || s.isEmpty()) continue
        let v = values[s.id]
        if (v !== undefined) total += v * s.getCount()
    }
    return total
}

function stFindFirstStack(player, itemId) {
    let inv = player.getInventory()
    for (let i = 0; i < inv.getContainerSize(); i++) {
        let s = inv.getItem(i)
        if (s && !s.isEmpty() && s.id === itemId) return s
    }
    return null
}

function stPayCoins(player, totalSpurs) {
    let coins = [
        ['numismatics:sun', 4096], ['numismatics:crown', 512], ['numismatics:cog', 64],
        ['numismatics:sprocket', 16], ['numismatics:bevel', 8], ['numismatics:spur', 1],
    ]
    let remaining = totalSpurs
    for (const [itemId, value] of coins) {
        let count = Math.floor(remaining / value)
        if (count > 0) {
            player.give(Item.of(itemId, count))
            remaining -= count * value
        }
    }
}

// Extracted so the test-only stage-grant hook below (#65) can run the exact
// same ST_CHECKS loop against a real ServerPlayer, instead of maintaining a
// second, driftable copy of it. Pure: takes server/player, returns the raw
// pass/skip/fail-tagged results plus the three counts - no output side
// effect, so both the command handler (chat) and the test hook (server log)
// can format it their own way.
function stRunSelftestChecks(server, player) {
    let results = []
    for (let i = 0; i < ST_CHECKS.length; i++) {
        let c = ST_CHECKS[i]
        let result
        try {
            result = c.fn(server, player)
        } catch (e) {
            result = { pass: false, detail: 'EXCEPTION: ' + e }
        }
        results.push({ name: c.name, pass: !!result.pass, skip: !!result.skip, detail: result.detail })
    }

    let passed = 0
    let failed = 0
    let skipped = 0
    for (let i = 0; i < results.length; i++) {
        let r = results[i]
        if (r.skip) { r.tag = 'SKIP'; skipped++ }
        else if (r.pass) { r.tag = 'PASS'; passed++ }
        else { r.tag = 'FAIL'; failed++ }
    }
    return { results: results, passed: passed, failed: failed, skipped: skipped }
}

function stRunSelftest(ctx) {
    let server = ctx.source.server
    let player = ctx.source.isPlayer() ? ctx.source.getPlayerOrException() : null

    function output(line) {
        ctx.source.sendSystemMessage(ST_ComponentClass.literal(line))
    }

    let run = stRunSelftestChecks(server, player)
    for (let i = 0; i < run.results.length; i++) {
        let r = run.results[i]
        output(`[${r.tag}] ${r.name} - ${r.detail}`)
    }
    let executed = run.passed + run.failed
    let status = run.failed === 0 ? 'PASS' : 'FAIL'
    output(`VPP_SELFTEST: ${status} (${run.passed}/${executed}, ${run.skipped} skipped)`)
    return run.passed
}

ServerEvents.commandRegistry(event => {
    let { commands: Commands } = event

    event.register(
        Commands.literal('vpp_selftest').executes(ctx => {
            try {
                return stRunSelftest(ctx)
            } catch (e) {
                console.error('[vpp selftest] top-level EXCEPTION: ' + e + (e && e.stack ? ('\n' + e.stack) : ''))
                ctx.source.sendSystemMessage(ST_ComponentClass.literal('VPP_SELFTEST: FAIL (top-level exception, see server log: ' + e + ')'))
                return 0
            }
        })
    )
})

// ---------------------------------------------------------------------------
// GitHub #65 (test-only player-gated check coverage): every player-gated
// ST_CHECKS entry above (`if (!player) return { skip: true, ... }`) reports
// SKIP under every existing test tier, because none of them can drive
// `/vpp_selftest` AS the joined player - see the KNOWN GAP note in
// scripts/tests/l3_client_join.py for the two routes already tried and
// ruled out (console `execute as <player> run ...` silently no-ops under
// KubeJS's own registered command; hmc-specifics 2.4.0 exposes no client
// chat verb to type the command).
//
// #65's original route (this comment's prior revision) granted a sentinel,
// test-only stage (`vpp_test_selftest_hook`) and ran these checks from a
// PlayerEvents.stageAdded(...) hook, on the theory that Stages.add()'s
// default add(String) method posts PlayerEvents.STAGE_ADDED with the real
// joined ServerPlayer before returning (javap-confirmed against
// kubejs-neoforge-2101.7.2-build.368.jar's Stages.class). That part was
// right, but two engineers proved the exception this whole mechanism was
// built to route around - `kubejs stages add <player> <stage>` throwing
// server-side ("An unexpected error occurred trying to execute that
// command") against a real connected client - is INSIDE KubeJS's own
// Stages.add(), specifically its AddStagePayload broadcast to that client,
// and fires BEFORE this file's stageAdded hook (or its try/catch) ever
// runs. The paired `stages remove` and a real tier-stage grant
// (andesite_age) both work fine against the same client; only the sentinel
// stage-ADD path throws, and only with a client attached. There is no
// stage-side fix available from Rhino script code for a throw inside
// KubeJS's own native broadcast, so #65 now runs these checks from a plain
// server COMMAND instead - no stage grant, no AddStagePayload broadcast, no
// exception.
//
// `/vpp_selftest_player` takes no Brigadier ArgumentType (this pack has
// never proven Commands.argument(...)/Arguments.* interop - see
// skill_respec.js's own comment on that decision) - it runs the existing
// player-gated checks against every currently connected ServerPlayer
// instead, via `server.players`, the same for-of target already proven
// elsewhere in this pack (mob_scaling.js/leaderboard.js/quests.js/
// progression_stage_bridge.js). In L3's single-client harness that is
// exactly the one joined player STAGE_PROBE and everything else in this
// script already exercises.
//
// Reports to the SERVER LOG (console.info) with the same
// VPP_SELFTEST_HOOK_LINE:/VPP_SELFTEST_HOOK: prefixes L3
// (scripts/tests/l3_client_join.py) already greps for, unchanged from the
// prior stage-hook mechanism, so both are unambiguous to grep for and can
// never collide with the command path's own VPP_SELFTEST:/`[TAG] name -
// detail` chat output.
function stRunSelftestPlayerHook(server) {
    let anyPlayers = false
    for (const player of server.players) {
        anyPlayers = true
        try {
            let run = stRunSelftestChecks(server, player)
            for (let i = 0; i < run.results.length; i++) {
                let r = run.results[i]
                console.info(`VPP_SELFTEST_HOOK_LINE: [${r.tag}] ${r.name} - ${r.detail}`)
            }
            let executed = run.passed + run.failed
            let status = run.failed === 0 ? 'PASS' : 'FAIL'
            console.info(`VPP_SELFTEST_HOOK: ${status} (${run.passed}/${executed}, ${run.skipped} skipped)`)
        } catch (e) {
            console.error('[vpp selftest player-hook] top-level EXCEPTION for ' + player.username + ': ' + e + (e && e.stack ? ('\n' + e.stack) : ''))
        }
    }
    return anyPlayers
}

ServerEvents.commandRegistry(event => {
    let { commands: Commands } = event

    event.register(
        Commands.literal('vpp_selftest_player').executes(ctx => {
            try {
                let server = ctx.source.server
                let any = stRunSelftestPlayerHook(server)
                if (!any) {
                    ctx.source.sendSystemMessage(ST_ComponentClass.literal('VPP_SELFTEST_HOOK: no connected players to run player-gated checks against'))
                    return 0
                }
                ctx.source.sendSystemMessage(ST_ComponentClass.literal('VPP_SELFTEST_HOOK: ran player-gated checks against all connected players - see server log'))
                return 1
            } catch (e) {
                console.error('[vpp selftest player-hook] top-level EXCEPTION: ' + e + (e && e.stack ? ('\n' + e.stack) : ''))
                ctx.source.sendSystemMessage(ST_ComponentClass.literal('VPP_SELFTEST_HOOK: FAIL (top-level exception, see server log: ' + e + ')'))
                return 0
            }
        })
    )
})
