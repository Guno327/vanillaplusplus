import hashlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# build_local_mods.py lives in scripts/, one level above scripts/ci/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import build_local_mods  # noqa: E402


def _mod_dir(tmp, version="8.10"):
    mod_dir = Path(tmp) / "vppintegration"
    (mod_dir / "gradle" / "wrapper").mkdir(parents=True)
    (mod_dir / "gradle" / "wrapper" / "gradle-wrapper.properties").write_text(
        "distributionUrl=https\\://services.gradle.org/distributions/"
        f"gradle-{version}-bin.zip\n"
    )
    return mod_dir


class _FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()
        return False


class EnsureGradleWrapperJarChecksumTest(unittest.TestCase):
    def test_matching_checksum_writes_jar(self):
        payload = b"PK\x03\x04 pretend wrapper jar bytes"
        digest = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            mod_dir = _mod_dir(tmp)
            with mock.patch.dict(
                build_local_mods.GRADLE_WRAPPER_JAR_SHA256,
                {"8.10.0": digest},
                clear=False,
            ), mock.patch(
                "build_local_mods.urllib.request.urlopen",
                return_value=_FakeResp(payload),
            ):
                build_local_mods.ensure_gradle_wrapper_jar(mod_dir)
            jar = mod_dir / "gradle" / "wrapper" / "gradle-wrapper.jar"
            self.assertTrue(jar.is_file())
            self.assertEqual(jar.read_bytes(), payload)

    def test_mismatched_checksum_refuses(self):
        payload = b"tampered bytes"
        with tempfile.TemporaryDirectory() as tmp:
            mod_dir = _mod_dir(tmp)
            with mock.patch.dict(
                build_local_mods.GRADLE_WRAPPER_JAR_SHA256,
                {"8.10.0": "0" * 64},
                clear=False,
            ), mock.patch(
                "build_local_mods.urllib.request.urlopen",
                return_value=_FakeResp(payload),
            ):
                with self.assertRaises(SystemExit) as ctx:
                    build_local_mods.ensure_gradle_wrapper_jar(mod_dir)
            self.assertIn("SHA-256 mismatch", str(ctx.exception))
            # nothing written on mismatch
            self.assertFalse(
                (mod_dir / "gradle" / "wrapper" / "gradle-wrapper.jar").exists()
            )

    def test_unpinned_version_refuses_without_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod_dir = _mod_dir(tmp, version="9.99")
            with mock.patch.dict(
                build_local_mods.GRADLE_WRAPPER_JAR_SHA256, {}, clear=True
            ), mock.patch(
                "build_local_mods.urllib.request.urlopen",
                side_effect=AssertionError("must not download an unpinned version"),
            ):
                with self.assertRaises(SystemExit) as ctx:
                    build_local_mods.ensure_gradle_wrapper_jar(mod_dir)
            self.assertIn("no pinned", str(ctx.exception))

    def test_existing_jar_is_left_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            mod_dir = _mod_dir(tmp)
            jar = mod_dir / "gradle" / "wrapper" / "gradle-wrapper.jar"
            jar.write_bytes(b"already here")
            with mock.patch(
                "build_local_mods.urllib.request.urlopen",
                side_effect=AssertionError("must not re-download an existing jar"),
            ):
                build_local_mods.ensure_gradle_wrapper_jar(mod_dir)
            self.assertEqual(jar.read_bytes(), b"already here")


if __name__ == "__main__":
    unittest.main()
