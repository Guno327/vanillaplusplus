"""Fast-tier, stdlib-only, no-network, no-JVM regression tests for the two
defects filed against GitHub #64's L0 harness (this project's
scripts/tests/l0_boot_smoke.sh, and the same fixed-log-path bug in
l1_selftest.py/l2_client_smoke.py/l3_client_join.py):

1. A fresh server/eula.txt defaults to eula=false, so a truly fresh
   checkout dies at boot with "You need to agree to the EULA" - invisible
   only because this project's long-lived dev checkout had eula.txt
   hand-set to true (server/ is untracked). The fix belongs in the test
   harness (l0_boot_smoke.sh), NOT in build_server.py: the shipped server
   bundle (scripts/build_server_bundle.py) deliberately excludes eula.txt
   so end users make their own agreement.
2. scripts/tests/{l0_boot_smoke.sh,l1_selftest.py,l2_client_smoke.py,
   l3_client_join.py} used to hardcode their log path(s) under /tmp, so
   concurrent git worktrees running the same tier on one machine silently
   clobbered each other's log mid-run.

l0_boot_smoke.sh is POSIX sh, not Python, and its actual runtime behavior
(booting a real JVM, tailing a fifo) is not unit-testable without a JVM,
network access, and a built server/ tree - none of which the fast tier may
use. What IS testable without any of that is the script's *source text*:
that it writes eula=true before the boot step, that the write is scoped to
the gitignored server/ build artifact only (never pack/ or anything
bundled), and that its LOG path is derived from $ROOT rather than a bare
hardcoded filename. These are deliberately text/static assertions, not a
simulation of the script actually running - said explicitly rather than
faking a behavioral test that doesn't exist.
"""
import hashlib
import importlib.util
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
L0_PATH = REPO_ROOT / "scripts" / "tests" / "l0_boot_smoke.sh"


def _load_by_path(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestL0EulaFix(unittest.TestCase):
    """Static assertions on l0_boot_smoke.sh's source text - see module
    docstring for why this is text-based rather than a behavioral test."""

    def setUp(self):
        self.src = L0_PATH.read_text()

    def test_writes_eula_true_before_boot(self):
        write_idx = self.src.find('echo "eula=true"')
        boot_idx = self.src.find('sh run.sh nogui > "$LOG"')
        self.assertNotEqual(write_idx, -1, "l0_boot_smoke.sh no longer writes eula=true")
        self.assertNotEqual(boot_idx, -1, "l0_boot_smoke.sh no longer boots run.sh as expected")
        self.assertLess(
            write_idx, boot_idx,
            "eula=true must be written before the server is booted, or the "
            "EULA rejection this test guards against will still occur",
        )

    def test_eula_write_targets_gitignored_server_tree_only(self):
        # Must write into $ROOT/server/eula.txt (the untracked build
        # artifact), never into pack/ (the source of truth for what
        # ships) or anywhere build_server_bundle.py would pick it up.
        self.assertIn('> "$ROOT/server/eula.txt"', self.src)
        self.assertNotIn("pack/eula.txt", self.src)

    def test_does_not_touch_build_server_bundle_exclusions(self):
        # Guard against ever "fixing" this by editing the bundler's
        # exclusion list instead of the test harness - that would silently
        # start shipping a pre-accepted EULA to end users.
        bundle_src = (REPO_ROOT / "scripts" / "build_server_bundle.py").read_text()
        self.assertIn(
            '"eula.txt"', bundle_src,
            "build_server_bundle.py must keep excluding eula.txt from the "
            "shipped bundle - end users must accept the EULA themselves",
        )


class TestL0LogPathIsUniquePerWorktree(unittest.TestCase):
    def setUp(self):
        self.src = L0_PATH.read_text()

    def test_log_path_is_not_a_bare_hardcoded_filename(self):
        self.assertNotIn(
            'LOG="/tmp/vpp_l0_boot_smoke.log"', self.src,
            "l0_boot_smoke.sh has regressed to a fixed log path shared by "
            "every worktree - concurrent runs will clobber each other's log",
        )

    def test_log_path_is_derived_from_root(self):
        self.assertRegex(
            self.src, r'LOG="/tmp/vpp_l0_boot_smoke_\$\{?\w+\}?\.log"',
            "LOG should be built from a $ROOT-derived tag variable",
        )
        # The tag itself must actually reference $ROOT, not just look like it does.
        tag_line = next(l for l in self.src.splitlines() if "WORKTREE_TAG=" in l)
        self.assertIn("$ROOT", tag_line)

    def test_prints_log_path_at_start_of_run(self):
        # Must appear before the "build server/" step so it's visible even
        # if a later step fails or hangs.
        print_idx = self.src.find("log file for this run")
        build_idx = self.src.find("build_server.py")
        self.assertNotEqual(print_idx, -1, "l0_boot_smoke.sh must print its log path")
        self.assertLess(print_idx, build_idx)


class TestPythonTierLogPathsAreUniquePerWorktree(unittest.TestCase):
    """l1/l2/l3 compute their LOG-ish constants at import time from ROOT
    (Path(__file__).resolve()...), so loading each module and inspecting
    its constants is a real (not just textual) check of the fix, unlike
    l0's shell script."""

    def _tag_for(self, root):
        return f"{root.name}_{hashlib.sha1(str(root).encode()).hexdigest()[:10]}"

    def test_l1_log_is_root_derived(self):
        mod = _load_by_path("l1_selftest", REPO_ROOT / "scripts" / "tests" / "l1_selftest.py")
        expected_tag = self._tag_for(mod.ROOT)
        self.assertIn(expected_tag, mod.LOG.name)
        self.assertNotEqual(mod.LOG.name, "vpp_l1_selftest.log")

    def test_l2_log_is_root_derived(self):
        mod = _load_by_path("l2_client_smoke", REPO_ROOT / "scripts" / "tests" / "l2_client_smoke.py")
        expected_tag = self._tag_for(mod.ROOT)
        self.assertIn(expected_tag, mod.LOG.name)
        self.assertNotEqual(mod.LOG.name, "vpp_l2_client_smoke.log")

    def test_l3_logs_are_root_derived(self):
        mod = _load_by_path("l3_client_join", REPO_ROOT / "scripts" / "tests" / "l3_client_join.py")
        expected_tag = self._tag_for(mod.ROOT)
        for log_path, bare_name in (
            (mod.SERVER_LOG, "vpp_l3_server.log"),
            (mod.CLIENT_LOG, "vpp_l3_client.log"),
            (mod.XVFB_LOG, "vpp_l3_xvfb.log"),
        ):
            self.assertIn(expected_tag, log_path.name)
            self.assertNotEqual(log_path.name, bare_name)

    def test_l1_l2_l3_log_names_differ_from_each_other(self):
        l1 = _load_by_path("l1_selftest2", REPO_ROOT / "scripts" / "tests" / "l1_selftest.py")
        l2 = _load_by_path("l2_client_smoke2", REPO_ROOT / "scripts" / "tests" / "l2_client_smoke.py")
        l3 = _load_by_path("l3_client_join2", REPO_ROOT / "scripts" / "tests" / "l3_client_join.py")
        names = {l1.LOG.name, l2.LOG.name, l3.SERVER_LOG.name, l3.CLIENT_LOG.name, l3.XVFB_LOG.name}
        self.assertEqual(len(names), 5, f"expected 5 distinct log filenames, got {names}")


if __name__ == "__main__":
    unittest.main()
