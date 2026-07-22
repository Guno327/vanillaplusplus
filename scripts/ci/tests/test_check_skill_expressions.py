import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_skill_expressions  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CATS_ROOT = ("pack", "kubejs", "data", "puffish_skills", "puffish_skills")


def _write_experience(tmp, cat_id, experience):
    """Writes a single category's experience.json - the only file
    check_skill_expressions.py reads - directly under a from-scratch
    pack/ tree. Everything else this checker doesn't look at (category.json,
    skills.json, ...) is deliberately omitted."""
    cat_dir = Path(tmp).joinpath(*CATS_ROOT, "categories", cat_id)
    cat_dir.mkdir(parents=True, exist_ok=True)
    (cat_dir / "experience.json").write_text(json.dumps(experience), encoding="utf-8")


class TestCheckSkillExpressions(unittest.TestCase):
    def test_valid_expression_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_experience(tmp, "cat1", {
                "experience_per_level": {"type": "expression", "data": {"expression": "70 * (1.13 ^ level)"}},
                "sources": [{
                    "type": "puffish_skills:mine_block",
                    "data": {
                        "variables": {
                            "silk_touch": {"operations": []},
                            "stone_like": {"operations": []},
                        },
                        "experience": [
                            {"condition": "!silk_touch & stone_like", "expression": "1"},
                        ],
                    },
                }],
            })
            errors, stats = check_skill_expressions.check_skill_expressions(Path(tmp))
            self.assertEqual(errors, [])
            self.assertEqual(stats["files"], 1)
            self.assertEqual(stats["expressions"], 3)

    def test_pow_literal_is_rejected(self):
        """Regression test for issue #79: issue #71 shipped
        EXPERIENCE_EXPR = "70 * pow(1.13, level)", which puffish_skills'
        real expression engine rejects outright (no `pow` function exists
        in it - see this checker's module docstring), silently dropping
        every category's whole datapack entry at boot. This exact literal
        string must always be caught."""
        with tempfile.TemporaryDirectory() as tmp:
            _write_experience(tmp, "cat1", {
                "experience_per_level": {"type": "expression", "data": {"expression": "70 * pow(1.13, level)"}},
                "sources": [],
            })
            errors, _ = check_skill_expressions.check_skill_expressions(Path(tmp))
            self.assertTrue(errors)
            self.assertTrue(any("pow" in e for e in errors), errors)

    def test_unknown_identifier_in_experience_per_level_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_experience(tmp, "cat1", {
                "experience_per_level": {"type": "expression", "data": {"expression": "70 * sqrt(level) + bogus"}},
                "sources": [],
            })
            errors, _ = check_skill_expressions.check_skill_expressions(Path(tmp))
            self.assertTrue(any("'bogus'" in e for e in errors), errors)

    def test_known_function_and_constant_are_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_experience(tmp, "cat1", {
                "experience_per_level": {"type": "expression", "data": {"expression": "clamp(level * pi, 1, 9999)"}},
                "sources": [],
            })
            errors, _ = check_skill_expressions.check_skill_expressions(Path(tmp))
            self.assertEqual(errors, [])

    def test_unknown_identifier_in_source_condition_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_experience(tmp, "cat1", {
                "experience_per_level": {"type": "expression", "data": {"expression": "70 * (1.13 ^ level)"}},
                "sources": [{
                    "type": "puffish_skills:kill_entity",
                    "data": {
                        "variables": {"used_right_weapon": {"operations": []}},
                        "experience": [{"condition": "used_right_weapon & nonexistent_var", "expression": "2"}],
                    },
                }],
            })
            errors, _ = check_skill_expressions.check_skill_expressions(Path(tmp))
            self.assertTrue(any("'nonexistent_var'" in e for e in errors), errors)

    def test_variable_scope_does_not_leak_across_sources(self):
        """A variable declared in one source's own `variables` object must
        not be treated as in-scope for a different source in the same
        file - each source's `experience` conditions/expressions can only
        see that same source's own declared variables."""
        with tempfile.TemporaryDirectory() as tmp:
            _write_experience(tmp, "cat1", {
                "experience_per_level": {"type": "expression", "data": {"expression": "70 * (1.13 ^ level)"}},
                "sources": [
                    {
                        "type": "puffish_skills:kill_entity",
                        "data": {
                            "variables": {"used_right_weapon": {"operations": []}},
                            "experience": [{"condition": "used_right_weapon", "expression": "2"}],
                        },
                    },
                    {
                        "type": "puffish_skills:increase_stat",
                        "data": {
                            "variables": {"amount": {"operations": []}},
                            # `used_right_weapon` belongs to the OTHER source above, not this one.
                            "experience": [{"condition": "used_right_weapon", "expression": "amount"}],
                        },
                    },
                ],
            })
            errors, _ = check_skill_expressions.check_skill_expressions(Path(tmp))
            self.assertTrue(any("'used_right_weapon'" in e and "sources[1]" in e for e in errors), errors)

    def test_variable_in_scope_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_experience(tmp, "cat1", {
                "experience_per_level": {"type": "expression", "data": {"expression": "70 * (1.13 ^ level)"}},
                "sources": [{
                    "type": "puffish_skills:enchant_item",
                    "data": {
                        "variables": {"levels": {"operations": []}},
                        "experience": [{"condition": "levels > 0", "expression": "levels * 4"}],
                    },
                }],
            })
            errors, _ = check_skill_expressions.check_skill_expressions(Path(tmp))
            self.assertEqual(errors, [])

    def test_missing_skills_root_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors, _ = check_skill_expressions.check_skill_expressions(Path(tmp))
            self.assertTrue(any("not found" in e for e in errors))

    def test_no_experience_json_files_passes_trivially(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills_root = Path(tmp).joinpath(*CATS_ROOT)
            skills_root.mkdir(parents=True)
            errors, stats = check_skill_expressions.check_skill_expressions(Path(tmp))
            self.assertEqual(errors, [])
            self.assertEqual(stats["files"], 0)

    def test_main_prints_pass_and_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_experience(tmp, "cat1", {
                "experience_per_level": {"type": "expression", "data": {"expression": "70 * (1.13 ^ level)"}},
                "sources": [],
            })
            self.assertEqual(check_skill_expressions.main([tmp]), 0)

    def test_main_returns_nonzero_on_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_experience(tmp, "cat1", {
                "experience_per_level": {"type": "expression", "data": {"expression": "70 * pow(1.13, level)"}},
                "sources": [],
            })
            self.assertEqual(check_skill_expressions.main([tmp]), 1)

    def test_real_generated_output_passes(self):
        """Runs the actual checker against this repo's real, generated
        pack/kubejs/data/puffish_skills/ tree (scripts/gen_skill_tree.py's
        output) - the same class of end-to-end check every other
        test_check_*.py file in this directory does for its own checker."""
        skills_root = check_skill_expressions._skills_root(REPO_ROOT)
        if not skills_root.is_dir():
            self.skipTest(f"not running inside the repo (no {skills_root} found)")
        errors, stats = check_skill_expressions.check_skill_expressions(REPO_ROOT)
        self.assertEqual(errors, [])
        self.assertGreater(stats["files"], 0)
        self.assertGreater(stats["expressions"], 0)


if __name__ == "__main__":
    unittest.main()
