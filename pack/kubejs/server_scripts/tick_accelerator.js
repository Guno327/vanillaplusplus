// TODO.md item 10: Time-in-a-Bottle tick accelerator (DECISIONS.md "Item 10 -
// Tick accelerator (user decisions, FINAL)" + "Item 10 (tick accelerator) -
// orchestrator calls on research verdicts"). Mods: time-in-a-bottle-universal
// 6.5.4 (modId tiab, item tiab:time_in_a_bottle) + its required companion
// time-in-a-bottle-fix-tiab-fix 1.3.0 (modId tiabfix, needed for crop/animal
// acceleration to actually work). Tier-locked at Brass Age via a plain
// ProgressiveStages item lock (pack/config/ProgressiveStages/brass_age.toml)
// - nothing to do here for that part.
//
// This script implements the two mechanisms DECISIONS.md calls out as
// needing custom KubeJS work on top of the mod's own behavior:
//
//   (a) Create-kinetics exclusion - layer onto tiab's own
//       `tiab:un_acceleratable` block tag (ground-truthed from the jar:
//       data/tiab/tags/block/un_acceleratable.json, replace:false, default
//       values [minecraft:chest, minecraft:grass_block] - the mod's own
//       shipped defaults, left untouched, we only ADD to the tag) via a
//       registry scan for every block whose BlockEntity is a Create
//       KineticBlockEntity. A hand-written id list would rot every time
//       Create or an addon ships a new kinetic block.
//
//   (b) Hard one-per-player enforcement for tiab:time_in_a_bottle - not
//       native to the mod. ItemEvents.crafted + a live inventory scan (not
//       a permanent flag, so re-crafting after genuine loss works) + manual
//       refund of the exact recipe ingredients, since the crafted event has
//       no verified cancel() semantics to lean on (confirmed: KubeJS's
//       ItemCraftedKubeEvent implements only KubePlayerEvent, no
//       Cancellable-style interface - see the class list in
//       kubejs-neoforge-2101.7.2-build.368.jar). Voiding the output by
//       zeroing its count is the reliable mechanism instead.
//
// DISCLOSED SOFT-ENFORCEMENT GAPS (per DECISIONS.md, accepted, not fixed
// here - same standing as every other unique-item gap in this pack):
//   - A second bottle stashed in external storage (Refined Storage network,
//     Ender Chest via item-transfer mods, a Sophisticated Backpack, a
//     Curios slot, etc.) evades the live-inventory scan below, since it
//     only reads the player's own vanilla Inventory container (main hotbar/
//     backpack slots + armor + offhand - see the comment on TIAB_ITEM_ID's
//     scan for why that one Container already covers all three).
//   - The jovian creative-crate duplication gap applies here exactly as it
//     does to every other unique item in this pack (Artifacts trinkets,
//     etc.) - a creative-mode player can just spawn in extra bottles.

// ---- (a) Create-kinetics registry scan -> tiab:un_acceleratable ----
//
// Ground-truthed against the actually-installed create-1.21.1-6.0.10.jar
// (this session had no javap/JDK available in the sandbox - verified
// instead with a small pure-Python .class constant-pool/method-table
// parser used as a javap substitute):
//   - com.simibubi.create.content.kinetics.base.KineticBlockEntity exists
//     at that exact path (extends com.simibubi.create.foundation.
//     blockEntity.SmartBlockEntity).
//   - Create's concrete kinetic blocks (e.g. simpleRelays/
//     AbstractShaftBlock) implement com.simibubi.create.foundation.block.
//     IBE, which itself implements vanilla net.minecraft.world.level.
//     block.EntityBlock and carries newBlockEntity(BlockPos, BlockState):
//     BlockEntity - i.e. the standard EntityBlock#newBlockEntity override,
//     also confirmed present (abstract, public) on vanilla EntityBlock
//     itself in the server jar. So: for every registered Block that
//     implements EntityBlock, calling newBlockEntity(pos, state) and
//     checking the result's class against KineticBlockEntity is a
//     mechanically sound way to find every kinetic block, including every
//     Create addon's own (create_sa/createaddition/createoreexcavation/
//     create_power_loader/etc), without a hand-maintained id list.
//
// Explicit iterator (not for-of) over the raw java.util Iterable returned
// by BuiltInRegistries.BLOCK - this codebase's own established convention
// (see leaderboard.js's collectPlayerEntries: KubeJS wrapper collections
// like EntityArrayList are a proven for-of target, but a *raw* Java
// Iterable/Set is walked via explicit iteration instead, not for-of).
ServerEvents.tags('block', event => {
    let UN_ACCELERATABLE_TAG = 'tiab:un_acceleratable'
    // Never touch spawners - explicit, twice-stated user decision in
    // DECISIONS.md ("Spawners deliberately remain accelerable... synergy
    // with Apothic Spawners upgrades is an intended late-game payoff").
    // Belt-and-suspenders: the scan below would never add them anyway
    // (SpawnerBlockEntity/ApothSpawnerTile - verified via javap-equivalent
    // on ApothicSpawners-1.21.1-1.3.4.jar, ApothSpawnerBlock extends
    // vanilla SpawnerBlock, no relation to Create's KineticBlockEntity
    // hierarchy at all) but this id-based skip is kept as an explicit,
    // readable guarantee rather than relying solely on the type check.
    let NEVER_EXCLUDE = ['minecraft:spawner', 'minecraft:trial_spawner']

    try {
        // NOTE: every binding in this try block (and the while loop below)
        // is declared with `let`, not `const` - this pack's installed Rhino
        // engine (KubeJS 2101.7.2/build.368) does not give `const` fresh
        // per-invocation/per-iteration scoping inside a try/catch or loop
        // body that can run more than once (see DESIGN.md's "Release
        // engineering" Rhino-bugs note - the same fix already applied to
        // selftest.js/leaderboard.js). ServerEvents.tags' callback runs more
        // than once per boot (confirmed at post-release-merge boot-test
        // time: the original all-`const` version threw "TypeError:
        // redeclaration of const/var X" on the very first statement of a
        // second invocation, sending every boot down the static-fallback
        // path below instead of the real registry scan).
        let BuiltInRegistriesClass = Java.loadClass('net.minecraft.core.registries.BuiltInRegistries')
        let EntityBlockClass = Java.loadClass('net.minecraft.world.level.block.EntityBlock')
        let KineticBlockEntityClass = Java.loadClass('com.simibubi.create.content.kinetics.base.KineticBlockEntity')
        let BlockPosClass = Java.loadClass('net.minecraft.core.BlockPos')

        let blockRegistry = BuiltInRegistriesClass.BLOCK
        let zeroPos = BlockPosClass.ZERO

        let scanned = 0
        let tagged = 0
        let skippedSpawners = 0
        let it = blockRegistry.iterator()
        while (it.hasNext()) {
            let block = it.next()
            scanned++
            if (!(block instanceof EntityBlockClass)) continue

            let idObj = blockRegistry.getKey(block)
            if (!idObj) continue
            let id = idObj.toString()
            if (NEVER_EXCLUDE.indexOf(id) !== -1) {
                skippedSpawners++
                continue
            }

            let blockEntity = null
            try {
                blockEntity = block.newBlockEntity(zeroPos, block.defaultBlockState())
            } catch (e) {
                // Some EntityBlocks assume a real level/position context at
                // construction time and throw here - skip defensively,
                // this is exactly the kind of per-block failure the
                // registry scan needs to survive without aborting.
                continue
            }
            if (blockEntity !== null && blockEntity instanceof KineticBlockEntityClass) {
                event.add(UN_ACCELERATABLE_TAG, id)
                tagged++
            }
        }
        console.info(`[vpp tick_accelerator] Create-kinetics registry scan: tagged ${tagged} block(s) into ${UN_ACCELERATABLE_TAG} out of ${scanned} blocks scanned (${skippedSpawners} spawner id(s) explicitly protected from exclusion)`)
    } catch (e) {
        // Rhino/registry interop failure at boot must not break script load
        // for the whole pack - log loudly and fall back to a small static
        // list of Create's own base kinetic blocks (covers the most common
        // player-visible cases; addon-added kinetic blocks will NOT be
        // excluded in this fallback path - a known, logged degradation,
        // not a silent one). This is exactly the kind of runtime interop
        // failure DECISIONS.md flags as a real risk for this design.
        console.error('[vpp tick_accelerator] Create-kinetics registry scan FAILED - falling back to a static base-Create id list (addon kinetic blocks will NOT be excluded from acceleration this boot): ' + e)
        const FALLBACK_KINETIC_IDS = [
            'create:shaft', 'create:cogwheel', 'create:large_cogwheel',
            'create:gearbox', 'create:clutch', 'create:gearshift',
            'create:water_wheel', 'create:large_water_wheel', 'create:windmill_bearing',
            'create:encased_fan', 'create:millstone', 'create:mechanical_press',
            'create:mechanical_mixer', 'create:mechanical_saw', 'create:mechanical_drill',
            'create:mechanical_plough', 'create:mechanical_harvester', 'create:deployer',
            'create:mechanical_arm', 'create:crushing_wheel', 'create:crushing_wheel_controller',
            'create:flywheel', 'create:rope_pulley', 'create:elevator_pulley',
            'create:hose_pulley', 'create:item_drain', 'create:portable_storage_interface',
            'create:portable_fluid_interface', 'create:sequenced_gearshift',
            'create:speedometer', 'create:stressometer', 'create:steam_engine',
            'create:steam_whistle', 'create:turntable', 'create:basin',
            'create:blaze_burner', 'create:depot', 'create:weighted_ejector',
        ]
        try {
            FALLBACK_KINETIC_IDS.forEach(id => event.add('tiab:un_acceleratable', id))
            console.error(`[vpp tick_accelerator] fallback applied: ${FALLBACK_KINETIC_IDS.length} static id(s) added to tiab:un_acceleratable`)
        } catch (e2) {
            console.error('[vpp tick_accelerator] fallback tag population ALSO failed - tiab:un_acceleratable only has the mod\'s own shipped defaults this boot: ' + e2)
        }
    }
})

// ---- (b) hard one-per-player enforcement ----
//
// Ground-truthed from the jar's own data/tiab/recipe/time_in_a_bottle.json
// (shaped 3x3: GGG / DCD / LBL):
const TIAB_ITEM_ID = 'tiab:time_in_a_bottle'
const TIAB_RECIPE_REFUND = [
    { id: 'minecraft:gold_ingot', count: 3 },
    { id: 'minecraft:diamond', count: 2 },
    { id: 'minecraft:clock', count: 1 },
    { id: 'minecraft:lapis_lazuli', count: 2 },
    { id: 'minecraft:glass_bottle', count: 1 },
]

ItemEvents.crafted(TIAB_ITEM_ID, event => {
    try {
        // `let`, not `const` - this callback fires on every craft of this
        // item, and this pack's installed Rhino build does not give `const`
        // fresh scoping across repeat invocations of the same try block
        // (see the registry-scan fix above / DESIGN.md's Rhino-bugs note);
        // an all-`const` version here would throw "redeclaration" on the
        // second bottle craft, silently defeating the one-per-player
        // enforcement this whole file exists to add.
        let player = event.player
        let craftedStack = event.item
        if (!player || !craftedStack || craftedStack.isEmpty()) return

        // NeoForge's PlayerEvent.ItemCraftedEvent (which this KubeJS event
        // wraps) fires from ResultSlot#checkTakeAchievements/onTake, i.e.
        // strictly BEFORE the crafted stack is placed into the player's
        // inventory or cursor (confirmed via constant-pool inspection of
        // ResultSlot.class in neoforge-21.1.235-server.jar: it calls
        // EventHooks.firePlayerCraftingEvent from inside onTake, ahead of
        // the caller's own inventory-placement logic). So a scan of
        // player.inventory at this exact moment can never see the item
        // currently being crafted - only genuinely pre-existing bottles -
        // no extra bookkeeping needed to avoid the craft flagging itself.
        //
        // player.inventory wraps net.minecraft.world.entity.player.
        // Inventory, which is a SINGLE Container spanning main/backpack
        // slots + armor + offhand together (confirmed via its own class
        // file: three backing lists - items/armor/offhand - combined
        // behind one getContainerSize()/getItem(int) address space, same
        // fact this pack's leaderboard.js already relies on for its own
        // coin-counting scan). So this one call covers "inventory, armor,
        // offhand" all at once, per DECISIONS.md's requirement - it does
        // NOT reach Ender Chest, Curios slots, backpacks, or any storage
        // network (see the disclosed gaps at the top of this file).
        let existingSlot = player.inventory.find(TIAB_ITEM_ID)
        if (existingSlot < 0) {
            return // no existing bottle found - this craft is legitimate
        }

        // Player already holds a bottle - void the newly crafted stack and
        // manually refund the exact ingredients it just consumed (cancel()
        // semantics on this event are unverified/unavailable - see the
        // header comment - so zeroing the output's count is the mechanism).
        craftedStack.count = 0
        TIAB_RECIPE_REFUND.forEach(ingredient => player.give(Item.of(ingredient.id, ingredient.count)))
        player.tell('§cYou already have a Time in a Bottle - only one per player is allowed. Ingredients refunded.')
    } catch (e) {
        console.error('[vpp tick_accelerator] one-per-player enforcement failed (bottle craft was NOT blocked this time) for ' + (event && event.player ? event.player.username : 'unknown player') + ': ' + e)
    }
})
