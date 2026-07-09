# Vanilla++ — Design

A Prism Launcher-compatible Create-centric modpack. See `instructions.md` for
the original requirements this design satisfies, and `pack/manifest.json` /
`pack/mods.lock.json` for the exact, reproducible mod list.

## Stack

- **Minecraft 1.21.1 + NeoForge 21.1.235** — the newest MC version with a
  mature Create ecosystem (Create 6.0.10). Mojang's post-1.21 calver releases
  (26.x) don't have a Create port yet, so 1.21.1 is the practical ceiling.
- **Create 6.0.10** as the progression backbone. Bundles Flywheel, Registrate,
  and Ponder as jar-in-jar — no separate install needed.
- **ProgressiveStages 2.1** as the tier-gating engine (see below). Chosen over
  the unmaintained GameStages (not ported past 1.20) and the newer, unproven
  EpochStages (10 downloads, published weeks ago) — ProgressiveStages has ~5
  months of history, active updates, and native FTB Teams/FTB Quests
  integration we'll lean on in Phases 4 and 6.
- Tooling: no packwiz binary (this environment has no Go toolchain or package
  manager) — `scripts/resolve_mods.py` + `scripts/mods.lock.json` do the same
  job against the Modrinth API, git-friendly and reproducible. See
  `scripts/build_server.py` for turning the lockfile into a runnable server.
- **Tom's Storage 2.3.2** for Tier 1's "dumb storage" (16M+ downloads, no hard
  dependencies) and **Refined Storage 2.0.9** for the real powered network
  from Tier 2 on — named explicitly in `instructions.md` ("think mods like
  refined storage"), 1.4M+ downloads, self-contained. **Create Crafts &
  Additions 1.6.0** (8.6M downloads) bridges the two: its Alternator turns
  Create's own rotational power into Forge Energy to run RS. See the storage
  section for how these three fit together. **KubeJS 2101.7.2 + Rhino** power
  the storage recipe patches here and the full recipe-gating pass in Phase 9.

## The tier ladder

Every other system in this pack (storage caps, RPG skill unlocks, currency,
combat/magic tiers, dimension access, mob difficulty zones) gates against one
of these six tiers. Tiers 0-3 stay entirely inside Create's own material
chain (no addon needed). Tier 4's storage content is fully resolved as of
Phase 2; only its narrative trigger is still a Phase 8 TODO.

**Tier 5 (Starforged Age) is no longer "endgame content, TBD" — it's the
explicit gateway to space.** Per a scope addition after Phase 2 (see
`instructions.md`'s "Resource infinity & space travel" section), space
travel is the modpack's ultimate end goal: once the overworld/Nether/End are
fully progressed, Starforged Age is where you build a rocket, and each
planet beyond it is its own additional tier layered on top (Tier 6, 7, ...),
gated behind the previous planet the same way every earlier tier gates the
next. The ladder isn't fixed at 6 tiers — it extends per planet, designed in
Phase 8. **Stellaris** is the chosen space-travel mod (Ad Astra, the more
famous pick, stalled at MC 1.20.4 and never reached NeoForge 1.21.1); it has
an existing Create-addon compat path via TFMG.

| # | Stage id | Name | Unlocked by | Create milestone | Storage / autocrafting rung | Vanilla tier & dimension also gated here |
|---|---|---|---|---|---|---|
| 0 | `rootborn` | Rootborn | starting stage | — | vanilla inventory/chests only | wood/stone |
| 1 | `andesite_age` | Andesite Age | craft/pick up `create:andesite_alloy` | water wheels, mixing/pressing, crushing wheels | **"dumb storage"** — Tom's Storage: Inventory Connector + Storage Terminal + Open Crate + Cable + Filing Cabinet, iron-tier only, no power, no autocrafting | iron tools/armor, rails |
| 2 | `brass_age` | Brass Age | craft/pick up `create:brass_ingot` | Mechanical Arm, Deployer, Sequenced Gearshift, Elevator Pulley, train control | **real powered network** — Refined Storage in full (Grid/Disk Drive/Controller, 1k+4k capacity), powered by Create Crafts & Additions' Alternator (kinetic→FE); first crafting automation via Create's Mechanical Arm/Deployer feeding RS's Importer/Exporter/External Storage | diamond tools/armor, enchanting table, beacon, **Nether** |
| 3 | `precision_age` | Precision Age | obtain `create:refined_radiance` or `create:shadow_steel` | Sturdy Sheet (Create's own top alloy) | 16k capacity; wireless/network devices (Wireless Grid, Network Receiver/Transmitter, Relay, Portable Grid, Security Manager) | netherite tier, elytra, totem, **The End** |
| 4 | `induction_age` | Induction Age | temp trigger: netherite ingot *(real narrative trigger TBD in Phase 8)* | — | **ceiling of the same system**: 64k capacity + Advanced Processor + native pattern-based autocrafting (Autocrafter/Autocrafter Manager/Pattern/Pattern Grid) | TBD |
| 5 | `starforged_age` | Starforged Age | temp: kill Ender Dragon *(real trigger likely "launch first rocket," TBD in Phase 8)* | — | — | gateway to space (Stellaris); Tier 6+ per-planet tiers extend beyond this, designed in Phase 8 |

Dependency chain is strictly linear (`rootborn -> andesite_age -> brass_age ->
precision_age -> induction_age -> starforged_age -> ...per-planet tiers`);
`linear_progression = true` in `progressivestages.toml` so granting any tier
auto-grants everything below it. This directly satisfies "previous Create
stuff should be necessary for the next tier of stuff."

### Resource infinity (added after Phase 2)

`instructions.md` now asks that all resources eventually become automatable
into effectively infinite supply. Resolved to mean **automated harvesting at
scale** — tireless Create contraptions, chunk-spanning quarries/miners, mob
farms — not true something-from-nothing duplication; the world's internal
logic stays consistent, automation just removes the need to manually gather.
Genuinely unique items (boss trophies, one-off structure/dungeon rewards) are
explicitly exempt and stay one-of-a-kind forever. Which tier this kicks in at
per-resource, and the specific mods/mechanisms used, are a Phase 8/9 design
question (likely spanning Induction Age onward through the space tiers) —
not yet implemented.

### Storage: two mods, not one — "dumb storage" then a real powered network

`instructions.md` draws a real distinction between the earliest tier
("really small limits," no autocrafting) and everything after it, and asks
specifically for something as low-tech as *linking chests together* at the
start. One continuous Refined Storage system stretched across all four tiers
(an earlier draft of this doc) can't express that distinction — RS's own
core devices are diamond/Nether-gated no matter how you slice it, so making
Tier 1 truly "dumb" meant either patching RS down twice or using a second,
genuinely simpler mod for Tier 1 alone. Went with the latter:

- **Tier 1 (Andesite Age) — Tom's Storage** (16M+ downloads, no hard
  dependencies): Inventory Connector links chests into one network, Storage
  Terminal browses it, Open Crate/Filing Cabinet add capacity. This is
  literally "link chests together," matching the ask directly. Its stock
  Inventory Connector recipe needs a diamond + ender pearl and its Storage
  Terminal needs Nether glowstone — both patched down to iron-tier
  substitutes via KubeJS (`pack/kubejs/server_scripts/storage.js`) so this
  tier doesn't secretly require Brass Age or the Nether. No power, no
  autocrafting — genuinely dumb, on purpose.
- **Tier 2 (Brass Age) on — Refined Storage**, the real network (named
  directly in `instructions.md`: "think mods like refined storage where you
  have a central interface"). Unlocked whole at Brass Age using its **stock**
  recipes — no patch needed this time, because Brass Age unlocks diamond (for
  RS's Advanced Processor) and the Nether (for RS's Quartz chain,
  `quartz_enriched_iron/copper`/`silicon`/everything built from them) in the
  same stage that RS itself unlocks. Capacity scales 1k → 4k (Brass) → 16k
  (Precision) → 64k (Induction); crafting automation first becomes possible
  at Brass Age through **Create's own Mechanical Arm/Deployer** feeding RS's
  Importer/Exporter/External Storage/Constructor/Destructor, not RS's own
  autocrafter — that stays locked until Induction Age, so Create remains the
  sole automation process even for storage. Full per-tier item/block lists
  are in `pack/config/ProgressiveStages/{andesite,brass,precision,
  induction}_age.toml`.
- **Powering RS — Create Crafts & Additions** (8.6M downloads), not a
  disabled energy requirement. RS ships a `requireEnergy` config toggle, and
  disabling it was this doc's original call — but Create has no *native* FE
  generation, and the intent behind the tier system is for every later
  system to be reachable "through Create," so a Create-native power bridge is
  the better fit than turning power off. Create Crafts & Additions' Alternator
  (kinetic → FE, recipe cost is pure Andesite-tier ingredients — andesite
  alloy, iron plates/rods, a copper spool from its own Rolling Mill) is
  unlocked at Brass Age alongside RS itself, so the whole "first real network"
  moment is one coherent unlock: automation (Mechanical Arm/Deployer), storage
  (RS), and power (Alternator) all arrive together.
  `refinedstorage-common.toml`'s `requireEnergy` is back to its default
  (`true`).

### RPG skills (Phase 3)

`instructions.md` asks for an RPG leveling system with skill categories
covering movement, gathering, and combat. Built on **Pufferfish's Skills**
(3.29M downloads, the standard skill-tree framework for NeoForge 1.21.1) +
**Pufferfish's Attributes** (2.46M downloads, adds attribute types the base
game lacks — `mining_speed`, `sword_damage`, `sprinting_speed`,
`bow_projectile_speed`, etc). The mod's own official "Default Skill Trees"
content pack was **not** shipped — it only covers two generic categories
(combat, mining), not the six specific ones asked for — so all six are
authored here instead, using the official pack's jar as a schema reference
(its `data/puffish_skills/puffish_skills/categories/<name>/*.json` layout).

- **Generated, not hand-typed.** `scripts/gen_skill_tree.py` emits the whole
  datapack into `pack/kubejs/data/puffish_skills/puffish_skills/`, KubeJS's
  raw-datapack injection folder. Six hand-typed JSON trees (categories,
  experience sources, node definitions, connections) would be tedious and
  error-prone; a generator with small per-category data tables is not. Each
  category is a simple linear ~10-node chain rather than the sprawling
  hex-snowflake layout the official pack uses (that shape is clearly built
  with their web-based visual editor, not something worth hand-authoring
  here).
- **Six categories**: Mining, Swords, Bows, Running, Swimming, Building.
  Mining/Swords/Bows grant XP via `mine_block`/`kill_entity` experience
  sources (ore-tier and weapon-tier XP tables in `gen_skill_tree.py`).
  Running/Swimming grant XP via `increase_stat`, keyed to vanilla's
  `minecraft:custom` stat type (`sprint_one_cm`/`swim_one_cm`). Building has
  **no native experience source** — confirmed by inspecting the mod's
  registered source types, there's no block-placement hook — so it's granted
  from `pack/kubejs/server_scripts/skills.js` on `BlockEvents.placed`,
  throttled per-player.
- **Rewards** are `puffish_attributes`-backed attribute modifiers (e.g. +3%
  Mining Speed, +5% Sprinting Speed, +0.1 Fortune per node), following the
  same per-node-buff pattern as the official pack.

Two real bugs surfaced only through the mod's own datapack validator
(`[puffish_skills] Data pack could not be loaded:` on boot) and both needed
the mod's actual source (`github.com/pufmat/skillsmod`, version-matched
against the shipped `puffish_skills-0.18.0` jar) to resolve correctly —
decompiled bytecode alone led to two wrong guesses in a row on the second one:

1. **Bows**: `kill_entity`'s weapon-match condition used `#c:tools/bows` /
   `#c:tools/crossbows` tags, which don't exist. Fixed to bare item ids
   (`"bow"`, `"crossbow"`), matching the convention already established by
   the mining category's ore matching.
2. **Running/Swimming**: `increase_stat` isn't the special case it looks
   like — it goes through the exact same `LegacyCalculation.parse` +
   `variables`/`experience` pipeline as `mine_block`/`kill_entity`
   (confirmed by reading `IncreaseStatExperienceSource.java` and
   `MineBlockExperienceSource.java` side by side). `amount` must be
   explicitly bound via a `get_increase_amount` operation (it is *not*
   implicitly available, despite what the legacy-compat code paths in the
   decompiled class suggested), and matching the specific stat requires
   chaining `get_stat` into a `puffish_skills:test` operation (registered on
   the STAT type by `StatCondition`, taking a `"stat"` field) — since the
   mod's `awardStat` mixin hook fires for *every* stat increase, not just
   the one each category cares about. The stat identifier format itself
   (`"<statType_ns>.<statType_path>:<stat_ns>.<stat_path>"`, e.g.
   `"minecraft.custom:minecraft.sprint_one_cm"`) was confirmed correct from
   the start via `BuiltinJson#parseStat`.

### Quest system (Phase 4)

`instructions.md` asks for three quest layers: a preset progression track
(team-shared), long-running quests that need exponentially more
interactions per reward, and randomized daily quests (both per-player, not
team-shared). Built on **FTB Quests** (2101.1.27), which brought in three
hard dependencies: **FTB Library**, **FTB Teams**, and **Architectury API**.
Architectury API is on Modrinth as usual; **the whole FTB suite (Library/
Teams/Quests) is CurseForge-exclusive** — confirmed by searching Modrinth,
which returns only third-party *addons* for FTB Quests, never the mod
itself. `scripts/resolve_mods.py` gained a second resolution path for this:
manifest entries with `"source": "curseforge"` plus a manually-pinned
`cf_file_id`/`cf_filename` (there's no CurseForge API key in this sandbox,
so these are looked up by hand off the CurseForge files page) are fetched
directly from CurseForge's public CDN
(`mediafilez.forgecdn.net/files/<id-without-last-3-digits>/<last 3 digits>/
<filename>`, no auth required — confirmed working, it's the same URL a
browser's download button hits) and hashed locally to populate the same
lockfile schema `build_server.py` already reads. No changes needed to
`build_server.py` itself; it never cared which registry a jar came from.

**FTB Teams is a hard dependency of FTB Quests itself**, not something we
chose to add early — FTB Quests won't even load without it. It's installed
now, but `progressivestages.toml` stays `team_mode = "solo"` until Phase 6;
installing the mod and turning on its team-progression semantics are
separate steps. One immediate upside: `ProgressiveStages` ships its own
optional FTB Teams/FTB Quests integration (visible in the boot log even
back in Phase 0's mixin warnings) that's now fully active —
`ProgressiveStagesStageProvider` replaces FTB Library's default stage
backend, so FTB Quests' `gamestage` task type now reads our *actual*
`ProgressiveStages` tiers (`rootborn`/`andesite_age`/`brass_age`/
`precision_age`/`induction_age`/`starforged_age`) directly, with no glue
code needed.

`scripts/gen_quests.py` generates the whole quest book into
`pack/config/ftbquests/quests/`, the same "generate, don't hand-type"
approach as Phase 3's skill trees, and for the same reason — the format has
too many interlocking required fields to author by hand across three
chapters. **Format gotcha worth flagging for future phases**: FTB Quests'
GitHub default branch is mid-rewrite onto a JSON5-based format for a much
newer Minecraft version, and its CHANGELOG documents that migration — but
our installed jar (2101.1.27, MC 1.21.1) predates it and uses the *old*
SNBT/`CompoundTag`-based format (`.snbt` files, real NBT-ish text syntax).
The generator's first draft was written against the default branch, produced
JSON that FTB Quests silently ignored (0 chapters loaded, zero errors —
the `.snbt` file-extension filter just never matched anything), and had to
be rewritten from scratch after cloning `FTBTeam/FTB-Quests` and
`FTBTeam/FTB-Library` at their **`1.21.1/main`** branches specifically and
re-deriving every field from *that* branch's `writeData`/`readData`
methods. Lesson (same one Phase 3 already taught, reinforced harder this
time): ground truth is whatever branch matches the shipped jar's own
version number, never a repo's default branch.

Three chapters originally (one now — see below):

- **Tier Progression** (the preset track): one quest per `ProgressiveStages`
  tier, chained by `dependencies`, each gated by a `gamestage` task on that
  tier's real stage id. Deliberately doesn't *grant* tiers through quest
  completion — `ProgressiveStages`' own triggers still do that — this
  chapter is a quest-book view of tier progress with RPG skill XP (see
  below) and a themed item as a bonus layered on top, avoiding any
  assumption about whether writing back through the just-replaced stage
  provider is even supported.
- ~~Lifetime Achievements~~ and ~~Daily Bounties~~ were originally built as
  two more FTB Quests chapters (four `minecraft:custom`-stat exponential
  chains; ~18 repeatable turn-in/kill-count quests) — **moved out of FTB
  Quests entirely in Phase 6** once real multi-member teams made the open
  issue below unavoidable. See Phase 6's "Team mode + claims" section for
  where they live now (plain KubeJS, inherently per-player) and why. The
  substitution of "blocks broken"/"xp levels gained" with other
  `minecraft:custom` stats (mob kills, play time, animals bred, fish
  caught — `instructions.md`'s own examples are introduced with "e.g. ...
  etc", not a mandated exact list) and the "static pool, not true
  randomization" call for dailies both carried over unchanged into the
  Phase 6 rebuild — those were content/scope decisions independent of
  which system tracks the progress.

RPG skill XP rewards go through a `command` reward type calling
`puffish_skills`' own `/puffish_skills experience add <player> <category>
<amount>` command (`net.puffish.skillsmod.commands.ExperienceCommand`) —
needs `permission_level: 2` since that command requires gamemaster
permission and a reward otherwise runs as the claiming player. (An earlier
draft had the wrong command path entirely — caught and fixed in Phase 5,
see that section.) Currency rewards (the "and/or" half of the
long-running-quest reward requirement) are deferred to Phase 5-and-beyond,
once/wherever the marketplace currency is the more natural fit than XP.

**Open issue found here, resolved in Phase 6**: FTB Quests tracks *all*
progress at the FTB Teams level (`TeamData` — literally named for it), with
no built-in per-quest-type granularity. In solo mode (as of this phase),
each player's own 1-person team made every quest type per-player already,
satisfying `instructions.md`'s split trivially — but once real multi-member
teams exist, daily/long-running quest progress would become team-shared
too. See Phase 6 for how this was actually resolved (moving those two
chapters off FTB Quests, not just accepting the deviation).

### Economy (Phase 5)

`instructions.md` asks for two related but distinct systems: (1) a tracked
currency with a "sell anything to a vendor" outlet, priced intelligently by
tier/difficulty, and (2) an async marketplace where players list items for
other players to buy without both being online at once.

**Currency + vendor: Create: Numismatics** (1M+ downloads, confirmed
NeoForge 1.21.1). Adds six coin *items* (Spur/Bevel/Sprocket/Cog/Crown/Sun,
1/8/16/64/512/4096 spurs respectively) plus Vendor and Creative Vendor
blocks. Chosen for the same reason as prior Create-addon picks — it's
Create-native (its Alternator-style power/kinetic integration fits the
pack's "everything through Create" spine) and its coins being plain items
means granting currency is just `/give`, no separate account API needed.

**Marketplace: Create: Marketplace** (built specifically to bridge
Numismatics — confirmed via its own dependency list: Numismatics and Create
are its only two *required* deps for our version; Xaero's Minimap/World Map
and Create: Tradeworks are optional and were left out). Adds a global board/
hotkey UI to browse and price-compare every player-run Vendor shop from
anywhere, with waypoint navigation to the shop once Xaero's Minimap is
present. **Scope note on "asynchronous remote":** purchase itself still
happens by walking to the seller's persistent Vendor block, not an instant
GUI checkout — the seller doesn't need to be online (the block just holds
its own inventory/price), but the buyer does need to travel there. A true
instant-anywhere alternative (Auction House Plus) exists but was rejected:
its NeoForge support for our version is unconfirmed (flagged as a to-do on
the mod's own page) and it needs a *different* economy-API mod (Impactor or
RealEconomy) as a bridge, which would fragment currency into two
non-interoperating systems unless custom glue code kept them in sync. The
user confirmed the travel-based, Numismatics-native option over that
larger-scope, less-verified alternative (2026-07-09).

**Pricing — reused, not re-derived:** rather than a second difficulty
metric (e.g. recursive crafting-cost analysis across the whole recipe
graph, which would be a much bigger undertaking and would likely just
reconstruct the same tier ordering anyway), `scripts/gen_economy.py` prices
items directly off `pack/config/ProgressiveStages/*.toml`'s own
`[items].locked` lists — the same tier-unlock data Phase 1 already
authored as this pack's difficulty signal. Each tier maps to a spur price
(`rootborn`→1, `andesite_age`→4, `brass_age`→16, `precision_age`→64,
`induction_age`→256, `starforged_age`→1024 — modest fractions of what
reaching that tier actually costs, so selling can't out-earn playing
normally, per `instructions.md`'s "avoid unbalanced exploits" ask); any
item not listed at any tier (the overwhelming majority of registered items —
dirt, food, mob drops, plain vanilla blocks) falls back to the tier-0 price
of 1 spur. This is a deliberate scope call, not an oversight: hand-tuning a
price for every single registered item isn't tractable and isn't what a
small 2-10 player private server needs (per the scope already recorded in
`instructions.md`'s Clarifications); "no limits on the ability to sell
arbitrary items" only requires everything sell for *something*.

**Selling itself is a `/sell` command**, generated into
`pack/kubejs/server_scripts/economy.js` alongside the embedded price table
(one file, so there's no cross-script load-order dependency between a data
file and logic file). Registered via KubeJS's `ServerEvents.commandRegistry`
rather than hooking the Vendor block's own right-click interaction — a
block-hook would've needed a way to distinguish "our admin-configured
universal sell point" from any ordinary player-placed Vendor (which should
keep its normal buy/sell-slot behavior), and solving that cleanly looked
more fragile than a plain command. Sells the player's whole main-hand stack
at its tier price, paying out the largest coin denominations that fit
(minimizing item clutter) via plain `/give`-equivalent `player.give(...)`
calls. Verified via the server console (no in-game client available in this
sandbox — see DESIGN.md's Verification section): `/puffish_skills
experience add @a mining 10` and `/sell` both resolved past command-lookup
(the first hit Brigadier's own "No player was found" for the `@a` selector
with nobody online, the second hit a plain "unexpected error" from
`ctx.source.playerOrException` failing because console isn't a player) —
neither produced "Unknown command," confirming both are registered and
reach their execution logic; a real player would need to actually claim a
quest reward or run `/sell` to exercise the full path end-to-end.

**Bug found and fixed while building this** (in already-committed Phase 4
code, not new work): `gen_quests.py`'s `skill_xp_reward()` had the wrong
command path for granting `puffish_skills` XP — `"skills experience add
..."` — discovered only because writing `economy.js` required re-reading
`pack/kubejs/server_scripts/skills.js`'s already-working
`puffish_skills experience add ...` call for reference and noticing the
mismatch. Root cause: `net.puffish.skillsmod.SkillsMod#onCommandsRegister`
registers `ExperienceCommand` as a *direct sibling* of `SkillsCommand`
under the `puffish_skills` root (`puffish_skills experience add ...`), not
nested under the "skills" subcommand as the name suggests. This would have
silently failed as an unknown command the first time any Phase 4 quest
reward was actually claimed in-game — data-load validation had passed
(FTB Quests doesn't check that a `command` reward's string resolves to a
real command until it's actually run), so this had shipped undetected.
Fixed and regenerated; DESIGN.md/this note exists so a future phase
re-checks any other `command`-reward strings against their mod's *actual*
registered command tree rather than trusting a plausible-looking guess.

### Why gate the Nether at Brass Age and The End at Precision Age

Vanilla lets you rush the Nether/End with almost no preamble. Both dimensions
now get a real reason to exist in the progression, per `instructions.md`'s
"multiple dimensions that lock away better progression" requirement: the
Nether is where RS's Quartz chain comes from, and it unlocks at Brass Age —
where RS itself unlocks, so there's no dead tier where the dimension is open
but nothing needs it yet. The End stays gated behind Precision Age as before.

### Team mode + claims (Phase 6)

`progressivestages.toml`'s `team_mode` is now `"ftb_teams"` (was `"solo"`
since Phase 1) — tier stages, and the Tier Progression FTB Quests chapter
that reads them via `gamestage` tasks, now share across a real FTB Teams
party rather than each player progressing independently. This is a config
flip only; ProgressiveStages' own backend does the actual party-wide stage
sharing (confirmed registered as FTB Library's stage provider since
Phase 4), so FTB Quests' `gamestage` task correctly reflects party progress
by checking any one member — no `team_stage: true` needed on the task
itself. **Not independently verifiable in this sandbox** (no in-game client
to actually form a party and check a second member's view — see the
Verification section).

**Claims: FTB Chunks.** All three of its required dependencies
(Architectury API, FTB Library, FTB Teams) were already installed since
Phase 4, so this reuses the exact same party/team system as the quest
sharing above, rather than introducing a second, parallel claims-specific
party concept (several Modrinth-native alternatives exist — Open Parties
and Claims among them — but they'd mean running two independent
party/team systems side by side for no benefit). Same CurseForge-CDN
resolution path as the rest of the FTB suite (still not on Modrinth).

**Real limitation resolved, not just documented — dailies/milestones moved
out of FTB Quests.** Phase 4 flagged an open issue: FTB Quests tracks *all*
progress at the FTB Teams level (`TeamData`), with no native way to keep
some chapters team-shared and others per-player. Once real multi-member
parties exist (this phase), that stopped being hypothetical — Lifetime
Achievements and Daily Bounties would have become party-shared too,
directly violating `instructions.md`'s "should NOT share daily/long running
quest progress" requirement. Presented with accepting that deviation vs.
rebuilding those two chapters outside FTB Quests, the user chose the
rebuild (2026-07-09). Tier Progression stays in FTB Quests (team-shared, as
intended); the other two moved to plain KubeJS, which is inherently
per-player since nothing routes through FTB Teams at all:

- **Lifetime Achievements** (`scripts/gen_achievements.py` →
  `pack/kubejs/server_scripts/achievements.js`): same four
  `minecraft:custom` stat chains as before, read via KubeJS's own
  `player.stats.getMobKills()`/`getPlayTime()`/`getAnimalsBred()`/
  `getFishCaught()` (confirmed by decompiling
  `dev.latvian.mods.kubejs.player.PlayerStatsJS` in the installed jar — a
  much more pleasant read than the FTB Quests source archaeology prior
  phases needed), checked on a `ServerEvents.tick` every 100 ticks.
  Progress ("how many tiers of this chain has this player already been
  granted") lives in `player.persistentData`, which is a `CompoundTag`
  stored directly on the player entity (confirmed via KubeJS's
  `WithPersistentData` interface) — inherently per-player, survives
  logout/restart, no team/party concept involved anywhere in the path.
- **Daily Bounties** (`scripts/gen_dailies.py` →
  `pack/kubejs/server_scripts/dailies.js`): same bounty pool. Kill bounties
  are tracked passively via `EntityEvents.death`, checking the killer is a
  player and the victim's type matches; item bounties are turned in via a
  new `/turnin` command (consumes the held stack, same
  `ServerEvents.commandRegistry` pattern as Phase 5's `/sell`) since "turn
  in N items" has no natural passive trigger the way a kill does. A
  `/dailies` command reports status. The 24h cooldown uses `Date.now()`
  (real wall-clock time) in `player.persistentData`, matching FTB Quests'
  own real-world `repeat_cooldown` semantics, not tick count.

Both scripts boot-verified with zero KubeJS errors (5/5 server scripts
loaded), and `/turnin`/`/dailies` both confirmed registered via the same
console-command trick used for `/sell` in Phase 5 (fail only on "console
isn't a player," never "Unknown command"). **What's not verified**: actual
kill-detection and stat-threshold-crossing end to end, since that needs a
live client actually killing a mob or racking up stats, which this sandbox
has no way to do — flagging honestly rather than claiming full coverage.

### Blacksmithing (Tier 1+)

`instructions.md` asks that metal tools go through "some kind of
blacksmithing" instead of a flat crafting-table recipe. Tier 1 currently just
unlocks vanilla iron tools outright as a placeholder — the recipe swap itself
is deferred to Phase 7 (combat variety), since the tool-crafting mechanic and
weapon-class balance are tightly coupled. Candidates found so far: **Silent
Gear** (modular tool assembly, confirmed on NeoForge 1.21.1) and **Fire and
Flames** ("a Blacksmith's Dream" — crucible processing + custom tool
crafting, also confirmed on NeoForge 1.21.1). Tetra, the classic pick, is not
ported past 1.20.x and is ruled out.

## Phase plan

0. ✅ Bootstrap tooling, Create + NeoForge, confirm server boots.
1. ✅ This tier ladder, implemented via ProgressiveStages config
   (`pack/config/ProgressiveStages/*.toml`).
2. ✅ Tiered storage progression: "dumb storage" (Tom's Storage) at Tier 1,
   real powered network (Refined Storage + Create Crafts & Additions) from
   Tier 2 on, capacity scaling every tier after, autocrafting unlocked at
   Brass Age via Create's own Mechanical Arm/Deployer, full native network
   autocrafting by Induction Age.
3. ✅ RPG skill/leveling system (Running/Swimming/Mining/Building/Swords/Bows)
   via Pufferfish's Skills + Attributes, six generated skill-tree categories.
4. ✅ Quest system via FTB Quests: preset tier-progression track + four
   long-running exponential stat chains + a static daily bounty pool
   (per-player already, since team_mode is still solo).
5. ✅ Economy via Create: Numismatics (tiered `/sell` pricing generated from
   ProgressiveStages tiers) + Create: Marketplace (global shop board).
6. ✅ Teams (`team_mode` flipped to `ftb_teams`) + chunk claims via FTB
   Chunks. Lifetime Achievements/Daily Bounties rebuilt outside FTB Quests
   as plain KubeJS (per-player by construction) once real parties made
   Phase 4's open FTB Quests team-sharing issue unavoidable.
7. Combat variety (balanced weapon classes tied to RPG skills) + blacksmithing
   recipe swap + mage/summoner archetype.
8. Mob scaling by zone + visual power indicator + dungeons/bosses with unique
   drops + structure density/reward scaling + Starforged Age as the space
   gateway (Stellaris, Create-addon compat via TFMG) with per-planet tiers
   extending the ladder beyond Tier 5 + resource-infinity automation
   (harvesting at scale, not duplication; unique boss/structure drops exempt).
9. Full KubeJS recipe-gating pass (E2E-style) across the whole mod list +
   server performance tuning + final Prism/.mrpack + Linux server packaging.

## Verification

`scripts/build_server.py` downloads/verifies every mod jar by hash and syncs
`pack/config`, `pack/kubejs`, `pack/defaultconfigs` into `server/`. Boot with:

```
cd server && java @user_jvm_args.txt @libraries/net/neoforged/neoforge/21.1.235/unix_args.txt nogui
```

`/progressivestages validate` (in-console) checks all stage files for syntax
errors and dependency issues; `/stage tree` prints the resolved dependency
graph.
