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

## The tier ladder

Every other system in this pack (storage caps, RPG skill unlocks, currency,
combat/magic tiers, dimension access, mob difficulty zones) gates against one
of these six tiers. Tiers 0-3 stay entirely inside Create's own material
chain (no addon needed). Tier 5 is a placeholder until Phase 8 picks the
endgame/dimension content that anchors it — see the TODO in
`pack/config/ProgressiveStages/starforged_age.toml`. **Tier 4 is not a
placeholder for "storage begins here"** — see the storage/autocrafting column
below and the corrected note after the table.

| # | Stage id | Name | Unlocked by | Create milestone | Storage / autocrafting rung | Vanilla tier & dimension also gated here |
|---|---|---|---|---|---|---|
| 0 | `rootborn` | Rootborn | starting stage | — | vanilla inventory/chests only | wood/stone |
| 1 | `andesite_age` | Andesite Age | craft/pick up `create:andesite_alloy` | water wheels, mixing/pressing, crushing wheels | **first browsable storage interface unlocked** — tiny capacity, manual only, no autocrafting | iron tools/armor, rails |
| 2 | `brass_age` | Brass Age | craft/pick up `create:brass_ingot` | Mechanical Arm, Deployer, Sequenced Gearshift, Elevator Pulley, train control | storage capacity scales up; **first crafting automation** via Create's own Mechanical Arm + Deployer feeding the network | diamond tools/armor, enchanting table, beacon, **Nether** |
| 3 | `precision_age` | Precision Age | obtain `create:refined_radiance` or `create:shadow_steel` | Sturdy Sheet (Create's own top alloy) | bigger storage tier; automation scales to multi-step Create contraptions (sequenced gearshifts, larger Deployer arrays) | netherite tier, elytra, totem, **The End** |
| 4 | `induction_age` | Induction Age | temp trigger: netherite ingot *(real trigger TBD in Phase 2)* | — | **ceiling of the same storage system**: full network capacity + native pattern-based autocrafting (e.g. Refined Storage's Crafter Manager or AE2's molecular assembler network — exact mod picked in Phase 2) | TBD |
| 5 | `starforged_age` | Starforged Age *(placeholder)* | temp: kill Ender Dragon | — *(Phase 8 picks the real endgame/dimension content)* | — | TBD |

Dependency chain is strictly linear (`rootborn -> andesite_age -> brass_age ->
precision_age -> induction_age -> starforged_age`); `linear_progression = true`
in `progressivestages.toml` so granting any tier auto-grants everything below
it. This directly satisfies "previous Create stuff should be necessary for
the next tier of stuff."

### Correction: storage starts at Tier 1, not Tier 4

An earlier draft of this doc gated "storage" as a whole to Tier 4
(Induction Age), treating it as a wholesale placeholder pending a new
AE2/Mekanism-class mod. That's wrong against `instructions.md`, which asks
for storage to be browsable "from traditional iron tier and onward" and to
"start out limited, but still browsable," with capacity *and* autocrafting
both continuing to scale after their first unlock rather than appearing
whole-cloth at some late tier.

Corrected model: **one continuous storage system spanning Tiers 1-4**, picked
in Phase 2 (Refined Storage/AE2/Sophisticated Storage are the candidates —
see Phase 2 task). It's introduced at Andesite Age (Tier 1) as a tiny,
browsable, manual-only interface; capacity scales at every tier after that;
autocrafting itself first becomes possible at Brass Age (Tier 2) specifically
*through Create's own Mechanical Arm/Deployer machinery* rather than a bolt-on
pattern autocrafter, keeping "engaging with Create should be the sole process
by which you automate things" true even for storage automation; and Tier 4
(Induction Age) is simply that same system's top rung (full network storage +
native pattern-based autocrafting), not a separate mod bolted on at the end.
Tier 4's trigger is still a temporary vanilla stand-in until Phase 2 finalizes
the mod and its real top-tier item/milestone.

### Why gate Nether at Brass Age and The End at Precision Age

Vanilla lets you rush the Nether/End with almost no preamble. Locking the
Nether behind Brass Age (Create's superheating/blaze-adjacent tier) and The
End behind Precision Age gives both dimensions a reason to exist in the
progression rather than being a speedrun detour — see `instructions.md`'s
"multiple dimensions that lock away better progression" requirement.

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
