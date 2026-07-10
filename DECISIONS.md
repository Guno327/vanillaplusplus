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
- `tfmg_stellaris_compat:replace_stellaris_loot` GlobalLootModifier WARN
  (`stellaris:heavy_ingot` unknown) — upstream version mismatch, unchanged
  by the Stellaris 1.4.25 bump.
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
