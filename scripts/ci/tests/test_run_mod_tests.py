import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import run_mod_tests  # noqa: E402


def _make_mod_dir(root, name, gradlew=True, libs_json=None):
    mod_dir = Path(root) / "mods-src" / name
    mod_dir.mkdir(parents=True)
    if gradlew:
        (mod_dir / "gradlew").write_text("#!/bin/sh\n")
    if libs_json is not None:
        (mod_dir / "libs.json").write_text(libs_json)
    return mod_dir


class RunModTestsTest(unittest.TestCase):
    def _patch_mods_src(self, root):
        return mock.patch.object(run_mod_tests, "MODS_SRC", Path(root) / "mods-src")

    def test_mod_with_libs_json_triggers_stage_libs(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_mod_dir(tmp, "vppintegration", libs_json='["silent-gear"]')
            with self._patch_mods_src(tmp), \
                    mock.patch.object(run_mod_tests.build_local_mods, "stage_libs") as m_stage, \
                    mock.patch.object(run_mod_tests.build_local_mods, "ensure_gradle_wrapper_jar") as m_wrapper, \
                    mock.patch.object(run_mod_tests.build_local_mods, "gradle_env", return_value={}), \
                    mock.patch("run_mod_tests.subprocess.run") as m_run:
                m_run.return_value.returncode = 0
                code = run_mod_tests.run_mod_tests("vppintegration")
            self.assertEqual(code, 0)
            m_stage.assert_called_once()
            self.assertEqual(m_stage.call_args[0][1], ["silent-gear"])
            m_wrapper.assert_called_once()

    def test_mod_without_libs_json_skips_stage_libs(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_mod_dir(tmp, "vppskills")
            with self._patch_mods_src(tmp), \
                    mock.patch.object(run_mod_tests.build_local_mods, "stage_libs") as m_stage, \
                    mock.patch.object(run_mod_tests.build_local_mods, "ensure_gradle_wrapper_jar") as m_wrapper, \
                    mock.patch.object(run_mod_tests.build_local_mods, "gradle_env", return_value={}), \
                    mock.patch("run_mod_tests.subprocess.run") as m_run:
                m_run.return_value.returncode = 0
                code = run_mod_tests.run_mod_tests("vppskills")
            self.assertEqual(code, 0)
            m_stage.assert_not_called()
            m_wrapper.assert_called_once()

    def test_ensure_gradle_wrapper_jar_always_called(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_mod_dir(tmp, "vppquests")
            with self._patch_mods_src(tmp), \
                    mock.patch.object(run_mod_tests.build_local_mods, "ensure_gradle_wrapper_jar") as m_wrapper, \
                    mock.patch.object(run_mod_tests.build_local_mods, "gradle_env", return_value={}), \
                    mock.patch("run_mod_tests.subprocess.run") as m_run:
                m_run.return_value.returncode = 0
                run_mod_tests.run_mod_tests("vppquests")
            m_wrapper.assert_called_once()

    def test_nonzero_gradle_exit_propagates(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_mod_dir(tmp, "vppfixes")
            with self._patch_mods_src(tmp), \
                    mock.patch.object(run_mod_tests.build_local_mods, "ensure_gradle_wrapper_jar"), \
                    mock.patch.object(run_mod_tests.build_local_mods, "gradle_env", return_value={}), \
                    mock.patch("run_mod_tests.subprocess.run") as m_run:
                m_run.return_value.returncode = 1
                code = run_mod_tests.run_mod_tests("vppfixes")
            self.assertEqual(code, 1)

    def test_unknown_mod_name_errors_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "mods-src").mkdir()
            with self._patch_mods_src(tmp):
                with self.assertRaises(SystemExit) as ctx:
                    run_mod_tests.run_mod_tests("doesnotexist")
            self.assertIn("no such mod directory", str(ctx.exception))

    def test_dir_with_no_gradlew_errors_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            _make_mod_dir(tmp, "notgradle", gradlew=False)
            with self._patch_mods_src(tmp):
                with self.assertRaises(SystemExit) as ctx:
                    run_mod_tests.run_mod_tests("notgradle")
            self.assertIn("no gradlew", str(ctx.exception))

    def test_main_requires_exactly_one_arg(self):
        self.assertEqual(run_mod_tests.main([]), 1)
        self.assertEqual(run_mod_tests.main(["a", "b"]), 1)


if __name__ == "__main__":
    unittest.main()
