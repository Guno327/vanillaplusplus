<!--
  Modrinth project-page content for "Vanilla++".

  This file is the source of truth for the pack's Modrinth project
  DESCRIPTION/body. Publishing it (via the Modrinth API or the
  publish-modrinth.yml workflow) requires the MODRINTH_TOKEN CI secret;
  that's a PM/owner action, not something this file does on its own.

  Notes for whoever publishes:
  - This is plain Modrinth-flavored markdown (headings/bold/lists/links) —
    no raw HTML, since Modrinth strips it from project bodies.
  - Deliberately does not name a "current" version number anywhere; the
    releases page/latest-release link is the version source of truth and
    changes independently of this file (see instructions in this file's
    task: a version was recently pulled, so nothing here should freeze on
    one).
  - See docs/modrinth-images.md for the accompanying image plan — none of
    the images it discusses are embedded here; add them only once real,
    licensing-clean assets exist per that plan.
-->

# Vanilla++

**A from-scratch, Create-driven progression overhaul for Minecraft 1.21.1.**
Every vanilla system you know — tools, storage, combat, leveling, economy,
even the way you get to the Moon — has been rebuilt around a ten-stage tech
ladder where each tier's machinery requires mastering the one before it.
Nothing is bolted on; everything is gated, tuned, and made to matter.

If you've ever wanted a Create-centric pack that treats *every* system —
not just automation — as part of the same progression, this is that pack.

---

## What makes it different

Most Create packs layer a handful of addons onto vanilla and call it done.
Vanilla++ instead asks, for every vanilla mechanic: *what would this look
like if Create's own logic of "engage with kinetic machinery to unlock the
next thing" applied here too?*

- **Tool crafting is blacksmithing, not a crafting-table recipe.** Iron
  tools go through a real multi-step Silent Gear process — forge parts from
  a blueprint and material, then assemble them at a Gear Workbench — instead
  of one flat recipe.
- **Storage scales with you.** Small, browsable, unpowered storage at the
  start; a full powered crafting network once you've earned it; a
  mid-tier bridge in between. You're never stuck manually digging through
  chests, but you're not handed the endgame network on day one either.
- **The RPG skill system isn't cosmetic.** Its buffs directly affect how
  fast you mine, swing, sprint, and swim — the things you're already doing
  to progress.
- **Space travel is the actual endgame**, not a mod installed for its own
  sake — it's gated behind genuinely beating the Nether and the End, the
  same way every earlier tier gates the next.
- **It's built from scratch.** Every mod choice, every recipe change, and
  every tier gate was picked and tuned specifically for this pack's own
  progression curve, not inherited from an existing curated modlist.

## Who it's for

Players who want a long, structured, multiplayer-friendly progression
built around Create — groups running their own small-to-medium server who
like having a clear "what's next" at every stage, rather than an open
sandbox with no throughline. If you want Create with real stakes attached
to storage, combat, leveling, and economy (not just contraptions), this is
built for you.

---

## Features

### Progression & tech

- A strict, ten-stage tier ladder (Rootborn → Andesite Age → Brass Age →
  Precision Age → Induction Age → Starforged Age, then four further
  frontier tiers through the solar system) built on Create's own material
  chain — each tier's key material unlocks the next tier's machinery.
- Vanilla progression (tool/armor tiers, enchanting, the Nether, the End)
  is folded into the same ladder instead of running on its own separate
  clock.
- Richer, simpler ore veins via Create Ore Excavation, and a
  duplicate-resource consolidation pass so the same metal never comes from
  two competing mods.
- Deep post-endgame automation once you've outgrown manual gathering
  entirely — an Aluminum-to-Combustion tech ladder (via TFMG) plus
  "infinite"-throughput capstones, so late-game resources stop being a
  hard bottleneck.
- Space travel as the true endgame: once the Ender Dragon falls, rocket
  construction opens up a chain of increasingly hostile planets and moons,
  each gated behind the one before it.

### Blacksmithing & gear

- Iron-tier tool crafting is replaced outright by Silent Gear's
  blueprint-and-workbench process — genuine multi-step blacksmithing, not
  a single recipe swap.
- Five additional weapon classes (dagger, greatsword, longsword, spear,
  tachi) via Epic Fight, each with its own moveset and tier-gated material
  progression alongside vanilla gear.

### Storage

- **Early game**: small, unpowered, genuinely "dumb" browsable storage —
  link chests into one interface with no crafting automation yet.
- **Mid game**: Sophisticated Storage bridges the gap with its own
  tiered containers (wood through netherite) as you climb the ladder.
- **Late game**: a full powered crafting network (Refined Storage) —
  wireless access, expanding capacity, and eventually native
  pattern-based autocrafting once you've reached the top tier. Power
  comes from Create itself, so automating your automation still runs
  through Create's kinetic chain.

### Skills & RPG progression

- A deep, consequential skill tree system (23 categories, hundreds of
  nodes) covering combat, gathering, movement, and more — every node is a
  real gameplay buff (mining speed, sprint speed, weapon damage, and more),
  not a cosmetic unlock.
- A `/respec` command if you want to rebuild your build.

### Economy & quests

- A tiered currency (coins from Spurs up to Suns) with a universal
  `/sell` outlet — every item in the pack has a price, scaled to the tier
  it takes to reach it, so selling never out-earns actually playing.
- An asynchronous player marketplace: browse and price-compare other
  players' shops from anywhere, then travel to buy — no both-players-online
  requirement to trade.
- A full preset quest track (one chapter per tier) walking you through the
  whole progression, plus long-running quests that scale exponentially and
  daily-refreshing randomized quests, both rewarding skill XP and currency.

### Multiplayer

- Party and chunk-claim support out of the box — share preset-track quest
  progress with your party while keeping personal long-running/daily quest
  progress your own, and reserve chunks so others can't touch your builds.
- A `/leaderboard` command for wealth, tier, and skill-level bragging
  rights across the server.

### Combat

- Five extra weapon classes with distinct movesets and a stamina system
  (Epic Fight), each hooking into its own skill category so committing to
  a weapon class pays off.
- A full spellcasting and summoning magic archetype (Ars Nouveau) sitting
  alongside melee and ranged as an equally viable playstyle.
- Mob difficulty that scales with location and with the player, with
  visual cues so you can tell at a glance whether something's stronger or
  weaker than you.

### World & exploration

- Expanded biome and structure variety, with rewards that scale with how
  rare a structure is to find.
- Persistent mobility progression: a four-tier jetpack line that
  culminates in permanent creative flight.
- A curated Curios/Artifacts ability system with its own upgrade path.
- A diet-variety food overhaul (Farmer's Delight ecosystem) that rewards
  eating a varied diet with permanent bonus hearts — reward-only, no
  penalties for repetition.

---

## Installation

**Client** — this pack ships as a standard Modrinth `.mrpack`:

1. Grab the client `.mrpack` from the pack's [GitHub releases
   page](https://github.com/Guno327/vanillaplusplus/releases/latest) (or
   this Modrinth project's Versions tab, once published there).
2. Import it into **Prism Launcher** (the primary target this pack is
   built and tested for) — the Modrinth App and ATLauncher also accept the
   same `.mrpack` format.
3. First import needs an internet connection: the `.mrpack` only bundles a
   mod-download manifest plus config/KubeJS overrides, and your launcher
   fetches the actual mod jars from their source on import.
4. Launch once and let the world fully load before joining a server —
   several systems (skill trees, KubeJS-driven UI) initialize on first
   client boot.

**Server** — a matching server `.zip` ships with every release: extract it,
accept the Minecraft EULA, and run `run.sh`/`run.bat`. It ships its own
NeoForge libraries (no separate installer step) and is pre-tuned with
Aikar's G1GC flags for a small-to-medium private server. See the
project's `README.md` for full server setup and memory-sizing notes.

**NixOS** — a NixOS module is also available for running the dedicated
server as a systemd service, declaratively fetching and verifying a pinned
release straight from GitHub. See the project's `README.md` for details.

**Shaders**: the client bundle ships Iris (off by default, no shaderpack
installed) so low-end setups aren't affected — see the project README for
recommended shaderpacks to add yourself.

---

## Beta status — please read before playing

**Vanilla++ is in public beta.** It is not, and will not be tagged, 1.0
until the maintainers are confident every system holds up in real play.
In practice that means:

- The pack boots cleanly and its data/registry/recipe systems are
  automatically verified on every change — the tier ladder, quests, skill
  trees, and storage tiers all resolve correctly server-side.
- Several things are **not yet confirmed on a live client** — things like
  in-game rendering correctness and a few newly-merged systems awaiting
  real playtesting. These are tracked openly as issues on the project's
  GitHub, not hidden.
- Expect rough edges. If you hit one, please file it — bug reports and
  feature requests are both very welcome and are the main way this pack
  actually improves.

We'd rather ship an honestly-labeled beta than an overstated 1.0.

---

## Links

- **Source & issue tracker**: <https://github.com/Guno327/vanillaplusplus>
- **Releases** (client `.mrpack` + server `.zip`):
  <https://github.com/Guno327/vanillaplusplus/releases>

Found a bug or have a feature idea? Open an issue on GitHub — that's the
project's ground truth for all outstanding work.
