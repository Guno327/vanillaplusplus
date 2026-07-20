import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_advancements  # noqa: E402


def _write_quests_js(root, quest_ids_and_deps):
    """quest_ids_and_deps: list of (id, [dependency_ids]) tuples, all in one
    synthetic chapter - mirrors gen_quests.py's real output shape closely
    enough for check_advancements._load_quest_ids() to parse."""
    quests = [
        {"id": qid, "title": qid, "tasks": [{"type": "checkmark"}], "rewards": [], "dependencies": deps}
        for qid, deps in quest_ids_and_deps
    ]
    chapters = [{"id": "c1", "title": "Chapter One", "quests": quests}]
    path = Path(root) / "pack" / "kubejs" / "server_scripts" / "quests.js"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "// GENERATED - test fixture\n"
        f"const QUEST_CHAPTERS = {json.dumps(chapters)}\n"
        "\nServerEvents.tick(event => {})\n",
        encoding="utf-8",
    )


def _write_advancement(root, quest_id, parent=None, background=False, impossible=True):
    adv_dir = Path(root) / "pack" / "kubejs" / "data" / "vanillaplusplus" / "advancement" / "quests"
    adv_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "criteria": {"impossible": {"trigger": "minecraft:impossible" if impossible else "minecraft:tick"}},
        "requirements": [["impossible"]],
        "display": {"icon": {"id": "minecraft:stone", "count": 1}, "title": quest_id, "description": "d", "frame": "task"},
    }
    if parent is not None:
        data["parent"] = "vanillaplusplus:quests/" + parent
    if background:
        data["display"]["background"] = "minecraft:textures/gui/advancements/backgrounds/stone.png"
    (adv_dir / f"{quest_id}.json").write_text(json.dumps(data))


class TestCheckAdvancements(unittest.TestCase):
    def test_valid_tree_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(tmp, [("q1", []), ("q2", ["q1"])])
            _write_advancement(tmp, "q1", parent=None, background=True)
            _write_advancement(tmp, "q2", parent="q1", background=False)
            errors, stats = check_advancements.check_advancements(Path(tmp))
            self.assertEqual(errors, [])
            self.assertEqual(stats["files"], 2)
            self.assertEqual(stats["roots"], 1)
            self.assertEqual(check_advancements.main([tmp]), 0)

    def test_missing_advancement_file_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(tmp, [("q1", []), ("q2", ["q1"])])
            _write_advancement(tmp, "q1", parent=None, background=True)
            errors, _ = check_advancements.check_advancements(Path(tmp))
            self.assertTrue(any("q2" in e and "no advancement file" in e for e in errors))

    def test_extra_advancement_file_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(tmp, [("q1", [])])
            _write_advancement(tmp, "q1", parent=None, background=True)
            _write_advancement(tmp, "ghost", parent=None, background=True)
            errors, _ = check_advancements.check_advancements(Path(tmp))
            self.assertTrue(any("ghost" in e and "don't correspond" in e for e in errors))

    def test_dangling_parent_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(tmp, [("q1", ["nope"])])
            _write_advancement(tmp, "q1", parent="nope", background=False)
            errors, _ = check_advancements.check_advancements(Path(tmp))
            self.assertTrue(any("does not resolve" in e for e in errors))

    def test_root_without_background_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(tmp, [("q1", [])])
            _write_advancement(tmp, "q1", parent=None, background=False)
            errors, _ = check_advancements.check_advancements(Path(tmp))
            self.assertTrue(any("missing display.background" in e for e in errors))

    def test_non_root_with_background_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(tmp, [("q1", []), ("q2", ["q1"])])
            _write_advancement(tmp, "q1", parent=None, background=True)
            _write_advancement(tmp, "q2", parent="q1", background=True)
            errors, _ = check_advancements.check_advancements(Path(tmp))
            self.assertTrue(any("should not set display.background" in e for e in errors))

    def test_multiple_roots_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(tmp, [("q1", []), ("q2", [])])
            _write_advancement(tmp, "q1", parent=None, background=True)
            _write_advancement(tmp, "q2", parent=None, background=True)
            errors, _ = check_advancements.check_advancements(Path(tmp))
            self.assertTrue(any("expected exactly 1 root" in e for e in errors))

    def test_wrong_criterion_trigger_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(tmp, [("q1", [])])
            _write_advancement(tmp, "q1", parent=None, background=True, impossible=False)
            errors, _ = check_advancements.check_advancements(Path(tmp))
            self.assertTrue(any("minecraft:impossible" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
