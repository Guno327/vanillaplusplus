// TODO.md item 8: /leaderboard chat command - wealth / tier / level, for
// individual players and party-based teams. Plain chat output (player.tell),
// same command-registration pattern economy.js/dailies.js already use -
// no GUI, no physical block/item.
//
// Ground-truth verification performed this session (javap against the
// actually-installed server jars under server/mods/ and server/libraries/,
// export PATH="/home/ubuntu/vanilla++/.tools/jdk-21.0.11+10/bin:$PATH"):
//
// WEALTH:
//  - Coin denominations copied from economy.js's own verified table
//    (numismatics:spur=1, bevel=8, sprocket=16, cog=64, crown=512, sun=4096).
//  - Physical coins are counted via net.minecraft.world.Container's
//    getContainerSize()/getItem(int) on both Player.getInventory() and
//    Player.getEnderChestInventory() (javap net.minecraft.world.entity.
//    player.Inventory / net.minecraft.world.inventory.
//    PlayerEnderChestContainer confirms both implement Container).
//  - Numismatics DOES have a server-side bank API and it IS cleanly
//    reachable from Rhino: `dev.ithundxr.createnumismatics.Numismatics.BANK`
//    is a public static final GlobalBankManager; `.getBalance()` (public int,
//    raw spurs, same base unit as the coin table per Coin.toSpurs) gives the
//    stored balance. Confirmed via javap against
//    CreateNumismatics-1.0.20+neoforge-mc1.21.1.jar. Included in wealth.
//    getAccount() is get-or-create (matches the mod's own /view command's
//    behavior) so calling it can silently create an empty 0-balance
//    account for a player who never opened a bank terminal - harmless.
//    CORRECTED (client-test-harness hardening, 2026-07-23): GlobalBankManager
//    overloads BOTH `getAccount(Player)` AND `getAccount(UUID)` (javap-
//    confirmed) - calling the Player-typed overload with a real, live
//    ServerPlayer from Rhino throws `InternalError: ... is ambiguous;
//    candidate methods are: ...` (ground-truthed: this is exactly what L3's
//    real-client-join tier hit, since a genuine connected player is the only
//    way to reach this code with a real ServerPlayer rather than a null/
//    console-only value). Rhino cannot disambiguate the two overloads for a
//    ServerPlayer argument even though it unambiguously satisfies `Player`
//    in plain Java. Calling `getAccount(player.getUUID())` instead resolves
//    to the single UUID overload with no ambiguity, and returns the exact
//    same BankAccount (both overloads key the same underlying account
//    store) - a same-behavior, ambiguity-free call, not a workaround that
//    changes what account is looked up.
//
// TIER: player.stages.has(id) - the same KubeJS game-stages binding
// mob_scaling.js already uses - across the 10 ProgressiveStages tier ids
// (confirmed present as `id = "..."` in pack/config/ProgressiveStages/
// *.toml). Tier = count of stages held, highest stage id shown nicely.
//
// LEVEL: net.puffish.skillsmod.api.SkillsAPI.getCategory(ResourceLocation)
// -> Optional<Category>; Category.getExperience() -> Optional<Experience>;
// Experience.getLevel(ServerPlayer) -> int. All confirmed via javap against
// puffish_skills-0.18.0-1.21-neoforge.jar. Category ResourceLocations use
// namespace "puffish_skills" (confirmed by decompiling
// net.puffish.skillsmod.SkillsMod.createIdentifier, the method the mod's
// own CategoryArgumentType uses to resolve bare category names like the
// ones skills.js/dailies.js already pass to the `puffish_skills experience
// add <player> <category> <amount>` command). The 12 category ids are the
// directory names under pack/kubejs/data/puffish_skills/puffish_skills/
// categories/. Level = sum of per-category levels (Pufferfish Skills has
// no single "overall level" concept - it's per-category).
//
// TEAMS (GitHub #32 - ported off FTB Teams to Open Parties and Claims,
// FTB Teams/Chunks dropped for redistribution reasons, see #28): OPAC's
// real API, confirmed via javap against the actually-resolved
// open-parties-and-claims-neoforge-1.21.1-0.27.8.jar (+ its Modrinth-
// published sources jar, cross-read for clarity) -
// xaero.pac.common.server.api.OpenPACServerAPI.get(server) -> instance;
// .getPartyManager() -> IPartyManagerAPI; .getAllStream() ->
// Stream<IServerPartyAPI> (every party on the server - confirmed by
// reading PlayerLogInPartyAssigner.java in the sources jar that, unlike
// FTB Teams, OPAC does NOT auto-create a personal solo party for every
// player, so this stream only contains parties players actually formed
// via /party create - solo players simply have no party and won't appear
// under "teams" at all, a real behavior difference from FTB Teams worth
// knowing about, not just a renamed API). IServerPartyAPI.
// getMemberInfoStream() -> Stream<IPartyMemberAPI> (confirmed via
// Party.java's getTypedMemberInfoStream(): `Stream.concat(Stream.of(owner),
// memberInfo.values().stream())` - this DOES include the owner, so no
// separate getOwner() call is needed, same "one call gets everyone" shape
// FTB Teams' Team.getMembers() had). IPartyMemberAPI.getUUID() -> UUID
// (IPartyPlayerInfoAPI's method, IPartyMemberAPI extends it).
// IServerPartyAPI.getDefaultName() -> String (confirmed via Party.java:
// `String.format("%s's Party", owner.getUsername())` - OPAC parties have
// no settable custom name unlike FTB Teams' short name, so this is the
// closest display-name equivalent and what's shown below).
// Team tier/wealth/level aggregation logic itself is unchanged from the
// FTB Teams version - team_mode's party-wide *stage* sharing is now a
// KubeJS bridge instead of ProgressiveStages' own backend (see
// progression_stage_bridge.js's psbSyncPartyStages - progressivestages
// 2.1/3.0.1's TeamProvider only ships SoloIntegration/
// ReflectiveFTBTeamsIntegration, confirmed via javap, no OPAC hook exists
// natively), so player.stages.has(id) on an online party member still
// reflects the party's collective tier within about a second of any
// member's stage grant, same practical effect as before. Team tier = max
// across whichever members we can read a value for (online live, offline
// cached) as a safety net, even though it should normally already be
// identical for every member. Team wealth/level = sum of member
// wealth/level (own decision, stated per TODO.md's open question - these
// aren't natively team-pooled so sum is the most natural aggregate for
// "how rich/skilled is this team as a whole", matching how a shared team
// storage/XP pool would read).
//
// CACHING: offline players/team-members can't have their tier/level read
// live (player.stages.has() and SkillsAPI.getCategory(...).getExperience()
// .getLevel() both require a live ServerPlayer instance) and wealth is
// expensive to recompute from a live inventory anyway - so all three
// metrics are cached in server.persistentData (confirmed present via
// javap dev.latvian.mods.kubejs.core.MinecraftServerKJS extends
// WithPersistentData -> kjs$getPersistentData(), the same pattern
// entity.persistentData already uses in mob_scaling.js), keyed by
// metric -> player UUID string -> {username, value, extra, timestamp}.
// Refreshed for every online player whenever /leaderboard runs, and also
// on PlayerEvents.loggedOut (confirmed present: EventGroup "PlayerEvents",
// handler id "loggedOut", via javap against
// dev.latvian.mods.kubejs.plugin.builtin.event.PlayerEvents) so a player's
// last-known numbers are reasonably fresh even if nobody ran the command
// right before they left. Offline entries are marked "(last seen)".

const COIN_VALUES = {
    'numismatics:sun': 4096,
    'numismatics:crown': 512,
    'numismatics:cog': 64,
    'numismatics:sprocket': 16,
    'numismatics:bevel': 8,
    'numismatics:spur': 1,
}

const TIER_IDS = [
    'rootborn', 'andesite_age', 'brass_age', 'precision_age', 'induction_age',
    'starforged_age', 'lunar_frontier', 'martian_frontier', 'inner_system', 'jovian_frontier',
]

// Issue #71 ("Expand Skill Trees / Categories"): 12 -> 23 categories - kept
// in sync by hand with gen_skill_tree.py's CATEGORY_SPECS ids (see that
// file) and skill_respec.js's RESPEC_SKILL_CATEGORIES, which lists the
// same 23 ids.
const SKILL_CATEGORIES = [
    'alchemy', 'bows', 'building', 'cooking', 'daggers', 'enchanting',
    'exploration', 'farming', 'fishing', 'greatswords', 'longswords',
    'magic', 'mining', 'running', 'sailing', 'smithing', 'spears',
    'swimming', 'swords', 'tachi', 'taming', 'trading', 'woodcutting',
]

const CACHE_ROOT_KEY = 'vpp_leaderboard_cache'

// Core vanilla NBT classes - always present, no defensive wrapping needed
// (unlike the three mod APIs below, which get try/catch since this session
// cannot boot-test against the real server).
const CompoundTagClass = Java.loadClass('net.minecraft.nbt.CompoundTag')
const ResourceLocationClass = Java.loadClass('net.minecraft.resources.ResourceLocation')

let SkillsAPIClass = null
try {
    SkillsAPIClass = Java.loadClass('net.puffish.skillsmod.api.SkillsAPI')
} catch (e) {
    console.error('[vpp leaderboard] Pufferfish Skills API (net.puffish.skillsmod.api.SkillsAPI) failed to load - /leaderboard level will report unavailable: ' + e)
}

let NumismaticsClass = null
try {
    NumismaticsClass = Java.loadClass('dev.ithundxr.createnumismatics.Numismatics')
} catch (e) {
    console.error('[vpp leaderboard] Numismatics bank API (dev.ithundxr.createnumismatics.Numismatics) failed to load - wealth will be coin-count only: ' + e)
}

let OpenPACServerAPIClass = null
try {
    OpenPACServerAPIClass = Java.loadClass('xaero.pac.common.server.api.OpenPACServerAPI')
} catch (e) {
    console.error('[vpp leaderboard] Open Parties and Claims API (xaero.pac.common.server.api.OpenPACServerAPI) failed to load - teams mode will report unavailable: ' + e)
}

// ---- persistent cache helpers ----

function ensureCompound(parent, key) {
    if (!parent.contains(key, 10)) { // 10 = NBT compound-tag type id
        parent.put(key, new CompoundTagClass())
    }
    return parent.getCompound(key)
}

function getMetricCache(server, metric) {
    let root = ensureCompound(server.persistentData, CACHE_ROOT_KEY)
    return ensureCompound(root, metric)
}

function cacheMetricValue(server, metric, player, value, extra) {
    let cache = getMetricCache(server, metric)
    let entry = new CompoundTagClass()
    entry.putString('username', player.username)
    entry.putInt('value', Math.trunc(value))
    entry.putLong('timestamp', Date.now())
    if (extra) entry.putString('extra', extra)
    cache.put(String(player.uuid), entry)
}

// ---- metric computation (each takes a live ServerPlayer) ----

function countCoins(container) {
    let total = 0
    let size = container.getContainerSize()
    for (let i = 0; i < size; i++) {
        let stack = container.getItem(i)
        if (!stack || stack.isEmpty()) continue
        let value = COIN_VALUES[stack.id]
        if (value !== undefined) total += value * stack.getCount()
    }
    return total
}

function computeWealth(player) {
    let total = countCoins(player.getInventory())
    total += countCoins(player.getEnderChestInventory())
    if (NumismaticsClass) {
        try {
            // getAccount(player.uuid), not getAccount(player) - see the
            // module docstring's CORRECTED note: the Player-typed overload is
            // ambiguous for a real ServerPlayer under Rhino; the UUID overload
            // is unambiguous and returns the identical account. `player.uuid`
            // (a property), not `player.getUUID()` - the latter is not a
            // callable Rhino method on KubeJS's ServerPlayer wrapper
            // (ground-truthed via a real L3 run: "TypeError: Cannot find
            // function getUUID..."); `.uuid` is this file's own accessor
            // elsewhere (see cache.put(String(player.uuid), ...) above).
            let account = NumismaticsClass.BANK.getAccount(player.uuid)
            total += account.getBalance()
        } catch (e) {
            console.error('[vpp leaderboard] bank balance read failed for ' + player.username + ': ' + e)
        }
    }
    return total
}

function computeTier(player) {
    let count = 0
    let highestId = null
    for (let i = 0; i < TIER_IDS.length; i++) {
        if (player.stages.has(TIER_IDS[i])) {
            count++
            highestId = TIER_IDS[i]
        }
    }
    return { count: count, highestId: highestId }
}

function niceTierName(id) {
    if (!id) return 'None'
    return id.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
}

function computeLevel(player) {
    if (!SkillsAPIClass) return 0
    let total = 0
    for (let i = 0; i < SKILL_CATEGORIES.length; i++) {
        try {
            let rl = ResourceLocationClass.fromNamespaceAndPath('puffish_skills', SKILL_CATEGORIES[i])
            let catOpt = SkillsAPIClass.getCategory(rl)
            if (catOpt.isPresent()) {
                let expOpt = catOpt.get().getExperience()
                if (expOpt.isPresent()) {
                    total += expOpt.get().getLevel(player)
                }
            }
        } catch (e) {
            console.error('[vpp leaderboard] level lookup failed for category ' + SKILL_CATEGORIES[i] + ' / player ' + player.username + ': ' + e)
        }
    }
    return total
}

// ---- ranking collection ----
// computeFn: ServerPlayer -> { value, extra }

function collectPlayerEntries(server, metric, computeFn) {
    let cache = getMetricCache(server, metric)
    let onlineKeys = {}
    let entries = []
    for (const p of server.players) { // KubeJS EntityArrayList, proven for-of target (mob_scaling.js)
        let r = computeFn(p)
        cacheMetricValue(server, metric, p, r.value, r.extra)
        onlineKeys[String(p.uuid)] = true
        entries.push({ name: p.username, value: r.value, extra: r.extra, online: true })
    }
    let offlineKeys = cache.getAllKeys().toArray() // raw java.util.Set - iterate via toArray, not for-of
    for (let i = 0; i < offlineKeys.length; i++) {
        let key = String(offlineKeys[i])
        if (onlineKeys[key]) continue
        let entry = cache.getCompound(key)
        entries.push({
            name: entry.getString('username'),
            value: entry.getInt('value'),
            extra: entry.contains('extra') ? entry.getString('extra') : null,
            online: false,
        })
    }
    entries.sort((a, b) => b.value - a.value)
    return entries
}

function collectTeamEntries(server, metric, computeFn) {
    if (!OpenPACServerAPIClass) return null
    let partyManager
    try {
        partyManager = OpenPACServerAPIClass.get(server).getPartyManager()
    } catch (e) {
        console.error('[vpp leaderboard] Open Parties and Claims party manager read failed: ' + e)
        return null
    }
    let cache = getMetricCache(server, metric)
    let teams = partyManager.getAllStream().toArray()
    let results = []
    for (let i = 0; i < teams.length; i++) {
        let team = teams[i]
        let members = team.getMemberInfoStream().toArray() // IPartyMemberAPI[], includes the owner (see header comment)
        let total = 0
        let best = 0
        let bestExtra = null
        let hasData = false
        for (let j = 0; j < members.length; j++) {
            let uuid = members[j].getUUID()
            let onlinePlayer = server.getPlayerList().getPlayer(uuid)
            let value, extra
            if (onlinePlayer) {
                let r = computeFn(onlinePlayer)
                value = r.value
                extra = r.extra
                cacheMetricValue(server, metric, onlinePlayer, value, extra)
                hasData = true
            } else {
                let key = String(uuid)
                if (cache.contains(key, 10)) {
                    let entry = cache.getCompound(key)
                    value = entry.getInt('value')
                    extra = entry.contains('extra') ? entry.getString('extra') : null
                    hasData = true
                } else {
                    value = 0
                    extra = null
                }
            }
            if (metric === 'tier') {
                if (value > best) { best = value; bestExtra = extra }
            } else {
                total += value
            }
        }
        results.push({
            name: team.getDefaultName(), // "<owner>'s Party" - OPAC parties have no settable custom name (see header comment)
            value: metric === 'tier' ? best : total,
            extra: metric === 'tier' ? bestExtra : null,
            memberCount: members.length,
            hasData: hasData,
        })
    }
    results.sort((a, b) => b.value - a.value)
    return results
}

// ---- output ----

function titleCase(s) { return s.charAt(0).toUpperCase() + s.slice(1) }

function sendTop10(player, title, entries, formatLine) {
    player.tell(`--- ${title} (top ${Math.min(10, entries.length)}) ---`)
    if (entries.length === 0) {
        player.tell('No data yet - run this again after players have been online.')
        return
    }
    let top = entries.slice(0, 10)
    for (let i = 0; i < top.length; i++) {
        player.tell(`${i + 1}. ${formatLine(top[i])}`)
    }
}

// ---- command registration ----

ServerEvents.commandRegistry(event => {
    let { commands: Commands } = event

    function metricCommand(name, computeFn, formatPlayerLine, formatTeamLine, unavailableMessage) {
        function levelGuardFails() {
            return name === 'level' && !SkillsAPIClass
        }

        function playersExec(ctx) {
            let player = ctx.source.playerOrException
            if (levelGuardFails()) {
                player.tell(unavailableMessage)
                return 0
            }
            let entries = collectPlayerEntries(player.server, name, computeFn)
            sendTop10(player, `${titleCase(name)} Leaderboard - Players`, entries, formatPlayerLine)
            return entries.length
        }

        function teamsExec(ctx) {
            let player = ctx.source.playerOrException
            if (levelGuardFails()) {
                player.tell(unavailableMessage)
                return 0
            }
            if (!OpenPACServerAPIClass) {
                player.tell('Teams leaderboard unavailable: Open Parties and Claims API (xaero.pac.common.server.api.OpenPACServerAPI) could not be loaded on this server.')
                return 0
            }
            let entries = collectTeamEntries(player.server, name, computeFn)
            if (entries === null) {
                player.tell('Teams leaderboard unavailable: could not read the Open Parties and Claims party manager.')
                return 0
            }
            sendTop10(player, `${titleCase(name)} Leaderboard - Teams`, entries, formatTeamLine)
            return entries.length
        }

        return Commands.literal(name)
            .executes(playersExec)
            .then(Commands.literal('players').executes(playersExec))
            .then(Commands.literal('teams').executes(teamsExec))
    }

    event.register(
        Commands.literal('leaderboard')
            .then(metricCommand(
                'wealth',
                p => ({ value: computeWealth(p), extra: null }),
                e => `${e.name} - ${e.value} spurs${e.online ? '' : ' (last seen)'}`,
                e => `${e.name} (${e.memberCount} member${e.memberCount === 1 ? '' : 's'}) - ${e.value} spurs total`,
                null
            ))
            .then(metricCommand(
                'tier',
                p => { const t = computeTier(p); return { value: t.count, extra: t.highestId } },
                e => `${e.name} - Tier ${e.value} (${niceTierName(e.extra)})${e.online ? '' : ' (last seen)'}`,
                e => `${e.name} (${e.memberCount} member${e.memberCount === 1 ? '' : 's'}) - Tier ${e.value} (${niceTierName(e.extra)})`,
                null
            ))
            .then(metricCommand(
                'level',
                p => ({ value: computeLevel(p), extra: null }),
                e => `${e.name} - Level ${e.value} (summed across ${SKILL_CATEGORIES.length} skill categories)${e.online ? '' : ' (last seen)'}`,
                e => `${e.name} (${e.memberCount} member${e.memberCount === 1 ? '' : 's'}) - Level ${e.value} total`,
                'Level leaderboard unavailable: Pufferfish Skills server API (net.puffish.skillsmod.api.SkillsAPI) could not be loaded on this server.'
            ))
    )
})

// Refresh cached numbers as a player leaves, so their "last seen" ranking
// reflects their final state rather than whatever it was the last time
// someone happened to run /leaderboard.
PlayerEvents.loggedOut(event => {
    let player = event.player
    if (!player || !player.server) return

    try {
        cacheMetricValue(player.server, 'wealth', player, computeWealth(player), null)
    } catch (e) {
        console.error('[vpp leaderboard] logout wealth cache refresh failed for ' + player.username + ': ' + e)
    }

    try {
        let t = computeTier(player)
        cacheMetricValue(player.server, 'tier', player, t.count, t.highestId)
    } catch (e) {
        console.error('[vpp leaderboard] logout tier cache refresh failed for ' + player.username + ': ' + e)
    }

    if (SkillsAPIClass) {
        try {
            cacheMetricValue(player.server, 'level', player, computeLevel(player), null)
        } catch (e) {
            console.error('[vpp leaderboard] logout level cache refresh failed for ' + player.username + ': ' + e)
        }
    }
})
