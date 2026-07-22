import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_storage_tiers  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

VALID_SHA512 = "a" * 128
VALID_SHA1 = "b" * 40


def _lock(entries):
    return {"minecraft": "1.21.1", "loader": "neoforge", "mods": entries}


def _lock_entry(slug, version_number="1.21.1-1.5.80.1999", filename=None, side="both"):
    return {
        "slug": slug,
        "project_id": "x",
        "version_id": "y",
        "version_number": version_number,
        "filename": filename or f"{slug}.jar",
        "url": f"https://cdn.example/{slug}.jar",
        "hashes": {"sha512": VALID_SHA512, "sha1": VALID_SHA1},
        "filesize": 12345,
        "side": side,
        "phase": 11,
        "note": "",
    }


def _manifest(slugs):
    return {"minecraft": "1.21.1", "loader": "neoforge",
            "mods": [{"slug": s, "side": "both", "phase": 11, "note": ""} for s in slugs]}


VALID_SNAPSHOT = {
    "modid": "sophisticatedstorage",
    "source_slug": "sophisticated-storage",
    "source_version": "1.21.1-1.5.80.1999",
    "blocks": ["barrel", "chest", "iron_barrel", "iron_chest", "iron_shulker_box",
               "gold_barrel", "gold_chest", "gold_shulker_box", "copper_barrel"],
    "items": ["stack_upgrade_tier_1", "stack_upgrade_tier_3", "basic_to_iron_tier_upgrade"],
}

MINIMAL_TIER_GATING_JS = """
const TG_TIER_INFO = [
    {
        tierName: 'Andesite Age',
        materialName: 'an Andesite Alloy',
        why: 'test',
        items: ['sophisticatedstorage:iron_barrel', 'sophisticatedstorage:stack_upgrade_tier_1'],
    },
]
ServerEvents.recipes(event => {
    const SOPH_STORAGE_TYPES = ['barrel', 'chest', 'shulker_box']
    SOPH_STORAGE_TYPES.forEach(type => {
        event.remove({ id: `sophisticatedstorage:iron_${type}` })
        event.custom({ result: { id: `sophisticatedstorage:iron_${type}` } }).id('vpp:x')
        event.remove({ id: `sophisticatedstorage:gold_${type}` })
        event.custom({ result: { id: `sophisticatedstorage:gold_${type}` } }).id('vpp:y')
    })
})
"""

ANDESITE_TOML = """
[stage]
id = "andesite_age"
display_name = "Andesite Age"
description = "x"
icon = "minecraft:stick"
unlock_message = "x"
dependency = "rootborn"

[items]
locked = ["id:sophisticatedstorage:basic_to_iron_tier_upgrade", "id:sophisticatedstorage:stack_upgrade_tier_1"]
always_unlocked = []

[blocks]
locked = ["id:sophisticatedstorage:iron_barrel", "id:sophisticatedstorage:iron_chest", "id:sophisticatedstorage:iron_shulker_box"]
always_unlocked = []

[dimensions]
locked = []

[recipes]
locked_ids = []
locked_items = []

[enforcement]
block_crafting_with_locked_ingredients = true
"""

BRASS_TOML = """
[stage]
id = "brass_age"
display_name = "Brass Age"
description = "x"
icon = "minecraft:stick"
unlock_message = "x"
dependency = "andesite_age"

[items]
locked = ["id:sophisticatedstorage:stack_upgrade_tier_3"]
always_unlocked = []

[blocks]
locked = ["id:sophisticatedstorage:gold_barrel", "id:sophisticatedstorage:gold_chest", "id:sophisticatedstorage:gold_shulker_box"]
always_unlocked = []

[dimensions]
locked = []

[recipes]
locked_ids = []
locked_items = []

[enforcement]
block_crafting_with_locked_ingredients = true
"""


class TestCheckStorageTiersFixture(unittest.TestCase):
    """Builds a minimal-but-complete valid fixture pack, then perturbs one
    thing at a time - same shape as test_check_lockfile.py's CLI tests."""

    def _write_pack(self, tmp, *, lock=None, manifest=None, snapshot=None,
                     tier_gating_js=None, extra_toml=None, omit_snapshot=False):
        root = Path(tmp)
        pack = root / "pack"
        pack.mkdir()
        (pack / "manifest.json").write_text(json.dumps(
            manifest if manifest is not None else _manifest(["sophisticated-storage", "sophisticated-core"])
        ), encoding="utf-8")
        (pack / "mods.lock.json").write_text(json.dumps(
            lock if lock is not None else _lock([_lock_entry("sophisticated-storage"), _lock_entry("sophisticated-core")])
        ), encoding="utf-8")

        prog = pack / "progression"
        prog.mkdir()
        (prog / "andesite_age.toml").write_text(ANDESITE_TOML, encoding="utf-8")
        (prog / "brass_age.toml").write_text(BRASS_TOML, encoding="utf-8")
        if extra_toml:
            for name, content in extra_toml.items():
                (prog / name).write_text(content, encoding="utf-8")

        if not omit_snapshot:
            reg_dir = pack / "mod_registries"
            reg_dir.mkdir()
            (reg_dir / "sophisticatedstorage.json").write_text(
                json.dumps(snapshot if snapshot is not None else VALID_SNAPSHOT), encoding="utf-8"
            )

        kubejs = pack / "kubejs" / "server_scripts"
        kubejs.mkdir(parents=True)
        (kubejs / "tier_gating.js").write_text(
            tier_gating_js if tier_gating_js is not None else MINIMAL_TIER_GATING_JS, encoding="utf-8"
        )
        return root

    def test_valid_fixture_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._write_pack(tmp)
            self.assertEqual(check_storage_tiers.main([str(root)]), 0)

    def test_missing_mod_from_lockfile_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._write_pack(tmp, lock=_lock([_lock_entry("sophisticated-core")]))
            self.assertEqual(check_storage_tiers.main([str(root)]), 1)

    def test_missing_dependency_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._write_pack(tmp, lock=_lock([_lock_entry("sophisticated-storage")]))
            self.assertEqual(check_storage_tiers.main([str(root)]), 1)

    def test_bad_hash_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = _lock_entry("sophisticated-storage")
            entry["hashes"]["sha512"] = "not-hex"
            root = self._write_pack(tmp, lock=_lock([entry, _lock_entry("sophisticated-core")]))
            self.assertEqual(check_storage_tiers.main([str(root)]), 1)

    def test_wrong_loader_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = _lock([_lock_entry("sophisticated-storage"), _lock_entry("sophisticated-core")])
            lock["loader"] = "fabric"
            root = self._write_pack(tmp, lock=lock)
            self.assertEqual(check_storage_tiers.main([str(root)]), 1)

    def test_client_only_side_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            entry = _lock_entry("sophisticated-storage", side="client")
            root = self._write_pack(tmp, lock=_lock([entry, _lock_entry("sophisticated-core")]))
            self.assertEqual(check_storage_tiers.main([str(root)]), 1)

    def test_missing_snapshot_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._write_pack(tmp, omit_snapshot=True)
            self.assertEqual(check_storage_tiers.main([str(root)]), 1)

    def test_stale_snapshot_version_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            stale = dict(VALID_SNAPSHOT)
            stale["source_version"] = "1.21.1-1.4.0.0"
            root = self._write_pack(tmp, snapshot=stale)
            self.assertEqual(check_storage_tiers.main([str(root)]), 1)

    def test_typo_id_in_progression_toml_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_toml = ANDESITE_TOML.replace(
                "sophisticatedstorage:iron_barrel", "sophisticatedstorage:iorn_barrle"
            )
            root = self._write_pack(tmp, extra_toml={"andesite_age.toml": bad_toml})
            self.assertEqual(check_storage_tiers.main([str(root)]), 1)

    def test_id_gated_at_two_tiers_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            dup_brass = BRASS_TOML.replace(
                'locked = ["id:sophisticatedstorage:gold_barrel"',
                'locked = ["id:sophisticatedstorage:iron_barrel", "id:sophisticatedstorage:gold_barrel"',
            )
            root = self._write_pack(tmp, extra_toml={"brass_age.toml": dup_brass})
            self.assertEqual(check_storage_tiers.main([str(root)]), 1)

    def test_item_listed_under_wrong_category_fails(self):
        # iron_barrel is a BLOCK in the snapshot; listing it under [items]
        # instead of [blocks] should be caught.
        with tempfile.TemporaryDirectory() as tmp:
            bad_toml = ANDESITE_TOML.replace(
                'locked = ["id:sophisticatedstorage:basic_to_iron_tier_upgrade", "id:sophisticatedstorage:stack_upgrade_tier_1"]',
                'locked = ["id:sophisticatedstorage:basic_to_iron_tier_upgrade", "id:sophisticatedstorage:stack_upgrade_tier_1", "id:sophisticatedstorage:iron_barrel"]',
            ).replace(
                'locked = ["id:sophisticatedstorage:iron_barrel", "id:sophisticatedstorage:iron_chest", "id:sophisticatedstorage:iron_shulker_box"]',
                'locked = ["id:sophisticatedstorage:iron_chest", "id:sophisticatedstorage:iron_shulker_box"]',
            )
            root = self._write_pack(tmp, extra_toml={"andesite_age.toml": bad_toml})
            self.assertEqual(check_storage_tiers.main([str(root)]), 1)

    def test_tier_gating_js_typo_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_js = MINIMAL_TIER_GATING_JS.replace(
                "sophisticatedstorage:iron_barrel'", "sophisticatedstorage:iron_barrle'"
            )
            root = self._write_pack(tmp, tier_gating_js=bad_js)
            self.assertEqual(check_storage_tiers.main([str(root)]), 1)

    def test_tg_tier_info_bad_tier_name_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_js = MINIMAL_TIER_GATING_JS.replace("tierName: 'Andesite Age'", "tierName: 'Made Up Age'")
            root = self._write_pack(tmp, tier_gating_js=bad_js)
            self.assertEqual(check_storage_tiers.main([str(root)]), 1)

    def test_comment_prose_is_not_flagged(self):
        # Comments freely say things like "sophisticatedstorage:barrel/chest"
        # in prose - must not false-positive.
        with tempfile.TemporaryDirectory() as tmp:
            js = MINIMAL_TIER_GATING_JS + "\n// base wood barrel/chest (sophisticatedstorage:barrel/chest, one id)\n"
            root = self._write_pack(tmp, tier_gating_js=js)
            self.assertEqual(check_storage_tiers.main([str(root)]), 0)


class TestCheckStorageTiersRealRepo(unittest.TestCase):
    def test_real_repo_passes(self):
        manifest_path = REPO_ROOT / "pack" / "manifest.json"
        if not manifest_path.is_file():
            self.skipTest(f"not running inside the repo (no manifest at {manifest_path})")
        self.assertEqual(check_storage_tiers.main([str(REPO_ROOT)]), 0)


if __name__ == "__main__":
    unittest.main()
