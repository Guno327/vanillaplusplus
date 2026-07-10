# Handoff

**Status as of this note: wave-2 complete. All 8 originally-scoped TODO.md
items (1-8) plus items 4/5/6's actual mechanics are implemented, boot-tested,
committed, and documented in `DESIGN.md`. Items 9/10/11 (food overhaul, tick
accelerator, skill-tree overhaul) are fully scoped and recorded in `TODO.md`
but explicitly DEFERRED POST-RELEASE per user directive — do not implement
them without being told to. Next focus is RELEASE PREP, not more features —
see "Release prep (current focus)" below.** Read `TODO.md` before doing
anything else — it's the authoritative backlog. `DECISIONS.md` at the repo
root is the durable decision log for everything decided in orchestrator-mode
sessions after the original 8-item planning pass; treat it as trusted input
alongside `TODO.md`/`DESIGN.md`.

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
11. **TODO.md item 4 (mobility)** — Create Stuff & Additions' native 4-tier
    jetpack ladder (copper/andesite/brass/netherite) mapped 1:1 onto
    Andesite/Brass/Precision/Induction Age; a Starforged Age (Tier 5)
    capstone grants item-free, stage-bound persistent `abilities.mayfly`
    via `mobility.js`, surviving death by construction since the grant is
    driven by ProgressiveStages stage membership, not an item/effect. Also
    closed the `create_nj` duplicate-netherite-jetpack tier-bypass hole
    wave-1 flagged, folded into `dedup.js`'s item-3 pattern. See DESIGN.md's
    "Personal mobility: jetpack -> persistent creative flight" section.
12. **TODO.md item 5 (Curios)** — Artifacts 13.2.1 wired into this pack's
    existing 4-tier structure-loot rarity buckets as its sole placement
    path (its own native loot injection silenced entirely); a 48-item
    curation table (ground-truthed, not the estimated 47); a
    duplicate-combine upgrade mechanic (`curios_upgrades.js`, 46 recipes)
    using Curios' own `curios:attribute_modifiers` component since
    vanilla's never applies in Curios slots. See DESIGN.md's "Curios as a
    discoverable/upgradeable player-ability system" section.
13. **TODO.md item 6 (mob variety)** — Creeper Overhaul + Born in Chaos
    (hostile) + Naturalist (passive fauna), every new mob's loot patched
    onto this pack's shared canonical drop set (32 entity loot overrides),
    unique weapons/armor/combat-stat charms stripped, `mob_scaling.js`'s
    `MONSTER_TYPES` extended with 61 new hostile ids. See DESIGN.md's
    "Hostile + passive mob variety, limited unique drops" section.

## Release prep (current focus)

All 8 originally-scoped `TODO.md` items (1-8) plus items 4/5/6's actual
mechanics are done (see "What's done" above) — the pack is feature-complete
for an initial release per user directive (2026-07-10 ~01:15 UTC). Three
further items (9: food overhaul, 10: tick accelerator, 11: skill-tree
overhaul) are fully scoped in `TODO.md`/`DECISIONS.md` but **explicitly
deferred to post-release** — don't implement them without being told to.

Priority order from here, per the user's own framing:
1. ~~Wave-2 integration of items 4/5/6~~ — **done, this pass.**
2. **Client-side test harness + functional test suite — architecture
   ADOPTED (`DECISIONS.md`, ~2026-07-10 02:15 UTC), NOT YET IMPLEMENTED.**
   GameTest was rejected (needs custom Java, this pack has none by design);
   protocol bots were rejected (confirmed dead end - NeoForge handshake
   doesn't cooperate). Adopted instead, in implementation order: **L0** boot
   smoke (`scripts/tests/l0_boot_smoke.sh` - formalize the grep discipline
   already used ad hoc every boot test in this project, against a
   documented known-noise baseline); **L1** a KubeJS `/vpp_selftest` command
   + runner (`l1_selftest.py`, via `cmd_fifo` or RCON) covering ~20
   data/parse/count/resolve assertions plus sell/leaderboard round-trips
   (the assertion list is sketched against expected KubeJS API surface, NOT
   yet verified against the installed jar - the implementing agent must
   verify each one and disclose any that Rhino can't actually reach); **L2**
   HeadlessMC client smoke (prototype-verified, artifacts at
   `/tmp/vpp-research/headlessmc/` - pinned launcher 2.9.0, note the repo
   moved to `headlesshq/headlessmc`) with the full `side != server` mod set,
   to catch client-only mixin crashes; **L3** an actual client join test,
   deliberately deferred until L0/L1/L2 are solid (unproven join mechanism,
   highest cost, least proven value so far). Watch-list once L2 exists:
   loaded-mods count, Create contraption/pulley/train rendering, GeckoLib
   entity visibility, Epic Fight animation playback, and a narrow
   Create-Aeronautics-Staff-of-Physics inventory-display bug reported at
   1.6.10 (confirm fixed at the installed 1.6.11).
3. **A release containing both a server bundle and a client bundle —
   architecture ADOPTED, NOT YET IMPLEMENTED.** `scripts/build_mrpack.py`
   already builds the client `.mrpack` (currently hardcodes version
   `0.9.0`). A new `scripts/build_server_bundle.py` is planned but not yet
   written: reuse `build_server.py`, zip `server/` minus
   `world/`/`logs/`/`cmd_fifo`, include `run.sh`/`libraries/`, and handle
   the EULA as an explicit first-run prompt documented in the bundle's
   README (a silent pre-acceptance was explicitly rejected). Versioning
   plan: a single `pack/VERSION` file read by both build scripts, embedded
   in both bundle filenames, bumped to `1.0.0` at the actual release cut.
   The shipped server bundle keeps `online-mode=true`; any L3 join testing
   must use a separate test-only `server.properties` profile with it
   flipped off, never the shipped default.

`DECISIONS.md` at the repo root is the durable decision log for
orchestrator-mode sessions (operating model, per-item research verdicts,
items 9/10/11's finalized specs, the full release test/bundling
architecture above, standing implementation notes) — read it alongside
`TODO.md`/`DESIGN.md` before picking up any of the above; it's more current
than this summary on the release-prep specifics.

**Serial-resource ownership still applies** if work resumes in
orchestrator/subagent mode: exactly one integrator agent owns git, `server/`
boots, `pack/manifest.json`+`mods.lock.json`, `pack/config/**`, and the docs
(`DESIGN.md`/`HANDOFF.md`/`TODO.md`) at a time; parallel agents get disjoint
file scopes and never touch those. This wave hit a live example of why that
matters — see `DECISIONS.md`'s operating-model notes and this session's own
checkpoint log (`/tmp/vpp-agent-checkpoints/wave2-integrator.md`) for the
concurrent-integrator race this pass detected and safely waited out rather
than fighting over git.

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
