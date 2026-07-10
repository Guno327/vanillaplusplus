// TODO.md item 9 (food overhaul, diet variety): standalone boot-sanity
// command for the Farmer's Delight ecosystem stack (farmersdelight,
// create-central-kitchen + create-dragons-plus, spice-of-life-onion +
// creativecore, ends-delight, extradelight) - `/vpp_food_selftest`.
//
// This is a SEPARATE command from the pack's existing `/vpp_selftest`
// (selftest.js) rather than an addition to it: this session's write scope
// is limited to new files, and keeping item 9's checks in their own command
// avoids growing an already-large shared assertion suite with a second
// author touching it. Same shape/conventions as selftest.js though: a flat
// array of (name, fn) checks, each wrapped so one failure/exception can't
// take down the rest, PASS/FAIL/SKIP tallied and a machine-readable summary
// line emitted last for a test-runner to grep. FD_-prefixed top-level names
// (this pack's server_scripts all share one Rhino scope - see selftest.js's
// own header comment on ST_-prefix collisions already hit once).
//
// Every binding that's reassigned across repeated invocations of the same
// function body uses `let`, never `const` - this pack's installed Rhino
// build does not give `const` fresh per-invocation scoping (see DESIGN.md's
// Rhino-bugs note; already bit tick_accelerator.js/selftest.js/
// leaderboard.js for real before the `let` fix).

const FD_MOD_IDS = [
    'farmersdelight', 'create_central_kitchen', 'create_dragons_plus',
    'solonion', 'creativecore', 'ends_delight', 'extradelight', 'appleskin',
]

// Confirmed real item ids (ground-truthed against each jar's own lang file/
// recipe jsons during item 9's research + implementation pass - not guessed).
const FD_KNIFE_LOCK_IDS = [
    'farmersdelight:golden_knife',
    'farmersdelight:diamond_knife',
    'farmersdelight:netherite_knife',
    'ends_delight:dragon_egg_shell_knife',
    'ends_delight:dragon_tooth_knife',
    'ends_delight:end_stone_knife',
    'ends_delight:purpur_knife',
]

const FD_SAMPLE_FOOD_ITEM_IDS = [
    'farmersdelight:vegetable_soup',
    'farmersdelight:golden_knife',
    'ends_delight:dragon_meat_stew',
    'ends_delight:fried_dragon_egg',
    'extradelight:bacon_cheeseburger',
    'extradelight:grater',
]

const FD_CCK_GAP_PATCH_RECIPE_IDS = [
    'vanillaplusplus:food_cck_gap/crack_non_hatchable_dragon_egg_knife',
    'vanillaplusplus:food_cck_gap/grated_ginger_knife',
    'vanillaplusplus:food_cck_gap/grate_bread_knife',
    'vanillaplusplus:food_cck_gap/grate_carrot_knife',
    'vanillaplusplus:food_cck_gap/grate_garlic_knife',
    'vanillaplusplus:food_cck_gap/grate_potato_knife',
    'vanillaplusplus:food_cck_gap/lemon_zest_grater_knife',
    'vanillaplusplus:food_cck_gap/lime_zest_grater_knife',
    'vanillaplusplus:food_cck_gap/orange_zest_grater_knife',
]

// A real, currently-generated Terralith biome id (Terralith_1.21.1_v2.6.2) -
// used only to confirm the `#minecraft:is_overworld` tag membership FD's
// wild-crop biome_modifier filters on actually reaches Terralith's biomes.
const FD_SAMPLE_TERRALITH_BIOME_ID = 'terralith:alpine_grove'

const FD_ResourceLocationClass = Java.loadClass('net.minecraft.resources.ResourceLocation')
const FD_RegistriesClass = Java.loadClass('net.minecraft.core.registries.Registries')
const FD_TagKeyClass = Java.loadClass('net.minecraft.tags.TagKey')
const FD_ComponentClass = Java.loadClass('net.minecraft.network.chat.Component')

// GROUND-TRUTHED this integration pass (real boot, not assumed): this pack's
// installed KubeJS build ships its own class filter
// (kubejs.classfilter.txt inside the jar) that blocks `net.neoforged.fml`
// wholesale (no re-allow entries under it) - `Java.loadClass('net.neoforged.
// fml.ModList')`/`'net.neoforged.fml.loading.FMLPaths'` both threw
// `InternalError: ... Class is not allowed by class filter!` on a real boot,
// confirmed by inspecting the shipped kubejs.classfilter.txt directly (also
// blocks `java.nio` down to one exception - `java.nio.ByteOrder` - and
// `java.io` down to `Closeable`/`Serializable`, so there is no working
// FMLPaths-replacement or raw-file-read path available from this sandbox
// either). Fixed: mod-loaded checks use the `Platform` global KubeJS itself
// registers (`Platform.isLoaded(modid)`, see BuiltinKubeJSPlugin - a
// pre-bound scripting global, not something this script Java.loadClass()s,
// so the class filter doesn't apply to it) instead of ModList. The
// config/solonion.json runtime check below is honestly SKIPped instead -
// see its own comment for why no in-JVM alternative exists.

function fdRl(id) {
    return FD_ResourceLocationClass.parse(id)
}

function fdItemRegistry(server) {
    return server.registryAccess().registryOrThrow(FD_RegistriesClass.ITEM)
}

const FD_CHECKS = []
function fdCheck(name, fn) { FD_CHECKS.push({ name: name, fn: fn }) }

fdCheck('all 8 item-9 mods (7 new + already-installed appleskin) are loaded', () => {
    let missing = []
    for (let i = 0; i < FD_MOD_IDS.length; i++) {
        if (!Platform.isLoaded(FD_MOD_IDS[i])) missing.push(FD_MOD_IDS[i])
    }
    return { pass: missing.length === 0, detail: missing.length === 0 ? 'all 8 loaded' : 'missing: ' + missing.join(',') }
})

fdCheck('7 knife tier-lock item ids (golden/diamond/netherite + 4 ends_delight) resolve', server => {
    let registry = fdItemRegistry(server)
    let missing = []
    for (let i = 0; i < FD_KNIFE_LOCK_IDS.length; i++) {
        if (!registry.containsKey(fdRl(FD_KNIFE_LOCK_IDS[i]))) missing.push(FD_KNIFE_LOCK_IDS[i])
    }
    return { pass: missing.length === 0, detail: missing.length === 0 ? 'all 7 resolve' : 'missing: ' + missing.join(',') }
})

fdCheck('sample food items across farmersdelight/ends-delight/extradelight resolve', server => {
    let registry = fdItemRegistry(server)
    let missing = []
    for (let i = 0; i < FD_SAMPLE_FOOD_ITEM_IDS.length; i++) {
        if (!registry.containsKey(fdRl(FD_SAMPLE_FOOD_ITEM_IDS[i]))) missing.push(FD_SAMPLE_FOOD_ITEM_IDS[i])
    }
    return { pass: missing.length === 0, detail: missing.length === 0 ? 'all ' + FD_SAMPLE_FOOD_ITEM_IDS.length + ' resolve' : 'missing: ' + missing.join(',') }
})

fdCheck('food_cck_gap_patch.js: all 9 knife-tool gap-patch recipes registered', server => {
    let missing = []
    for (let i = 0; i < FD_CCK_GAP_PATCH_RECIPE_IDS.length; i++) {
        let opt = server.getRecipeManager().byKey(fdRl(FD_CCK_GAP_PATCH_RECIPE_IDS[i]))
        if (!opt.isPresent()) missing.push(FD_CCK_GAP_PATCH_RECIPE_IDS[i])
    }
    return { pass: missing.length === 0, detail: missing.length === 0 ? 'all 9 present' : 'missing: ' + missing.join(',') }
})

fdCheck('Terralith wild-crop generation prerequisite: a real Terralith biome is in #minecraft:is_overworld', server => {
    let registry = server.registryAccess().registryOrThrow(FD_RegistriesClass.BIOME)
    let tagKey = FD_TagKeyClass.create(FD_RegistriesClass.BIOME, fdRl('minecraft:is_overworld'))
    let tagOpt = registry.getTag(tagKey)
    if (!tagOpt.isPresent()) return { pass: false, detail: '#minecraft:is_overworld tag not present' }
    let found = false
    let it = tagOpt.get().iterator()
    while (it.hasNext()) {
        let holder = it.next()
        if (String(registry.getKey(holder.value())) === FD_SAMPLE_TERRALITH_BIOME_ID) { found = true; break }
    }
    return { pass: found, detail: found ? FD_SAMPLE_TERRALITH_BIOME_ID + ' is a member, ok' : FD_SAMPLE_TERRALITH_BIOME_ID + ' NOT found in #minecraft:is_overworld' }
})

// SoL-Onion's own config lives outside NeoForge's TOML system (CreativeCore's
// Gson-based config framework), at config/solonion.json, generated on first
// boot. GROUND-TRUTHED this integration pass (a real boot, not assumed):
// there is no in-JVM-reachable way to read an arbitrary server-relative file
// from this pack's KubeJS/Rhino sandbox at all - `net.neoforged.fml`
// (FMLPaths, for locating the config dir), `java.nio` (Files/Paths, for
// reading it), and `java.io` (File, same) are ALL blocked by this pack's
// installed KubeJS's own class filter (kubejs.classfilter.txt), not just the
// FMLPaths call this check originally tried. This is a structural sandbox
// limit, not a bug fixable by picking a different Java API. So this check
// honestly SKIPs (never FAILs, never fakes a PASS) - the actual runtime
// verification that config/solonion.json's `detriments`/`resetOnDeath`/
// `trackedFoodDiversityDecay`/`trackCount` landed correctly is done
// EXTERNALLY by the release integrator, reading the file directly right
// after a real boot (see DESIGN.md's food-system section for the confirmed
// values and the real, ground-truthed JSON shape - `benefit` turned out to
// be a quoted SNBT-like STRING, e.g. `"{key:\"minecraft:generic.max_health\",
// op:0,type:\"att\",val:2.0d}"`, not the nested `{type, ...}` object the
// pre-boot guidance had guessed, since it couldn't be confirmed without a
// live boot).
fdCheck('config/solonion.json: detriments empty + resetOnDeath/trackedFoodDiversityDecay false + trackCount sized (verified externally, not from KubeJS - see comment above)', () => {
    return { skip: true, detail: 'not reachable from this pack\'s KubeJS/Rhino sandbox (net.neoforged.fml + java.nio + java.io are all blocked by the installed KubeJS build\'s own kubejs.classfilter.txt) - verified externally by the release integrator instead, see DESIGN.md\'s food-system section' }
})

fdCheck('recipe manager: farmersdelight-namespaced recipe count is sane (> 200)', server => {
    // Namespace-prefix count via recipeHolder.id() (the same accessor
    // selftest.js's own "vanillaplusplus:artifact_upgrade/* == 46" check
    // already proves reachable from Rhino) rather than reaching for a
    // recipe-type accessor whose KubeJS/Rhino bean-property exposure isn't
    // independently confirmed - covers farmersdelight's ~333 own recipe
    // files (106 of them farmersdelight:cutting) as a sanity floor without
    // depending on an unverified API surface.
    let recipes = server.getRecipeManager().getRecipes().toArray()
    let n = 0
    for (let i = 0; i < recipes.length; i++) {
        if (String(recipes[i].id()).indexOf('farmersdelight:') === 0) n++
    }
    return { pass: n > 200, detail: n + ' farmersdelight:* recipes' }
})

function fdRunSelftest(ctx) {
    let server = ctx.source.server

    function output(line) {
        ctx.source.sendSystemMessage(FD_ComponentClass.literal(line))
    }

    let results = []
    for (let i = 0; i < FD_CHECKS.length; i++) {
        let c = FD_CHECKS[i]
        let result
        try {
            result = c.fn(server)
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
    output(`VPP_FOOD_SELFTEST: ${status} (${passed}/${executed}, ${skipped} skipped)`)
    return passed
}

ServerEvents.commandRegistry(event => {
    let { commands: Commands } = event

    event.register(
        Commands.literal('vpp_food_selftest').executes(ctx => {
            try {
                return fdRunSelftest(ctx)
            } catch (e) {
                console.error('[vpp food_selftest] top-level EXCEPTION: ' + e + (e && e.stack ? ('\n' + e.stack) : ''))
                ctx.source.sendSystemMessage(FD_ComponentClass.literal('VPP_FOOD_SELFTEST: FAIL (top-level exception, see server log: ' + e + ')'))
                return 0
            }
        })
    )
})
