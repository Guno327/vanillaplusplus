# Handoff

**Status as of this note: autonomous work in progress, mid-TODO-list.**
The user asked for a planning-only session (brainstormed and scoped 8
TODO items into `TODO.md`, no implementation) followed by unattended
overnight-style work: implement `TODO.md` items in order, self-scheduling
wakeups across usage-refresh boundaries (CronCreate one-shot jobs, ~4
hours apart — see the memory note below for the pattern), until either
the list is exhausted or told to stop. **Read `TODO.md` before doing
anything else** — it's the authoritative backlog, each item pre-scoped
with the user so implementation shouldn't need to re-ask questions already
answered there. Item 1 (ore veins) is done; resume at whichever item is
next un-checked.

## What's done

Everything through four post-launch overhauls, each fully implemented,
boot-tested, committed, and documented in `DESIGN.md`:

1. **Original 9-phase build** (tier ladder, storage, RPG skills, quests,
   economy, teams/claims, combat/magic variety, mob scaling/dungeons/space
   travel, performance/packaging) — `DESIGN.md`'s "Phase plan" section.
2. **Gear overhaul** (5 parts) — all weapon/tool/armor progression funneled
   through Silent Gear smithing or boss drops; Epic Fight's 5 weapon types
   extended across all 10 tiers with a 6-way melee skill split; Ars Nouveau
   mage armor redirected through Silent Gear; 3 boss-unique weapons.
3. **Utility overhaul** (6 parts) — fixed a real tool tier-gating bug
   (harvest_tier tags were never populated); Silent Gear's *native* Paxel
   gear type (a hand-rolled KubeJS version was built, boot-verified, then
   discarded once the native one was discovered — see the memory note
   below); gear utility traits (auto-smelt/AoE/reach/magnet); Building
   Wands; Sophisticated Backpacks + a separate "Miner's Pouch" line.
4. **Travel overhaul** (3 parts) — boats/Create Trains/Waystones
   teleportation, gated by tier via ProgressiveStages locks. Part 2 (air
   travel) originally shipped as Immersive Aircraft, then revised per user
   request to **Create Aeronautics** instead, gated via KubeJS recipe
   patches (`pack/kubejs/server_scripts/travel.js`) that reuse materials
   already tier-locked elsewhere in the pack, rather than explicit item
   locks — see DESIGN.md's travel overhaul section for the full ingredient
   mapping.
5. **World exploration overhaul** (3 parts) — Terralith (+TerraBlender
   +Lithostitched) for ~100 new vanilla-block biomes, When Dungeons
   Arise + Structory + 8 more YUNG's "Better X" mods for structure
   variety, `scripts/gen_structure_loot.py`-generated reward scaling
   (currency + tier-trigger materials + Apotheosis gems, scaled by a
   4-tier structure rarity bucket) across 55 chest loot tables, and
   tightened `structure_set` spawn spacing for stronghold/woodland
   mansion/end city (the three structures tied to explicit tier-gate
   items: End access, totems, elytra). See DESIGN.md's world exploration
   overhaul section for the full mod list and design rationale.
6. **TODO.md item 1 (ore veins)** — Create Ore Excavation added; its
   native Iron/Diamond/Netherite drill ladder mapped onto Andesite/Brass/
   Precision Age; 3 new vein types (allthemodium/vibranium/unobtainium)
   added for the late-game meta-material tier, gated behind the Netherite
   Drill. See DESIGN.md's "Ore veins via Create Ore Excavation" section.
7. **TODO.md item 2 (endgame automation deepening)** — a curated 5-tier
   TFMG milestone ladder (Aluminum→Steel→Petrochemical→Electrical→
   Combustion Age) mapped onto Tiers 5-9; the 3 "infinite" capstones
   (storage/energy/all-resources) turned out to already exist as
   fully-functional, recipe-less creative blocks in Create/Refined
   Storage — new survival recipes added and gated at Jovian Frontier
   instead of building custom infinite-behavior blocks. One disclosed,
   unfixed gap: `create:creative_crate` has no technical guard against
   duplicating a genuinely unique item. See DESIGN.md's "Post-Tier-4
   endgame automation deepening" section.
8. **TODO.md item 3 (duplicate-resource consolidation)** — AllTheOres'
   zinc/aluminum/lead/nickel and Stellaris' steel hard-consolidated onto
   Create/TFMG canonical items via redirected smelting/crafting/loot-table
   overrides + `dedup.js` tag cleanup; ATO overworld ore worldgen
   neutralized (nether/End kept, no canonical source there); closed a real
   tier-bypass hole on `tfmg:aluminum_ingot`. TFMG-vs-RefinedStorage
   silicon checked and left alone (genuinely different resources). See
   DESIGN.md's "Duplicate-resource consolidation audit" section.
9. **TODO.md item 7 (Create-native chunk loading)** — Create: Power Loader
   added, two tiers locked at Andesite/Brass Age; running-cost guardrail
   satisfied natively (force-loading stops when the kinetic network
   stops); FTB Chunks' own force-loading fully disabled via
   `pack/config/ftbchunks-world.snbt` (claims untouched). See DESIGN.md's
   "Block-based chunk loading via Create: Power Loader" section.
10. **TODO.md item 8 (leaderboards)** — `/leaderboard <wealth|tier|level>
    [players|teams]` chat command in a new `leaderboard.js`; wealth =
    coin count + genuinely-reachable Numismatics bank balance; tier =
    ProgressiveStages stage count; level = summed Pufferfish Skills
    per-category levels; teams via FTB Teams API, summed/maxed as
    appropriate. All three mod APIs wrapped with honest "unavailable"
    fallbacks, never a silent vanilla-XP substitute. See DESIGN.md's
    "Leaderboards: wealth / tier / level" section.

## TODO backlog (in progress)

`TODO.md` at the repo root has 8 user-scoped items from a planning session
— read it fully before picking up work. Items 1, 2, 3, 7, and 8 are done
(see above). Items 4, 5, and 6 (jetpack→creative-flight mobility,
discoverable Curios abilities, hostile/passive mob variety) are
**scaffolded but not implemented** — see "Wave-2 scaffolding" below for
exactly what's in place vs. still open. Implement in order unless told
otherwise, don't re-litigate decisions already recorded in the file, but
do still verify any named mod against the actually-installed jar before
building on it.

### Wave-2 scaffolding (mods added, mechanics NOT implemented)

An integrator pass (2026-07-10) added the 7 new mods items 4-6 need to
`pack/manifest.json`/`pack/mods.lock.json` and boot-tested them in, plus
added the jetpack tier locks item 4 needs — but did **not** implement any
of items 4/5/6's actual mechanics (that's still wave-2's job):

- **Item 4 (jetpacks)**: `create-stuff-additions` (mod id `create_sa`,
  4 native chestplate jetpacks: copper/andesite/brass/netherite) +
  `create-netherite-additions` (mod id `create_nj`, adds a Netherite
  Exoskeleton + its own second netherite jetpack). Tier locks added:
  copper→andesite_age, andesite→brass_age, brass→precision_age,
  **both** netherite jetpacks (`create_sa:netherite_jetpack_chestplate`
  AND `create_nj:netherite_jetpack_chestplate`)→induction_age (locking
  both closes a tier-bypass hole the same way item 3 did for aluminum).
  **GROUND-TRUTH FINDING for wave-2**: `create_nj`'s netherite jetpack is
  a duplicate of `create_sa`'s own native one (different recipe, same
  functional slot) - worth folding into TODO.md item 3's dedup pattern,
  not confirmed necessary since `create_nj` is also needed for its
  Exoskeleton. **Still open**: the Starforged Age creative-flight
  capstone itself (not started - no mod/mechanism chosen yet), and
  whether any intermediate jetpack rungs need KubeJS-scripted stat
  changes beyond the mod's own native behavior.
- **Item 5 (Curios)**: `artifacts` added (zero hard deps, Curios/
  cloth-config/JEI all soft-detected). **Nothing else done** - loot-table
  wiring into `scripts/gen_structure_loot.py`'s rarity tiers, the
  duplicate-combine upgrade mechanic, and the "no tier lock, loot-weight
  only" balance question are all still fully open.
- **Item 6 (mob variety)**: `creeper-overhaul` + its required deps
  `resourceful-config` and `resourceful-lib` (the latter needed at the
  **class level** - `NoClassDefFoundError` on `ResourcefulRegistries` -
  even though neither Modrinth's dependency metadata nor the mod's own
  `neoforge.mods.toml` declares it; found only via an actual boot-test
  crash, same pattern as this pack's existing geckolib/curios precedent
  for Ars Nouveau). Plus `borninchaos` (confirmed via its own jar:
  geckolib is genuinely optional there, Modrinth's metadata is wrong to
  call it required) and `naturalist` (geckolib 4.9.2 satisfies its
  `>=4.7` requirement). **Nothing else done** - no loot-table patching to
  the shared canonical drop set, no `mob_scaling.js` `MONSTER_TYPES`
  extension, no biome-appropriateness pass against the new Terralith
  biomes.

All 7 new mods are boot-tested clean as of this pass (third boot test,
after fixing the resourceful-lib gap above) - they load with no
`ModLoadingException`/`FATAL` and no new errors beyond one pre-existing-
pattern non-fatal WARN (`create_nj:netherite_flywheel_recipe` fails to
parse - a bug in that mod's own bundled recipe JSON, unrelated to
anything added this pass, doesn't block loading).

This is an unattended, self-resuming work session: each wakeup should
schedule the *next* wakeup (~4 hours out, via `CronCreate` with
`recurring: false` since `ScheduleWakeup` caps at 1 hour) *before*
starting any work, then read this file + `TODO.md`, then continue. Keep
working through items without stopping at each one's completion — only
stop if the list is exhausted or capacity runs out mid-task (in which
case, update this section with exactly what's mid-flight before you can't
anymore). **Scheduling gotcha learned the hard way**: a one-shot cron
pinned to the *current* minute has already passed by the time it's
created and will never fire — always pin it to a future time and sanity-
check with CronList.

**Orchestrator mode (user directive, 2026-07-10 ~00:05 UTC)**: the main
session now orchestrates; heavy implementation/research is delegated to
background subagents on the "sonnet" model via the Agent tool. Division
of labor: subagents write code/do research but never run git, never boot
the server, and never touch manifest.json/mods.lock.json/DESIGN.md/
HANDOFF.md/TODO.md; the orchestrator integrates their output, runs the
single boot test (one server, one port — boot tests can't run
concurrently anyway), commits each logical part separately, updates docs,
and adds any new mods to the manifest itself via resolve_mods.py/
build_server.py.

**Status as of the integrator pass (2026-07-10, ~00:35-00:47 UTC)**: the
4 sonnet subagents referenced above (items 3+8 implementation, items 4+5
and 6+7 research) have all completed and been integrated, boot-tested
(3 full boot cycles - items 3/7(partial)/8 together, then the completed
FTB Chunks config, then the 7 wave-2-scaffold mods), and committed. Items
3, 7, and 8 are now fully done (see "What's done" above). Items 4/5/6 are
scaffolded only (new mods in the manifest + jetpack tier locks) - see
"Wave-2 scaffolding" above for the exact boundary of what's in place vs.
still open.

**Next session should**: pick up items 4/5/6's actual mechanics using the
scaffolding + research briefs already in place (mods installed, deps
verified, jetpack items tier-locked) - no further mod-discovery research
should be needed for the mods already chosen, though item 4's creative-
flight capstone and item 5's content-mod choice for Curios still need
mod/mechanism decisions of their own (only `artifacts` was scaffolded per
the research brief's leading candidate; nothing was scaffolded yet for a
capstone mechanism). Same orchestrator/subagent division of labor as
before: subagents write code/do research, the orchestrating session runs
git/boot-tests/manifest edits/docs.

Full narrative and rationale for every decision lives in `DESIGN.md` —
that file, not this one, is the source of truth. `instructions.md` has the
original requirements plus a "Clarifications & Resolved Decisions"
appendix. `git log` has one detailed commit per part explaining what broke
and why, in order.

## If asked to keep building

- Read `DESIGN.md` fresh — don't assume anything from a prior session's
  summary is still accurate without checking.
- Boot-test methodology (used after every change in this project):
  `python3 scripts/build_server.py` (downloads/syncs `server/`), then
  `cd server && rm -f cmd_fifo && mkfifo cmd_fifo && export PATH=".../jdk-21.0.11+10/bin:$PATH"`,
  launch with `(tail -f cmd_fifo | timeout 120 sh run.sh nogui > /tmp/LOG 2>&1 &)`,
  poll for `Done (` / `Loading errors` / `ModLoadingException` in the log,
  grep for errors and stage-tag/recipe/material counts, then
  `echo "stop" > cmd_fifo` to shut down cleanly.
- Ground truth over assumption: verify against the actually-installed jar
  (decompile with `javap`/`jar tf`/`jar xf` under
  `.tools/jdk-21.0.11+10/bin`) rather than training-data memory of a mod's
  behavior — this has caught real bugs every single time it was done and
  missed several before it became habitual.
- Commit after each logical part with a detailed message (why, not just
  what) — this is what makes `git log` alone a usable resume point.

## Persistent memory

Project memory (survives across sessions, separate from this file) is at
`project_vanilla_plus_plus.md`, `feedback_autonomous_overnight_work.md` in
the auto-memory store. It's kept reasonably current but `git log` +
`DESIGN.md` are the authoritative source if the two ever disagree.
