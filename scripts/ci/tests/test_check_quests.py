import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_quests  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _write_quests_js(root, body):
    """body is the raw JS text that should follow `const QUEST_CHAPTERS = `
    (a JSON list literal) - mirrors gen_quests.py's own output shape
    (assignment, then arbitrary runtime code after it, which this checker
    must never need to parse)."""
    path = Path(root) / "pack" / "kubejs" / "server_scripts" / "quests.js"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "// GENERATED - test fixture\n"
        f"const QUEST_CHAPTERS = {body}\n"
        "\n"
        "// pretend runtime code follows, exactly like the real generated file\n"
        "ServerEvents.tick(event => {})\n",
        encoding="utf-8",
    )
    return path


class TestCheckQuests(unittest.TestCase):
    def test_valid_tree_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(
                tmp,
                '[{"id": "c1", "title": "Chapter One", "quests": ['
                '{"id": "c1__q1", "title": "Q1", "tasks": [{"type": "checkmark"}], '
                '"rewards": [{"type": "item", "item": "minecraft:stone", "count": 1}], "dependencies": []},'
                '{"id": "c1__q2", "title": "Q2", "tasks": [{"type": "checkmark"}], '
                '"rewards": [], "dependencies": ["c1__q1"]}'
                ']}]',
            )
            errors, stats = check_quests.check_quests(Path(tmp))
            self.assertEqual(errors, [])
            self.assertEqual(stats["chapters"], 1)
            self.assertEqual(stats["quests"], 2)
            self.assertEqual(stats["dependencies"], 1)
            self.assertEqual(check_quests.main([tmp]), 0)

    def test_duplicate_quest_id_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(
                tmp,
                '[{"id": "c1", "quests": [{"id": "dup", "tasks": [{"type": "checkmark"}], "rewards": [], "dependencies": []}]},'
                '{"id": "c2", "quests": [{"id": "dup", "tasks": [{"type": "checkmark"}], "rewards": [], "dependencies": []}]}]',
            )
            errors, stats = check_quests.check_quests(Path(tmp))
            self.assertTrue(any("duplicate id 'dup'" in e for e in errors))
            self.assertEqual(check_quests.main([tmp]), 1)

    def test_duplicate_chapter_id_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(
                tmp,
                '[{"id": "same", "quests": []}, {"id": "same", "quests": []}]',
            )
            errors, stats = check_quests.check_quests(Path(tmp))
            self.assertTrue(any("duplicate id 'same'" in e for e in errors))

    def test_dangling_dependency_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(
                tmp,
                '[{"id": "c1", "quests": [{"id": "q1", "dependencies": ["does_not_exist"], '
                '"tasks": [{"type": "checkmark"}], "rewards": []}]}]',
            )
            errors, stats = check_quests.check_quests(Path(tmp))
            self.assertTrue(
                any("does_not_exist" in e and "not the id of any quest" in e for e in errors)
            )
            self.assertEqual(check_quests.main([tmp]), 1)

    def test_item_ids_are_not_confused_with_quest_ids(self):
        # Two different quests both grant/require the SAME item id
        # (e.g. minecraft:stone) - this must not be treated as a duplicate
        # quest id, since item ids live in a different namespace entirely
        # (and, unlike the old SNBT format, tasks/rewards don't carry their
        # own "id" field at all anymore - only "item": "<item id>").
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(
                tmp,
                '[{"id": "c1", "quests": ['
                '{"id": "q1", "tasks": [{"type": "item", "item": "minecraft:stone", "count": 1}], "rewards": [], "dependencies": []},'
                '{"id": "q2", "tasks": [{"type": "item", "item": "minecraft:stone", "count": 1}], "rewards": [], "dependencies": []}'
                ']}]',
            )
            errors, stats = check_quests.check_quests(Path(tmp))
            self.assertEqual(errors, [])

    def test_unknown_task_type_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(
                tmp,
                '[{"id": "c1", "quests": [{"id": "q1", "tasks": [{"type": "not_a_real_type"}], "rewards": [], "dependencies": []}]}]',
            )
            errors, stats = check_quests.check_quests(Path(tmp))
            self.assertTrue(any("unknown type" in e for e in errors))

    def test_unknown_reward_type_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(
                tmp,
                '[{"id": "c1", "quests": [{"id": "q1", "tasks": [{"type": "checkmark"}], '
                '"rewards": [{"type": "not_a_real_type"}], "dependencies": []}]}]',
            )
            errors, stats = check_quests.check_quests(Path(tmp))
            self.assertTrue(any("unknown type" in e for e in errors))

    def test_currency_reward_type_is_rejected(self):
        # Deliberately excluded reward type - see gen_quests.py's own
        # spur_rewards() docstring for why Numismatics currency is always
        # granted as literal coin items instead.
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(
                tmp,
                '[{"id": "c1", "quests": [{"id": "q1", "tasks": [{"type": "checkmark"}], '
                '"rewards": [{"type": "currency", "amount": 10}], "dependencies": []}]}]',
            )
            errors, stats = check_quests.check_quests(Path(tmp))
            self.assertTrue(any("currency" in e for e in errors))

    def test_zero_tasks_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(
                tmp,
                '[{"id": "c1", "quests": [{"id": "q1", "tasks": [], "rewards": [], "dependencies": []}]}]',
            )
            errors, stats = check_quests.check_quests(Path(tmp))
            self.assertTrue(any("zero tasks" in e for e in errors))

    def test_missing_quests_script_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors, stats = check_quests.check_quests(Path(tmp))
            self.assertTrue(errors)
            self.assertEqual(check_quests.main([tmp]), 1)

    def test_missing_assignment_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pack" / "kubejs" / "server_scripts" / "quests.js"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("// no QUEST_CHAPTERS assignment in this file\n", encoding="utf-8")
            errors, stats = check_quests.check_quests(Path(tmp))
            self.assertTrue(any("could not find" in e for e in errors))

    def test_real_repo_quest_tree_passes(self):
        quests_js = REPO_ROOT / "pack" / "kubejs" / "server_scripts" / "quests.js"
        if not quests_js.is_file():
            self.skipTest(f"not running inside the repo (no quests.js found at {quests_js})")
        self.assertEqual(check_quests.main([str(REPO_ROOT)]), 0)

    def test_real_repo_quest_tree_has_expected_counts(self):
        # GitHub #33's own acceptance bar: content parity with the removed
        # FTB Quests book (10 chapters / 62 quests / 87 dependency edges -
        # see scripts/gen_quests.py's module docstring and DESIGN.md's
        # "Quest-book overhaul" section for where these numbers come from).
        quests_js = REPO_ROOT / "pack" / "kubejs" / "server_scripts" / "quests.js"
        if not quests_js.is_file():
            self.skipTest(f"not running inside the repo (no quests.js found at {quests_js})")
        errors, stats = check_quests.check_quests(REPO_ROOT)
        self.assertEqual(errors, [])
        self.assertEqual(stats["chapters"], 10)
        self.assertEqual(stats["quests"], 62)
        self.assertEqual(stats["dependencies"], 87)


if __name__ == "__main__":
    unittest.main()
