# TODO

Brainstormed additions, queued for a future auto-wakeup session to implement.
Each item below has already been scoped with the user — implement per the
recorded decisions, don't re-litigate them, but DO still verify any named
mod/mechanism against the actually-installed jar before building on it
(this project's standing "ground truth over assumption" rule) since some
items below were confirmed from memory, not a live check.

## 1. ✅ DONE — Ore veins for simpler/richer ore generation

**Implemented** via Create Ore Excavation (verified match for the user's
"Create: Ore Excavation" guess). See `DESIGN.md`'s "Ore veins via Create
Ore Excavation" section for the full writeup: the mod's own Iron/Diamond/
Netherite drill ladder was mapped directly onto this pack's existing
Andesite/Brass/Precision Age tiers, and three new vein types (allthemodium/
vibranium/unobtainium) were added for the late-game meta-material tier,
gated behind the Netherite Drill (Precision Age) plus the pre-existing
ingot-level lock. Boot-tested clean, committed. Original scoping notes
kept below for reference.

**Ask**: use Create-ecosystem "ore veins" to supply a simpler way to
generate ore-type resources, instead of relying solely on manually-placed
vanilla ore scatter + player-built Create drill contraptions
(`DESIGN.md`'s existing "Resource infinity" section, Phase 8).

**Decisions**:
- **Mechanism**: likely **Create: Ore Excavation** (a Create-family addon
  adding large excavatable underground ore vein deposits, dug out with
  drills/excavators) — this was the user's leading guess, not yet verified
  against Modrinth/the actual jar. **First implementation step**: confirm
  this mod actually exists on Modrinth for NeoForge 1.21.1 and matches
  this description before committing to it; if it doesn't fit, fall back
  to extending whatever feature Create itself already uses to place its
  own zinc ore, per the session's second-choice option.
- **Ore scope**: cover vanilla ore tiers (iron/gold/diamond/ancient
  debris/etc.) **and** Create's own materials (zinc, etc.) **and** the
  late-game meta-material tier (Allthemodium/Vibranium/Unobtainium) —
  i.e. veins should span the entire tier ladder, not just early game.
- **Tier gating**: richer/rarer veins should be gated the same way
  everything else in this pack is — tied into the existing dimension/
  distance-from-spawn/player-tier difficulty scaling already built for
  mob scaling (`pack/kubejs/server_scripts/mob_scaling.js`) and the
  structure loot-rarity tiers (`scripts/gen_structure_loot.py`), so
  better veins show up farther out / deeper / in harder zones, consistent
  with the rest of the pack rather than a bolted-on separate system.
- **Purpose** (all three, not mutually exclusive):
  1. Replace/simplify manual mining as an early-game ore source.
  2. Feed the "resource infinity" automation story — gives the existing
     drill-contraption automation pattern something structured to target
     instead of arbitrary strip-mined terrain.
  3. Double as an exploration reward hook, same spirit as the structure
     loot-rarity scaling just shipped (rarer/deeper veins = better payoff).

**Open for the implementing session to resolve**: exact mod/version to
add, whether vein *richness* or vein *location* (or both) is what scales
with tier, and whether this needs its own KubeJS scaling script (mirroring
`mob_scaling.js`'s dimension+distance+player-tier formula) or can reuse
config-only tuning from the mod itself.

## 2. ✅ DONE — Post-Tier-4 endgame automation deepening (TFMG + storage chase + "infinite" capstones)

**Implemented.** See `DESIGN.md`'s "Post-Tier-4 endgame automation
deepening" section for the full writeup: a curated 5-tier TFMG milestone
ladder (Aluminum -> Steel -> Petrochemical -> Electrical -> Combustion
Age) mapped onto Tiers 5-9; the RS storage chase was verified to have no
native tier above 64k and honestly scoped down rather than inventing one;
all three "infinite" capstones turned out to already exist as fully-
functional, recipe-less creative blocks in Create/Refined Storage
(`create:creative_motor`, `create:creative_crate`, `refinedstorage:
creative_storage_block`/`creative_fluid_storage_block`) - new survival
recipes were added and gated at Jovian Frontier rather than building
custom infinite-behavior blocks from scratch. One real gap disclosed and
left open: `create:creative_crate` has no technical guard against being
filtered to duplicate a genuinely unique item, violating this pack's own
resource-infinity exemption - flagged, not fixed. Boot-tested clean,
committed. Original scoping notes kept below for reference.

**Ask**: right now Tiers 5-9 (Starforged Age through Jovian Frontier) are
pure travel gates — each unlocks the next planet's dimension and locks a
couple of items, but adds zero new automation progression (confirmed by
re-reading `pack/config/ProgressiveStages/tier6_lunar_frontier.toml`
through `tier9_jovian_frontier.toml`: only item/dimension locks, no
"Create milestone"-equivalent). Storage/autocrafting (Refined Storage) also
hard-caps at Induction Age's 64k/Advanced Processor — nothing scales past
Tier 4. TFMG (Create: The Factory Must Grow) is installed only as a
dependency bridge for Stellaris compat; none of its own machines are used
anywhere. The user wants Tier 4+ to become the pack's real "build ever-more-
complex automation for ever-harder recipes" endgame loop, leaning heavily
on TFMG, with Refined Storage's capacity chase continuing upward and three
ultra-endgame "infinite" capstone items (storage / energy / all-resources)
as the true final rewards.

**Decisions**:
- **Tier structure**: mirror the existing pattern — each of Tiers 5-9
  should get its own named TFMG/automation milestone alongside its planet/
  dimension unlock, the same way Tiers 0-4 pair a Create milestone with
  each stage in the tier ladder table. Reaching a planet should also mean
  reaching the next automation tier, not just the next destination.
- **Storage chase**: keep climbing raw Refined Storage disk capacity past
  Induction Age's 64k — continue the existing 1k→4k→16k→64k pattern
  upward (e.g. 256k, 1M, beyond), each new capacity tier gated behind a
  TFMG-produced material (continuing "previous tier's stuff necessary for
  the next tier's stuff"). **Needs verification at implementation time**:
  confirm what capacity tiers Refined Storage 2.0.9 actually natively
  supports past 64k before committing to specific numbers — may need a
  custom KubeJS-defined disk tier if RS's own ceiling is lower than what
  this chase needs.
- **The three "infinite" capstones** (infinite storage / infinite energy /
  infinite all-resources): each is a single, ultra-rare craftable item or
  block — the true final-tier reward, requiring a deep, fully-automated
  TFMG+Create production chain to produce even one. Not spread across
  tiers as incremental unlocks; these sit at the very end of the
  progression as the actual "you've mastered the automation game" payoff.
  - "Infinite all-resources" respects the existing Phase 8 exemption:
    covers every *automatable* resource, but genuinely unique items (boss
    trophies, one-off structure/dungeon rewards) stay one-of-a-kind
    forever, same rule as everything else in the pack.
  - "Infinite energy": presumably an FE output framed as effectively
    uncapped/very large rather than literally infinite in a
    balance-breaking sense — exact number/mechanism still open, needs
    design work at implementation time.
  - No per-player vs. shared-team restriction — build it so either mode
    works naturally depending on how a given group chooses to organize
    their factory, don't hard-code one or the other.

**Open for the implementing session to resolve**:
- Full inventory of what TFMG 1.1.1 (the version this pack is pinned to,
  see the space-travel section's dependency-range note) actually contains
  — needs a real decompile/`jar tf` pass, not assumption, before designing
  the milestone chain. This is a much bigger unknown than item 1's mod
  identity check.
- The actual recipe chains for each new automation tier and the three
  capstones — this is a substantial design task (analogous in scope to
  the original Phase 8 space-travel tier design), not a quick config edit.
- Whether any of this needs new KubeJS scripting (e.g. a custom "infinite"
  FE-generation block/behavior) vs. pure recipe-gating through existing
  mod items.
- Narrative/trigger naming for the new sub-milestones within each existing
  Tier 5-9 stage (each stage currently has one dependency chain entry;
  decide whether new automation milestones become their own
  ProgressiveStages stages inserted into the ladder, or stay as ungated
  "soft" progression within an existing stage).

## 3. ✅ DONE — Duplicate-resource consolidation audit

**Implemented.** See `DESIGN.md`'s "Duplicate-resource consolidation
audit" section for the full writeup: zinc/aluminum/lead/nickel
(AllTheOres -> Create/TFMG) and steel (Stellaris -> TFMG) hard-
consolidated via redirected smelting/crafting/loot-table datapack
overrides plus `pack/kubejs/server_scripts/dedup.js` for additive tag
cleanup; ATO's overworld-only ore worldgen neutralized per-metal (nether/
End variants kept since no canonical source covers those dimensions);
Stellaris's overworld steel ore removed outright, its moon steel ore
surgically dropped from a shared feature list. The aluminum consolidation
closes a real tier-bypass hole (`alltheores:aluminum_ingot` had no
ProgressiveStages lock, letting players skip the Tier 5 gate on
`tfmg:aluminum_ingot`). Bounded sweep: Stellaris-vs-TFMG steel implemented
(clean case); TFMG-vs-RefinedStorage silicon checked and left alone
(genuinely different resources - different tag namespaces, ingot vs. raw
material, no shared recipe chain). No orphaned tier-lock/pricing
references found. Boot-tested clean, committed. Original scoping notes
kept below for reference.

**Ask**: with ~40 mods installed, some likely add overlapping/duplicate
versions of the same underlying resource (raw ores, but also potentially
overlapping tool/equipment lines) — these should be found and consolidated
down to one canonical item each, not left sitting side by side.

**Decisions**:
- **Merge method**: hard consolidation, not tag-based interop. Pick one
  canonical item per duplicated resource; remove/hide the others via
  KubeJS and redirect their ore blocks/loot tables/recipes to produce the
  canonical item instead. This pack already has precedent for this exact
  pattern — Allthemodium's own native tools/armor/weapons were fully
  removed via KubeJS in Phase 10, keeping only its raw materials, with
  everything crafting through Silent Gear instead.
- **Scope**: broadest reasonable reading — not just raw ores/ingots/dusts/
  nuggets, but any duplicated item *category* across mods, including
  overlapping tool/equipment lines, not only resource nodes.
- **Which mods**: no specific overlap suspected yet — this needs a full
  audit across all ~40 installed mods' registered items from scratch, not
  a targeted check of a couple of suspected pairs.
- **Tie-break rule when a duplicate is found**: prefer vanilla's own item
  when one exists (e.g. if a mod adds a redundant copy of something
  vanilla already has, vanilla wins and the mod's version folds into it).
  For duplicates with no vanilla equivalent (mod vs. mod), no rule was set
  in this session — **the implementing session should default to "prefer
  whichever mod is most central to this pack's own material chain
  (Create/Silent Gear/Allthemodium) over incidental additions"** as the
  closest fit to the rest of this pack's design philosophy, but flag any
  genuinely ambiguous case rather than guessing silently.

**Open for the implementing session to resolve**:
- This is a large, expensive audit by nature (every registered item across
  ~40 mod jars) — worth scoping/batching the work (e.g. mod-by-mod jar
  inspection via `javap`/`jar tf`, or diffing registered item ids/tags
  across mods programmatically) rather than attempting it in one pass.
  Given this project's "ground truth over assumption" rule, each suspected
  duplicate needs to be confirmed against the actual installed jars, not
  assumed from mod names/descriptions, before any hard-removal work
  happens — a wrong merge is much harder to walk back than a wrong
  addition.
- Whether this pass should also re-run/patch `gen_economy.py` pricing and
  the ProgressiveStages tier files afterward, since removing/redirecting
  items could orphan price-table or tier-lock entries that reference a
  removed item id.
- How to handle a duplicate where the two competing items are at
  *different* points in this pack's own tier ladder (e.g. one copy is
  already tier-gated, the other isn't) — the merge needs to preserve
  whichever gating is more correct, not silently drop it.

## 4. ✅ DONE — Personal mobility progression: jetpack → persistent creative flight

**Implemented.** See `DESIGN.md`'s "Personal mobility: jetpack -> persistent
creative flight" section for the full writeup: Create Stuff & Additions'
native 4-tier jetpack ladder (copper/andesite/brass/netherite) mapped 1:1
onto Andesite/Brass/Precision/Induction Age; the Starforged Age (Tier 5)
capstone is a straight `abilities.mayfly` grant/revoke keyed to
ProgressiveStages stage membership (`pack/kubejs/server_scripts/
mobility.js`), not a wearable — item-free by design, survives death by
construction since the grant is stage-driven rather than item/effect-driven
(this pack's `keepInventory: false` never touches it). Also closed the
tier-bypass hole wave-1 flagged: `create-netherite-additions` shipped a
second, duplicate netherite jetpack — its recipe is now redirected to the
canonical `create_sa` item via a datapack override, folded into `dedup.js`'s
existing TODO.md item 3 pattern; both jetpacks' `induction_age.toml` locks
stay in place regardless (defense in depth). Two disclosed boot-only
unknowns remain (no per-tick mayfly reassertion; client-side toggle
responsiveness mid-session unverified without a live client). Boot-tested
clean, committed. Original scoping notes kept below for reference.

**Ask**: the pack currently has no personal flight ability at all — only
Elytra gliding (Precision Age) and Create Aeronautics vehicles (Brass Age
on). The user wants a dedicated personal-mobility progression: a simple
jetpack early on, upgrading over time, culminating in true persistent
creative-style flight.

**Decisions**:
- **Mod choice**: no specific mod named — research and pick the best fit
  against NeoForge 1.21.1 compatibility and this pack's design, the same
  process already used to choose Create Aeronautics/Waystones for the
  Travel overhaul.
- **Relationship to the existing Travel overhaul**: standalone new
  system, **not** a new part of that overhaul. Keep it as its own
  progression track rather than folding it into boats/trains/aircraft/
  teleportation.
- **Progression shape**: culminates **earlier than the full tier ladder**
  — true creative flight should land at **Starforged Age** (Tier 5, the
  "overworld/Nether/End are fully beaten, space travel begins" gateway),
  not held back through the entire Tier 6-9 planet-by-planet grind.
  Explicitly **not** tied to item 2's "infinite" endgame capstones —
  that option was declined; this is its own, earlier-arriving reward.
  Number/spacing of the intermediate jetpack rungs before that point is
  still open (e.g. does every tier 0-4 get an upgrade, or just some) —
  left for the implementing session to design against whatever mod is
  chosen.
- **Mechanic for the capstone**: true creative-mode-style flight — a
  toggleable, no-fuel/no-duration-limit ability, most likely granted via
  a wearable/trinket item (Curios is already installed) rather than a
  command or gamemode switch. Needs implementation-time research into how
  to actually grant/persist the vanilla `abilities.mayfly`-equivalent
  state through a survival-mode item (attribute modifier vs. a
  persistent effect vs. a Curios capability hook — mechanism not yet
  decided, just the end-user behavior).

**Open for the implementing session to resolve**:
- Candidate mod(s) for the early jetpack rungs (needs the same Modrinth-
  resolution + dependency-discovery process used for every other mod in
  this pack) and whether the same mod can plausibly also deliver the
  Starforged Age creative-flight capstone, or whether the capstone needs
  a bespoke KubeJS-granted ability layered on top of a chosen jetpack mod.
- How many intermediate tiers the jetpack should have between "simple
  early jetpack" and "Starforged Age creative flight," and which
  ProgressiveStages tiers they land on.
- Whether the capstone should be revocable (e.g. lost on death without
  keepInventory, since this pack already sets `keepInventory: false` per
  its gamerules) or should behave more like a permanent unlock — worth
  flagging since a "persistent" flight capstone that's trivially lost on
  death would undercut the "persistent" framing.

## 5. ✅ DONE — Curios as a discoverable/upgradeable player-ability system

**Implemented** via Artifacts 13.2.1 (zero new hard deps). See `DESIGN.md`'s
"Curios as a discoverable/upgradeable player-ability system" section for the
full writeup: Artifacts' own native loot injection was silenced entirely
(empty-pool overrides across all 35 of its inject tables) so this pack's
existing 4-tier structure-loot rarity buckets become the sole placement
path — no ProgressiveStages tier lock, per the recorded decision, just loot
weighting; a 48-item curation table (the master tag holds 48, not the
estimated 47, counted programmatically) split 18/19/8/3 across Common/
Uncommon/Rare/Epic, landing a tier-flat ~5-6% artifact chance per chest
while bucket choice scales quality. `pack/kubejs/server_scripts/
curios_upgrades.js` implements the duplicate-combine upgrade (2x same
artifact → 1x plus a bonus stat, one rule per Curios slot type, 46 recipes
total) using Curios' own `curios:attribute_modifiers` component rather than
vanilla's — a verified ground-truth deviation, since vanilla's component
never applies in Curios slots. Boot-tested clean, committed. Original
scoping notes kept below for reference.

**Ask**: make Curios (already installed as an Ars Nouveau dependency, not
yet used as its own content system) a strong source of player abilities —
mostly discoverable through exploration, some craftable, each unique
trinket granting an ability or bonus, with an upgrade path.

**Decisions**:
- **Content source**: no specific mod adopted yet — research broadly
  rather than anchoring on a single named candidate. (During scoping, a
  mod called "Artifacts" — Curios-compatible, dozens of discoverable
  passive/active-ability trinkets found in loot chests, mostly not
  craftable — came up as a plausible strong fit; worth checking early in
  the research pass, but not a mandate to adopt it over other options.)
- **Discovery mechanism**: hook into the structure loot-rarity tiers just
  shipped (`scripts/gen_structure_loot.py`'s Common/Uncommon/Rare/Epic
  buckets from the world exploration overhaul) — curios should slot into
  that existing infrastructure (rarer structures roll better curios)
  rather than relying solely on whatever loot placement the adopted
  content mod ships natively.
- **Upgrade mechanic**: combine duplicates found through exploration into
  a stronger version of the same curio — keeps the loop centered on
  exploration/luck rather than on crafting-station material sinks.
- **Tier gating**: curios are usable immediately on pickup, **no**
  ProgressiveStages tier lock — this is a deliberate exception to the
  pack's usual "almost everything is tier-gated" convention, because a
  found curio is explicitly meant to be a pure exploration payoff (find
  something great early = exciting), not another progression gate.
- **Relationship to item 4 (mobility progression)**: the two stay mostly
  separate, but curios *can* contribute minor mobility bonuses (e.g. a
  slow-fall or double-jump trinket) as one ability category among many.
  The actual jetpack → persistent-creative-flight backbone still comes
  from item 4's dedicated mod/system, not from curios — curios are a
  minor supplementary source of movement perks, not a replacement.

**Open for the implementing session to resolve**:
- Concrete mod choice (or bespoke KubeJS build) after the broad research
  pass — confirm NeoForge 1.21.1 + Curios compatibility against the
  actually-installed jar before committing, per this project's standing
  "ground truth over assumption" rule.
- Exact mechanism for wiring a content mod's curio items into
  `gen_structure_loot.py`'s bonus pools (may need the generator script
  extended to accept a configurable per-tier curio item list once the
  mod's own item ids are known) vs. patching the mod's own native loot
  injection instead.
- What "combine duplicates" looks like technically (a crafting-table
  recipe, an anvil-style combine, a dedicated station) — depends heavily
  on what the adopted mod natively supports; don't force a bespoke UI/
  station if the mod already ships one.
- Whether "no tier lock" needs any balance guardrail at all (e.g. should
  truly capstone-tier curios still be rare enough via loot weighting
  alone to avoid trivializing early game, since there's no tier lock as a
  backstop) — flagged as a real tension between "pure reward" and overall
  pack balance, not resolved in this session.

## 6. ✅ DONE — Hostile + passive monster/animal variety, with limited unique drops

**Implemented** via Creeper Overhaul 4.0.6 + Born in Chaos 1.7.6 (hostile
variety) + Naturalist (passive fauna) — Alex's Mobs was ruled out during
scoping for its unique-drop-heavy design. See `DESIGN.md`'s "Hostile +
passive mob variety, limited unique drops" section for the full writeup:
every new mob's loot was patched after the fact onto this pack's existing
shared canonical drop set (32 entity loot overrides across `born_in_chaos_v1`
— note the real data namespace, NOT the Modrinth slug `borninchaos` — and
`naturalist`), matching `instructions.md`'s own cattle/bird example; unique
weapons/armor/combat-stat charms stripped (including Born in Chaos' charm
accessories, to keep the skill system and item 5's Artifacts as the sole
sanctioned sources of that kind of permanent bonus); Creeper Overhaul's 16
variants verified already 100% vanilla-drop, no override needed.
`mob_scaling.js`'s `MONSTER_TYPES` whitelist extended with all 61 new
hostile ids so they participate in the existing difficulty-scaling system.
Flagged for live-play review, not blocking: 41/45 Born in Chaos hostiles
spawn via a `neoforge:any` biome predicate (everywhere), no
biome-appropriateness tuning against the new Terralith biomes yet. Boot-
tested clean, committed. Original scoping notes kept below for reference.

**Ask**: `instructions.md` explicitly asks for "more varied mobs/animals"
and "lots of different types of mobs > still limited types of drop" (its
own example: multiple cattle types should all still just drop beef) — this
was never addressed in any phase so far. The pack is still effectively
vanilla-mob-only: Apotheosis' Elites/Invaders are stronger *variants* of
existing vanilla mobs (not new species), `mob_scaling.js` scales vanilla
mob attributes, and Ars Nouveau's Wilden line is new entities but
player-summoned combat familiars, not wild fauna. Passive animal variety
hasn't been touched at all. This item is a real content pass to close that
gap, for both hostile and passive mobs, while deliberately avoiding a
pile of new unique drop items.

**Decisions**:
- **Mod choice**: no lead — research broadly against NeoForge 1.21.1
  compatibility. Explicitly flagged during scoping: a well-known option
  like Alex's Mobs is a poor fit *despite* its popularity/creature count,
  because it's known for adding lots of mob-specific unique drops/
  trophies, which cuts directly against this item's own constraint —
  weigh candidates on drop-list cleanliness, not just creature variety.
- **One mod or several**: no fixed rule — use whichever combination fits
  best. A single mod covering both hostile and passive variety well is
  fine if one exists, but don't force one mod to cover both if a
  hostile-focused mod and a separate passive-fauna-focused mod fit
  better individually.
- **Drop strategy**: patch everything after the fact, regardless of what
  the source mod(s) ship natively. Mod selection should be driven by
  creature quality/variety, not narrowed to only-vanilla-drop mods —
  after adoption, use this pack's existing KubeJS loot-override pattern
  (same mechanism `scripts/gen_structure_loot.py` already established for
  structure chests: copy the real loot table, then override) to redirect
  every new mob's drops into a small shared canonical set (beef/
  porkchop/mutton/chicken/leather/feathers/string/etc., extending the set
  only if a genuinely new resource type is actually warranted) —
  matching `instructions.md`'s own cattle/bird example precisely.
- **Difficulty-scaling hookup**: yes — extend `mob_scaling.js`'s
  `MONSTER_TYPES` whitelist (currently a hardcoded `Set` of vanilla mob
  ids only) to include every new hostile mob added here, so they
  participate in the same dimension/distance/player-tier scaling,
  star-rating nametag, and bonus-currency-on-kill system vanilla hostiles
  already get. New hostiles should feel consistent with existing ones,
  not exist as a separate unscaled category.

**Open for the implementing session to resolve**:
- Concrete mod(s), confirmed against the actually-installed jar (ground
  truth over assumption, as always) before committing.
- Full inventory of each new mob's native loot table before patching —
  needs the same "extract real loot table from the installed jar, copy
  it, then override" approach `gen_structure_loot.py` already
  established, applied to entity loot tables this time
  (`data/<modid>/loot_table/entities/*.json`) rather than chest loot.
- Whether new *passive* mobs also need any interaction with
  `mob_scaling.js` (currently scoped to hostiles only) or should stay
  entirely out of that system, consistent with vanilla passive mobs
  already being excluded from it today.
- Whether any new mobs should spawn biome-appropriately relative to the
  ~100 new Terralith biomes just added (world exploration overhaul) —
  not decided in this session, but a natural pairing worth considering
  given the timing of both additions.

## 7. ✅ DONE — Block-based chunk loading (Create-native, replacing FTB Chunks' menu flow)

**Implemented** via Create: Power Loader (verified Create-native match).
See `DESIGN.md`'s "Block-based chunk loading via Create: Power Loader"
section for the full writeup: two loader tiers (`andesite`/`brass`,
matching this mod's own naming to this pack's tier ladder 1:1) locked at
`andesite_age.toml`/`brass_age.toml`, running-cost guardrail satisfied
natively by the mod's own design (force-loading stops the instant the
parent kinetic network stops spinning - no KubeJS scripting needed or
possible, chunk force-loading is a Java-level hook), independent of FTB
Chunks' claim system. FTB Chunks' own menu-based force-loading fully
disabled via `pack/config/ftbchunks-world.snbt` (`max_force_loaded_chunks:
25 -> 0`, `force_load_mode: "default" -> "never"`) - claims/protection
untouched. No hard loaded-chunk cap set, per the user's decision leaving
that specific guardrail open. Boot-tested twice (mod load, then the
tracked config file's acceptance), committed. Original scoping notes kept
below for reference.

**Ask**: FTB Chunks (installed since Phase 6 for land claims) already ships
a native force-loading feature, but it's menu/permission-driven (an FTB
Ranks permission node, `ftbchunks.chunk_load_offline`, gates whether
force-loaded chunks stay loaded while a team is offline) and was never
configured for this pack — see the chunkloading status discussion earlier
this session. The user wants chunk-loading done through an actual
placeable block instead of that menu-driven flow.

**Decisions**:
- **Disable FTB Chunks' own force-loading feature** (`force_loading`
  config in `ftbchunks-world.snbt`) entirely — FTB Chunks stays installed
  and active for land claims/protection only, not for keeping chunks
  ticking.
- **Look specifically for a Create-native chunk-loading solution** (a
  Create addon, not a generic standalone chunk-loader mod) — consistent
  with this pack's standing rule that "engaging with Create should be the
  sole process by which you automate things." A generic non-Create chunk
  loader mod is the fallback only if no reasonable Create-native option
  exists after real research (not assumed yet either way).
- **Independent of FTB Chunks' claim system** — the loader block should
  work anywhere a player can legally build, with no prerequisite that the
  chunk already be claimed via FTB Chunks. Keeps chunk-loading and
  land-protection as two clearly separate concerns.
- **Tier-gated** — unlock the chunk-loader block at a specific
  ProgressiveStages tier, consistent with almost everything else in this
  pack, rather than making it available from the start.
- **Running cost** — it should require ongoing power/fuel to keep a chunk
  loaded, not be a free always-on toggle once placed. Given this pack's
  existing power story (Create's own kinetic power, bridged to FE via
  Create Crafts & Additions' Alternator from Brass Age on), a kinetic- or
  FE-cost mechanism is the natural fit, but the exact cost mechanism
  wasn't pinned down further in this session.
- **No explicit chunk-count cap decided** — the user selected tier-gating
  and running cost as the two guardrails; a hard per-player/team loaded-
  chunk limit was offered as an option but not explicitly chosen. Treat
  this as open rather than assumed-off: worth a real design call at
  implementation time given server performance is an explicit stated
  concern (`instructions.md`) and this pack already added C2ME
  specifically for chunk-loading cost.

**Open for the implementing session to resolve**:
- Whether a genuinely Create-native chunk-loading addon actually exists
  for NeoForge 1.21.1 — needs real research; if nothing fits, decide
  between a generic chunk-loader mod vs. a bespoke KubeJS/datapack-level
  implementation (worth noting this may not be easy to build purely via
  KubeJS — chunk force-loading is usually a mod-level/Java-level hook,
  not something the datapack layer can express on its own; confirm this
  before committing to a "just script it" fallback).
- Exact FE/kinetic cost curve and how it scales (flat per-chunk cost? does
  cost rise with tier the way storage capacity does?).
- Which ProgressiveStages tier is the right unlock point — no specific
  tier was named this session.
- Whether a hard loaded-chunk cap (per block, per player, per team) is
  needed on top of the running-cost guardrail, given the performance
  concern flagged above but not resolved into a specific limit.

## 8. ✅ DONE — Leaderboards: wealth / tier / level comparison

**Implemented.** See `DESIGN.md`'s "Leaderboards: wealth / tier / level"
section for the full writeup: one new file (`pack/kubejs/server_scripts/
leaderboard.js`) implementing `/leaderboard <wealth|tier|level>
[players|teams]` via `player.tell`, following `economy.js`'s command-
registration pattern. Wealth = physical coin count (inventory + ender
chest) plus a genuinely-reachable Numismatics bank-balance read
(`dev.ithundxr.createnumismatics.Numismatics.BANK`, confirmed via
`javap`). Tier = count of held ProgressiveStages stages via `player.
stages.has`. Level = summed Pufferfish Skills per-category levels via its
`SkillsAPI` (confirmed reachable via `javap`, all 12 category ids
verified). Teams = FTB Teams API, wealth/level summed across members,
tier maxed (reusing `player.stages.has` rather than FTB Teams' own
separate stage store, since it's already proven team-shared per Phase 6).
Offline players/members cached in `server.persistentData`, refreshed live
and on logout, shown with a `(last seen)` marker. All three mod APIs
wrapped in try/catch with honest "unavailable" chat messages - never a
silent vanilla-XP substitute. Boot-tested clean (all API classes loaded,
script counted among 12/12 KubeJS scripts with 0 errors), committed.
Original scoping notes kept below for reference.

**Ask**: some way for players to compare wealth (Numismatics currency),
tier progress (ProgressiveStages stage reached), and RPG skill levels
(Pufferfish Skills) against each other.

**Decisions**:
- **Display mechanism**: a **chat command** (e.g. `/leaderboard` prints
  text output directly in chat) — confirmed as the real intent after an
  earlier back-and-forth in this session. Not a GUI screen, and not a
  physical placeable block/item (the "NA, no item" answer to the access
  question still applies under this mechanism too — a chat command needs
  no physical access point).
- **Metrics shape**: separate leaderboards per metric — one for wealth,
  one for tier, one for level — not a single combined/composite score.
- **Ranking scope**: both individual players AND teams should be
  rankable. Currency and skill levels are currently per-player (not
  team-pooled) so an individual ranking is a direct read of existing
  data; tier progress is already team-shared via FTB Teams (per the
  Phase 6 preset-track design), so a team ranking there is also a
  fairly direct read, but wealth/level would need to be aggregated
  (summed? averaged? — not decided) to produce a meaningful team ranking
  since those aren't natively team-pooled values today.
- **Access**: not a craftable/placeable item (see display mechanism above
  — a GUI/command-driven screen doesn't need a physical access point the
  way a Create Display Board would have).

**Open for the implementing session to resolve**:
- Exact command name(s)/syntax (a single `/leaderboard` with arguments
  for which metric, e.g. `/leaderboard wealth|tier|level [player|team]`,
  vs. separate commands per metric — not decided) and output formatting
  (ranked list length, whether it's paginated, etc.).
- How to aggregate per-player wealth/level into a team-level ranking
  (sum vs. average vs. highest-member, given these aren't natively
  team-pooled stats).
- Where the tier/level/wealth numbers get pulled from technically:
  `player.stages` (already used by `mob_scaling.js` for tier reads),
  Numismatics' own currency-tracking API (needs research — currency is
  physical coin items today, not a stored balance, so "wealth" may need
  to be computed as counted coin value across a player's inventory/
  storage network rather than read from a single stored number), and
  Pufferfish Skills' own level API per category (needs research into
  whether it exposes a clean per-player/per-category level query).
- Implementation is a KubeJS `ServerEvents.commandRegistry` command,
  same pattern already proven in `pack/kubejs/server_scripts/economy.js`'s
  `/sell` command — no new mod/GUI framework needed.
- Update cadence (live query on each command invocation vs. periodically
  cached) — not discussed this session, but worth a real decision given
  the wealth metric in particular may be expensive to compute live if it
  means scanning inventories/storage networks.

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

## 10. NOT STARTED — DEFERRED POST-RELEASE — Tick accelerator (Time in a Bottle)

**Ask**: a classic "Time in a Bottle" item — passive real-time tick accrual,
right-click a block to spend the stored time as a temporary speed
multiplier on that block/machine.

**Decisions (finalized, user session 2026-07-10)**:
- **Model**: classic Time-in-a-Bottle item — passive real-time accrual,
  consumed on right-click against a target block to stack a temporary
  speed multiplier there.
- **Adopt**: time-in-a-bottle-universal 6.5.4 (the only viable TiaB-style
  mod found for NeoForge 1.21.1, zero hard deps) plus its companion fix
  addon (tiab-entity-fix, required for crop/animal acceleration to work at
  all on modern versions — confirmed via research, not assumed).
- **Gate: Brass Age (Tier 2)** — a plain ProgressiveStages item lock, no
  more elaborate gating mechanism needed.
- **Exclusions: Create kinetic blocks ONLY.** Layer the exclusion onto the
  mod's own `tiab:un_acceleratable` block tag (confirmed `replace:false`,
  i.e. additive) via a KubeJS registry scan tagging every block whose
  BlockEntity subclasses Create's `KineticBlockEntity` (~39 base classes /
  ~90+ ids including addons — a hand-maintained list would rot as this pack
  adds/removes Create addons over time). Fallback if the Rhino/Java
  registry-scan interop fails at implementation time: a generated static id
  list instead. This keeps Create's own RPM/Stress economy orthogonal to
  the accelerator, matching this pack's "engaging with Create is the sole
  automation process" rule.
- **Spawners deliberately stay accelerable** — explicitly NOT excluded.
  Synergy with Apothic Spawners upgrades (already installed, Phase 8) is an
  intended late-game payoff, not an exploit to close off.
- **Hard one-per-player** — not natively supported by any TiaB mod, needs a
  bespoke KubeJS craft-enforcement layer: an `ItemEvents.crafted` hook plus
  a live inventory scan (not a permanent flag, since re-crafting after a
  genuine loss must keep working) plus a manual ingredient refund on the
  blocked craft (exact `cancel()` semantics need verifying at
  implementation time). Keep `max_rate_multi` at its default 256x cap, per
  the pack's standing server-performance mandate — no reason to raise it.

**Open for the implementing session to resolve**:
- Disclosed, accepted soft-enforcement gaps in the one-per-player rule:
  stashed copies sitting in external storage (not on the player, not in
  their tracked inventory scan) evade the craft-time scan; the same
  `create:creative_crate` duplication gap already disclosed for item 2's
  infinite capstones applies here too, unchanged.
- Exact `cancel()`/refund mechanics for the enforcement hook — needs
  implementation-time verification against the installed KubeJS/ItemEvents
  API, not assumed from the mod's docs.

## 11. NOT STARTED — DEFERRED POST-RELEASE — Skill-tree overhaul (all 12 categories)

**Ask**: rework Pufferfish Skills' skill trees across all 12 categories (not
just combat) into a shared-trunk-then-fork shape, with hard-exclusive but
respeccable specialization paths.

**Decisions (finalized, user session 2026-07-10)**:
- **All 12 categories branch**, not just combat: swords, daggers,
  greatswords, longswords, spears, tachi, bows, magic, mining, running,
  swimming, building.
- **Shape**: ~15 nodes per category — a ~5-node shared trunk of general
  passives, then a fork into TWO 5-node specialization paths.
- **Exclusivity: HARD but respeccable.** Taking one path locks out the
  other entirely; a respec mechanism must exist to undo that choice.
  Implementation-time research needed to verify native support: the
  skill-connection schema, `skillReplaceCooldown`/`maxPassiveSkills`
  gamerules, and whether a reset command already exists natively before
  building a bespoke one.
- **Node effects: attribute modifiers ONLY** — no scripted procs anywhere
  in the tree. Keeps every node mechanically simple and inspectable.
- **Core design law, the load-bearing constraint for the whole item: paths
  trade by stacking DIFFERENT FAMILIES OF UPSIDES — no node anywhere
  carries a downside.** Flagship worked example from the decision session:
  a swords category forking into a fast-attacks path vs. a slower-
  deliberate-hits path, each all-upside within its own theme (attack speed
  + smaller per-hit bonuses vs. attack damage + heavier per-hit bonuses,
  not "faster but weaker" as a tradeoff). Every weapon category needs a
  topical equivalent of this same shape, not a copy-paste of the sword
  example. Path themes must be designed against the VERIFIED attribute
  inventory this pack's mods actually expose — especially which attributes
  Epic Fight's animation-driven combat engine actually respects, since a
  path built around an attribute Epic Fight silently ignores would be a
  dead spec. This attribute-inventory verification is the implementation
  session's central research crux, not a minor detail.

**Open for the implementing session to resolve**:
- Full verified inventory of which vanilla/modded attributes Epic Fight's
  combat actually reads at runtime, before any path is designed around one.
- Native respec support (connection schema, gamerules, commands) vs.
  needing a bespoke KubeJS reset mechanism.
- Concrete node-by-node design for all 12 categories × ~15 nodes — a large
  content-design task in its own right, comparable in scope to the
  original gear-overhaul melee-skill-split work.
