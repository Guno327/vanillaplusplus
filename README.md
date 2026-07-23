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

### Shaders (Iris)

The client bundle includes **Iris** (a Sodium-compatible shader loader) and
**Iris & Oculus Flywheel Compat** (fixes Create's kinetic contraptions/
ghost-block previews rendering black under a shaderpack — without it,
Flywheel just disables its optimizations whenever a shaderpack is active).
Both ship **enabled as mods but with no shaderpack installed** — shaders are
off by default so low-end setups aren't affected — as an example of how to
turn shaders on if you want them, not a mandatory visual change.

To try shaders yourself:

1. Pick a shaderpack. For this pack's Create-heavy, moderately-modded
   renderer we'd suggest **Sildur's Enhanced Default**
   ([Modrinth](https://modrinth.com/shader/sildurs-enhanced-default-shaders)) —
   genuinely minimal/subtle (closest to vanilla's own look) and one of the
   lighter-weight options that still plays nicely with Sodium/Iris. Prefer
   more visual flair and can spare the frame rate? **Complementary
   Reimagined** on its "Low" preset
   ([Modrinth](https://modrinth.com/shader/complementary-reimagined)) is a
   good step up.
   **We do not bundle either shaderpack file in this repo** — both are
   distributed under "all rights reserved"/custom licenses that permit
   installing them from their own official pages but don't clearly grant us
   the right to redistribute the file itself inside a modpack we ship. Grab
   the `.zip` from the link above instead.
2. Drop the downloaded `.zip` straight into your instance's `shaderpacks/`
   folder (Prism: right-click the instance → Folders → Shader Packs Folder).
3. In-game: Options → Video Settings → Shader Packs (Iris adds this menu),
   select the pack you downloaded, and enable it.

`scripts/build_mrpack.py` also knows how to bundle a shaderpack from
`pack/shaderpacks/` into the release automatically (same override mechanism
used for `config`/`kubejs`/`defaultconfigs`) — that directory just doesn't
exist in this repo today, for the licensing reason above. Anyone with actual
redistribution rights to a shaderpack file can drop it there and it will be
picked up on the next build.

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

## Running on NixOS

This repo ships a flake (`flake.nix` + `nix/module.nix`) with a NixOS
module (`nixosModules.default`) for running the dedicated server as a
systemd service. It **defaults to a real declarative fetch of the server
bundle straight from this repo's own GitHub release asset**
(`nix/release.json`'s `repo`/`tag`/`assetName`/`sha256`, verified via
`pkgs.fetchurl`'s `sha256` check at build time) — never from this repo's
working tree. This repo is public, so that asset URL needs no credentials.
A manually downloaded release zip is still supported as an explicit
override (see step 2 below) for a custom/older/different build.

**How you get a newer release.** `nix/release.json` pins one exact
release, and every mint rewrites that pin, so *upgrading is
`nix flake update`* on whichever input points at this repo — then
`nixos-rebuild switch`. There is deliberately no "always grab whatever is
newest" mode: a flake cannot resolve that during a pure evaluation
(`pkgs.fetchurl` needs the hash up front), and a runtime fetch would mean
your server silently changing version underneath a rebuild. Pin, update,
rebuild — the ordinary Nix workflow.

Modrinth is not involved. A Modrinth CDN fetch was tried first (#28) and
abandoned: it depends on Modrinth's own project-review status, still
pending as of this writing (#44). The release script can still record an
optional `modrinth` pin with `--modrinth`, but nothing in the module reads
it.

> **Validation status, stated plainly**: `nix` could not be installed in
> this project's own sandboxed development environment (no root, `/nix`
> cannot be created — a single-user install was attempted and failed at
> exactly that step), and this remained true when #28's GitHub-fetch
> default was added. The flake and module were written and carefully
> reviewed by hand and cross-checked against real nixpkgs source
> (`pkgs/build-support/fetchurl/default.nix`/`builder.sh`,
> `lib/types.nix`, `pkgs/top-level/all-packages.nix` for `jdk21_headless`
> on the pinned `nixos-25.11` branch), but **`nix flake check` / `nix
> build` / `nixos-rebuild` have not actually been run against them,
> `pkgs.fetchurl` default included.** Treat this as reviewed-but-untested
> and sanity-check the evaluation (`nix flake check`, then a
> `nixos-rebuild build-vm` or similar) on your own machine before relying
> on it. See `DECISIONS.md`'s dated entries for the full writeup of what
> was verified vs. assumed.

### 1. Referencing this repo as a flake input

`vanillaplusplus` is now a **public** GitHub repo, so `{ inputs.vanillaplusplus.url = "github:Guno327/vanillaplusplus"; }`
works with no credentials at all — skip straight to step 3. The
token/SSH options below are only relevant if you fork this to a private
repo of your own (separate from the server-archive question below):

- **git+https with a token** (matches this repo's own tooling convention):
  ```nix
  {
    inputs.vanillaplusplus.url =
      "git+https://x-access-token:${builtins.readFile /etc/nix/vpp-token}@github.com/Guno327/vanillaplusplus.git";
  }
  ```
  (reading the token from a file rather than inlining it keeps it out of
  your flake.nix/flake.lock history; `/etc/nix/vpp-token`, `0400`,
  root-owned, is a reasonable place for it).
- **`nix.settings.access-tokens`** (a real, documented Nix setting —
  `host=token` pairs used by Nix's own `github:`/`gitlab:` fetcher) plus
  the plain `github:` shorthand:
  ```nix
  { config, ... }:
  {
    nix.settings.access-tokens."github.com" = builtins.readFile /etc/nix/vpp-token;
  }
  ```
  ```nix
  { inputs.vanillaplusplus.url = "github:Guno327/vanillaplusplus"; }
  ```
- SSH (`git+ssh://git@github.com/Guno327/vanillaplusplus.git`) works too
  if you already have deploy-key/SSH access set up for this repo, and
  avoids token management entirely.

A **fine-grained PAT scoped read-only to this one repo** (Contents:
read-only is enough for both fetching the flake and reading releases) is
the recommended token shape either way.

### 2. The server bundle (nothing to do by default)

`services.vanillaplusplus.serverArchive` defaults to a `pkgs.fetchurl`
derivation pulling the pinned release's server bundle straight from its
GitHub release asset (`nix/release.json`'s `repo`/`tag`/`assetName`) — Nix
fetches and verifies it (against the pinned `sha256`) itself as part of
evaluating the fixed-output derivation, the same way any other pinned
dependency in a flake works. There's nothing to download by hand for the
common case; just leave `serverArchive` unset (see step 3).

Override it if you want a **different/custom/older build** instead:
grab `vanilla-plus-plus-server-*.zip` from the
[releases page](https://github.com/Guno327/vanillaplusplus/releases) and
save it somewhere on the NixOS host, e.g.
`/root/vanilla-plus-plus-server-0.1.0.zip`, then set `serverArchive` to
that path. The module still checks whatever `serverArchive` resolves to
against `nix/release.json`'s pinned sha256 on every sync, warning (not
failing) on a mismatch — for the default this is redundant with Nix's own
build-time verification; for a manual override it's the only check you
get.

(This used to be a required manual step, back when the only fetchable
release asset lived on this — then-private — GitHub repo, with no stable
unauthenticated URL to fetch it from inside a Nix derivation. A Modrinth
CDN fetch was tried as the fix for that, but Modrinth's own project-review
process stalled that pin — see `DECISIONS.md`'s dated entries for the
full history.)

### 3. Enable the module

```nix
{
  inputs.vanillaplusplus.url = "github:Guno327/vanillaplusplus"; # see step 1

  outputs = { self, nixpkgs, vanillaplusplus, ... }: {
    nixosConfigurations.myhost = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        vanillaplusplus.nixosModules.default
        {
          services.vanillaplusplus = {
            enable = true;
            eula = true; # https://aka.ms/MinecraftEULA -- must be explicit
            # serverArchive not set: defaults to fetching the pinned
            # release from Modrinth (see step 2). Uncomment to override
            # with a manually downloaded build instead:
            # serverArchive = "/root/vanilla-plus-plus-server-0.1.0.zip";
            openFirewall = true;
            # jvmOpts defaults to the shipped -Xms6G/-Xmx6G + Aikar's flags --
            # override only if you need different memory/GC tuning.
            serverProperties = {
              motd = "Vanilla++ - Create-centric progression overhaul";
              max-players = 20;
            };
          };
        }
      ];
    };
  };
}
```

### Module options (summary — see `nix/module.nix` for full descriptions)

| Option | Default | Notes |
|---|---|---|
| `enable` | `false` | |
| `eula` | `false` | Must be set `true` explicitly (assertion) — mirrors the bundle's own EULA refusal and upstream `services.minecraft-server.eula`. |
| `serverArchive` | `pkgs.fetchurl` from the pinned Modrinth release | Override with a manually downloaded release zip's path for a custom/older/different build — plain string to avoid a ~380MB Nix-store copy, or a path literal if you don't mind one. |
| `jvmOpts` | shipped `-Xms6G -Xmx6G` + Aikar's flags, verbatim | Written to `user_jvm_args.txt` fresh on every start. |
| `dataDir` | `/var/lib/vanillaplusplus` | Holds `world/`, `logs/`, `server.properties`, `eula.txt`, and the synced bundle. |
| `openFirewall` | `false` | Opens `port` in `networking.firewall`. |
| `port` | `25565` | Also feeds `server.properties`' `server-port`. |
| `user` / `group` | `vanillaplusplus` | Static (not `DynamicUser` — a poor fit for a large, must-persist `dataDir`). |
| `serverProperties` | `{}` | Attrset merged onto the shipped `server.properties`, non-destructively (nix-declared keys win, everything else — including your own manual edits in `dataDir` — survives upgrades). |

Upgrading (default/Modrinth path): update your flake input to a newer
commit of this repo (`nix flake update vanillaplusplus` or equivalent —
`nix/release.json`'s pin moves with the repo, not with anything on your
host), `nixos-rebuild switch`, restart the service — the new
`pkgs.fetchurl` derivation is fetched automatically. Upgrading with a
manual `serverArchive` override: download the new release zip, point
`serverArchive` at it (a new path, or the same path with new contents —
either works, detection is by file size+mtime), `nixos-rebuild switch`,
restart. Either way, `world/`, `logs/`, `crash-reports/`, and your
`server.properties`/`eula.txt` are never touched by the sync; only
`mods/`, `config/`, `kubejs/`, `defaultconfigs/`, `libraries/`, `run.sh`,
`run.bat` get refreshed.
Stopping is done by writing `stop` to a fifo (the same mechanism this
project's own dev boot-testing uses for a clean shutdown, see
`HANDOFF.md`), not a bare `SIGTERM`/`SIGKILL`, to avoid a stale `world/`
lock file.

## Reporting bugs & requesting features

Issues are the ground truth for outstanding work on this pack. When filing
one, label it **`bug`** or **`feature`** (there are currently no issue
templates in this repo, so please apply the label yourself — it's what
puts the issue on the right track below).

**Bug reports** move through `needs-triage` -> `triaged` ->
`fix-in-progress` -> `fix-pushed`. Once triaged, a fix is developed and
boot-tested before it's pushed; `fix-pushed` means a fix exists (branch/PR)
and is ready for review, not necessarily merged to `main` yet. A fix is
considered released once it rides a minted release cut from `main` after
the fix merged; agents may mint that release continuously (see the release
policy below), so closing an issue as fixed-and-released no longer waits on
a manual owner call.

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

**Releases may be minted continuously during development** — any
maintainer agent may cut a release at any point by dispatching
`mint-release.yml` from `main`. The one hard requirement is that a **full
test run must pass before publishing**: the workflow builds and publishes
nothing unless the fast tier (unit tests + static checks) and boot tier
(L0 boot smoke + L1 `/vpp_selftest`) are both green. There is no
owner-prompt or label gate beyond that (directives 2026-07-23 — see
`DECISIONS.md`). The L2/L3 human-in-the-loop tiers can't run on hosted
runners; every release's notes disclose that boundary rather than implying
they ran.

**The pack is in beta — releases are never minted at 1.0.0 until the owner
lifts the hold.** `scripts/ci/next_version.py` hard-refuses any `>= 1.0.0`
version (so a SemVer `major` bump from the current 0.x line fails the mint
by design), and every release ships as a `prerelease`. While in beta, a
notable/breaking wave is cut as a `minor` bump (0.y+1.0) and a routine one
as a `patch` bump (0.y.z+1).

## Repo layout

| Path | What it is |
|---|---|
| `pack/` | The modpack source of truth: manifest, mod lockfile, config, kubejs scripts, `VERSION` |
| `mods-src/` | Hand-rolled Vanilla++ mods (GitHub #67 established this convention) — each `mods-src/<modid>/` is a fully self-contained, independently Modrinth-publishable NeoForge project (own gradle build, `src/main/java`+`resources`, `README.md`, `LICENSE`). Wired into the pack via a `"source": "local"` `pack/manifest.json` entry (`resolve_mods.py` hashes the already-built jar instead of resolving one remotely) — see `mods-src/vppintegration/README.md` for the first mod built this way and DECISIONS.md's #67 entry for the full convention writeup |
| `scripts/` | Build/release tooling (`build_mrpack.py`, `build_server_bundle.py`, `resolve_mods.py`, generators), `update_nix_release.py` (repins `nix/release.json` to the latest minted release), and the L0/L1/L2 test suites under `scripts/tests/` |
| `flake.nix`, `nix/` | The NixOS flake/module for running the dedicated server (see "Running on NixOS" above) — `nix/module.nix` is the module, `nix/release.json` pins the current release's version/hash, including the GitHub release asset URL `serverArchive` fetches from by default |
| `server/` | Generated, local-only dev server (synced from `pack/` by `scripts/build_server.py`) — not part of the repo's shipped content |
| `DESIGN.md` | The canonical design doc — full rationale for every system, mod choice, and tier |
| `TODO.md` | The feature backlog, one section per item, with implementation status |
| `DECISIONS.md` | Durable decision log for judgment calls made during development |
| `HANDOFF.md` | Release-pipeline context: how to reproduce a build, current release status |
