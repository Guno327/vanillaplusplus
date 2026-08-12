import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import discover_mod_gradle_projects  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = Path(__file__).resolve().parent.parent / "discover_mod_gradle_projects.py"


class TestDiscoverLogic(unittest.TestCase):
    def test_real_repo_finds_the_four_mods(self):
        mods = discover_mod_gradle_projects.discover(REPO_ROOT)
        self.assertEqual(mods, ["vppfixes", "vppintegration", "vppquests", "vppskills"])

    def test_synthetic_tmpdir_only_dirs_with_gradlew_are_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mods_src = root / "mods-src"
            mods_src.mkdir()

            has_gradle = mods_src / "hasgradle"
            has_gradle.mkdir()
            (has_gradle / "gradlew").write_text("#!/bin/sh\n")

            no_gradle = mods_src / "nogradle"
            no_gradle.mkdir()
            (no_gradle / "build.gradle").write_text("")

            mods = discover_mod_gradle_projects.discover(root)
            self.assertEqual(mods, ["hasgradle"])

    def test_missing_mods_src_yields_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            mods = discover_mod_gradle_projects.discover(Path(tmp))
            self.assertEqual(mods, [])

    def test_non_directory_entries_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mods_src = root / "mods-src"
            mods_src.mkdir()
            (mods_src / "stray-file.txt").write_text("not a dir")
            mods = discover_mod_gradle_projects.discover(root)
            self.assertEqual(mods, [])

    def test_pycache_and_dotfile_junk_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mods_src = root / "mods-src"
            mods_src.mkdir()

            pycache = mods_src / "__pycache__"
            pycache.mkdir()
            (pycache / "gradlew").write_text("junk")

            dotdir = mods_src / ".hidden"
            dotdir.mkdir()
            (dotdir / "gradlew").write_text("junk")

            real = mods_src / "realmod"
            real.mkdir()
            (real / "gradlew").write_text("#!/bin/sh\n")

            mods = discover_mod_gradle_projects.discover(root)
            self.assertEqual(mods, ["realmod"])

    def test_result_is_sorted_and_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mods_src = root / "mods-src"
            mods_src.mkdir()
            for name in ["zeta", "alpha", "mike"]:
                d = mods_src / name
                d.mkdir()
                (d / "gradlew").write_text("#!/bin/sh\n")

            mods = discover_mod_gradle_projects.discover(root)
            self.assertEqual(mods, ["alpha", "mike", "zeta"])


class TestDiscoverCli(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )

    def test_cli_plain_output(self):
        result = self._run()
        self.assertEqual(result.returncode, 0)
        lines = [l for l in result.stdout.splitlines() if l.strip()]
        self.assertEqual(lines, ["vppfixes", "vppintegration", "vppquests", "vppskills"])

    def test_cli_json_output_matches_plain(self):
        plain = self._run()
        as_json = self._run("--json")
        self.assertEqual(as_json.returncode, 0)
        parsed = json.loads(as_json.stdout)
        plain_lines = [l for l in plain.stdout.splitlines() if l.strip()]
        self.assertEqual(parsed, plain_lines)

    def test_cli_with_explicit_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mods_src = root / "mods-src"
            mods_src.mkdir()
            d = mods_src / "onlymod"
            d.mkdir()
            (d / "gradlew").write_text("#!/bin/sh\n")

            result = self._run(str(root))
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "onlymod")


if __name__ == "__main__":
    unittest.main()
