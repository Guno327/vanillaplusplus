# Handoff

**Operating model (2026-07-19)**: this project now runs under the
machine-level AI Delivery Organization charter at `~/ORCHESTRATION.md`
(CEO → per-project PM → sonnet Engineers; PM is sole git/GitHub owner;
feature branches + PR only, Conventional Commits, tests-first). Start at
`SPEC.md` in this repo root, then this file's runbooks. The prior
orchestrator-mode + standing-loop model described in older DECISIONS.md
entries is historical context only.

**Status**: `v0.2.0` (beta) shipped 2026-07-20, superseding `v0.1.1`
(2026-07-14). This cut removed the entire FTB suite (FTB Teams/Chunks/
Quests/Library) — CurseForge-exclusive mods this project has no
redistribution permission for (#28) — replacing FTB Teams + FTB Chunks
with Open Parties and Claims (#32, Modrinth-hosted, LGPL-3.0) and FTB
Quests with a bespoke KubeJS quest tracker (#33), plus a vanilla
advancement tree as a free GUI layer over it (#36). Also folds in the QoL
wave (Lootr/Gravestone/ClientSort, #13/#14/#16) and a real bug fix (#24,
the entire RPG skill-point system was unallocatable in every category).
Full canonical L0/L1/L2 test suite green before the cut (see the `v0.2.0`
GitHub release body for exact numbers). `pack/VERSION` is `0.2.0`.
Modrinth publishing (paused since the FTB redistribution issue) resumed
alongside this cut — see `publish-modrinth.yml` and #28. `DECISIONS.md` at
the repo root is the durable decision log for everything decided in
orchestrator-mode sessions; treat it as trusted input alongside
`TODO.md`/`DESIGN.md`.

**Post-v0.2.0 (2026-07-20, later the same day)**: #43 merged — the NixOS
module defaulted to a declarative `pkgs.fetchurl` of the server bundle
from Modrinth's CDN via a `modrinth` pin in `nix/release.json`, falling
back to the manual-zip path while that pin is absent (it was: the
Modrinth project was still in draft, public API 404s). Owner then asked
to switch the default off Modrinth entirely rather than wait on its
review timeline — ground-truthed that `Guno327/vanillaplusplus` is now a
**public** repo (ran `gh repo view`) and that a plain unauthenticated
`HEAD` request to the GitHub release asset URL returns `200` with the
correct byte size, so `serverArchive` now defaults to `pkgs.fetchurl`
straight from `nix/release.json`'s repo/tag/assetName/sha256 instead —
unconditionally available for every release, no `modrinth` pin needed.
See `DECISIONS.md`'s dated entry for the full writeup. Issue **#44**
(`needs-owner`) is downgraded: submitting the Modrinth project for review
no longer unblocks anything Nix-deployment-related, but its item 2
(delete the stale FTB-embedding v0.1.1 draft version before the project
goes public) still stands on its own. #45 merged — `mint-release.yml` (#27): dispatch-anytime release
minting from main (bump input + prerelease default true; gates on ci.yml +
boot.yml via `workflow_call`; workspace-only `pack/VERSION` write; release
+ notes + nix repin + explicit Modrinth dispatch + automated sync PR).
First live mint may need the "Allow GitHub Actions to create and approve
pull requests" repo setting (couldn't be verified via PAT — 403). #23
closed: the crafted-item stage-trigger fix DID ship in v0.2.0 (rode in via
the #33 lineage; v0.2.0's blob matches main's). #21 closed: all 9 drifted
mods were already bumped to latest during #35's re-resolve and shipped
through the full v0.2.0 gate.

**v0.2.1 (2026-07-20, same evening)**: owner reported every client join
hanging at "Loading Terrain" (#49). Root cause ground-truthed via `javap`
against the installed Sable jar (Create Aeronautics' physics dep): its
per-player UDP streaming pipeline completes an auth handshake, then drops
it ~29s later and the client never survives the mid-session TCP fallback.
Fix (#50, merged): new `pack/config/sable-common.toml` setting
`DISABLE_UDP_PIPELINE = true` — Sable then uses TCP from the start.
v0.2.1 was minted with `mint-release.yml`'s **first live run**: everything
worked (gates, bundles, release, notes, nix repin, Modrinth dispatch)
except the final open-sync-PR step, refused exactly as predicted above —
the PM opened the sync PR by hand (#51, merged) and filed **#52**
(`needs-owner`) for the one-checkbox repo setting that fixes future
mints. #49 remains open (`fix-pushed` + `verify-in-game`) pending a real
in-game join. The L3 live-join test tier that would automate that check
is filed as #47 (`awaiting-approval`).

**#49 retested on v0.2.1, still hangs (2026-07-21)**: owner confirmed the
#50 fix did not resolve the Loading Terrain hang. Re-verified #50 is fully
active at runtime (javap + a fresh boot log show Sable's UDP pipeline never
starts - `l0_boot_smoke.sh` now asserts this directly, see below), which
rules Sable back OUT as the cause - the original diagnosis correlated a
real bug with the hang but that correlation no longer explains a hang that
persists with the pipeline provably disabled. #47 approved by the owner in
the same session; `scripts/tests/l3_client_join.py` added (see "Release
pipeline" below) to chase the real cause directly via a live join rather
than more static analysis.

**L3 now runs green end-to-end (2026-07-22)**: owner provided a permanent
Incus cluster so L3 has a machine with a display (see "L3 test host"
below). L3 reaches `L3 PASS` reproducibly - a real client with the full
mod set joins the dedicated server, survives a 45s post-join settle window
past Sable's historical ~29s mark without disconnecting, and is not
sitting on a loading/dirt-message screen.

**#49 ROOT-CAUSED AND FIXED (2026-07-22, later the same day)** — superseding
the "#49 did NOT reproduce" paragraph below, which is kept for the record.
The owner's full client log from a fresh `v0.2.1` freeze ends in an
unbounded repeat of JEI's `Ingredients are being added at runtime: 249
FluidStack`. Cause: **ProgressiveStages 3.0.1's JEI plugin feedback-loops
with JEI** — its ingredient listener calls `scheduleRefresh()`, the queued
refresh clears its own re-entry guard before running, and 3.0.1's
`refreshLockedFluids()` re-adds every unlocked fluid via
`addIngredientsAtRuntime`, which JEI notifies listeners for
unconditionally. `2.1` (what `v0.2.0` shipped) early-returns from that
method when no mod is locked, and this pack locks none — 3.0.1 dropped
that guard and only ever arrived as a drive-by re-resolve bump during #32.
Fix: **`progressivestages` pinned to `2.1`** in `pack/manifest.json` +
lockfile, mechanism recorded in the manifest note. Verified L0 green, and
L3 with a new direct assertion: **0** runtime ingredient-add passes on 2.1
vs **2506** in the same 45s window on 3.0.1 (deliberate positive control).
**L3 now reproduces #49** — the old "does not reproduce" finding was a gap
in what L3 looked at. Full writeup in `DECISIONS.md`. Two things stay
open on #49: an upstream bug report, and the *item*-path variant of the
same loop (`refreshJei()` re-adds owned locked item ids unconditionally in
**both** versions) — inert at `rootborn` because that tier locks nothing,
unproven once a tier is unlocked. Owner still needs to confirm in-game.

**#49 did NOT reproduce there, which is not the same as fixed.** The owner
reproduced the hang on v0.2.1 by hand; L3 does not. Something differs
between the two environments - L3 runs Mesa llvmpipe software rendering,
connects over loopback, and joins a freshly generated world - so the right
reading is "L3 does not reproduce it", not "#49 is resolved". **#49 stays
open and must not be closed on this evidence.** One concrete lead for
whoever picks it up: the join log shows Sable's *client*-side UDP channel
still going active (`Starting remote client UDP channel future` /
`Client UDP channel active`, then inactive/closed a moment later). #50
disabled the **server** pipeline only; the client half still runs.

Everything that blocked L3 turned out to be harness bugs, not pack bugs -
five of them, all now fixed and documented inline in the script. The one
worth knowing without reading the file: HeadlessMC stubs LWJGL out **by
default**, and its `-lwjgl` flag does *not* select that stub (per its own
help it "Removes lwjgl code, causing Minecraft not to render anything").
An earlier revision of this file claimed the opposite. The switch that
actually matters is the config property `hmc.check.xvfb=true`; without it
the client loads its whole mod set, reports `Backend API: NO CONTEXT`, and
dies on a Sodium fence object *even with Xvfb running perfectly*.

One acceptance criterion from #47 is **not** met: L3 does not run
`/vpp_selftest` as the joined player, so selftest.js's player-gated checks
still report SKIP and remain unexercised anywhere in the suite. Both
routes are dead ends with this toolchain (`execute as <player> run ...`
silently no-ops server-side; hmc-specifics 2.4.0 exposes no usable chat
verb) - reasoning is recorded at the KNOWN GAP comment in the script.
Worth its own issue.

**GitHub is now ground truth for outstanding bugs and in-game
verifications** (user directive, 2026-07-10): the project's GitHub repo at
`https://github.com/Guno327/vanillaplusplus` (remote `origin`) tracks all
open bugs, needs-in-game-verification checklists, and open reviews as
issues #1-#11 (#4-#11 closed/resolved as of the `v0.1.1` cut; #1-#3 remain
open, human-only verify-in-game items — see the `v0.1.1` release's
"Verification wanted" note, which now flags `/respec` as testable for #1)
— see DECISIONS.md's "GitHub as ground truth (2026-07-10)" section for the
full mapping and label state machine. `TODO.md` remains the backlog for
planned feature work; GitHub issues are for bugs/verifications/reviews
surfaced after something ships. Both `v0.1.0` and `v0.1.1` are deliberately
beta semantics (this pack has real, disclosed unverified-in-game gaps) —
see each GitHub release itself for its own full test-status/verification-
wanted summary posted at cut time.

## Release pipeline

Re-run in order to reproduce a release build (each step exits nonzero on
failure, safe to chain with `&&`); artifact naming/contents/versioning are
covered by DESIGN.md's "Bundle design"/"Versioning" sections, not repeated
here:

```
python3 scripts/resolve_mods.py          # manifest.json -> mods.lock.json
sh scripts/tests/l0_boot_smoke.sh        # build + boot + baseline-diff the log
python3 scripts/tests/l1_selftest.py     # boot + /vpp_selftest + parse the result
python3 scripts/tests/l2_client_smoke.py # full client mod set via HeadlessMC
python3 scripts/tests/l3_client_join.py  # live join against the dedicated server (needs xvfb-run, see below)
python3 scripts/build_mrpack.py          # client .mrpack
python3 scripts/build_server_bundle.py   # server .zip
python3 scripts/update_nix_release.py    # repin nix/release.json to the minted release
```

**NixOS flake obligation (added 2026-07-10)**: `update_nix_release.py` must
run *after* the GitHub release is actually cut (it reads the release back
via the API, so the release has to exist first) and its output
(`nix/release.json`) must be committed. This keeps the NixOS module
(`flake.nix`/`nix/module.nix`) informed of the current release's
version/sha256 for its `serverArchive` mismatch-warning check — the module
itself deploys from a manually downloaded release zip, not an automatic
fetch (see README.md's "Running on NixOS" section and DECISIONS.md's dated
entry for why), so nothing else about this pipeline needs to change, but
this step is easy to forget since it's new and separate from the
mrpack/server-zip build steps above. Needs a GitHub token (env var,
`--token`, or `gh auth token`).

L2 needs the HeadlessMC research instance at `/tmp/vpp-research/headlessmc/`
+ `/home/ubuntu/.minecraft` (not part of this repo; a fresh environment
would need to redo that setup — see DESIGN.md's "Release engineering"
section for the exact working launch invocation, including the two
harness-specific flags (`sodium.checks.issue2561=false`, `--retries 3`)
that took real `javap` decompilation to discover).

L3 needs everything L2 does, plus `Xvfb` on PATH (Mesa llvmpipe software
rendering is sufficient — no GPU) and the `hmc-specifics` HeadlessMC
control mod, which the script installs itself. It also writes the
HeadlessMC config properties it depends on (`hmc.check.xvfb`,
`hmc.keepfiles`) rather than assuming a hand-edited config — see
`configure_headlessmc()`.

Unlike L2 it cannot run against HeadlessMC's stubbed LWJGL: this pack's
client mod set creates a real GL fence object every render tick (Sodium),
which dies immediately without an actual (even software) GL surface. Note
this is controlled by `hmc.check.xvfb`, **not** by the `-lwjgl` launch
flag, whose meaning is the opposite of what its name suggests.

## L3 test host (owner-provided, permanent)

L3 is meant to be a standard part of the suite from now on, so the owner
granted standing access (2026-07-22) to an Incus 7.0.1 cluster at
`192.168.0.1:8443` (NixOS host, ZFS, lxc+qemu drivers).

- Talk to it with `scripts/incus_api.py` — a stdlib-only Incus REST client.
  There is no `incus`/`lxc` CLI and no `curl` on the dev box (Ubuntu Core,
  no apt, no root), which is why this exists rather than shelling out.
  Client cert lives in `~/.config/incus/`, restricted to project `vpp`;
  the server cert is pinned TOFU on first contact.
- Container `vpp-l3`: Ubuntu 24.04, 8 CPU / 12 GiB / 40 GiB on pool
  `fast`, Xvfb + Mesa llvmpipe, JDK 21.0.11+10 (same build as the pinned
  `.tools` JDK), the NeoForge 21.1.235 server install, the `~/.minecraft`
  research instance, and the repo at `/home/ubuntu/vanilla++`.
- **Run it as user `ubuntu`, never root.** HeadlessMC derives the
  Minecraft game dir from the JDK's `user.home` (the passwd entry, *not*
  `$HOME`), so as root it looks in `/root/.minecraft`, finds no versions,
  and fails at version resolution.
- `build_server.py` does **not** install NeoForge — `run.sh` and
  `libraries/` come from a one-off `neoforge-*-installer.jar --installServer`
  run that is not captured in any script. A fresh machine therefore cannot
  produce a bootable server from the repo alone. Worth fixing.

## Post-release backlog

Full detail lives in TODO.md item 12 (L3 live-client-join test, MoreCulling
long-term watch, `noisiumed`-class resolver-bug re-check) and as GitHub
issues **#3** (rendering-correctness spot-check) and **#8** (residual Rhino
const-in-for-of audit in `economy.js`/`selftest.js`) — see DECISIONS.md's
"GitHub as ground truth" section for the issue mapping. TODO.md item 9
(food overhaul) landed as part of the `v0.1.0` cut — its own needs-in-game-
verification items (diet-hearts persistence, CCK automation, Terralith
wild-crop density, SoL-Onion Food Book UI) are noted in its DESIGN.md
section but not yet filed as GitHub issues.

## What's done

Everything is implemented, boot-tested, and committed. `TODO.md` items
1-11 each carry their own DONE summary and pointer to the relevant
`DESIGN.md` section (or, for items 10/11, `DECISIONS.md`'s dated sections
plus commit hashes, since those two landed after the last DESIGN.md
transcription pass). `DECISIONS.md`'s "Post-release merges" section has
the item 10/11 merge history, including a real Rhino-scoping bug the
item-10 boot test caught and fixed forward.

**Serial-resource ownership still applies** if work resumes in
orchestrator/subagent mode: exactly one integrator agent owns git, `server/`
boots, `pack/manifest.json`+`mods.lock.json`, `pack/config/**`, and the docs
(`DESIGN.md`/`HANDOFF.md`/`TODO.md`) at a time; parallel agents get disjoint
file scopes and never touch those. This wave hit a live example of why that
matters — see `DECISIONS.md`'s operating-model notes and this session's own
checkpoint log (`/tmp/vpp-agent-checkpoints/wave2-integrator.md`) for the
concurrent-integrator race this pass detected and safely waited out rather
than fighting over git.

Full narrative and rationale for every decision lives in `DESIGN.md` —
that file, not this one, is the source of truth. `instructions.md` has the
original requirements plus a "Clarifications & Resolved Decisions"
appendix. `git log` has one detailed commit per part explaining what broke
and why, in order.

## If asked to keep building

- Read `DESIGN.md` fresh — don't assume anything from a prior session's
  summary is still accurate without checking.
- Boot-test methodology (used after every change in this project):
  `python3 scripts/build_server.py` (downloads/syncs `server/`), then
  `cd server && rm -f cmd_fifo && mkfifo cmd_fifo && export PATH=".../jdk-21.0.11+10/bin:$PATH"`,
  launch with `(tail -f cmd_fifo | timeout 120 sh run.sh nogui > /tmp/LOG 2>&1 &)`,
  poll for `Done (` / `Loading errors` / `ModLoadingException` in the log,
  grep for errors and stage-tag/recipe/material counts, then
  `echo "stop" > cmd_fifo` to shut down cleanly. As of the 1.0.0 release,
  `sh scripts/tests/l0_boot_smoke.sh` formalizes exactly this (build + boot
  + baseline-diffed log + clean stop, single exit code) — prefer it over
  hand-rolling the sequence above for a plain pass/fail check;
  `scripts/tests/l1_selftest.py` additionally drives `/vpp_selftest` for a
  runtime data/registry/command sanity sweep. IMPORTANT: always stop a
  server you booted manually (`echo "stop" > cmd_fifo`, then confirm no
  `java`/`tail -f cmd_fifo` processes remain) before booting another one —
  a stale process still holding `server/world`'s lock will make the next
  boot fail with a `DirectoryLock` exception that looks like a real bug but
  isn't (hit and lost time to this during 1.0.0's L1 development).
- Ground truth over assumption: verify against the actually-installed jar
  (decompile with `javap`/`jar tf`/`jar xf` under
  `.tools/jdk-21.0.11+10/bin`) rather than training-data memory of a mod's
  behavior — this has caught real bugs every single time it was done and
  missed several before it became habitual.
- Commit after each logical part with a detailed message (why, not just
  what) — this is what makes `git log` alone a usable resume point.

## Persistent memory

Project memory (survives across sessions, separate from this file) is at
`project_vanilla_plus_plus.md`, `feedback_autonomous_overnight_work.md` in
the auto-memory store. It's kept reasonably current but `git log` +
`DESIGN.md` are the authoritative source if the two ever disagree.
