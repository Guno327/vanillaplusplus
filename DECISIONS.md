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

## Item 4 (mobility) — orchestrator calls on research verdicts

- **Primary mod: Create Stuff & Additions 2.1.4.a** (+ Create: Stuff &
  Netherite Additions 1.2): 4 native jetpack tiers map 1:1 onto Tiers 1-4
  (Copper→Andesite Age, Andesite→Brass, Brass→Precision,
  Netherite→Induction). Runner-up (Create Jetpack) rejected: hard Kotlin
  dependency, only 2 tiers, elytra-ingredient recipe needing patches.
- **Chest-slot contention accepted**: jetpacks are chestplates, competing
  with Silent Gear chestplates/Elytra/battlemage robes — same tradeoff
  shape as vanilla Elytra; documented, not worked around.
- **Starforged flight capstone is item-free and stage-bound**: KubeJS
  grants `mayfly` on `starforged_age` stage (stageAdded + loggedIn +
  respawned reassertion; revoke path if stage lost). Survives death by
  construction (`keepInventory: false` concern resolved). Not tied to any
  wearable; Curios stays reserved for item 5.

## Item 5 (curios) — orchestrator calls on research verdicts

- **Mod: Artifacts 13.2.1** (zero new hard deps; Curios 9.5.1 soft-detect).
  Runner-up Relics rejected (new hard dep, smaller pool, craft-first).
- Native loot injection silenced via empty-pool overrides of ALL its
  inject tables; this pack's 4-tier structure-loot buckets become the ONLY
  placement path (one rarity system, not two).
- **Duplicate-combine upgrade design**: 2x same artifact → same artifact +
  bonus stat via `minecraft:attribute_modifiers` component on the crafted
  result (generic across all 47 Java-coded abilities; items are
  component-free so no matching breakage). Capped; exact syntax verified
  by the implementing agent.

## Item 6 (mob variety) — endorsed judgment calls from implementation

- Born in Chaos data namespace is `born_in_chaos_v1` (NOT the Modrinth
  slug) — overrides written there; a slug-named path would silently no-op.
- **Charm accessories stripped along with weapons** (charmof_power/
  resistance/stealth/endurance/fury): permanent combat-stat accessories
  would compete with the skill system and item 5's Artifacts as the
  sanctioned accessory source. Endorsed by orchestrator.
- Flagged for live-play review: 41/45 Born in Chaos hostiles spawn via
  `neoforge:any` biome predicate (everywhere, all dimensions) — possible
  future spawn-tuning pass if the world feels samey; not blocking.

## Item 9 — Food overhaul (user decisions, FINAL — to be written into TODO.md at wave-2)

- **Diet mechanic: reward variety only** — Spice-of-Life-Carrot style
  permanent bonus hearts at distinct-foods-eaten milestones; NO repetition
  punishment, no food groups.
- **Content: Farmer's Delight ecosystem** (research verifying exact
  NeoForge 1.21.1 port + a Create automation bridge like Central Kitchen
  for our versions; KubeJS fallback assessed if the diet mod is dead on
  1.21.1).
- **Light tier gating**: basic farming/cooking free from Tier 0 (food is
  survival-critical); advanced stations/meals at Andesite/Brass Age.
- **Automation bar: every food chain fully Create-automatable end-to-end**;
  stations that can't be driven by Create get patched or the gap disclosed.
- Interaction flags for the implementer: FD meals inherit the economy's
  tier-0 default sell price (probably correct, deliberate look wanted);
  foods from Create Stuff & Additions/Naturalist must count toward diet
  variety totals.

## Item 10 — Tick accelerator (user decisions, FINAL — to be written into TODO.md at wave-2)

- **Model: classic Time-in-a-Bottle item** — passive real-time tick
  accrual; right-click a block to stack a temporary speed multiplier.
- **Gate: Brass Age (Tier 2)** — plain ProgressiveStages item lock.
- **Exclusions: Create kinetic blocks ONLY** (RPM/stress economy stays
  orthogonal — research checking for a Create block tag to blacklist
  against). **Spawners deliberately remain accelerable** — user explicitly
  declined that exclusion; synergy with Apothic Spawners upgrades is an
  intended late-game payoff, not an exploit to close.
- **Hard one-per-player** — not native to any TiaB mod; needs a KubeJS
  craft-enforcement layer (research designing it: re-craft after genuine
  loss should work; the jovian creative-crate duplication gap applies and
  stays disclosed like other unique items).

## Item 11 — Skill-tree overhaul (user decisions, FINAL — to be written into TODO.md at wave-2)

- **All 12 categories branch** (not just combat): swords, daggers,
  greatswords, longswords, spears, tachi, bows, magic, mining, running,
  swimming, building.
- **Shape: ~15 nodes each** — ~5-node shared trunk of general passives,
  then a fork into TWO 5-node spec paths.
- **Exclusivity: HARD but respeccable** — taking one path locks the other;
  respec exists (research verifying native support: connection schema,
  skillReplaceCooldown/maxPassiveSkills gamerules, reset commands).
- **Node effects: attribute modifiers ONLY** — no scripted procs.
- **Core design law: paths trade by stacking DIFFERENT FAMILIES OF
  UPSIDES — no node anywhere carries a downside.** Flagship example:
  swords spec into fast attacks vs slower deliberate hits; every weapon
  gets a topical equivalent. Path themes must be designed against the
  VERIFIED attribute inventory (especially which attributes Epic Fight's
  animation-driven combat actually respects — the research crux).

## Item 9 (food) — orchestrator calls on research verdicts (2026-07-10 ~00:50 UTC)

- **Adopt the full recommended stack**: farmers-delight 1.21.1-1.3.2,
  create-central-kitchen 2.5.0 + create-dragons-plus 1.11.2 (its required
  lib), spice-of-life-onion 1.5.6 + creativecore (its required lib),
  appleskin 3.0.9+mc1.21, ends-delight 2.6.1, extradelight 2.6.6.
- **Central Kitchen over Slice & Dice**: reuses base-Create blocks
  (Saw/Arm/Blaze Burner) instead of adding a bespoke automation block;
  avoids a Kotlin-for-Forge hard dep; converts all 75 FD cutting recipes
  to Saw recipes at runtime. Slice & Dice's sprinkler deferred as a
  possible future nice-to-have, NOT installed.
- **Rejected**: miners-delight, brewin-and-chewin (each drags a new hard
  library dep — fails the zero-new-deps bar for optional companions).
- **SoL-Onion config MUST ship with the `detriments` list empty/disabled**
  (the mod supports penalties; the user chose reward-only — this is a
  config obligation, verify on first boot).
- **No new tier locks needed** — gating falls out of existing iron/diamond
  locks (cooking pot/stove/skillet/iron knife are iron-gated → Andesite;
  diamond knife → Brass; automation is Brass via Arm/Deployer). One
  convention add: explicitly lock `farmersdelight:golden_knife` at Brass
  alongside the diamond knife for this pack's explicit-lock consistency.
- Boot-check obligations: Terralith wild-crop generation (tag-based,
  structurally sound), Central Kitchen Saw-conversion tool-requirement
  edge case, gen_economy tier-0 pricing for new foods (keep cheap).

## Item 10 (tick accelerator) — orchestrator calls on research verdicts (2026-07-10 ~00:50 UTC)

- **Adopt**: time-in-a-bottle-universal 6.5.4 (only viable TiaB-style mod
  on NeoForge 1.21.1; zero hard deps) + its companion fix addon
  (time-in-a-bottle-fix-tiab-fix / tiab-entity-fix-1.0.3 — required for
  crop/animal acceleration to work at all in modern versions).
- **Create-kinetics exclusion**: layer onto the mod's own
  `tiab:un_acceleratable` block tag (replace:false confirmed) via a KubeJS
  registry scan tagging every block whose BlockEntity subclasses Create's
  `KineticBlockEntity` (~39 base classes / ~90+ ids incl. addons — a hand
  list would rot). Fallback if the Rhino interop fails at boot: generated
  static id list. Spawners NEVER go in that tag (user decision).
- **One-per-player**: ItemEvents.crafted hook + live inventory scan (not a
  permanent flag — re-crafting after genuine loss must work) + manual
  ingredient refund (cancel() semantics unverified). Accepted, disclosed
  soft-enforcement gaps: stashed copies in external storage evade the
  scan; the jovian creative-crate duplication gap applies as it does to
  all unique items. Keep `max_rate_multi` at default (256x cap) per the
  server-performance mandate.

## Wave-1 integrator findings — orchestrator calls (2026-07-10)

- `create_nj` (Netherite Additions) ships a SECOND netherite jetpack
  duplicating `create_sa`'s — integrator locked BOTH at induction_age
  (closing the tier bypass). **Call: fold into the item 3 dedup pattern at
  wave 2** — remove/redirect the duplicate jetpack recipe, keep create_nj
  installed for its Exoskeleton.
- Items 3/7/8 committed; item 4/5/6 mod scaffolding committed and
  boot-tested. Wave-2 integrator picks up from HANDOFF.md's "Wave-2
  scaffolding" section.

## Item 5 implementation outcomes — endorsed deviations (2026-07-10 ~01:10 UTC)

- Artifacts' master tag holds **48** items, not research's 47 (counted
  programmatically by the implementing agent).
- **Upgrade combines use `curios:attribute_modifiers`**, not vanilla's
  component: vanilla equipment modifiers never apply in Curios slots;
  Curios ships a field-for-field-identical parallel DataComponentType
  (verified via javap against Curios 9.5.1). The one held (not worn)
  artifact — umbrella — uses the vanilla component. Endorsed: correct
  ground-truth deviation from the original design.
- `everlasting_beef`/`eternal_steak` excluded from combines (consumables,
  no equip slot; they already have Artifacts' own smelt-upgrade path).
- Bonus stat is defined per Curios slot type (head/necklace/hands/feet/
  belt/curio), not per item; repeat combines are implicitly capped (output
  components are fixed, second combine reproduces the same result).
- 46 combine recipes total under `vanillaplusplus:artifact_upgrade/*`.

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

Research prototype-verified (artifacts at /tmp/vpp-research/headlessmc/ +
~/.minecraft/ ready to extend; HeadlessMC pinned at launcher 2.9.0 — repo
renamed to headlesshq/headlessmc, old docs 404, treat upgrades cautiously).

- **Test layers adopted**: L0 boot smoke (scripts/tests/l0_boot_smoke.sh —
  formalizes the existing grep discipline + the known-noise baseline
  recorded above); L1 = KubeJS `/vpp_selftest` command + runner
  (l1_selftest.py via cmd_fifo or RCON) implementing the 20-assertion
  list from the research brief (data/parse/count/resolve assertions +
  sell/leaderboard round-trips); L2 = HeadlessMC client smoke with the
  full side!=server mod set (catches client-only mixin crashes);
  L3 = client join test — DEFERRED until L1/L2 are solid (join mechanism
  unproven; highest cost, least proven value).
- **Implementation order**: L0+L1 first, then L2, then server bundle,
  L3 last.
- **GameTest rejected** (needs custom Java; pack has none by design).
  **Protocol bots rejected** (NeoForge handshake, confirmed dead end).
- **online-mode call**: the SHIPPED server bundle keeps
  `online-mode=true`. Any L3 join testing uses a separate test-only
  server.properties profile with it flipped false — never the default.
- **RCON**: enabling it is left to the release integrator's judgment for
  the L1 runner (fifo works today; RCON gives request/response).
- **Server bundle**: new scripts/build_server_bundle.py — reuse
  build_server.py, zip server/ minus world//logs//cmd_fifo, include
  run.sh/libraries/, eula handled as a first-run prompt (NOT pre-accepted
  silently... a loud documented pre-acceptance is acceptable if the
  implementer finds first-run friction too high; either way it must be
  explicit in the bundle README).
- **Versioning**: single source of truth — pack/VERSION file read by both
  build_mrpack.py (currently hardcodes 0.9.0) and build_server_bundle.py;
  version embedded in both bundle filenames. Initial release target:
  bump to 1.0.0 at cut time.
- L1 caveat recorded honestly: the 20-assertion list is sketched against
  expected KubeJS API surface, not yet verified against the installed
  jar — the implementing agent verifies per assertion and drops/replaces
  what Rhino can't reach, disclosing each.

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

While the release integrator owns main/server, three parallel accelerators
run in isolation:
- **Items 10 and 11 pre-implemented in git WORKTREES** (own branches,
  static validation only — no boots, no main-tree writes, read-only
  access to the main repo's server/mods jars). Merged + boot-verified by
  a post-release integrator, NOT before the 1.0.0 cut. Provisional
  balance calls made to unblock item 11: XP formula unchanged (accept the
  ~50% longer grind for 15 nodes; playtest later), respec initially free
  (cost/cooldown friction deferred to a balance pass) — both explicitly
  provisional.
- **L3 join-mechanism research** runs against its OWN /tmp server copy on
  port 25566 with online-mode=false (test-only profile per the recorded
  rule) and its own isolated HeadlessMC game dir — explicitly forbidden
  from ~/.minecraft (in use by the release integrator's L2) and the repo
  server/.
- Release-wave finding worth its own line: **noisiumed had shipped a
  non-functional Fabric jar since Phase 9** (Modrinth "primary" file flag
  unreliable when a version bundles multi-loader jars) — resolver fixed to
  prefer loader-matched jars; the pack's worldgen-noise optimizer loads
  for the first time ever in 1.0.0.

## Item 11 pre-built — branch ready for post-release merge (2026-07-10 ~03:10 UTC)

- **Branch: `worktree-agent-a77d7c3d4e95059c7`** (2 commits: generator
  rewrite + regenerated 12×15-node trees; skill_respec.js). Static
  validation complete: all 61 JSON files parse, every category has
  exactly 15 nodes / 14 normal edges / 1 exclusive edge between fork
  entries, zero `epicfight:` attributes anywhere, all SkillsAPI
  signatures javap-verified (including bytecode confirmation of the
  orphaned-node gotcha — unlocked skills return UNLOCKED before the
  exclusion check, so respec MUST lock all 5 path nodes, which it does).
- Endorsed deviations: /respec uses 12 literal subcommands (no
  Commands.argument precedent in this codebase to verify unbooted);
  Skill$State compared via string, not nested-class loading.
- **Post-release merge checklist** (boot-verify after merging the
  branch): no "[puffish_skills] Data pack could not be loaded" at boot;
  in-game exclusive-edge behavior (unlock a0 → b0 EXCLUDED, a-path opens,
  b-path stays shut); /respec full-path lock + point refund + re-pick;
  /respec-with-nothing-committed says "nothing to respec" without
  throwing; L0/L1 suites still green.

## Item 10 pre-built — branch ready for post-release merge (2026-07-10 ~03:25 UTC)

- **Branch: `worktree-agent-ae58d0ccfdfb4ce35`** (3 commits: manifest +
  lockfile for tiab-universal 6.5.4 + tiabfix; brass_age.toml lock on
  `tiab:time_in_a_bottle`; tick_accelerator.js with both mechanisms).
- Ground-truthed: exact refund recipe (3 gold, 2 diamond, 2 lapis, clock,
  glass bottle); the un_acceleratable tag is replace:false and actively
  read by the mod; fix addon modId `tiabfix` (its jar-internal version
  string says 1.0.0 vs Modrinth's 1.3.0 — cosmetic mismatch, both pinned).
- Two verification wins that shaped the implementation: KubeJS's
  ItemCraftedKubeEvent is NOT cancellable (confirmed — enforcement voids
  the stack via count=0 + refunds, exactly the fallback DECISIONS.md
  anticipated), and NeoForge fires the craft event BEFORE the crafted
  item reaches the inventory (verified in ResultSlot bytecode), so the
  live one-per-player scan cannot false-positive on the bottle being
  crafted.
- **Post-release merge checklist**: registry-scan runs at tag-gen time
  with a sane logged count; tagged Create block genuinely refuses
  acceleration in-game; tiabfix mixins apply + crops/animals accelerate;
  double-craft (incl. shift-click batch) voids+refunds the second bottle
  and re-craft after genuine loss works; spawners remain accelerable.
- Note for merge order: BOTH pre-built branches (items 10 + 11) touch
  pack/kubejs/server_scripts/ additively and item 10 touches
  brass_age.toml/manifest — merge each with a boot test between, item
  order at the post-release integrator's discretion.

## Post-release merges (2026-07-10)

Both pre-built branches merged into `main` one at a time with a full
L0+L1 boot test between, per their post-release merge checklists above.
Merge order chosen: **item 11 first** (pure additive data + one new
script, no manifest/lockfile churn), **item 10 second** (manifest/
lockfile/new-jars, more moving parts) — DECISIONS.md left the order to
the integrator's discretion, both branches touch
`pack/kubejs/server_scripts/` additively but on disjoint files, so
neither ordering risked a conflict.

- **Item 11 merge** (`ec2ca5f`, `--no-ff`, no conflicts): skill-tree
  overhaul + `/respec`. L0 PASS (78 server mods, 0 KubeJS errors/
  warnings, no unbaselined WARN/ERROR, clean stop); confirmed boot log
  shows `[puffish_skills] Data pack \`puffish_skills\` loaded
  successfully!` (i.e. NOT the failure string the checklist named). L1
  PASS (17/17, 4 skipped — player-online-only assertions, expected in a
  console-only run).
- **Item 10 merge** (`d918f83`, `--no-ff`, no conflicts): Time-in-a-
  Bottle tick accelerator. First L0 run technically exited PASS but
  grepping the log per the checklist ("registry-scan runs at tag-gen
  time with a sane logged count") caught a real, live bug: the scan was
  throwing `TypeError: redeclaration of var BuiltInRegistries` every
  single boot and silently falling back to the disclosed static 38-id
  list — the checklist's real scan never actually ran. Root cause:
  `tick_accelerator.js`'s `ServerEvents.tags` callback (registry scan +
  its `while` loop) and its `ItemEvents.crafted` callback (one-per-player
  enforcement) both declared per-invocation/per-iteration bindings with
  `const`, hitting the exact installed-Rhino limitation this file's own
  "Release engineering" Rhino-bugs note already documents and previously
  fixed in `selftest.js`/`leaderboard.js` — `const` doesn't get fresh
  scoping across repeat invocations of the same try/catch or loop body on
  this KubeJS/Rhino build. Fixed forward (commit `2e60738`, same session,
  not a separate agent) by converting every such `const` to `let` in both
  callbacks, matching the established codebase workaround. Re-verified:
  the registry scan now genuinely runs and logs `tagged 173 block(s) into
  tiab:un_acceleratable out of 3604 blocks scanned (2 spawner id(s)
  explicitly protected from exclusion)`. Re-ran L0 (PASS, 80 server mods
  including tiab-neoforge-6.5.4.jar + tiab-entity-fix-1.0.3.jar freshly
  downloaded) and L1 (PASS, 17/17, 4 skipped) clean after the fix.
  Confirmed benign: Stellaris `heavy_ingot` WARN present as expected;
  tiabfix's two mixin WARNs (generic refmap-could-not-be-read dev-env
  boilerplate seen on every mod in this pack; an Applied-Energistics-2
  compat mixin harmlessly not finding its target since this pack has no
  AE2 installed — unrelated to the crop/animal acceleration the fix mod
  exists for).
- Both merges verified no stray `java`/`tail -f cmd_fifo` processes
  before the next boot (no `DirectoryLock` false failures hit this pass).
- **L2 HeadlessMC client harness checked and found not applicable**: it's
  a pure mod-set-assembly + launch + crash-detection smoke test (see
  `scripts/tests/l2_client_smoke.py`) — it doesn't simulate any player
  action (no bot, no scripted commands/crafting/skill-unlocking), so it
  cannot exercise either branch's in-game-only checklist items. Per this
  task's explicit instruction, no new test infrastructure was built to
  cover this gap.
- **Needs in-game verification** (could not be checked statically, via
  boot log, or via L0/L1/L2 — collected here, also filed under TODO.md
  items 10/11):
  - Item 11: in-game exclusive-edge behavior (unlock a0 → b0 excluded,
    a-path opens/b-path shut); `/respec` full-path lock + point refund +
    re-pick; `/respec` with nothing committed replies "nothing to
    respec" without throwing.
  - Item 10: tagged Create block genuinely refuses acceleration in-game;
    tiabfix mixins actually accelerate crops/animals in play; double-
    craft (incl. shift-click batch) void+refund and re-craft-after-
    genuine-loss both work as coded; spawners remain accelerable in
    practice.
- Neither branch's worktree was deleted — both retained per instruction.

## Standing implementation notes

- Incidental Stellaris bump rode along with the item 7 resolver run
  (1.4.24 → 1.4.25) — watch its known heavy_ingot WARN in the next boot.
- Wave-2 integrator duties queue: fold in item 5 + item 6 agent outputs,
  boot-test, commit items 4/5/6, transcribe items 9/10/11 from this file
  into TODO.md, act on food/tick/skill research briefs (spawn
  implementation agents), add `.gitignore` entry only if checkpoint files
  ever move into the repo (they currently live in /tmp).

## GitHub as ground truth (2026-07-10, user directive)

The project's private GitHub repo (`https://github.com/Guno327/
vanillaplusplus`, remote `origin`) is now the ground truth for outstanding
bugs and needs-in-game-verification items, superseding this file's own
lists for that purpose going forward:

- **Issues supersede the needs-in-game-verification lists.** The "Post-
  release merges (2026-07-10)" section above's two needs-in-game-
  verification bullets (item 11's skill-tree/respec checks, item 10's
  Time-in-a-Bottle checks) now live as GitHub issues **#1** ("Verify item
  11: skill-tree exclusive fork + /respec") and **#2** ("Verify item 10:
  Time-in-a-Bottle behaviors"). The prose above is left as historical
  record (per this file's own convention of not rewriting history) — do
  not re-derive or duplicate those checklists locally; check the issues.
  A third verify-in-game issue, **#3** ("Verify: rendering-correctness
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
  `vanilla-plus-plus-*-1.0.0.mrpack`/`.zip` bundles sitting at the repo
  root (both gitignored, untracked build output — confirmed via `git
  ls-files`) are superseded by this decision and should be deleted and
  regenerated as `0.1.0` bundles by whichever wave cuts the actual
  release; they are left in place by this pass since deleting build
  artifacts is out of scope for a docs-only update.
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
