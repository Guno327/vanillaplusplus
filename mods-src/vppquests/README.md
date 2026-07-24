# VPP Quests

A small, standalone NeoForge 1.21.1 mod providing the Vanilla++ modpack's
own quest book - a real dependency-graph GUI plus in-game progress
tracking. This is now the pack's **sole** quest system.

Built for the [Vanilla++ modpack](https://github.com/Guno327/vanillaplusplus)
(GitHub issue #109), following the `mods-src/<modid>/` convention #67
established (`mods-src/vppintegration/` is the first worked example): a
fully self-contained, independently Modrinth-publishable project, not
pack-specific glue.

## History and the cutover

This mod replaces two earlier, licensing-forced rewrites of the pack's
quest system: FTB Quests (Phase 4, dropped for redistribution-rights
reasons), then a bespoke KubeJS tracker (`quests.js`, GitHub #33) with a
vanilla-advancement GUI bolted on top (#36/#66) since no other free GUI
option existed at the time. The owner reported in 0.5.2 that this second
system was broken end to end - progress wasn't being recognized at all -
and once this mod was ready to actually load in the pack, directed a full
cutover rather than more patching of dead code: **`quests.js`, its
advancement-generation code, the generated advancement JSON files, and
their CI checks are all REMOVED, not deprecated-in-place.** There is no
legacy-progress migration either - the owner explicitly said not to worry
about carrying old quest/progress data forward, so every player starts
fresh in `vppquests`. `achievements.js` and `dailies.js` are separate
features (lifetime achievements, daily bounties) with no dependency on the
removed quest infra - both were checked and left completely untouched.

`pack/manifest.json` now wires this mod into the pack for real
(`source: "local"`, phase 26, `side: "both"` - client for the GUI/keybind,
server for the registry/attachment/tracker).

## What this mod includes

- **Data model** (`quest/Quest.java`, `QuestChapter.java`, `QuestTask.java`,
  `QuestReward.java`) - a quest is a JSON file under
  `data/<namespace>/vppquests/quest/<chapter>/<slug>.json`, with a real
  multi-parent `dependencies` list (an actual DAG, not vanilla
  advancements' single-parent collapse), 5 task types
  (`item`/`kill`/`dimension`/`gamestage`/`checkmark`) and 5 reward types
  (`item`/`xp`/`command`/`gamestage`/`toast`), plus a `criticalPath` flag
  reserved for a future critical-path-spine questline redesign.
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
  "N/M" task progress). A pannable node-and-edge dependency-graph canvas
  is the single largest remaining GUI task - not built yet.

## Quest content

`scripts/gen_vppquests_data.py` is the single, self-contained source of
truth for this mod's 62-quest/10-chapter book, generating data-driven JSON
under `pack/kubejs/data/vanillaplusplus/vppquests/{chapter,quest}/**`
(this mod's `QuestReloadListener` reads the merged datapack
`ResourceManager`, not just its own jar resources, so content lives in the
pack's existing datapack tree, not baked into the mod). The content
originated in the now-removed `gen_quests.py`/`quests.js` - it wasn't what
was broken, so it was kept and is now generated directly in this mod's own
schema rather than imported from the deleted legacy generator. Validated
by `scripts/ci/check_vppquests.py` (10 chapters / 62 quests / 87
dependency edges). `criticalPath` is left `false`/absent throughout - that
flag is reserved for a future questline redesign, not this content.

Re-run `python3 scripts/gen_vppquests_data.py` any time this content needs
to change - it's the one place to edit it.

## What this mod does NOT include yet

- **The real dependency-graph canvas.** `QuestScreen` is a list view, not a
  pannable node-and-edge tree.
- **A persistent tracker HUD overlay** ("next quest" affordance without
  opening the full screen).
- **Party/team progress-sharing.** `QuestProgressAttachment` is keyed
  per-player entity only. A `getPartyKey(player)` seam calling Open
  Parties and Claims' `getPartyByMember(UUID)` would be needed for
  team-shared completion (rewards would stay per-player) - not wired in
  yet, flagged in `QuestProgressAttachment`'s own class doc.
- **A gamestage bridge.** `gamestage` tasks/rewards round-trip through the
  data model/JSON/network layers but are never satisfied/granted by
  `QuestProgressTracker` - deliberately, since wiring a hard dependency on
  this pack's specific progression-stage mod would break this mod's
  "standalone, Modrinth-publishable, no pack-specific glue" goal. A later
  pack-side bridge (or an optional soft-dependency mixin, mirroring
  `vppintegration`'s own pattern) can hook it without changing this mod's
  public API.
- **A redesigned/expanded questline.** The current 62-quest book is a
  straight carry-over of the old system's content; a larger, more granular
  rewrite (enumerating every progression milestone, using the
  `criticalPath` flag for a "blindly followable" spine) is a possible
  future direction, not started here.

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
`build.gradle`, and this repo's own `.tools/jdk-21.0.11+10` if present).
The built jar lands at `build/libs/vppquests-0.1.0.jar`, which
`pack/manifest.json`'s `vppquests` entry (`source: "local"`, phase 26,
`side: "both"`) points at - `scripts/build_local_mods.py` builds it
automatically before `scripts/resolve_mods.py` hashes it into
`pack/mods.lock.json`, same as `vppintegration`.

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
