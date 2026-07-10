#!/bin/sh
# L0 boot smoke test (release test architecture, DECISIONS.md "Release test
# + bundling architecture - ADOPTED"). Formalizes the ad-hoc grep discipline
# this project has used after every change: build server/, boot it, assert
# a clean Done line, zero fatal loading errors, the expected server-side mod
# count, KubeJS "0 errors" on both script layers, NO warning/error line
# outside the documented known-noise baseline (DECISIONS.md's "Known-
# acceptable boot noise" section plus additions this script's own author
# ground-truthed across this session's boot tests), and a clean stop.
#
# Usage: sh scripts/tests/l0_boot_smoke.sh
# Exit code 0 = PASS, nonzero = FAIL (see stderr for the specific reason).

set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
JDK="$ROOT/.tools/jdk-21.0.11+10/bin"
LOG="/tmp/vpp_l0_boot_smoke.log"
FIFO="$ROOT/server/cmd_fifo"

fail() {
    echo "L0 FAIL: $1" >&2
    exit 1
}

echo "== L0: build server/ from pack/mods.lock.json =="
cd "$ROOT" || fail "cannot cd to repo root"
python3 scripts/build_server.py || fail "build_server.py failed"

EXPECTED_JAR_COUNT=$(ls "$ROOT"/server/mods/*.jar 2>/dev/null | wc -l | tr -d ' ')
LOCKFILE_SERVER_COUNT=$(python3 -c "
import json
d = json.load(open('$ROOT/pack/mods.lock.json'))
print(len([m for m in d['mods'] if m['side'] != 'client']))
")
if [ "$EXPECTED_JAR_COUNT" != "$LOCKFILE_SERVER_COUNT" ]; then
    fail "server/mods jar count ($EXPECTED_JAR_COUNT) != lockfile side!=client count ($LOCKFILE_SERVER_COUNT)"
fi
echo "expected server mod count: $EXPECTED_JAR_COUNT (matches lockfile)"

echo "== L0: boot server (nogui, 240s timeout) =="
cd "$ROOT/server" || fail "cannot cd to server/"
rm -f cmd_fifo
mkfifo cmd_fifo
PATH="$JDK:$PATH"
export PATH
(tail -f cmd_fifo | timeout 240 sh run.sh nogui > "$LOG" 2>&1 &)

echo "== L0: poll for Done/fatal-error markers (up to 200s) =="
i=0
MATCHED=""
while [ "$i" -lt 40 ]; do
    if grep -qE "Done \(|Loading errors|ModLoadingException|FATAL|DirectoryLock" "$LOG" 2>/dev/null; then
        MATCHED=1
        break
    fi
    sleep 5
    i=$((i + 1))
done
[ -n "$MATCHED" ] || fail "server did not reach a Done/fatal-error marker within 200s - see $LOG"

if grep -qE "DirectoryLock|already locked" "$LOG"; then
    fail "world directory was locked by a stale process - stop any prior server instance first"
fi
if ! grep -qE "Done \(" "$LOG"; then
    fail "server did not print a Done( line (loading error/exception occurred) - see $LOG"
fi
if grep -qE "ModLoadingException|FATAL|Loading errors were found" "$LOG"; then
    fail "fatal mod-loading error found in boot log - see $LOG"
fi
if grep -qE "fml\.modloadingissue\.brokenfile|is a Fabric mod and cannot be loaded" "$LOG"; then
    fail "a mod jar was skipped as the wrong loader variant (regression of the noisiumed-class bug fixed in resolve_mods.py's pick_file()) - see $LOG"
fi

echo "== L0: KubeJS script-load error/warning counts must be zero =="
if ! grep -qE "Loaded [0-9]+/[0-9]+ KubeJS startup scripts in .* with 0 errors and 0 warnings" "$LOG"; then
    fail "KubeJS startup scripts did not report 0 errors/0 warnings - see $LOG"
fi
if ! grep -qE "Loaded [0-9]+/[0-9]+ KubeJS server scripts in .* with 0 errors and 0 warnings" "$LOG"; then
    fail "KubeJS server scripts did not report 0 errors/0 warnings - see $LOG"
fi

echo "== L0: diff WARN/ERROR lines against the known-noise baseline =="
# Known-acceptable boot noise. Sources: DECISIONS.md's "Known-acceptable
# boot noise" section (wave-1 baseline, 4 clean boots) plus additional
# categories ground-truthed across this release-integration session's own
# clean boots (5+ full boot cycles, Stage A/B) - pre-existing, unrelated to
# the release changes, and consistent across every boot. A test that fails
# on any of these is miscalibrated; a test that misses something NEW beyond
# this list is too loose - keep this list additive-only, one entry per
# genuinely-verified-benign category, never a blanket wildcard.
BASELINE_PATTERNS='
RuntimeDistCleaner.*invalid dist DEDICATED_SERVER
Error loading class:.*for invalid dist DEDICATED_SERVER
netherite_flywheel_recipe
Error while deserializing datapack for minecraft:wooden_sword
Couldn.t load tag c:tools
Couldn.t load tag c:enchantables
Couldn.t load tag minecraft:enchantable
Not all defined tags for registry.*c:tools/shield
Couldn.t load advancements:.*dungeons_arise
bei_ExtraDragonFight
Skipping recipe (stellaris|tfmg):.*unknown type: minecraft:empty
Skipping recipe silentgear:woodcutting/.*unknown type: woodcutter:woodcutting
Skipping recipe silentgear:sapling/.*unknown type: bonsaitrees2:sapling
RecipeComponentValue.*Failed to parse recipe .silentgear:(binding|grip)_(template|blueprint)
ModernFix.*took.*seconds to load
ConfigTracker/CONFIG.*is not correct\. Correcting
Static binding violation.*modernfix
VanillaPackResourcesBuilder.*uses unexpected schema
BuiltinKubeJSClientPlugin does not load on server side, skipping
Parsing error loading recipe farmersdelight:integration/silentgear/cutting/netherwood
'

# Strip ANSI colour codes and log4j prefix, then keep only WARN/ERROR lines.
CLEAN_LOG=$(sed -E 's/\x1b\[[0-9;]*m//g' "$LOG" | grep -E '\[(WARN|ERROR)\]')

UNKNOWN=""
OLD_IFS="$IFS"
IFS='
'
for line in $CLEAN_LOG; do
    matched=0
    for pat in $BASELINE_PATTERNS; do
        [ -z "$pat" ] && continue
        if echo "$line" | grep -qE "$pat"; then
            matched=1
            break
        fi
    done
    if [ "$matched" -eq 0 ]; then
        UNKNOWN="$UNKNOWN
$line"
    fi
done
IFS="$OLD_IFS"

if [ -n "$UNKNOWN" ]; then
    echo "L0 FAIL: WARN/ERROR lines outside the known-noise baseline:" >&2
    echo "$UNKNOWN" >&2
    fail "new warning/error class(es) detected - see above, update the baseline only after verifying each is genuinely benign"
fi

echo "== L0: clean stop =="
echo "stop" > cmd_fifo
i=0
STOPPED=""
while [ "$i" -lt 20 ]; do
    if ! pgrep -f "java.*neoforge.*server" > /dev/null 2>&1; then
        STOPPED=1
        break
    fi
    sleep 2
    i=$((i + 1))
done
[ -n "$STOPPED" ] || fail "server did not shut down within 40s of 'stop'"

echo "L0 PASS: boot clean, $EXPECTED_JAR_COUNT server mods, 0 KubeJS errors/warnings, no unbaselined WARN/ERROR, clean stop"
exit 0
