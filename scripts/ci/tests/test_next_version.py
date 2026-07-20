import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import next_version  # noqa: E402


class TestParseSemver(unittest.TestCase):
    def test_valid_tag_parses(self):
        self.assertEqual(next_version.parse_semver("v1.2.3"), (1, 2, 3))

    def test_v0_0_0_parses(self):
        self.assertEqual(next_version.parse_semver("v0.0.0"), (0, 0, 0))

    def test_missing_v_prefix_is_rejected(self):
        self.assertIsNone(next_version.parse_semver("1.2.3"))

    def test_two_component_version_is_rejected(self):
        self.assertIsNone(next_version.parse_semver("v1.2"))

    def test_prerelease_suffix_is_rejected(self):
        # This project doesn't tag pre-release suffixes (see module
        # docstring) - a tag like this should be ignored, not crash.
        self.assertIsNone(next_version.parse_semver("v1.2.3-beta"))

    def test_non_numeric_component_is_rejected(self):
        self.assertIsNone(next_version.parse_semver("vX.Y.Z"))

    def test_garbage_is_rejected(self):
        self.assertIsNone(next_version.parse_semver("not-a-tag"))

    def test_whitespace_is_stripped(self):
        self.assertEqual(next_version.parse_semver("  v2.0.1  \n"), (2, 0, 1))


class TestLatestReleaseVersion(unittest.TestCase):
    def test_picks_highest_semver_not_lexical_order(self):
        # Lexical sort would put v0.10.0 before v0.9.0 wrongly; this must
        # compare numerically.
        tags = ["v0.9.0", "v0.10.0", "v0.2.0"]
        self.assertEqual(next_version.latest_release_version(tags), (0, 10, 0))

    def test_matches_real_repo_tag_history(self):
        # Ground-truthed against this repo's actual `git tag -l` output.
        tags = ["v0.1.0", "v0.1.1", "v0.2.0"]
        self.assertEqual(next_version.latest_release_version(tags), (0, 2, 0))

    def test_ignores_unparseable_tags(self):
        tags = ["v0.1.0", "not-a-release-tag", "v1.0.0-rc1"]
        self.assertEqual(next_version.latest_release_version(tags), (0, 1, 0))

    def test_empty_tag_list_returns_none(self):
        self.assertIsNone(next_version.latest_release_version([]))

    def test_all_unparseable_returns_none(self):
        self.assertIsNone(next_version.latest_release_version(["latest", "nightly"]))


class TestBumpVersion(unittest.TestCase):
    def test_patch_bump(self):
        self.assertEqual(next_version.bump_version((0, 2, 0), "patch"), (0, 2, 1))

    def test_minor_bump_resets_patch(self):
        self.assertEqual(next_version.bump_version((0, 2, 5), "minor"), (0, 3, 0))

    def test_major_bump_resets_minor_and_patch(self):
        self.assertEqual(next_version.bump_version((0, 2, 5), "major"), (1, 0, 0))

    def test_invalid_bump_raises(self):
        with self.assertRaises(ValueError):
            next_version.bump_version((0, 2, 0), "banana")


class TestFormatVersion(unittest.TestCase):
    def test_format(self):
        self.assertEqual(next_version.format_version((1, 2, 3)), "1.2.3")


class TestComputeNextVersion(unittest.TestCase):
    def test_patch_bump_from_current_repo_state(self):
        # pack/VERSION and the latest tag are both 0.2.0 at time of
        # writing (see HANDOFF.md) - a patch mint from here should be
        # 0.2.1.
        tags = ["v0.1.0", "v0.1.1", "v0.2.0"]
        self.assertEqual(next_version.compute_next_version(tags, "patch"), "0.2.1")

    def test_minor_bump(self):
        tags = ["v0.1.0", "v0.1.1", "v0.2.0"]
        self.assertEqual(next_version.compute_next_version(tags, "minor"), "0.3.0")

    def test_major_bump(self):
        tags = ["v0.1.0", "v0.1.1", "v0.2.0"]
        self.assertEqual(next_version.compute_next_version(tags, "major"), "1.0.0")

    def test_no_tags_at_all_bumps_from_implicit_v0_0_0(self):
        self.assertEqual(next_version.compute_next_version([], "minor"), "0.1.0")
        self.assertEqual(next_version.compute_next_version([], "patch"), "0.0.1")
        self.assertEqual(next_version.compute_next_version([], "major"), "1.0.0")

    def test_invalid_bump_propagates(self):
        with self.assertRaises(ValueError):
            next_version.compute_next_version(["v0.2.0"], "banana")


class TestCli(unittest.TestCase):
    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = next_version.main(argv)
        return code, buf.getvalue().strip()

    def test_cli_with_explicit_tags(self):
        code, out = self._run(["--bump", "patch", "--tag", "v0.1.0", "--tag", "v0.2.0"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "0.2.1")

    def test_cli_single_tag(self):
        code, out = self._run(["--bump", "major", "--tag", "v2.5.9"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "3.0.0")

    def test_cli_invalid_bump_is_rejected_by_argparse(self):
        with self.assertRaises(SystemExit):
            self._run(["--bump", "banana", "--tag", "v0.2.0"])

    def test_cli_reads_real_repo_git_tags_when_none_given(self):
        # No --tag at all -> falls back to `git tag --list "v*"` in this
        # repo. Only meaningful when actually running inside a git
        # checkout with tags (this worktree is one - see module docstring
        # ground-truthing against v0.1.0/v0.1.1/v0.2.0).
        import subprocess
        result = subprocess.run(
            ["git", "tag", "--list", "v*"],
            cwd=str(next_version.ROOT),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not result.stdout.strip():
            self.skipTest("not running inside a git checkout with v* tags")
        code, out = self._run(["--bump", "patch"])
        self.assertEqual(code, 0)
        # Whatever it is, it must be a valid 3-component version string.
        self.assertRegex(out, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
