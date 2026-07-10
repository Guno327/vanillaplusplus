# Handoff

**Status**: `v0.1.0` (beta) shipped as this project's first GitHub release,
2026-07-10, after TODO.md item 9 (food overhaul) landed and closed out the
last in-progress item. TODO.md items 1-11 are all DONE — TODO.md carries a
one-line-per-item pointer into DESIGN.md's per-item sections (items 1-9) or
DECISIONS.md's dated sections (items 10/11, which predate a DESIGN.md
transcription pass). `pack/VERSION` is `0.1.0`. `DECISIONS.md` at the repo
root is the durable decision log for everything decided in orchestrator-mode
sessions; treat it as trusted input alongside `TODO.md`/`DESIGN.md`.

**GitHub is now ground truth for outstanding bugs and in-game
verifications** (user directive, 2026-07-10): the project's GitHub repo at
`https://github.com/Guno327/vanillaplusplus` (remote `origin`) tracks all
open bugs, needs-in-game-verification checklists, and open reviews as
issues #1-#8 — see DECISIONS.md's "GitHub as ground truth (2026-07-10)"
section for the full mapping and label state machine. `TODO.md` remains
the backlog for planned feature work; GitHub issues are for bugs/
verifications/reviews surfaced after something ships. `v0.1.0` is
deliberately beta semantics (this pack has real, disclosed unverified-
in-game gaps) — see the GitHub release itself for the full test-status/
verification-wanted summary posted at cut time.

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
