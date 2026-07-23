# VPP Quests

A small, standalone NeoForge 1.21.1 mod providing the Vanilla++ modpack's
own quest book - a real dependency-graph GUI plus in-game progress
tracking, eventually replacing the pack's current chat-command-only KubeJS
quest tracker (`pack/kubejs/server_scripts/quests.js`, GitHub #33) and its
vanilla-advancement GUI layer (#36/#37/#66).

Built for the [Vanilla++ modpack](https://github.com/Guno327/vanillaplusplus)
(GitHub issue #109), following the `mods-src/<modid>/` convention #67
established (`mods-src/vppintegration/` is the first worked example): a
fully self-contained, independently Modrinth-publishable project, not
pack-specific glue.

**This is Phase A + Phase B (identity-mapping migration) only** - the mod
scaffold, data model, first-pass GUI, and the migration that carries a
player's already-completed legacy quests forward. See the parent repo's
`DESIGN.md` ("GitHub issue #109" sections) for the full architecture
proposal, migration plan, and phasing (A: scaffold, B: migration, C:
cutover, D: questline rebuild, E: optional achievements/dailies fold-in).
Phases C-D require explicit owner sign-off and are **not** part of this
mod yet - notably, `pack/kubejs/server_scripts/quests.js` is untouched and
still the pack's active quest system (this mod is not yet wired into
`pack/manifest.json`); Phase B only adds the one-way migration path so
cutover (Phase C) has somewhere safe to land later.

## What Phase A includes

- **Data model** (`quest/Quest.java`, `QuestChapter.java`, `QuestTask.java`,
  `QuestReward.java`) - a quest is a JSON file under
  `data/<namespace>/vppquests/quest/<chapter>/<slug>.json`, with a real
  multi-parent `dependencies` list (an actual DAG, not vanilla
  advancements' single-parent collapse), the same 5 task types / 5 reward
  types `quests.js` already implements (`item`/`kill`/`dimension`/
  `gamestage`/`checkmark` tasks; `item`/`xp`/`command`/`gamestage`/`toast`
  rewards), plus a new `criticalPath` flag for the eventual questline
  rebuild's "blindly followable" spine.
- **Registry + reload listener** (`quest/QuestReloadListener.java`,
  `QuestRegistry.java`) - a `SimplePreparableReloadListener` that parses
  every quest/chapter JSON on datapack load and `/reload`, same
  "generate, don't hand-type, reload like everything else" discipline this
  pack's other systems follow.
- **Progress tracking** (`data/QuestProgressAttachment.java`,
  `ModAttachments.java`, `quest/QuestProgressTracker.java`) - a NeoForge
  data attachment (the modern capability-system replacement) holding
  completed quest ids + per-task progress counters, persisted via a Codec
  and driven by a throttled server-tick evaluator that checks item/kill/
  dimension/checkmark tasks and grants item/xp/command/toast rewards on
  completion.
- **Client sync** (`network/`) - two `CustomPacketPayload`s
  (`QuestDefinitionsSyncPayload`, `QuestProgressSyncPayload`) keep a
  client-side mirror (`client/ClientQuestState.java`) current on login and
  whenever server state changes, so the GUI never round-trips per frame.
- **GUI** (`client/gui/QuestScreen.java`, opened via the `K` keybind) - a
  list-per-chapter view with a detail panel (description + live
  "N/M" task progress), per this issue's own risk-mitigation
  recommendation to ship that first rather than block Phase A on a full
  pannable dependency-graph canvas.
- `src/main/resources/data/vppquests/vppquests/` ships three tiny example
  quest/chapter JSON files as parser/registry test fixtures - **not**
  migrated pack content (Phase A explicitly does not migrate the existing
  62 quests; see "What Phase A does NOT include" below).

## What Phase B includes

- **`quest/QuestLegacyMigration.java`** - on a player's first login after
  this mod is installed, reads `quests.js`'s legacy save file directly
  (ground-truthed via jar inspection of the pinned
  `kubejs-neoforge-2101.7.2-build.368.jar`: KubeJS mixes `persistentData`
  onto `MinecraftServer` and round-trips it through a plain compressed-NBT
  file at `<world save>/kubejs_persistent_data.nbt`, resolved via
  `LevelResource`/`MinecraftServer#getWorldPath` - no KubeJS dependency
  needed to read it, it's vanilla NBT), extracts the
  `vpp_quests_progress` compound quests.js itself writes, and marks the
  same quest ids complete in `QuestProgressAttachment` - a strict identity
  mapping (same ids, no reinterpretation), matching DESIGN.md's Phase B
  description exactly. Idempotent via a `legacyMigrated` flag on the
  attachment (now part of its Codec). Because a migrated quest is marked
  complete *before* `QuestProgressTracker` ever evaluates it, rewards are
  never double-granted - the tracker's existing "skip if already complete"
  check does that for free, so no separate "rewards already granted" flag
  was needed.
- **Known Phase B limitation (disclosed):** only the per-player fallback
  progress key (`quests.js`'s `"player:" + uuid`) is migrated. Team-keyed
  progress (`"team:" + partyId`, when Open Parties and Claims is present)
  is not, because this mod's `QuestProgressAttachment` is itself
  per-player-only in Phase A (see its own class doc) - migrating a
  party-keyed compound has nowhere to land until that seam exists. This is
  a UX regression for team players only (they'd re-complete a few quests),
  never a correctness/reward-duplication bug. Revisit once a later phase
  wires the same `getPartyKey(player)` re-key GitHub #32 already proved out
  for `quests.js`.

## What Phase A/B does NOT include yet

- **The real dependency-graph canvas.** `QuestScreen` is a list view, not a
  pannable node-and-edge tree. A true DAG rendering (nodes with icons,
  multi-parent dependency lines drawn between them, per-chapter panning)
  is the single largest remaining GUI task - explicitly flagged as the
  biggest implementation risk in DESIGN.md's #109 proposal.
- **A persistent tracker HUD overlay** ("next quest" affordance without
  opening the full screen) - not built in this scaffold.
- **Party/team progress-sharing.** `QuestProgressAttachment` is keyed
  per-player entity only. The design's requirement (completion is
  party-shared, rewards are strictly per-player) needs a
  `getPartyKey(player)` seam calling Open Parties and Claims'
  `getPartyByMember(UUID)` - the same one-function-change precedent GitHub
  #32 already established for `quests.js`'s `getProgressKey()`. Flagged in
  `QuestProgressAttachment`'s own class doc; not wired here since no
  party/gameplay-system code is in this task's scope.
- **A gamestage bridge.** `gamestage` tasks/rewards round-trip through the
  data model/JSON/network layers but are never satisfied/granted by
  `QuestProgressTracker` - deliberately, since wiring a hard dependency on
  this pack's specific progression-stage mod would break this mod's
  "standalone, Modrinth-publishable, no pack-specific glue" goal. A later
  pack-side bridge (or an optional soft-dependency mixin, mirroring
  `vppintegration`'s own pattern) can hook it without changing this mod's
  public API.
- **Cutover and the questline rebuild** (Phases C-D) - untouched.
  `pack/manifest.json`, `pack/kubejs/server_scripts/quests.js`/
  `achievements.js`/`dailies.js`, and the advancement-generation code are
  all unmodified; quests.js remains the pack's actual active quest system
  and keeps writing to the same legacy save file Phase B's migration reads
  from (both systems can coexist - this mod is not installed in the pack
  yet, see "Build instructions").

## Build instructions

Confirmed working end-to-end (JDK 21, Gradle 8.10, network access to
`services.gradle.org` and `maven.neoforged.net`/`repo1.maven.org` for the
NeoForge/Minecraft dependencies):

```sh
cd mods-src/vppquests
./gradlew build
```

`gradlew`/`gradlew.bat` are committed, but `gradle/wrapper/gradle-wrapper.jar`
(a binary) is gitignored. If it's missing, generate it once with any local
Gradle 8.x install: `gradle wrapper --gradle-version 8.10`, then re-run
`./gradlew build`.

`JAVA_HOME` must point at a JDK 21 (`java.toolchain.languageVersion = 21` in
`build.gradle`). The built jar lands at `build/libs/vppquests-0.1.0.jar`.
This mod is **not** wired into `pack/manifest.json` - it's a standalone
scaffold, not yet installed in the pack (see "What Phase A does NOT
include yet").

Every NeoForge API used here (`SimplePreparableReloadListener`,
`FileToIdConverter`, `AttachmentType`, `RegisterPayloadHandlersEvent`/
`PacketDistributor`, `AddReloadListenerEvent`, `ServerTickEvent.Post`,
`RegisterKeyMappingsEvent`) was ground-truthed against the real, resolved
NeoForge 21.1.235 jar via `jar tf`/jdk tooling during this build, not
guessed - the mod compiled cleanly on the first full build once the two
real package-name corrections below were made (both since fixed):

- `RegisterKeyMappingsEvent` lives in
  `net.neoforged.neoforge.client.event`, not
  `net.neoforged.neoforge.event`.
- `Screen` already declares a `protected void rebuildWidgets()` - this
  mod's own widget-refresh helper is named `refreshWidgets()` instead to
  avoid an access-modifier override conflict.
