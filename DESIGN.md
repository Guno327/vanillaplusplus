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

### Why gate the Nether at Brass Age and The End at Precision Age

Vanilla lets you rush the Nether/End with almost no preamble. Both dimensions
now get a real reason to exist in the progression, per `instructions.md`'s
"multiple dimensions that lock away better progression" requirement: the
Nether is where RS's Quartz chain comes from, and it unlocks at Brass Age —
where RS itself unlocks, so there's no dead tier where the dimension is open
but nothing needs it yet. The End stays gated behind Precision Age as before.

### Team mode

`progressivestages.toml` currently sets `team_mode = "solo"` because FTB Teams
isn't installed yet. **Flip this to `"ftb_teams"` in Phase 6** once FTB Teams
is added — that's what makes the preset tier progression shared across a team
while daily/long-running quest progress (added on top in Phase 4, tracked
separately) stays per-player, per the team requirement in `instructions.md`.

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
4. Quest system: preset track (team-shared) + long-running exponential
   quests + randomized daily quests (both per-player).
5. Economy (tiered vendor pricing) + async player marketplace.
6. Teams (flip `team_mode` to `ftb_teams`) + chunk claims.
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
