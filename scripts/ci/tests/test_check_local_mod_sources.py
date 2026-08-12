import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_local_mod_sources  # noqa: E402
import local_mod_source_hash  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _build_local_mod(root, slug, jar_bytes=b"PK\x03\x04 fake jar bytes"):
    """Lay out a root/mods-src/<slug>/ source tree + a root/mods-src/<slug>/
    build/libs/<slug>.jar, matching this repo's real local-mod convention,
    and return (mod_dir, lock_entry) with a lock entry that's internally
    consistent (source_sha256/hashes.sha1 both correct for what's on disk)."""
    root = Path(root)
    mod_dir = root / "mods-src" / slug
    (mod_dir / "src" / "main" / "java").mkdir(parents=True)
    (mod_dir / "src" / "main" / "java" / "Foo.java").write_text("class Foo {}\n", encoding="utf-8")
    (mod_dir / "build.gradle").write_text("// build\n", encoding="utf-8")

    libs_dir = mod_dir / "build" / "libs"
    libs_dir.mkdir(parents=True)
    jar_path = libs_dir / f"{slug}-1.0.0.jar"
    jar_path.write_bytes(jar_bytes)

    local_path = str(jar_path.relative_to(root)).replace("\\", "/")
    entry = {
        "slug": slug,
        "local_path": local_path,
        "hashes": {
            "sha1": hashlib.sha1(jar_bytes).hexdigest(),
            "sha512": hashlib.sha512(jar_bytes).hexdigest(),
        },
        "source_sha256": local_mod_source_hash.fingerprint(mod_dir),
        "filesize": len(jar_bytes),
    }
    return mod_dir, entry


class CheckLocalModSourcesLogicTest(unittest.TestCase):
    def test_well_formed_entry_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, entry = _build_local_mod(root, "somemod")
            errors = check_local_mod_sources.check_local_mod_sources({"mods": [entry]}, root)
            self.assertEqual(errors, [])

    def test_no_local_path_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = {"slug": "remote-mod", "hashes": {"sha1": "a" * 40, "sha512": "b" * 128}}
            errors = check_local_mod_sources.check_local_mod_sources({"mods": [entry]}, root)
            self.assertEqual(errors, [])

    def test_source_sha256_without_local_path_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry = {"slug": "weird-mod", "source_sha256": "a" * 64}
            errors = check_local_mod_sources.check_local_mod_sources({"mods": [entry]}, root)
            self.assertTrue(any("weird-mod" in e and "no 'local_path'" in e for e in errors))

    def test_missing_jar_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mod_dir, entry = _build_local_mod(root, "somemod")
            (root / entry["local_path"]).unlink()
            errors = check_local_mod_sources.check_local_mod_sources({"mods": [entry]}, root)
            self.assertTrue(any("somemod" in e and "not found" in e and "resolve_mods.py" in e for e in errors))

    def test_sha1_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mod_dir, entry = _build_local_mod(root, "somemod")
            entry["hashes"]["sha1"] = "0" * 40  # wrong
            errors = check_local_mod_sources.check_local_mod_sources({"mods": [entry]}, root)
            self.assertTrue(any("somemod" in e and "hashes.sha1" in e and "resolve_mods.py" in e for e in errors))

    def test_missing_source_sha256_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mod_dir, entry = _build_local_mod(root, "somemod")
            del entry["source_sha256"]
            errors = check_local_mod_sources.check_local_mod_sources({"mods": [entry]}, root)
            self.assertTrue(any("somemod" in e and "missing 'source_sha256'" in e and "resolve_mods.py" in e for e in errors))

    def test_stale_source_sha256_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mod_dir, entry = _build_local_mod(root, "somemod")
            # Edit source WITHOUT rebuilding the jar or re-pinning - the
            # exact drift GitHub #198 is about.
            (mod_dir / "src" / "main" / "java" / "Foo.java").write_text(
                "class Foo { int bugfix; }\n", encoding="utf-8")
            errors = check_local_mod_sources.check_local_mod_sources({"mods": [entry]}, root)
            self.assertTrue(any("somemod" in e and "drifted" in e and "resolve_mods.py" in e for e in errors))


class CheckLocalModSourcesCliTest(unittest.TestCase):
    def _write_lock(self, root, mods):
        pack = Path(root) / "pack"
        pack.mkdir(parents=True, exist_ok=True)
        (pack / "mods.lock.json").write_text(json.dumps({"mods": mods}), encoding="utf-8")

    def test_cli_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, entry = _build_local_mod(root, "somemod")
            self._write_lock(root, [entry])
            self.assertEqual(check_local_mod_sources.main([str(root)]), 0)

    def test_cli_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, entry = _build_local_mod(root, "somemod")
            del entry["source_sha256"]
            self._write_lock(root, [entry])
            self.assertEqual(check_local_mod_sources.main([str(root)]), 1)

    def test_cli_missing_lockfile(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(check_local_mod_sources.main([tmp]), 1)

    def test_real_repo_local_mods_are_consistent(self):
        lock_path = REPO_ROOT / "pack" / "mods.lock.json"
        if not lock_path.is_file():
            self.skipTest(f"not running inside the repo (no lockfile at {lock_path})")
        self.assertEqual(check_local_mod_sources.main([str(REPO_ROOT)]), 0)


if __name__ == "__main__":
    unittest.main()
