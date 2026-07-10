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

**Tier 5 (Starforged Age) is the explicit gateway to space, and Tiers 6-9
now extend the ladder through the solar system (finalized in Phase 8).**
Per a scope addition after Phase 2 (see `instructions.md`'s "Resource
infinity & space travel" section), space travel is the modpack's ultimate
end goal: once the overworld/Nether/End are fully progressed (triggered by
the Ender Dragon kill), Starforged Age is where you build a rocket, and
each planet beyond it is its own additional tier layered on top, gated
behind the previous planet the same way every earlier tier gates the next.
**Stellaris** is the chosen space-travel mod (Ad Astra, the more famous
pick, stalled at MC 1.20.4 and never reached NeoForge 1.21.1); it has a
confirmed Create-addon compat path via **TFMG** (Create: The Factory Must
Grow), via a third `tfmg-stellaris-compat` mod. That compat mod pins
`create-tfmg` to version 1.1.1, not the latest 1.2.0 — its own dependency
range is `[1.1.0, 1.2.0)` and it hasn't been updated for TFMG's newest
release yet (found via the actual boot error, not Modrinth's dependency
metadata — `scripts/resolve_mods.py` gained a `pin_version` manifest field
for exactly this situation). **Known non-fatal issue**: the compat mod's
own loot-table modifier references `stellaris:heavy_ingot`, which doesn't
exist in our resolved Stellaris version — logs a `WARN` on boot
("Could not decode GlobalLootModifier... Unknown registry key") but
doesn't block loading; a version-mismatch between the two mods' own
release cadences, not something in our control.

| # | Stage id | Name | Unlocked by | Create milestone | Storage / autocrafting rung | Vanilla tier & dimension also gated here |
|---|---|---|---|---|---|---|
| 0 | `rootborn` | Rootborn | starting stage | — | vanilla inventory/chests only | wood/stone |
| 1 | `andesite_age` | Andesite Age | craft/pick up `create:andesite_alloy` | water wheels, mixing/pressing, crushing wheels | **"dumb storage"** — Tom's Storage: Inventory Connector + Storage Terminal + Open Crate + Cable + Filing Cabinet, iron-tier only, no power, no autocrafting | iron tools/armor, rails, Epic Fight's iron-tier weapons, Ars Nouveau's wand |
| 2 | `brass_age` | Brass Age | craft/pick up `create:brass_ingot` | Mechanical Arm, Deployer, Sequenced Gearshift, Elevator Pulley, train control | **real powered network** — Refined Storage in full (Grid/Disk Drive/Controller, 1k+4k capacity), powered by Create Crafts & Additions' Alternator (kinetic→FE); first crafting automation via Create's Mechanical Arm/Deployer feeding RS's Importer/Exporter/External Storage | diamond tools/armor, enchanting table, beacon, **Nether**, Epic Fight's diamond-tier weapons |
| 3 | `precision_age` | Precision Age | obtain `create:refined_radiance` or `create:shadow_steel` | Sturdy Sheet (Create's own top alloy) | 16k capacity; wireless/network devices (Wireless Grid, Network Receiver/Transmitter, Relay, Portable Grid, Security Manager) | netherite tier, elytra, totem, **The End**, Epic Fight's netherite-tier weapons |
| 4 | `induction_age` | Induction Age | temp trigger: netherite ingot *(real narrative trigger still TBD — not resolved in Phase 8, out of that phase's actual scope; revisit in Phase 9's recipe-gating pass)* | — | **ceiling of the same system**: 64k capacity + Advanced Processor + native pattern-based autocrafting (Autocrafter/Autocrafter Manager/Pattern/Pattern Grid) | TBD |
| 5 | `starforged_age` | Starforged Age | kill the Ender Dragon | — | — | gateway to space: locks Stellaris' rocket items/blocks until reached |
| 6 | `lunar_frontier` | Lunar Frontier | reach `stellaris:earth_orbit` (i.e. launch a rocket) | — | — | locks the Moon (`stellaris:moon`) |
| 7 | `martian_frontier` | Martian Frontier | reach the Moon | — | — | locks Mars + its orbit station |
| 8 | `inner_system` | Inner System | reach Mars | — | — | locks Venus + Mercury + their orbit stations (grouped — no clear natural ordering between two comparably-hostile planets) |
| 9 | `jovian_frontier` | Jovian Frontier | reach Venus *or* Mercury | — | — | locks Jupiter, the current end of Stellaris' explorable system |

Dependency chain is strictly linear (`rootborn -> andesite_age -> brass_age ->
precision_age -> induction_age -> starforged_age -> lunar_frontier ->
martian_frontier -> inner_system -> jovian_frontier`); `linear_progression =
true` in `progressivestages.toml` so granting any tier auto-grants
everything below it. This directly satisfies "previous Create stuff should
be necessary for the next tier of stuff." **Not independently verifiable in
this sandbox**: actually flying a rocket to each planet and confirming the
dimension-entry triggers fire as designed needs a live client — boot-tested
only that the tier files parse cleanly (stage count went 6 → 10, tier-tagged
item count 139 → 143, exactly matching the new locked items added).

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

### Combat variety + blacksmithing + magic (Phase 7)

`instructions.md` asks for three related systems here: blacksmithing instead
of flat tool recipes, a variety of roughly-equal weapon classes that hook
into the RPG leveling system, and a magic system covering mage/summoner as
combat archetypes. Three mods, chosen after Silent Gear/Fire and Flames were
short-listed for blacksmithing back in Phase 0 (Fire and Flames was
ultimately passed over — tiny download count, Silent Gear is the
overwhelmingly more mature/battle-tested pick and Tetra, the classic
choice, isn't ported past 1.20.x):

- **Silent Gear** (401k downloads) for blacksmithing: a genuinely multi-step
  process (Stone Anvil → craft parts from a blueprint/template + material →
  assemble at a Gear Workbench), not a single recipe — confirmed via its
  own wiki, not assumed. The flat vanilla iron tool recipes (pickaxe/sword/
  axe/shovel/hoe) are removed via `pack/kubejs/server_scripts/
  blacksmithing.js`, forcing players through Silent Gear instead. Scoped to
  iron only, not diamond/netherite or armor — converting every metal tier
  would mean verifying Silent Gear's higher-tier materials are equivalently
  balanced, which is more scope than this phase needs; those stay on
  vanilla recipes (still tier-gated as before).
- **Epic Fight** (3.3M downloads) for weapon variety: adds five new weapon
  types (dagger/greatsword/longsword/spear/tachi, each at wood/stone/iron/
  gold/diamond/netherite material tiers, confirmed via the mod's own
  bundled recipes) with distinct movesets/skills, plus a stamina system —
  a single well-established mod rather than stacking a separate
  weapon-variety mod (e.g. Spartan Weaponry) with a separate skill/animation
  mod. **The RPG-leveling hook needed zero extra work**: Epic Fight's own
  `data/minecraft/tags/item/swords.json` puts every one of its weapons
  (all 32, including a bonus uchigatana) directly in the vanilla
  `#minecraft:swords` tag, which Phase 3's Swords skill category already
  keys its `kill_entity` trigger on — confirmed by extracting the jar, not
  assumed. New weapons are tier-gated to match their material: iron-tier
  locked in `andesite_age.toml` (alongside vanilla iron gear),
  diamond-tier in `brass_age.toml`, netherite-tier in `precision_age.toml`
  — matching wherever this pack's own tier ladder already locks that
  vanilla material (diamond in `brass_age.toml`, netherite in
  `precision_age.toml` — see "The tier ladder" section above for the full
  mapping). On balance ("make sure options are equally
  effective, as close as possible"): no manual per-weapon stat tuning was
  done — Epic Fight's whole premise is balanced weapon classes with
  different playstyles, so its own defaults are trusted rather than
  second-guessed without combat-testing infrastructure this sandbox
  doesn't have (no in-game client — see Verification).
- **Ars Nouveau** (3.17M downloads) for the magic system: spell-crafting
  covers the mage archetype directly; summon rituals (Summon Guardians,
  Summon Wilden) and combat-capable familiars cover summoner. Both
  archetypes share **one** new RPG skill category (`magic`, added to
  `scripts/gen_skill_tree.py` alongside Phase 3's six) rather than two
  separate categories — `instructions.md` only asks that mage/summoner
  exist as *a* combat archetype, not that they track separately. Its XP
  source is a `kill_entity` check for holding `ars_nouveau:wand`, the same
  mechanism Swords/Bows already use, though it's an approximation (a spell
  can land its killing blow after the wand's left the player's hand, e.g.
  a delayed AOE) rather than an exact "killed via magic" signal — no
  cleaner native hook was found without deeper Ars Nouveau internals than
  this phase's budget covered. Reward attributes are Ars Nouveau's *own*
  perk attributes (`ars_nouveau:ars_nouveau.perk.{spell_damage,max_mana,
  mana_regen,warding}` — confirmed by decompiling
  `com.hollingsworth.arsnouveau.api.perk.PerkAttributes`, since
  `puffish_attributes` predates Ars Nouveau being in the pack and has
  nothing magic-specific). Ars Nouveau brought two undeclared dependencies
  neither Modrinth's own metadata nor the mod page mentioned as required —
  **GeckoLib** and **Curios** — only surfaced by reading the actual
  `ModLoadingException` from a real boot attempt; both resolve fine on
  Modrinth. The wand + its Enchanting Apparatus/Arcane Pedestal are
  tier-locked to Andesite Age as a light touch on top of gating that
  already exists in practice (the recipe needs gold + Source Gems, and
  finding archwood/sourcestone to build the apparatus is itself a real
  exploration gate).

**Structural note on "encourage the player to stick with one weapon
class"**: this falls out of the existing design rather than needing new
work — each weapon type's kills feed a *specific* skill category (Swords,
Bows, or now Magic), so a player who commits to one weapon class
accumulates that category's buffs, naturally reinforcing specialization.

### Mob scaling + dungeons/bosses + structures + space travel + resource-infinity (Phase 8)

The largest remaining phase, bundling five requirements from
`instructions.md`. Mods added: **Apotheosis** (+ its required chain —
Placebo, Patchouli, Apothic Attributes/Spawners/Enchanting) for mob
scaling and boss loot; **YUNG's Better Dungeons** (+ YUNG's API) for
dungeons; **Dungeons and Taverns** for structure variety; **Create: TFMG +
Stellaris + their compat mod** for space travel (see "The tier ladder"
section above for the full space-travel writeup — kept there since it's
fundamentally a tier-ladder extension).

- **Mob scaling — two independent layers, not one.** Apotheosis' Apothic
  Invaders (dramatic spawn: light beam + sound) and Elites (spawn silently
  in place of normal mobs) give a real, visually-distinct "this mob is
  tougher" signal with scaled loot (gems, affix items) — but its own
  in-game documentation says these spawn "randomly in place of their
  normal counterparts," i.e. flat chance, not zone-scaled. That leaves
  `instructions.md`'s actual zone/dimension/player-progression scaling
  requirement unaddressed by the mod alone, so
  `pack/kubejs/server_scripts/mob_scaling.js` adds a second, independent
  layer on top of vanilla mob attributes (deliberately *not* hooking into
  Apotheosis' own internal spawn-chance system, which would be far more
  fragile to integrate with reliably): on `EntityEvents.spawned`, a
  difficulty multiplier is computed from dimension (Nether 1.5x, End 2x),
  distance from world spawn (+15% per 500 blocks, capped at 2.5x), and the
  nearest player's own `ProgressiveStages` tier count (+10% per tier
  reached, via `player.stages.has(id)` — KubeJS's own generic game-stages
  binding, which `ProgressiveStages` plugs into; confirmed by decompiling
  `KubeJSStagesCompat$ProgressiveStagesBridge`, not guessed) — directly
  satisfying "the player causing these mobs to spawn should also influence
  their base difficulty based on their level/progression." Above a small
  threshold, the mob's `generic.max_health`/`generic.attack_damage` are
  scaled via `modifyAttribute(..., 'multiply_base')` and it gets a
  star-rating custom name (color-coded gray→dark_red) as the "look at it
  and tell" indicator — a nametag rather than a fancier visual (glow
  outline/particles) since that's what's reliably implementable via
  KubeJS scripting without client-side rendering work. `EntityEvents.death`
  grants bonus Numismatics currency proportional to how far above baseline
  the killed mob's difficulty was, covering "rewards scale with difficulty."
  **Verification gap, disclosed**: this only exercises at actual mob-spawn
  time, which the headless boot-test sandbox can't trigger (no player
  present) — confirmed only that the script loads without syntax errors
  (7/7 KubeJS scripts, 0 errors), not that the runtime logic behaves as
  designed. Several API calls here were corrected mid-implementation after
  decompiling KubeJS's actual class files rather than trusting a first
  guess (e.g. `entity.getAttribute(id).setBaseValue(...)` doesn't exist —
  the real API is `entity.modifyAttribute(attributeId, modifierId, amount,
  operation)`) — same "verify against the installed jar" discipline this
  whole project has needed repeatedly.
- **Dungeons + bosses with unique drops**: YUNG's Better Dungeons overhauls
  vanilla's dungeon structure into larger multi-room layouts (the "some
  sort of dungeons" ask). Apotheosis separately ships its own
  `boss_dungeon`/`boss_dungeon_2` generated structures with dedicated boss
  loot tables (gems + `apotheosis:sigil_of_malice`, confirmed by reading
  the bundled loot table JSON) — Apotheosis' affix/gem system is itself
  how "unique weapons" manifest here (randomized name/rarity/stat
  combinations on socketed gear), rather than a bespoke per-boss unique
  weapon list built from scratch. No custom loot-table work was added on
  top of what these two mods already ship.
- **Structures**: Dungeons and Taverns overhauls loot/variety across most
  vanilla structures (villages, mansions, strongholds, etc.) — no
  dependencies, zero-risk addition. `instructions.md`'s specific asks
  ("rewards scale with discovery probability," "important structures
  spawn at a minimum rate") are the kind of fine-grained per-structure
  tuning that would need real playtesting to get right and weren't
  custom-tuned this phase — relying on Dungeons and Taverns' own defaults
  rather than guessing at numbers with no way to verify structure spawn
  rates in this sandbox.
- **Resource infinity**: no new mod added here — per the scope already
  resolved after Phase 2 ("automated harvesting at scale... not true
  something-from-nothing duplication"), this is satisfied by Create's own
  existing toolkit: movable Contraptions carrying multiple Mechanical
  Drills (the standard community "Create quarry" pattern) for
  chunk-spanning ore/stone automation, Mechanical Saws for automated tree
  farms, and animal breeding pens for food/leather at scale — all already
  available at the tiers established in Phases 0-2. Deliberately *not*
  adding a dedicated quarry mod (e.g. one of the many "Quarry+"-style
  mods): `instructions.md` separately requires "engaging with Create
  should be the sole process by which you automate things," and a
  bolted-on quarry mod would cut against that more directly than it would
  help.

### Recipe-gating audit, performance, and packaging (Phase 9)

`instructions.md` asks for three things here: as much recipe-gating as
possible for guided progression, server performance as "a major concern,"
and a Prism-importable/Linux-server-runnable final output.

**Recipe-gating audit — spot-checked, not exhaustive, and disclosed as
such.** Tier-gating has been applied incrementally and deliberately to each
mod's clearest power-tier-defining items as they were added across Phases
1-8 (iron/diamond/netherite tool and weapon tiers, storage capacity rungs,
Ars Nouveau's wand+apparatus, Stellaris' rocket components and each
planet's dimension). A fully exhaustive item-by-item audit across all 40
installed mods' complete item lists was not attempted — that's a large
amount of ground (Silent Gear alone reports 132 materials/48 parts/75
traits at boot) and, without a live client to actually playtest the
resulting balance, more static auditing risks producing plausible-looking
gates that don't actually reflect real play patterns. Flagging honestly
rather than claiming false completeness: if deeper coverage turns out to
matter (e.g. whether Silent Gear's material tiers or Apotheosis' gem tiers
have an early-game exploit path around the vanilla-ore gates already in
place), that's a good candidate for a future audit pass with real
playtesting, not something resolved by more static analysis alone.

**Server performance.** Added **ModernFix** (startup/memory/loading time),
**FerriteCore** (heap usage), **C2ME** (concurrent chunk
management — server-only: a heavily-modded worldgen stack is exactly where
chunk loading dominates server cost), **Krypton Reno** (network stack —
server-only), and **Noisiumed** (worldgen noise performance, complements
C2ME's parallelism rather than duplicating it). All five resolve with zero
required dependencies and boot-verified clean (client-only mixin warnings
for optional Sodium/VulkanMod/Starlight compat hooks that correctly no-op
on a dedicated server, not real errors).

Beyond mods, `pack/user_jvm_args.txt` and `pack/server.properties` are new
tracked source files, synced into `server/` by `build_server.py` alongside
`config`/`kubejs`/`defaultconfigs` — this matters because `server/` itself
is gitignored/regenerated, so hand-tuning those files directly there (as a
first pass here initially did, then had to be corrected) would silently
evaporate on the next fresh build elsewhere. Contents:
- **JVM args**: [Aikar's flags](https://docs.papermc.io/paper/aikars-flags),
  the standard, widely-used G1GC tuning preset — a safe, well-established
  choice over untested custom tuning, at a 6GB default heap sized for this
  pack's scope (30+ mods including Create and several large content mods).
- **server.properties**: `view-distance`/`simulation-distance` 10→8 (real
  perf/experience tradeoff, judged reasonable for an exploration-focused
  pack); `max-tick-time` 60000→`-1` (disables the watchdog — standard
  modded-server practice, since heavily modded packs routinely have long
  single-tick stalls, e.g. at world/chunk-gen time, that the watchdog would
  otherwise kill unnecessarily); `sync-chunk-writes` true→`false` (real
  I/O-throughput/crash-safety tradeoff — worth flagging to whoever runs
  this that regular backups matter more with it off); `difficulty`
  easy→`normal` (easy mutes hunger/mob damage, undermining the whole
  combat/RPG system this pack is built around); `allow-flight` false→`true`
  (avoids false-kicking players for using legitimate modded flight/
  low-gravity movement — Stellaris' planets, Ars Nouveau rituals, etc. —
  a reasonable relaxation given the small-private-group scope already
  established, not appropriate for a public server).

**Packaging.** `scripts/build_mrpack.py` builds a Prism Launcher-importable
`.mrpack` (Modrinth's pack format) directly from `pack/mods.lock.json` —
`modrinth.index.json` at the zip root (mod list with direct download URLs +
hashes, reusing exactly what `mods.lock.json` already stores, including for
the CurseForge-sourced mods — a `.mrpack` just needs *a* working URL per
mod, not specifically a Modrinth one) plus an `overrides/` folder with
`config`/`kubejs`/`defaultconfigs`. `server.properties`/`user_jvm_args.txt`
are deliberately left out of the `.mrpack` — meaningless for a Prism
client instance, already covered separately by `build_server.py` for the
Linux server side. Validated by re-opening the built zip and checking
`modrinth.index.json` parses with the expected mod count/hashes/per-side
`env` flags (server-only mods like C2ME correctly marked
`"client": "unsupported"`). The Linux server side was already the thing
being boot-tested throughout every phase of this project — `server/` (via
`build_server.py`) *is* the runnable Linux server package, so nothing new
was needed there beyond the performance tuning above.

### Gear overhaul: unified smithing/boss-drop progression + expanded melee variety (post-Phase 9)

After all 9 original phases shipped, a follow-up request tightened the
combat/gearing system specifically: every weapon, tool, and armor piece
should come from exactly two sources — Silent Gear's smithing process, or a
boss drop — with all other native gear-crafting paths removed, the melee
category expanded well beyond "Swords," and every tier upgrade offering
something for every playstyle. Implemented as 5 boot-tested parts:

**Part 1 — mods + Silent Gear material foundation.** Added **Allthemodium**
(+ its **ATO - All the Ores** companion) as the material source for
Tiers 4-9 space-and-beyond progression, per explicit direction to lean on a
late-game "meta material" mod rather than inventing bespoke materials.
7 new Silent Gear materials generated by `scripts/gen_gear_materials.py`
into `pack/kubejs/data/silentgear/silentgear_materials/`, stats
extrapolated from Silent Gear's own iron→netherite growth curve, one per
tier from Andesite Alloy (Tier 1) through a custom "Star Alloy" (Tier 7,
Allthemodium's `unobtainium_vibranium_alloy_ingot`). Silent Gear's material
schema requires a `part_substitutes` key even when empty — omitting it
crashes the whole server (`MaterialJsonException`), caught on the first
boot test. A second bug (material count off by one) turned out to be a key
collision: an unprefixed `"brass"` material key silently overwrote Silent
Gear's own built-in `brass.json` — fixed by prefixing all 7 generated keys
with `vpp_`.

**Part 2 — redirect native gear crafting through Silent Gear.**
`pack/kubejs/server_scripts/blacksmithing.js` expanded from Phase 7's
iron-tools-only scope to remove **every** vanilla tool/sword/bow/crossbow/
armor recipe across all material tiers, all netherite smithing-upgrade
recipes, and Allthemodium's own native gear recipes. One recipe-count
discrepancy (55 removed instead of 88) traced to Allthemodium's recipe ids
including a `smithing/` subfolder segment the removal calls were missing.

**Part 3 — Epic Fight weapon-type integration + melee skill split.**
Epic Fight's 5 custom weapon types (dagger/greatsword/longsword/spear/
tachi) only natively go up to its own netherite ceiling; `scripts/
gen_weapon_tiers.py` extends each type across the 4 new post-netherite
tiers (Allthemodium/Vibranium/Unobtainium/Star Alloy) — 20 new KubeJS-
registered items with matching `epicfight:capabilities/weapons/*.json`
files, added to the shared `#minecraft:swords` tag (tags merge across
datapacks, unlike Part 1's material-file collision). Epic Fight's own 30
tiered crafting-table recipes are removed and replaced with one consistent
smithing-adjacent recipe per (type × all 10 tiers): a Silent-Gear-crafted
`silentgear:sword_blade` part (any material — going through Silent Gear's
own process is what satisfies "the same smithing route") plus that tier's
raw material (already tier-locked) plus a stick. The single "Swords" skill
category (Phase 3) is split into 6 — swords/daggers/greatswords/
longswords/spears/tachi — each keyed on its own `vanillaplusplus:<type>s`
tag spanning all 10 tiers, with distinct but comparable attribute rewards
(e.g. spears grant bonus `minecraft:player.entity_interaction_range`
reach, greatswords grant knockback + max health, tachi grants attack speed
+ luck) so each weapon type is a genuinely differentiated, comparably
powerful playstyle rather than a re-skinned sword. A real bug surfaced
here: capability files were first written to `data/epicfight/capabilities/
weapons/`, but Epic Fight's `ItemCapabilityReloadListener` resolves the
target item's namespace from the *data folder* a capability file lives
under (confirmed by decompiling the class — it builds the lookup
`ResourceLocation` from the folder's namespace, not anything inside the
JSON), so all 20 items were silently missing their capability
(`epicfight:star_alloy_tachi` doesn't exist; `vanillaplusplus:star_alloy_
tachi` does). Fixed by moving the files to `data/vanillaplusplus/
capabilities/weapons/`, matching the items' real namespace.

**Part 4 — Ars Nouveau mage armor through Silent Gear smithing.** Ars
Nouveau's 3 robe recipes (Sorcerer's Wrap/Arcanist's Robes/Battlemage's
Gambeson, one chestplate-slot item per set) are redirected off vanilla
gold/iron/diamond chestplate reagents onto a Silent Gear chestplate (any
material) via `pack/kubejs/server_scripts/ars_nouveau_armor.js`. Since each
robe resolves to a fixed vanilla `ArmorMaterial` regardless of the reagent
used (confirmed by decompiling `EnchantingApparatusRecipe` —
`keepNbtOfReagent` only carries over components, not which material tier
was used), requiring a *specific* material tier as reagent wouldn't add
any real gate over requiring any Silent Gear chestplate. Comparable-
difficulty gating is instead enforced the same way every other item in
this pack is gated: locking each robe item directly in ProgressiveStages —
Sorcerer's Wrap (lowest defense, most Thread slots) at Andesite Age
(Tier 1, alongside the wand itself), Arcanist's Robes (mid) at Precision
Age (Tier 3), Battlemage's Gambeson (highest defense, fewest Thread slots)
at Starforged Age (Tier 5) — preserving the set's original low-to-high
defense ordering while spreading them across the ladder.

**Part 5 — boss unique weapons.** 3 new loot-only items, unobtainable via
any smithing route, generated alongside Part 3's tier ladder in the same
`gen_weapon_tiers.py` (kept as one script since both parts share the same
`vanillaplusplus:` item namespace/capability folder/tag files — two
scripts independently regenerating the same tag files would fight each
other on re-runs): **Duskfang** (dagger, Sharpness III + Looting II) added
as a new weighted entry in Apotheosis' `boss_drops.json` and
`rare_boss_drops.json` alongside their existing gem/sigil drops (original
content preserved exactly, confirmed by decompiling the jar); **Withering
Maul** (greatsword, Sharpness IV + Fire Aspect II) from the Wither; and
**Starfall Tachi** (tachi, Sharpness V + Looting III, exceeding even the
Star Alloy tier's own stat ceiling) from the Ender Dragon. Vanilla's own
`wither.json`/`ender_dragon.json` loot tables are empty by default — the
Nether Star and dragon egg/XP drops are hardcoded in each entity's Java
class, bypassing the loot table entirely (confirmed via decompiling the
vanilla data jar) — so overriding these files with a real pool is purely
additive. Enchantments are applied via each loot entry's `minecraft:
set_enchantments` function (writes the component directly), which needs no
enchantability-tag membership on the item itself.

**Disclosed limitation**: as with Phase 7's original combat variety work,
actual combat-feel balance across the now-6 melee categories plus mage
plus 3 boss uniques can't be playtested in this sandbox (no live client —
see Verification). The design goal (comparable percentage-based reward
curves per skill category, monotonic stat scaling per tier, boss uniques
strictly above the craftable ceiling) is verifiable statically via boot
tests and decompiled source, but "equally effective in real combat"
fundamentally needs a live client to confirm.

### Utility overhaul: tool tier-gating fix, Paxel, gear traits, building wand, backpacks (post-gear-overhaul)

A follow-up to the combat/gearing overhaul above, applying the same rigor
to utility equipment: pickaxes/axes/shovels/hoes following the tier
ladder, a combined Paxel, additional gear utility (auto-smelting, AoE
mining), a gating audit, and three new tiered utility items (a building
wand, a general backpack, and a separate voidable "Miner's Pouch"). Six
boot-tested parts:

**Part 1 — fix tool tier-gating (a real, previously undiscovered bug).**
Every one of our 7 Silent Gear materials' `harvest_tier.
incorrect_blocks_for_tool` pointed at a `vanillaplusplus:incorrect_for_
<name>_tools` tag that was never created - it resolved to empty, meaning
tools of ANY of our tiers could mine every block in the game regardless of
tier, silently, since Silent Gear's material schema doesn't error on a
missing tag reference. Found by decompiling Silent Gear's own iron/diamond
materials and noticing they point to Silent Gear's own tags, which are
themselves thin wrappers around vanilla's real hierarchy (e.g.
`silentgear:incorrect_for_iron_tools` is literally `["#minecraft:
incorrect_for_iron_tool"]`). Fixed by plugging our 7 tags into the
existing vanilla/NeoForge/Allthemodium tag chain rather than enumerating
any blocks ourselves: NeoForge itself patches `minecraft:
incorrect_for_diamond_tool` to include `#neoforge:needs_netherite_tool`,
and Allthemodium patches `minecraft:incorrect_for_netherite_tool` with its
own vibranium/unobtainium/alloy exclusions while separately shipping
ready-made `c:incorrect_for_allthemodium_tool` / `..._vibranium_tool` /
`..._unobtainium_tool` tags that are each exactly "everything from the
next tier up." `scripts/gen_gear_materials.py` now generates these tags
alongside the materials themselves.

**Part 2 — Paxel, discovered to already exist natively.** Initial research
(checking KubeJS's own item-builder API and third-party "paxel" mods) found
no way to build a genuine combined pickaxe+axe+shovel without either an
unsupported feature (KubeJS GitHub issue #474, still open) or risky raw
Java interop. A hand-rolled version was built and boot-verified working
(via `Java.loadClass` + vanilla's `Tier.createToolProperties(TagKey)`,
fixing two real Rhino bugs along the way - bare `{ }` blocks don't give
real `const`/`let` scoping, and consecutive `(() => {...})()` IIFEs need
explicit trailing semicolons or ASI silently chains them into one broken
call). But further inspection of the *actually installed* Silent Gear
version (4.2.1.1) revealed it already ships a native Paxel gear type
(`GearPaxelItem`, its own blueprint/template/parts pipeline) - missed by
the original gear overhaul's research since that phase was combat-focused
and had no reason to check for a mining-tool gear type. It works with all
7 of our materials automatically (their `gear_type_blacklist` is empty)
and inherits tier-gating for free from Part 1's fix and the existing raw-
material ProgressiveStages locks. The hand-rolled version was discarded
entirely in favor of the native one. Its recipe (blueprint + 5 material
parts, like every other gear type) doesn't literally "combine 3 existing
tools" as first asked, but goes through the exact same smithing route as
everything else and costs noticeably more material than a single tool (5
parts vs. 3 for a plain pickaxe) - a disclosed adjustment instructions.md
explicitly allows.

**Part 3 — gear utility traits.** Silent Gear ships a rich, data-driven
trait system already used for material flavor (e.g. iron's "malleable").
Added a `"traits"` list to each material, scaling by tier: `reach` (+block/
entity interaction range, T1-2 and T7), `magnetic` (auto-pickup, T2+),
`widen` (mining AoE, T3+), `fortunate` (built-in Fortune, T4+), `magmatic`
(auto-smelts mined ore, T5+) - all confirmed real, working traits by
reading their JSON + doc comments in the jar. `multi_break` (vein-miner
style) is a documented no-op stub in the jar itself ("This trait has never
been coded") and was deliberately not used. No new mod or item needed -
applies automatically to every tool/weapon/armor piece made from that
material.

**Part 4 — gating audit.** Spot-checked (disclosed non-exhaustive, same
convention as Phase 9) for utility bypasses outside our system: Create's
Extendo Grip is already transitively gated by its own `create:brass_ingot`
requirement (Brass Age); Allthemodium has no remaining loose utility items
(magnets, jetpacks, etc.) beyond what gear overhaul Part 2 already
stripped. No changes needed.

**Part 5 — Building Wand.** Adds **Building Wands** (+ required Cloth
Config; Architectury API already installed since Phase 4) for directional/
row-column/fill/box/circle/grid block placement plus a Palette pattern
system. Ships 5 tiers (stone/copper/iron/diamond/netherite) as a hardcoded
Java enum with no material registry to extend past netherite - same
disclosed ceiling Epic Fight had before the combat overhaul's Part 3
bespoke extension, not worth replicating for a secondary utility item -
plus a 3-tier Magic Bag block-source item. All 8 items locked via
ProgressiveStages (stone_wand free from rootborn; copper/iron/magic_bag_1
→ andesite_age; diamond/magic_bag_2 → brass_age; netherite/magic_bag_3 →
precision_age).

**Part 6 — backpacks + Miner's Pouch.** Adds **Sophisticated Backpacks** (+
required Sophisticated Core) for the general expandable-inventory ask.
Same native-ceiling situation as the wand (6 tiers: leather/copper/iron/
gold/diamond/netherite), gated the same way (leather free from rootborn
through netherite → precision_age). The separate "Miner's Pouch" - a
voidable bulk per-item-type storage, since Dank Null doesn't exist for
1.21.1 (confirmed directly: not present in any 1.21.1 build of Cyclic, the
mod that contains it) - isn't a new item but any backpack fitted with
Sophisticated Backpacks' own Void + Filter + Stack Upgrade items, gated as
an independent progression line: Stack Upgrade (starter/1/2/3/4/omega,
×1.5 up to ×33,554,431 stacks per slot) follows the same copper→iron→gold→
diamond→netherite chain as the backpacks, with Omega Tier (crafted from 9x
Tier 4, no raw ingredient of its own) reserved as `jovian_frontier`'s
capstone reward - the final tier's payoff for the whole line. Filter/Void
Upgrades (plus their Advanced variants) are gated similarly across
andesite_age through precision_age.

**Disclosed limitation**: as with the combat overhaul, actual in-game feel
(mining speed/correctness for the Paxel and traits, wand/backpack utility)
can't be playtested in this sandbox (no live client). Boot tests confirm
scripts execute and objects construct without error, and stat curves are
disclosed as simple monotonic formulas, but real gameplay feel needs a
live client to confirm.

### Travel overhaul: boats -> trains -> aircraft -> teleportation (post-utility-overhaul)

The pack had no travel progression at all - just walking, never-gated
vanilla boats, and Stellaris' rockets (already the Tier 5+ interplanetary
gateway, unrelated to intra-world travel). The user asked for an arc: foot
-> increasingly capable vehicles as tiers advance -> teleportation,
explicitly gated late. Three boot-tested parts. Parts 1 and 3 need no
KubeJS at all - every lock in them is a plain ProgressiveStages item lock,
either explicit (nothing in vanilla/the new mods naturally gates these
items) or added alongside an existing transitive ingredient lock for
consistency with this pack's established double-locking convention. Part 2
was later revised (see below) to use KubeJS recipe patches instead.

**Part 1 - boats + Create Trains.** Boats (9 wood variants + bamboo raft,
plus chest variants) locked until `andesite_age` (Tier 1) - the first
vehicle upgrade past walking. Create's own Trains - confirmed already
installed via Create 6.0.10's own `com/simibubi/create/content/trains/...`
classes, no new mod needed - locked until `brass_age` (Tier 2), realizing
that tier's own "train control" milestone description which was previously
just flavor text with nothing enforcing it. Track Station/Signal/Railway
Casing are already naturally gated by `create:brass_casing` (Brass Age's
own material); Track, Cart Assembler, Gantry Carriage, and Minecart
Coupling are all craftable from Tier 1 materials on their own, but are
locked here too so the entire train experience is a single Brass Age
package rather than something partially assemblable a tier early.

**Part 2 - Immersive Aircraft (planes/airships), later replaced by Create
Aeronautics.** Originally shipped with **Immersive Aircraft**: 6 vehicles
(biplane/gyrodyne/quadrocopter -> `brass_age`; airship/cargo_airship ->
`precision_age`; warship -> `induction_age`), all explicit locks since none
of the 6 are naturally gated by any tier-locked ingredient. **Create
Aeronautics** was considered and rejected at the time because reading that
release's jar showed **zero recipe files** - it looked like a build-your-
own-ship-from-special-blocks system, harder to tier-gate than a plain
crafted item, and needed two more dependencies (Sable + itself) for a
redundant capability.

**Revision (user request, post-launch):** the user asked to swap air travel
to Create Aeronautics specifically, and to gate its components through
recipe ingredients rather than direct ProgressiveStages locks. Re-reading
the *current* 1.3.0 jar (ground truth over the stale earlier finding, per
this project's own standing rule) showed the "zero recipe files" note was
true of an older release only - 1.3.0's bundled jar (jarjar-embeds Offroad
and Simulated, both irrelevant here beyond satisfying Aeronautics' own
dependency) ships a full `data/aeronautics/recipe/` tree. Immersive
Aircraft removed entirely (mod, lockfile entry, all 3 explicit locks); Sable
added as a real separate dependency (confirmed required via the jar's own
`neoforge.mods.toml`, version range `[2.0.0,3.0.0)`, satisfied by Sable
2.0.3).

Gating is now implicit, reusing materials this pack already tier-locks
elsewhere, instead of new explicit item locks - implemented in
`pack/kubejs/server_scripts/travel.js`:
- **Brass Age**: `aeronautics:propeller_bearing` already requires
  `create:brass_casing` in its native recipe - already naturally gated, no
  patch needed. `aeronautics:adjustable_burner` patched to add
  `create:brass_sheet` into its one open recipe slot, so burner/balloon
  flight opens on the same tier as propeller-driven flight.
- **Precision Age**: `aeronautics:gyroscopic_propeller_bearing` and
  `aeronautics:smart_propeller` both need `simulated:gyroscopic_mechanism`
  (a sequenced-assembly item from Brass-tier materials only) - patched to
  swap in `create:sturdy_sheet` so the self-leveling/steerable upgrade
  needs Precision Age. `aeronautics:levitite_blend` (the mod's antigravity
  fluid, `create:mixing`) needs crushed `minecraft:end_stone` in its native
  recipe - untouched, since the only practical source is the End itself,
  already locked until this tier.
- **Induction Age**: `aeronautics:steam_vent` (the passive/industrial heat
  source, vs. the Brass Age burner's manual redstone-toggled one) patched
  to add `allthemodium:allthemodium_ingot` - this pack's existing top
  material, reused rather than inventing a new one - as the ceiling right
  before the Tier 5 space gateway.

Boot-tested clean after the swap: `travel.js` loads with 0 errors/0
warnings, Sable's physics pipelines initialize for every dimension
(including Allthemodium's), and no recipe-id conflicts or load errors
appear anywhere in the log.

**Part 3 - Waystones (teleportation).** The standard, most mature choice
(20.6M downloads, requires the **Balm** library) for the explicit
"teleportation, gated later" ask. Locked at `induction_age` (Tier 4) - the
automation ceiling immediately before the Tier 5 space gateway, so
intra-world teleportation is the last travel upgrade before interplanetary
rockets take over. Every recipe uses only vanilla materials (ender pearl,
amethyst shard, emerald, obsidian, stone bricks) with nothing naturally
tier-locked in this pack, so gating is entirely explicit: `warp_stone`,
all 6 waystone variants (default/mossy/sandy/blackstone/deepslate/
end_stone), and the 3 scroll items (warp/return/portal). `warp_stone` is
itself an ingredient in the waystone block's own recipe, so locking it
alone already blocks crafting a waystone transitively - both are still
locked explicitly anyway.

**Disclosed limitation**: as with every other overhaul, actual in-game
feel (does an Aeronautics contraption actually fly well, does a waystone
teleport correctly, does a train run smoothly) can't be verified in this
sandbox - only that the mods load cleanly and the intended
items/ingredients are tier-gated, confirmed via boot-test stage-tag counts
(Parts 1/3) or clean KubeJS/recipe reload logs (Part 2's revision).

### World exploration overhaul: biome variety + structure variety + reward scaling (post-travel-overhaul)

Phase 8 covered dungeons (YUNG's Better Dungeons) and generic structure
loot variety (Dungeons and Taverns) but explicitly punted on two of
`instructions.md`'s specific asks: "the world must be varied in content
and biomes" (no biome mod had ever been added - Dungeons and Taverns only
touches loot/layout, not terrain) and "structures should have rewards that
scale with their probability of being discovered" / "important structures
should spawn at a minimum rate" (both flagged in Phase 8's own DESIGN.md
notes as real gaps, deferred for lack of a concrete design at the time).
This overhaul closes both, plus adds a second wave of structure-variety
mods on top of Phase 8's. Three parts, all boot-tested together.

**Part 1 - biome and structure variety mods.** 12 new mods:
- **Terralith** (+ **TerraBlender**, its cross-mod biome-region API, +
  **Lithostitched**, a hard dependency not listed in Modrinth's own
  metadata for our version - found only via the actual boot error, `Mod
  terralith requires lithostitched 1.7.7 or above`, same "ground truth
  over assumption" pattern this project keeps running into). ~100 new
  overworld biomes plus several of its own structures, built entirely from
  **vanilla blocks** - deliberately chosen over Biomes O'Plenty (which
  ships hundreds of new blocks/items) specifically so `gen_economy.py`
  needs zero new pricing work: anything not in a tier file already falls
  back to the tier-0 price, which is exactly correct for plain vanilla
  blocks. Boot log confirms Terralith registers as the base `minecraft:
  overworld`/`minecraft:nether` TerraBlender regions (replacing vanilla's
  own default terrain, not layering beside it), with Ars Nouveau's
  existing region still composing fine alongside it at index 1.
- **When Dungeons Arise** and **Structory**: new jigsaw structures spread
  across many biomes (desert/ice/jungle/mushroom/sky/swamp/savanna
  dungeons, small atmospheric lore sites), pure structure-count variety,
  no hard dependencies.
- **8 more YUNG's "Better X" mods** (Mineshafts, Strongholds, Desert
  Temples, Jungle Temples, Nether Fortresses, Witch Huts, Ocean Monuments,
  End Island) alongside Phase 8's existing Better Dungeons - same author,
  same `yungs-api` dependency (already installed), overhauling nearly
  every remaining vanilla structure type into larger, more varied,
  biome-themed layouts. `yungs-better-ocean-monuments` (not "-temples") and
  `yungs-better-abandoned-villages` (doesn't exist as a mod - villages
  aren't in this family) were the two real 404s hit while resolving the
  slug list against Modrinth's search API rather than guessing at names.

**Part 2 - reward scaling by structure rarity.** `scripts/
gen_structure_loot.py` (generated, not hand-typed - same philosophy as
`gen_skill_tree.py`/`gen_economy.py`) buckets 55 vanilla chest-type loot
tables into four tiers by real danger/vanilla spacing (Common: mineshafts,
desert/jungle temples, igloos, ruined portals, pillager outposts, simple
dungeons, all 14 village-house tables; Uncommon: Nether fortress/bastion
chests, shipwrecks, underwater ruins, buried treasure, most trial-chamber
rooms; Rare: bastion treasure rooms, all 3 stronghold tables, ancient city
+ its ice box, trial-chamber reward vaults; Epic: End City treasure, the
woodland mansion, and the trial chamber's unique-reward tables) and
appends one extra guaranteed-roll loot pool per table, scaled per tier,
on top of the full vanilla pools (copied byte-for-byte from the actual
installed vanilla data jar at generation time - NeoForge/KubeJS datapack
loading has no merge semantics, a `pack/kubejs/data/...` override fully
replaces the target loot table id, so preserving the original loot means
copying it, not just adding a pool onto a stub).

Bonus-pool contents are drawn from this pack's own progression signals
rather than invented flavor items, so exploration rewards double as a real
progression accelerant: Numismatics currency scaled tier-for-tier with
`gen_economy.py`'s own coin denominations, and the tier ladder's own
unlock-trigger materials (`create:brass_ingot` in Uncommon,
`create:refined_radiance`/`shadow_steel` in Rare, `allthemodium:
allthemodium_ingot` in Epic) - picking one of these up from a chest
legitimately advances a player's stage, the same "craft/pick up" trigger
the tier ladder table already documents elsewhere, so a lucky find in a
dangerous structure can genuinely fast-track progression. Rare and Epic
tiers also add `apotheosis:random_gem` entries restricted to a rising
`purities` floor (`["normal","flawless"]` Rare, `["flawless","perfect"]`
Epic) - the loot-entry type, its `purities` field, and Purity's six
serialized names (`cracked`/`chipped`/`flawed`/`normal`/`flawless`/
`perfect`) were confirmed by decompiling `GemLootPoolEntry.class` and
`Purity.class` in the installed Apotheosis jar rather than guessed; the
`quality` field already used in this pack's existing `apotheosis/
loot_table/entity/*.json` overrides (Phase 7's boss uniques) turned out to
be a different, vanilla-standard field entirely (a weight-vs-luck-
attribute interaction), not a rarity floor - worth flagging since it would
have been an easy mix-up. Silent Gear separately runtime-injects a few
items into 5 of these same tables (`ruined_portal`, `bastion_bridge`,
`bastion_treasure`, `nether_bridge`, `bastion_other`) via its own
`GlobalLootModifier` mechanism, confirmed composing cleanly with the
full-replace datapack override underneath it (both visible in the same
clean boot log, no conflict - two different injection mechanisms, not a
collision).

**Part 3 - minimum spawn-rate guarantees for progression-critical
structures.** `instructions.md`: "important structure for progression
should spawn at a minimum rate to ensure there is one over X blocks."
Scoped to the three structures directly named as tier-gate items in the
tier ladder table rather than re-tuning all 19 vanilla `structure_set`
files speculatively: **stronghold** (the only route to the End - the
single most important progression bottleneck in the game), **woodland
mansion** (source of totems of undying, the Precision Age gate item), and
**end city** (source of elytra, also a Precision Age gate item). Overrides
in `pack/kubejs/data/minecraft/worldgen/structure_set/`:
- `strongholds.json`: concentric-rings `distance` 32->20, `spread` 3->2
  (vanilla's own values extracted from the installed data jar, not
  guessed) - shrinks the first-ring search radius roughly in half.
- `woodland_mansions.json`: random-spread `spacing` 80->40, `separation`
  20->12 - vanilla's spacing (~1280 chunks average) was the rarest
  structure in the game by a wide margin; still special at half that, but
  actually findable in a normal exploration session on a small private
  server.
- `end_cities.json`: `spacing` 20->16, `separation` 8->8 (kept - the
  original 11 exceeded the new spacing and vanilla requires
  `separation < spacing`) - a modest tighten since the End's outer islands
  were already reasonably dense.

All three only affect chunks generated *after* this change - the existing
boot-test `server/world/` (gitignored, disposable) keeps whatever it
already generated near spawn under the old values, which is expected and
not a concern for a dev-only test world.

**Boot-tested clean** after fixing the Lithostitched dependency gap: all
12 new mods load, 0 KubeJS script errors, and none of the 55 generated
loot tables or 3 structure_set overrides produced a parse/load error.
Two pre-existing, disclosed-elsewhere issues appeared in the same log and
are **not** from this phase: the `c:tools/bow` family of missing tag
references (same underlying gap Phase 3's Bows skill-tree fix already
worked around) and `tfmg_stellaris_compat`'s known `stellaris:heavy_ingot`
loot-modifier warning (Phase 8). **Two new, non-fatal issues surfaced and
are disclosed rather than silently accepted**: When Dungeons Arise ships 2
broken advancement JSONs (`dungeons_arise:find_thornborn_towers`,
`find_fishing_hut` - fail to load with a "couldn't load advancements"
error but don't block server start, an upstream mod bug outside this
pack's control) and YUNG's Better End Island logs an `ERROR`-level `key
missing: bei_ExtraDragonFight` on a fresh world's dragon-fight NBT (also
non-fatal - the server continues past it to `Done`).

**Disclosed limitation**: as with every other overhaul, this sandbox has
no live client, so the actual in-game feel of ~100 new biomes, the new
structures' jigsaw layouts, and whether the tightened stronghold/mansion/
end-city spacing "feels right" for a 2-10 player server can't be
playtested here - only that every mod loads cleanly, the generated loot
table JSON is well-formed and additive over vanilla's own pools, and the
structure_set overrides use vanilla's own real placement values as a
baseline (not invented numbers).

### Ore veins via Create Ore Excavation (TODO.md item 1)

First item off the post-launch TODO backlog (`TODO.md`, brainstormed and
scoped with the user in a planning-only session before this autonomous
work resumed). Ask: a simpler, Create-native way to generate ore-type
resources than manually-placed vanilla scatter + a player-built drill
Contraption (the only mechanism Phase 8's "resource infinity" section
ever established).

**Mod choice, verified not guessed.** The user's leading guess was
"Create: Ore Excavation." Modrinth search turned up two candidates:
`create-ore-excavation` ("Extract resources using machines powered by
Rotational Force") and a different mod, plain `ore-excavation` ("mine
whole veins... in one go" - a vein-miner-style *tool* mod, not a worldgen
mod). Decompiling the first jar's `data/createoreexcavation/` confirmed it
matches the ask precisely: a self-contained, fully data-driven ore-vein
placement system (`createoreexcavation:vein` recipes with their own
`placement.spacing/separation`, `biomeWhitelist`, and richness range,
independent of vanilla ore generation) paired with Create-rotational-
power-driven `createoreexcavation:drilling` recipes that extract from a
vein. Only hard dependency is Create itself (already installed); JEI and
CC:Tweaked integrations are optional and were left uninstalled.

**The mod's own native tool ladder already matches this pack's
convention exactly - reused, not reinvented.** `createoreexcavation:drill`
(Iron Drill) -> `diamond_drill` -> `netherite_drill` is a fixed 3-rung
Iron/Diamond/Netherite ladder, mirroring the exact tier-to-vanilla-
material mapping already used pack-wide (iron tools at Andesite Age,
diamond tools at Brass Age, netherite tier at Precision Age). Explicit
ProgressiveStages locks were added following each tier file's own
established convention (add an explicit lock even where a natural
ingredient-based gate already exists, for consistency - see the Wands/
Sophisticated Backpacks precedent in `precision_age.toml`):
- `andesite_age.toml`: `createoreexcavation:drill` + `vein_finder` (the
  entry-level vein-hunting kit) - neither is naturally gated by its own
  ingredients (plain iron; amethyst/ender_eye/redstone ore/a wooden rod),
  so both needed an explicit lock, not just a consistency one.
- `brass_age.toml`: `diamond_drill` + `vein_atlas` (diamond isn't
  independently tier-locked in this pack, so this needed an explicit lock
  too, not just consistency).
- `precision_age.toml`: `netherite_drill` (naturally gated already via
  its smithing recipe's `netherite_ingot` addition, already locked at
  this tier) plus the three industrial-scale machines - `drilling_machine`,
  `sample_drill`, `extractor` - which all share `create:sturdy_sheet` in
  their `create:mechanical_crafting` recipe (this tier's own Create
  milestone material), also already naturally gated. All five got the
  same "explicit lock anyway" treatment.

**Three new vein types added for the late-game meta-material tier**
(`pack/kubejs/data/createoreexcavation/recipe/ore_vein_type/` +
`.../recipe/drilling/`, following the same raw-datapack-injection pattern
established for structure loot/loot tables): `allthemodium`, `vibranium`,
`unobtainium`, outputting `allthemodium:raw_allthemodium`/`raw_vibranium`/
`raw_unobtainium` (item ids and translation keys confirmed from the
installed Allthemodium jar's own lang file, not guessed). Placement
rarity increases across the three (spacing 600/800/1000, separation
32/48/64, richness multiplier tapering 1.5-0.6 / 1.0-0.4 / 0.8-0.3),
loosely bracketing vanilla's own iron (spacing 128) vs. netherite
(spacing 512) as reference points. Each vein's `drilling` recipe requires
`createoreexcavation:netherite_drill` specifically (an explicit `item`
match, not the mod's own generic `createoreexcavation:drills` tag that
iron/zinc/etc. use) with rising Stress/tick cost (1024/1200 ->
2048/1800 -> 4096/2400) - so extracting these veins is impossible until
Precision Age, when the Netherite Drill itself unlocks, on top of the
pre-existing ingot-level lock on `allthemodium:allthemodium_ingot`
(Induction Age) already preventing early smelting even if a raw ore were
somehow obtained first.

**How this answers the "richer veins farther out / player-tier scaling"
part of the ask, honestly.** The TODO item asked for vein rarity to tie
into the same dimension/distance/player-tier scaling `mob_scaling.js` and
the structure loot tiers use. Checked and disclosed: `createoreexcavation`
exposes no player-position-aware runtime hook (its `placement` block is a
static, world-gen-time `spacing`/`separation` pair, evaluated once per
region like vanilla's own `random_spread` structure placement - there's
no equivalent of `EntityEvents.spawned`'s live distance-to-spawn check
available for a vein). The substitute actually implemented is tool-
gating, not runtime scaling: since drilling a vein requires the matching-
tier drill item, and that item is ProgressiveStages-locked, a player
mechanically cannot exploit a rarer vein before reaching the matching
tier, regardless of where in the world it generated. This achieves the
same practical outcome (rarer materials require more progression to
reach) through the mechanism the mod actually offers, rather than forcing
a scaling formula the mod has no hook for.

**Boot-tested clean**: mod loads (`Create Ore Excavation 1.6.8`), 0 KubeJS
script errors (10/10 server scripts, 2/2 startup scripts), no parse
errors for any of the 6 new recipe JSON files, and `ProgressiveStages`
still resolves cleanly (`StageFileLoader`: 10 stage definitions,
`StageTagRegistry`: 213 total tier-tagged items, up from the pre-change
count by exactly the 8 new locked ids added this pass). One incidental
finding, not acted on this pass: the mod ships its own KubeJS plugin
(`Found plugin source createoreexcavation` in the boot log) - unexplored,
flagged as a candidate for a future pass if a runtime scaling hook turns
out to exist there after all.

**Disclosed limitation**: as with every other overhaul, this sandbox has
no live client - whether the new veins actually generate findable/minable
deposits in a real explored world, and whether the rarity curve feels
right, can't be verified here, only that the recipe schema is well-formed
and the tier-gating chain is correctly wired.

### Post-Tier-4 endgame automation deepening (TODO.md item 2)

Second TODO backlog item. Ask: Tiers 5-9 (Starforged Age through Jovian
Frontier) were pure travel gates with zero automation progression -
confirmed by re-reading `tier6_lunar_frontier.toml` through
`tier9_jovian_frontier.toml` before starting: only item/dimension locks,
no "Create milestone"-equivalent, and TFMG (Create: The Factory Must
Grow, installed since Phase 8 purely as a Stellaris compat dependency)
had never had a single one of its own items referenced anywhere in this
pack. The user wants Tier 4+ to become the pack's real automation
endgame, leaning on TFMG, with the Refined Storage capacity chase
continuing upward and three "infinite" capstones (storage/energy/all-
resources) as the true final reward.

**TFMG milestone ladder - a curated subset, not an exhaustive audit,
disclosed as such** (same "spot-checked" precedent Phase 9's recipe-
gating audit already established for this pack - TFMG's own lang file has
~800 entries, auditing all of them wasn't attempted). Decompiled the
installed jar's lang file to pick one real material + a small set of
signature machine blocks per tier, mirroring how Tiers 0-4's own "Create
milestone" column names a handful of things, not every item:

| Tier | Name | TFMG milestone | Key locked ids |
|---|---|---|---|
| 5 Starforged Age | Aluminum Age | basic smelting/framing | `aluminum_ingot`, `bauxite`, `aluminum_frame`, `air_intake` |
| 6 Lunar Frontier | Steel Age | the mod's core metallurgy chain | `steel_ingot`, `blast_furnace_hatch`, `coke_oven`, `casting_basin`, `blast_stove` |
| 7 Martian Frontier | Petrochemical Age | oil refining | `crude_oil_bucket`, `diesel_bucket`, `cast_iron_chemical_vat`, `fireclay` |
| 8 Inner System | Electrical Age | TFMG's own power grid (a distinct energy type from Create's kinetic/FE, bridged via its own Converter block) | `electric_motor`, `accumulator`, `converter`, `copper_cable_hub` |
| 9 Jovian Frontier | Combustion Age | engine parts, the ladder's ceiling | `engine_cylinder`, `diesel_engine_cylinder`, `engine_controller`, `engine_gearbox` |

Every id was confirmed to exist in the installed jar's lang file before
being written into a `.toml` - none guessed from the mod's general
reputation.

**Storage chase - verified, then honestly scoped down.** Decompiled
Refined Storage 2.0.9's lang file expecting to find capacity tiers above
64k to continue the existing 1k->4k->16k->64k pattern; confirmed **no
such native tier exists** - RS's own storage block/disk ladder stops at
64k, and the only thing beyond it is a `creative_storage_block`/
`creative_storage_disk` pair (and fluid equivalents) with **no survival
crafting recipe at all** - genuinely infinite capacity, shipped by RS's
own developers, gated only by being creative-menu-only by default. Rather
than inventing a fictitious "256k"/"1M" intermediate tier (which would
need a custom item with its own Java-level capacity resolution RS
doesn't expose to a KubeJS-only patch), the honest design actually
implemented: the storage chase has no new intermediate rungs across
Tiers 5-8 (64k stays the practical ceiling through that whole span), and
the real payoff is unlocking survival access to RS's own already-built
infinite-capacity block as part of the Jovian Frontier capstone set
below. Disclosed as a real scope-down from the TODO's original ask, not
silently dropped.

**The three "infinite" capstones - real infinite behavior, not a KubeJS
approximation.** The TODO flagged the exact mechanism as open ("does this
need new KubeJS scripting for a custom infinite FE-generation block").
Investigated both Create and Refined Storage's own registries first
rather than assuming custom logic was needed, and found all three already
exist, fully implemented, in mods already installed:
- **Infinite storage** -> `refinedstorage:creative_storage_block` +
  `creative_fluid_storage_block` (confirmed: "Stores an infinite amount
  of items"/"buckets" per RS's own lang file).
- **Infinite energy** -> `create:creative_motor` - Create's own
  "compact, configurable source of Rotational Force" (per Create's
  ponder tooltip text), chosen over TFMG's own `creative_generator`
  specifically because it's Create-native, consistent with this pack's
  standing "engaging with Create should be the sole process by which you
  automate things" rule, and bridges to FE via the Alternator already
  installed since Phase 2.
- **Infinite all-resources** -> `create:creative_crate` - "provides an
  endless supply of the item specified" per Create's own tooltip, a
  direct, literal match for the ask.

None of the four had a survival crafting recipe (confirmed by grepping
each jar for `recipe.*creative` - zero hits in Create, TFMG, or Refined
Storage). New `create:mechanical_crafting` recipes were added for all
four (`pack/kubejs/data/refinedstorage/recipe/creative_storage_block.json`
+ `creative_fluid_storage_block.json`, `pack/kubejs/data/create/recipe/
creative_motor.json` + `creative_crate.json`), each requiring a mix of
this tier's own capstone material (`allthemodium:
unobtainium_vibranium_alloy_ingot`), the matching Tier 8 TFMG milestone
item (electric motor for the energy capstone, chemical vat for the
resource capstone), `create:precision_mechanism`/`brass_casing`/
`electron_tube`, and (for the two storage capstones) the previous 64k/
4096B storage block being consumed as an ingredient - so building the
final tier genuinely requires having climbed the whole ladder first, not
just holding the raw materials. All four gated behind `jovian_frontier`
(the final tier) via ProgressiveStages block locks. No per-player/team
restriction was built in, per the user's explicit call - whoever crafts
one owns it, same as every other block in the game.

**Disclosed exploit risk, not resolved this pass**: `create:creative_crate`
lets a player configure which single item it endlessly supplies. Nothing
technical stops a player from filtering it to a genuinely unique item
(a boss-unique weapon, a one-off structure reward) and duplicating that
specific item type indefinitely - which would directly violate this
pack's own resource-infinity exemption ("genuinely unique items... stay
one-of-a-kind forever," established after Phase 2 and reaffirmed in this
very TODO item's own decision record). Preventing this would need a
KubeJS event hook intercepting the crate's filter-configuration action
(not confirmed to exist/be exposed for this block) or a Java-level fix
outside KubeJS's reach - flagged honestly as an unresolved gap rather
than either ignored or half-fixed with an unverified workaround.

**Boot-tested clean**: all TFMG milestone locks (23 new locked ids across
5 tier files) load without a TOML parse error, `ProgressiveStages`
resolves cleanly (10 stages, 219 tier-tagged items - up by exactly 6 new
[items]-section entries, [blocks]-section entries tracked separately from
this particular counter), and all 4 new capstone recipes load with no
"unknown recipe"/parse warnings tied to their ids (the handful of
`unknown type: minecraft:empty` warnings present in the log are
pre-existing, from Stellaris/TFMG/Silent Gear's own bundled recipes, not
from anything added this pass).

**Disclosed limitation**: as with every prior overhaul, no live client
means the actual feel of a 5-tier TFMG grind, whether the curated
milestone item lists are the *right* representative picks out of TFMG's
~800 total entries, and whether the capstone recipes are correctly
balanced as "the hardest thing in the game" can't be verified here - only
that every id is real, every lock loads, and every new recipe resolves.

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
7. ✅ Combat variety via Epic Fight (weapon classes auto-hook into the
   existing Swords skill category via its own `#minecraft:swords` tag) +
   blacksmithing via Silent Gear (vanilla iron tool recipes removed) +
   mage/summoner via Ars Nouveau (new Magic skill category).
8. ✅ Mob scaling (Apotheosis Elites/Invaders + custom zone/progression-based
   KubeJS scaling) + dungeons (YUNG's Better Dungeons) + boss drops
   (Apotheosis affix/gem loot) + structures (Dungeons and Taverns) +
   Starforged Age as the space gateway (Stellaris + Create: TFMG) with
   Tiers 6-9 extending the ladder per-planet + resource-infinity via
   Create's own contraption-based automation (no new mod needed).
9. ✅ Recipe-gating audit (spot-checked, disclosed as non-exhaustive) +
   server performance (ModernFix/FerriteCore/C2ME/Krypton/Noisiumed +
   Aikar's flags + tuned server.properties) + `scripts/build_mrpack.py`
   for a Prism-importable `.mrpack` + the already-proven `server/` Linux
   server package.

## Verification

`scripts/build_server.py` downloads/verifies every mod jar by hash and syncs
`pack/config`, `pack/kubejs`, `pack/defaultconfigs` into `server/`. Boot with:

```
cd server && java @user_jvm_args.txt @libraries/net/neoforged/neoforge/21.1.235/unix_args.txt nogui
```

`/progressivestages validate` (in-console) checks all stage files for syntax
errors and dependency issues; `/stage tree` prints the resolved dependency
graph.

`scripts/build_mrpack.py` builds `vanilla-plus-plus.mrpack` (gitignored,
regenerate on demand) directly from `pack/mods.lock.json` — importable into
Prism Launcher for a client instance.
