import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_skill_trees  # noqa: E402


CATS_ROOT = ("pack", "kubejs", "data", "puffish_skills", "puffish_skills")


def _cat_dir(tmp, cat_id):
    return Path(tmp).joinpath(*CATS_ROOT, "categories", cat_id)


def _write_config(tmp, category_ids):
    root = Path(tmp).joinpath(*CATS_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    (root / "config.json").write_text(json.dumps({"version": 3, "categories": category_ids}))


def _write_valid_category(
    tmp,
    cat_id="test_cat",
    *,
    skills=None,
    definitions=None,
    connections=None,
    experience_expr="70 * (1.13 ^ level)",
    attribute="generic.luck",
    operation="addition",
):
    """A minimal-but-valid 3-node tree: root -> a -> b, all `normal`, one
    definition referenced by every node. Callers override just the piece
    they're testing."""
    cat_dir = _cat_dir(tmp, cat_id)
    cat_dir.mkdir(parents=True, exist_ok=True)

    (cat_dir / "category.json").write_text(json.dumps({
        "unlocked_by_default": True,
        "title": "Test",
        "icon": {"type": "item", "data": {"item": "stone"}},
        "background": "textures/gui/advancements/backgrounds/stone.png",
    }))

    if definitions is None:
        definitions = {
            "def_a": {
                "title": "+0.1 Luck",
                "icon": {"type": "item", "data": {"item": "rabbit_foot"}},
                "rewards": [{"type": "puffish_skills:attribute", "data": {"attribute": attribute, "value": 0.1, "operation": operation}}],
            }
        }
    (cat_dir / "definitions.json").write_text(json.dumps(definitions))

    if skills is None:
        skills = {
            "root": {"x": 0, "y": 0, "definition": "def_a", "root": True},
            "a": {"x": 32, "y": 0, "definition": "def_a"},
            "b": {"x": 64, "y": 0, "definition": "def_a"},
        }
    (cat_dir / "skills.json").write_text(json.dumps(skills))

    if connections is None:
        connections = {"normal": {"bidirectional": [["root", "a"], ["a", "b"]]}}
    (cat_dir / "connections.json").write_text(json.dumps(connections))

    (cat_dir / "experience.json").write_text(json.dumps({
        "experience_per_level": {"type": "expression", "data": {"expression": experience_expr}},
        "sources": [],
    }))


class TestCheckSkillTrees(unittest.TestCase):
    def test_valid_category_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_config(tmp, ["test_cat"])
            _write_valid_category(tmp)
            errors, stats = check_skill_trees.check_skill_trees(Path(tmp))
            self.assertEqual(errors, [])
            self.assertEqual(stats["categories"], 1)
            self.assertEqual(stats["skills"], 3)
            self.assertEqual(stats["roots"], 1)
            self.assertEqual(check_skill_trees.main([tmp]), 0)

    def test_no_root_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_config(tmp, ["test_cat"])
            _write_valid_category(tmp, skills={
                "root": {"x": 0, "y": 0, "definition": "def_a"},
                "a": {"x": 32, "y": 0, "definition": "def_a"},
            }, connections={"normal": {"bidirectional": [["root", "a"]]}})
            errors, _ = check_skill_trees.check_skill_trees(Path(tmp))
            self.assertTrue(any("no skill node has" in e for e in errors))

    def test_multiple_roots_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_config(tmp, ["test_cat"])
            _write_valid_category(tmp, skills={
                "root": {"x": 0, "y": 0, "definition": "def_a", "root": True},
                "root2": {"x": 32, "y": 0, "definition": "def_a", "root": True},
            }, connections={"normal": {"bidirectional": []}})
            errors, _ = check_skill_trees.check_skill_trees(Path(tmp))
            self.assertTrue(any("expected exactly 1 root node" in e for e in errors))

    def test_exclusive_connection_is_banned(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_config(tmp, ["test_cat"])
            _write_valid_category(tmp, connections={
                "normal": {"bidirectional": [["root", "a"], ["a", "b"]]},
                "exclusive": {"bidirectional": [["a", "b"]]},
            })
            errors, _ = check_skill_trees.check_skill_trees(Path(tmp))
            self.assertTrue(any("exclusive" in e and "removed exclusivity" in e for e in errors))

    def test_unreachable_node_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_config(tmp, ["test_cat"])
            # 'b' has no edge to anything - stranded.
            _write_valid_category(tmp, connections={"normal": {"bidirectional": [["root", "a"]]}})
            errors, _ = check_skill_trees.check_skill_trees(Path(tmp))
            self.assertTrue(any("not reachable from the root" in e for e in errors))

    def test_dangling_definition_reference_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_config(tmp, ["test_cat"])
            _write_valid_category(tmp, skills={
                "root": {"x": 0, "y": 0, "definition": "def_a", "root": True},
                "a": {"x": 32, "y": 0, "definition": "ghost_def"},
                "b": {"x": 64, "y": 0, "definition": "def_a"},
            })
            errors, _ = check_skill_trees.check_skill_trees(Path(tmp))
            self.assertTrue(any("ghost_def" in e and "not a key in definitions.json" in e for e in errors))

    def test_orphan_definition_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_config(tmp, ["test_cat"])
            definitions = {
                "def_a": {
                    "title": "+0.1 Luck",
                    "icon": {"type": "item", "data": {"item": "rabbit_foot"}},
                    "rewards": [{"type": "puffish_skills:attribute", "data": {"attribute": "generic.luck", "value": 0.1, "operation": "addition"}}],
                },
                "def_unused": {
                    "title": "+1% Attack Speed",
                    "icon": {"type": "item", "data": {"item": "sugar"}},
                    "rewards": [{"type": "puffish_skills:attribute", "data": {"attribute": "generic.attack_speed", "value": 0.01, "operation": "multiply_base"}}],
                },
            }
            _write_valid_category(tmp, definitions=definitions)
            errors, _ = check_skill_trees.check_skill_trees(Path(tmp))
            self.assertTrue(any("def_unused" in e and "orphaned" in e for e in errors))

    def test_overlapping_coordinates_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_config(tmp, ["test_cat"])
            _write_valid_category(tmp, skills={
                "root": {"x": 0, "y": 0, "definition": "def_a", "root": True},
                "a": {"x": 32, "y": 0, "definition": "def_a"},
                "b": {"x": 32, "y": 0, "definition": "def_a"},
            })
            errors, _ = check_skill_trees.check_skill_trees(Path(tmp))
            self.assertTrue(any("both sit at" in e for e in errors))

    def test_unknown_attribute_id_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_config(tmp, ["test_cat"])
            _write_valid_category(tmp, attribute="totally_made_up:not_a_real_attribute")
            errors, _ = check_skill_trees.check_skill_trees(Path(tmp))
            self.assertTrue(any("not in check_skill_trees.py's KNOWN_ATTRIBUTE_IDS" in e for e in errors))

    def test_unknown_attribute_operation_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_config(tmp, ["test_cat"])
            # 'add_value' is vanilla AttributeModifier.Operation vocabulary,
            # NOT puffish's own - exactly the cross-vocabulary mistake
            # documented in DECISIONS.md for mob_scaling.js.
            _write_valid_category(tmp, operation="add_value")
            errors, _ = check_skill_trees.check_skill_trees(Path(tmp))
            self.assertTrue(any("attribute operation 'add_value'" in e for e in errors))

    def test_linear_experience_curve_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_config(tmp, ["test_cat"])
            _write_valid_category(tmp, experience_expr="100 + level * 40")
            errors, _ = check_skill_trees.check_skill_trees(Path(tmp))
            self.assertTrue(any("does not look exponential" in e for e in errors))

    def test_non_increasing_experience_curve_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_config(tmp, ["test_cat"])
            _write_valid_category(tmp, experience_expr="100")
            errors, _ = check_skill_trees.check_skill_trees(Path(tmp))
            self.assertTrue(any("not strictly increasing" in e for e in errors))

    def test_exponential_experience_curve_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_config(tmp, ["test_cat"])
            _write_valid_category(tmp, experience_expr="70 * (1.13 ^ level)")
            errors, _ = check_skill_trees.check_skill_trees(Path(tmp))
            self.assertEqual(errors, [])

    def test_missing_category_dir_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_config(tmp, ["ghost_cat"])
            errors, _ = check_skill_trees.check_skill_trees(Path(tmp))
            self.assertTrue(any("missing category.json" in e for e in errors))

    def test_real_generated_output_passes(self):
        """Runs the actual checker against this repo's real, generated
        skill-tree output (not a synthetic fixture) - catches drift between
        gen_skill_tree.py and this checker's invariants."""
        errors, stats = check_skill_trees.check_skill_trees(check_skill_trees.REPO_ROOT)
        self.assertEqual(errors, [])
        self.assertGreaterEqual(stats["categories"], 20)


if __name__ == "__main__":
    unittest.main()
