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

## TODO backlog (in progress)

`TODO.md` at the repo root has 8 user-scoped items from a planning session
— read it fully before picking up work. Items 1-2 are done (see above).
Items 3-8 (duplicate-resource consolidation, jetpack→creative flight
mobility, discoverable Curios abilities, hostile/passive mob variety,
Create-native chunk loading, wealth/tier/level leaderboards) are fully
scoped with recorded decisions but not yet started — implement in order
unless told otherwise, don't re-litigate decisions already recorded in
the file, but do still verify any named mod against the actually-installed
jar before building on it.

This is an unattended, self-resuming work session: each wakeup should
schedule the *next* wakeup (~4 hours out, via `CronCreate` with
`recurring: false` since `ScheduleWakeup` caps at 1 hour) *before*
starting any work, then read this file + `TODO.md`, then continue. Keep
working through items without stopping at each one's completion — only
stop if the list is exhausted or capacity runs out mid-task (in which
case, update this section with exactly what's mid-flight before you can't
anymore).

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
