"""Unit tests for check_mod_dependencies_offline - the FAST-TIER (every PR,
no network/jars) counterpart to check_mod_dependencies.py, added as v0.5.0
follow-up hardening so a missing required dependency (the reeses_sodium_
options case) is caught on every PR, not just weekly/on-dispatch boot-tier
runs. Covers both guards: the lockfile<->snapshot SYNC check, and the
resolve() pass-through against the committed snapshot data."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_mod_dependencies_offline as offline  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _lock(mods):
    return {"minecraft": "1.21.1", "loader": "neoforge", "mods": mods}


def _lock_mod(slug, version_number="1.0.0"):
    return {"slug": slug, "version_number": version_number, "filename": f"{slug}.jar",
            "url": f"https://cdn.example/{slug}.jar", "hashes": {"sha512": "a" * 128},
            "filesize": 1, "side": "both", "phase": 0, "note": ""}


def _snapshot_mod(version_number, provided, required):
    return {"version_number": version_number, "provided": provided, "required": required}


def _req(modid, version_range="[1,)"):
    return {"modId": modid, "versionRange": version_range, "enforced": version_range is not None}


def _write(root, lock, snapshot):
    pack = Path(root) / "pack"
    (pack / "mod_registries").mkdir(parents=True)
    (pack / "mods.lock.json").write_text(json.dumps(lock), encoding="utf-8")
    (pack / "mod_registries" / "mod_dependencies.json").write_text(json.dumps(snapshot), encoding="utf-8")


class TestSyncGuard(unittest.TestCase):
    def test_in_sync_snapshot_passes(self):
        lock = _lock([_lock_mod("a", "1.0.0")])
        snapshot = {"mods": {"a": _snapshot_mod("1.0.0", ["a"], [])}}
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, lock, snapshot)
            self.assertEqual(offline.main([tmp]), 0)

    def test_mod_added_to_lockfile_without_regenerating_fails(self):
        # Lockfile now has 'b' too, but the snapshot was never regenerated.
        lock = _lock([_lock_mod("a", "1.0.0"), _lock_mod("b", "1.0.0")])
        snapshot = {"mods": {"a": _snapshot_mod("1.0.0", ["a"], [])}}
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, lock, snapshot)
            self.assertEqual(offline.main([tmp]), 1)

    def test_mod_removed_from_lockfile_leaves_stale_snapshot_entry_fails(self):
        lock = _lock([_lock_mod("a", "1.0.0")])
        snapshot = {"mods": {"a": _snapshot_mod("1.0.0", ["a"], []),
                              "b": _snapshot_mod("1.0.0", ["b"], [])}}
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, lock, snapshot)
            self.assertEqual(offline.main([tmp]), 1)

    def test_version_bump_without_regenerating_fails(self):
        lock = _lock([_lock_mod("a", "2.0.0")])
        snapshot = {"mods": {"a": _snapshot_mod("1.0.0", ["a"], [])}}
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, lock, snapshot)
            self.assertEqual(offline.main([tmp]), 1)

    def test_missing_snapshot_file_fails(self):
        lock = _lock([_lock_mod("a", "1.0.0")])
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "pack"
            pack.mkdir(parents=True)
            (pack / "mods.lock.json").write_text(json.dumps(lock), encoding="utf-8")
            self.assertEqual(offline.main([tmp]), 1)


class TestResolutionAgainstSnapshot(unittest.TestCase):
    def test_satisfied_dependency_passes(self):
        lock = _lock([_lock_mod("a", "1.0.0"), _lock_mod("b", "1.0.0")])
        snapshot = {"mods": {
            "a": _snapshot_mod("1.0.0", ["a"], [_req("b")]),
            "b": _snapshot_mod("1.0.0", ["b"], []),
        }}
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, lock, snapshot)
            self.assertEqual(offline.main([tmp]), 0)

    def test_reeses_case_missing_required_dependency_fails(self):
        # Reproduces the v0.5.0 regression: sodium-options-api requires
        # reeses_sodium_options, which is never installed/provided.
        lock = _lock([_lock_mod("sodium-options-api", "1.0.0")])
        snapshot = {"mods": {
            "sodium-options-api": _snapshot_mod(
                "1.0.0", ["sodiumoptionsapi"], [_req("reeses_sodium_options", "*")]
            ),
        }}
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, lock, snapshot)
            self.assertEqual(offline.main([tmp]), 1)

    def test_dependency_provided_via_jarinjar_in_snapshot_passes(self):
        lock = _lock([_lock_mod("create", "1.0.0"), _lock_mod("iris-flw-compat", "1.0.0")])
        snapshot = {"mods": {
            "create": _snapshot_mod("1.0.0", ["create", "flywheel", "ponder"], []),
            "iris-flw-compat": _snapshot_mod("1.0.0", ["irisflwcompat"], [_req("flywheel")]),
        }}
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, lock, snapshot)
            self.assertEqual(offline.main([tmp]), 0)

    def test_malformed_dep_without_versionrange_is_not_enforced(self):
        lock = _lock([_lock_mod("stellaris", "1.0.0")])
        dep = {"modId": "sky_aesthetics", "versionRange": None, "enforced": False}
        snapshot = {"mods": {"stellaris": _snapshot_mod("1.0.0", ["stellaris"], [dep])}}
        with tempfile.TemporaryDirectory() as tmp:
            _write(tmp, lock, snapshot)
            self.assertEqual(offline.main([tmp]), 0)


class TestRealRepoSnapshot(unittest.TestCase):
    def test_real_repo_snapshot_in_sync_and_resolves(self):
        pack_dir = REPO_ROOT / "pack"
        if not (pack_dir / "mod_registries" / "mod_dependencies.json").is_file():
            self.skipTest("pack/mod_registries/mod_dependencies.json not present "
                           "(run scripts/gen_mod_dependencies.py)")
        self.assertEqual(offline.main([str(REPO_ROOT)]), 0)


if __name__ == "__main__":
    unittest.main()
