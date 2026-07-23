# VPP Quests (planned — design only, not yet implemented)

**Status: this directory is a placeholder describing planned structure.
No Java, build config, or resources exist here yet — see GitHub issue
#109 and `DESIGN.md`'s "GitHub issue #109 — custom questing mod +
questline rebuild: design proposal" section in the parent repo for the
full design writeup, phasing, and open questions. This README exists so
the planned layout is visible before implementation starts; it is not
itself the implementation plan (DESIGN.md is authoritative).**

## What this will be

A small, standalone NeoForge 1.21.1 mod providing this modpack's own
quest book — a real dependency-graph GUI plus in-game progress
tracking — replacing the current chat-command-only KubeJS tracker
(`pack/kubejs/server_scripts/quests.js`, GitHub #33) and its
vanilla-advancement GUI layer (#36/#37/#66). Built for the
[Vanilla++ modpack](https://github.com/Guno327/vanillaplusplus), and
follows the `mods-src/<modid>/` convention GitHub #67 established
(see `mods-src/vppintegration/` for the first worked example of that
convention): a fully self-contained, independently Modrinth-publishable
project, not pack-specific glue.

## Planned layout (not yet created)

```
mods-src/vppquests/
  build.gradle, settings.gradle, gradle.properties, gradle/   — standard NeoForge mod-dev project files
  LICENSE                                                     — MIT, matching vppintegration's precedent
  src/main/java/dev/vanillaplusplus/vppquests/
    VppQuests.java                                            — mod entrypoint
    quest/Quest.java, QuestChapter.java, QuestTask.java,
         QuestReward.java                                     — data model (mirrors quests.js's existing
                                                                 5 task types / 5 reward types, plus a new
                                                                 criticalPath flag — see DESIGN.md)
    quest/QuestReloadListener.java                             — parses data/<ns>/vppquests/quest/**/*.json
    data/QuestProgressAttachment.java                          — NeoForge data attachment on the player,
                                                                 tracks completed quest ids + in-progress
                                                                 task counters, party-shared per the
                                                                 existing OPAC getPartyByMember(UUID) seam
    network/                                                   — client-sync payloads for progress + GUI state
    client/gui/QuestScreen.java, QuestTrackerOverlay.java       — the quest map/detail-panel screen and the
                                                                 persistent "next quest" HUD
    migration/                                                 — one-time migration from quests.js's
                                                                 persistentData completion map (see
                                                                 DESIGN.md's migration section)
  src/main/resources/
    META-INF/neoforge.mods.toml
    data/<ns>/vppquests/quest/<chapter>/<slug>.json             — quest definitions (data-driven; generated
                                                                 by an updated scripts/gen_quests.py, not
                                                                 hand-authored — same discipline the rest
                                                                 of this pack's content generators follow)
  README.md (this file — expand into the vppintegration-style
             "what it does" writeup once real implementation lands)
```

## Why nothing is implemented yet

GitHub #109 was scoped as **design/plan only** — the owner wanted the
architecture, migration approach, and questline-rebuild methodology
reviewed and approved before any code gets written, given the size of
the effort (a full custom mod with client/server networking and GUI
rendering, plus a full questline rewrite). See DESIGN.md for the
complete proposal, phasing (mod scaffold → migration → cutover →
questline rebuild → optional achievements/dailies fold-in), and the
open questions flagged for the owner.
