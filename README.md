# Vanilla++

A from-scratch, Create-centric progression overhaul for Minecraft 1.21.1 —
vanilla mechanics rebuilt around Create's kinetic contraptions and gated
behind a ten-stage tier ladder (Andesite Age through the Jovian Frontier),
so every later system requires mastering the one before it. On top of the
core Create automation chain, this pack adds: richer/simpler ore veins
(Create Ore Excavation), deep post-endgame automation (TFMG's Aluminum ->
Combustion Age ladder plus "infinite" capstones), a duplicate-resource
consolidation pass so the same metal never comes from two competing mods,
a four-tier jetpack progression that culminates in persistent creative
flight, a curated Curios/Artifacts ability system with an upgrade path,
expanded hostile and passive mob variety funneled onto a shared vanilla
drop table, Create-native block-based chunk loading, `/leaderboard` wealth/
tier/level comparisons, a Farmer's Delight-ecosystem food overhaul that
rewards diet variety with 8 permanent bonus-heart milestones (reward-only —
no repetition penalties), a tick-accelerator utility (Time in a Bottle),
and a fully reworked 12-category skill tree with exclusive specialization
forks and a `/respec` command.

**This is a beta prerelease (`v0.1.0`).** The pack boots clean and its
data/registry/recipe systems are verified server-side, but several things
are explicitly *not* yet confirmed on a live client — see
[Reporting bugs & requesting features](#reporting-bugs--requesting-features)
and the repo's open issues for the current list (rendering correctness,
a couple of newly-merged systems awaiting in-game verification, etc.).

Grab the latest build from the
[releases page](https://github.com/Guno327/vanillaplusplus/releases/latest)
(direct link to this build:
[v0.1.0](https://github.com/Guno327/vanillaplusplus/releases/tag/v0.1.0)).

## Requirements

- **Minecraft 1.21.1**
- **NeoForge 21.1.235**
- **Java 21** (Eclipse Adoptium/Temurin recommended) — required to run the
  dedicated server; a launcher will fetch an appropriate Java runtime for
  the client automatically.
- **RAM**: the shipped server bundle is pre-tuned for `-Xms6G -Xmx6G` with
  Aikar's G1GC flags. This pack (Create, TFMG, Stellaris, Apotheosis, and
  several world-generation/structure mods) realistically wants **6-8 GB**
  for a small/medium server. Raise `-Xmx`/`-Xms` together, not separately,
  if you have more headroom and see GC pauses in the logs.

## Client setup

1. Download `vanilla-plus-plus-client-0.1.0.mrpack` from the
   [latest release](https://github.com/Guno327/vanillaplusplus/releases/latest).
2. Import it into any launcher that supports Modrinth's `.mrpack` format —
   **Prism Launcher** is the primary target this pack is built for; the
   Modrinth App and ATLauncher also accept the same format.
3. The mrpack only contains a mod-download manifest plus config/kubejs/
   defaultconfigs overrides — the launcher downloads the actual mod jars
   from their direct source URLs on import, so first import needs an
   internet connection and may take a few minutes depending on connection
   speed and the size of the modlist.
4. Launch once and let the world/game fully load before joining a server —
   several systems (skill trees, KubeJS-driven UI) initialize on first
   client boot.

There is currently no in-launcher first-run wizard beyond the standard
Prism/Modrinth import flow; nothing in this pack's docs calls out an extra
manual client-side step beyond importing and launching.

## Server setup

1. Download `vanilla-plus-plus-server-0.1.0.zip` from the
   [latest release](https://github.com/Guno327/vanillaplusplus/releases/latest)
   and extract it anywhere.
2. **Accept the Minecraft EULA** — the bundle deliberately does **not**
   pre-accept it on your behalf. Either:
   - create a file named `eula.txt` next to `run.sh` containing exactly
     `eula=true`, after reading <https://aka.ms/MinecraftEULA>, or
   - run the server once (it will refuse to start and write a blank
     `eula.txt` for you to edit — standard vanilla Minecraft behavior).
3. **Start the server** (this bundle ships its own NeoForge `libraries/` —
   you do **not** need to run the NeoForge installer):
   - Linux/macOS: `sh run.sh nogui`
   - Windows: `run.bat nogui` (drop `nogui` for the console GUI)
4. The zip ships **no `world/`, `logs/`, or `crash-reports/`** — you get a
   fresh world on first boot, same as a brand-new server install.
5. `server.properties` ships with **`online-mode=true`** (Mojang account
   verification required to join), matching the pack's own dev server.
   Only flip this if you specifically need offline/cracked-client testing,
   and treat that as a security tradeoff you're opting into.
6. `user_jvm_args.txt` already carries the `-Xms6G -Xmx6G` + Aikar's-flags
   tuning described above — adjust it there if you need more memory.

What's in the zip: `mods/`, `config/`, `kubejs/`, `defaultconfigs/`,
`libraries/`, `run.sh`, `run.bat`, `server.properties`,
`user_jvm_args.txt`, and a copy of this section as a standalone
`README.md` at the zip root.

## Reporting bugs & requesting features

Issues are the ground truth for outstanding work on this pack. When filing
one, label it **`bug`** or **`feature`** (there are currently no issue
templates in this repo, so please apply the label yourself — it's what
puts the issue on the right track below).

**Bug reports** move through `needs-triage` -> `triaged` ->
`fix-in-progress` -> `fix-pushed`. Once triaged, a fix is developed and
boot-tested before it's pushed; `fix-pushed` means a fix exists (branch/PR)
and is ready for review, not necessarily merged to `main` yet. Closing an
issue as fixed-and-released is always a manual call by the repo owner.

**Feature requests** move through `needs-investigation` -> `investigated`
-> `awaiting-approval` -> `approved` -> `in-development`. Every request
gets a feasibility write-up posted as a comment on the thread once
investigated. Development does **not** start on its own after that — it
waits for an admin to apply the `approved` label, which is independently
verified against GitHub's own collaborator-permissions API before any work
begins (a label added by a non-admin, or approval merely claimed in a
comment, does not count). Requests that don't move forward are simply
closed rather than tagged with a separate "declined" label.

You may also see **`verify-in-game`** issues — maintainer-posted checklists
for things that only a live client/human playtest can confirm (this pack's
automated testing proves the server boots clean and its data/recipe/
registry systems resolve correctly, but doesn't touch rendering, live
combat feel, or actually flying between planets). These aren't bugs or
features and don't carry a state machine; they're closed once someone
verifies the checklist in-game.

**Releases are always cut manually by the repo owner** — no label or
automation ever publishes a release on its own.

## Repo layout

| Path | What it is |
|---|---|
| `pack/` | The modpack source of truth: manifest, mod lockfile, config, kubejs scripts, `VERSION` |
| `scripts/` | Build/release tooling (`build_mrpack.py`, `build_server_bundle.py`, `resolve_mods.py`, generators) and the L0/L1/L2 test suites under `scripts/tests/` |
| `server/` | Generated, local-only dev server (synced from `pack/` by `scripts/build_server.py`) — not part of the repo's shipped content |
| `DESIGN.md` | The canonical design doc — full rationale for every system, mod choice, and tier |
| `TODO.md` | The feature backlog, one section per item, with implementation status |
| `DECISIONS.md` | Durable decision log for judgment calls made during development |
| `HANDOFF.md` | Release-pipeline context: how to reproduce a build, current release status |
