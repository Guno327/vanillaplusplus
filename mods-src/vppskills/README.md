# VPP Skills

A NeoForge 1.21.1 mod scaffold for Vanilla++'s own Path-of-Exile-style
skill-tree GUI (GitHub issue #163), meant to eventually replace
puffish_skills' built-in tree screen. Built for the
[Vanilla++ modpack](https://github.com/Guno327/vanillaplusplus) following the
`mods-src/<modid>/` convention #67 established.

**This is a PHASE 1 FOUNDATION only.** It is not wired into
`pack/manifest.json`/`pack/mods.lock.json` and is not shipped in the pack -
puffish_skills remains the pack's real, live skill system. See "Phase 2+
plan" below for what's deliberately deferred.

## What phase 1 includes

- **A real, building NeoForge 1.21.1 mod** - `build.gradle`/
  `gradle.properties`/`settings.gradle`/`gradlew` match `vppquests`' and
  `vppfixes`' exact conventions (same plugin versions, same
  `net.neoforged.moddev`/parchment/reproducible-archive setup). No
  `libs.json` - this mod calls no other mod's Java API (see
  `neoforge.mods.toml`'s trailing comment), only its own build-time-ported
  copy of puffish_skills' generated JSON.

- **Tree data model + loader** (`tree/SkillTreeNode.java`,
  `SkillTreeConnection.java`, `SkillTreeCategory.java`, `SkillTreeData.java`,
  `SkillTreeLoader.java`) - a clean, puffish-independent representation
  (node id/position/root flag/title/icon, edges with a group id) parsed from
  puffish_skills' own JSON shape
  (`category.json`/`skills.json`/`connections.json`/`definitions.json`).

  The pack's real tree data
  (`pack/kubejs/data/puffish_skills/puffish_skills/categories/**`, currently
  one unified category - `adventurer`, 791 nodes/790 edges per GitHub #116)
  is **ported into this mod's own jar at build time** by `build.gradle`'s
  `importSkillTreeData` task, into this mod's own namespace at
  `assets/vppskills/tree/categories/**` (plus a generated `index.json`
  listing category ids). This is a deliberate choice over reading the live
  server datapack the way `vppquests`' `QuestReloadListener` does: a
  dedicated-server client never has local access to that server's `data/`
  folder, while `assets/` ships in every mod jar and is always available
  client-side regardless of connection type - the right fit for a phase-1
  proof-of-concept screen that must not depend on any particular running
  server. `SkillTreeLoader` then reads it back at runtime through the real
  client `ResourceManager` (`FileToIdConverter`-shaped, hand-rolled Gson -
  the same parsing style `QuestReloadListener` already proved for this
  pack's JSON), not raw classpath access, so it stays resource-pack
  overridable. It is a one-shot load (`client/ClientSkillTreeState`), not a
  live `PreparableReloadListener` - see "Phase 2+ plan".

  This task never writes back to `pack/kubejs/data/...` - puffish_skills'
  generated data is untouched, per #163's scope.

- **Proof-of-concept client screen** (`client/gui/SkillTreeScreen.java`,
  opened by the `P` debug keybind - `client/ModKeyMappings.java`,
  `client/ClientSkillTreeEvents.java`, same tick-poll pattern `vppquests`'
  `ClientQuestEvents` already proved) - a pannable (left-drag) + zoomable
  (scroll wheel, zoom-to-cursor) canvas rendering the REAL node positions and
  curved connectors from the ported data, all 791 nodes / 790 edges. See
  that class's doc for the pan/zoom/curve rendering approach (one
  `PoseStack` translate+scale per frame for pan/zoom; curved connectors are
  quadratic-Bezier-sampled thick rectangles rotated per segment, since
  `GuiGraphics` has no arbitrary-angle line primitive - ground-truthed via
  `javap` against the resolved jar). Placeholder square node icons
  (color-coded root vs. normal) - final art is a later phase. No
  interactions: no click-to-unlock, no XP/points, no server round-trip.

## What this phase does NOT include (deliberately, per #163's scope)

- **Point/XP economy** - no unlock cost, no available-points tracking.
- **Attribute-reward application** - `definitions.json`'s
  `puffish_skills:attribute` rewards are read (title/icon only) but never
  granted to a player.
- **Save-data persistence** - nothing is written for a player; re-opening
  the screen always shows the same static, unlockable-by-nobody tree.
- **Client-sync network payloads** - the tree ships baked into the jar
  (see above), not synced from a server; there is no
  `CustomPacketPayload` here at all yet.
- **Respec.**
- **Migration off puffish_skills.** puffish_skills stays exactly as-is and
  remains the pack's live skill system throughout phase 1.
- **Pack wiring.** Not in `pack/manifest.json`/`pack/mods.lock.json`.
- **A live reload listener.** `SkillTreeLoader.load()` runs once per
  `ClientSkillTreeState` cache fill; wiring a real
  `PreparableReloadListener` via `RegisterClientReloadListenersEvent`
  (ground-truthed to exist on the resolved NeoForge jar) so `F3+T` picks up
  edits is a trivial, low-risk phase-2 follow-up, not needed to prove this
  phase's approach.

## Phase 2+ plan (needs owner check-in before starting)

1. **Point/XP economy** - decide whether vppskills grows its own
   XP/level/points model or keeps reading puffish_skills' experience state
   during a transition window. Risk: puffish_skills' `experience.json`
   schema and unlock-cost rules aren't ported by this phase at all yet.
2. **Persistence** - a NeoForge data attachment on the player (same pattern
   `vppquests`' `QuestProgressAttachment` already uses) holding
   unlocked-node ids. Risk: needs a real migration/seed decision for
   players who already have puffish_skills progress (see point 6).
3. **Click-to-unlock + attribute application** - wire `SkillTreeScreen`'s
   node click to a server-validated unlock (adjacency + point-cost check),
   then apply `definitions.json`'s reward list as real attribute
   modifiers. Risk: needs the exact same `multiply_base`/`multiply_total`
   operation vocabulary DECISIONS.md already flagged as puffish-specific
   (not vanilla's `AttributeModifier.Operation`) - a real translation
   layer, not a copy-paste.
4. **Client-sync payloads** - once unlock state is server-authoritative,
   the client needs its own mirror (mirroring `vppquests`' `network/`
   package: definitions sync + progress sync `CustomPacketPayload`s) so the
   screen doesn't touch the network directly. Risk: 791 nodes is a lot of
   payload to keep small; likely needs delta sync, not a full resend per
   change.
5. **Respec** - a command or in-tree action that refunds points and clears
   attribute modifiers. Risk: must exactly reverse whatever operation
   vocabulary point 3 lands on, or stat drift accumulates.
6. **Migration off puffish_skills** - the highest-risk item. Needs an
   owner decision on whether existing players' puffish_skills progress is
   carried forward (mapping puffish's per-category unlock state onto
   vppskills' node ids) or reset, matching the precedent `vppquests`' own
   README set ("owner explicitly said not to worry about carrying old
   quest/progress data forward, so every player starts fresh") - but skill
   points represent real player investment in a way quest progress didn't,
   so this needs its own explicit call, not an assumed carry-over of that
   precedent.
7. **Real art** - replace the placeholder square nodes/generic curve style
   with actual node icons (`ItemStack` rendering was deliberately NOT
   attempted in phase 1 - GuiGraphics's item renderer's interaction with an
   arbitrary `PoseStack` scale under pan/zoom couldn't be verified without a
   live GL context in this sandbox, so it's left as a phase-2 risk to
   verify in a real client run rather than guessed here) and a
  background/border treatment matching each category's `category.json`
  (`background.texture`/`width`/`height`/`position` - read by neither this
  phase's loader nor screen).
8. **Pack wiring + cutover.** Only after the above are reviewed: add to
   `pack/manifest.json`, decide whether puffish_skills is removed outright
   (matching the FTB Quests -> vppquests precedent) or kept installed but
   unused during a transition window.

## Build instructions

```sh
cd mods-src/vppskills
./gradlew build
```

`gradlew`/`gradlew.bat` are committed; `gradle/wrapper/gradle-wrapper.jar`
(binary) is gitignored - `scripts/build_local_mods.py`'s
`ensure_gradle_wrapper_jar()` step fetches it automatically, or generate it
once locally with `gradle wrapper --gradle-version 8.10`.

`JAVA_HOME` must point at a JDK 21 (this repo's own `.tools/jdk-21.0.11+10`
if present). The jar lands at `build/libs/vppskills-0.1.0.jar`.

Every NeoForge/Minecraft API this mod calls (`GuiGraphics`'s draw-call set,
`PoseStack`'s `pushPose`/`translate`/`scale`/`mulPose`, `Screen`'s
`mouseDragged`/`mouseScrolled` signatures, `ResourceManager`/
`ResourceLocation.fromNamespaceAndPath`, `RegisterKeyMappingsEvent`,
`org.joml.Quaternionf.rotationZ`) was ground-truthed with `javap`/`jar tf`
against the resolved NeoForge 21.1.235 jars and the Mojang-published Gson
2.10.1/JOML 1.10.5 library jars this pack's server already vendors under
`server/libraries/`, not assumed from memory - see this class's own doc
comments for what was checked and why (e.g. `GuiGraphics` has no
arbitrary-angle line primitive, only axis-aligned `hLine`/`vLine`, which is
why curved connectors are drawn as rotated filled rectangles instead).

Reproducibility (GitHub #145): `importSkillTreeData`'s directory listings
are explicitly sorted, and the standard
`preserveFileTimestamps=false`/`reproducibleFileOrder=true` archive settings
are carried over from `vppquests`/`vppfixes` - two independent
`./gradlew build` runs of this mod produce a byte-identical jar (verified
by comparing `sha1sum` of `build/libs/vppskills-0.1.0.jar` across a `clean
build` and a second `build`).
