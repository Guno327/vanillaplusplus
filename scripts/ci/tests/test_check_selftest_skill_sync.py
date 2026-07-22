import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_selftest_skill_sync  # noqa: E402


SKILLS_ROOT = ("pack", "kubejs", "data", "puffish_skills", "puffish_skills")
SELFTEST_JS_PATH = ("pack", "kubejs", "server_scripts", "selftest.js")


def _write_selftest_js(tmp, category_ids, node_count):
    """Mirrors the real selftest.js shape closely enough for
    check_selftest_skill_sync's textual extraction to parse: a
    single-quoted, trailing-comma JS array literal for ST_SKILL_CATEGORIES,
    followed by an integer const for ST_SKILL_NODE_COUNT_PER_CATEGORY."""
    path = Path(tmp).joinpath(*SELFTEST_JS_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    cats_body = ", ".join(f"'{c}'" for c in category_ids)
    path.write_text(
        "// GENERATED - test fixture\n"
        f"const ST_SKILL_CATEGORIES = [\n    {cats_body},\n]\n"
        f"const ST_SKILL_NODE_COUNT_PER_CATEGORY = {node_count}\n"
        "\nstCheck('dummy', () => ({ pass: true, detail: 'ok' }))\n",
        encoding="utf-8",
    )


def _write_generated_data(tmp, category_ids, node_count):
    """Writes real generated-shape data: config.json's category list plus
    one categories/<id>/skills.json per category with exactly node_count
    entries (content of each node doesn't matter to this checker)."""
    root = Path(tmp).joinpath(*SKILLS_ROOT)
    root.mkdir(parents=True, exist_ok=True)
    (root / "config.json").write_text(json.dumps({"version": 3, "categories": category_ids}))
    for cat_id in category_ids:
        cat_dir = root / "categories" / cat_id
        cat_dir.mkdir(parents=True, exist_ok=True)
        skills = {f"n{i}": {"x": i, "y": 0, "definition": "def_a"} for i in range(node_count)}
        (cat_dir / "skills.json").write_text(json.dumps(skills))


class CheckSelftestSkillSyncTest(unittest.TestCase):
    def test_fails_on_the_exact_issue_77_shape(self):
        """The real pre-fix bug: #71 shipped 23 categories x 34 nodes, but
        selftest.js's node-count assertion was left at the old 15. Building
        that exact shape here (23 declared categories, but the node-count
        constant still 15) must fail loudly and name the drift."""
        with tempfile.TemporaryDirectory() as tmp:
            category_ids = [f"cat{i}" for i in range(23)]
            _write_selftest_js(tmp, category_ids, node_count=15)
            _write_generated_data(tmp, category_ids, node_count=34)

            errors, stats = check_selftest_skill_sync.check_selftest_skill_sync(Path(tmp))

            self.assertTrue(errors, "expected the stale 15-vs-34 node count to be flagged")
            joined = "\n".join(errors)
            self.assertIn("ST_SKILL_NODE_COUNT_PER_CATEGORY", joined)
            self.assertIn("15", joined)
            # every one of the 23 categories should show up as a bad count
            for cat_id in category_ids:
                self.assertIn(f"{cat_id}=34", joined)

    def test_passes_on_matching_real_repo_data(self):
        """Run against this actual checked-out repo's real
        selftest.js + generated puffish_skills data - the ground truth this
        check exists to protect. Skips (does not fail) if run outside the
        real repo checkout, e.g. from an unrelated CI sandbox."""
        real_root = check_selftest_skill_sync.REPO_ROOT
        selftest_path = real_root / check_selftest_skill_sync.SELFTEST_JS_REL
        config_path = real_root / check_selftest_skill_sync.SKILLS_CONFIG_REL
        if not selftest_path.is_file() or not config_path.is_file():
            self.skipTest("not running inside the real repo checkout")

        errors, stats = check_selftest_skill_sync.check_selftest_skill_sync(real_root)

        self.assertEqual(errors, [])
        self.assertEqual(stats["selftest_categories"], stats["generated_categories"])
        self.assertGreater(stats["selftest_node_count_per_category"], 0)

    def test_category_id_mismatch_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            generated_ids = ["alchemy", "bows", "mining"]
            js_ids = ["alchemy", "bows", "typo_category"]  # 'mining' missing, 'typo_category' extra
            _write_selftest_js(tmp, js_ids, node_count=5)
            _write_generated_data(tmp, generated_ids, node_count=5)

            errors, stats = check_selftest_skill_sync.check_selftest_skill_sync(Path(tmp))

            joined = "\n".join(errors)
            self.assertIn("mining", joined)
            self.assertIn("typo_category", joined)

    def test_matching_shape_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            category_ids = ["alchemy", "bows", "mining"]
            _write_selftest_js(tmp, category_ids, node_count=34)
            _write_generated_data(tmp, category_ids, node_count=34)

            errors, stats = check_selftest_skill_sync.check_selftest_skill_sync(Path(tmp))

            self.assertEqual(errors, [])
            self.assertEqual(stats["selftest_categories"], 3)
            self.assertEqual(stats["selftest_node_count_per_category"], 34)
            self.assertEqual(stats["generated_categories"], 3)


if __name__ == "__main__":
    unittest.main()
