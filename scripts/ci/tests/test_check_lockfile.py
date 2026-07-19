import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_lockfile  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _mod(slug, side="both", phase=0, **extra):
    entry = {"slug": slug, "side": side, "phase": phase}
    entry.update(extra)
    return entry


def _lock_mod(slug, side="both", phase=0, filename=None, url=None, sha512="a" * 128, **extra):
    entry = {
        "slug": slug,
        "side": side,
        "phase": phase,
        "filename": filename if filename is not None else f"{slug}.jar",
        "url": url if url is not None else f"https://cdn.example/{slug}.jar",
        "hashes": {"sha512": sha512, "sha1": "b" * 40},
        "filesize": 12345,
    }
    entry.update(extra)
    return entry


class TestCheckLockfileLogic(unittest.TestCase):
    def test_consistent_manifest_and_lock_pass(self):
        manifest = {"minecraft": "1.21.1", "loader": "neoforge",
                    "mods": [_mod("create"), _mod("jei", side="client", phase=1)]}
        lock = {"minecraft": "1.21.1", "loader": "neoforge",
                "mods": [_lock_mod("create"), _lock_mod("jei", side="client", phase=1)]}
        errors = check_lockfile.check_lockfile(manifest, lock)
        self.assertEqual(errors, [])

    def test_slug_missing_from_lock_is_reported(self):
        manifest = {"mods": [_mod("create"), _mod("jei")]}
        lock = {"mods": [_lock_mod("create")]}
        errors = check_lockfile.check_lockfile(manifest, lock)
        self.assertTrue(any("jei" in e and "missing from mods.lock.json" in e for e in errors))

    def test_extra_slug_in_lock_is_reported(self):
        manifest = {"mods": [_mod("create")]}
        lock = {"mods": [_lock_mod("create"), _lock_mod("extra-mod")]}
        errors = check_lockfile.check_lockfile(manifest, lock)
        self.assertTrue(any("extra-mod" in e and "not in manifest.json" in e for e in errors))

    def test_missing_filename_is_reported(self):
        manifest = {"mods": [_mod("create")]}
        entry = _lock_mod("create")
        entry["filename"] = ""
        lock = {"mods": [entry]}
        errors = check_lockfile.check_lockfile(manifest, lock)
        self.assertTrue(any("filename" in e for e in errors))

    def test_missing_url_is_reported(self):
        manifest = {"mods": [_mod("create")]}
        entry = _lock_mod("create")
        del entry["url"]
        lock = {"mods": [entry]}
        errors = check_lockfile.check_lockfile(manifest, lock)
        self.assertTrue(any("url" in e for e in errors))

    def test_missing_sha512_is_reported(self):
        manifest = {"mods": [_mod("create")]}
        entry = _lock_mod("create")
        entry["hashes"] = {"sha1": "b" * 40}  # no sha512
        lock = {"mods": [entry]}
        errors = check_lockfile.check_lockfile(manifest, lock)
        self.assertTrue(any("hashes.sha512" in e for e in errors))

    def test_side_mismatch_is_reported(self):
        manifest = {"mods": [_mod("create", side="both")]}
        lock = {"mods": [_lock_mod("create", side="server")]}
        errors = check_lockfile.check_lockfile(manifest, lock)
        self.assertTrue(any("side mismatch" in e for e in errors))

    def test_phase_mismatch_is_reported(self):
        manifest = {"mods": [_mod("create", phase=0)]}
        lock = {"mods": [_lock_mod("create", phase=5)]}
        errors = check_lockfile.check_lockfile(manifest, lock)
        self.assertTrue(any("phase mismatch" in e for e in errors))

    def test_curseforge_sourced_manifest_entry_uses_same_lock_schema(self):
        # Ground-truthed: this repo's mods.lock.json uses one schema for
        # every entry regardless of manifest "source" - a curseforge-
        # sourced manifest entry still needs filename/url/hashes.sha512 in
        # the lock, same as any other.
        manifest = {"mods": [_mod("ftb-quests", source="curseforge", cf_project_slug="ftb-quests-forge")]}
        lock = {"mods": [_lock_mod("ftb-quests")]}
        errors = check_lockfile.check_lockfile(manifest, lock)
        self.assertEqual(errors, [])


class TestCheckLockfileCli(unittest.TestCase):
    def _write_pack(self, tmp, manifest, lock):
        pack = Path(tmp) / "pack"
        pack.mkdir()
        (pack / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (pack / "mods.lock.json").write_text(json.dumps(lock), encoding="utf-8")
        return pack

    def test_cli_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_pack(
                tmp,
                {"mods": [_mod("create")]},
                {"mods": [_lock_mod("create")]},
            )
            self.assertEqual(check_lockfile.main([tmp]), 0)

    def test_cli_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_pack(
                tmp,
                {"mods": [_mod("create"), _mod("missing-mod")]},
                {"mods": [_lock_mod("create")]},
            )
            self.assertEqual(check_lockfile.main([tmp]), 1)

    def test_cli_missing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(check_lockfile.main([tmp]), 1)

    def test_real_repo_lockfile_is_consistent(self):
        manifest_path = REPO_ROOT / "pack" / "manifest.json"
        if not manifest_path.is_file():
            self.skipTest(f"not running inside the repo (no manifest at {manifest_path})")
        self.assertEqual(check_lockfile.main([str(REPO_ROOT)]), 0)


if __name__ == "__main__":
    unittest.main()
