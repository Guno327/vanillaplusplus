import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import local_mod_source_hash  # noqa: E402


def _mod_tree(root, extra_files=None):
    """A minimal mods-src/<modid>/-shaped tree: a couple of src/** files plus
    the top-level build.gradle this module also hashes."""
    mod_dir = Path(root) / "somemod"
    (mod_dir / "src" / "main" / "java").mkdir(parents=True)
    (mod_dir / "src" / "main" / "java" / "Foo.java").write_text("class Foo {}\n", encoding="utf-8")
    (mod_dir / "src" / "main" / "resources").mkdir(parents=True)
    (mod_dir / "src" / "main" / "resources" / "mod.toml").write_text("id=somemod\n", encoding="utf-8")
    (mod_dir / "build.gradle").write_text("// build\n", encoding="utf-8")
    (mod_dir / "gradle.properties").write_text("version=1.0\n", encoding="utf-8")
    if extra_files:
        for rel, content in extra_files.items():
            p = mod_dir / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
    return mod_dir


class FingerprintTest(unittest.TestCase):
    def test_deterministic_across_repeated_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod_dir = _mod_tree(tmp)
            a = local_mod_source_hash.fingerprint(mod_dir)
            b = local_mod_source_hash.fingerprint(mod_dir)
            self.assertEqual(a, b)

    def test_unchanged_by_touching_mtimes(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod_dir = _mod_tree(tmp)
            before = local_mod_source_hash.fingerprint(mod_dir)
            # Bump every file's mtime without touching content.
            future = time.time() + 3600
            for p in mod_dir.rglob("*"):
                if p.is_file():
                    os.utime(p, (future, future))
            after = local_mod_source_hash.fingerprint(mod_dir)
            self.assertEqual(before, after)

    def test_changes_when_content_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod_dir = _mod_tree(tmp)
            before = local_mod_source_hash.fingerprint(mod_dir)
            (mod_dir / "src" / "main" / "java" / "Foo.java").write_text("class Foo { int x; }\n", encoding="utf-8")
            after = local_mod_source_hash.fingerprint(mod_dir)
            self.assertNotEqual(before, after)

    def test_changes_when_file_renamed(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod_dir = _mod_tree(tmp)
            before = local_mod_source_hash.fingerprint(mod_dir)
            src = mod_dir / "src" / "main" / "java" / "Foo.java"
            dst = mod_dir / "src" / "main" / "java" / "Bar.java"
            src.rename(dst)
            after = local_mod_source_hash.fingerprint(mod_dir)
            self.assertNotEqual(before, after)

    def test_ignores_files_under_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod_dir = _mod_tree(tmp)
            before = local_mod_source_hash.fingerprint(mod_dir)
            build_junk = mod_dir / "src" / "main" / "build" / "generated.txt"
            build_junk.parent.mkdir(parents=True)
            build_junk.write_text("should not affect the fingerprint\n", encoding="utf-8")
            (mod_dir / "build").mkdir()
            (mod_dir / "build" / "libs").mkdir()
            (mod_dir / "build" / "libs" / "somemod-1.0.jar").write_bytes(b"PK\x03\x04fakejar")
            after = local_mod_source_hash.fingerprint(mod_dir)
            self.assertEqual(before, after)

    def test_ignores_gitignored_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod_dir = _mod_tree(tmp)
            (mod_dir / ".gitignore").write_text("run/\n", encoding="utf-8")
            before = local_mod_source_hash.fingerprint(mod_dir)
            run_junk = mod_dir / "src" / "main" / "run" / "junk.txt"
            run_junk.parent.mkdir(parents=True)
            run_junk.write_text("ignored\n", encoding="utf-8")
            after = local_mod_source_hash.fingerprint(mod_dir)
            self.assertEqual(before, after)

    def test_rename_across_files_does_not_collide(self):
        # Guards the length-prefixed framing: two different (path, content)
        # layouts that would concatenate to the same bytes under naive
        # framing must not hash equal.
        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            mod_a = _mod_tree(tmp1, extra_files={"src/main/java/ab.txt": "cd"})
            mod_b = _mod_tree(tmp2, extra_files={"src/main/java/a.txt": "bcd"})
            self.assertNotEqual(
                local_mod_source_hash.fingerprint(mod_a),
                local_mod_source_hash.fingerprint(mod_b),
            )


class SourceFilesTest(unittest.TestCase):
    def test_includes_expected_top_level_files_and_excludes_missing_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod_dir = _mod_tree(tmp)  # no settings.gradle, no libs.json
            rels = {p.relative_to(mod_dir).as_posix() for p in local_mod_source_hash.source_files(mod_dir)}
            self.assertIn("build.gradle", rels)
            self.assertIn("gradle.properties", rels)
            self.assertNotIn("settings.gradle", rels)
            self.assertIn("src/main/java/Foo.java", rels)

    def test_libs_json_included_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod_dir = _mod_tree(tmp, extra_files={"libs.json": "[]"})
            rels = {p.relative_to(mod_dir).as_posix() for p in local_mod_source_hash.source_files(mod_dir)}
            self.assertIn("libs.json", rels)


if __name__ == "__main__":
    unittest.main()
