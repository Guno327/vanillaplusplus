# Decision Log

Running log of decisions made in orchestrator sessions that are not yet
reflected in TODO.md/DESIGN.md (agents transcribe from here at integration
time — this file is the durable source; conversation context is not).
Older decisions already committed live in TODO.md (items 1-8 scoping) and
DESIGN.md (implementation rationale); this file picks up from the
orchestrator-mode switch. Newest entries at the bottom of each section.

## Operating model (user directives, 2026-07-10)

- **Orchestrator mode** (~00:05 UTC): the main session makes decisions and
  orchestrates only — NO hands-on implementation by the orchestrator. All
  work is delegated to background subagents on the **sonnet** model. The
  user discusses new features with the orchestrator in the foreground
  while agents work.
- **Serial-resource ownership**: exactly one "integrator" agent at a time
  owns git, server boots, pack/manifest.json + mods.lock.json,
  pack/config/**, and the docs (DESIGN/HANDOFF/TODO). Parallel agents get
  disjoint file scopes and never touch those. Orchestrator adds nothing by
  hand; wave-N integrators fold parallel agents' output in, boot-test, and
  commit per logical part.
- **Decision recording + checkpointing** (~00:40 UTC): every decision gets
  recorded durably (this file); subagents must checkpoint progress
  regularly — after each pipeline stage / logical unit, append a dated
  entry to `/tmp/vpp-agent-checkpoints/<role>.md` (`mkdir -p` first)
  listing: stage completed, files written so far, verified facts, and the
  exact next step — so a killed/stalled agent's partial state is
  recoverable without re-deriving. Long-running agents also give interim
  status when pinged via SendMessage. Integrator commits remain the
  strongest checkpoints; the file protocol covers non-integrator agents
  who cannot commit.
- Scheduling (revised 2026-07-10 ~14:35 UTC, user call): each session
  schedules its successor wakeup for **5 hours after that session's own
  start** (first message), not a fixed ~4h cadence — usage windows are 5h
  from the first message, so the old ~4h spacing woke the session before
  its usage had reset. Add a few minutes' buffer past the exact +5h mark,
  pick an off-minute, use one-shot CronCreate. A one-shot cron pinned to
  the current minute never fires — always pin future, verify via CronList.
  Cron jobs are session-only (in-memory): if the session ends, the chain
  dies and the user must re-prompt.

## Items 4/5/6 (mobility / curios / mob variety) — research verdicts

Fully transcribed into DESIGN.md: "Personal mobility: jetpack -> persistent
creative flight" (item 4 — mod choice/runner-up rejection, chest-slot
contention, Starforged capstone mechanism), "Curios as a discoverable/
upgradeable player-ability system" (item 5 — mod choice, native loot
injection silencing, duplicate-combine design), and "Hostile + passive mob
variety, limited unique drops" (item 6 — Born in Chaos namespace gotcha,
charm-accessory stripping, spawn-predicate flag) sections.

## Items 9/10/11 (food / tick accelerator / skill-tree overhaul) — decisions

Item 9's finalized decisions (diet mechanic, Farmer's Delight ecosystem
adoption + rejections, tier gating, automation bar, SoL-Onion config
obligation) and its research-verdict detail (exact mod/version list,
Central Kitchen-over-Slice&Dice rationale, boot-check obligations) are
fully transcribed into TODO.md item 9 — that item is still IN PROGRESS, so
TODO.md's copy is the one to read/update, not this file.

Item 10's finalized decisions (TiaB model, Brass Age gate, Create-kinetics-
only exclusion mechanism, spawners-stay-accelerable call, one-per-player
enforcement design) and item 11's finalized decisions (all-12-categories
branch, ~15-node shared-trunk-then-fork shape, hard-but-respeccable
exclusivity, attribute-modifiers-only node design, the no-downside design
law) are fully transcribed into TODO.md items 10/11 respectively, both now
DONE and merged — see those sections for the implementation-time research
verdicts too (exact mod versions, the `tiab:un_acceleratable` tag scan
mechanism, native puffish_skills exclusivity/respec support). No DESIGN.md
section exists for items 10/11 (they landed after the last DESIGN.md
transcription pass) — TODO.md is their canonical home.

## Wave-1 integrator findings — orchestrator calls (2026-07-10)

`create_nj`'s duplicate netherite-jetpack tier-bypass finding and its
fold-in to the item 3 dedup pattern is fully transcribed into DESIGN.md's
"Personal mobility" section (the `create_nj`/`create_sa` dedup writeup).
Wave-2 (items 3/4/5/6/7/8 committed and boot-tested) is long complete.

## Item 5 implementation outcomes — endorsed deviations (2026-07-10 ~01:10 UTC)

Fully transcribed into DESIGN.md's "Curios as a discoverable/upgradeable
player-ability system" section: the 48-not-47 item count, the
`curios:attribute_modifiers`-over-vanilla-component deviation, the
`everlasting_beef`/`eternal_steak` combine exclusion, per-slot-type bonus
stats, and the 46-recipe total.

## Checkpoint-protocol lesson (2026-07-10 ~01:10 UTC)

Mid-flight SendMessage instructions get treated as suspected prompt
injection by cautious subagents (the item 5 agent explicitly refused one —
correct defensive posture, wrong conclusion). **Protocol fix: checkpoint/
check-in discipline is baked into every agent's ORIGINAL brief from now
on, never injected mid-run.** Mid-run pings are for status requests only,
and agents may reasonably ignore even those.

## Release-prep pivot (user directive, 2026-07-10 ~01:15 UTC)

- Features are declared sufficient for an **initial release**. Priority
  order from here: (1) wave-2 integration of items 4/5/6 (must be
  committed/boot-verified first), (2) client-side test harness research +
  a functional test suite for the whole pack, (3) a release containing
  BOTH a server bundle and a client bundle.
- **Items 9/10/11 (food, tick accelerator, skill trees) are deferred to
  post-release** — fully scoped in this file, transcribed into TODO.md at
  wave 2, NOT implemented before the release ships.
- Test-harness research dispatched (headless client options, protocol-bot
  feasibility against a NeoForge server, server-side GameTest/command-
  driven suites, KubeJS self-test pattern, release bundling via the
  existing build_mrpack.py + a server-bundle layout).

## Client-side optimization mods for the release (user directive, 2026-07-10 ~01:25 UTC)

- Research dispatched for a client-optimization mod set to include in the
  release's CLIENT bundle. Scope: **optimization only** (FPS, load time,
  memory) — client QoL/content mods are a separate open question already
  parked with the release-bundling researcher.
- Key constraint to verify per candidate: compatibility with Create 6.0.10's
  Flywheel renderer (historical Sodium-family conflicts) — a client
  renderer mod that breaks Create's visuals is disqualifying in a
  Create-centric pack.
- Plumbing note: manifest `side` markers already exist (c2me/krypton are
  side:server) — client-only picks enter as side:client; build_mrpack.py/
  build_server.py side-handling to be verified by the implementing wave.
- Validation dependency: client-only mods cannot be boot-tested on the
  dedicated server at all — their verification rides on the headless
  client harness (L2 smoke) being researched in parallel.

## Known-acceptable boot noise (baseline for the release test suite, as of wave-1 completion 2026-07-10)

The L0 boot-smoke layer must treat these as EXPECTED (non-failing), all
verified non-fatal across 4 clean wave-1 boots — a test that fails on any
of these is miscalibrated; a test that misses NEW warnings beyond these is
too loose:
- `create-netherite-additions` bundled `netherite_flywheel_recipe.json`
  WARN (empty smithing template array) — upstream data bug in that mod.
- `epicfight` "Error while deserializing datapack for
  minecraft:wooden_sword: No value present" WARN.
- `c:tools/*` + `minecraft:enchantable/*` missing-tag-reference ERRORs
  (pre-existing, Phase 3-era, cosmetic).
- When Dungeons Arise's 2 broken advancement JSONs; YUNG's Better End
  Island's `bei_ExtraDragonFight` NBT ERROR on fresh worlds.
- RuntimeDistCleaner / client-class mixin noise on a dedicated server
  (Sodium/VulkanMod/Quark/Starlight compat hooks no-op'ing).

## Orchestration lesson: one integrator at a time, gated on completion NOTIFICATION (2026-07-10)

Wave-2's integrator was spawned while wave-1's was still finalizing (its
HANDOFF edits were visible but its completion notification hadn't
arrived). Both handled it gracefully — wave-1 surgically excluded wave-2
agents' files from its commits (verified via git log --name-only) — but
two concurrent integrators on git/server is a collision risk that worked
out rather than a safe pattern. **Rule going forward: never spawn the
next integrator until the previous one's completion notification has
actually arrived.**

## Item 11 (skill trees) — research verdicts, recorded as the implementation blueprint (2026-07-10 ~01:45 UTC; deferred post-release)

All source-verified against puffish_skills 0.18.0 (pufmat/skillsmod branch
1.21, exact version match), puffish_attributes 0.8.2, epic-fight 21.17.3.1,
ars_nouveau 5.12.1, and the shipped vanilla 1.21.1 data jar.

- **Hard exclusivity is NATIVE**: connections.json supports a second
  top-level `exclusive` group (bidirectional/unidirectional pairs) beside
  `normal`; each skill has `required_exclusions` (default 1). Minimal
  design: ONE bidirectional exclusive edge between the two fork children
  (pathA node1 ↔ pathB node1) — the rival path's remaining nodes stay
  locked via normal prerequisites. Exclusion state re-evaluates
  dynamically, which is what makes respec work. No KubeJS enforcement
  needed.
- **Respec**: the boot-log gamerules (skillReplaceCooldown/
  maxPassiveSkills/keepSkills) are EPIC FIGHT's separate hotbar-skill
  system — a red herring, do not touch. Real mechanism: public
  `net.puffish.skillsmod.api.SkillsAPI` → Category.getSkill(id).lock(player);
  points auto-refund (spent points are computed live from unlocked set).
  **Correctness gotcha: unlocked nodes are never re-validated against
  prerequisites — a respec routine MUST lock all 5 nodes of the abandoned
  path, not just the fork node**, or orphaned nodes keep granting rewards.
  Implement as a KubeJS respec command/item (new skill_respec.js).
- **Epic Fight crux — flagship fast-vs-deliberate is implementable,
  attributes-only, via VANILLA attributes**: `generic.attack_speed`
  literally multiplies Epic Fight's attack-animation playback rate
  (AttackAnimation.getPlaySpeed reads the vanilla attribute), and
  `generic.attack_damage` flows through vanilla Player.attack() which
  Epic Fight reuses. **LANDMINE: do NOT put `epicfight:` attributes
  (impact/armor_negation/stamina/...) into puffish rewards** — Epic Fight
  attaches them via a raw mixin bypassing the DefaultAttributeRegistry
  that puffish's AttributeReward validation checks; high confidence they
  hard-fail datapack load. (Optional future workaround if ever wanted:
  KubeJS SKILL_UNLOCK/SKILL_LOCK listeners mutating the live
  AttributeInstance directly. A 30-second boot test with one dummy
  epicfight:impact reward node would settle it.)
- **Attribute aliasing note**: `puffish_skills:player.X` ids in the
  current generator are valid — both that form and `puffish_attributes:X`
  resolve to the same attribute (BuiltinJson namespace rewrite + the
  attributes mod's own player.-prefix aliases).
- **12-category path table (verified ids only; A = cadence/utility,
  B = power/control)**:
  swords A attack_speed+sword_damage / B attack_damage+knockback;
  daggers A attack_speed(larger)+movement_speed / B luck+melee_damage;
  greatswords A attack_speed(modest) / B attack_damage+max_health+knockback;
  longswords A attack_speed+movement_speed / B attack_damage+melee_damage;
  spears A knockback+attack_speed / B entity_interaction_range(reach)+attack_damage;
  tachi A attack_speed+movement_speed / B attack_damage+luck;
  bows A bow/crossbow_projectile_speed / B ranged_damage;
  magic A ars_nouveau mana_regen_bonus / B spell_damage_bonus+max_mana;
  mining A mining_speed+pickaxe_speed / B fortune;
  running A sprinting_speed / B jump+step_height;
  swimming A water_movement_efficiency / B oxygen_bonus+submerged_mining_speed;
  building A block_break_speed / B block_interaction_range+step_height.
- **Generator changes**: branch layout coordinates (trunk 5 nodes, two
  parallel 5-node columns), one exclusive edge per category, 3 reward
  dicts per category (trunk/A/B), XP curve ~+50% for 15 nodes (retune or
  accept longer grind — balance call open), plus skill_respec.js.
- Open balance calls for playtest: XP pacing, respec cost friction.

## Client-optimization set — ADOPTED for the release client bundle (orchestrator call, 2026-07-10 ~02:00 UTC)

Six mods, zero new hard deps (cloth-config already installed):
- `sodium` 0.8.12+mc1.21.1 (side:client) — SHIP IT. Evidence chain:
  Create 6.0.10's bundled Flywheel 1.0.6 jar-in-jar declares
  `sodium [0.6.0-beta.2,)` as an optional CLIENT dep in its own toml AND
  ships real SodiumCompat classes — first-party support, not hearsay.
- `entityculling` 1.10.5 (client), `immediatelyfast` 1.6.11+1.21.1-neoforge
  (client), `moreculling` 1.0.8 (client), `dynamic-fps` 3.11.4 (client),
  `clumps` 19.0.0.1 (side:both — matches the ModernFix/FerriteCore
  convention). Internal compat matrix verified: only one renderer
  replacement in the set.
- **Excluded**: badoptimizations (documented Epic Fight freeze issue —
  the pack's whole combat system; too risky for an initial release);
  embeddium (superseded, Sodium-incompatible); enhanced-block-entities
  fork (single-maintainer AT into BE rendering, no Create evidence).
- **Deferred post-release**: iris shaders (beta-only on NeoForge 1.21.1 +
  needs a third compat mod still actively patching Create bugs).
- **MoreCulling contingency, decided now**: its toml's minecraft range
  `[1.21,1.21.1)` textually EXCLUDES 1.21.1 (exclusive upper bound)
  despite Modrinth listing it for 1.21.1 — #1 client-boot check. If it
  fails to load, DROP it from the set (don't pin/patch around it).
- **Config obligations for the implementing wave**: pre-populate
  EntityCulling's whitelist for Create pulleys (named in the mod's own
  docs) and GeckoLib-animated entities (Ars Nouveau familiars, Born in
  Chaos, Naturalist) BEFORE first client test; verify
  build_mrpack.py/build_server.py actually honor side:client (client
  bundle includes, server excludes).
- Client-harness watch-list (L2 smoke): loaded-mods list contains all 6;
  Create contraption/pulley/train rendering; GeckoLib entity visibility;
  Epic Fight animation playback; ImmediatelyFast + Create Aeronautics
  Staff of Physics inventory display (narrow reported bug at 1.6.10,
  confirm fixed at 1.6.11).
- Implementation queues behind wave-2 (one-integrator rule) as part of
  the release wave.

## Release test + bundling architecture — ADOPTED (orchestrator calls, 2026-07-10 ~02:15 UTC)

The L0/L1/L2/L3 test-layer design, bundle contents, and versioning scheme
decided here are fully transcribed (as-built, with real bug findings) into
DESIGN.md's "Release engineering" section — see that section rather than
this one for current detail. Two rejected-alternative calls worth keeping
since DESIGN.md only references them, not restates why: **GameTest
rejected** (needs custom Java; pack has none by design). **Protocol bots
rejected** (NeoForge handshake, confirmed dead end).

## Client QoL mods — user decision (2026-07-10 ~02:20 UTC)

All three adopted for the release client bundle: **JEI** (recipe viewer —
near-mandatory given the pack's recipe-gating identity; several installed
mods ship optional JEI integrations that light up for free), **Xaero's
Minimap + World Map** (exploration QoL for the ~100-biome/structure-hunt
overhaul), **AppleSkin** (pulled forward from the deferred item 9 food
stack). Implementing wave verifies exact slugs/versions/side markers
against jars per standing protocol, and checks whether any want a
server-side presence for full functionality (JEI recipe sync, Xaero's
optional server component) — side:both is acceptable where the jar
supports it, client-only otherwise.

## Acceleration wave during release cut (orchestrator calls, 2026-07-10 ~02:50 UTC)

While the release integrator owned main/server, items 10/11 were
pre-implemented in git worktrees (static validation only, no boots, no
main-tree writes) for a post-release integrator to merge — see "Item 10/11
pre-built branches + post-release merges" below and TODO.md items 10/11
for the outcome (the provisional
balance calls made to unblock item 11 — XP formula unchanged, respec
initially free — are superseded by the actual merge; still open per GitHub
issue #1). The noisiumed Fabric-jar bug found during this wave is
transcribed into DESIGN.md's "Release engineering" section.

**Still-relevant operational note for any future L3 work**: L3
join-mechanism research must run against its own `/tmp` server copy (a
different port than the shipped default, e.g. 25566) with
`online-mode=false` (test-only profile only, never the shipped default)
and its own isolated HeadlessMC game dir — explicitly not `~/.minecraft`
(used by L2) or the repo's `server/`.

## Item 10/11 pre-built branches + post-release merges (2026-07-10)

Items 10/11 were pre-implemented on worktree branches
(`worktree-agent-a77d7c3d4e95059c7` for item 11, 2 commits;
`worktree-agent-ae58d0ccfdfb4ce35` for item 10, 3 commits — neither
worktree deleted, both retained), static-validated only, then merged into
`main` one at a time with a full L0+L1 boot test between (item 11 first as
pure additive data, item 10 second). **Full merge account — including the
real Rhino-scoping bug the item-10 boot test caught and fixed forward
(commit `2e60738`), exact commit hashes, and post-fix L0/L1 results — is
transcribed into TODO.md items 10/11; that's the current source, not this
entry.**

Ground-truthed implementation facts not restated in TODO.md (kept here
since they exist nowhere else): item 10's exact one-per-player refund
recipe (3 gold, 2 diamond, 2 lapis, clock, glass bottle); KubeJS's
`ItemCraftedKubeEvent` confirmed NOT cancellable and NeoForge confirmed to
fire the craft event *before* the item reaches the inventory (verified in
`ResultSlot` bytecode), both of which shaped the void+refund enforcement
design; item 11's endorsed deviations that `/respec` uses 12 literal
subcommands (no `Commands.argument` precedent in this codebase to verify
unbooted) and `Skill$State` is compared via string rather than nested-class
loading.

**L2 HeadlessMC client harness checked and found not applicable** to
either branch's in-game-only checklist items: it's a pure mod-set-assembly
+ launch + crash-detection smoke test with no bot/scripted-action
capability, so it structurally cannot exercise unlock/respec/craft
behavior. Needs-in-game-verification items for both branches now live as
GitHub issues **#1** (item 11) and **#2** (item 10) — see "GitHub as
ground truth" below.

## GitHub as ground truth (2026-07-10, user directive)

The project's private GitHub repo (`https://github.com/Guno327/
vanillaplusplus`, remote `origin`) is now the ground truth for outstanding
bugs and needs-in-game-verification items, superseding this file's own
lists for that purpose going forward:

- **Issues supersede the needs-in-game-verification lists.** The "Item
  10/11 pre-built branches + post-release merges" section above's two
  needs-in-game-verification items (item 11's skill-tree/respec checks,
  item 10's Time-in-a-Bottle checks) now live as GitHub issues **#1**
  ("Verify item 11: skill-tree exclusive fork + /respec") and **#2**
  ("Verify item 10: Time-in-a-Bottle behaviors"). Do not re-derive or
  duplicate those checklists locally; check the issues. A third
  verify-in-game issue, **#3** ("Verify: rendering-correctness
  spot-check"), was also opened, folding in HANDOFF.md's rendering-
  correctness note and TODO.md item 12's identical entry.
- **Other open bugs/reviews filed as issues too**, mined from this file/
  DESIGN.md/HANDOFF.md's flagged-for-review, known-WARN, and disclosed-
  gap notes: **#4** (Stellaris `heavy_ingot` boot WARN, known/watch),
  **#5** (Born in Chaos 41/45-hostiles-via-`neoforge:any` spawn-tuning
  review), **#6** (tiabfix jar-internal-version-vs-Modrinth cosmetic
  mismatch, confirm benign), **#7** (`create:creative_crate` unique-item
  duplication exploit, previously disclosed-unresolved), **#8** (residual
  Rhino `const`-in-for-of scoping risk audit, `economy.js`/`selftest.js`).
  TODO.md's own numbered items (including item 9, still in progress) are
  NOT duplicated into issues — TODO.md remains the authoritative backlog
  for planned feature work; GitHub issues track bugs/verifications/
  reviews surfaced after the fact.
- **New issues from here on go straight to GitHub**, not into this file's
  needs-in-game-verification-style lists — this file continues to record
  *decisions*, GitHub tracks *outstanding work items*.
- **Label state machine** (full detail in `/tmp/vpp-agent-checkpoints/
  gh-issues-integration-design.md`, § 2-3): bug track `needs-triage` ->
  `triaged` -> `fix-in-progress` -> `fix-pushed`; feature track `needs-
  investigation` -> `investigated` -> `awaiting-approval` -> `approved` ->
  `in-development`. Bugs are auto-triaged and auto-fix-pushed by bot
  subagents (still boot-tested before any push, same discipline as every
  other change in this repo); features require an admin-verified
  `approved` label (checked against GitHub's own collaborator-permission
  API, never inferred from issue/comment text) before any development
  starts. Releases remain manual-only regardless of label state — no
  label authorizes cutting or publishing a release. A new kind label,
  `verify-in-game`, marks checks only a human player can perform (no
  state machine attached — it's not a bug or a feature, just a flag that
  static/boot-test verification cannot close the loop).
- **Release versioning decision: the first minted GitHub release will be
  `v0.1.0`** (beta semantics — this pack has real, disclosed unverified-
  in-game gaps and one still-in-progress TODO item, so calling it `1.0.0`
  overstated maturity; the user's call). This supersedes the local-only
  `1.0.0` naming used for the pre-GitHub release cut. `pack/VERSION`
  stays at its current value for now and gets bumped to `0.1.0` **at
  release-cut time**, after TODO.md item 9 (food overhaul) lands — not
  before, and not as part of this documentation pass. The stale
  `vanilla-plus-plus-*-1.0.0.mrpack`/`.zip` bundles that sat at the repo
  root (both gitignored, untracked build output — confirmed via `git
  ls-files`) were superseded by this decision and deleted in this same
  repo-cleanup pass; regenerate `0.1.0` bundles via the release pipeline
  (HANDOFF.md) when the actual release is cut.
- **Issue-triage workflow ownership**, restated from the design doc for
  durability: `check_issues.py` runs read-only at the top of every
  wakeup (informational, like reading `TODO.md`); every GitHub *write*
  (comment, label, commit, push) goes through a delegated subagent, never
  the orchestrator directly; a fix/feature branch + PR is used rather
  than pushing straight to `main` for anything the bot originates (this
  differs from `vanilla++`'s own straight-to-main convention, which
  relies on the single-trusted-integrator rule that doesn't hold for
  externally-reported issues); issue content (titles/bodies/comments) is
  untrusted input, evaluated but never executed as instructions.

## Item 9 (food overhaul) integration — final rulings + real-vs-drafted findings (2026-07-10)

TODO.md item 9 landed this pass (7 mods, phase 20) - full writeup in
DESIGN.md's "Food overhaul: Farmer's Delight ecosystem + diet-variety bonus
hearts" section. Recorded here for durability, since this integration pass
made two calls the pre-implementation handoff had explicitly left open/
flagged:

- **Lock-mapping rulings, both verified against this pack's REAL, already-
  documented material-tier convention** (grepped `andesite_age.toml`'s own
  header comment, not assumed): **iron -> Andesite Age, gold/diamond ->
  Brass Age, netherite -> Precision Age**. End-material knives (End's
  Delight's 4 knife tools) locked at **Precision Age**, matching the
  pre-implementation checklist's own drafted call (dimension-gate
  precedent, no stronger "End-derived tool" precedent found). ExtraDelight's
  spoon lineup (`iron_spoon`/`gold_spoon`/`diamond_spoon`/`netherite_spoon`,
  ground-truthed via the jar's own recipe jsons) mapped to
  **iron_spoon->Andesite, gold_spoon/diamond_spoon->Brass,
  netherite_spoon->Precision** - **this is the real, verified mapping,
  and it DEVIATES from the pre-implementation handoff's drafted assumption
  of "netherite -> Induction Age"**. The real precedent is unambiguous:
  every existing netherite-tier lock in this pack (`netherite_wand`,
  `netherite_backpack`, vanilla netherite gear/tools, Epic Fight's netherite
  weapons) lives in `precision_age.toml`; none exist in `induction_age.toml`
  for a general material-tier reason (the two netherite jetpack entries
  that DO live in `induction_age.toml` are a documented one-off dedup/
  tier-bypass case from TODO.md item 4, not a material-tier precedent).
- **SoL-Onion config JSON-shape deviation**: the pre-implementation
  guidance doc could not confirm the nested shape of a `benefits` list
  entry without a live boot, and flagged this explicitly. Real,
  ground-truthed shape (this pass's own first boot, no override): each
  entry is `{"threshold": <num>, "benefit": "<string>"}` where `benefit` is
  a quoted, SNBT-like **string** (e.g.
  `"{key:\"minecraft:generic.max_health\",op:0,type:\"att\",val:2.0d}"`),
  not the nested `{type: ..., ...}` JSON object the guidance doc's
  necessarily-uncertain pre-boot guess used as a placeholder shape. The
  actual edit reused the generated file's own real stock MAX_HEALTH
  `benefit` string verbatim across all 8 new threshold entries, per the
  guidance doc's own "reuse the template" instruction - this worked exactly
  as recommended, only the shape guess itself was inaccurate before a real
  boot could confirm it.
- **A real KubeJS/Rhino sandbox limit, found and fixed during boot-testing,
  not anticipated by the pre-implementation handoff**: this pack's
  installed KubeJS build (`kubejs-neoforge-2101.7.2-build.368.jar`) ships
  its own `kubejs.classfilter.txt` that blocks `net.neoforged.fml`
  wholesale AND, more restrictively than the food_selftest.js draft
  assumed, blocks `java.nio` and `java.io` almost entirely too (only
  `java.nio.ByteOrder`/`java.io.Closeable`/`Serializable` re-allowed) - so
  there is no in-JVM path at all to read an arbitrary server-relative file
  (like `config/solonion.json`) from this pack's KubeJS sandbox, not just
  the `FMLPaths` call the script originally tried. Fixed: mod-loaded checks
  now use the `Platform` global KubeJS itself registers
  (`Platform.isLoaded(modid)`, a pre-bound scripting global the class
  filter doesn't gate - confirmed via `BuiltinKubeJSPlugin.class`'s own
  binding registration) instead of the blocked `ModList` class; the
  config-runtime check in `/vpp_food_selftest` now honestly `SKIP`s
  (documented why) instead of a permanent, unfixable `FAIL` - actual
  runtime verification of `config/solonion.json` is done externally by the
  release integrator reading the file directly post-boot (confirmed:
  `detriments: []`, `resetOnDeath: false`, `trackedFoodDiversityDecay:
  false`, `trackCount: 150`, all 8 benefit thresholds present - while the
  real booted server process was still running).
- **A second, genuinely new but benign upstream bug**, added to
  `scripts/tests/l0_boot_smoke.sh`'s known-noise baseline: Farmer's Delight
  1.3.2's own bundled optional Silent Gear integration recipe
  (`farmersdelight:integration/silentgear/cutting/netherwood`) references
  an unregistered custom ingredient type
  (`farmersdelight:tool_action`/`neoforge:ingredient_serializer`) - a real
  upstream FD data bug, not this pack's own scripting. `RecipeManager` logs
  one `Parsing error loading recipe...` and skips just that recipe (a
  decorative Silent-Gear-flavor variant, no core food chain affected); boot
  reaches `Done(` clean regardless.
- Boot-check obligations all run for real (not just planned): L0 (87 server
  mods, 0 KubeJS errors/warnings, no unbaselined WARN/ERROR), L1 (17/17, 4
  skipped, unaffected), `/vpp_food_selftest` (6/6, 1 honest skip), SoL-Onion
  detriments/reset/decay/trackCount verified empty/correct at real runtime,
  Terralith wild-crop generation confirmed structurally (real biome tag
  membership + FD's own biome_modifier tag/temperature filter read directly
  from the jar), CCK Saw-automation coverage ground-truthed against all 222
  `farmersdelight:cutting` recipes across the 3 delight jars.

## NixOS flake + module for the dedicated server (2026-07-10)

Added `flake.nix` + `nix/module.nix` (`nixosModules.default`) + `nix/release.json`
+ `scripts/update_nix_release.py` so the server can run as a systemd service on
NixOS, deployed from a **minted GitHub release**, never this repo's working tree.
Full writeup in README.md's "Running on NixOS" section; decisions/rationale not
restated there:

- **Release pinning**: `nix/release.json` (repo/tag/version/assetName/assetId/
  assetApiUrl/size/sha256 (SRI)/sha256Hex/neoforgeVersion) is committed and
  regenerated by `scripts/update_nix_release.py` at every release cut (verified
  against the real `v0.1.0` release: downloaded the actual uploaded asset bytes
  back via the GitHub API — `Accept: application/octet-stream` on
  `/repos/Guno327/vanillaplusplus/releases/assets/472660547` — confirmed size
  378792450 bytes matches the API's own record and the working-tree copy's hash,
  sha256 `56056b4edc576af294f5775e90572f1309086f747f68274ea6d3843cca1dce1e`,
  auto-detected `neoforgeVersion` 21.1.235 from the zip's own
  `libraries/net/neoforged/neoforge/<version>/unix_args.txt` path). **Release
  pipeline obligation, added to HANDOFF.md**: run
  `python3 scripts/update_nix_release.py` (needs a GitHub token — env var,
  `--token`, or `gh auth token`) after every mint and commit the updated
  `nix/release.json`.
- **Private-repo asset fetch — researched, then deliberately NOT shipped as an
  automated mechanism (mid-flight user/coordinator pivot)**: nixpkgs' `fetchurl`
  has a real `netrcPhase`/`netrcImpureEnvVars`/`curlOptsList` mechanism built
  exactly for authenticated fetches without baking secrets into the store —
  ground-truthed against real nixpkgs master source (`pkgs/build-support/
  fetchurl/{default.nix,builder.sh}`), not memory: `netrcPhase` writes a `netrc`
  file into the FOD build's own `$PWD`, `builder.sh` auto-adds `--netrc-file
  "$PWD/netrc"` to its `curl` invocation, and `netrcImpureEnvVars` forwards named
  env vars from the invoking Nix daemon's own environment into the sandboxed
  build. This is a genuinely different subsystem from `nix.conf`'s
  `netrc-file`/`access-tokens` settings (those cover Nix's *own* internal
  downloader — flake-input/`fetchTarball`/substituter fetches — and never touch
  `pkgs.fetchurl`'s builder.sh, which shells out to a literal `curl` binary and
  knows nothing about `nix.conf`). **However**: `nix` could not be installed in
  this project's sandboxed dev environment at all (no root — a single-user
  install got as far as needing `mkdir -m 0755 /nix && chown` via sudo, which
  failed; `mkdir /nix` directly also failed, Permission denied on `/`), so this
  mechanism was never actually exercised end-to-end (no real `nix build` through
  a real nix-daemon with a token-bearing environment). Per explicit direction
  ("don't ship an untested fetcher as an option"), it was **cut entirely** rather
  than shipped as an unverified secondary option — the module's only supported
  path is a manually downloaded release zip
  (`services.vanillaplusplus.serverArchive`, required, a plain host path or Nix
  path literal). README documents the researched-but-unshipped mechanism
  briefly for anyone who wants to pick it back up later. The SEPARATE concern of
  authenticating to fetch *this flake itself* from the user's own system flake
  (private-repo `github:`/`git+https` input) is unaffected by this and still
  documented (git+https with a token, `nix.settings.access-tokens`, or SSH).
- **State-preserving sync**: the module's `ExecStartPre` script unzips
  `serverArchive` into an isolated `/tmp` staging dir (`PrivateTmp=true`, so no
  Nix-store duplication of the ~380MB bundle on top of its unpacked copy in
  `dataDir`) then `rsync -a --delete` into `dataDir`, excluding `world/`,
  `logs/`, `crash-reports/`, `server.properties`, `eula.txt`,
  `user_jvm_args.txt`, `cmd_fifo`, and its own stamp file — so upgrades refresh
  `mods/config/kubejs/defaultconfigs/libraries/run.sh/run.bat` but never touch
  runtime state. Change-detection is a cheap `stat` size+mtime fingerprint of
  the archive file (skips the unzip+rsync entirely when unchanged, rather than
  relying on a Nix-level version string — works equally for pinned releases and
  custom/local zips). `server.properties` is merged (nix-declared
  `serverProperties` keys always win, everything else already on disk survives)
  rather than overwritten, seeded from the shipped default only on a genuinely
  first-ever boot. `eula.txt` and `user_jvm_args.txt` are fully regenerated from
  nix-declared options every start (not "state" — always exactly what's
  configured). Stop mechanism replicates this repo's own dev boot-test tooling
  exactly (a `cmd_fifo` + `echo stop`, per `HANDOFF.md`'s validated clean-shutdown
  pattern) rather than relying solely on `SIGTERM`, since that's the one
  mechanism this project has actually exercised and confirmed doesn't leave a
  stale `world/` lock.
- **Validation status — stated plainly, not claimed as tested**: `nix flake
  check`/`nix build`/`nixos-rebuild` were never run — `nix` is not installable in
  this sandbox (see above). The flake/module were hand-reviewed (brace/paren
  balance checked programmatically, every Nix antiquotation in the generated
  shell scripts traced by hand, `lib.types.path`/`nullOr`/`fetchurl`'s real
  params all cross-checked against fetched nixpkgs source rather than memory)
  but this is reviewed-but-untested, not verified-working. Flagged prominently
  in README.md's "Running on NixOS" section too.
- **`jdk21_headless`** confirmed present on `nixos-25.11` (the flake's pinned
  nixpkgs branch — confirmed to exist via the GitHub API at write time, with
  `backport-*-to-release-26.05` branches existing too implying 25.11 is the
  current numbered stable release) by fetching and grepping the real
  `pkgs/top-level/all-packages.nix` from that branch.

## Bug-triage wave 1 — GitHub issues #4/#6/#7/#8 (2026-07-10)

Worked the bug-triage queue end to end (needs-triage -> triaged -> [fix-
in-progress -> fix-pushed | closed as benign/accepted] for each), per
`HANDOFF.md`'s boot methodology and this file's "GitHub as ground truth"
label state machine. Every root cause below was re-derived against the
actually-installed jars/scripts under `.tools/jdk-21.0.11+10/bin`
(`jar`/`javap`), never assumed from the issue text or prior narrative —
two of the four turned out to need real correction to what was
previously on record.

- **#6 (tiabfix version string) — CLOSED, confirmed benign, no code
  change.** `server/mods/tiab-entity-fix-1.0.3.jar`'s sha1/sha512/
  filesize match `mods.lock.json`'s pin exactly; its own `neoforge.mods.
  toml` really does say `version = "1.0.0"` (cosmetic bug in the
  author's build). Modrinth's own changelog API confirms 1.3.0 = "All
  crashes have been fixed" vs 1.0.0 "Initial Release" — the pinned jar
  is the improved one despite the stale internal string. Neither `tiab`
  nor `tiabfix`'s own toml references tiabfix's version in any
  dependency range, and no update-checker mod exists in this pack — zero
  functional or dependency-resolution consequence either way.
- **#4 (Stellaris `heavy_ingot` WARN) — CLOSED, FIXED (previously
  mischaracterized as benign-cosmetic noise; ground truth found a real,
  narrow gameplay effect).** `tfmg_stellaris_compat`'s own loot-modifier
  JSON still references `stellaris:heavy_ingot`, an item renamed
  upstream to `stellaris:heavy_metal_ingot` (confirmed absent/present
  respectively in the actually-installed `stellaris-1.21-neoforge-
  1.4.25.jar`). The stale key wasn't just log noise: `stellaris:pumpjack`'s
  own loot table drops 2x `heavy_metal_ingot` on break, and because the
  compat mod's replacement list never matched the old id, that drop was
  never being converted to `tfmg:aluminum_nugget` like every sibling
  entry in the same list already is. Fixed via a KubeJS datapack override
  at `pack/kubejs/data/tfmg_stellaris_compat/loot_modifiers/
  replace_stellaris_loot.json` (same override mechanism already used
  elsewhere in this pack) correcting the one stale key. Removed the now-
  permanently-dead `stellaris:heavy_ingot` pattern from `scripts/tests/
  l0_boot_smoke.sh`'s known-noise baseline and from this file's own
  boot-noise list above — L0 re-run confirms the WARN is gone entirely,
  replaced by the mod's own INFO log showing the corrected mapping.
  Commit `976105c`.
- **#8 (Rhino `const` audit) — CLOSED, FIXED, and the bug's own
  documented mechanism corrected.** Ground-truthed the installed Rhino
  engine directly (`server/mods/rhino-2101.2.7-build.85.jar`) with a
  standalone Java harness against its own `Context`/`Function` API
  rather than trusting this repo's prior "no fresh scoping across repeat
  invocations" narrative. **Corrected finding**: the actual trigger is
  any `const`/`let` declared directly inside a `try { }` block body
  (throws `TypeError: redeclaration of const/var X` on the very first
  call, not just repeat calls); `catch (e) { }` blocks are unaffected;
  plain and destructuring `for (const x of ...)` for-of loops are safe
  even under genuine repeated invocation through the same callback
  object, with or without a further `const` in the loop body. This
  clears `economy.js`'s `payCoins` and `selftest.js`'s `stPayCoins`
  (this issue's two named targets) as confirmed-safe, no change needed.
  Auditing every `try {` in `pack/kubejs/**/*.js` against the corrected
  criterion found one real, previously-undiscovered, currently-live bug:
  `skill_respec.js`'s `respecCategory()` (backs `/respec`, item 11's
  skill trees) had `const` declared directly in its outer try and a
  nested per-node try — meaning **every `/respec` call would have thrown
  on its first statement and always reported "Respec failed"**, directly
  threatening GitHub issue #1's own in-game `/respec` verification.
  Converted to `let` throughout, matching this codebase's established
  workaround; verified both via the same Rhino harness (before: fails on
  call 1; after: 3 repeated calls succeed) and a clean L0+L1 boot. A full
  in-game `/respec` exercise still needs issue #1's live player. Commit
  `653a024`.
- **#7 (creative_crate unique-item duplication) — CLOSED, accepted
  risk, re-confirmed rather than newly resolved.** Confirmed
  `create:creative_crate` really is survival-craftable in this pack
  (deliberately — `pack/kubejs/data/create/recipe/creative_crate.json` +
  `tier9_jovian_frontier.toml`'s final-tier gate), so this is real, not
  hypothetical. Decompiled the actual `create-1.21.1-6.0.10.jar`
  (`CreativeCrateBlockEntity`/`FilteringBehaviour`) and confirmed by full
  bytecode inspection — not just "unconfirmed" as the original
  implementation note hedged — that setting a crate's filter fires zero
  NeoForge events, so no KubeJS-level intercept is possible. Scoped a
  Java-mixin fix (the only remaining technical option, `tiabfix`-style)
  and judged it not warranted this pass: this codebase has no existing
  registry of "genuinely unique" item ids to check against, and the
  closest candidates (the 3 Phase-7 boss-unique weapons) are themselves
  repeatable weighted loot-table drops, not hard-capped-at-one rewards,
  which blurs whether they even qualify for the "one-of-a-kind forever"
  exemption this issue invokes. No code change; closed re-affirming the
  exploit-risk disclosure already on record in `DESIGN.md`'s "Resource
  infinity" section, now with definitive (rather than hedged) evidence
  that no engine-level hook exists.

All fixes boot-tested (L0, plus L1 for #8) before push; full narrative,
evidence, and per-issue Rhino-harness reproduction details are in each
issue's own closing comment on GitHub and in this session's checkpoint
log (`/tmp/vpp-agent-checkpoints/bug-triage-wave1.md`).

## GitHub #9 — "Some tools are still craftable" — FIXED, systematic sweep (2026-07-11)

Reporter (repo admin) hit Create-adjacent metal tools (aluminum/lead/
copper) still craftable despite the design spec's "all tools/weapons only
from Silent Gear". **Root cause**: `blacksmithing.js` and
`weapon_smithing.js` only ever enumerated vanilla + Allthemodium + Epic
Fight recipes via hand-typed tier x type cross products — every OTHER mod
shipping native tool/weapon recipes (TFMG, Create Stuff & Additions,
Stellaris, AllTheOres, Apotheosis, Apothic Enchanting, Ars Nouveau, Born
in Chaos, and vanilla's own 1.21 mace) was never touched.

**Fix**: new `pack/kubejs/server_scripts/tool_consolidation_sweep.js` — a
pattern-based runtime sweep (`event.forEachRecipe`, javap-verified against
the installed KubeJS jar; first use of that API in this pack) over every
registered recipe's real output item, with an explicit
namespace/item-exceptions list and a per-namespace boot-log count, so
future mod additions stay covered without another hand-typed list.
Ground-truthed by a static scan of all 87 jars' 9,873 recipe jsons PLUS
two live boots with temporary per-id logging (the runtime sweep caught
things the static scan structurally missed, e.g. Create's `results`-list
schema).

**Removed (93 recipes, boot-verified per-id)**: TFMG aluminum/lead tools
(10 — the reporter's example; TFMG's steel tools ship upstream-disabled as
`minecraft:empty` and never registered), Create S&A brass/copper/zinc/
rose_quartz/experience/blazing tools + Blazing Cleaver + Portable Drill
(28), Stellaris steel tools (5), AllTheOres ore hammers (5 — **later
RE-EXEMPTED by #86, see the dated entry at the bottom of this file**: they
turned out to be crafting-grid dust-processing ingredients, not mining
tools, and removing them orphaned the entire ore/ingot→dust pipeline),
Apotheosis'
own stone->iron->golden->diamond tool smithing-upgrade ladder (15 — a
second missed bypass of the vanilla tool removal), Apothic Enchanting's
craftable Inert Trident + its infusion into a real `minecraft:trident`
(2), Ars Nouveau's Enchanter's Sword + Spell Bow/Crossbow + dye variants
(6 — Part 4 already redirected Ars mage ARMOR through Silent Gear, so its
weapons were the same oversight class, not an exception), Born in Chaos'
16 unique named weapons (item 6 stripped these from mob LOOT but left
their crafting recipes live — the actual hole), vanilla `minecraft:mace`
(1 — post-dates `blacksmithing.js`'s tier table), and Epic Fight's own
`minecraft:netherite_<type>_smithing` diamond->netherite upgrades (5 — a
bypass of `weapon_smithing.js`'s Silent-Gear-gated netherite tier).

**Exceptions ruled and kept** (documented in-script too):
- **Farmer's Delight / End's Delight knives + ExtraDelight spoons — KEPT.**
  Item 9 explicitly adopted and tier-locked these as KITCHEN tools for the
  cutting-board/Saw food-automation chain (Andesite/Brass/Precision Age).
  Ruling: they are accepted kitchen tools, NOT consolidation targets — the
  food overhaul's documented design depends on them being craftable.
  ExtraDelight's gingerbread/sugar-cookie "pickaxes"/"swords" are edible
  foods (tagged `c:foods/cookie/*`), not tools.
- **Wands — KEPT**: Ars Nouveau casting/dominion wands are the mage
  archetype's class mechanic; Building Wands are construction utilities
  (`wands:netherite_wand` already Precision-locked). Neither is a
  mining/combat tool in the consolidation sense.
- **"Drill"/"saw"/"hammer" MACHINES — KEPT**: create:mechanical_drill/saw,
  createoreexcavation's vein-drill components, stellaris:pumpjack_drill,
  TFMG's pumpjack-hammer multiblock parts (3 of 4 are placeable blocks) —
  machine components matched only by name substring. The one genuine
  handheld among them, `create_sa:portable_drill` (3x3 mining gadget), IS
  removed via an explicit extra-ids list.
- **Novelty/non-tools — KEPT**: `create:cardboard_sword` (joke item),
  `apothic_enchanting:pickaxe_tome`/`bow_tome` (enchanting tomes),
  ExtraDelight decorative ribbon bows. TiaB is untouched (not a
  tool/weapon; its own Brass Age gate stands).

**Verification**: L0 boot smoke PASS + L1 self-test PASS — both run via
scratchpad variants identical to the canonical scripts except for
excluding a parallel agent's in-progress (currently unparseable) draft
jsons under `pack/kubejs/data/born_in_chaos_v1/neoforge/biome_modifier/`
from the synced `server/` copy (those drafts kill registry loading for ANY
boot and are untracked/outside this fix; canonical L0/L1 must be re-run
when that work lands). Boot log's own sweep line now self-audits:
`removed 93 ... alltheores=5 apotheosis=15 apothic_enchanting=2
ars_nouveau=6 born_in_chaos_v1=16 create_sa=28 minecraft=6 stellaris=5
tfmg=10 | silentgear recipes still registered: 582`. Fix lands in the
NEXT release; v0.1.0 still has the bug.

## Integration wave 2 — GitHub #5 (BiC spawn buckets) + #10 (quest book) + #11 (Jade) (2026-07-11)

Folded in three fully-drafted, admin-approved features in one integration
pass (one integrator, serial resource ownership per the operating model),
one commit per feature, full canonical test suite green with everything in.
All three land in the NEXT release — v0.1.0 has none of them.

- **#5 — Born in Chaos spawn retargeting (Option B), commit `8378454`.**
  41 same-path override JSONs retarget the formerly-`neoforge:any`
  (spawn-everywhere) BiC hostiles onto 12 thematic biome-tag buckets;
  weights/counts keep the jar's shipped values, the 4 already-curated mobs
  untouched. **Real bug found at integration boot, invisible to the
  drafter's `json.load` validation**: a JSON HolderSet accepts a biome tag
  only as a single top-level string — the drafted list-of-tag-strings form
  fails NeoForge's codec on all 41 files at once and kills ALL registry
  loading (this is precisely the "unparseable drafts" the #9 pass had to
  exclude to boot). Fixed with NeoForge's composite holder sets
  (`{"type": "neoforge:or", "values": [...]}` for the 28 multi-tag files,
  plain tag string for the 13 single-tag ones), ground-truthed against the
  installed neoforge-21.1.235 jar. Bonus evidence from the failed boot:
  the registry error named the KubeJS data pack as its source for these
  ids, proving same-path override precedence over the mod jar. Spawn-feel
  needs a live session (flagged on the issue). DESIGN.md's mob-variety
  section updated with the bucket summary.
- **#10 — quest book overhaul, commit `a5f3a6b`.** 1 chapter/6 quests →
  10 chapters/62 quests, one full walkthrough chapter per tier; old
  `tier_progression.snbt` deleted; `scripts/gen_quests.py` replaced by the
  new generator (same filename, per the handoff checklist). **Integration
  cross-check catch**: the draft's four vanilla-pickaxe craft quests
  (`minecraft:stone/iron/diamond/netherite_pickaxe`,
  `only_from_crafting: true`) targeted recipes `blacksmithing.js` removed
  in the gear overhaul — permanently uncompletable as drafted; retargeted
  to `silentgear:pickaxe` (the pack's real craftable tool item). The
  mandated quest-vs-#9-sweep cross-check found **zero** collisions between
  quest item targets and the sweep's 93 removed recipe outputs — the
  pickaxe gap predates the sweep (gear-overhaul era) and was the only
  craft-target defect. Boot-verified via FTB Quests' own count line
  ("Loaded 1 chapter groups, 10 chapters, 62 quests") per the checklist's
  silent-skip warning. Pacing/reward feel needs a live playtest (flagged
  on the issue). DESIGN.md's quest-system section gained a full subsection.
- **#11 — Jade + Jade Addons, commit `8e2643e`.** Manifest phase 21,
  both `side:"both"`; lockfile regenerated via the canonical
  `resolve_mods.py`; resolved sha512s match the research handoff's
  download-verified pins exactly (no drift → no stop-and-investigate).
  Disclosed side effect of the full regen: unpinned `puffish_skills`
  tracked upstream 0.18.0 → 0.18.1 (the manifest's documented convention);
  the passing boots ran 0.18.1. No config shipped (zero-config precedent).
  Server-side value confirmed in the boot log (Jade plugins loading from
  Tom's Storage/Waystones/Ars Nouveau/Apothic). Watch-item: jade-addons
  6.1.0 is a 2025-03 build; first suspect if Create tooltips ever break.
  In-game tooltip check needs a real window (flagged on the issue).

**Full canonical suite, everything in (no scratch variants this time)**:
L0 boot smoke PASS (89 server mods, 0 KubeJS errors/warnings, no
unbaselined WARN/ERROR, clean stop; #9 sweep line unchanged at 93 removed
/ identical per-namespace counts / silentgear 582 — Jade adds no recipes,
confirmed not assumed). L1 self-test PASS (17/17, 4 console-only skips;
10036 total recipes). L2 HeadlessMC client smoke PASS with the enlarged
client set: 92 client-relevant lockfile entries (was 90 — DESIGN.md's L2
section updated), 116 distinct modids seen incl. jar-in-jar libs, 0 fatal
FML errors, `mod/jade` and `mod/jadeaddons` both present in the
resource-reload success marker (16 occurrences each), MoreCulling still
loading fine, the usual disclosed STB/imageio harness race and nothing
else. Every server stopped cleanly between boots (echo stop > cmd_fifo,
no stray java/tail processes).

## Release v0.1.1 (2026-07-14)

Second beta cut, minted after a full canonical test run on main with
everything from integration wave 2 already in (GitHub #5/#9/#10/#11 —
this release's actual content is unchanged from wave 2's own final state;
this pass's job was test/cut/mint, not new implementation work). Full
result: L0 boot smoke PASS (89 server mods, 0 KubeJS startup/server script
errors or warnings, no unbaselined WARN/ERROR, clean stop; tool-
consolidation sweep line unchanged — 93 removed, silentgear 582; quest
book `10 chapters, 62 quests`), L1 self-test PASS (`17/17`, 4 console-only
skips), L2 HeadlessMC client smoke PASS (92 client-relevant lockfile
entries, 116 distinct modids incl. jar-in-jar libs, 0 fatal FML errors,
all 10 Stage-A optimization/QoL mods confirmed present by modid, the
usual disclosed STB/imageio harness race and nothing else).

- `pack/VERSION` bumped `0.1.0` -> `0.1.1`, committed/pushed separately
  (`1b14920`) from the docs pass per this session's own step ordering.
- Client `.mrpack` (94 mods, 0.29 MB) and server `.zip` (632 files, 362 MB)
  bundles built via the canonical `scripts/build_mrpack.py`/
  `scripts/build_server_bundle.py` — `build_server_bundle.py`'s own
  `build_server.py` re-sync reported `server/ is up to date` (no mutation
  vs. the state L0/L1/L2 had just tested), so no L0 re-run was needed
  before minting.
- GitHub release `v0.1.1` (id `353820006`, tag at commit `1b14920`,
  prerelease=true, title "v0.1.1 (beta)") minted via a one-off python3
  stdlib-`urllib` script (no `gh`/`curl`, per this session's own
  constraint) — token parsed from `/home/ubuntu/.vpp-git-credentials`
  (git-credential-store `https://user:token@github.com` form), never
  printed. Both bundle assets uploaded to `uploads.github.com` and
  verified via a GET back: exactly 2 assets, sizes matching the local
  files byte-for-byte (client 304471 bytes, server 379577444 bytes).
  Release body: what-changed-since-v0.1.0 (bug fixes #4/#6/#7/#8/#9,
  features #5/#10/#11), full test-status numbers, and a "Verification
  wanted" note on #1/#2/#3 flagging that `/respec` (fixed by #8) is now
  actually testable for #1's checklist.
- `nix/release.json` repinned via `scripts/update_nix_release.py --tag
  v0.1.1` (run *after* the release existed, per the script's own
  documented ordering) — downloaded the real uploaded server-zip asset
  bytes back from the release (379577444 bytes, size-verified against the
  API's own record) and hashed those canonical bytes: sha256
  `1f6af8faeb82fc380c5dde6ee0528be78b25c07877acdbef217ff4a1b78f2ce2`.
  NeoForge version auto-detected unchanged at 21.1.235. Committed/pushed
  separately (`87c0538`).
- One short comment posted on each of the three open verify-in-game
  issues (#1/#2/#3) linking the new release; #1's comment specifically
  calls out that `/respec` is fixed in this build so its full checklist is
  now testable end-to-end for the first time. None of the three were
  closed (human-only in-game verification, unchanged from wave 2).
- **Environment note for any future session on this machine**: `git` is
  not on the default shell `PATH` at all in this sandbox; the real binary
  lives at `/snap/claude-code/43/usr/bin/git` (or whatever the current
  snap revision is) and its network operations (`push`/`fetch`) additionally
  need `GIT_EXEC_PATH` pointed at that same revision's `usr/lib/git-core`
  and `LD_LIBRARY_PATH` including that revision's `usr/lib/x86_64-linux-gnu`
  (for `libcurl-gnutls.so.4`, which `git-remote-https` dynamically links).
  Local-only git commands (status/commit/log/diff) work fine without this;
  only the network-touching subcommands need the full three-variable
  combo.
- Stale local `0.1.0` bundles at the repo root
  (`vanilla-plus-plus-client-0.1.0.mrpack`,
  `vanilla-plus-plus-server-0.1.0.zip` — both untracked/gitignored build
  output, confirmed via `git status`) were deleted after the `0.1.1`
  bundles were built and uploaded; only the `0.1.1` bundles remain at the
  repo root.

## Migration to the AI Delivery Organization charter (2026-07-19, owner directive)

- Project management moved to `~/ORCHESTRATION.md` (machine-level,
  deliberately untracked): **CEO** (Fable, wakes on token refresh,
  discovers projects as `~/*/SPEC.md`, launches PMs) → **PM** (Fable, one
  per project, sole git/GitHub owner, stateless — reconstructs from
  SPEC.md + repo + GitHub per charter §3) → **Engineers** (sonnet, scoped
  tasks in isolated worktrees, never touch git). This supersedes this
  repo's prior orchestrator-mode operating model AND the session-local
  standing-loop/start+5h wakeup chain (cancelled; the CEO now provides all
  wake-ups).
- `SPEC.md` created at repo root as the charter discovery anchor / PM
  entry point (summary + pointers; instructions.md/DESIGN.md remain the
  detailed sources and win on detail).
- Charter deltas that CHANGE prior conventions here, effective now:
  (a) **no direct commits to main** — feature branches + PR, merged after
  CI passes (the migration commit itself is the final direct-to-main
  commit, made before the branch rule can be satisfied since no CI exists
  yet); (b) **Conventional Commits**; (c) shared PM git identity
  `AI Project Manager (Claude) <ai-pm@ghov.net>` in `~/.gitconfig`;
  (d) tests-first per charter §6 — the existing L0/L1/L2 suites are the
  harness baseline, per-change failing-tests-first becomes the norm once
  CI exists.
- Charter §4 gap: **no CI/CD**. "Infrastructure precedes features" — a
  GitHub issue tracks bootstrapping GitHub Actions (constraint for the PM:
  full L0/L1 needs a booted 89-mod server with Modrinth downloads + Java
  21 — feasible in Actions but heavy; staged approach sensible: JSON/SNBT/
  manifest/lockfile validation + Rhino-pattern lint first, boot smoke
  behind a label or nightly).
- Unchanged by migration: issue label state machine, admin-approval gate
  for features, verify-in-game issues are human-only, releases only on
  explicit owner prompt, ground-truth-over-assumption, the boot/test/
  release runbooks in HANDOFF.md.

## QoL wave — GitHub #13 (Gravestone) + #14 (ClientSort) + #16 (Lootr) (2026-07-19)

Three owner-filed, owner-`approved` feature issues, all "add one well-chosen
mod", landed together as one PR (one commit per mod) after Modrinth-API +
jar-bytecode ground-truthing by a sonnet Engineer. Full per-mod rationale
(candidates rejected and why, dependency/side/config analysis, pack-
interaction findings) lives in each mod's `pack/manifest.json` note — the
notes are the canonical record this time; highlights only:

- **#16 lootr** (owner-named): zero deps; composes with
  `gen_structure_loot.py`'s table replacement (instances per-player from the
  registered table id); decay/refresh off by default = one static roll,
  matching the bonus-pool design. No config shipped.
- **#13 gravestone-mod** (henkelmax): over yigd (dead-ended at 1.21.1) /
  Universal Graves (no neoforge) / Corail (not on Modrinth for neoforge).
  Permanent-until-broken graves, items only (no XP surface at all).
  `pack/config/gravestone-server.toml` = bytecode-ground-truthed defaults
  with `only_owners_can_break=true`.
- **#14 clientsort**: over Inventory Profiles Next (would add
  kotlin-for-forge + libipn) and others; its `classPolicies` validation
  auto-disables sorting per menu class on mismatch — exactly the modded-
  container (RS/Tom's/Sophisticated) dupe-risk mitigation we needed.
  `pack/config/clientsort-server.json` = documented defaults with
  `validationActiveServer=true`.
- All three at `phase: 22`, `side: both`. Lock diff kept to exactly the 3
  new entries: `resolve_mods.py`'s re-resolve found 9 unrelated upstream
  bumps (progressivestages, rhino, placebo, modernfix, c2me-neoforge,
  sophisticated-core, sophisticated-backpacks, balm, waystones) which were
  deliberately reverted — version bumps are a separate decision, not a
  side effect of a feature PR.
- Tests: L0 PASS (92 server mods, 0 KubeJS errors, no unbaselined
  WARN/ERROR), L1 PASS (17/17), L2 PASS (95 client mods, 119 modids, 0 FML
  errors). **L2 harness note**: `/tmp` was wiped since v0.1.1, taking
  `/tmp/vpp-research/headlessmc/` with it; rebuilt this session by
  re-downloading headlessmc-launcher 2.9.0 into that exact path
  (`~/.minecraft` instance survived untouched) — HANDOFF.md's L2 setup
  pointer remains accurate.
- In-game behavior (grave placement/recovery, per-player loot rolls,
  sorting vs modded containers) is a human check: filed as a
  `verify-in-game` issue at PR time.

## NixOS module's default server-archive fetch switched from Modrinth to GitHub (2026-07-20, owner directive)

PR #43 (part of #28) shipped `serverArchive`'s default as a `pkgs.fetchurl`
pull from `nix/release.json`'s `modrinth` pin. Confirmed live, same day:
the `v0.2.0` Modrinth version published successfully but the **project**
itself was still in draft/unpublished review status, so the public API
404s for everything under it (not a timing issue polling could fix) —
`modrinth` was absent from `nix/release.json`, and `serverArchive` fell
back to its pre-#28 required-manual-option behavior. Owner submitted the
project for review the same day; still 404ing as of this entry.

Owner asked to switch the default to fetch straight from GitHub instead,
to stop depending on Modrinth's review timeline. Ground-truthed before
implementing (this project's standing rule): `gh repo view` shows
`Guno327/vanillaplusplus` is now **public** (was private when the original
Modrinth pivot happened — see the 2026-07-10 NixOS entry above, which
researched and deliberately shelved a `netrcPhase`-based authenticated
`fetchurl` for exactly this then-private-repo case), and a live
unauthenticated `HEAD` request to
`https://github.com/Guno327/vanillaplusplus/releases/download/v0.2.0/vanilla-plus-plus-server-0.2.0.zip`
returned `200` with the correct 380423937-byte `Content-Length`. So the
original blocker that justified the Modrinth detour no longer exists.

**Change**: `nix/module.nix`'s `githubServerArchive` (renamed from
`modrinthServerArchive`) now builds the release-asset URL directly from
`nix/release.json`'s already-present `repo`/`tag`/`assetName`, verified via
`pkgs.fetchurl`'s `sha256` check against the already-present `sha256`
field (SRI-formatted, accepted by `fetchurl` as-is — no `modrinth` pin
needed at all). This is unconditionally available for every release
(those fields are never optional, unlike `modrinth`), so `serverArchive`'s
type dropped `nullOr` and the corresponding "resolved to null" assertion
was removed as unreachable. `flake.nix` and README.md's "Running on
NixOS" section (including its now-stale "private repo" framing in step 1)
updated to match. The Modrinth publish workflow/pin itself
(`publish-modrinth.yml`, `update_nix_release.py`'s `--modrinth-only`) is
untouched — still useful for the Modrinth *listing* players can install
from, just no longer what this module defaults to.

## L3 live-join test made to actually run; #49 narrowed, not closed (2026-07-22)

Owner provided permanent access to an Incus cluster so L3 could run
somewhere with a display, and asked for L3 to become a standard part of
the test suite. It now reaches `L3 PASS` reproducibly (five clean runs):
a real client with the full mod set joins the dedicated server, survives a
45s post-join settle window past Sable's historical ~29s mark, and is not
sitting on a loading/dirt-message screen.

**Every blocker was in the harness, not the pack.** Five distinct bugs,
each of which independently prevented a join, listed because several are
badly counter-intuitive and cost a full ~10-minute client boot apiece to
find:

1. **`hmc.check.xvfb=true` is the switch that matters, not `-lwjgl`.**
   HeadlessMC installs its LWJGL redirection layer (stubbing
   lwjgl-glfw/lwjgl-opengl into no-ops) *by default* — that is its whole
   purpose. Its `-lwjgl` flag does not select the stub; per its own
   `help launch` it "Removes lwjgl code, causing Minecraft not to render
   anything", i.e. more headless, and neither L2 nor L3 ever passed it.
   The previous revision of `l3_client_join.py` asserted the exact
   opposite in its docstring and would have stayed broken on any machine.
   With the property off, the client loads its entire mod set, reports
   `OpenGL Vendor:` empty and `Backend API: NO CONTEXT`, and dies on
   Sodium's fence object *while Xvfb is running perfectly*. With it on,
   `XvfbService` shells out to `ps aux`, logs "Running with xvfb", skips
   redirection, and the same run reports `OpenGL Renderer: llvmpipe`.
2. **`connect` takes ip and port as separate arguments.** `connect
   host:port` reaches hmc-specifics' ConnectCommand fine and then throws
   inside it — Minecraft's `ServerAddress` hands the string to Guava's
   `HostAndPort.fromParts()`, which rejects a host that already carries a
   port. The IllegalArgumentException only appears as a stack trace in the
   client log, so the symptom is just "never joined".
3. **The launcher and the game race for the same stdin.** HeadlessMC gives
   the game its own stdin, so each line written to the FIFO is delivered
   to whichever process the kernel wakes. Lines landing on the launcher
   are rejected with "Couldn't find command for '[connect, ...]', did you
   mean 'help'?" and lost. This reads like a missing mod but is not —
   launcher-side verbs like `quit` still work, so the relay looks healthy.
   Fix is to resend until the server confirms the join. `-quit` is *not*
   the fix: it makes the launcher delete the game's instrumented runtime
   dir on the way out (only half-fixed by `hmc.keepfiles=true`) and, since
   it relays the game's stdout, its exit kills the game before it renders
   a frame.
4. **The client instance never got `pack/{config,kubejs,defaultconfigs}`.**
   `build_server.py` syncs these into `server/` and `build_mrpack.py`
   ships them under `overrides/`, so real players are unaffected — but
   nothing did the equivalent for the local research instance. The pack
   registers its own items from `pack/kubejs/startup_scripts`, so the
   client was kicked mid-handshake with "The server send registries with
   unknown keys: ResourceKey[minecraft:item / vanillaplusplus:...]".
   Looks exactly like a pack bug; is purely a stale test instance.
5. **The server was killed mid-test by its own `timeout 300`.** A
   hardcoded literal that could not track the other timeouts; the full run
   (boot + ~3min client load + settle) exceeds it, so the server exited
   during the post-join phase and the failure surfaced as a missing
   assertion result rather than "the server died". Now derived from the
   other constants.

**#49: L3 does not reproduce it. That is not the same as fixed, and it
must not be closed on this evidence.** The owner reproduced the hang by
hand on v0.2.1; L3 does not. The environments differ in ways that could
plausibly matter (Mesa llvmpipe software rendering, loopback networking, a
freshly generated world), so the honest conclusion is that L3 fails to
reproduce it, not that the bug is gone. Concrete lead for next session:
the join log shows Sable's **client**-side UDP channel still going active
and then closing — #50 disabled the *server* pipeline only.

**Accepted gap**: L3 does not run `/vpp_selftest` as the joined player, so
selftest.js's player-gated checks still SKIP and remain unexercised
anywhere in the suite. Both available routes are dead ends with this
toolchain: from the console `execute run vpp_selftest` works but
`execute as <player> run vpp_selftest` (and `@a`) silently produces
nothing — no result, no error, no exception, with the player provably
online via a `list` probe and a 150s window; from the client,
hmc-specifics 2.4.0's registered command surface accepts `connect`, `gui`
and `menu` but rejects `command`, `./...` and even `disconnect`. Recorded
as a KNOWN GAP in the script rather than faked or silently dropped; worth
its own issue.

**New tooling**: `scripts/incus_api.py`, a stdlib-only Incus REST client
(TOFU server-cert pinning, async-operation waiting, websocket-free exec
via `record-output`, streaming file push). Needed because the dev box has
no `incus`/`lxc` CLI and no `curl`, and Ubuntu Core offers no apt or root
to install any. One trap encoded in it: a raw `+` in a query path decodes
to a space, so anything under `vanilla++` 404s unless the path is quoted.

## ProgressiveStages dropped entirely; progression gated by materials (#49, owner decision, 2026-07-22)

The pin-to-2.1 fix (PR #55) was closed unmerged in favour of removing the mod.
What settled it was testing the residual item-path variant of the same JEI
bug on the *pinned 2.1* build: 45s after joining, before any stage grant,
**0** ingredient-add passes; 30s after `stage grant <player> andesite_age`,
**7810** passes, each re-adding the same `67 net.minecraft.world.item.
ItemStack`, still climbing at teardown. `refreshJei()`'s item path re-adds
every locked item id the player already owns, unconditionally, in both 2.1
and 3.0.1 — so the pin fixed *joining* and nothing else: the freeze returned
the moment anyone unlocked their first tier. Older versions are not a way
out either (`1.3`/`1.2` never call `registerIngredientListener`, so no loop,
but they also ship no `MultiTrigger*` and no `KubeJSStagesCompat`, both of
which this pack depends on). **2.1 was the floor and the floor was not high
enough.**

Owner's call: drop the mod, rely on resource availability and crafting
recipes. A bug class that cannot return.

**Why this was cheap rather than a rewrite.** KubeJS ships its own stage
backend: `dev.latvian.mods.kubejs.stages.StageEvents.create()` falls back to
`TagWrapperStages` (player-NBT-backed, synced via KubeJS's own
`SyncStagesPayload`) whenever no mod claims `StageCreationEvent` —
ProgressiveStages was merely one claimant. javap-confirmed against
kubejs-neoforge-2101.7.2-build.368.jar. So `player.stages`,
`PlayerEvents.stageAdded` and `/kubejs stages` keep working, and every script
that reads stages — `quests.js` (its whole "gamestage" task type),
`mob_scaling.js`, `mobility.js`, `leaderboard.js`, `selftest.js` — needed no
changes at all.

**What actually changed:**

- `progression_stage_bridge.js` is now the *only* granter of tier stages. It
  already granted the four item-triggered tiers (it was written for #23,
  because the mod's own triggers missed crafted items); the three trigger
  types the mod still owned are ported into it — `PSB_STARTING_STAGES`
  (rootborn at login), `PSB_DIMENSION_STAGE_TRIGGERS` (the four Stellaris
  frontier stages, evaluated from the player's current dimension on the
  existing 20-tick scan), and `PSB_BOSS_STAGE_TRIGGERS` (ender dragon ->
  starforged_age, via `EntityEvents.death`). The boss grant goes to every
  player in the dimension, not just the killer: the End fight is a group
  activity and a single-killer grant would strand everyone else on this
  pack's one hard tier gateway.
- `pack/config/ProgressiveStages/*.toml` moved to `pack/progression/*.toml`
  and `progressivestages.toml` was deleted. The tier files are still the
  pack's tier manifest (`gen_economy.py` prices off them, unchanged output
  byte-for-byte after the path move) — they are design data now, read by
  generators and shipped to nobody, since `build_server.py`/`build_mrpack.py`
  only sync `config`/`kubejs`/`defaultconfigs`. `triggers.toml` was deleted
  outright: the bridge's constants ARE the trigger definition now, so keeping
  a second copy would only invite drift.
- New `pack/kubejs/server_scripts/tier_gating.js`: 13 recipe edits, each
  adding ONE tier material to a recipe whose only gate was the deleted lock.

**Which families actually needed an edit — grounded, not guessed.** A recipe
audit across all 4758 craftable ids in the built server showed most of the
lock list was already redundant: Create/TFMG/Stellaris/AllTheModium chains
gate themselves, Refined Storage gates itself through its own basic ->
improved -> advanced processor chain (`autocrafter` and `wireless_transmitter`
need an advanced processor; `16k_storage_part` needs an improved one), and
`weapon_smithing.js`/`storage.js`/`ars_nouveau_armor.js`/`tick_accelerator.js`
had already re-authored several families whose gates therefore survive
untouched. **Caveat worth recording**: the first version of that audit
produced false positives — it flagged `create:track_station` (which actually
needs `railway_casing`) and `refinedstorage:controller` (it matched RS's
*recoloring* recipe, not the real one). Every family below was confirmed by
reading its real recipe JSON out of the jar, not by the heuristic. A proper
recursive-reachability version of the audit is worth having as a permanent
tool and is filed as follow-up work, not blocking.

Edited: Waystones (`warp_stone` -> netherite ingot; one edit covers the
10-id family, since every waystone/sharestone/portstone recipe in the jar
consumes warp_stone and the three scrolls are inert without a placed
waystone), Sophisticated Backpacks (`iron_backpack`/`gold_backpack` +
`stack_upgrade_starter_tier`/`tier_2` — the chains gate everything above
them; kept the mod's own `backpack_upgrade` recipe type via `event.custom()`
because that type is what carries stored CONTENTS into the upgraded
backpack, and a plain shaped recipe would silently delete a player's
inventory), Building Wands (copper/iron/diamond wand + magic_bag_1/2),
Tom's Storage upper terminals (crafting/wireless — the *base* terminal stays
deliberately pulled down to iron tier by `storage.js`), and Create Ore
Excavation's entry drill.

**Deliberately not reimplemented** (owner chose "pure materials only" when
asked): mob-spawn gating, dimension-travel blocking, block-interaction rules,
locked-item name masking, and JEI hiding of locked items. Born in Chaos mobs
now spawn from world start and the Nether is open from the beginning.

**Verification.** L0 PASS (88 server mods — one fewer, 0 KubeJS
errors/warnings, no unbaselined WARN/ERROR). L1 PASS 28/28 with three new
checks: the ported trigger tables are wired, the starting stage grants on a
live player, and every one of the 13 gated recipes both resolves and actually
demands its tier material (`Predicate#test` probe against the live recipe
manager — the same technique the storage.js check uses, since KubeJS's class
shutter hides `Ingredient`'s own members). L3 with the #49 refresh-loop
assertion plus the new post-join stage-grant probe is the end-to-end proof
that the bug class is gone.

## JEI acquisition-info wave, and a silently-dead mob-scaling feature it uncovered (#57, 2026-07-22)

Owner asked for JEI to carry as much "how do I get this?" information as
possible. Split in two, because two different things know the answer.

**What the game knows — seven addons.** All verified to have real 1.21.1 +
NeoForge builds and their side markers taken from Modrinth's own
client_side/server_side fields, per this pack's standing rule:

| mod | side | why |
| --- | --- | --- |
| Just Enough Resources | client | ore distribution per dimension/biome, mob + plant drops, dungeon loot, trades |
| Advanced Loot Info | **both** (server_side=required) | reads the REAL loot tables, so it covers this pack's own `gen_structure_loot.py` output and every modded mob with no per-mod support |
| JEI WorldGen | both | newest worldgen addon; deliberately overlaps JER — see below |
| Just Enough Breeding | client | Naturalist adds a large animal set |
| JEED | client | Ars Nouveau + Apotheosis effects |
| Just Enough Professions | both | villager workstations; its one required dep is JEI itself |
| Enchantment Descriptions (+prickle, +bookshelf-lib) | both | Apotheosis' enchanting overhaul is central here — the only pick with a dependency cost |

**Deliberate redundancy, to be resolved in game:** JER's 1.21.1 build is from
2025-05 and may not see this pack's modded ore generation (Stellaris/TFMG/
AllTheOres/AllTheModium); JEI WorldGen is from 2026-07 and claims universal
compatibility. Both are installed so the loser can be dropped on evidence
rather than guessed at now.

**What only the pack knows — `jei_info.js`.** No addon can explain what this
pack did to its own recipes, and that is where players actually dead-end:
`minecraft:iron_pickaxe` has no recipe at all (the #9 tool sweep deleted it to
funnel players to Silent Gear, whose own JEI plugin documents the Silent Gear
side perfectly but is not pointed AT from the item you looked up);
`waystones:warp_stone` demands netherite because #49's `tier_gating.js` put it
there; `create:andesite_alloy` silently grants a quest-gating stage;
`alltheores:zinc_ingot` was unified out of its tag by `dedup.js` and is
consumed by nothing.

`RecipeViewerEvents.addInformation` is posted with `ScriptType.SERVER`
(javap-confirmed: `recipe/viewer/server/ItemData` posts
`RecipeViewerEvents.ADD_INFORMATION` with `ScriptType.SERVER` and a
`ServerAddItemInformationKubeEvent`, synced to the client's viewer), so the
layer lives in `server_scripts` in the same Rhino scope as the tables it
reads. Three of its four sources are read from the script that owns the
behaviour rather than hand-copied — `tool_consolidation_sweep.js` now
publishes `TCS_REMOVED_TOOL_ITEMS` from its own removal pass (so it covers
mods added later, which a hand-typed list would miss), `tier_gating.js`
publishes `TG_TIER_INFO`, and `progression_stage_bridge.js`'s trigger table is
read directly. Only the dedup redirects are hand-maintained, because
`dedup.js` is a series of `event.remove(tag, item)` calls with no list to
read; that one is covered by a selftest check instead.

**The bug this wave uncovered, which is bigger than the wave.** L3's new
post-join stage-grant probe is the first test in this suite that ever put a
real player holding a real tier stage next to a real mob spawn. It
immediately surfaced `EntityEvents.spawned` throwing
`IllegalArgumentException: 'multiply_base' is not a valid enum constant`.

`mob_scaling.js` passed `'multiply_base'` to KubeJS's
`entity.modifyAttribute()`, which coerces to vanilla's
`AttributeModifier.Operation` — whose only valid ids are `add_value`,
`add_multiplied_base`, `add_multiplied_total`. The spelling came from
puffish_skills' `attr_reward` vocabulary, where it is correct (see
`scripts/gen_skill_tree.py`, which still uses it correctly for Puffish's own
json) — two systems, same semantic, different word. The throw happened
*before* `setHealth`, the `vpp_difficulty` tag and the star nametag, so:
**mob difficulty scaling has never worked**, and the death-reward bonus that
reads that tag never paid out either. Nothing but a server-log ERROR line
said so — L0 boots with no players, L1 is console-only, and no test had ever
staged the one situation that triggers it.

Fixed to `add_multiplied_base` behind a named constant
(`MS_SCALING_OPERATION`) with the trap documented at the use site, plus a
selftest guard pinning it to the three ids the vanilla enum accepts. Worth
recording as a lesson about test coverage shape rather than test count: the
suite was green the entire time this feature was dead, because every tier
below L3 structurally cannot observe it.

**Verification.** L0 PASS (94 server mods — 88 + the 6 both-side additions,
0 KubeJS errors/warnings, no unbaselined WARN/ERROR). L1 PASS 31/31,
including new checks that the info layer generates pages for all four sources
(driven by a recording stub, since a console-only boot never syncs a recipe
viewer), that `TG_TIER_INFO` only describes recipes this pack really gates,
and the mob-scaling operation guard. L2 PASS — the real risk gate for seven
new JEI plugins: 100 client mods / 124 modids discovered, dependency-resolved
and mixin-applied with zero mod-loading errors. L3 PASS with the refresh-loop
assertion at 0 both after join and after a tier grant, and the enum error gone
from the server log.

**Harness note:** the L3 probe's grant confirmation now reads back
`kubejs stages list` rather than watching for the "Added '<stage>' stage for
<player>" line. `StageCommands.addStage` only prints that when `Stages.add()`
returns true — i.e. when the player did not already hold the stage — and L3
reuses its world between runs, so from the second run onward the grant is a
silent no-op and the probe would have skipped forever.

## v0.3.0 cut + session wrap (2026-07-22)

Minted `v0.3.0` (prerelease) off `main` at `59d35c5` via `mint-release.yml`,
bump=minor. Everything worked except the final "Open post-release sync PR"
step, refused exactly as it was for v0.2.1 — that is #52's one repo setting,
still unticked — so the sync PR was opened by hand again (#59). Release notes
were rewritten afterward: the auto-changelog said "drop ProgressiveStages" and
nothing about this being a breaking cut for both sides, which is the one thing
an operator needs to read first.

**`/releases/latest` excludes prereleases.** Found the hard way while repinning
`nix/release.json`: every release this project has ever cut is a disclosed
prerelease, so `update_nix_release.py`'s default (no `--tag`) path 404'd.
Fixed in #60 to list releases and take the newest published one. Worth knowing
generally — it will bite any tooling that assumes `/latest` means "newest".

**Modrinth taken off the critical path** (#60), after the owner noted approval
would take a while and confirmed the repo is public. The flake already fetched
from the GitHub release asset (since #28); what remained was vestigial —
a per-mint Modrinth poll costing ~30s of retries and ending in a "re-run with
--modrinth-only" instruction for a pin nothing reads, plus a `_comment` in
`nix/release.json` that flatly described the wrong default. Modrinth is now
opt-in via `--modrinth`.

**Stated plainly in flake.nix/README, because it is a real constraint:** a
flake cannot resolve "whatever release is newest right now" during a pure
evaluation — `pkgs.fetchurl` needs the hash up front. "Latest" therefore means
"latest as pinned in nix/release.json", which every mint rewrites; consumers
upgrade with `nix flake update` + `nixos-rebuild switch`. A runtime fetch in
the systemd unit would give hands-off updates at the cost of hash verification,
rollback, and a server that changes version underneath a rebuild — offered to
the owner, not built.

**Open at session end:** #58 (in-game verification of v0.3.0 — the one thing no
test tier here can settle), #52 and #44 (both one-click owner actions; #44
downgraded to distribution-reach only), #61 (recursive recipe-reachability
audit tool), #62 (L3's `gui` check passes vacuously and needs the
resend-until-answered treatment `connect` already has).

## Release policy — agents may mint continuously (CEO directive, 2026-07-23)

**Supersedes the "releases are manual-only, cut only on explicit owner
prompt" rule** that governed every prior cut (v0.1.0 → v0.3.0). New policy,
verbatim intent from the CEO: *agents may mint releases — major and minor
(and patch) — continuously throughout development; the only restriction is
that a full test run must pass before publishing, and otherwise there is no
restriction.*

Concretely:

- **No owner-prompt gate.** Any engineer/PM agent may dispatch
  `mint-release.yml` from `main` at any point. Choosing the SemVer `bump`
  (`major` | `minor` | `patch`) is the agent's call, not the owner's. The
  old "no label or automation ever publishes a release" and "cut only on
  explicit owner prompt" statements in README/SPEC/HANDOFF are retired and
  reworded to match this entry — this log is the durable source.
- **The one hard gate is a full test run.** `mint-release.yml` already
  enforces it structurally: the `mint-release` job `needs:` both
  `fast-tier` (ci.yml — unit tests + all static checks) and `boot-tier`
  (boot.yml — L0 boot smoke + L1 `/vpp_selftest`), so a release cannot be
  built unless the complete automated suite the pipeline can run on hosted
  runners is green. This is the "full test run" the directive requires; it
  was already the technical behavior, so no workflow logic changes — only
  the policy framing around it does.
- **L2/L3 boundary is unchanged and still disclosed, not silently
  dropped.** L2 (HeadlessMC client smoke) and L3 (live client join) remain
  local-sandbox / Incus-host tiers that hosted Actions runners cannot run;
  every mint's release notes keep disclosing this honest boundary (the
  existing "Append test-status disclosure" step). "Full test run" means the
  full *automated hosted* suite (fast + boot) is required-green — it does
  not, and cannot, block a mint on the human-in-the-loop L2/L3 tiers
  without defeating the "continuous" intent. Running L3 against a cut
  before flipping `prerelease=false` for a GA remains encouraged, not
  required.
- **`prerelease` stays a labeling choice, no longer an approval gate.** It
  still defaults to `true` (safe default — every cut so far has been a
  disclosed beta), and an agent may flip it to `false` for a GA when the
  work warrants it. There is no separate owner sign-off for a major/GA cut
  beyond the same full-test-run gate. *(Amended below by the beta-hold
  directive — GA is now owner-gated and hard-blocked; keep `prerelease=true`
  on every cut.)*

See [[project-github-issues-workflow]] memory — its "never cut/publish a
release until the user manually prompts" rule is superseded by this entry.

### Beta hold — never mint 1.0.0 until the owner lifts it (owner directive, 2026-07-23)

Amends the bullet above. The pack stays a **beta prerelease** and must
**never be minted at 1.0.0 or above** until the owner explicitly says
otherwise. Enforced in code, not just docs, so no agent can cross into GA
by accident:

- **`scripts/ci/next_version.py` hard-refuses any computed version `>= 1.0.0`**
  unless `--allow-ga` is passed (unit-tested, `TestEnforceBetaHold` /
  `TestCli`). `mint-release.yml` does **not** pass `--allow-ga`, so from the
  current 0.x line a **`major` bump fails the mint fast** (it would produce
  1.0.0). Only `minor` (0.y+1.0) and `patch` (0.y.z+1) succeed — both keep
  us in the 0.x beta line.
- **Every cut stays `prerelease=true`.** GA (`prerelease=false`, i.e. a real
  1.0.0) is reserved for the owner's explicit go-ahead; until then agents
  leave the flag at its `true` default.
- **Release-cadence mapping while in beta (owner correction, 2026-07-23):**
  the terms are defined by CONTENT, not SemVer field names —
  - A **"major release"** is any release that includes **new features**; it
    is cut as `0.x.0 → 0.(x+1).0` (the workflow's **`minor`** bump input).
    Features are shipped together in these.
  - A **"minor bump"** is a **bug-fixes-only** release; it is cut as
    `0.x.y → 0.x.(y+1)` (the workflow's **`patch`** bump input).
  - So: does the wave add any feature? → major release → dispatch `minor`.
    Bug fixes only? → minor bump → dispatch `patch`. (SemVer `major` stays
    blocked by the beta hold regardless.) Cut releases continuously as
    meaningful work lands, behind the full-test gate — the owner wants
    versions pushed as they make sense, just never GA.
- **Lifting the hold** (owner-only, later): pass `--allow-ga` in
  `next_version.py`'s invocation (and cut with `prerelease=false`). That's
  the single, deliberate escape hatch — nothing else needs changing.

## #86 fix — ore hammers RE-EXEMPTED from the #9 tool sweep (2026-07-23)

Partially reverses the "AllTheOres ore hammers (5)" removal in the #9
tool-consolidation entry above (see the annotated line in that entry).
**Not a change of the #9 design intent** — that sweep exists to remove
alternate *mining-tool* ladders that compete with Silent Gear, and it did
so correctly for everything else. The ore hammers were simply
misclassified: decompiling AllTheOres' `OreHammer.class` shows they are
plain `Item` subclasses with no tool tier and no attack damage — their only
override is `getCraftingRemainingItem`, i.e. a durability-ticking
crafting-grid ingredient (bucket-shaped), not a wieldable pickaxe/weapon.
Their sole purpose is filling the `alltheores:ore_hammers` tag slot in ~90
native `dust_from_ingot`/`dust_from_ore`/`dust_from_raw` recipes across ~30
materials, several of which (electrum, invar, constantan, lumium, signalum,
enderium, iridium, cinnabar, fluorite, peridot) have **no other dust source
in this pack** (Create's crushing wheels only double raw ore → crushed-ore;
there is no ingot/generic-dust recipe type). Stripping the hammers' own
craft recipes therefore silently orphaned the whole ore/ingot→dust pipeline
— the bug reported in #86. Fix: added the 5 ids to
`tool_consolidation_sweep.js`'s `TOOL_EXEMPT_ITEM_IDS` (same mechanism as
`tfmg:oil_hammer`), restoring the mod's unmodified 1:1 conversions (no
duplication path introduced). Full design rationale in DESIGN.md's #86
entry. Static-verified (`run_all.py` green, jar-confirmed ids/recipes); the
hammer crafting + JEI recipe display still needs `verify-in-game`.

## #67 — custom-mods convention established: `mods-src/<modid>/` (2026-07-23)

**Governance precedent, not just a #67 implementation note.** The prior #67
investigation (see DESIGN.md) concluded the Overgeared quality x Silent Gear
material bridge is not achievable as data/config/KubeJS — Silent Gear's
material assignment is a data component only its own recipe/stat code
populates, and Overgeared's forging recipes are static single-item results
with no way to carry it across. The owner authorized an exception to this
pack's "no new mods" rule specifically to hand-roll a small Java compat
mod, and set a **new standing rule alongside it: every custom-built mod for
this pack gets its own independent, Modrinth-publishable source tree**, not
inline Java mixed into `pack/`. This entry records that convention, using
the first such mod (`vppintegration`, the #67 bridge) as the worked
example — the next custom mod slots in beside it the same way.

**Layout.** `mods-src/<modid>/` is a fully self-contained NeoForge 1.21.1
project: its own `build.gradle`/`settings.gradle`/`gradle.properties`,
`src/main/java` + `src/main/resources` (mods.toml, mixins config, datapack
JSON), its own `README.md` (what it does, why it exists, build
instructions) and `LICENSE` (MIT, chosen since neither this pack nor its
other mod choices dictate a license for pack-original code). Nothing under
`mods-src/` is pack-specific glue that only makes sense inline — each
directory there must stand alone as a publishable mod.

**How a locally-built jar enters the pack build.** Every other mod in
`pack/manifest.json` is a resolved remote URL+hash (Modrinth, or CurseForge
CDN for the two mods with redistribution permission - see
`scripts/resolve_mods.py`'s own docstring). A `mods-src/` jar has no remote
host at all, so a third manifest `"source"` was added: `"local"`, paired
with a `"local_path"` field (repo-relative path to the already-`gradle
build`-produced jar, e.g. `mods-src/vppintegration/build/libs/
vppintegration-1.0.0.jar`). `resolve_mods.py`'s new `resolve_one_local()`
hashes whatever real jar already sits at that path (it does NOT invoke
gradle itself — this pipeline has never shelled out to a build tool for any
mod source) and writes a normal lock entry, with `"url"` set to the
repo-relative path string rather than an HTTP URL (satisfies
`check_lockfile.py`'s "non-empty url" rule without claiming a fetchable
one). `build_server.py` and `build_mrpack.py` both special-case
`local_path` present to copy that file directly instead of downloading —
`build_mrpack.py` additionally always treats a local mod as **bundled**
(embedded under the `.mrpack`'s `overrides/mods/`) since there is no
Modrinth-allowlisted host to reference by URL, same mechanism already used
for the two CurseForge-hosted mods.

**Not yet activated.** `vppintegration`'s source, build config, README, and
LICENSE are complete (PR #TODO), and the three pack scripts above support
`"source": "local"` end-to-end, but `pack/manifest.json`/`mods.lock.json`
do NOT yet have a `vppintegration` entry: the sandbox that authored the mod
had no JDK at all (not just no network), so no real jar exists yet to hash.
Adding a manifest entry without a real corresponding jar would either fail
`check_lockfile.py`'s consistency check or require a fabricated hash
pointing at nothing — both rejected as exactly the "ship something that
doesn't work" outcome the original #67 investigation flagged as out of
bounds. Follow-up (real build environment): run `gradle build` in
`mods-src/vppintegration/`, then re-run `resolve_mods.py` to add the real
manifest+lock entries and fold the mod into an actual pack build.
