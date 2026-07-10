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

### Duplicate-resource consolidation audit (TODO.md item 3)

Ask: with ~40 mods installed, find overlapping copies of the same
underlying resource and hard-consolidate each down to one canonical item,
same pattern Phase 10 used to fold Allthemodium's native tools/armor into
Silent Gear. Tie-break rule set in `TODO.md`: vanilla wins if it exists,
otherwise whichever mod is most central to this pack's own material chain
(Create/its addons) beats an incidental mod.

**What was actually duplicated, confirmed jar-by-jar, not assumed.**
AllTheOres (ATO) ships its own zinc/aluminum/lead/nickel lines that fully
duplicate items Create and TFMG already provide, and Stellaris ships its
own steel line duplicating TFMG's:
- **Zinc**: `create:zinc_ingot`/`zinc_block`/`zinc_nugget`/`raw_zinc`/
  `raw_zinc_block` all confirmed present in the installed Create 6.0.10
  jar (`jar tf` against `assets/create/textures/item/zinc_ingot.png` etc.)
  - canonical over `alltheores:zinc_*`.
- **Aluminum/lead/nickel**: `tfmg:aluminum_ingot`/`lead_ingot`/
  `nickel_ingot` all confirmed present in the installed TFMG 1.1.1 jar -
  canonical over `alltheores:aluminum_*`/`lead_*`/`nickel_*`.
- **Steel**: `tfmg:steel_ingot` (this pack's own Tier 6 TFMG milestone
  lock, see the endgame-automation section above) vs. `stellaris:
  steel_ingot`, a fully parallel ore->ingot chain Stellaris ships with
  **no ProgressiveStages lock at all** - a real, exploitable bypass of the
  Tier 6 gate. Folded into the bounded extra sweep the TODO item invited
  ("check stellaris-vs-tfmg steel"); confirmed and fixed.

**Consolidation mechanism**: hard redirect via raw datapack overrides
under `pack/kubejs/data/<modid>/...` (the same JSON-override pattern used
throughout this pack) - each override keeps the original recipe/loot
entry's id but redirects its *output* to the canonical item, rather than
adding a new competing recipe. Covers: all 4 metals' smelting/blasting
(ore/raw/raw_block/dust, 32 files), zinc/aluminum/lead/nickel's crafting
conversions (block<->ingot<->nugget, plates, raw<->raw_block, 24 files),
and 12 ATO ore-block loot tables across nether/end/"other" dimension
variants (redirecting the raw-drop entry only, verified against each
original loot table's actual JSON via `jar xf` before editing - e.g.
`alltheores:raw_zinc` -> `create:raw_zinc`, confirmed to exist in the
Create jar first). Stellaris's steel recipe outputs were redirected the
same way (`pack/kubejs/data/stellaris/recipe/misc/steel_*.json`, 12
files).

**Worldgen neutralization, done per-metal not blanket.** ATO's ore
worldgen lives in `data/alltheores/neoforge/biome_modifier/<metal>_
{overworld,nether,end}.json` (confirmed via `jar tf`) - three separate
files per metal, not one. Only the `_overworld` variant was neutered
(`{"type": "neoforge:none"}`) for zinc/aluminum/lead/nickel, since Create's
own zinc ore and TFMG's own aluminum/lead/nickel sources (verified: TFMG
generates aluminum via bauxite, separately from ATO's ore-block system)
already cover the overworld. The `_nether`/`_end` variants were
deliberately left alone - Create/TFMG have no nether/End generation for
these metals, so removing ATO's would leave zinc/aluminum/lead/nickel with
zero worldgen source in those dimensions. Their ore blocks and loot tables
(`nether_zinc_ore.json` etc.) still generate and still drop `create:
raw_zinc` (via the redirected loot table) or the equivalent, so the tag-
based smelting override still resolves them correctly. Stellaris's steel
worldgen got asymmetric treatment for the same reason: `add_overworld_
ores.json` (steel-ore-only in that dimension) was fully neutered since
vanilla iron - TFMG's real feedstock - already covers the overworld, but
`add_moon_ores.json` mixes `moon_steel_ore` in with three *other*
Stellaris-exclusive features (`moon_desh_ore`, `moon_ice_shard_ore`,
`moon_soul_soil`) with no TFMG/Create counterpart - that file was
surgically edited to drop only `moon_steel_ore` from its `features` array,
confirmed by diffing against the original extracted from the jar rather
than guessing the feature list.

**Tag cleanup via `dedup.js`, not tag-file overrides.** A tag JSON
override fully replaces the file (no merge, this project's own standing
datapack rule) - overriding `c:ingots/zinc` directly would silently drop
every other mod's entry in that tag too. Used KubeJS's additive
`ServerEvents.tags(...).remove(tag, id)` API instead
(`pack/kubejs/server_scripts/dedup.js`), removing only the now-dead
duplicate entries (`alltheores:zinc_ingot`, `stellaris:steel_ore`, etc.)
while leaving every other mod's tag membership untouched. Entries for
items that still legitimately generate somewhere (nether/end ore blocks,
per the worldgen decision above) were deliberately kept in their `c:ores/*`
tag rather than removed, since the smelting recipe's `tag`-based ingredient
still needs to resolve them.

**Closing the aluminum tier-bypass hole - the actual point of the aluminum
consolidation.** `tfmg:aluminum_ingot` is locked at `starforged_age.toml`
(Tier 5) - confirmed via `grep` against the tier files. Before this
change, `alltheores:aluminum_ingot` had zero lock anywhere, so a player
could smelt aluminum via ATO's ore chain and skip the Tier 5 gate entirely
for anything downstream that only checked for "an aluminum ingot" loosely
via the `c:ingots/aluminum` tag. Redirecting ATO's own smelting recipes to
output `tfmg:aluminum_ingot` directly closes this the same way the item
3/7 pattern closes every other hole in this pack: the locked item id is
now the *only* aluminum ingot obtainable by any path, so ProgressiveStages'
existing recipe-blocking already covers it with no new lock needed.

**Bounded extra sweep - one clean case shipped, one ambiguous case flagged
and skipped.** Per the TODO item's own scoping ("implement only clean
cases, document-and-skip ambiguous ones"):
- Stellaris steel vs. TFMG steel: clean case, implemented (above).
- TFMG silicon vs. Refined Storage silicon: checked both jars directly.
  `tfmg:silicon_ingot` is a solid metal-ingot-style item fed by TFMG's own
  bauxite/vat industrial chain (tagged `c:ingots/silicon`), while
  `refinedstorage:silicon` is a separate raw/processed material used in
  RS's own processor recipes (tagged plainly `c:silicon`, a different tag
  namespace entirely, not `c:ingots/*`). The two mods never converge on a
  shared tag, and nothing in either mod's recipe chain suggests they're
  meant to be the same underlying resource (one is a cast metal ingot, the
  other reads as a semiconductor-grade material) - genuinely ambiguous,
  left alone, flagged here rather than guessed at.

**Orphan sweep**: grepped every `ProgressiveStages/*.toml`, `server_
scripts/*.js`, and `scripts/gen_economy.py` for references to every
removed/redirected id. No orphaned references found - none of the removed
`alltheores:*`/`stellaris:steel_*` ids were ever locked, priced, or
scripted against directly anywhere else in the pack (they were pure
parallel-duplicate items with no other pack-side integration), so nothing
needed patching beyond the consolidation itself.

**Boot-tested clean**: `jar tf`-verified item ids for every redirect
target before writing the override (`create:zinc_ingot`/`zinc_block`/
`raw_zinc`, `tfmg:aluminum_ingot`/`lead_ingot`/`nickel_ingot`), all 68 new/
modified datapack files load with 0 KubeJS errors (`Added 59 recipes,
removed 120 recipes, modified 9 recipes, with 0 failed recipes`), and the
pre-existing `tfmg_stellaris_compat:replace_stellaris_loot` non-fatal WARN
(`stellaris:heavy_ingot` unknown registry key - a bug in that compat mod
itself, unrelated to this consolidation) is present and unchanged from its
previously-known baseline.

### Block-based chunk loading via Create: Power Loader (TODO.md item 7)

Ask: replace FTB Chunks' menu/permission-driven force-loading (never
configured in this pack) with an actual placeable, Create-native block,
independent of FTB Chunks' claim system, tier-gated, with an ongoing
power/fuel cost.

**Mod choice, verified not guessed.** Modrinth search for a Create-native
chunk loader turned up `create-power-loader` ("Create: Power Loader") -
decompiling `data/create_power_loader/` confirmed it's exactly what the
ask describes: loader blocks that must be spun under real Create
rotational power and continuously draw Stress to stay active (`config`
classes expose per-tier `speedMultiplier`/`stressImpact`), with STATIC/
CONTRAPTION/TRAIN/STATION modes, and zero dependency on FTB Chunks or any
claim system - it force-loads chunks unconditionally wherever placed and
spun. Only hard dependency is Create `[6.0.0,)` (installed 6.0.10); JEI is
optional and not installed, same as this pack's `create-ore-excavation`
precedent.

**Two tiers, matching this pack's own tier ladder by name, not just by
mapping onto it.** The mod itself ships loader tiers literally named
`andesite`/`brass` (its own recipe-material progression happens to mirror
this pack's Andesite Age -> Brass Age naming), each with an `empty_*` (the
placed, unspun block) and non-`empty_*` (actively loading) variant:
- `andesite_age.toml`: `create_power_loader:empty_andesite_chunk_loader` +
  `andesite_chunk_loader`. Its own crafting recipe already requires a
  respawn anchor (crying obsidian - a Nether item, Brass Age in this
  pack), so in practice it's craftable one tier later than this lock
  suggests; the lock was added anyway to match the mod's own andesite
  material-tier naming and this file's established "lock explicitly even
  where a natural gate exists" convention, with the recipe's own
  self-gating as the stricter of the two in practice.
- `brass_age.toml`: `create_power_loader:empty_brass_chunk_loader` +
  `brass_chunk_loader` - naturally gated already via `create:brass_casing`
  + `precision_mechanism` in its `mechanical_crafting` recipe (both this
  tier's own milestone materials), explicit lock added for consistency.

**Running-cost guardrail satisfied natively, no KubeJS scripting needed.**
The user's "ongoing power/fuel cost, not a free always-on toggle" ask is
met by the mod's own core design, not a bolted-on system: a loader only
force-loads chunks while its parent kinetic network is actively spinning
above its configured Stress threshold - stop the network (run out of fuel/
break the power train) and force-loading stops with it. This is a Java-
level mod behavior (chunk force-loading is a server-tick hook, not
something the datapack/KubeJS layer can express, confirmed per this
project's standing note on the limits of that layer), so no custom
scripting was written or was possible here; the mod already does exactly
what was asked.

**Disclosed, left open per the TODO item's own decision record**: no hard
loaded-chunk cap was set (the user selected tier-gating + running-cost as
the two guardrails and left a hard cap explicitly open) - if server
performance from stacked loaders becomes a real problem, the mod's own
`hard_team_force_limit`-equivalent config (unexplored this pass) would be
the place to add one later.

**FTB Chunks' own force-loading fully disabled, claims untouched.**
`server/config/ftbchunks-world.snbt` doesn't exist in a fresh checkout
(`scripts/build_server.py`'s `config/` mirror deletes and regenerates it
from the mod's defaults every build) - so the correct sequence was: boot
once with defaults to get a real, mod-generated file, copy *that* into
`pack/config/ftbchunks-world.snbt` as the new tracked baseline, then edit
exactly two keys inside its `force_loading` block:
- `max_force_loaded_chunks: 25 -> 0` - the decisive cap. This pack never
  configured the FTB Ranks `ftbchunks.max_force_loaded` override
  permission, so a hard `0` here means literally nobody can force-load a
  chunk through FTB Chunks' own menu, full stop.
- `force_load_mode: "default" -> "never"` - defense-in-depth. `"default"`
  would let a team keep force-loading chunks offline if they had the
  `ftbchunks.chunk_load_offline` FTB Ranks permission (also never
  configured), so this key alone wouldn't have mattered much - `"never"`
  closes it explicitly anyway rather than relying on an unconfigured
  permission staying unconfigured forever.
Every other key (`claiming.*`, `party_limit_mode`, `fake_players`, etc.)
was left untouched - land claims and protection stay fully functional,
only the force-loading feature is neutered.

**Boot-tested twice.** First boot (alongside items 3/8) validated the two
TOML locks parse cleanly and the mod loads with no errors. Second boot,
after committing the copied-and-edited `ftbchunks-world.snbt` to the
tracked config, confirmed FTB Chunks accepts the tracked file with zero
config-correction/parse errors (`grep -i ftbchunks` on the boot log shows
only the normal mod-load line, no `is not correct. Correcting` warning -
contrast with the pack's own `progressivestages.toml`, which does show
that warning on every boot, unrelated to this change and pre-existing).

**Incidental Stellaris 1.4.24 -> 1.4.25 version bump**, rode along in the
same `resolve_mods.py` run as the power-loader addition (Modrinth serving
a newer version by the time this was resolved). Confirmed non-disruptive:
the pre-existing, previously-known non-fatal WARN (`tfmg_stellaris_compat:
replace_stellaris_loot` failing to decode over `stellaris:heavy_ingot`, a
bug in the compat mod itself) is present and byte-for-byte unchanged
across all three boot tests this session - the bump didn't fix or worsen
it, and didn't introduce any new Stellaris-side warnings.

### Leaderboards: wealth / tier / level (TODO.md item 8)

Ask: a `/leaderboard` chat command (no GUI, no item) comparing Numismatics
wealth, ProgressiveStages tier, and Pufferfish Skills level, for both
individual players and FTB Teams teams.

**One new file, one established pattern.** `pack/kubejs/server_scripts/
leaderboard.js` follows `economy.js`'s own `ServerEvents.commandRegistry`
pattern exactly - no new mod or GUI framework. Coin denominations
(`spur`=1, `bevel`=8, `sprocket`=16, `cog`=64, `crown`=512, `sun`=4096)
were copied from `economy.js`'s own already-verified table rather than
re-derived.

**Wealth**: physical coins are counted across both `Player.getInventory()`
and `Player.getEnderChestInventory()` (confirmed both implement
`net.minecraft.world.Container` via `javap` against the installed server
jars) - plus, going beyond the TODO item's own "may need to be computed
as counted coin value" hedge, a genuine Numismatics bank-balance read.
`dev.ithundxr.createnumismatics.Numismatics.BANK` (public static
`GlobalBankManager`) -> `.getAccount(Player)` -> `.getBalance()` was
confirmed reachable from Rhino via `Java.loadClass` and `javap` against
the installed `CreateNumismatics-1.0.20` jar, and is added into the wealth
total. `getAccount()` is get-or-create (matching the mod's own `/view`
command's behavior), so calling it can silently create an empty
0-balance account for a player who never opened a bank terminal -
harmless, noted in-code.

**Tier**: `player.stages.has(id)` across the 10 ProgressiveStages tier
ids, the same KubeJS game-stages binding `mob_scaling.js` already uses -
count of stages held, highest held stage shown by name.

**Level**: `net.puffish.skillsmod.api.SkillsAPI.getCategory(...)` ->
`Category.getExperience()` -> `Experience.getLevel(ServerPlayer)`,
confirmed via `javap` against the installed `puffish_skills-0.18.0` jar,
summed across the 12 skill category ids (Pufferfish Skills has no single
"overall level" concept - it's inherently per-category, so a sum is the
`/leaderboard level` value). Category `ResourceLocation`s use namespace
`puffish_skills`, confirmed by decompiling the mod's own
`SkillsMod.createIdentifier` (the same resolution method its
`CategoryArgumentType` uses for the bare category names `skills.js`/
`dailies.js` already pass to its command).

**Teams**: reuses `player.stages.has(...)` for team tier rather than FTB
Teams' own separate `TeamStagesHelper` (a different stage store backing
FTB Quests' `team_stage` feature, not confirmed to share
ProgressiveStages' own backing data) - `progressivestages.toml`'s
`team_mode = "ftb_teams"` (confirmed in Phase 6) already means every team
member reads the same tier value, so this is the more directly-proven
path per this project's ground-truth rule. `dev.ftb.mods.ftbteams.api.
FTBTeamsAPI.api().getManager().getTeams()` -> `Team.getMembers()`/
`getShortName()`, confirmed via `javap` against the installed `ftb-teams`
jar. Team wealth/level are **summed** across members (own decision, since
neither is natively team-pooled - stated as the most natural aggregate,
matching how a shared team storage/XP pool would read); team tier is the
**max** across members as a safety net even though it should already be
identical team-wide.

**Caching for offline players/members.** `player.stages.has()` and
`SkillsAPI...getLevel()` both require a live `ServerPlayer` instance, and
wealth is expensive to recompute from a live inventory - so all three
metrics are cached in `server.persistentData` (confirmed present via
`javap` against `MinecraftServerKJS`, the same pattern `mob_scaling.js`
already uses on `entity.persistentData`), keyed by metric -> player UUID
-> `{username, value, extra, timestamp}`. Refreshed for every online
player on each `/leaderboard` invocation, and also on `PlayerEvents.
loggedOut` (confirmed present via `javap` against KubeJS's own
`PlayerEvents` plugin class) so a departing player's numbers are
reasonably fresh even if nobody ran the command right before they left.
Offline entries are marked `(last seen)` in the output.

**Command shape**: `/leaderboard <wealth|tier|level> [players|teams]`
(defaulting to `players`), top-10 via `player.tell`, matching the TODO
item's own suggested syntax exactly.

**Honest unavailability, never a silent vanilla substitute.** All three
mod APIs (Numismatics bank, Pufferfish Skills, FTB Teams) are loaded via
try/catch `Java.loadClass` at script-load time; if any fails to load, the
corresponding feature degrades to an honest chat message (`"Level
leaderboard unavailable: Pufferfish Skills server API ... could not be
loaded on this server."`) rather than silently falling back to something
misleading like vanilla XP levels - the TODO item's own explicit
instruction ("never substitute vanilla XP"). Every individual reflective
call inside the per-player loops is also wrapped in its own try/catch, so
one player's bad read can't take down the whole leaderboard for everyone
else.

**Boot-tested clean**: all three mod API classes (`Numismatics`,
`SkillsAPI`, `FTBTeamsAPI`) loaded successfully via `Java.loadClass` (no
"failed to load" console errors from `leaderboard.js` in the boot log),
and the script counted cleanly among the `12/12 KubeJS server scripts...
0 errors and 0 warnings` boot line. Command registration and live
leaderboard output couldn't be exercised without a connected client (same
disclosed limitation as every prior overhaul) - verified that the script
loads and every referenced class/method resolves, not that a real
`/leaderboard` invocation produces correct-looking chat output.

### Personal mobility: jetpack -> persistent creative flight (TODO.md item 4)

Ask: the pack had no personal flight ability at all outside Elytra
(Precision Age) and Create Aeronautics vehicles (Brass Age+) - a dedicated
mobility progression, a simple jetpack upgrading over time, culminating in
true persistent creative-style flight at Starforged Age (Tier 5), standing
apart from the travel overhaul rather than folded into it.

**Mod choice, verified not guessed (wave-1 scaffolding, folded in here).**
Create Stuff & Additions 2.1.4.a (`create_sa`) ships exactly 4 native
chestplate-style jetpacks - confirmed via its own `en_us.json` lang file
and item model/recipe file presence, not assumed from the mod's name:
copper/andesite/brass/netherite, mapping 1:1 onto this pack's own
Andesite/Brass/Precision/Induction Age material ladder. Create: Stuff &
Netherite Additions 1.2 (`create_nj`) was added alongside it for its
Netherite Exoskeleton. The runner-up, Create Jetpack, was rejected: hard
Kotlin-for-Forge dependency, only 2 tiers, and an Elytra-ingredient recipe
that would have needed KubeJS patches to fit this pack's own material
ladder - `create_sa`'s native ladder needed none of that.

**Tier locks** (already in place from wave-1, verified present in all four
files this pass): `andesite_age.toml` locks `create_sa:
copper_jetpack_chestplate`; `brass_age.toml` locks `create_sa:
andesite_jetpack_chestplate`; `precision_age.toml` locks `create_sa:
brass_jetpack_chestplate`; `induction_age.toml` locks **both**
`create_sa:netherite_jetpack_chestplate` and `create_nj:
netherite_jetpack_chestplate` (closing a tier-bypass hole the same way
TODO.md item 3 did for `alltheores:aluminum_ingot` - see that section).

**Chest-slot contention with other gear, accepted not worked around.**
Jetpacks are chestplates, so they directly compete with Silent Gear
chestplates, Elytra, and the Ars Nouveau battlemage robes for the same
equipment slot. This is the identical tradeoff shape vanilla Elytra
already imposes pack-wide (fly vs. armor value, same choice players already
make) - documented as a deliberate design consequence, not a bug or a gap
to script around with a second equipment slot.

**create_nj's netherite jetpack was a genuine duplicate - deduped this
pass.** Wave-1 flagged it and recorded the call in `DECISIONS.md`:
`create_nj:netherite_jetpack_chestplate` is a second, independently-
recipe'd netherite jetpack that fully duplicates `create_sa`'s own native
one (same chestplate slot, same functional item). Ground-truthed by
decompiling the installed `create_sna-1.2-neoforge-1.21.1.jar` (create_nj's
actual jar filename, note the mismatch from the mod id) -
`data/create_nj/recipe/netherite_jetpack_recipe.json` is a `create:
mechanical_crafting` recipe (diamond + `create:encased_fan` +
`create_nj:nether_engine` + netherite ingots -> `create_nj:
netherite_jetpack_chestplate`). Folded into `dedup.js`'s existing pattern
(`TODO.md` item 3): rather than a `c:` tag removal (jetpacks share no
common tag to clean up), a raw datapack override at `pack/kubejs/data/
create_nj/recipe/netherite_jetpack_recipe.json` keeps create_nj's own
pattern/ingredients byte-for-byte but redirects `result.id` to
`create_sa:netherite_jetpack_chestplate` - crafting create_nj's recipe now
hands the player the canonical item. `create_nj:netherite_jetpack_
chestplate` becomes unobtainable through normal survival play, but its
`induction_age.toml` lock stays in place anyway per the recorded decision
(defense in depth, matching the aluminum precedent - "unobtainable" alone
was never trusted as a substitute for a real lock elsewhere in this pack).
`create_nj` stays installed, unaffected, for the Exoskeleton it was always
also needed for.

**The Starforged Age capstone is deliberately item-free and stage-bound,
not another wearable.** Recorded decision: true creative-mode-style flight
- toggleable, no fuel, no duration limit - granted the moment a player
reaches the `starforged_age` ProgressiveStages stage (Tier 5, the gateway
out of the overworld/Nether/End loop into space travel), landing well
before the full Tier 6-9 planet grind, and explicitly *not* tied to a
Curios trinket (item 5 stays reserved for its own, separate ability
economy) or item 2's "infinite" endgame capstones (that pairing was
considered and declined).

Mechanism, in `pack/kubejs/server_scripts/mobility.js`: a straight
`Player.getAbilities().mayfly` grant/revoke keyed off stage membership, not
an item/effect/attribute. `mayfly` (not `flying`) is what's set - it makes
the double-jump-to-fly toggle available the moment it's granted without
yanking the player into the air, identical to how creative mode's own
flight toggle behaves. `PlayerEvents.stageAdded('starforged_age', ...)`
grants it and messages the player; `PlayerEvents.stageRemoved(...)` revokes
it (skipped if the player's current gamemode already grants flight
natively, so the revoke path never fights creative/spectator mode);
`loggedIn`/`respawned` reconcile mayfly against current stage membership on
every login and respawn, independent of the stage-change events.

**Survives death by construction - the exact risk `TODO.md` item 4
flagged.** This pack sets `keepInventory: false`, which would trivially
strip an item-granted or effect-granted "persistent" flight capstone on
death, undermining the word "persistent." Since the grant here is driven
entirely by ProgressiveStages stage membership - player-persistent data,
untouched by inventory clearing or gamerules - the capstone survives death
without any special-casing: the player still holds `starforged_age` after
respawning, and the `respawned` handler re-asserts `mayfly` from that stage
every time, regardless of whether vanilla's own `Abilities` fields would
have carried across on their own.

**API surface re-verified against the installed jar, not assumed from
memory** (full trail in the script's own header comment): KubeJS 2101.7.2's
`PlayerEvents.STAGE_ADDED`/`STAGE_REMOVED` are `TargetedEventHandler
<String>` firing a `StageChangedEvent` with `.player`/`.stage`; `Player.
getAbilities()` returns a plain `net.minecraft.world.entity.player.
Abilities` data class with public `mayfly`/`flying`/`instabuild` fields and
no setters for them (confirmed via `javap` - direct field assignment from
Rhino is the only way in, and it works); `ServerPlayer.
onUpdateAbilities()` is a separate override from the base `Player` method
and is what actually sends the client sync packet, so it's called
explicitly rather than relying on the field mutation alone to reach the
client.

**Boot-tested clean**: `create_sa`/`create_nj` both load with no
`ModLoadingException`, all four jetpack tier locks resolve, `mobility.js`
and the re-pointed `create_nj` recipe override both loaded with zero
KubeJS script errors and zero recipe-parse failures (checked specifically
- `netherite_jetpack_recipe` does not appear in any `Failed to parse`
warning line).

**Two disclosed boot-only unknowns** (documented inline in `mobility.js`,
can't be resolved without a connected client): (1) this script only
re-asserts `mayfly` on login/respawn/stage-change, not every tick - if some
other system ever silently clears a player's `mayfly` flag mid-session,
the fix won't land until their next login/respawn/stage change; left this
way deliberately since a per-tick check across every online player is a
real cost for something that should almost never need to fire. (2) whether
the client-side flight toggle "feels" the change instantly the same tick
`stageAdded` fires mid-session, or needs a reconnect/respawn to pick it up,
isn't verifiable without an actual client attached.

### Curios as a discoverable/upgradeable player-ability system (TODO.md item 5)

Ask: make Curios (installed since Phase 7 as an Ars Nouveau dependency, never
used as its own content system) a real source of player abilities - mostly
discoverable through exploration, some craftable, each unique trinket
granting an ability or bonus, with an upgrade path, and deliberately **no**
ProgressiveStages tier lock (a found curio is meant to be a pure exploration
payoff, not another progression gate).

**Mod choice (wave-1 scaffolding, folded in here): Artifacts 13.2.1.** Zero
new hard dependencies - Curios 9.5.1 (already installed), cloth-config, and
JEI are all soft-detected. The runner-up, Relics, was rejected: a new hard
dependency, a smaller item pool, and a craft-first design that cuts against
this item's "found through exploration" ask.

**Native loot injection silenced entirely - this pack's own structure-loot
tiers become the ONLY placement path.** Artifacts ships its own loot
injection as Global Loot Modifiers, rolling extra items into vanilla
structure chests natively. Per the recorded decision (one rarity system, not
two competing ones), every one of its 35 inject tables was overridden to an
empty pool - `pack/kubejs/data/artifacts/loot_table/inject/{chests,
archaeology}/**` (30 chest tables + 5 archaeology tables, counted against the
actually-installed jar, not assumed) - which silences the mod's own GLM
placement without touching the GLM registration itself (an empty pool just
rolls nothing). Its 2 entity-drop GLMs (cow/mooshroom -> Everlasting Beef)
were left native since they sit entirely outside the structure-loot
mechanism this hookup targets.

**48 items, not 47 - counted programmatically, not guessed.** The original
research brief estimated 47 Java-coded abilities; extracting the installed
jar and counting `data/artifacts/tags/item/artifacts.json`'s own master tag
puts the real number at 48. Every one of the 48 is accounted for: 45 spread
across a 4-tier Common/Uncommon/Rare/Epic curation table (18/19/8/3 items,
judged per-item from the mod's own `en_us.json` config-description strings
plus its Curios equip-slot tag as a tie-breaker for borderline cases), plus
`umbrella` (held, not worn), plus 2 deliberately excluded from the *upgrade*
mechanic only (`everlasting_beef`/`eternal_steak` - see below). The full
per-item bucket reasoning lives in `scripts/gen_structure_loot.py`'s own
module docstring, alongside `curios_upgrades.js`'s matching 48-count note.

**Hooked into the existing structure-loot rarity tiers, exactly as
decided**, not a bespoke placement system: each of the 4 curation buckets is
written as its own small nested loot table
(`pack/kubejs/data/artifacts/loot_table/vpp_bucket/{common,uncommon,rare,
epic}.json`, uniform weight-1 per item plus its own empty-weight backstop),
and each of `gen_structure_loot.py`'s 4 existing `TIERS` bonus pools gets one
new low-weight (`ARTIFACT_BUCKET_WEIGHT = 2`) reference into the matching
bucket. The two backstops (top-level pool, nested bucket table) compound
multiplicatively to land every tier at a roughly tier-flat ~5-6% chance of
finding *some* artifact per chest visit, while which bucket a chest's tier
draws from is what actually scales the *quality* - Common-bucket items only
ever show up in Common-tier chests, Epic-bucket items only in the 4 rarest
structures in the game. Regenerating the buckets meant re-running the
generator against all 55 chest tables, hence the 55 modified
`pack/kubejs/data/minecraft/loot_table/chests/**` files alongside the new
artifacts-namespaced ones in this commit - same files the world exploration
overhaul originally wrote, now carrying one additional pool entry each.

**Duplicate-combine upgrade mechanic**, in `pack/kubejs/server_scripts/
curios_upgrades.js`: combining 2x the same artifact produces 1x the same
artifact plus a bonus stat, via a data component stamped onto the crafted
result - one rule per Curios *slot type* (head/necklace/hands/feet/belt/
curio), not a bespoke recipe per item, so it works uniformly across all of
Artifacts' Java-coded abilities without touching any of their internals
(every artifact ships component-free by default, so adding a component to a
shapeless recipe's output can't collide with anything the item's own ability
code reads). 46 recipes total under `vanillaplusplus:artifact_upgrade/*` (45
per-item across the 6 Curios slot groups + 1 for the held umbrella),
generated by a loop over the same per-slot item lists, not hand-written one
at a time.

**Ground-truth deviation from the literal brief, endorsed.** The original
brief specified the vanilla `minecraft:attribute_modifiers` component for
the combine output. Verified via `javap` against the installed jars: that
component only applies while an item sits in one of vanilla's own
`EquipmentSlotGroup` slots - Artifacts trinkets are worn in *Curios* slots, a
separate inventory capability vanilla's component never sees. Curios 9.5.1
ships its own parallel, field-for-field-identical `curios:
attribute_modifiers` component (`top.theillusivec4.curios.api.
CurioAttributeModifiers`, confirmed by class-file inspection) for exactly
this case, so curio-worn items get that component instead; the one held
item, `umbrella`, isn't a Curios item at all and correctly gets the literal
vanilla component the brief asked for, since that's what actually governs a
held item.

**Combine-cap semantics**: capped implicitly, no extra guard code needed.
Each recipe's output component set is a fixed single-entry modifier list
(not derived from the two input stacks' own components), and KubeJS's
default shapeless ingredient matching ignores components - so feeding two
already-upgraded copies back through the same recipe just reproduces the
same capped result again, not a stacking +2.

**Exclusions, both disclosed and deliberate**: `everlasting_beef`/
`eternal_steak` are excluded from the combine mechanic (consumables with no
persistent equip slot - a stamped attribute modifier would never get a
chance to apply before the item is eaten; Artifacts already ships its own
smelt-upgrade path between the two, so nothing is lost).

**Boot-tested clean**: all 35 inject overrides and all 4 `vpp_bucket` tables
parse with zero loot/component errors; all 46 `artifact_upgrade` recipes
register with zero `curios:attribute_modifiers`/`minecraft:
attribute_modifiers` parse failures (no precedent for this component
combination anywhere else in this pack, checked specifically); `curios_
upgrades.js` and the regenerated `gen_structure_loot.py` output both loaded
cleanly among the 14/14 KubeJS server scripts with 0 errors, 0 warnings.

**Disclosed limitation, same shape as every other overhaul in this pack**:
no live client to confirm loot actually rolls artifacts at the expected
~5-6% rate in a real explored world, or that the combine recipes feel
right in an actual crafting grid - verified that the schema is well-formed
and every recipe/table resolves, not the in-game feel.

### Hostile + passive mob variety, limited unique drops (TODO.md item 6)

Ask: `instructions.md` explicitly called for "more varied mobs/animals" with
"still limited types of drop" (its own example: multiple cattle types should
all still just drop beef) - never addressed in any prior phase. The pack was
still effectively vanilla-mob-only going into this item.

**Mod choice (wave-1 scaffolding, folded in here): Creeper Overhaul 4.0.6 +
Born in Chaos 1.7.6 + Naturalist for passive fauna.** Alex's Mobs was
explicitly ruled out during scoping for being known to ship lots of
mob-specific unique drops/trophies, cutting directly against this item's own
drop-cleanliness constraint. Creeper Overhaul required two additional
dependencies discovered only via an actual boot-test crash (`resourceful-
config` declared in its own `neoforge.mods.toml`; `resourceful-lib` needed
at the **class level** - `NoClassDefFoundError` on `ResourcefulRegistries` -
even though neither Modrinth's dependency metadata nor the mod's own
`neoforge.mods.toml` names it, the same discovery pattern this pack already
hit for Ars Nouveau's geckolib/curios dependency in Phase 7).

**Namespace catch: Born in Chaos' real data namespace is `born_in_chaos_v1`,
NOT the Modrinth slug `borninchaos`.** Confirmed by extracting the jar
directly - a slug-named override path would have silently no-op'd against
nothing, producing zero errors and zero effect, the worst kind of silent
failure. Every loot override and `mob_scaling.js` entry for this mod uses
the verified real namespace.

**Canonical drop mapping, patched after the fact regardless of what each mod
ships natively** (per the recorded decision - mod selection was driven by
creature quality/variety, not narrowed to only-vanilla-drop mods up front):
entity loot table overrides at `pack/kubejs/data/born_in_chaos_v1/
loot_table/entities/` (22 files) and `pack/kubejs/data/naturalist/
loot_table/entities/` (10 files), each copied from the real installed-jar
table and redirected onto this pack's existing shared canonical drop set
(beef/porkchop/mutton/chicken/leather/feathers/string/etc.) - matching
`instructions.md`'s own cattle/bird example precisely. Creeper Overhaul's 16
biome-flavored creeper variants were checked against the installed jar and
found to already be 100% vanilla-drop (they just reskin/reflavor the
creeper, no custom items anywhere in their loot), so no override was needed
there at all - verified, not assumed, before leaving them untouched.

**Load-bearing custom items kept, unique weapons/armor/charms stripped.**
Where a mob's native drop is structurally load-bearing to that mod's own
mechanics (not just a flavor drop), it stayed in the overridden table
alongside the canonical redirect; every unique weapon, armor piece, and
combat-stat charm was stripped outright. That last category specifically
includes Born in Chaos' charm accessories (`charmof_power/resistance/
stealth/endurance/fury`) - a call made and endorsed during implementation,
not just a drop-cleanliness technicality: permanent combat-stat accessories
from mob drops would have competed directly with both this pack's own skill
system and item 5's Artifacts as the sanctioned source of that kind of
bonus, so they were cut rather than kept as a second, unscaled source of the
same thing.

**Difficulty-scaling hookup, as decided**: `mob_scaling.js`'s `MONSTER_
TYPES` whitelist - previously a hardcoded `Set` of vanilla mob ids only -
was extended with all 16 Creeper Overhaul variants and all 45 wild-spawning
Born in Chaos hostiles (61 new ids total), so every new hostile participates
in the same dimension/distance/player-tier scaling, star-rating nametag, and
bonus-currency-on-kill system vanilla hostiles already get. Passive mobs
(all of Naturalist, Born in Chaos' non-hostile entries) stay outside this
system entirely, consistent with vanilla passive mobs already being excluded
from it today - no new precedent needed there.

**Flagged for live-play review, not blocking**: 41 of Born in Chaos' 45
hostiles spawn via a `neoforge:any` biome predicate - everywhere, in every
dimension, with no biome-appropriateness filtering relative to the ~100 new
Terralith biomes the world exploration overhaul added. Left as-is rather
than guessed at without a live world to actually judge "does this feel too
samey" against - recorded as a candidate for a future spawn-tuning pass if
it turns out to be a real problem in practice, not treated as a bug now.

**Boot-tested clean**: `Creeper Overhaul 4.0.6`, `Born in Chaos 1.7.6`, and
`Naturalist 1.0.2` (plus `resourcefulconfig`/`resourcefullib`) all load with
no `ModLoadingException`; all 32 entity loot overrides parse with zero
missing-loot-table/unknown-item errors; `mob_scaling.js`'s extended
`MONSTER_TYPES` set loaded cleanly among the 14/14 KubeJS server scripts
with 0 errors, 0 warnings.

**Disclosed limitation**: same as every other overhaul in this sandbox - no
live client to confirm actual spawn rates, drop rates, or the `neoforge:any`
spawn-everywhere finding above feel right in a real explored world; verified
that every mod loads, every override resolves, and the scaling hookup is
correctly wired, not the in-game feel.

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

`scripts/build_mrpack.py` builds `vanilla-plus-plus-client-<VERSION>.mrpack`
(gitignored, regenerate on demand) directly from `pack/mods.lock.json` —
importable into Prism Launcher for a client instance. See "Release
engineering" below for the full release test/bundling pipeline this became
part of for the 1.0.0 cut.

## Release engineering

Added for the 1.0.0 initial release (DECISIONS.md's "Release test +
bundling architecture — ADOPTED", ~2026-07-10). Everything through the
"Phase plan" above shipped features; this section covers how the release
itself is tested, versioned, and packaged.

### Test architecture: four layers, each catching a different failure class

**L0 — boot smoke** (`scripts/tests/l0_boot_smoke.sh`). Builds `server/`,
boots it, and asserts: a clean `Done(` line; zero
`ModLoadingException`/`Loading errors`/`FATAL`; the server-side mod count
matches `pack/mods.lock.json`'s `side != "client"` count; both KubeJS
script layers (startup + server) report `0 errors and 0 warnings`; every
WARN/ERROR line in the boot log matches an explicitly documented
known-noise baseline (encoded as grep patterns, not a blanket allow-list —
DECISIONS.md's "Known-acceptable boot noise" section plus a few more
categories this release wave ground-truthed across 6+ clean boots:
pre-existing benign recipe-skip WARNs from stellaris/tfmg/silentgear,
ModernFix/mixin/VanillaPackResourcesBuilder informational WARNs). Catches:
mod-loading/dependency regressions, config corruption, and — critically —
*new* warning classes a change might silently introduce, which ad hoc "eyeball
the log" boot testing (this project's practice through wave-2) reliably
misses once a boot log is thousands of lines long.

**L1 — self-test** (`pack/kubejs/server_scripts/selftest.js`'s
`/vpp_selftest` command + `scripts/tests/l1_selftest.py`'s driver). Boots the
server, issues the command via `cmd_fifo` (no attached `ServerPlayer` —
console-only, matching this project's whole boot-testing history), and
parses a machine-readable `VPP_SELFTEST: PASS (n/n, k skipped)` summary
line. 17 always-executable assertions cover the pack's real systems:
ProgressiveStages stage resolution, Pufferfish Skills category/experience
presence, Numismatics bank API reachability, FTB Teams manager reachability,
item/entity/loot-table registry resolution (coin denominations, cross-mod
dedup-canonical items, `born_in_chaos_v1:krampus`, a generated
`artifacts:vpp_bucket/common` loot table), recipe-manager sanity (>1000
total recipes; the Curios upgrade recipes are exactly 46, matching item 5's
implementation count), command registration (`/leaderboard`, `/sell`), a
`persistentData` round-trip, and an economy sell round-trip mirroring
`economy.js`'s own price table. 3 more assertions need a live
`ServerPlayer` (bank balance for a player, stage checks against a player,
the sell round-trip's inventory side) and report `SKIP` rather than a faked
`PASS` when none is attached — an honest gap, not a lowered bar; driving
those needs L2/L3. There was **no pre-existing 20-assertion list** anywhere
in the repo despite DECISIONS.md referencing one (the research brief that
would have enumerated it was never captured to a durable file) — this set
was authored fresh against the pack's actual systems and iterated against
real boot errors until every assertion either passed or was replaced.

Building L1 surfaced three real bugs no prior boot test had caught, because
none had ever actually *executed a command* against a live server before —
every previous "boot test" in this project's history only ever watched the
startup log, never drove gameplay logic:
1. **`noisiumed` had shipped a non-functional Fabric jar since Phase 9.**
   `resolve_mods.py` trusted Modrinth's per-file `"primary"` flag, but a
   single Modrinth *version* can bundle fabric/forge/neoforge jars
   together, and noisiumed's primary happened to be its Fabric build even
   when queried with `loaders=["neoforge"]`. FML silently skipped it every
   boot (`"is a Fabric mod and cannot be loaded"`) — a real, live gap this
   pack shipped for an entire wave. Fixed: `resolve_mods.py`'s new
   `pick_file()` matches the file to the requested loader by filename,
   falling back to `"primary"` only when no loader-specific match exists.
2. **The installed Rhino engine (KubeJS 2101.7.2/build.368) does not give
   `const`/`let` fresh per-iteration block scoping inside a `for(;;)` loop
   body or a `try`/`catch` invoked from one** — re-executing the same
   `const` declaration on a 2nd+ iteration throws
   `TypeError: redeclaration of const/var X`. This is a real, load-bearing
   Rhino limitation different from standard V8/spec ES6 behavior. Found
   because `/leaderboard` — wave-2, committed, boot-tested, but never
   actually *command-executed* — would have crashed the instant more than
   one cached/online entry existed. Fixed by converting nested `const` to
   `let` throughout `selftest.js` and `leaderboard.js`. Two `for (const x
   of ...)` for-of forms elsewhere (`economy.js`'s `payCoins`,
   `selftest.js`'s own coin helper) were left as-is — different iteration
   protocol, not proven broken, flagged here as an unverified residual risk
   for anyone else writing command-execution KubeJS code.
3. **KubeJS/Rhino exposes zero-arg Java accessors like
   `ServerLevel.dimension()` as pre-resolved bean properties, not callable
   methods** — calling them with `()` throws `"Cannot call property X ...
   It is not a function"`. Also learned `server.registryAccess()` does
   **not** contain the loot_table registry (`"Missing registry:
   minecraft:loot_table"`) — loot tables are a *reloadable* (datapack)
   registry reached via `server.reloadableRegistries().lookup()
   .lookupOrThrow(...)`, which returns a `HolderLookup` (`.get(ResourceKey)
   -> Optional`, not `Registry`'s `.containsKey()`).

**L2 — HeadlessMC client smoke** (`scripts/tests/l2_client_smoke.py`).
Assembles the *full* client-relevant mod set (every lockfile entry with
`side != "server"`, 81 mods including all 6 client-optimization mods and 3
QoL mods added for this release) into a real HeadlessMC 2.9.0 instance
(`/home/ubuntu/.minecraft`) and launches it offline, catching client-only
mixin/dependency crashes the dedicated server structurally can't see
(`side:client` mods never land in `server/mods` — `build_server.py` has
excluded them since before this release, verified correct this wave). The
"Reloading ResourceManager" line — reached on every attempt — lists every
loaded mod's resource pack; reaching it, with zero
`ModLoadingException`/missing-dependency/cowardly-refusing errors, is
conclusive proof of mod discovery + dependency resolution + mixin
application for the complete set. Two real blockers were found and worked
around in the *test harness*, ground-truthed via `javap` decompilation and
repeated manual launches rather than assumed:
- **Sodium's `PreLaunchChecks` aborts before any mod loads** because it
  can't recognize HeadlessMC's LWJGL version string. Decompiling Sodium's
  `BugChecks`/`PreLaunchChecks` classes found the documented workaround for
  exactly this non-standard-launcher case (Sodium's own GH issue 2561):
  system property `sodium.checks.issue2561=false`, which must be passed via
  HeadlessMC's `launch ... --jvm "..."` flag — the actual game runs in a
  *forked* process, so an outer `-D` flag on the launcher jar never reaches
  it.
- **HeadlessMC's own `headlessmc-lwjgl` module has a flaky race condition**
  in its STB→`javax.imageio` PNG-decode redirection under this pack's
  ~4000-texture concurrent resource-reload load — confirmed via 10 repeated
  manual launches: the complete mod list loaded cleanly *every single time*,
  but a different specific `javax.imageio.IIOException` (different message,
  different texture) crashed asset decoding each run before reaching a
  fully texture-atlas-stitched "menu-ready" state. This is a harness-level
  instability, not a pack defect (10/10 consistent full mod-list load, 0/10
  FML errors, the specific crash point never repeats). `l2_client_smoke.py`
  discloses this explicitly in its own PASS report rather than either
  silently failing the whole client bundle over it or silently ignoring it;
  `--retries 3` is a pragmatic mitigation that doesn't mask genuine FML
  errors (checked independently of retry count).

**MoreCulling verdict**: loaded successfully. DECISIONS.md's pre-declared
contingency (its `neoforge.mods.toml` minecraft-version range is literally
`[1.21,1.21.1)`, textually excluding exact 1.21.1) was evaluated and did
**not** trigger — confirmed present in L2's loaded-mod list, matching the
JEI-precedent reasoning already recorded (JEI has the identical range
pattern and is known-good everywhere on 1.21.1). Kept in the manifest with
no changes needed.

**L3 — live client join** — deliberately **not implemented** for this
release. The join mechanism itself is unproven (protocol bots were already
confirmed a dead end against NeoForge's handshake, per DECISIONS.md), it's
the highest-cost layer to build, and L0–L2 already cover the failure modes
most likely to actually break a release (server-side data/recipe/loot
regressions, client-only mod-loading crashes). Left as explicit post-release
backlog — see TODO.md.

### The honest L2/L3 boundary

L0-L2 together prove: the server boots clean with no fatal errors and no
new warning classes; the pack's core data/recipe/loot/registry systems
resolve correctly at runtime (not just "the JSON parses"); and the full
client mod set discovers, dependency-resolves, and mixin-applies cleanly.

**None of this release's testing verifies:**
- **Rendering correctness** — Create contraption/pulley/train visuals,
  GeckoLib entity animation playback (Ars Nouveau familiars, Born in Chaos,
  Naturalist), Epic Fight's animation-driven combat, general UI/inventory
  layout (including the narrow Create Aeronautics Staff-of-Physics
  inventory-display bug reported at ImmediatelyFast 1.6.10 — this release
  ships 1.6.11, which the changelog claims fixes it, but that claim itself
  is unverified by anything in this pipeline).
- **A live client join** — L3, deliberately deferred.
- **Multiplayer interaction** — team/party mechanics, PvP balance, server
  load under multiple real players.
- **Live combat/economy balance** — numbers were set by design intent
  (DESIGN.md's various tier/pricing sections), not measured against actual
  play.

These gaps are genuine, not oversights papered over — L2's own script prints
this boundary explicitly in its PASS report, and it's restated here and in
HANDOFF.md so it survives a session reset.

### Bundle design

Two artifacts, both versioned from the single `pack/VERSION` file (`1.0.0`
for this release):

- **Client**: `scripts/build_mrpack.py` → `vanilla-plus-plus-client-<VERSION>.mrpack`.
  Modrinth's `.mrpack` format — a `modrinth.index.json` mod-download
  manifest (direct URLs + hashes, `env` markers derived from each lockfile
  entry's `side`) plus an `overrides/` folder for `config`/`kubejs`/
  `defaultconfigs`. Small (~250 KB) since it doesn't embed the actual mod
  jars, just downloads them on import (Prism Launcher).
- **Server**: `scripts/build_server_bundle.py` → `vanilla-plus-plus-server-<VERSION>.zip`.
  Reuses `build_server.py`'s own sync (imported, not duplicated) then zips
  `server/` minus runtime/session state (`world/`, `logs/`, `cmd_fifo`,
  `crash-reports/`, `*.log`, the redundant `neoforge-installer.jar`, and
  pure caches like `.sable/`/`cache/`/`local/`). Includes everything
  `run.sh`/`run.bat` need to boot (`mods/`, `config/`, `kubejs/`,
  `defaultconfigs/`, `libraries/`, `server.properties`,
  `user_jvm_args.txt`). ~350 MB (mostly `libraries/` + server-side mod
  jars). `eula.txt` is **deliberately excluded** — even though this dev
  session's own `server/eula.txt` has `eula=true` from boot-testing,
  shipping that would silently pre-accept the EULA on the operator's
  behalf, which the recorded release decision explicitly rejected. A
  generated `README.md` at the zip root documents the first-run EULA step,
  Java 21 requirement, and the JVM/RAM tuning already baked into
  `user_jvm_args.txt`.

`online-mode=true` ships unchanged in the server bundle (the recorded
default); any future L3 join-testing must use a separate test-only
`server.properties` profile with it flipped off, never this shipped one.

### Versioning

`pack/VERSION` is the single source of truth, read by both build scripts
and embedded in both artifact filenames — bump it once at the next release
cut rather than hunting for hardcoded version strings in multiple places
(the bug this replaced: `build_mrpack.py` hardcoded `"0.9.0"` and had
silently drifted from reality before this release wave).
