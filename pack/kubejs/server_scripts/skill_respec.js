// Issue #71 ("Expand Skill Trees / Categories") - `/respec <category>`.
//
// Before issue #71, every puffish_skills category forked at a shared trunk
// into two MUTUALLY EXCLUSIVE 5-node spec paths, and this file's job was to
// let a player abandon their committed fork and try the other one (locking
// exactly the 5 nodes of the path they'd committed to, refund automatic).
//
// Issue #71 point 2 removed exclusivity entirely: every category is now a
// 34-node tree (scripts/gen_skill_tree.py) where every node is reachable by
// spending enough points, nothing is ever locked OUT by a rival choice. So
// there is no more "committed path" to detect or abandon - the one thing
// left for a respec to do is let a player who mis-spent points reclaim them
// and replan, which is a FULL reset of the category, not a per-path one.
//
// That simplification also means the old node-by-node lock loop (needed
// before because a respec had to lock exactly 5 specific node ids on
// whichever path had been committed to) is dead weight now - the public API
// has a purpose-built bulk operation for exactly this:
//   net.puffish.skillsmod.api.Category#resetSkills(ServerPlayer): void
// (method descriptor confirmed this session via a raw classfile constant-
// pool parse of the installed puffish_skills-0.18.1-1.21-neoforge.jar's
// net/puffish/skillsmod/api/Category.class - `resetSkills` takes exactly a
// ServerPlayer and returns void, sitting right next to `unlock`/`lock`/
// `erase` in the same public API surface already relied on below). This
// locks every unlocked skill in the category and refunds every spent point
// in one call - no per-node id list to keep in sync with gen_skill_tree.py's
// node-count/shape at all, which the old per-path approach could not have
// avoided (it hardcoded ['a0'..'a4']/['b0'..'b4'], impossible to keep
// working once categories went from 15 fixed nodes to 34 generated ones).
//
// API surface (javap/constant-pool-verified against net.puffish.skillsmod.
// api.* in the same jar):
//   SkillsAPI.getCategory(ResourceLocation) -> Optional<Category>
//   Category.getSpentPoints(ServerPlayer)   -> int
//   Category.resetSkills(ServerPlayer)      -> void

const RESPEC_SKILL_CATEGORIES = [
    'alchemy', 'bows', 'building', 'cooking', 'daggers', 'enchanting',
    'exploration', 'farming', 'fishing', 'greatswords', 'longswords',
    'magic', 'mining', 'running', 'sailing', 'smithing', 'spears',
    'swimming', 'swords', 'tachi', 'taming', 'trading', 'woodcutting',
]

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
function chargeRespecCost(player, categoryId) {
    return true
}

function respecCategory(player, categoryId) {
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
        let rl = RespecResourceLocationClass.fromNamespaceAndPath('puffish_skills', categoryId)
        let catOpt = RespecSkillsAPIClass.getCategory(rl)
        if (!catOpt.isPresent()) {
            player.tell(`Unknown skill category: ${categoryId}`)
            return
        }
        let category = catOpt.get()

        let spentPoints = category.getSpentPoints(player)
        if (spentPoints <= 0) {
            player.tell(`You haven't spent any points in ${categoryId} yet - nothing to respec.`)
            return
        }

        if (!chargeRespecCost(player, categoryId)) {
            return // chargeRespecCost is responsible for telling the player why
        }

        category.resetSkills(player)
        player.tell(`Respec complete: cleared every unlocked node in ${categoryId} and refunded ${spentPoints} point(s). Replan freely - nothing in this category locks you out anymore.`)
    } catch (e) {
        console.error(`[vpp respec] respec failed for ${player.username} / ${categoryId}: ${e}`)
        player.tell('Respec failed - see server log.')
    }
}

ServerEvents.commandRegistry(event => {
    const { commands: Commands } = event

    let respecCommand = Commands.literal('respec')
        .executes(ctx => {
            ctx.source.playerOrException.tell(`Usage: /respec <category>. Categories: ${RESPEC_SKILL_CATEGORIES.join(', ')}`)
            return 0
        })

    // One literal subcommand per category rather than a string ArgumentType
    // - Brigadier literal chaining (Commands.literal(...).then(...)) is
    // already exercised elsewhere in this pack's command registrations
    // (economy.js/dailies.js), whereas no script here has ever registered a
    // Commands.argument(...)/Arguments.STRING interop call, and this cannot
    // be boot-tested to find out if that guess would have been right.
    for (const categoryId of RESPEC_SKILL_CATEGORIES) {
        respecCommand = respecCommand.then(
            Commands.literal(categoryId)
                .executes(ctx => {
                    respecCategory(ctx.source.playerOrException, categoryId)
                    return 1
                })
        )
    }

    event.register(respecCommand)
})
