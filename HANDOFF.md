# Handoff note (autonomous work session)

**UPDATE 2026-07-09 ~01:47 UTC**: user is deliberately restarting Claude
Code inside `tmux` for safety (this exact session is being killed on
purpose, not dying from a cutoff). They will type **"RESUME"** in the new
tmux-wrapped session to pick this back up. If you are the instance reading
this because the user said "RESUME": read this entire file, then
`git log --oneline -10` and `git status` to confirm real state, then
continue from the "Where things stand right now" section below. The
**CronCreate job `2857c58e` from the old session is dead** (cron jobs are
session-only, killed when Claude exits) - if the user still wants the
nightly 1-4AM America/New_York autonomous window, recreate it (see the
`feedback-autonomous-overnight-work` memory for the exact pattern/cron
math) - don't assume it's still running.

Started 2026-07-08 ~21:40 EDT. Original plan: keep implementing phases,
commit frequently, stop all work by **4:00 AM America/New_York** and leave
a final progress report as the last message. That plan still holds in the
new session too, once resumed.

This file is scratch/working state, not permanent design doc content —
DESIGN.md and instructions.md remain the source of truth. Delete this file
once the user is back and has reviewed final progress (or once superseded
by a fresher handoff note if another autonomous stretch happens later).

## Where things stand right now

Phase 3 (RPG skill/leveling system) is in progress. Picked **Pufferfish's
Skills** (framework, 3.29M downloads) + **Pufferfish's Attributes** (extra
attribute types: mining_speed, sword_damage, sprinting_speed,
bow_projectile_speed, etc, 2.46M downloads) - both confirmed on NeoForge
1.21.1, both added to pack/manifest.json and resolved into mods.lock.json.

Decided NOT to ship the official "Default Skill Trees" content pack - it
only covers 2 generic categories (combat, mining), not the specific list
instructions.md asks for (Running/Swimming/Mining/Building/Swords/Bows).
Authoring our own 6 categories instead, using Default Skill Trees' jar as a
schema reference (extracted and inspected directly - it's data/puffish_skills/
puffish_skills/categories/<name>/{category,experience,definitions,skills,
connections}.json).

Wrote `scripts/gen_skill_tree.py` - a generator (not hand-typed JSON, too
error-prone/tedious for 6 categories) that emits this datapack content into
`pack/kubejs/data/puffish_skills/puffish_skills/` (KubeJS's raw-datapack
injection folder - confirmed this exists via boot log: "Validated 0 files in
kubejs/data/"). Six categories generated: mining, swords, bows, running,
swimming, building - each a simple linear chain of ~10 nodes (not the
sprawling hex-snowflake pattern the official pack uses; that's clearly
authored via their web-based visual editor, not hand-typed, so a linear
chain is the pragmatic choice here).

Wrote `pack/kubejs/server_scripts/skills.js` - grants Building category XP
on block placement (verified via jar inspection that NO native experience
source exists for block placement - only mine_block/kill_entity/craft_item/
fish_item/enchant_item/smelt_item/increase_stat), throttled per-player.

### Bugs found by the mod's own datapack validator - status

Ran `puffish_skills-0.18.0` against our generated data; three problems
surfaced. **Both root-caused bugs have fixes APPLIED to
`scripts/gen_skill_tree.py` as of this update, but NOT YET RE-VERIFIED**
(a boot test was started and interrupted before it reached the validation
log line - see "Immediate next step" below).

1. **Bows category** [FIX APPLIED]: was using `#c:tools/bows` /
   `#c:tools/crossbows` as item tags - error: "Unknown item tag" (these
   tags don't exist). Changed to bare item ids `"bow"` / `"crossbow"`
   (matching the established convention from the mining reference example,
   which uses bare ids like `"coal_ore"` for exact matches and `#namespace:
   tag` only for actual tags) - see the `kill_entity_source(...)` calls in
   the `bows` category block.

2. **Running/Swimming categories** [FIX APPLIED]: `stat_source()` had the
   wrong JSON shape for `puffish_skills:increase_stat` - error: "Unused
   field `stat_type`", "Unused field `stat`" (both nested under an invented
   `variables` block). **Root cause, confirmed by decompiling the class
   file with `javap -p -c -constants` on
   `net/puffish/skillsmod/api/json/BuiltinJson.class`** (found in
   `/tmp/skills_inspect/skills_ex/` - re-download+extract the `skills`
   Modrinth project's jar if that scratch dir is gone, it's not committed
   anywhere): the `IncreaseStatExperienceSource$Data` record has exactly
   two top-level `data` fields, `stat` and `experience` - no `variables`
   wrapper, `amount` is an implicitly-bound variable in the expression.
   The `stat` field's bytecode (`lambda$parseStat$2`) showed it splits the
   value on `:` into two halves, then splits EACH half again on `.` to get
   a namespace+path pair - one pair identifies the StatType (looked up in
   `BuiltInRegistries.STAT_TYPE`), the other the Stat itself. So the format
   is `"<statType_namespace>.<statType_path>:<stat_namespace>.<stat_path>"`.
   For vanilla's `minecraft:custom` stat type: `"minecraft.custom:minecraft.
   sprint_one_cm"` and `"minecraft.custom:minecraft.swim_one_cm"` - both
   `stat_source()` call sites in the `running`/`swimming` category blocks
   updated to this format, and `stat_source()` itself rewritten to only
   emit `{"stat": ..., "experience": ...}` (no `variables`/`stat_type`).

3. **Building category** [not yet checked]: has no `sources` at all in its
   generated `experience.json` (intentional - XP comes from the KubeJS
   `BlockEvents.placed` script instead). This wasn't flagged by the
   validator in the run that caught bugs 1/2, so probably fine, but
   haven't seen a fully clean boot yet to be 100% sure - confirm as part of
   the next boot test.

### Immediate next step — bug 2 (running/swimming) fix was WRONG, new error signature

Re-ran the boot test with fixes 1+2 applied (log ended up at
`/tmp/skills_test2.log`; that server process has already exited on its
own, nothing left running - confirmed via `pgrep`). Result:

- **Bows fix (#1) WORKED** - no more errors about it. Bare item ids
  `"bow"`/`"crossbow"` are correct, leave that alone.
- **Running/swimming fix (#2) is STILL WRONG**, but with a different error
  now:
  ```
  Unused field `stat` at `data` at index 0 at `sources` at .../running/experience.json
  Unknown variable `amount` at `experience` at `data` at index 0 at `sources` at .../running/experience.json
  ```
  (same for swimming). So my theory that `IncreaseStatExperienceSource$Data`
  has top-level fields `stat`+`experience` (no `variables`) was **wrong** -
  "stat" IS a recognized-but-wrong key ("Unused field", not "Unknown
  field"), and critically **"amount" is STILL expected to be a
  pre-declared variable**, just like `mine_block`/`kill_entity`'s
  `variables` blocks require every variable used in an expression/condition
  to be explicitly declared via an `operations` pipeline. This strongly
  suggests `increase_stat` follows the SAME `variables`-pipeline pattern as
  every other source type (I was wrong to special-case it), and the actual
  stat identifier probably belongs as `data` on a `get_increase_amount` (or
  `get_stat` + `get_stat_value` chained) OPERATION inside a `variables`
  entry, NOT as a sibling field of `experience` at the top level. Something
  like (untested, best guess based on the pattern from mine_block/
  kill_entity, needs a live boot to confirm - do NOT guess a third time
  without testing):
  ```json
  {
    "type": "puffish_skills:increase_stat",
    "data": {
      "variables": {
        "amount": {
          "operations": [
            {"type": "get_increase_amount", "data": {"stat": "minecraft.custom:minecraft.sprint_one_cm"}}
          ]
        }
      },
      "experience": "amount * 0.02"
    }
  }
  ```
  Also worth checking: maybe the top-level field is `stats` (plural, a
  list) rather than `stat` (singular) - the earlier disassembly of
  `IncreaseStatExperienceSource$Data` showed BOTH `stat` and `stats` as
  separate string fragments in the class file, and I incorrectly assumed
  `stat` was the field without confirming against `stats`. **Two root
  causes were wrong in a row on this one field** (first `stat_type`+`stat`
  nested under `variables`, then bare `stat`+`experience`) - stop
  hypothesizing from decompiled fragments alone and either (a) iterate
  fast against a live boot (each attempt is ~10-15s to the validation
  line - much cheaper than more static analysis), trying the
  `variables`-wrapped shape above first, or (b) find the mod's actual
  GitHub source via WebFetch (linked from https://modrinth.com/mod/skills)
  and grep/read the real `IncreaseStatExperienceSource.java` directly -
  probably faster than continued bytecode reading at this point given two
  misses already.

  Update `stat_source()` in `scripts/gen_skill_tree.py` once the real shape
  is confirmed, `python3 scripts/gen_skill_tree.py`, `python3
  scripts/build_server.py`, reboot, check `/tmp/skills_test2.log`-equivalent
  for `[puffish_skills]` ERROR lines (or clean silence = success).

### Verification pattern established (reuse this)

```
cd /home/ubuntu/vanilla++
python3 scripts/gen_skill_tree.py          # regenerate datapack JSON after editing the generator
python3 scripts/build_server.py            # sync mods/config/kubejs into server/
cd server && rm -f cmd_fifo && mkfifo cmd_fifo && \
  export PATH="/home/ubuntu/vanilla++/.tools/jdk-21.0.11+10/bin:$PATH" && \
  (tail -f cmd_fifo | timeout 90 sh run.sh nogui > /tmp/skills_test.log 2>&1 &)
# wait for "Done (" in the log (use Monitor or poll the log file), then:
echo "stop" > cmd_fifo
grep -iE "puffish|error|exception" /tmp/skills_test.log
```
The `puffish_skills` mod logs a very explicit `[puffish_skills] Data pack
'puffish_skills' could not be loaded:` block with every individual problem
when our generated JSON is wrong - read that block fully after every boot,
it's the fastest signal we have (faster than static bytecode analysis).

### Once mining/swords/bows/running/swimming/building all validate cleanly

- Confirm in-game-equivalent sanity: at minimum, boot clean with zero
  `[puffish_skills]` ERROR lines in the log.
- Update `pack/manifest.json` notes if the final source/attribute choices
  changed from what's there now.
- Update `DESIGN.md`: add a "RPG skills" section documenting the six
  categories, their XP sources, and the buff list per category (mirroring
  the style of the storage section) - this hasn't been written yet, do it
  once implementation is confirmed working, not before (avoid documenting
  something that might still change during debugging).
- Commit Phase 3 with a message in the same style as prior phase commits
  (`git log --oneline` / `git log -3` for tone reference) - mention the
  two real bugs found+fixed via jar inspection, same as prior phases'
  commit messages have done (that's been a consistent, valuable pattern -
  keep it).
- Mark task #4 (Phase 3) completed via TaskUpdate, move to Phase 4 (quest
  system) if time/tokens remain - see DESIGN.md's Phase plan section for
  scope.

## General reminders for whoever/whatever resumes this

- No git remote exists on this repo - it's local-only in this sandbox.
  Don't try to push anywhere unless explicitly asked.
- Portable JDK 21 lives at `/home/ubuntu/vanilla++/.tools/jdk-21.0.11+10/`
  (downloaded from GitHub releases, not a package manager - this sandbox
  has no apt/yum, only snap + direct downloads work for tooling).
- `scripts/resolve_mods.py` (Modrinth API -> pack/mods.lock.json) and
  `scripts/build_server.py` (lockfile -> server/ folder) are the whole
  mod-management pipeline; no packwiz binary available in this environment.
- Always `python3 scripts/build_server.py` after editing anything under
  `pack/` before booting the server - `server/` is a derived/gitignored
  build output, not source.
- Commit style: detailed commit bodies explaining *why*, not just *what*,
  including any bugs found/fixed via verification and how they were found.
  Match this pattern - it's been valuable for resuming context.
