# Handoff

**Status as of this note: RELEASE 1.0.0 SHIPPED.** All 8 originally-scoped
`TODO.md` items (1-8) plus items 4/5/6's actual mechanics, the release
client-optimization/QoL mod set, the L0/L1/L2 test suite, and both release
artifacts are implemented, tested, committed, and documented in `DESIGN.md`'s
"Release engineering" section. Items 9/10/11 (food overhaul, tick
accelerator, skill-tree overhaul) are fully scoped in `TODO.md`/`DECISIONS.md`
but explicitly DEFERRED POST-RELEASE — see "Post-release backlog" below.
Read `TODO.md` before doing anything else — it's the authoritative backlog.
`DECISIONS.md` at the repo root is the durable decision log for everything
decided in orchestrator-mode sessions after the original 8-item planning
pass; treat it as trusted input alongside `TODO.md`/`DESIGN.md`.

## Release 1.0.0

Artifacts (both gitignored build output, regenerate on demand — see
"Re-running the release pipeline" below):
- **Client**: `vanilla-plus-plus-client-1.0.0.mrpack` (~250 KB) — import
  into Prism Launcher.
- **Server**: `vanilla-plus-plus-server-1.0.0.zip` (~350 MB) — extract,
  read the bundled `README.md`, accept the EULA yourself (deliberately not
  pre-accepted), `sh run.sh nogui`.

Both build from `pack/VERSION` (currently `1.0.0`) via
`scripts/build_mrpack.py` / `scripts/build_server_bundle.py` respectively —
bump that one file at the next release cut, nowhere else.

### Re-running the release pipeline

```
python3 scripts/resolve_mods.py          # manifest.json -> mods.lock.json
sh scripts/tests/l0_boot_smoke.sh        # build + boot + baseline-diff the log
python3 scripts/tests/l1_selftest.py     # boot + /vpp_selftest + parse the result
python3 scripts/tests/l2_client_smoke.py # full client mod set via HeadlessMC
python3 scripts/build_mrpack.py          # client .mrpack
python3 scripts/build_server_bundle.py   # server .zip
```

L0/L1/L2 all exit nonzero on failure — safe to chain with `&&`. L2 needs the
HeadlessMC research instance at `/tmp/vpp-research/headlessmc/` +
`/home/ubuntu/.minecraft` (not part of this repo; a fresh environment would
need to redo that setup — see DESIGN.md's "Release engineering" section for
the exact working launch invocation, including the two harness-specific
flags (`sodium.checks.issue2561=false`, `--retries 3`) that took real
`javap` decompilation to discover).

### What this release's testing does NOT cover (read before assuming it's bug-free)

Rendering correctness (Create contraption/pulley/train visuals, GeckoLib
animation, Epic Fight combat animation, general UI/inventory layout —
including whether ImmediatelyFast 1.6.11 actually fixed the Staff-of-Physics
display bug reported at 1.6.10), a live client join (L3, deliberately
deferred — see below), multiplayer interaction, and live combat/economy
balance. See DESIGN.md's "The honest L2/L3 boundary" for the full statement
— it's restated there so it survives future summarization.

## Post-release backlog

- **L3 — live client join test.** Deferred from this release (unproven join
  mechanism against NeoForge's handshake, highest cost, least proven value
  of the 4 test layers). If picked up: use a separate test-only
  `server.properties` profile with `online-mode=false`, never the shipped
  default.
- **Items 9/10/11** (food overhaul, tick accelerator, skill-tree overhaul) —
  fully scoped in `TODO.md`/`DECISIONS.md`, not implemented. Don't start
  without being told to.
- **Rendering-correctness spot-check** — the L2/L3 boundary above means
  nobody has actually looked at this pack's GeckoLib entities, Create
  contraption visuals, or Epic Fight combat animations render correctly.
  Worth a manual pass before wider release, not blocking this 1.0.0 cut.
- **Residual Rhino const-in-loop risk** — this release's L1 development
  found the installed Rhino engine doesn't give `const`/`let` fresh
  per-iteration scoping inside `for(;;)` loops or try/catch blocks invoked
  from one (see DESIGN.md's "Release engineering" section for the full
  finding). Fixed everywhere it was actually hit
  (`selftest.js`/`leaderboard.js`), but two `for (const x of ...)` for-of
  forms elsewhere (`economy.js`'s `payCoins`, `selftest.js`'s own coin
  helper) were left unverified — worth a deliberate audit pass, not an
  emergency.

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
14. **Release 1.0.0** — 10 client-optimization/QoL mods (sodium,
    entityculling, immediatelyfast, moreculling, dynamic-fps, clumps, jei,
    xaeros-minimap, xaeros-world-map, appleskin); a 4-layer test suite (L0
    boot smoke, L1 `/vpp_selftest`, L2 HeadlessMC client smoke, L3
    deferred); `pack/VERSION`-driven client `.mrpack` + server `.zip`
    bundles. Fixed a real, previously-shipping bug found via testing
    (`noisiumed`'s Fabric-jar mis-resolution) and a Rhino const-in-loop
    scoping bug in `leaderboard.js`. See DESIGN.md's "Release engineering"
    section.

`DECISIONS.md` at the repo root is the durable decision log for
orchestrator-mode sessions (operating model, per-item research verdicts,
items 9/10/11's finalized specs, the full release test/bundling
architecture, standing implementation notes) — read it alongside
`TODO.md`/`DESIGN.md`; DESIGN.md's "Release engineering" section is the
canonical, detailed writeup of everything summarized above.

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
  `echo "stop" > cmd_fifo` to shut down cleanly. As of the 1.0.0 release,
  `sh scripts/tests/l0_boot_smoke.sh` formalizes exactly this (build + boot
  + baseline-diffed log + clean stop, single exit code) — prefer it over
  hand-rolling the sequence above for a plain pass/fail check;
  `scripts/tests/l1_selftest.py` additionally drives `/vpp_selftest` for a
  runtime data/registry/command sanity sweep. IMPORTANT: always stop a
  server you booted manually (`echo "stop" > cmd_fifo`, then confirm no
  `java`/`tail -f cmd_fifo` processes remain) before booting another one —
  a stale process still holding `server/world`'s lock will make the next
  boot fail with a `DirectoryLock` exception that looks like a real bug but
  isn't (hit and lost time to this during 1.0.0's L1 development).
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
