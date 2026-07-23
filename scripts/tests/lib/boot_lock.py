"""Shared machine-wide advisory boot lock for the Python test tiers
(GitHub #80). Imported by scripts/tests/l1_selftest.py, l2_client_smoke.py,
and l3_client_join.py.

Why this exists: this machine routinely has 3-4 git worktrees checked out
at once, each able to run one of the l0-l3 boot tiers, each booting a REAL
Minecraft server/client. Nothing previously stopped two of those from
running at once - they compete for real CPU/RAM, which inflates boot time
toward BOOT_TIMEOUT_S=200 and produces spurious timeouts that look like
pack regressions but are really resource contention.

The fix is a single fixed-path flock, shared with scripts/tests/lib/
boot_lock.sh's shell equivalent (same BOOT_LOCK_PATH). fcntl.flock()/
flock(1) both lock the *inode*, so this Python lock and the shell lock
mutually exclude each other even though L0 is POSIX sh and L1-L3 are
Python - that cross-language guarantee is the actual point of #80, not
just cross-worktree-within-one-language exclusion.

Usage:
    from lib.boot_lock import BootLock, register_process_cleanup

    with BootLock():
        # start timing any BOOT_TIMEOUT_S deadline only from inside this
        # block, per #80's acceptance criteria - queueing behind another
        # run must never itself cause a timeout failure.
        tail_proc = subprocess.Popen(["tail", "-f", str(FIFO)], ...)
        register_process_cleanup(tail_proc, extra_pkill_pattern=f"tail -f {FIFO}")
        ...
"""
import atexit
import fcntl
import signal
import subprocess
import sys
import time

# Deliberately a single fixed path (not tagged per worktree like this
# project's LOG paths) - the whole point is that every worktree's boot
# tiers contend for the SAME lock. Must match scripts/tests/lib/boot_lock.sh's
# BOOT_LOCK_PATH exactly.
BOOT_LOCK_PATH = "/tmp/vpp_boot_tier.lock"
BOOT_LOCK_WAIT_TIMEOUT_S = 600
_POLL_S = 1.0


class BootLockTimeout(Exception):
    """Raised when the boot lock could not be acquired within the bounded
    wait window - a clear, specific failure rather than hanging forever."""


class BootLock:
    """Context manager around a machine-wide flock at BOOT_LOCK_PATH.

    Blocking is bounded and announced: a first non-blocking attempt either
    succeeds immediately, or prints a "waiting" message and polls with a
    hard timeout, raising BootLockTimeout (with a clear, actionable message)
    if the wait window elapses.
    """

    def __init__(self, path=BOOT_LOCK_PATH, timeout_s=BOOT_LOCK_WAIT_TIMEOUT_S,
                 announce=lambda msg: print(msg, flush=True)):
        self.path = path
        self.timeout_s = timeout_s
        self._announce = announce
        self._fh = None

    def acquire(self):
        self._fh = open(self.path, "w")
        try:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._announce(f"== boot lock: acquired {self.path} ==")
            return self
        except BlockingIOError:
            pass

        self._announce(
            f"== boot lock: another boot holds {self.path}, waiting "
            f"(up to {self.timeout_s}s)... =="
        )
        deadline = time.monotonic() + self.timeout_s
        while True:
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._announce(f"== boot lock: acquired {self.path} after waiting ==")
                return self
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    self._fh.close()
                    self._fh = None
                    raise BootLockTimeout(
                        f"timed out after {self.timeout_s}s waiting for the machine-wide "
                        f"boot lock ({self.path}) - another boot tier appears stuck; check "
                        f"for a hung process holding it (lsof {self.path}) before retrying."
                    )
                time.sleep(min(_POLL_S, max(0.0, deadline - time.monotonic())))

    def release(self):
        if self._fh is not None:
            try:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
            finally:
                self._fh.close()
                self._fh = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        return False


def register_process_cleanup(proc, extra_pkill_pattern=None):
    """Guarantee `proc` is terminated on normal exit, an uncaught exception,
    or a caught signal (#80: orphaned `tail -f cmd_fifo` readers left
    holding the FIFO open after a cut-off session).

    Registers both an atexit hook (covers normal return and Python
    exceptions propagating out of main, since finally/atexit both still run
    then) and SIGTERM/SIGINT/SIGHUP handlers (covers a killed/cut-off
    session, which otherwise bypasses try/finally entirely because the
    default disposition for those signals is immediate termination, not a
    raised exception).

    extra_pkill_pattern is defense-in-depth for the exact case #80 called
    out - the FIFO path is unique per worktree checkout, so pattern-matching
    on it can never affect another worktree's reader.
    """

    def _cleanup():
        if proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
        if extra_pkill_pattern:
            try:
                subprocess.run(["pkill", "-f", extra_pkill_pattern], check=False)
            except Exception:
                pass

    atexit.register(_cleanup)

    def _on_signal(signum, frame):
        _cleanup()
        sys.exit(128 + signum)

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        try:
            signal.signal(sig, _on_signal)
        except (ValueError, OSError):
            # ValueError: not the main thread; OSError: signal unsupported
            # on this platform. Either way, the atexit hook above still
            # covers normal exit / exception paths.
            pass

    return _cleanup
