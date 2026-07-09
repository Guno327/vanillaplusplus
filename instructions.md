# Goal

Your goal is to design a prism compatible modpack.

## Requirments

- Vanilla Minecraft, but with all things create + similar type vibe mods
    - This should be the newest possible minecraft version that is compatible will all other requirements.
    - Should replace or enhance vanilla mechanics through following create progression to all extension mods that get progressivley more useful and expensive
    - Previous create stuff should be neccessary for the next tier of stuff
- Should replace vanilla processes with more engaging alternatives
    - Instead of making metal tools normally have some kinds of blacksmithing
    - Ore processing through create is encouraged (introduce additional gains if necessary)
- All resources should eventually be automatable to the point of becoming infinite, in some format
    - This applies broadly, not just to already-renewable stuff like wood/food - the intent is that nothing should stay a hard, permanent bottleneck once a player is far enough into progression
    - Exact mechanism and which tier this kicks in at is open - see clarifying questions
- Should introduce a consequential RPG leveling system
    - should have a colleciton of skills that match to things you will be doing
        - Running
        - Swimming
        - Mining
        - Building
        - Swords
        - Bows
        - Etc.
    - Should provide actually useful buffs that directly effect the ability of the player to progress swiftly
- Should have some kind of economy
    - Each item included in the modpack should have some kind of preset value that is determined intelligently based on the tier/difficult of the resources used to construct it or its difficulty to obtain in general
    - Players should have some way to arbitrarily sell all items to some kinds of vendor that offers them some kind of tracked currency 
    - There should be no limits on the ability of players to offload items for money, but you should try to avoid unbalanced exploits to earn currency easily
- Should have some kind of marketplace
    - Players should be able to put items up for sale on a remote marketplace where other players can purchase them asyncronously
    - This can be any item, but generally more difficult to obtain items will sell to players for more than the vendor due to their rarity/complexity
- There should be some kind of quest/progression system aside from character leveling/progression
    - There should be a preset track that is custom built to guide the player through the progression of getting stronger and more powerful items/processes
    - There should also be long running quests to track general interactions (e.g. blocks broken, mobs killed, xp levels gained, time played, etc.)
        - These quests should continue to progress at an exponential rate where more and more interactions are required for a reward
        - The rewards should be experience to the RPG leveling system and/or the currency used for the marketplace
    - There should be randomly generated quests to perform specific actions on a daily (realworld) interval refresh after being completed
- There needs to be some kind of team system
    - Players should share progress (but not rewards) for preset track quests
    - Player should not share daily/long running quest progress shared
- There needs to be some kind of claim system
    - Players should be able to reserve chunks in a way that prevents others from interacting with them
- Storage should be a highly interactive and interable process
    - From traditional iron tier and onward (where ever you determine that to be in the progression) storage should be browsable
        - Thing mods like refined storage where you have a central interface to interact with your items at one place
    - The storage should start out limited, but still browsable
        - Think really small limits at beggining tiers
        - Think no ability to automate crafting until a certain point
            - The auto crafting available abilities should continue to scale after you first unlock it, just like storage
    - You should be encouraged to upgrade to new ways of handleing storage as you progress
- Combat should be engaging and offer a variety of options
    - Think different weapon types that have different pros/cons or playstyles
    - Encourage the player to stick with one weapon class
        - Hooks into RPG leveling system to provide some buffs
    - Make sure options are equally effective (as close as possible)
- There should be an emphasis on world exploration and generated structures
    - In addition to accumulating resource the player should be encouraged to explore
    - These means the world must be varied in content and biomes
    - Multiple dimensions that lock away better progression through the tier system should be implemnted
    - Structures should have rewards that scale with their probability of being discovered
    - Important structure for progression should spawn at a minimum rate to ensure there is one over X blocks when chunks are generated
- Space travel should be the ultimate end goal of the modpack
    - Once all overworld tiers and existing dimensions (Nether/End) are fully progressed through, space travel should open up to new, harder planets with further progression and resources available
    - This is expected to require leaning on Create addons and similarly-themed mods beyond Create's own ecosystem, since Create itself has no native space content
- The world should be as interactable as possible
    - Dynamic lights
    - More interesting animations 
    - More varied mobs / animals
    - Lots of different types of mobs > still limited types of drop
        - E.g. if you add a bunch of different animals all should drop leather not their own hides
            - There could be multiple type of cattle, they should all drop beef
            - There could be multiple birds, they shoull all drop poultry meat / chicken
- There should be some magical system
    - In addition to traditional combat roles mage/summoner should be a combat archetype
    - Introduce mechanics to make these an engaging as playing meele or ranged
- As many recepies as possible should be customized to provide a guided progression
    - Make sure players cannot access certain mods/structures/mechanics unless they first complete earlier objectives
        - Enginmatics 2 experts progression is a good example of this
- There should be some sort of dungeons
    - There should be bosses that drop unique weapons based on their difficulty
- Mobs should scale
    - Different areas that are less likely to be accessed earlier on should spawn more difficult monsters
    - Player should be able to easily tell by looking at a monster if it is stronger than the player or weaker
        - This should be on a scale of how much weaker/stronger they are
    - Mobs rewards (xp, money, drops) should scale with their difficulty if they appear in multiple zones/areas
    - The player that is causing these mobs to spawn should also influence their base difficulty base on their level/progression
- Engaging with create should be the sole process by which you automate things
    - Travel should be accelerated through create mechanics
    - This should be the way to create more and more complex recepies


# Limitations
- You may use existing mods and make custom edits when neccessary
- You may not create entirely new mods, but you can edit/integrate multiple mods together to provide functionality
- You may install libraries that allow you to edit the game (crafting recepies, loot tables, etc.) 
- Should be compatible with Prism Launcher in format
- All mods must be ensured to be compatible with each other
- Output should be able to be imported to Prism Launcher or used to run a linux server
- Client performance is less of a concern, but you should make sure it runs as efficiently as possible
- Server performance is a major concern. Make sure the server packed modpack includes mods/edit to make it as performant as possible

# Permissions
- You may research on the web
- You may downloads mods/structure the modpack using any system you think fits best
- When you are unsure between multiple options you may take to accomplish something you may loop in the user to answer a pointed question
    - You should include any needed context/sources that the user may need to review to decide
- You may use git to track your progress and revisions
- You may run the linux server version to make sure it runs correctly in this environment
- You may install any system packages that enhance your workflow and testing

# Clarifications & Resolved Decisions

Added during implementation (through Phase 2) to record ambiguities in the
above that had to be resolved with a judgment call or a user check-in, so
later phases (or a fresh session) don't have to rediscover the reasoning.
Full detail and rationale lives in `DESIGN.md`; this section is the short
index of *what was decided and why it matters going forward*.

## Scope decisions (confirmed with the user before implementation began)
- Build the mod list from scratch rather than forking an existing curated
  Create modpack (e.g. Create: Astral, Create: Above and Beyond).
- Server scale is a small private group (roughly 2-10 trusted players), not
  a large public server. This should keep economy/claims/anti-grief/mob-scaling
  tuning in later phases modest — don't over-build moderation or anti-cheat
  infrastructure the requirements never asked for.
- Delivery is a vertical slice, phase by phase (see `DESIGN.md`'s Phase
  plan), committing and verifying each phase end-to-end before starting the
  next, rather than stubbing every system shallowly up front.

## Technical foundation (not specified above; established in Phase 0)
- Minecraft 1.21.1 + NeoForge 21.1.235 — the newest MC version with a mature
  Create ecosystem (Create 6.0.10). Mojang's post-1.21 calver releases (26.x)
  have no Create port as of this build.
- No `packwiz` binary is available in this build environment (no Go
  toolchain or package manager to run it). `scripts/resolve_mods.py` +
  `pack/mods.lock.json` substitute — git-friendly, reproducible, resolved
  against the Modrinth API directly.

## Resolved ambiguities in the requirements above
- **"Storage should be browsable from traditional iron tier onward... start
  out limited"**: split across two mods rather than one system stretched
  thin. Tier 1 (Andesite Age, roughly vanilla iron tier) gets genuinely
  "dumb storage" — Tom's Storage, linking chests into one browsable
  interface, no power, no autocrafting. Tier 2 (Brass Age) onward gets the
  real network — Refined Storage (the mod named directly above), unlocked
  once Create's own automation and diamond/Nether access are also available.
- **"No ability to automate crafting until a certain point... continue to
  scale after you first unlock it"**: two-stage automation. Brass Age:
  Create's own Mechanical Arm/Deployer feed the storage network directly
  (not a bolt-on autocrafter), so "engaging with Create should be the sole
  process by which you automate things" holds even for storage. Induction
  Age (the top tier): Refined Storage's own native pattern-based autocrafting
  becomes available as the final scaling step.
- **Storage network power**: not addressed above at all. Refined Storage
  needs Forge Energy for its Controller, and Create doesn't natively produce
  FE. Resolved to generating it through Create itself — Create Crafts &
  Additions' Alternator (kinetic → FE) — rather than disabling the power
  requirement, which was tried first and was the wrong call against the
  "sole process by which you automate things" requirement.
- **Blacksmithing** ("instead of making metal tools normally have some kind
  of blacksmithing"): not yet implemented — deferred to Phase 7 (combat
  variety), since tool-crafting mechanics and weapon-class balance are
  tightly coupled. Two candidates identified so far, Silent Gear and Fire
  and Flames; Tetra, the usual pick for this, isn't ported to 1.21.1.
  Tier 1 currently unlocks vanilla iron tools as a placeholder in the
  meantime.
