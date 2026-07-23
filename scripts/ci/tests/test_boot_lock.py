"""Fast-tier, stdlib-only, no-network, no-JVM regression tests for GitHub
#80's machine-wide boot lock (scripts/tests/lib/boot_lock.{sh,py}) and the
cmd_fifo-reader cleanup it adds to the l0-l3 boot tiers.

Covers:
  - BootLock acquire / contend (a second acquirer blocks until release,
    and announces the wait) / release, using a real flock against a temp
    path so this is a behavioral test, not just a source-text assertion.
  - BootLock's bounded timeout: a lock held by another process/thread for
    longer than the wait window raises BootLockTimeout with a clear
    message, rather than hanging forever.
  - register_process_cleanup's trap-equivalent behavior: a tracked
    subprocess is terminated by the atexit hook the function installs, and
    signal handlers are actually registered for SIGTERM/SIGINT/SIGHUP.
  - Cross-language consistency: scripts/tests/lib/boot_lock.sh's
    BOOT_LOCK_PATH constant matches boot_lock.py's BOOT_LOCK_PATH exactly -
    the whole point of #80 is that the shell (L0) and Python (L1-L3) tiers
    flock the SAME path, so a source-text drift here would silently break
    the cross-language guarantee without any test noticing.
  - Static assertions that l0_boot_smoke.sh and l1/l2/l3 actually source/
    import the shared helper and wire the lock + cleanup in, and that
    BOOT_TIMEOUT_S-style deadlines are computed after lock acquisition, not
    before - matching this project's existing text-assertion style for the
    parts of l0_boot_smoke.sh that aren't otherwise unit-testable without a
    JVM (see test_l0_eula_and_unique_logs.py's module docstring for the
    same rationale).
"""
import importlib.util
import multiprocessing
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
LIB_DIR = REPO_ROOT / "scripts" / "tests" / "lib"
TESTS_DIR = REPO_ROOT / "scripts" / "tests"

sys.path.insert(0, str(LIB_DIR))
import boot_lock  # noqa: E402


def _load_by_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _hold_lock_for(path, seconds, ready_flag_path):
    """Run in a child process: acquire the lock at `path`, signal readiness
    by creating `ready_flag_path`, hold it for `seconds`, then release."""
    import fcntl
    fh = open(path, "w")
    fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
    Path(ready_flag_path).write_text("ready")
    time.sleep(seconds)
    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    fh.close()


class TestBootLockAcquireContendRelease(unittest.TestCase):
    """Behavioral tests against a real flock, using a private temp path so
    this can never collide with (or be blocked by) a real boot's lock."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="vpp_boot_lock_test_")
        self.lock_path = str(Path(self.tmpdir) / "test.lock")

    def test_acquire_and_release_when_uncontended(self):
        announcements = []
        lock = boot_lock.BootLock(path=self.lock_path, timeout_s=5, announce=announcements.append)
        lock.acquire()
        try:
            self.assertTrue(Path(self.lock_path).exists())
            # No contention, so there must be no "waiting" announcement.
            self.assertTrue(any("acquired" in a for a in announcements))
            self.assertFalse(any("waiting" in a for a in announcements))
        finally:
            lock.release()

    def test_context_manager_acquires_and_releases(self):
        with boot_lock.BootLock(path=self.lock_path, timeout_s=5) as lock:
            self.assertIsNotNone(lock._fh)
        self.assertIsNone(lock._fh, "release() must clear the file handle on __exit__")

    def test_second_acquirer_contends_then_succeeds_after_release(self):
        """A held lock makes a second acquirer wait (and announce it), then
        succeed once the holder releases - the actual mutual-exclusion
        guarantee #80 requires."""
        ready_flag = Path(self.tmpdir) / "ready"
        holder = multiprocessing.Process(
            target=_hold_lock_for, args=(self.lock_path, 2, str(ready_flag))
        )
        holder.start()
        try:
            deadline = time.time() + 5
            while not ready_flag.exists() and time.time() < deadline:
                time.sleep(0.05)
            self.assertTrue(ready_flag.exists(), "holder process never signalled it acquired the lock")

            announcements = []
            start = time.monotonic()
            lock = boot_lock.BootLock(path=self.lock_path, timeout_s=10, announce=announcements.append)
            lock.acquire()
            elapsed = time.monotonic() - start
            try:
                # Actually had to wait for the holder's ~2s hold, proving
                # real mutual exclusion rather than a no-op lock.
                self.assertGreater(elapsed, 0.5, "second acquirer did not actually wait for the first")
                self.assertTrue(
                    any("waiting" in a for a in announcements),
                    "contended acquisition must announce that it is waiting",
                )
            finally:
                lock.release()
        finally:
            holder.join(timeout=5)

    def test_contended_acquire_times_out_with_clear_message(self):
        """Bounded timeout: a lock held longer than the wait window must
        raise BootLockTimeout with an actionable message, never hang."""
        ready_flag = Path(self.tmpdir) / "ready2"
        holder = multiprocessing.Process(
            target=_hold_lock_for, args=(self.lock_path, 10, str(ready_flag))
        )
        holder.start()
        try:
            deadline = time.time() + 5
            while not ready_flag.exists() and time.time() < deadline:
                time.sleep(0.05)
            self.assertTrue(ready_flag.exists(), "holder process never signalled it acquired the lock")

            lock = boot_lock.BootLock(path=self.lock_path, timeout_s=1)
            start = time.monotonic()
            with self.assertRaises(boot_lock.BootLockTimeout) as ctx:
                lock.acquire()
            elapsed = time.monotonic() - start
            # Bounded: must not have waited substantially longer than the
            # configured timeout (a hang would blow well past this).
            self.assertLess(elapsed, 5, "timeout did not actually bound the wait")
            self.assertIn(self.lock_path, str(ctx.exception))
            self.assertIsNone(lock._fh, "a timed-out acquire must not leak the file handle")
        finally:
            holder.terminate()
            holder.join(timeout=5)


class _FakeProc:
    """Minimal stand-in for subprocess.Popen, just enough for
    register_process_cleanup's poll()/terminate() calls."""

    def __init__(self):
        self.terminated = False
        self._alive = True

    def poll(self):
        return None if self._alive else 0

    def terminate(self):
        self.terminated = True
        self._alive = False


class TestRegisterProcessCleanup(unittest.TestCase):
    """register_process_cleanup is this project's trap-equivalent for the
    Python tiers: it must terminate a tracked reader process via both an
    atexit hook and real signal handlers, so a cut-off session (#80) can
    never leave an orphaned `tail -f cmd_fifo` behind."""

    def test_atexit_cleanup_terminates_live_process(self):
        proc = _FakeProc()
        cleanup = boot_lock.register_process_cleanup(proc)
        self.assertFalse(proc.terminated)
        cleanup()  # simulate the atexit hook firing
        self.assertTrue(proc.terminated)

    def test_cleanup_is_a_noop_on_an_already_dead_process(self):
        proc = _FakeProc()
        proc._alive = False
        cleanup = boot_lock.register_process_cleanup(proc)
        cleanup()  # must not raise even though poll() != None
        self.assertFalse(proc.terminated, "terminate() should not be called on an already-exited process")

    def test_registers_handlers_for_term_int_hup(self):
        import signal
        prev = {
            sig: signal.getsignal(sig)
            for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
        }
        try:
            proc = _FakeProc()
            boot_lock.register_process_cleanup(proc)
            for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
                handler = signal.getsignal(sig)
                self.assertTrue(
                    callable(handler) and handler not in (signal.SIG_DFL, signal.SIG_IGN),
                    f"register_process_cleanup did not install a real handler for {sig!r}",
                )
        finally:
            for sig, handler in prev.items():
                signal.signal(sig, handler)

    def test_extra_pkill_pattern_is_invoked_on_cleanup(self):
        calls = []
        proc = _FakeProc()
        real_run = subprocess.run

        def _fake_run(cmd, **kwargs):
            calls.append(cmd)
            return real_run(["true"])

        subprocess.run = _fake_run
        try:
            cleanup = boot_lock.register_process_cleanup(proc, extra_pkill_pattern="tail -f /some/fifo")
            cleanup()
        finally:
            subprocess.run = real_run
        self.assertTrue(
            any(cmd[:2] == ["pkill", "-f"] and cmd[2] == "tail -f /some/fifo" for cmd in calls),
            f"expected a pkill -f 'tail -f /some/fifo' call, got {calls}",
        )


class TestCrossLanguageLockPathConsistency(unittest.TestCase):
    """The entire cross-language guarantee in #80 rests on the shell and
    Python helpers flock-ing the exact same path. A silent drift here would
    make L0 and L1-L3 stop mutually excluding each other with no other test
    catching it."""

    def test_shell_and_python_lock_paths_match(self):
        sh_src = (LIB_DIR / "boot_lock.sh").read_text()
        m = re.search(r'BOOT_LOCK_PATH="\$\{BOOT_LOCK_PATH:-([^}]+)\}"', sh_src)
        self.assertIsNotNone(m, "could not find BOOT_LOCK_PATH default in boot_lock.sh")
        sh_path = m.group(1)
        self.assertEqual(
            sh_path, boot_lock.BOOT_LOCK_PATH,
            "boot_lock.sh and boot_lock.py must flock the exact same fixed path, "
            "or L0 (shell) and L1-L3 (Python) will stop mutually excluding each other",
        )

    def test_lock_path_is_fixed_not_per_worktree(self):
        # Deliberately NOT tagged like this project's LOG paths - the point
        # of #80 is that every worktree contends for the SAME lock.
        self.assertNotIn("WORKTREE", boot_lock.BOOT_LOCK_PATH)
        self.assertTrue(boot_lock.BOOT_LOCK_PATH.startswith("/tmp/"))


class TestTierWiring(unittest.TestCase):
    """Static/import-time assertions that each tier actually wires the lock
    and cleanup in - the l0 shell script's own boot behavior isn't
    unit-testable without a JVM (see test_l0_eula_and_unique_logs.py's
    module docstring for the identical rationale), so this checks source
    text there and real imported module state for the Python tiers."""

    def test_l0_sources_the_shared_lock_helper(self):
        src = (TESTS_DIR / "l0_boot_smoke.sh").read_text()
        self.assertIn('. "$ROOT/scripts/tests/lib/boot_lock.sh"', src)

    def test_l0_acquires_lock_before_backgrounding_the_boot(self):
        src = (TESTS_DIR / "l0_boot_smoke.sh").read_text()
        acquire_idx = src.find("acquire_boot_lock")
        boot_idx = src.find("timeout 240 sh run.sh nogui")
        self.assertNotEqual(acquire_idx, -1, "l0_boot_smoke.sh no longer calls acquire_boot_lock")
        self.assertNotEqual(boot_idx, -1)
        self.assertLess(
            acquire_idx, boot_idx,
            "the lock must be acquired before the server boot is backgrounded, "
            "so BOOT_TIMEOUT_S-equivalent polling starts only after acquisition",
        )

    def test_l0_traps_release_and_fifo_cleanup_on_every_exit_path(self):
        src = (TESTS_DIR / "l0_boot_smoke.sh").read_text()
        self.assertRegex(
            src, r"trap\s+'release_boot_lock;\s*cleanup_fifo_reader",
            "l0_boot_smoke.sh must trap EXIT/INT/TERM/HUP to release the lock "
            "and kill any orphaned tail -f reader",
        )
        # Must cover EXIT and at least the common terminating signals.
        trap_line = next(l for l in src.splitlines() if l.strip().startswith("trap "))
        for token in ("EXIT", "INT", "TERM"):
            self.assertIn(token, trap_line, f"trap line missing {token}: {trap_line!r}")

    def test_l1_imports_boot_lock_and_uses_it_in_main(self):
        mod = _load_by_path("l1_selftest", TESTS_DIR / "l1_selftest.py")
        self.assertTrue(hasattr(mod, "boot_lock"))
        src = (TESTS_DIR / "l1_selftest.py").read_text()
        self.assertIn("boot_lock.BootLock()", src)
        self.assertIn("boot_lock.register_process_cleanup(tail_proc", src)

    def test_l2_imports_boot_lock_and_uses_it_in_main(self):
        mod = _load_by_path("l2_client_smoke", TESTS_DIR / "l2_client_smoke.py")
        self.assertTrue(hasattr(mod, "boot_lock"))
        src = (TESTS_DIR / "l2_client_smoke.py").read_text()
        self.assertIn("boot_lock.BootLock()", src)

    def test_l3_imports_boot_lock_and_uses_it_for_both_fifo_readers(self):
        mod = _load_by_path("l3_client_join", TESTS_DIR / "l3_client_join.py")
        self.assertTrue(hasattr(mod, "boot_lock"))
        src = (TESTS_DIR / "l3_client_join.py").read_text()
        self.assertIn("boot_lock.BootLock()", src)
        # Both the server-side and client-side cmd_fifo readers must be
        # covered - #80 explicitly calls out orphaned readers left in
        # wt-*/server, and L3 has a second one (the HeadlessMC client fifo)
        # that l1_selftest.py doesn't.
        self.assertEqual(
            src.count("boot_lock.register_process_cleanup(tail_proc"), 2,
            "expected exactly two register_process_cleanup(tail_proc...) call "
            "sites in l3_client_join.py (server fifo reader + client fifo reader)",
        )

    def test_l3_boot_timeout_starts_only_after_lock_acquisition(self):
        src = (TESTS_DIR / "l3_client_join.py").read_text()
        lock_idx = src.find("with boot_lock.BootLock():")
        # Skip past boot_server()'s own definition site further up the file -
        # look only for the actual call, which lives inside
        # _run_l3_boot_and_join() (invoked from within the lock context).
        boot_server_call_idx = src.find("boot_server(env)", src.find("def _run_l3_boot_and_join"))
        self.assertNotEqual(lock_idx, -1)
        self.assertNotEqual(boot_server_call_idx, -1)
        self.assertLess(
            lock_idx, boot_server_call_idx,
            "boot_server() (which starts BOOT_TIMEOUT_S) must be called from "
            "inside the boot-lock context, not before it",
        )


if __name__ == "__main__":
    unittest.main()
