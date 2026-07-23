// `/respec` - full reset of the unified skill tree.
//
// Before issue #71, every puffish_skills category forked at a shared trunk
// into two MUTUALLY EXCLUSIVE 5-node spec paths, and this file's job was to
// let a player abandon their committed fork and try the other one (locking
// exactly the 5 nodes of the path they'd committed to, refund automatic).
//
// Issue #71 point 2 removed exclusivity WITHIN a category entirely: every
// category became a 34-node tree where every node is reachable by spending
// enough points, nothing locked OUT by a rival choice. Issue #116
// ("Converge all skill trees into ONE unified tree") SUPERSEDES #71's
// 23-category structure with a single category (scripts/gen_skill_tree.py's
// UNIFIED_CATEGORY_ID) - there is exactly one category to respec now, so
// `/respec` no longer takes a category argument at all. Issue #116 DOES
// reintroduce exclusivity, but only at the 4 class-root nodes (a full
// `exclusive` clique - see gen_skill_tree.py's module docstring point 3);
// a full-category reset via Category#resetSkills locks every unlocked node
// including the chosen class root, which per
// net.puffish.skillsmod.server.data.CategoryData.getSkillState's exclusion
// re-evaluation (live off the unlocked-skill set, not cached) immediately
// un-excludes the other 3 class roots again - so a respec really does let a
// player freely re-pick their class afterward, not just replan within it.
//
// The public API has a purpose-built bulk operation for a full reset:
//   net.puffish.skillsmod.api.Category#resetSkills(ServerPlayer): void
// (method descriptor confirmed via a raw classfile constant-pool parse of
// the installed puffish_skills-0.18.1-1.21-neoforge.jar's
// net/puffish/skillsmod/api/Category.class - `resetSkills` takes exactly a
// ServerPlayer and returns void, sitting right next to `unlock`/`lock`/
// `erase` in the same public API surface already relied on below). This
// locks every unlocked skill in the category and refunds every spent point
// in one call - no per-node id list to keep in sync with gen_skill_tree.py's
// node-count/shape at all.
//
// API surface (javap/constant-pool-verified against net.puffish.skillsmod.
// api.* in the same jar):
//   SkillsAPI.getCategory(ResourceLocation) -> Optional<Category>
//   Category.getSpentPoints(ServerPlayer)   -> int
//   Category.resetSkills(ServerPlayer)      -> void

const RESPEC_UNIFIED_CATEGORY_ID = 'adventurer'

let RespecResourceLocationClass = null
let RespecSkillsAPIClass = null
try {
    RespecResourceLocationClass = Java.loadClass('net.minecraft.resources.ResourceLocation')
    RespecSkillsAPIClass = Java.loadClass('net.puffish.skillsmod.api.SkillsAPI')
} catch (e) {
    console.error('[vpp respec] Pufferfish Skills API failed to load - /respec will be unavailable: ' + e)
}

// ---------------------------------------------------------------------------
// Cost hook. Respec is FREE for now (provisional call, recorded in
// DECISIONS.md - open balance question for playtest). This is the one
// obvious insertion point for a future cost: return false (after telling the
// player why, e.g. insufficient currency) to block the respec, or charge the
// currency here and return true to let it proceed.
// ---------------------------------------------------------------------------
function chargeRespecCost(player) {
    return true
}

function respecUnifiedTree(player) {
    if (!RespecSkillsAPIClass || !RespecResourceLocationClass) {
        player.tell('Respec is unavailable right now (skill API failed to load).')
        return
    }
    try {
        // `let`, not `const`, for every binding declared directly inside
        // this try block - this pack's installed Rhino build (KubeJS
        // 2101.7.2/build.368) throws "TypeError: redeclaration of
        // const/var X" for a `const`/`let` declared directly inside a
        // `try { }` body, ground-truthed against the actual installed
        // rhino-2101.2.7-build.85.jar (GitHub issue #8's audit) - matches
        // the same installed-Rhino limitation already fixed elsewhere in
        // this codebase (tick_accelerator.js/selftest.js/leaderboard.js).
        let rl = RespecResourceLocationClass.fromNamespaceAndPath('puffish_skills', RESPEC_UNIFIED_CATEGORY_ID)
        let catOpt = RespecSkillsAPIClass.getCategory(rl)
        if (!catOpt.isPresent()) {
            player.tell('The unified skill tree is unavailable right now.')
            return
        }
        let category = catOpt.get()

        let spentPoints = category.getSpentPoints(player)
        if (spentPoints <= 0) {
            player.tell("You haven't spent any skill points yet - nothing to respec.")
            return
        }

        if (!chargeRespecCost(player)) {
            return // chargeRespecCost is responsible for telling the player why
        }

        category.resetSkills(player)
        player.tell(`Respec complete: cleared every unlocked node and refunded ${spentPoints} point(s). Your class choice is unlocked again too - pick freely and replan from scratch.`)
    } catch (e) {
        console.error(`[vpp respec] respec failed for ${player.username}: ${e}`)
        player.tell('Respec failed - see server log.')
    }
}

ServerEvents.commandRegistry(event => {
    const { commands: Commands } = event

    // Issue #116: one unified category means there's nothing left to pick a
    // category argument FOR - `/respec` alone fully resets the tree
    // (including the chosen class, letting the player switch classes too).
    let respecCommand = Commands.literal('respec')
        .executes(ctx => {
            respecUnifiedTree(ctx.source.playerOrException)
            return 1
        })

    event.register(respecCommand)
})
