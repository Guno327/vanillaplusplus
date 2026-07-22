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


def _write_advancement(root, quest_id, parent=None, background=False, trigger=None):
    """trigger defaults to the *correct* trigger for the role (minecraft:tick
    for a root - no parent - and minecraft:impossible for a non-root), so
    callers only need to override it to construct a broken fixture."""
    if trigger is None:
        trigger = "minecraft:tick" if parent is None else "minecraft:impossible"
    adv_dir = Path(root) / "pack" / "kubejs" / "data" / "vanillaplusplus" / "advancement" / "quests"
    adv_dir.mkdir(parents=True, exist_ok=True)
    criterion_key = "auto" if trigger == "minecraft:tick" else "impossible"
    data = {
        "criteria": {criterion_key: {"trigger": trigger}},
        "requirements": [[criterion_key]],
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

    def test_non_root_wrong_criterion_trigger_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(tmp, [("q1", []), ("q2", ["q1"])])
            _write_advancement(tmp, "q1", parent=None, background=True)
            _write_advancement(tmp, "q2", parent="q1", background=False, trigger="minecraft:tick")
            errors, _ = check_advancements.check_advancements(Path(tmp))
            self.assertTrue(any("minecraft:impossible" in e for e in errors))

    def test_impossible_root_is_rejected_this_is_the_66_regression(self):
        """GitHub #66: this is *exactly* the pre-fix data shape - a root
        gated on minecraft:impossible, exactly like every other quest. Per
        the decompiled AdvancementVisibilityEvaluator/PlayerAdvancements
        evidence in this module's docstring, a root that's never granted is
        never visible, so the entire quest tab silently never appeared. The
        validator must reject this shape so the regression can't come back
        silently."""
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(tmp, [("q1", []), ("q2", ["q1"])])
            _write_advancement(tmp, "q1", parent=None, background=True, trigger="minecraft:impossible")
            _write_advancement(tmp, "q2", parent="q1", background=False)
            errors, _ = check_advancements.check_advancements(Path(tmp))
            self.assertTrue(
                any("minecraft:tick" in e for e in errors),
                f"expected a minecraft:tick-related error, got: {errors}",
            )
            self.assertEqual(check_advancements.main([tmp]), 1)

    def test_root_with_extra_criterion_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(tmp, [("q1", [])])
            adv_dir = Path(tmp) / "pack" / "kubejs" / "data" / "vanillaplusplus" / "advancement" / "quests"
            adv_dir.mkdir(parents=True, exist_ok=True)
            data = {
                "criteria": {
                    "auto": {"trigger": "minecraft:tick"},
                    "impossible": {"trigger": "minecraft:impossible"},
                },
                "requirements": [["auto"], ["impossible"]],
                "display": {
                    "icon": {"id": "minecraft:stone", "count": 1},
                    "title": "q1",
                    "description": "d",
                    "frame": "task",
                    "background": "minecraft:textures/gui/advancements/backgrounds/stone.png",
                },
            }
            (adv_dir / "q1.json").write_text(json.dumps(data))
            errors, _ = check_advancements.check_advancements(Path(tmp))
            self.assertTrue(any("exactly one" in e for e in errors))

    def test_cycle_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            # q1 is the one real root. q2 and q3 form a two-node cycle that
            # never reaches it - a data-integrity bug distinct from the
            # "no root at all" case (there IS exactly one root here).
            _write_quests_js(tmp, [("q1", []), ("q2", ["q3"]), ("q3", ["q2"])])
            _write_advancement(tmp, "q1", parent=None, background=True)
            _write_advancement(tmp, "q2", parent="q3", background=False)
            _write_advancement(tmp, "q3", parent="q2", background=False)
            errors, stats = check_advancements.check_advancements(Path(tmp))
            self.assertEqual(stats["roots"], 1)
            self.assertTrue(any("cycle" in e for e in errors))

    def test_depth_beyond_visibility_depth_is_detected(self):
        """GitHub #66: even with a self-granting root, AdvancementVisibilityEvaluator
        only looks 2 ancestor generations past a SHOW node - a quest chained
        3+ levels below the root (root -> q1 -> q2 -> q3) is invisible to a
        player who hasn't completed anything yet, the same symptom as #66
        just pushed a couple of tiers deeper. The validator must catch it."""
        with tempfile.TemporaryDirectory() as tmp:
            _write_quests_js(tmp, [("q1", []), ("q2", ["q1"]), ("q3", ["q2"]), ("q4", ["q3"])])
            _write_advancement(tmp, "q1", parent=None, background=True)
            _write_advancement(tmp, "q2", parent="q1", background=False)
            _write_advancement(tmp, "q3", parent="q2", background=False)
            _write_advancement(tmp, "q4", parent="q3", background=False)
            errors, _ = check_advancements.check_advancements(Path(tmp))
            self.assertTrue(
                any("q4" in e and "VISIBILITY_DEPTH" in e for e in errors),
                f"expected a VISIBILITY_DEPTH error for q4, got: {errors}",
            )
            # q2 (depth 1) and q3 (depth 2) are still within the window.
            self.assertFalse(any("q2.json" in e and "VISIBILITY_DEPTH" in e for e in errors))
            self.assertFalse(any("q3.json" in e and "VISIBILITY_DEPTH" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
