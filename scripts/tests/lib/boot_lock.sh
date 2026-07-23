#!/bin/sh
# Shared machine-wide advisory boot lock for the shell-based test tiers
# (GitHub #80). Sourced by scripts/tests/l0_boot_smoke.sh, NOT executed
# directly.
#
# Why this exists: this machine routinely has 3-4 git worktrees checked out
# at once, each able to run scripts/tests/l0_boot_smoke.sh or the l1-l3
# Python tiers, each booting a REAL Minecraft server/client. Nothing
# previously stopped two of those from running at once - they compete for
# real CPU/RAM, which inflates boot time toward BOOT_TIMEOUT_S=200 and
# produces spurious timeouts that look like pack regressions but are really
# resource contention.
#
# The fix is a single fixed-path flock, shared across BOTH this shell helper
# and scripts/tests/lib/boot_lock.py's Python equivalent (same
# BOOT_LOCK_PATH). flock(1)/fcntl.flock() both operate on the *inode*, so a
# shell tier (L0) and a Python tier (L1/L2/L3) mutually exclude each other
# even though they hold the file open through completely different APIs -
# this is what makes the exclusion machine-wide and cross-language rather
# than merely cross-worktree-within-one-language.
#
# Usage (see l0_boot_smoke.sh):
#   . "$ROOT/scripts/tests/lib/boot_lock.sh"
#   acquire_boot_lock
#   trap 'release_boot_lock; cleanup_fifo_reader "$FIFO"' EXIT INT TERM HUP
#   ... start the FIFO reader + boot the server, start timing BOOT_TIMEOUT_S
#       only from here on, per #80's acceptance criteria ...
#
# BOOT_LOCK_PATH is deliberately a single fixed path (not tagged per
# worktree like the LOG paths elsewhere in this project) - the whole point
# is that every worktree's boot tiers contend for the SAME lock.

BOOT_LOCK_PATH="${BOOT_LOCK_PATH:-/tmp/vpp_boot_tier.lock}"
BOOT_LOCK_WAIT_TIMEOUT_S="${BOOT_LOCK_WAIT_TIMEOUT_S:-600}"
BOOT_LOCK_FD=9

# Acquires the machine-wide boot lock, blocking (with a bounded, announced
# wait) if another boot tier already holds it. Exits nonzero with a clear
# message if the wait times out, rather than hanging forever.
acquire_boot_lock() {
    eval "exec ${BOOT_LOCK_FD}>\"$BOOT_LOCK_PATH\""
    if flock -n "$BOOT_LOCK_FD"; then
        echo "== boot lock: acquired $BOOT_LOCK_PATH =="
        return 0
    fi
    echo "== boot lock: another boot holds $BOOT_LOCK_PATH, waiting (up to ${BOOT_LOCK_WAIT_TIMEOUT_S}s)... =="
    if flock -w "$BOOT_LOCK_WAIT_TIMEOUT_S" "$BOOT_LOCK_FD"; then
        echo "== boot lock: acquired $BOOT_LOCK_PATH after waiting =="
        return 0
    fi
    echo "FAIL: timed out after ${BOOT_LOCK_WAIT_TIMEOUT_S}s waiting for the machine-wide boot lock ($BOOT_LOCK_PATH) - another boot tier appears stuck; check for a hung process holding it (lsof $BOOT_LOCK_PATH) before retrying." >&2
    exit 1
}

# Releases the lock by closing its file descriptor. Safe to call even if
# the lock was never acquired.
release_boot_lock() {
    eval "exec ${BOOT_LOCK_FD}>&-" 2>/dev/null || true
}

# Kills any `tail -f "$1"` process still running against the given cmd_fifo
# path (#80: orphaned `tail -f cmd_fifo` readers left in wt-*/server hold
# the FIFO open invisibly after a cut-off session). The fifo path passed in
# is always an absolute, per-worktree path (e.g. "$ROOT/server/cmd_fifo"),
# so this pkill can never match another worktree's reader.
cleanup_fifo_reader() {
    fifo="${1:-}"
    [ -n "$fifo" ] || return 0
    pkill -f "tail -f $fifo" 2>/dev/null || true
}
