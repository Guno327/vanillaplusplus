# TODO

Brainstormed additions, queued for a future auto-wakeup session to implement.
Each item below has already been scoped with the user — implement per the
recorded decisions, don't re-litigate them, but DO still verify any named
mod/mechanism against the actually-installed jar before building on it
(this project's standing "ground truth over assumption" rule) since some
items below were confirmed from memory, not a live check.

## 1. ✅ DONE — Ore veins for simpler/richer ore generation

**Implemented** via Create Ore Excavation. Its native Iron/Diamond/
Netherite drill ladder was mapped onto this pack's Andesite/Brass/
Precision Age tiers; three new vein types (allthemodium/vibranium/
unobtainium) were added for the late-game meta-material tier, gated
behind the Netherite Drill. See DESIGN.md's "Ore veins via Create Ore
Excavation" section for the full writeup.

## 2. ✅ DONE — Post-Tier-4 endgame automation deepening (TFMG + storage chase + "infinite" capstones)

**Implemented.** A curated 5-tier TFMG milestone ladder (Aluminum ->
Steel -> Petrochemical -> Electrical -> Combustion Age) mapped onto
Tiers 5-9; the three "infinite" capstones turned out to already exist as
recipe-less creative blocks in Create/Refined Storage, gated at Jovian
Frontier with new survival recipes rather than built from scratch. One
disclosed, unfixed gap: `create:creative_crate` has no guard against
duplicating a unique item (now GitHub issue #7). See DESIGN.md's
"Post-Tier-4 endgame automation deepening" section for the full writeup.

## 3. ✅ DONE — Duplicate-resource consolidation audit

**Implemented.** Zinc/aluminum/lead/nickel (AllTheOres -> Create/TFMG) and
steel (Stellaris -> TFMG) hard-consolidated via redirected smelting/
crafting/loot-table overrides plus `dedup.js`; ATO's overworld-only ore
worldgen neutralized per-metal; closed a real tier-bypass hole on
`alltheores:aluminum_ingot`. TFMG-vs-RefinedStorage silicon checked and
left alone (genuinely different resources). See DESIGN.md's
"Duplicate-resource consolidation audit" section for the full writeup.

## 4. ✅ DONE — Personal mobility progression: jetpack → persistent creative flight

**Implemented.** Create Stuff & Additions' native 4-tier jetpack ladder
mapped 1:1 onto Andesite/Brass/Precision/Induction Age; a Starforged Age
(Tier 5) capstone grants item-free, stage-bound persistent
`abilities.mayfly`, surviving death by construction since the grant is
stage-driven not item/effect-driven. Also closed the `create_nj`
duplicate-jetpack tier-bypass hole (folded into item 3's dedup pattern).
See DESIGN.md's "Personal mobility: jetpack -> persistent creative
flight" section for the full writeup.

## 5. ✅ DONE — Curios as a discoverable/upgradeable player-ability system

**Implemented** via Artifacts 13.2.1. Its own native loot injection was
silenced entirely so this pack's existing 4-tier structure-loot rarity
buckets become the sole placement path (no tier lock, by design); a
48-item curation table across Common/Uncommon/Rare/Epic; a
duplicate-combine upgrade mechanic (46 recipes) using Curios' own
`curios:attribute_modifiers` component rather than vanilla's. See
DESIGN.md's "Curios as a discoverable/upgradeable player-ability system"
section for the full writeup.

## 6. ✅ DONE — Hostile + passive monster/animal variety, with limited unique drops

**Implemented** via Creeper Overhaul 4.0.6 + Born in Chaos 1.7.6 (hostile)
+ Naturalist (passive) — Alex's Mobs ruled out for its unique-drop-heavy
design. Every new mob's loot patched onto this pack's shared canonical
drop set (32 entity loot overrides); unique weapons/armor/charms stripped;
`mob_scaling.js` extended with 61 new hostile ids. Flagged for live-play
review, not blocking: 41/45 Born in Chaos hostiles spawn everywhere with
no biome tuning (now GitHub issue #5). See DESIGN.md's "Hostile + passive
mob variety, limited unique drops" section for the full writeup.

## 7. ✅ DONE — Block-based chunk loading (Create-native, replacing FTB Chunks' menu flow)

**Implemented** via Create: Power Loader. Two loader tiers locked at
Andesite/Brass Age; force-loading stops natively the instant the parent
kinetic network stops (no running-cost scripting needed or possible); FTB
Chunks' own menu-based force-loading fully disabled, claims/protection
untouched. No hard loaded-chunk cap set, per the user's decision leaving
that guardrail open. See DESIGN.md's "Block-based chunk loading via
Create: Power Loader" section for the full writeup.

## 8. ✅ DONE — Leaderboards: wealth / tier / level comparison

**Implemented.** `/leaderboard <wealth|tier|level> [players|teams]` chat
command in `leaderboard.js`; wealth = coin count + Numismatics bank
balance, tier = ProgressiveStages stage count, level = summed Pufferfish
Skills per-category levels, teams via FTB Teams API. All three mod APIs
wrapped with honest "unavailable" fallbacks, never a silent vanilla-XP
substitute. See DESIGN.md's "Leaderboards: wealth / tier / level" section
for the full writeup.

## 9. NOT STARTED — DEFERRED POST-RELEASE — Food overhaul (diet variety)

**Ask**: a food/diet overhaul rewarding meal variety, built on Farmer's
Delight and its ecosystem, fully Create-automatable end to end.

**Decisions (finalized, user session 2026-07-10)**:
- **Diet mechanic: reward variety only** — Spice-of-Life-Carrot style
  permanent bonus hearts at distinct-foods-eaten milestones. **No**
  repetition punishment, no food groups — purely additive.
- **Content: the full Farmer's Delight ecosystem**, orchestrator-adopted
  after research (verified against NeoForge 1.21.1, not assumed): farmers-
  delight 1.21.1-1.3.2; create-central-kitchen 2.5.0 (chosen over Slice &
  Dice — reuses base-Create blocks (Saw/Arm/Blaze Burner) instead of a
  bespoke automation block, avoids a Kotlin-for-Forge hard dep, converts all
  75 FD cutting recipes to Saw recipes at runtime) + create-dragons-plus
  1.11.2 (its required lib); spice-of-life-onion 1.5.6 (the diet-variety
  mechanic itself) + creativecore (its required lib); appleskin 3.0.9+mc1.21
  (hunger/saturation UI); ends-delight 2.6.1; extradelight 2.6.6. Rejected:
  miners-delight, brewin-and-chewin (each drags a new hard library
  dependency — fails the zero-new-deps bar for optional companions).
- **Light tier gating**: basic farming/cooking free from Tier 0 (food is
  survival-critical, shouldn't be gated); advanced stations/meals at
  Andesite/Brass Age. No new explicit tier locks are expected to be needed
  — gating should fall out of existing iron/diamond material locks
  (cooking pot/stove/skillet/iron knife are iron-gated → Andesite; diamond
  knife → Brass; automation is Brass via Arm/Deployer). One explicit add
  planned regardless, for this pack's lock-everything-explicitly
  convention: `farmersdelight:golden_knife` locked at Brass alongside the
  diamond knife.
- **Automation bar**: every food chain must be fully Create-automatable
  end-to-end; any station that can't be driven by Create gets patched, or
  the gap gets disclosed rather than silently left unautomatable.
- **SoL-Onion config MUST ship with its `detriments` list empty/disabled**
  — the mod supports penalties, but the user chose reward-only. This is a
  config obligation to verify on first boot, not just a code change.
- Interaction flags for the implementer: FD meals inherit the economy's
  tier-0 default sell price unless that looks wrong on inspection; foods
  from Create Stuff & Additions/Naturalist must count toward diet-variety
  totals, not just base-FD foods.

**Open for the implementing session to resolve**:
- Boot-check obligations flagged in advance: Terralith wild-crop generation
  (tag-based, structurally sound per research but unverified live),
  Central Kitchen's Saw-conversion tool-requirement edge case, and
  `gen_economy.py` tier-0 pricing for the new foods (keep cheap).
- Exact bonus-heart milestone curve (how many distinct foods per heart,
  cap) — not pinned down in the decision session.

## 10. ✅ DONE — Tick accelerator (Time in a Bottle)

**Merged into main 2026-07-10** (commits `6cc3194`/`cbd18e6` via `--no-ff`
merge `d918f83`, fix-forward `2e60738`). time-in-a-bottle-universal 6.5.4
+ tiabfix added, `tiab:time_in_a_bottle` locked at Brass Age;
`tick_accelerator.js` adds a Create-kinetics registry-scan exclusion
(spawners deliberately left accelerable) and hard one-per-player craft
enforcement (void + ingredient refund). Boot-testing caught and fixed
forward a real Rhino `const`-scoping bug in the registry scan (this
pack's documented Rhino limitation — see DESIGN.md's Release engineering
section); post-fix the scan genuinely runs (173 blocks tagged out of
3604 scanned). L0+L1 green after the fix. No DESIGN.md section exists for
this item (merged after the last transcription pass) — see DECISIONS.md's
"Item 10/11 pre-built branches + post-release merges" section for
ground-truthed implementation facts not repeated here. **Needs in-game
verification**: GitHub issue #2.

## 11. ✅ DONE — Skill-tree overhaul (all 12 categories)

**Merged into main 2026-07-10** (commits `6970b2b`/`c64b2f9` via `--no-ff`
merge `ec2ca5f`). All 12 Pufferfish Skills categories reworked into a
5-node shared trunk forking into two hard-exclusive 5-node specialization
paths (attribute-modifiers only, no scripted procs, no node ever carries
a downside); exclusivity native to puffish_skills via an
`exclusive.bidirectional` connection group; new `/respec <category>`
command locks the full abandoned path via `SkillsAPI` (including the
orphaned-node gotcha: unlocked skills report UNLOCKED before the
exclusion check, so a partial lock would leave stray active nodes — this
implementation locks the whole path). Boot-tested clean (L0+L1 green,
17/17 assertions). No DESIGN.md section exists for this item — see
DECISIONS.md's "Item 11 (skill trees) — research verdicts" section for
the full attribute-inventory design rationale (the verified 12-category
attribute table and the Epic Fight attribute-compatibility crux). **Needs
in-game verification**: GitHub issue #1.

## 12. NOT STARTED — Release follow-ups (post-1.0.0)

**Ask**: cleanup/extension items surfaced by shipping release 1.0.0 (see
DESIGN.md's "Release engineering" section for full context on each).

- **L3 — live client join test.** Deliberately deferred from the 1.0.0 test
  suite (L0 boot smoke / L1 self-test / L2 HeadlessMC client smoke all
  shipped and green). The join mechanism itself is unproven — protocol bots
  were already confirmed a dead end against NeoForge's handshake — so this
  is genuinely new implementation work, not a small addition. If picked up:
  use a separate test-only `server.properties` profile with
  `online-mode=false`; never flip that on the shipped default profile.
- **Rendering-correctness spot-check** — now GitHub issue **#3**. L0-L2
  prove mod loading and server-side data/registry correctness, but nothing
  looks at an actual rendered frame (Create visuals, GeckoLib animation,
  Epic Fight combat, ImmediatelyFast/Staff-of-Physics). See the issue,
  not this bullet, for current status.
- **Residual Rhino const-in-loop scoping risk** — now GitHub issue **#8**.
  Fixed everywhere it was actually hit this release (`selftest.js`,
  `leaderboard.js`); two `for (const x of ...)` forms elsewhere
  (`economy.js`'s `payCoins`, `selftest.js`'s own coin helper) remain
  unverified. See the issue, not this bullet, for current status.
- **MoreCulling long-term watch.** Its `neoforge.mods.toml` minecraft-
  version range is literally `[1.21,1.21.1)`, textually excluding exact
  1.21.1 — it loaded fine in this release's L2 HeadlessMC smoke test (not
  a false alarm, matching JEI's identical-range precedent), but a future
  MoreCulling update could tighten that range for real. Re-run
  `scripts/tests/l2_client_smoke.py` after any MoreCulling version bump;
  its own built-in contingency (drop from manifest/lockfile, not
  pin/patch) already fires automatically if it ever does fail to load.
- **`noisiumed`-class resolver bugs in other mods.** `resolve_mods.py`'s
  `pick_file()` was fixed this release after discovering `noisiumed` had
  silently shipped a non-functional Fabric jar since Phase 9 (Modrinth's
  per-file `"primary"` flag isn't reliable when a single version bundles
  multi-loader jars). The fix is loader-name-matching, applied pack-wide on
  the next `resolve_mods.py` run, but it's worth explicitly re-running the
  resolver once and diffing `mods.lock.json` after any future manifest
  change, in case another mod has the same latent issue that just hasn't
  been noticed yet (only `noisiumed` was affected as of this release, per
  a full lockfile diff this session).
