# Handoff

**Operating model (2026-07-19)**: this project now runs under the
machine-level AI Delivery Organization charter at `~/ORCHESTRATION.md`
(CEO → per-project PM → sonnet Engineers; PM is sole git/GitHub owner;
feature branches + PR only, Conventional Commits, tests-first). Start at
`SPEC.md` in this repo root, then this file's runbooks. The prior
orchestrator-mode + standing-loop model described in older DECISIONS.md
entries is historical context only.

**Current status (2026-08-12, late)**: shipped release is **`v0.8.0`**
(`pack/VERSION` == `0.8.0`); `main` is green at **`4c65676`** and **`dev`
and `main` are identical** (0 commits apart). **No unmerged work is
outstanding, shipping or otherwise, and no worktrees are left over** (the
tree is a single checkout — verify with `git worktree list`). Everything
landed this day was non-shipping — the modpack is byte-identical to
`v0.8.0` and no release was minted. (The one `pack/` touch is three added
`source_sha256` metadata fields in `pack/mods.lock.json`; no mod jar, mod
set, or client artifact changed, so no L3 run was owed.)

Landed 2026-08-12, in order: the promote `63f4a61` (#191, tracked by #190),
then JUnit coverage for the two mods that had none (#194 — `0cc1e4c` #195
vppquests, `baada43` #196 vppfixes), then the local-mod source pin
(`e5c288b` #199, closing #198) and its scope fix (`910c140` #203,
closing #202), then the vppskills per-node refund (`4c65676` #206, closing
#205).

**⚠️ THERE IS NO JDK ON THIS MACHINE — read before planning any Java work.**
`java` is not on PATH; there is no `/usr/lib/jvm`, no sdkman, no nix-store
JDK. `mods-src/<mod>/gradlew` exists but has no JVM to run on, so
**`./gradlew test` cannot be run locally, ever, by any agent.** The JUnit
tier runs *only* in GitHub Actions (`mods-tests.yml`, temurin 21).
Consequences a resuming PM must internalise:
- **CI is the compiler of record.** Every Java change is merged on CI
  evidence alone. Always block on the PR's `JUnit (<mod>)` job in-session.
- **A true tests-first red/green cycle is not observable here.** The most
  an Engineer can honestly say is "it would not have compiled". Do not
  accept, and do not let an Engineer claim, a green local test run — it is
  necessarily fabricated. Brief Engineers on this explicitly and up front;
  otherwise they burn their window hunting for gradle.
- **Engineers must verify Minecraft/NeoForge/Brigadier APIs by inspection**
  against the real neighbouring source, never from recall. A wrong symbol
  costs a full CI round-trip.
- When judging whether CI's green is meaningful, check the job log shows
  `:compileTestJava` and `:test` actually *executed* (no `UP-TO-DATE`, no
  `NO-SOURCE`) — that is the #194 lesson made checkable.
Getting a JDK installed is the single highest-leverage unblock available
and is owner-gated (machine-level provisioning, §8).

**`vppskills` is the one unblocked code lane, and here is why.** It is the
only `mods-src/*` project **absent from `pack/mods.lock.json`** — no
`hashes.sha1`, no `source_sha256`. So changes to `mods-src/vppskills/src/main/**`
do **not** trip the #198 drift check, do **not** touch `pack/`, and owe
**no L3 run**. Every other mod's `src/main/**` is gated by the re-pin →
`pack/` → L3 chain described below, and `incus` is not installed here.
`vppskills` is also non-shipping (puffish_skills is still live in-game), so
work there is reversible. When the board is otherwise owner-gated, this is
where a PM can still make real progress — #205 was picked precisely on that
reasoning, and further vppskills work (e.g. the deferred right-click-to-
refund GUI seam in `SkillTreeScreen`) is the natural continuation, with the
caveat that GUI code needing a live `Font` is untestable in this tier.

**Incident note (#170), recorded so it is not rediscovered as a mystery:**
the inert prompt-injection artifact preserved at
`/home/ubuntu/wt/67/.scratch/gen/` **was deleted on 2026-08-12** by a PM
that ran a leftover-worktree cleanup *before* reading the `needs-owner`
thread that had frozen it as evidence. It is unrecoverable (never committed
to any ref, so no copy exists anywhere). None of #170's security
*conclusions* depended on it — those came from git ground truth that is
intact — but the owner's open "purge vs. preserve for toolchain analysis"
decision was closed by accident rather than by them. Disclosed in full on
#170. **Process rule this bought: read GitHub state, including open
`needs-owner` threads, BEFORE any destructive filesystem or git operation.**
A tree looking "ambiguous" in `git worktree list` is not evidence it is
unowned.

**Local-mod source pin (#198/#199) — the drift guard, and the one known
exception (#200).** The three shipped local mods (`vppquests`, `vppfixes`,
`vppintegration`) exist as **jars committed to git**, pinned in
`pack/mods.lock.json` by `hashes.sha1`/`sha512`. Nothing tied a pinned jar
back to the source it was built from: the JUnit tier compiles from
*source*, `check_lockfile.py` never opens a jar, and `build_server.py`'s
`ensure_local_mods_built()` only makes the jar match the *pin*, never the
source. **A fix could merge to `main`, be covered by a passing named
regression test, and never reach players.**

Now each local-mod lock entry also carries **`source_sha256`** — a
deterministic fingerprint over the mod's build inputs
(`scripts/ci/local_mod_source_hash.py`), written by `resolve_one_local()`
and verified by `scripts/ci/check_local_mod_sources.py` in the fast tier.
Editing `mods-src/<modid>/src/**` without re-pinning now **fails CI**,
naming the mod and the remedy (`python3 scripts/resolve_mods.py`, then
commit the rebuilt jar *and* the lockfile). It is deliberately **not** a
rebuild-and-compare-jar-hashes check: the fast tier is stdlib-only with no
gradle or network.

**The fingerprint covers `src/main/**` only — not `src/test/**` (#202,
`910c140`).** As first landed it hashed all of `src/**`, so adding a JUnit
test to a local mod tripped the drift check even though the jar could not
change (12 of vppquests' 39 inputs were test files). The printed remedy —
re-pin the jar — would have turned every test-only PR into a
`pack/`-touching, L3-owing change, i.e. **it gate-blocked writing tests**,
backwards for a tests-first charter. `build.gradle` stays included despite
also configuring the test task, because it *can* change the jar; that
asymmetry is deliberate and documented in the module docstring.

**Practical consequence for a resuming PM, worth internalising before
planning:** a change under `mods-src/<modid>/src/test/**` is cheap and
unblocked, but **any `src/main/**` change now requires a rebuild + re-pin,
which touches `pack/` and therefore owes an L3 run this machine cannot
perform.** That is why the `QuestScreen` `ellipsize`/`stripContentWidth`/
`maxChapterScroll` clipping coverage (#159/#164) named below as the one
valuable uncovered area is **not** currently pickup-able: the helpers are
`private` and `Font`-bound, so covering them needs a `src/main/**`
extraction, not just a new test file.

Read `source_sha256`'s semantic precisely: **"the source has not moved
since the last pin"** — *not* "this jar was built from this source".
#199 backfilled the baseline from current source, and for `vppquests` the
pinned jar was built from **pre-`ef6d1bb`** source, so the backfill blessed
one pre-existing discrepancy. **#200** documents it: rebuilding on a clean
`main` with zero source edits changes exactly **one** of 53 jar entries
(`QuestProgressTracker.class`; identical entry set, order, and zip
timestamps — the build *is* deterministic), because `ef6d1bb` flipped
`dependenciesSatisfied` from `private` to package-private for testability
without re-pinning. **Behaviourally a no-op, no in-game impact.** The fix
rewrites a jar hash under `pack/`, making it client-affecting and therefore
owed an **L3 run — and `incus` is not installed in this environment**, so a
PM cannot self-serve it. Disposition per #200: **fold the re-pin into the
next `vppquests` change**, which needs a gate anyway and absorbs the delta.
Do not silently re-pin just to make the check look right.

**Test coverage (#194) — read this before assuming a green `JUnit (<mod>)`
job means anything.** #183 gave every `mods-src/*` project a CI job, but two
of the four mods had **zero tests**, so those jobs passed in ~3 minutes
without asserting anything — worse than no job, because a green check read
as coverage. Now: vppquests 0 → **57 tests** (12 classes), vppfixes 0 → **1
test**. vppquests carries named regression tests for the shipped defects
**#156** (payload round-trip using a 40,018-char blob — the oversized input
*is* the test; a small string passes on the broken `writeUtf` code too),
**#166** (`GamestageBridge`, incl. a throwing resolver swallowed to
`false`), and **#164 item 5** (`QuestRewardBridge`). The suite was verified
load-bearing by reverting the #156 fix and watching it fail with
`EncoderException: String too big (was 40018 characters, max 32767)`.

vppfixes ending at **one** test is correct, not a shortfall — it is a
bytecode-patch mod. **The hard boundary of this test tier, hit independently
from two directions: `BuiltInRegistries` is unreachable under plain JUnit**
(`IllegalArgumentException: Not bootstrapped`; `Bootstrap.bootStrap()` was
tried and NPEs headless). So any path touching a vanilla registry, plus all
Mixins, all live-server-bound code (`ServerPlayer`/`ItemStack`/
`PacketDistributor`/`ServerLifecycleHooks`), and GUI layout code needing a
live `Font`, are out of scope for this tier. **Do not treat that as a gap to
"fix" casually** — it would mean building bootstrap infrastructure this repo
has never had. The one genuinely valuable uncovered area is `QuestScreen`'s
`ellipsize`/`stripContentWidth`/`maxChapterScroll` (#159/#164 clipping): if
quest-title clipping regresses, it will still be an owner-in-game find.

Note the repo now uses the **GitHub App identity only** — the PAT-era
repo-local `user.*` override was removed and `gh`'s revoked personal-account
token was cleared (#193). **`gh auth status` reporting "not logged into any
GitHub hosts" is the correct state, not a fault**: pass
`GH_TOKEN=$(python3 /home/ubuntu/.config/github-app/mint-token.py Guno327)`
explicitly per invocation. Do not run `gh auth login`.

That promote carried onto `main`: the vppskills custom skill-tree mod
through **Phase B** (`da24691` #175 = phases 1-3 foundation, `cac6576` #180
= XP economy + one-free-respec) and the four CI-infrastructure landings of
2026-08-11/12 (#183 JUnit tier, #184 least-privilege permissions, #188
permissions enforcement + Modrinth dry-run). **All of it is
non-shipping**: the promote diff touched only `mods-src/vppskills/**`,
`scripts/ci/**`, `.github/workflows/**`, `.gitignore`, and this file —
`pack/`, `server/`, `nix/`, and `flake.nix` were untouched, so the shipped
modpack is byte-identical and no release was implied or minted.
`puffish_skills` is still the live in-game skill system; **nothing ships
until the #163 Phase-C cutover is approved** (see below).

Two consequences of that promote worth knowing:

- **The JUnit tier now actually guards `main`.** `mods-tests.yml`'s
  `push: branches: [main]` half had been inert since #183 (it only ever ran
  on PR branches), so `main` was passing by omission. First `push: main`
  run — `31564071739` on `63f4a61` — is **green** across all four mods.
- **The L3 gate was deliberately not run for this promote**, and that was
  correct, not a shortcut: the gate is scoped to *client-affecting* merges
  to `main` and to `mint-release.yml` dispatches. A mods-src/CI-only diff
  changes no pack content, no mod set, and no client artifact. `CI (boot)`
  likewise did not run on the push (path-filtered, no pack change) — also
  correct behaviour, not a gap. **The gate is unchanged and still
  mandatory for anything touching `pack/`.**

CI runs on PRs and on `main`, not on `dev` pushes. The long narrative below
(from the v0.3.0 status paragraph) is an **append-only historical log** —
accurate for its date, not the current build; reconstruct current reality
from `git log`, the GitHub releases, and open issues/PRs per ORCHESTRATION
§3, not from the older paragraphs here.

**CI tiers as of 2026-08-11** (changed — do not assume the older narrative
below): there are now *two* PR-facing tiers. **CI (fast)** (`ci.yml`) is
unchanged: stdlib-Python static validators over `pack/`, on every PR.
**Mod tests (JUnit)** (`mods-tests.yml`, added by #183) runs the JUnit
suites of every `mods-src/*` Gradle project — previously those suites had
*never* run in CI, so a PR could break every Java test and still show
green. It is path-filtered to `mods-src/**` (plus its own definition and
`scripts/ci/discover_mod_gradle_projects.py`) so docs/pack-only PRs are not
slowed, and the mod list is discovered, not hardcoded, so a fifth mod is
picked up automatically. Cost: ~2m40s–4m per mod, four jobs in parallel.

The one non-obvious thing to know before touching it: **do not "simplify"
it to call `./gradlew` directly.** A fresh checkout has neither
`gradle/wrapper/gradle-wrapper.jar` (this repo does not vendor the binary
wrapper) nor `libs/*.jar` for `vppfixes`/`vppintegration` (Modrinth-only
`compileOnly` deps) — both deliberately gitignored — so a bare `./gradlew`
dies immediately. `scripts/ci/run_mod_tests.py` bootstraps both by reusing
`scripts/build_local_mods.py`'s existing checksum-pinned wrapper fetch and
lockfile-pinned libs staging. Two attempts at #183 hit this; the second one
shipped only because the bootstrap was reused rather than re-invented.
Note the `push: branches: [main]` half of that workflow only becomes live
at the next `dev`→`main` promote.

All workflows declare explicit least-privilege `permissions:` (#184), and
as of #188 that is **enforced, not just audited**:
`scripts/ci/check_workflow_permissions.py` runs in the fast tier on every
PR and fails if a workflow declares no explicit `permissions:` block, uses
`write-all`, or performs a `gh` write operation (release/PR/issue writes,
`gh workflow run`, `gh api -X POST/PATCH/PUT/DELETE`) without the matching
write scope. It is stdlib-only — no PyYAML in the fast tier — so it uses a
narrow indentation-based parser that **fails loudly** on anything it can't
confidently parse rather than passing silently.

The earlier "audited but not run-verified — watch the next release for a
403" warning on the two Modrinth workflows is **resolved**:

- `publish-modrinth.yml` gained a `dry_run` `workflow_dispatch` input that
  gates only the `mc-publish` step. Dispatched against `v0.8.0` on
  2026-08-12 (run `31555513980`): the resolve + `gh release download` steps
  **succeeded under `contents: read`** and the publish step was skipped —
  so the audit was correct, no 403 exists, and the whole GitHub-token half
  is now re-verifiable on demand without shipping a Modrinth version.
- `modrinth-delete.yml` is now `permissions: {}`. Its `contents: read` was
  justified as "needed for the checkout itself", but that job has no
  checkout step and only curls Modrinth's API — the comment described a
  step that never existed.
- #188 also found the real hole: `mint-release.yml` had **no top-level
  `permissions:`**, so its `compute-version` job fell back to the
  repository default token. It now has a `contents: read` floor; the one
  write-performing job keeps its own write block, which overrides the floor
  for that job only.

The open backlog is **owner-gated or gate-blocked**, so a resuming PM with
no new owner input should verify `main`/green + no orphaned fixes, then
enter the §7 idle-watch loop. The one non-owner-gated item is **#200**
(vppquests re-pin), and it is blocked on an L3 run this machine cannot
perform — see above; it is not idle work a PM should pick up:

- **`needs-owner`** (awaiting the owner in the issue thread): **#170**
  (security — prompt-injection surfaced for investigation, no unauthorized
  content shipped. A full repo provenance/forensic scan was run 2026-08-11
  after a PAT exposure and posted to that thread: **no credential
  exfiltration, no non-agent-origin code, the PAT was never committed to
  any ref so no history rewrite is needed**, and the #170 injection was
  re-confirmed never to have reached `main`/`dev`. Two owner decisions
  remain: disposition of the inert artifact preserved at
  `/home/ubuntu/wt/67/.scratch/gen/` — that worktree is deliberately kept
  while the rest were cleaned up — and the still-unresolved root cause of
  how the forged context was injected), **#163** (vppskills **Phase-C cutover decision** — mod
  is built to Phase B on `dev`, non-shipping; awaiting the owner's go-ahead
  to wire it into the pack and replace live puffish_skills, which is also
  the pack's earned skill-XP economy across 8 server scripts — see the
  Phase-C scoping comment), **#44** (Modrinth distribution reach + delete
  stale v0.1.1 draft version).
- **`verify-in-game`** (awaiting the owner's in-game confirmation; the fix
  for each is already merged to `main` and shipped): **#166**, **#159**,
  **#155**, **#154**, **#116**, **#94**, **#91**, **#67**, **#141** (v0.7.0
  NC-mod swaps; owner ruled option 3 / accept-risk on 2026-08-02, so its
  `needs-owner` is cleared — only in-game confirmation remains), and **#1**
  (verify item 11: skill-tree exclusive fork + /respec; per-node refund is
  the still-open design item, folded into #163's Phase-C scope).

No open PRs. Local worktree hygiene (2026-08-11): 21 stale agent worktrees
were removed and 2 pruned; all 102 branches were left intact.
`/home/ubuntu/wt/67` is deliberately preserved as #170 evidence.

**Historical — v0.3.0 status (2026-07-22)**: `v0.3.0` (prerelease) shipped,
superseding `v0.2.1`. `pack/VERSION` was `0.3.0`. **This was a breaking cut
for both sides** — the server's mod set changed, so a v0.3.0 client will not
connect to a v0.2.1 server.

What it contains:

- **#49 fixed by removing ProgressiveStages entirely.** Its client JEI plugin
  fed its own ingredient-refresh notifications back into itself and froze
  every client on "Loading Terrain". Pinning was not enough — the same loop
  returned at the first tier unlock (7810 refresh passes in 30s, measured) —
  so progression now gates on materials and recipes alone. Stages survive as
  markers on KubeJS's own persistent backend, granted by
  `progression_stage_bridge.js`. See `DECISIONS.md`'s two dated entries.
- **Mob-spawn gating, dimension-travel blocking and locked-item masking are
  gone with it**, deliberately ("pure materials only", owner decision). Born
  in Chaos mobs spawn from world start; the Nether is open immediately.
- **JEI acquisition-info wave (#57)**: seven info addons (JER, Advanced Loot
  Info, JEI WorldGen, Just Enough Breeding/Professions/Effects, Enchantment
  Descriptions) plus `jei_info.js`, a pack-aware layer that reads the tables
  owning each behaviour rather than hand-copied lists.
- **Mob difficulty scaling works for the first time.** A wrong
  attribute-operation id (`multiply_base`, which is puffish_skills'
  vocabulary, not vanilla's) threw on every scaled spawn — killing the stat
  boost, the star nametags and the death-reward bonus. Found by L3's new
  post-join stage-grant probe.
- **Nix/flake**: the module fetches the server bundle straight from this
  repo's public GitHub release asset; Modrinth is off the critical path
  entirely (#60). Upgrading a host is `nix flake update` + `nixos-rebuild
  switch`.

Test suite at cut time: L0 PASS (94 server mods), L1 PASS 31/31, L2 PASS (100
client mods / 124 modids), L3 PASS (0 refresh-loop passes after join *and*
after a tier grant). **Not yet confirmed by a human in game — that is #58**,
and its headline check is not "does it join" but "craft an Andesite Alloy and
keep playing", because the previous build joined fine and only froze at the
first tier unlock.

**Previously** — `v0.2.0` (beta) shipped 2026-07-20, superseding `v0.1.1`
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

One acceptance criterion from #47 is **not** met, and can't be: L3 does not
run the `/vpp_selftest` **command** itself as the joined player. Both routes
tried are dead ends with this toolchain (`execute as <player> run ...`
silently no-ops server-side; hmc-specifics 2.4.0 exposes no usable chat
verb) - reasoning is recorded at the KNOWN GAP comment in the script.

That gap was tracked as #65 and is now closed a different way: what actually
mattered was exercising selftest.js's player-gated *checks* (not literally
invoking the command), so #65 wired a test-only `PlayerEvents.stageAdded`
hook in selftest.js (`ST_TEST_HOOK_STAGE = 'vpp_test_selftest_hook'`, a
sentinel id nothing else in the pack ever grants) that runs the exact same
`ST_CHECKS` loop the command runs, against the real `ServerPlayer` KubeJS's
own `Stages.add()` hands the event (javap-confirmed on
kubejs-neoforge-2101.7.2-build.368.jar: the default `add()` method posts
`PlayerEvents.STAGE_ADDED` with `getPlayer()` before returning, for any
`Stages` backend - the same mechanism `mobility.js`'s own
`stageAdded('starforged_age', ...)` already relies on). L3 grants that
sentinel post-join with the exact same `kubejs stages add <player> <stage>`
command it already uses for `STAGE_PROBE`, reads the hook's
`VPP_SELFTEST_HOOK_LINE:`/`VPP_SELFTEST_HOOK:` lines back from the server
log, asserts the summary is PASS, and asserts at least one check actually
ran PASS/FAIL (not SKIP) - then reverts the grant so a rerun against the
same reused world sees a fresh transition and the hook fires again.
Statically verified (CI green, javap-checked event wiring); **needs one real
L3 run on the owner's Incus host to confirm it fires and passes in
practice** - not runnable in this sandbox.

**#49 root-caused and fixed by dropping ProgressiveStages (2026-07-22)**:
the owner's full freeze log ended in an unbounded repeat of JEI's
`Ingredients are being added at runtime: 249 FluidStack`. ProgressiveStages'
client JEI plugin registers an ingredient listener that calls
`scheduleRefresh()`, its queued refresh clears its own re-entry guard before
running, and the refresh re-adds ingredients through
`addIngredientsAtRuntime` — which JEI notifies listeners for unconditionally.
Pinning to 2.1 fixed only *joining*: the item-path variant of the same loop
fired the moment a tier unlocked (measured on the pinned build: **7810**
refresh passes in 30s after `andesite_age`). PR #55 (the pin) was closed
unmerged; the owner's call was to remove the mod entirely and gate
progression by materials and recipes alone.

That was cheap because KubeJS ships its own persistent stage backend
(`StageEvents.create()` -> `TagWrapperStages` when no mod claims
`StageCreationEvent`), so `player.stages` and every script reading it —
quests, mob scaling, flight, leaderboard, selftest — needed no changes.
`progression_stage_bridge.js` absorbed the three trigger types the mod still
owned (starting stage, the four Stellaris dimension stages, ender-dragon ->
starforged_age); the tier TOMLs moved to `pack/progression/` as generator
design data; and new `tier_gating.js` adds one tier material to the 13
recipes whose only gate was the deleted lock (Waystones, backpack/wand
tiers, Tom's upper terminals, Create Ore Excavation's drill). Mob-spawn
gating, dimension-travel blocking and locked-item name masking are
deliberately gone, not reimplemented. Full writeup in `DECISIONS.md`.

Verified L0 PASS (88 mods), L1 PASS 28/28 (three new checks), and L3 PASS
with two new assertions — a refresh-loop counter and a post-join stage-grant
probe: **0** ingredient-add passes after granting `andesite_age`, against
7810 on the pinned-2.1 build.

**No upstream bug report will be filed** (owner decision, 2026-07-22). One was
written up in full — mechanism, both loop paths, a measured repro and three
suggested fixes — but this pack no longer ships ProgressiveStages, so chasing
a fix in someone else's mod buys this project nothing. It is dropped from the
backlog deliberately, not forgotten; the full analysis lives in `DECISIONS.md`
if it is ever needed again (e.g. if a future pack wants the mod back).

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

**Policy (CEO directive, 2026-07-23 — see DECISIONS.md "Release policy"):**
agents may mint releases (major/minor/patch) continuously throughout
development. No owner-prompt gate; the sole hard requirement is a full test
run green before publish. In practice you cut a release by dispatching
`mint-release.yml` from `main` (it runs fast-tier + boot-tier as required
`needs:` gates, then builds + publishes). The manual step sequence below is
the local-reproduction / debugging runbook for that same build — the
workflow is the normal path now.

**RELEASE GATE — required, owner-host, cannot be skipped (client-test-harness
hardening, follow-up to the v0.5.0/v0.5.1 client-only launch regressions):**
`mint-release.yml`'s fast-tier + boot-tier gates both boot only the
*dedicated server* — L0/L1/`check_lockfile`/etc structurally cannot see a
client-only launch crash, because `side:client` mods never land in
`server/mods`. Two releases shipped broken anyway because of exactly that
blind spot: v0.5.0 (a client-only mod hard-requiring a never-installed
dependency) and v0.5.1 (`sodium-dynamic-lights`/`lambdynlights_api`
exporting the same Java module package - `java.lang.module.
ResolutionException` at client startup, before any mod code even runs).
L3 (`scripts/tests/l3_client_join.py`) already boots a real client against
this exact failure class, but before this hardening pass it wasn't a
required step and was fragile to drive by hand against the Incus test host
(`vpp-l3` is not a git checkout — see "L3 test host" below - so nothing
before this synced the CURRENT pack onto it, and a stale-content run
"passes" a build it never actually looked at).

The required step, before merging any client-affecting PR to `main` and
before dispatching `mint-release.yml`:

```
python3 scripts/tests/run_l3_incus.py
```

This one command syncs the current `pack/` + `scripts/` trees onto
`vpp-l3` (replacing whatever was there), pre-cleans any stale process/FIFO
left by an earlier run, runs `run_l3.sh` there as `ubuntu`, streams the
server/client log tails as the run progresses, and prints one of:

```
L3 GATE: PASS
L3 GATE: FAIL
```

**A merge/mint may only proceed on `L3 GATE: PASS`.** This cannot run on a
hosted GitHub runner - it needs a real (even if software/Xvfb) GL surface
and the Incus host's fixed `vpp-l3` container, neither of which a hosted
runner has - so it is an owner/PM-run manual step, not wired into
`mint-release.yml`'s `needs:` gates.

**Status as of this hardening pass: the driver works and catches real
regressions, but `L3 GATE: PASS` has not yet been reached against any
branch.** Run against `main` at the v0.5.1 state: FAILS immediately with
the exact `ResolutionException` above, confirming the driver catches the
class of bug it was built for. Run against
`hotfix/remove-sodium-dynamic-lights-splitpackage`: that crash is gone
(mod discovery/loading/rendering all complete, client reaches the main
menu) - **the split-package fix itself is confirmed correct** - but the
join is then blocked by two SEPARATE, previously-hidden bugs the fix
doesn't touch: (1) `baguettelib` is pinned `side:"server"` but its
NeoForge channel is required client-side too, so the server rejects the
client with "Incompatible client!" at connect time; (2) once that's
worked around, the join disconnects ~30s later with `Connection reset by
peer` - the exact signature of the still-open #49 lead (Sable's
**client**-side UDP channel; `#50` only disabled the **server** side).
Both reproduced on independent runs, not one-off flakes. See
DECISIONS.md's dated "L3 client boot+join becomes a REQUIRED release
gate" entry for the full evidence and follow-up items - **do not promote
this hotfix branch to `main` on the strength of the split-package fix
alone; the pack cannot reach a real client join yet.** See
`scripts/tests/run_l3_incus.py`'s own module docstring for the sync-set
reasoning and `scripts/ci/tests/test_run_l3_incus.py` for its unit
coverage.

**STATIC follow-up (client-test-harness hardening, disjoint pass,
2026-07-23): `scripts/ci/check_mod_dependencies.py` (boot tier) now also
statically catches v0.5.1's actual failure class** - Java split packages
(two mods/Jar-in-Jar bundles exporting the same package -
`java.lang.module.ResolutionException`) and mods declaring an
`[[accessTransformers]]` file that isn't actually packaged (the incident
log's other line: `Access transformer file accesstransformer.cfg provided
by mod irisflw does not exist!`). This closes the gap L3 alone left open:
L3 proves a specific build boots on real hardware, but only after the fact
and only on the owner's Incus host; this new check fails the boot tier
itself (and therefore blocks a mint) the moment a split-package-conflicting
mod is added, without needing an L3 run to discover it. Validated against
reality, not synthetic-only: run against `main`'s actual pinned mod set it
correctly FAILS with the exact `sodium-dynamic-lights` /
`ars-nouveau`-JIJ'd-`lambdynlights_api` conflict (main still carries the
v0.5.1 regression - `hotfix/remove-sodium-dynamic-lights-splitpackage`
above was never merged, pending the two separate join-blocking bugs it
found); run against that hotfix branch's mod set (sodium-dynamic-lights
removed) it PASSES clean, 113 mods, zero split-package/AT problems. See
`check_mod_dependencies.py`'s module docstring for the exact
de-duplication rule (keyed on each Jar-in-Jar bundle's own declared modId,
matching NeoForge's real Jar-in-Jar selection - validated against this
pack's own `create`+`iris-flw-compat` both bundling `flywheel` under
different Maven coordinates but the same modId, correctly NOT flagged) and
`scripts/ci/tests/test_check_mod_dependencies.py` for unit coverage
(fixtures mirror the real sodium-dynamic-lights/lambdynlights/flywheel
jar shapes).

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
                                          # - on the Incus vpp-l3 host, use the driver instead:
                                          #   python3 scripts/tests/run_l3_incus.py (see "RELEASE GATE" above)
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

As of the v0.3.0 cut, the open items are:

- **#58** (`verify-in-game`) — does v0.3.0 actually fix #49 on real hardware.
  The one thing no tier in this suite can settle; read its checklist before
  testing, the discriminating step is the tier unlock, not the join.
- **#52** (`needs-owner`) — the repo setting that lets Actions open the
  post-release sync PR. Until it lands, every mint needs that PR opened by
  hand (done for v0.2.1 as #51 and v0.3.0 as #59). One checkbox.
- **#44** (`needs-owner`) — Modrinth project review. No longer blocks
  anything: the Nix module fetches from this repo's public GitHub release
  (#60), so this is now purely about distribution reach.
- **#61 / #62** — this session's two deliberate follow-ups (a recursive
  recipe-reachability audit tool, and L3's `gui` command needing the same
  resend-until-answered treatment `connect` already has).
- TODO.md item 12's remaining watch items (MoreCulling long-term watch,
  `noisiumed`-class resolver-bug re-check) — its L3 live-client-join entry is
  now **delivered** (#47, merged with #56).
- GitHub issues **#3** (rendering-correctness spot-check) and **#8**
  (residual Rhino const-in-for-of audit in `economy.js`/`selftest.js`) — see
  DECISIONS.md's "GitHub as ground truth" section for the issue mapping. TODO.md item 9
(food overhaul) landed as part of the `v0.1.0` cut — its own needs-in-game-
verification items (diet-hearts persistence, CCK automation, Terralith
wild-crop density, SoL-Onion Food Book UI) are noted in its DESIGN.md
section but not yet filed as GitHub issues.

## What's done

v0.5.0 follow-up hardening: missing-mod-dependency detection now also runs
in **fast-tier** (every PR/push via `ci.yml` → `run_all.py`), not just
`boot.yml`'s weekly/on-dispatch/at-mint runs. New `scripts/gen_mod_
dependencies.py` (network, run by hand on lockfile changes) produces a
committed offline snapshot `pack/mod_registries/mod_dependencies.json`;
new `scripts/ci/check_mod_dependencies_offline.py` validates it's in sync
with `pack/mods.lock.json` and re-runs the same `resolve()` logic against
it, entirely offline. See `DESIGN.md`'s "Fast-tier missing-dependency check
(v0.5.0 follow-up hardening)" section for the full design and how the sync
guard works.

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
