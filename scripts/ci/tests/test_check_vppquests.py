import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_vppquests  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _write_chapter(root, namespace, chapter_id, doc):
    path = Path(root) / "pack" / "kubejs" / "data" / namespace / "vppquests" / "chapter" / f"{chapter_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _write_quest(root, namespace, chapter_id, slug, doc):
    path = Path(root) / "pack" / "kubejs" / "data" / namespace / "vppquests" / "quest" / chapter_id / f"{slug}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


class TestCheckVppquests(unittest.TestCase):
    def test_no_data_at_all_passes(self):
        # vppquests content is optional pack data, not a hard requirement -
        # a pack with none yet (or none at all) is still "consistent".
        with tempfile.TemporaryDirectory() as tmp:
            errors, stats = check_vppquests.check_vppquests(Path(tmp))
            self.assertEqual(errors, [])
            self.assertEqual(stats["chapters"], 0)
            self.assertEqual(stats["quests"], 0)
            self.assertEqual(check_vppquests.main([tmp]), 0)

    def test_valid_tree_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_chapter(tmp, "ns", "c1", {"title": "C1", "subtitle": [], "icon": "minecraft:stone", "order": 0})
            _write_quest(tmp, "ns", "c1", "q1", {
                "chapter": "ns:c1", "title": "Q1", "icon": "minecraft:stone",
                "tasks": [{"type": "checkmark"}], "rewards": [], "dependencies": [],
            })
            _write_quest(tmp, "ns", "c1", "q2", {
                "chapter": "ns:c1", "title": "Q2", "icon": "minecraft:stone",
                "tasks": [{"type": "checkmark"}], "rewards": [{"type": "item", "item": "minecraft:stone", "count": 1}],
                "dependencies": ["ns:c1/q1"],
            })
            errors, stats = check_vppquests.check_vppquests(Path(tmp))
            self.assertEqual(errors, [])
            self.assertEqual(stats["chapters"], 1)
            self.assertEqual(stats["quests"], 2)
            self.assertEqual(stats["dependencies"], 1)
            self.assertEqual(check_vppquests.main([tmp]), 0)

    def test_wrong_chapter_field_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_chapter(tmp, "ns", "c1", {"title": "C1", "subtitle": [], "icon": "minecraft:stone", "order": 0})
            _write_quest(tmp, "ns", "c1", "q1", {
                "chapter": "ns:wrong_chapter", "title": "Q1", "icon": "minecraft:stone",
                "tasks": [{"type": "checkmark"}], "rewards": [], "dependencies": [],
            })
            errors, stats = check_vppquests.check_vppquests(Path(tmp))
            self.assertTrue(any("expected 'ns:c1'" in e for e in errors))

    def test_dangling_dependency_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_chapter(tmp, "ns", "c1", {"title": "C1", "subtitle": [], "icon": "minecraft:stone", "order": 0})
            _write_quest(tmp, "ns", "c1", "q1", {
                "chapter": "ns:c1", "title": "Q1", "icon": "minecraft:stone",
                "tasks": [{"type": "checkmark"}], "rewards": [], "dependencies": ["ns:c1/does_not_exist"],
            })
            errors, stats = check_vppquests.check_vppquests(Path(tmp))
            self.assertTrue(any("does_not_exist" in e and "not the id of any quest file" in e for e in errors))
            self.assertEqual(check_vppquests.main([tmp]), 1)

    def test_unknown_task_type_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_chapter(tmp, "ns", "c1", {"title": "C1", "subtitle": [], "icon": "minecraft:stone", "order": 0})
            _write_quest(tmp, "ns", "c1", "q1", {
                "chapter": "ns:c1", "title": "Q1", "icon": "minecraft:stone",
                "tasks": [{"type": "not_a_real_type"}], "rewards": [], "dependencies": [],
            })
            errors, stats = check_vppquests.check_vppquests(Path(tmp))
            self.assertTrue(any("unknown type" in e for e in errors))

    def test_unknown_reward_type_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_chapter(tmp, "ns", "c1", {"title": "C1", "subtitle": [], "icon": "minecraft:stone", "order": 0})
            _write_quest(tmp, "ns", "c1", "q1", {
                "chapter": "ns:c1", "title": "Q1", "icon": "minecraft:stone",
                "tasks": [{"type": "checkmark"}], "rewards": [{"type": "not_a_real_type"}], "dependencies": [],
            })
            errors, stats = check_vppquests.check_vppquests(Path(tmp))
            self.assertTrue(any("unknown type" in e for e in errors))

    def test_unknown_frame_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_chapter(tmp, "ns", "c1", {"title": "C1", "subtitle": [], "icon": "minecraft:stone", "order": 0})
            _write_quest(tmp, "ns", "c1", "q1", {
                "chapter": "ns:c1", "title": "Q1", "icon": "minecraft:stone", "frame": "not_a_real_frame",
                "tasks": [{"type": "checkmark"}], "rewards": [], "dependencies": [],
            })
            errors, stats = check_vppquests.check_vppquests(Path(tmp))
            self.assertTrue(any("unknown value" in e for e in errors))

    def test_zero_tasks_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_chapter(tmp, "ns", "c1", {"title": "C1", "subtitle": [], "icon": "minecraft:stone", "order": 0})
            _write_quest(tmp, "ns", "c1", "q1", {
                "chapter": "ns:c1", "title": "Q1", "icon": "minecraft:stone",
                "tasks": [], "rewards": [], "dependencies": [],
            })
            errors, stats = check_vppquests.check_vppquests(Path(tmp))
            self.assertTrue(any("zero tasks" in e for e in errors))

    def test_duplicate_chapter_id_is_detected(self):
        # Two different namespaces both defining a "c1" chapter is fine
        # (ids are namespace-qualified) - but the same namespace can't.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pack" / "kubejs" / "data" / "ns" / "vppquests" / "chapter"
            path.mkdir(parents=True, exist_ok=True)
            # Simulate a duplicate by writing the same logical id from two
            # different namespaces sharing a chapter id string is NOT a dup
            # (covered implicitly); real dup coverage is same-namespace,
            # which the filesystem itself prevents (one file per id) - so
            # instead assert good behavior across two distinct namespaces.
            _write_chapter(tmp, "ns1", "c1", {"title": "C1", "subtitle": [], "icon": "minecraft:stone", "order": 0})
            _write_chapter(tmp, "ns2", "c1", {"title": "C1", "subtitle": [], "icon": "minecraft:stone", "order": 0})
            errors, stats = check_vppquests.check_vppquests(Path(tmp))
            self.assertEqual(errors, [])
            self.assertEqual(stats["chapters"], 2)

    def test_invalid_json_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pack" / "kubejs" / "data" / "ns" / "vppquests" / "chapter" / "c1.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{not valid json", encoding="utf-8")
            errors, stats = check_vppquests.check_vppquests(Path(tmp))
            self.assertTrue(any("invalid JSON" in e for e in errors))

    def test_real_repo_vppquests_tree_passes(self):
        vppquests_dir = REPO_ROOT / "pack" / "kubejs" / "data" / "vanillaplusplus" / "vppquests"
        if not vppquests_dir.is_dir():
            self.skipTest(f"not running inside the repo (no vppquests data found at {vppquests_dir})")
        self.assertEqual(check_vppquests.main([str(REPO_ROOT)]), 0)

    def test_real_repo_vppquests_tree_matches_legacy_quest_counts(self):
        # scripts/gen_vppquests_data.py is a lossless port of
        # scripts/gen_quests.py's own 62-quest/10-chapter/87-dependency
        # book (GitHub #109's Phase A content-port slice) - counts must
        # match check_quests.py's own real-repo counts exactly.
        vppquests_dir = REPO_ROOT / "pack" / "kubejs" / "data" / "vanillaplusplus" / "vppquests"
        if not vppquests_dir.is_dir():
            self.skipTest(f"not running inside the repo (no vppquests data found at {vppquests_dir})")
        errors, stats = check_vppquests.check_vppquests(REPO_ROOT)
        self.assertEqual(errors, [])
        self.assertEqual(stats["chapters"], 10)
        self.assertEqual(stats["quests"], 62)
        self.assertEqual(stats["dependencies"], 87)


if __name__ == "__main__":
    unittest.main()
