import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_forging_recipes  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FORGING_DIR_REL = check_forging_recipes.FORGING_DIR_REL


def _write_recipe(root, name, doc):
    path = Path(root) / FORGING_DIR_REL / f"{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _full_metal_ladder_docs():
    """One valid recipe per (metal x part type), matching a real
    KNOWN_KEY_ITEM_TO_MATERIAL/PART_TYPE_RESULT_IDS pairing - enough to
    satisfy the full coverage matrix on its own."""
    docs = {}
    for key_item, metal in check_forging_recipes.KNOWN_KEY_ITEM_TO_MATERIAL.items():
        for part_type, result_id in check_forging_recipes.PART_TYPE_RESULT_IDS.items():
            docs[f"{metal}_{part_type}"] = {
                "type": "overgeared:forging",
                "category": "TOOL_HEADS",
                "hammering": 3,
                "key": {"#": {"item": key_item}},
                "pattern": ["#"],
                "result": {"count": 1, "id": result_id},
                "show_notification": False,
                "tier": "stone",
            }
    return docs


class TestCheckForgingRecipes(unittest.TestCase):
    def test_no_data_at_all_reports_every_metal_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors, stats = check_forging_recipes.check_forging_recipes(Path(tmp))
            self.assertEqual(stats["recipes"], 0)
            # Every targeted metal is missing every part type with nothing on disk.
            self.assertEqual(len(errors), len(check_forging_recipes.TARGETED_METALS))
            self.assertEqual(check_forging_recipes.main([tmp]), 1)

    def test_full_metal_ladder_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, doc in _full_metal_ladder_docs().items():
                _write_recipe(tmp, name, doc)
            errors, stats = check_forging_recipes.check_forging_recipes(Path(tmp))
            self.assertEqual(errors, [])
            self.assertEqual(
                stats["recipes"],
                len(check_forging_recipes.KNOWN_KEY_ITEM_TO_MATERIAL) * len(check_forging_recipes.PART_TYPE_RESULT_IDS),
            )
            self.assertEqual(check_forging_recipes.main([tmp]), 0)

    def test_missing_one_part_type_for_one_metal_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs = _full_metal_ladder_docs()
            del docs["star_alloy_hammer_head"]
            for name, doc in docs.items():
                _write_recipe(tmp, name, doc)
            errors, stats = check_forging_recipes.check_forging_recipes(Path(tmp))
            self.assertTrue(any("'star_alloy'" in e and "hammer_head" in e for e in errors))

    def test_unknown_result_id_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_recipe(tmp, "bogus", {
                "type": "overgeared:forging",
                "category": "TOOL_HEADS",
                "hammering": 3,
                "key": {"#": {"item": "overgeared:heated_iron_ingot"}},
                "pattern": ["#"],
                "result": {"count": 1, "id": "silentgear:not_a_real_part"},
                "show_notification": False,
                "tier": "stone",
            })
            errors, stats = check_forging_recipes.check_forging_recipes(Path(tmp))
            self.assertTrue(any("not a known Silent Gear tool-head part id" in e for e in errors))

    def test_unknown_key_item_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_recipe(tmp, "bogus", {
                "type": "overgeared:forging",
                "category": "TOOL_HEADS",
                "hammering": 3,
                "key": {"#": {"item": "vppintegration:heated_unregistered_thing"}},
                "pattern": ["#"],
                "result": {"count": 1, "id": "silentgear:axe_head"},
                "show_notification": False,
                "tier": "stone",
            })
            errors, stats = check_forging_recipes.check_forging_recipes(Path(tmp))
            self.assertTrue(any("not a known heated-metal item" in e for e in errors))

    def test_unknown_tier_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_recipe(tmp, "bogus", {
                "type": "overgeared:forging",
                "category": "TOOL_HEADS",
                "hammering": 3,
                "key": {"#": {"item": "overgeared:heated_iron_ingot"}},
                "pattern": ["#"],
                "result": {"count": 1, "id": "silentgear:axe_head"},
                "show_notification": False,
                "tier": "diamond",
            })
            errors, stats = check_forging_recipes.check_forging_recipes(Path(tmp))
            self.assertTrue(any("expected one of" in e and "tier" in e for e in errors))

    def test_invalid_json_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / FORGING_DIR_REL / "broken.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{not json", encoding="utf-8")
            errors, stats = check_forging_recipes.check_forging_recipes(Path(tmp))
            self.assertTrue(any("invalid JSON" in e for e in errors))

    def test_real_repo_passes(self):
        # The actual pack content this check ships alongside should always
        # be internally consistent - same "real repo" smoke test pattern as
        # other scripts/ci/tests/test_check_*.py files.
        errors, stats = check_forging_recipes.check_forging_recipes(REPO_ROOT)
        self.assertEqual(errors, [])
        self.assertGreater(stats["recipes"], 0)
        self.assertEqual(check_forging_recipes.main([str(REPO_ROOT)]), 0)


if __name__ == "__main__":
    unittest.main()
