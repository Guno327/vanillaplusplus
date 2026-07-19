import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import validate_json  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class TestValidateJson(unittest.TestCase):
    def test_valid_json_and_mcmeta_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            (pack / "config").mkdir(parents=True)
            (pack / "config" / "good.json").write_text('{"a": 1}', encoding="utf-8")
            (pack / "config" / "pack.mcmeta").write_text('{"pack": {"pack_format": 1}}', encoding="utf-8")

            files = validate_json.find_files(pack)
            self.assertEqual(len(files), 2)
            for f in files:
                self.assertIsNone(validate_json.check_file(f))

            self.assertEqual(validate_json.main([tmp]), 0)

    def test_bad_json_is_detected_with_filename_and_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            pack.mkdir(parents=True)
            bad = pack / "broken.json"
            bad.write_text('{"a": 1,}', encoding="utf-8")  # trailing comma - invalid JSON

            err = validate_json.check_file(bad)
            self.assertIsNotNone(err)
            self.assertIn("line", err)

            self.assertEqual(validate_json.main([tmp]), 1)

    def test_bad_mcmeta_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            pack.mkdir(parents=True)
            (pack / "pack.mcmeta").write_text("not json at all", encoding="utf-8")
            self.assertEqual(validate_json.main([tmp]), 1)

    def test_non_json_files_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            pack.mkdir(parents=True)
            (pack / "readme.txt").write_text("not json, not checked", encoding="utf-8")
            self.assertEqual(validate_json.main([tmp]), 0)

    def test_missing_pack_dir_fails_clearly(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(validate_json.main([tmp]), 1)

    def test_real_repo_tree_passes(self):
        pack_dir = REPO_ROOT / "pack"
        if not pack_dir.is_dir():
            self.skipTest(f"not running inside the repo (no pack/ found at {pack_dir})")
        self.assertEqual(validate_json.main([str(REPO_ROOT)]), 0)


if __name__ == "__main__":
    unittest.main()
