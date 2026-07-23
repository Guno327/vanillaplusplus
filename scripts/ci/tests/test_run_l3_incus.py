"""Fast-tier coverage for the pure helpers inside
`scripts/tests/run_l3_incus.py` (the driver that syncs pack/+scripts/ to the
Incus `vpp-l3` host and runs L3 there - see that module's docstring for the
full release-gate context).

None of this touches the network or the Incus API - it exercises the sync
file-selection logic and the PASS/FAIL verdict logic against real temp
directories and canned (rc, stdout, stderr) tuples, exactly the kind of
thing that must NOT regress silently: a driver that "passes" a build it
never actually synced, or that trusts exit code 0 without checking for the
PASS marker, is precisely the false-positive failure mode this whole harness
exists to rule out.

Loaded by path rather than imported by name, matching test_l3_client_join.py:
scripts/tests/ is not a package and shares no import root with scripts/ci/.
"""

import doctest
import importlib.util
import tarfile
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MODULE_PATH = REPO_ROOT / "scripts" / "tests" / "run_l3_incus.py"


def _load():
    spec = importlib.util.spec_from_file_location("run_l3_incus", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestModuleIsImportable(unittest.TestCase):
    def test_no_import_time_side_effects(self):
        """Importing must not touch the network or instantiate Incus() -
        only main() should do that. If this ever breaks, it breaks before
        the rest of this suite does something surprising."""
        module = _load()
        self.assertTrue(callable(module.main))
        self.assertTrue(callable(module.sync_to_l3))
        self.assertTrue(callable(module.run_l3))


class TestShouldSync(unittest.TestCase):
    def setUp(self):
        self.should_sync = _load().should_sync

    def test_pack_and_scripts_files_included(self):
        self.assertTrue(self.should_sync(("pack", "mods.lock.json")))
        self.assertTrue(self.should_sync(("pack", "kubejs", "startup_scripts", "foo.js")))
        self.assertTrue(self.should_sync(("scripts", "tests", "l3_client_join.py")))
        self.assertTrue(self.should_sync(("scripts", "tests", "lib", "boot_lock.py")))

    def test_pycache_dir_and_contents_excluded(self):
        self.assertFalse(self.should_sync(("scripts", "__pycache__")))
        self.assertFalse(self.should_sync(("scripts", "tests", "__pycache__", "l2_client_smoke.cpython-312.pyc")))

    def test_compiled_bytecode_suffixes_excluded_even_outside_pycache(self):
        self.assertFalse(self.should_sync(("scripts", "incus_api.pyc")))
        self.assertFalse(self.should_sync(("scripts", "weird.pyo")))


class TestIterSyncFilesAndTarball(unittest.TestCase):
    """Builds a small fake repo tree (a fake pack/ and scripts/) and checks
    the actual file-walk + tar-build behavior, not just should_sync() in
    isolation - a bug in the rglob/relative_to plumbing wouldn't show up
    in TestShouldSync alone."""

    def setUp(self):
        self.module = _load()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "pack" / "kubejs").mkdir(parents=True)
        (self.root / "pack" / "mods.lock.json").write_text("{}")
        (self.root / "pack" / "kubejs" / "startup.js").write_text("// js")
        (self.root / "scripts" / "tests" / "__pycache__").mkdir(parents=True)
        (self.root / "scripts" / "tests" / "l3_client_join.py").write_text("# py")
        (self.root / "scripts" / "tests" / "__pycache__" / "stale.pyc").write_text("junk")
        (self.root / "server").mkdir()  # must NOT be synced
        (self.root / "server" / "world_data.bin").write_text("should not sync")

    def tearDown(self):
        self.tmp.cleanup()

    def test_iter_sync_files_excludes_pycache_and_other_trees(self):
        found = {arcname for _, arcname in self.module.iter_sync_files(self.root)}
        self.assertIn("pack/mods.lock.json", found)
        self.assertIn("pack/kubejs/startup.js", found)
        self.assertIn("scripts/tests/l3_client_join.py", found)
        self.assertNotIn("scripts/tests/__pycache__/stale.pyc", found)
        self.assertFalse(any(name.startswith("server/") for name in found))

    def test_build_sync_tarball_contains_exactly_the_expected_files(self):
        dest = self.root / "out.tar.gz"
        count = self.module.build_sync_tarball(self.root, dest)
        self.assertEqual(count, 3)  # mods.lock.json, startup.js, l3_client_join.py
        with tarfile.open(dest, "r:gz") as tf:
            names = set(tf.getnames())
        self.assertEqual(
            names,
            {"pack/mods.lock.json", "pack/kubejs/startup.js", "scripts/tests/l3_client_join.py"},
        )

    def test_build_sync_tarball_raises_no_error_on_missing_sync_dirs(self):
        """A tree with neither pack/ nor scripts/ yields zero files - the
        caller (sync_to_l3) is what refuses to push that; this function
        itself just reports 0, it doesn't need to know it's a problem."""
        empty = Path(tempfile.mkdtemp())
        try:
            dest = empty / "out.tar.gz"
            count = self.module.build_sync_tarball(empty, dest)
            self.assertEqual(count, 0)
        finally:
            import shutil
            shutil.rmtree(empty)


class TestEvaluateResult(unittest.TestCase):
    def setUp(self):
        self.evaluate = _load().evaluate_result

    def test_clean_pass(self):
        passed, summary = self.evaluate(
            0, "== L3: stuff ==\nL3 PASS: a real client joined and survived.\n"
        )
        self.assertTrue(passed)
        self.assertIn("L3 PASS:", summary)

    def test_nonzero_exit_is_fail_even_with_pass_text_somewhere(self):
        passed, _ = self.evaluate(1, "L3 PASS: a real client joined and survived.\n")
        self.assertFalse(passed)

    def test_explicit_fail_marker(self):
        passed, summary = self.evaluate(1, "", "L3 FAIL: fatal client error before reaching readiness marker\n")
        self.assertFalse(passed)
        self.assertIn("L3 FAIL:", summary)

    def test_zero_exit_with_no_marker_is_still_a_fail(self):
        """The exact false-positive this driver must never produce: rc==0
        alone is not a pass. See evaluate_result()'s own docstring."""
        passed, summary = self.evaluate(0, "some unrelated output, no marker at all\n")
        self.assertFalse(passed)
        self.assertIn("no L3 PASS/FAIL marker", summary)

    def test_both_markers_present_is_a_fail(self):
        """Defense in depth: if a run somehow logged both (e.g. a crash
        during teardown after main() already printed PASS), treat it as a
        FAIL rather than trusting the earlier PASS line."""
        passed, _ = self.evaluate(
            1, "L3 PASS: a real client joined.\nL3 FAIL: teardown killed the process.\n"
        )
        self.assertFalse(passed)

    def test_no_output_at_all(self):
        passed, summary = self.evaluate(-1, "", "")
        self.assertFalse(passed)
        self.assertIn("no output captured", summary)


class TestComputeWorktreeTag(unittest.TestCase):
    def test_matches_l3_client_joins_own_derivation(self):
        """Ground-truthed against l3_client_join.py's literal
        `f"{ROOT.name}_{hashlib.sha1(str(ROOT).encode()).hexdigest()[:10]}"`
        for the fixed remote checkout path - if these ever diverge, the
        driver would tail the wrong log files and silently stream nothing."""
        import hashlib
        module = _load()
        remote_root = "/home/ubuntu/vanilla++"
        expected = f"vanilla++_{hashlib.sha1(remote_root.encode()).hexdigest()[:10]}"
        self.assertEqual(module.compute_worktree_tag(remote_root), expected)


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(_load()))
    return tests


if __name__ == "__main__":
    unittest.main()
