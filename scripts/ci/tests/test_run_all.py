import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import run_all  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _minimal_valid_pack(root):
    """A from-scratch pack/ tree that should pass every one of the five
    checks, used to test run_all's own aggregation/exit-code logic without
    depending on the real repo tree."""
    pack = Path(root) / "pack"
    (pack / "config").mkdir(parents=True)
    (pack / "kubejs" / "server_scripts").mkdir(parents=True)
    (pack / "kubejs" / "data" / "vanillaplusplus" / "advancement" / "quests").mkdir(parents=True)

    # GitHub #70: sophisticated-storage + its sophisticated-core dependency,
    # matching what check_storage_tiers.py requires (real filename/hash/
    # side, a registry snapshot, and at least one gated id it can verify).
    soph_mods = [
        {"slug": "sophisticated-storage", "side": "both", "phase": 11},
        {"slug": "sophisticated-core", "side": "both", "phase": 11},
    ]
    manifest = {"minecraft": "1.21.1", "loader": "neoforge",
                "mods": [{"slug": "create", "side": "both", "phase": 0}] + soph_mods}
    lock = {"minecraft": "1.21.1", "loader": "neoforge",
            "mods": [{"slug": "create", "side": "both", "phase": 0,
                      "filename": "create.jar", "url": "https://cdn.example/create.jar",
                      "hashes": {"sha512": "a" * 128}}] + [
                {"slug": m["slug"], "side": "both", "phase": 11,
                 "filename": f"{m['slug']}-1.21.1-1.0.0.jar",
                 "url": f"https://cdn.example/{m['slug']}.jar",
                 "version_number": "1.21.1-1.0.0",
                 "hashes": {"sha512": "a" * 128, "sha1": "b" * 40},
                 "filesize": 100} for m in soph_mods
            ]}
    (pack / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (pack / "mods.lock.json").write_text(json.dumps(lock), encoding="utf-8")

    (pack / "mod_registries").mkdir(parents=True)
    (pack / "mod_registries" / "sophisticatedstorage.json").write_text(json.dumps({
        "modid": "sophisticatedstorage",
        "source_slug": "sophisticated-storage",
        "source_version": "1.21.1-1.0.0",
        "blocks": ["iron_barrel"],
        "items": ["stack_upgrade_tier_1"],
    }), encoding="utf-8")

    (pack / "progression").mkdir(parents=True)
    (pack / "progression" / "andesite_age.toml").write_text(
        '[stage]\n'
        'id = "andesite_age"\n'
        'display_name = "Andesite Age"\n'
        'description = "d"\n'
        'icon = "minecraft:stick"\n'
        'unlock_message = "m"\n'
        '\n'
        '[items]\n'
        'locked = ["id:sophisticatedstorage:stack_upgrade_tier_1"]\n'
        'always_unlocked = []\n'
        '\n'
        '[blocks]\n'
        'locked = ["id:sophisticatedstorage:iron_barrel"]\n'
        'always_unlocked = []\n'
        '\n'
        '[dimensions]\n'
        'locked = []\n',
        encoding="utf-8")

    (pack / "config" / "sample.json").write_text('{"a": 1}', encoding="utf-8")
    # GitHub #33: the quest book lives in pack/kubejs/server_scripts/quests.js
    # now (a `const QUEST_CHAPTERS = [...]` JSON literal), not FTB Quests SNBT.
    (pack / "kubejs" / "server_scripts" / "quests.js").write_text(
        'const QUEST_CHAPTERS = [{"id": "c1", "quests": '
        '[{"id": "q1", "tasks": [{"type": "checkmark"}], "rewards": [], "dependencies": []}]}]\n',
        encoding="utf-8")
    (pack / "kubejs" / "server_scripts" / "clean.js").write_text(
        "try {\n    let x = 1\n} catch (e) {}\n", encoding="utf-8")
    # GitHub #70: tier_gating.js, referencing the same id the progression
    # toml above locks so check_storage_tiers.py's cross-checks pass.
    (pack / "kubejs" / "server_scripts" / "tier_gating.js").write_text(
        "const TG_TIER_INFO = [\n"
        "    {\n"
        "        tierName: 'Andesite Age',\n"
        "        materialName: 'an Andesite Alloy',\n"
        "        why: 'test',\n"
        "        items: ['sophisticatedstorage:iron_barrel'],\n"
        "    },\n"
        "]\n"
        "ServerEvents.recipes(event => {})\n",
        encoding="utf-8")
    # GitHub #36: one advancement file per quest, matching quests.js above.
    # GitHub #66: q1 has no dependencies, i.e. it's the tree's root, so its
    # criterion must be the self-granting minecraft:tick (not
    # minecraft:impossible) or the whole tab is never visible - see
    # scripts/ci/check_advancements.py's module docstring.
    advancement = {
        "criteria": {"auto": {"trigger": "minecraft:tick"}},
        "requirements": [["auto"]],
        "display": {"icon": {"id": "minecraft:stone", "count": 1}, "title": "Q1",
                     "description": "d", "frame": "task",
                     "background": "minecraft:textures/gui/advancements/backgrounds/stone.png"},
    }
    (pack / "kubejs" / "data" / "vanillaplusplus" / "advancement" / "quests" / "q1.json").write_text(
        json.dumps(advancement), encoding="utf-8")

    # GitHub #24: one minimal, valid puffish_skills category (config.json +
    # category.json with starting_points, one definition, one root skill).
    skills_root = pack / "kubejs" / "data" / "puffish_skills" / "puffish_skills"
    cat_dir = skills_root / "categories" / "cat1"
    cat_dir.mkdir(parents=True)
    (skills_root / "config.json").write_text(json.dumps({"categories": ["cat1"]}), encoding="utf-8")
    (cat_dir / "category.json").write_text(json.dumps({"starting_points": 1}), encoding="utf-8")
    (cat_dir / "definitions.json").write_text(json.dumps({"def1": {}}), encoding="utf-8")
    (cat_dir / "skills.json").write_text(
        json.dumps({"skill1": {"x": 0, "y": 0, "definition": "def1", "root": True}}), encoding="utf-8")

    # GitHub #77: check_selftest_skill_sync.py cross-checks selftest.js's
    # hand-maintained ST_SKILL_CATEGORIES / ST_SKILL_NODE_COUNT_PER_CATEGORY
    # against the puffish_skills data above - keep them in sync with cat1's
    # single-category, single-node shape.
    (pack / "kubejs" / "server_scripts" / "selftest.js").write_text(
        "const ST_SKILL_CATEGORIES = [\n    'cat1',\n]\n"
        "const ST_SKILL_NODE_COUNT_PER_CATEGORY = 1\n",
        encoding="utf-8")
    return pack


class TestRunAll(unittest.TestCase):
    def test_all_checks_pass_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            _minimal_valid_pack(tmp)
            self.assertEqual(run_all.main([tmp]), 0)

    def test_one_failing_check_causes_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = _minimal_valid_pack(tmp)
            (pack / "config" / "broken.json").write_text("not json", encoding="utf-8")
            self.assertEqual(run_all.main([tmp]), 1)

    def test_real_repo_tree_passes(self):
        pack_dir = REPO_ROOT / "pack"
        if not pack_dir.is_dir():
            self.skipTest(f"not running inside the repo (no pack/ found at {pack_dir})")
        self.assertEqual(run_all.main([str(REPO_ROOT)]), 0)


if __name__ == "__main__":
    unittest.main()
