# Handoff

**Status as of this note: clean.** Working tree has no uncommitted changes,
no open tasks, nothing mid-flight. This is a context-reset checkpoint, not
a snapshot of interrupted work — read this, then just wait for the user's
next request.

## What's done

Everything through three post-launch overhauls, each fully implemented,
boot-tested, committed, and documented in `DESIGN.md`:

1. **Original 9-phase build** (tier ladder, storage, RPG skills, quests,
   economy, teams/claims, combat/magic variety, mob scaling/dungeons/space
   travel, performance/packaging) — `DESIGN.md`'s "Phase plan" section.
2. **Gear overhaul** (5 parts) — all weapon/tool/armor progression funneled
   through Silent Gear smithing or boss drops; Epic Fight's 5 weapon types
   extended across all 10 tiers with a 6-way melee skill split; Ars Nouveau
   mage armor redirected through Silent Gear; 3 boss-unique weapons.
3. **Utility overhaul** (6 parts) — fixed a real tool tier-gating bug
   (harvest_tier tags were never populated); Silent Gear's *native* Paxel
   gear type (a hand-rolled KubeJS version was built, boot-verified, then
   discarded once the native one was discovered — see the memory note
   below); gear utility traits (auto-smelt/AoE/reach/magnet); Building
   Wands; Sophisticated Backpacks + a separate "Miner's Pouch" line.
4. **Travel overhaul** (3 parts) — boats/Create Trains/Immersive Aircraft/
   Waystones teleportation, all gated by tier, pure ProgressiveStages
   locks throughout (no KubeJS needed).

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
  `echo "stop" > cmd_fifo` to shut down cleanly.
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
