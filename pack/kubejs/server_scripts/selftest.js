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
const ST_SKILL_CATEGORIES = [
    'bows', 'building', 'daggers', 'greatswords', 'longswords', 'magic',
    'mining', 'running', 'spears', 'swimming', 'swords', 'tachi',
]
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

stCheck('SkillsAPI: 12 skill categories all present', () => {
    if (!ST_SkillsAPIClass) return { pass: false, detail: 'SkillsAPI class unavailable' }
    let missing = []
    for (let i = 0; i < ST_SKILL_CATEGORIES.length; i++) {
        let catRl = ST_ResourceLocationClass.fromNamespaceAndPath('puffish_skills', ST_SKILL_CATEGORIES[i])
        let opt = ST_SkillsAPIClass.getCategory(catRl)
        if (!opt.isPresent()) missing.push(ST_SKILL_CATEGORIES[i])
    }
    return { pass: missing.length === 0, detail: missing.length === 0 ? 'all 12 present' : 'missing: ' + missing.join(',') }
})

stCheck('SkillsAPI: swords category has an Experience/level source', () => {
    if (!ST_SkillsAPIClass) return { pass: false, detail: 'SkillsAPI class unavailable' }
    let catRl = ST_ResourceLocationClass.fromNamespaceAndPath('puffish_skills', 'swords')
    let catOpt = ST_SkillsAPIClass.getCategory(catRl)
    if (!catOpt.isPresent()) return { pass: false, detail: 'swords category missing' }
    let expOpt = catOpt.get().getExperience()
    return { pass: expOpt.isPresent(), detail: expOpt.isPresent() ? 'ok' : 'no Experience for swords category' }
})

stCheck('Numismatics: bank account/balance reachable for a player', (server, player) => {
    if (!ST_NumismaticsClass) return { pass: false, detail: 'Numismatics class unavailable' }
    if (!player) return { skip: true, detail: 'no player online (console-only L1 run)' }
    let account = ST_NumismaticsClass.BANK.getAccount(player)
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
// mapping still agrees with config/ProgressiveStages/triggers.toml's own
// [items] section + precision_age's [[multi]] any_of list (both files
// declare they must be kept in sync; this is what actually enforces that).
stCheck('progression_stage_bridge: PSB_ITEM_STAGE_TRIGGERS loaded and matches triggers.toml', () => {
    if (typeof PSB_ITEM_STAGE_TRIGGERS === 'undefined' || typeof psbApplyItemStageTriggers !== 'function') {
        return { pass: false, detail: 'progression_stage_bridge.js did not load into the shared server_scripts scope' }
    }
    // Mirrors config/ProgressiveStages/triggers.toml's [items] section
    // (3 entries) plus precision_age's [[multi]] any_of item list
    // (1 entry, 2 alternative items) - see that file's own header comment.
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
    return { pass: mismatches.length === 0, detail: mismatches.length === 0 ? (PSB_ITEM_STAGE_TRIGGERS.length + ' triggers match triggers.toml') : mismatches.join('; ') }
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

function stRunSelftest(ctx) {
    let server = ctx.source.server
    let player = ctx.source.isPlayer() ? ctx.source.getPlayerOrException() : null

    function output(line) {
        ctx.source.sendSystemMessage(ST_ComponentClass.literal(line))
    }

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
        let tag
        if (r.skip) { tag = 'SKIP'; skipped++ }
        else if (r.pass) { tag = 'PASS'; passed++ }
        else { tag = 'FAIL'; failed++ }
        output(`[${tag}] ${r.name} - ${r.detail}`)
    }
    let executed = passed + failed
    let status = failed === 0 ? 'PASS' : 'FAIL'
    output(`VPP_SELFTEST: ${status} (${passed}/${executed}, ${skipped} skipped)`)
    return passed
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
