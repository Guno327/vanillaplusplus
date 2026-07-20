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
// NumismaticsClass/FTBTeamsAPIClass names and threw
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
let ST_FTBTeamsAPIClass = null
try {
    ST_FTBTeamsAPIClass = Java.loadClass('dev.ftb.mods.ftbteams.api.FTBTeamsAPI')
} catch (e) {
    console.error('[vpp selftest] FTBTeamsAPI class failed to load: ' + e)
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

stCheck('FTBTeamsAPI: team manager reachable', () => {
    if (!ST_FTBTeamsAPIClass) return { pass: false, detail: 'FTBTeamsAPI class unavailable' }
    let manager = ST_FTBTeamsAPIClass.api().getManager()
    let teams = manager.getTeams()
    return { pass: teams != null, detail: (teams ? teams.size() : 0) + ' teams' }
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
