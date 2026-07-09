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
- **Refined Storage 2.0.9** for the browsable storage network — named
  explicitly in `instructions.md` ("think mods like refined storage"), 1.4M+
  downloads, self-contained (no extra required mods). Energy requirement
  disabled (see storage section). **KubeJS 2101.7.2 + Rhino** power the
  storage recipe patch here and the full recipe-gating pass in Phase 9.

## The tier ladder

Every other system in this pack (storage caps, RPG skill unlocks, currency,
combat/magic tiers, dimension access, mob difficulty zones) gates against one
of these six tiers. Tiers 0-3 stay entirely inside Create's own material
chain (no addon needed). Tier 5 is still a placeholder until Phase 8 picks
the endgame/dimension content that anchors it — see the TODO in
`pack/config/ProgressiveStages/starforged_age.toml`. Tier 4's storage
content is fully resolved as of Phase 2; only its narrative trigger is still
a Phase 8 TODO.

| # | Stage id | Name | Unlocked by | Create milestone | Storage / autocrafting rung | Vanilla tier & dimension also gated here |
|---|---|---|---|---|---|---|
| 0 | `rootborn` | Rootborn | starting stage | — | vanilla inventory/chests only | wood/stone |
| 1 | `andesite_age` | Andesite Age | craft/pick up `create:andesite_alloy` | water wheels, mixing/pressing, crushing wheels | **first browsable storage interface** — Grid + Cable + Disk Drive + 1k Disk/Block, manual only, no autocrafting | iron tools/armor, rails, **Nether** |
| 2 | `brass_age` | Brass Age | craft/pick up `create:brass_ingot` | Mechanical Arm, Deployer, Sequenced Gearshift, Elevator Pulley, train control | 4k capacity; **first crafting automation** — Create's Mechanical Arm/Deployer feed the network via Importer/Exporter/External Storage/Constructor/Destructor | diamond tools/armor, enchanting table, beacon |
| 3 | `precision_age` | Precision Age | obtain `create:refined_radiance` or `create:shadow_steel` | Sturdy Sheet (Create's own top alloy) | 16k capacity; wireless/network devices (Wireless Grid, Network Receiver/Transmitter, Relay, Portable Grid, Security Manager) | netherite tier, elytra, totem, **The End** |
| 4 | `induction_age` | Induction Age | temp trigger: netherite ingot *(real narrative trigger TBD in Phase 8)* | — | **ceiling of the same system**: 64k capacity + Advanced Processor + native pattern-based autocrafting (Autocrafter/Autocrafter Manager/Pattern/Pattern Grid) | TBD |
| 5 | `starforged_age` | Starforged Age *(placeholder)* | temp: kill Ender Dragon | — *(Phase 8 picks the real endgame/dimension content)* | — | TBD |

Dependency chain is strictly linear (`rootborn -> andesite_age -> brass_age ->
precision_age -> induction_age -> starforged_age`); `linear_progression = true`
in `progressivestages.toml` so granting any tier auto-grants everything below
it. This directly satisfies "previous Create stuff should be necessary for
the next tier of stuff."

### Storage: Refined Storage, one continuous system spanning Tiers 1-4

Picked over AE2 and Sophisticated Storage because `instructions.md` names it
directly ("think mods like refined storage where you have a central
interface"). It's introduced at Andesite Age (Tier 1) as a tiny, browsable,
manual-only interface; capacity scales every tier after that (1k -> 4k -> 16k
-> 64k, RS's own native disk tiers, fluid tiers mirror in lockstep); crafting
automation first becomes possible at Brass Age (Tier 2) specifically *through
Create's own Mechanical Arm/Deployer* feeding the network via RS's
Importer/Exporter/External Storage/Constructor/Destructor, rather than RS's
own pattern autocrafter — keeping "engaging with Create should be the sole
process by which you automate things" true even for storage automation. RS's
own native autocrafting (Autocrafter/Pattern) is reserved for Induction Age
(Tier 4), which is that same system's top rung rather than a separate mod
bolted on late. Full per-tier item/block lists are in
`pack/config/ProgressiveStages/{andesite,brass,precision,induction}_age.toml`.

Two real snags surfaced while implementing this, both resolved:

- **Every RS component needs Nether Quartz** (`quartz_enriched_iron/copper`,
  `silicon`, and everything built from them all require `c:gems/quartz`,
  which is Nether-exclusive in vanilla). The original design gated the Nether
  behind Brass Age; that made Tier-1 storage impossible outright, so **the
  Nether now unlocks at Andesite Age instead** — verified by extracting the
  actual RS jar's recipe JSONs rather than assuming.
- **RS's stock Disk Drive recipe needs an Advanced Processor**, which needs a
  diamond — locked until Brass Age, which would make the Tier-1 network
  impossible even with the Nether open. Patched via KubeJS
  (`pack/kubejs/server_scripts/storage.js`) down to an Improved Processor
  (gold-tier, never locked by any stage). The Controller didn't need a
  similar patch: RS ships a `requireEnergy` config option, and with it
  disabled (`pack/config/refinedstorage-common.toml`) the Controller becomes
  entirely optional — Create has no native FE generation, and building a
  whole power subsystem just to browse a storage disk isn't something
  `instructions.md` asked for.

### Why gate Nether at Andesite Age and The End at Precision Age

Vanilla lets you rush the Nether/End with almost no preamble. Locking the End
behind Precision Age gives it a reason to exist in the progression rather
than being a speedrun detour, per `instructions.md`'s "multiple dimensions
that lock away better progression" requirement. The Nether unlocks a tier
earlier than originally planned (Andesite Age, not Brass Age) purely because
Refined Storage's material chain requires it — see the storage section above.

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
2. Tiered storage progression: browsable storage introduced at Tier 1
   (tiny, manual-only), capacity scaling every tier after, autocrafting
   unlocked at Tier 2 via Create's own Mechanical Arm/Deployer, scaling to
   full network autocrafting by Tier 4.
3. RPG skill/leveling system (Running/Swimming/Mining/Building/Swords/Bows/etc).
4. Quest system: preset track (team-shared) + long-running exponential
   quests + randomized daily quests (both per-player).
5. Economy (tiered vendor pricing) + async player marketplace.
6. Teams (flip `team_mode` to `ftb_teams`) + chunk claims.
7. Combat variety (balanced weapon classes tied to RPG skills) + blacksmithing
   recipe swap + mage/summoner archetype.
8. Mob scaling by zone + visual power indicator + dungeons/bosses with unique
   drops + structure density/reward scaling + real dimension for Tier 5.
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
