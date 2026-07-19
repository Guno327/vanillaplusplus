import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_quests  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _make_quests_tree(root):
    quests = Path(root) / "pack" / "config" / "ftbquests" / "quests"
    (quests / "chapters").mkdir(parents=True)
    _write(quests / "chapter_groups.snbt", '{"chapter_groups": []}')
    return quests


class TestCheckQuests(unittest.TestCase):
    def test_valid_tree_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            quests = _make_quests_tree(tmp)
            _write(
                quests / "chapters" / "chapter_one.snbt",
                '{"id": "0001", "filename": "chapter_one", "quests": ['
                '{"id": "0002", "tasks": [{"id": "0003", "type": "checkmark"}], '
                '"rewards": [{"id": "0004", "type": "item", "item": {"id": "minecraft:stone", "count": 1}}]},'
                '{"id": "0005", "dependencies": ["0002"], "tasks": [{"id": "0006", "type": "checkmark"}]}'
                '], "quest_links": []}',
            )
            errors, stats = check_quests.check_quests(Path(tmp))
            self.assertEqual(errors, [])
            self.assertEqual(stats["chapters"], 1)
            self.assertEqual(stats["quests"], 2)
            self.assertEqual(stats["dependencies"], 1)
            self.assertEqual(check_quests.main([tmp]), 0)

    def test_duplicate_quest_id_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            quests = _make_quests_tree(tmp)
            _write(
                quests / "chapters" / "a.snbt",
                '{"id": "c1", "quests": [{"id": "dup", "tasks": [], "rewards": []}]}',
            )
            _write(
                quests / "chapters" / "b.snbt",
                '{"id": "c2", "quests": [{"id": "dup", "tasks": [], "rewards": []}]}',
            )
            errors, stats = check_quests.check_quests(Path(tmp))
            self.assertTrue(any("duplicate id 'dup'" in e for e in errors))
            self.assertEqual(check_quests.main([tmp]), 1)

    def test_duplicate_chapter_id_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            quests = _make_quests_tree(tmp)
            _write(quests / "chapters" / "a.snbt", '{"id": "same", "quests": []}')
            _write(quests / "chapters" / "b.snbt", '{"id": "same", "quests": []}')
            errors, stats = check_quests.check_quests(Path(tmp))
            self.assertTrue(any("duplicate id 'same'" in e for e in errors))

    def test_dangling_dependency_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            quests = _make_quests_tree(tmp)
            _write(
                quests / "chapters" / "a.snbt",
                '{"id": "c1", "quests": [{"id": "q1", "dependencies": ["does_not_exist"], '
                '"tasks": [], "rewards": []}]}',
            )
            errors, stats = check_quests.check_quests(Path(tmp))
            self.assertTrue(
                any("does_not_exist" in e and "not the id of any quest" in e for e in errors)
            )
            self.assertEqual(check_quests.main([tmp]), 1)

    def test_item_ids_are_not_confused_with_quest_ids(self):
        # Two different quests both grant/require the SAME item id
        # (e.g. minecraft:stone) - this must not be treated as a duplicate
        # quest/task/reward id, since item ids live in a different
        # namespace entirely.
        with tempfile.TemporaryDirectory() as tmp:
            quests = _make_quests_tree(tmp)
            _write(
                quests / "chapters" / "a.snbt",
                '{"id": "c1", "quests": ['
                '{"id": "q1", "icon": {"id": "minecraft:stone", "count": 1}, "tasks": '
                '[{"id": "t1", "type": "item", "item": {"id": "minecraft:stone", "count": 1}}], "rewards": []},'
                '{"id": "q2", "icon": {"id": "minecraft:stone", "count": 1}, "tasks": '
                '[{"id": "t2", "type": "item", "item": {"id": "minecraft:stone", "count": 1}}], "rewards": []}'
                ']}',
            )
            errors, stats = check_quests.check_quests(Path(tmp))
            self.assertEqual(errors, [])

    def test_chapter_groups_referencing_missing_chapter_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            quests = _make_quests_tree(tmp)
            _write(quests / "chapters" / "a.snbt", '{"id": "c1", "filename": "a", "quests": []}')
            _write(
                quests / "chapter_groups.snbt",
                '{"chapter_groups": [{"id": "g1", "chapters": ["c1", "ghost_chapter"]}]}',
            )
            errors, stats = check_quests.check_quests(Path(tmp))
            self.assertTrue(any("ghost_chapter" in e for e in errors))

    def test_missing_quests_dir_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors, stats = check_quests.check_quests(Path(tmp))
            self.assertTrue(errors)
            self.assertEqual(check_quests.main([tmp]), 1)

    def test_real_repo_quest_tree_passes(self):
        quests_dir = REPO_ROOT / "pack" / "config" / "ftbquests" / "quests"
        if not quests_dir.is_dir():
            self.skipTest(f"not running inside the repo (no quests dir found at {quests_dir})")
        self.assertEqual(check_quests.main([str(REPO_ROOT)]), 0)


if __name__ == "__main__":
    unittest.main()
