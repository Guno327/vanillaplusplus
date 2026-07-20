import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import run_all  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _minimal_valid_pack(root):
    """A from-scratch pack/ tree that should pass every one of the five
    checks, used to test run_all's own aggregation/exit-code logic without
    depending on the real repo tree."""
    pack = Path(root) / "pack"
    (pack / "config").mkdir(parents=True)
    (pack / "kubejs" / "server_scripts").mkdir(parents=True)

    manifest = {"minecraft": "1.21.1", "loader": "neoforge",
                "mods": [{"slug": "create", "side": "both", "phase": 0}]}
    lock = {"minecraft": "1.21.1", "loader": "neoforge",
            "mods": [{"slug": "create", "side": "both", "phase": 0,
                      "filename": "create.jar", "url": "https://cdn.example/create.jar",
                      "hashes": {"sha512": "a" * 128}}]}
    (pack / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (pack / "mods.lock.json").write_text(json.dumps(lock), encoding="utf-8")

    (pack / "config" / "sample.json").write_text('{"a": 1}', encoding="utf-8")
    # GitHub #33: the quest book lives in pack/kubejs/server_scripts/quests.js
    # now (a `const QUEST_CHAPTERS = [...]` JSON literal), not FTB Quests SNBT.
    (pack / "kubejs" / "server_scripts" / "quests.js").write_text(
        'const QUEST_CHAPTERS = [{"id": "c1", "quests": '
        '[{"id": "q1", "tasks": [{"type": "checkmark"}], "rewards": [], "dependencies": []}]}]\n',
        encoding="utf-8")
    (pack / "kubejs" / "server_scripts" / "clean.js").write_text(
        "try {\n    let x = 1\n} catch (e) {}\n", encoding="utf-8")
    return pack


class TestRunAll(unittest.TestCase):
    def test_all_checks_pass_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            _minimal_valid_pack(tmp)
            self.assertEqual(run_all.main([tmp]), 0)

    def test_one_failing_check_causes_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = _minimal_valid_pack(tmp)
            (pack / "config" / "broken.json").write_text("not json", encoding="utf-8")
            self.assertEqual(run_all.main([tmp]), 1)

    def test_real_repo_tree_passes(self):
        pack_dir = REPO_ROOT / "pack"
        if not pack_dir.is_dir():
            self.skipTest(f"not running inside the repo (no pack/ found at {pack_dir})")
        self.assertEqual(run_all.main([str(REPO_ROOT)]), 0)


if __name__ == "__main__":
    unittest.main()
