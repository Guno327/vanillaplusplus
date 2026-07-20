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
module now defaults to a declarative `pkgs.fetchurl` of the server bundle
from Modrinth's CDN via a `modrinth` pin in `nix/release.json`, falling
back to the manual-zip path while that pin is absent. The pin *is* absent:
the Modrinth project is still in draft (public API 404s), so generating it
is blocked on owner action — issue **#44** (`needs-owner`: submit project
for review + delete the stale FTB-embedding v0.1.1 draft version); once
done, run `scripts/update_nix_release.py --modrinth-only`, commit, and
close #28. #45 merged — `mint-release.yml` (#27): dispatch-anytime release
minting from main (bump input + prerelease default true; gates on ci.yml +
boot.yml via `workflow_call`; workspace-only `pack/VERSION` write; release
+ notes + nix repin + explicit Modrinth dispatch + automated sync PR).
First live mint may need the "Allow GitHub Actions to create and approve
pull requests" repo setting (couldn't be verified via PAT — 403). #23
closed: the crafted-item stage-trigger fix DID ship in v0.2.0 (rode in via
the #33 lineage; v0.2.0's blob matches main's). #21 closed: all 9 drifted
mods were already bumped to latest during #35's re-resolve and shipped
through the full v0.2.0 gate.

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
