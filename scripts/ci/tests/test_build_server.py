"""Fast-tier, stdlib-only, no-network unit tests for build_server.py's
NeoForge installer bootstrap (GitHub #64). Downloads and subprocess calls
are stubbed - these tests never touch the network or spawn a real JVM.
"""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import build_server  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def _pin(**overrides):
    pin = {
        "version": "21.1.235",
        "url": "https://maven.neoforged.net/releases/net/neoforged/neoforge/21.1.235/neoforge-21.1.235-installer.jar",
        "filename": "neoforge-21.1.235-installer.jar",
        "hashes": {
            "sha256": "a" * 64,
            "sha512": "b" * 128,
        },
        "filesize": 12345,
    }
    pin.update(overrides)
    return pin


class TestPinShape(unittest.TestCase):
    """The pin itself, as it actually lives in pack/mods.lock.json."""

    def test_real_lockfile_has_loader_installer_pin(self):
        lock = json.loads((REPO_ROOT / "pack" / "mods.lock.json").read_text())
        self.assertIn("loader_installer", lock)
        pin = lock["loader_installer"]
        for field in ("version", "url", "filename", "hashes"):
            self.assertIn(field, pin, f"loader_installer missing {field!r}")
        self.assertIn("sha256", pin["hashes"])
        self.assertTrue(pin["url"].startswith("https://"))
        self.assertIn(pin["version"], pin["url"])
        self.assertIn(pin["version"], pin["filename"])

    def test_real_pin_version_matches_pack_toml(self):
        import tomllib

        lock = json.loads((REPO_ROOT / "pack" / "mods.lock.json").read_text())
        toml = tomllib.loads((REPO_ROOT / "pack" / "pack.toml").read_text())
        self.assertEqual(
            lock["loader_installer"]["version"],
            toml["versions"]["neoforge"],
            "pack/mods.lock.json loader_installer.version has drifted from "
            "pack/pack.toml [versions].neoforge - single source of truth violated",
        )


class TestEnsureNeoforgeInstalled(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.server = self.root / "server"
        self.tools = self.root / ".tools"
        self.java_bin = self.tools / "jdk-21.0.11+10" / "bin" / "java"
        self.java_bin.parent.mkdir(parents=True)
        self.java_bin.write_text("#!/bin/sh\n")

        patcher_root = mock.patch.object(build_server, "ROOT", self.root)
        patcher_server = mock.patch.object(build_server, "SERVER", self.server)
        patcher_tools = mock.patch.object(build_server, "TOOLS_DIR", self.tools)
        patcher_jdk = mock.patch.object(build_server, "JDK_JAVA_BIN", self.java_bin)
        patcher_toml = mock.patch.object(build_server, "PACK_TOML", self.root / "nonexistent.toml")
        for p in (patcher_root, patcher_server, patcher_tools, patcher_jdk, patcher_toml):
            p.start()
            self.addCleanup(p.stop)

    def _write_installed_artifacts(self, version="21.1.235"):
        lib_dir = self.server / "libraries" / "net" / "neoforged" / "neoforge" / version
        lib_dir.mkdir(parents=True)
        (self.server / "run.sh").write_text("#!/bin/sh\n")
        (lib_dir / "unix_args.txt").write_text("...\n")
        (lib_dir / f"neoforge-{version}-server.jar").write_bytes(b"fake jar")

    def test_missing_pin_hard_fails(self):
        with self.assertRaises(SystemExit):
            build_server.ensure_neoforge_installed({})

    def test_missing_artifacts_detected_and_triggers_install(self):
        pin = _pin()
        lock = {"loader_installer": pin}

        installer_bytes = b"fake installer jar contents"
        real_sha256 = hashlib.sha256(installer_bytes).hexdigest()
        pin["hashes"]["sha256"] = real_sha256

        def fake_download(url, dest, timeout=300):
            dest.write_bytes(installer_bytes)

        ran = {}

        def fake_run(cmd, cwd=None, capture_output=None, text=None):
            ran["cmd"] = cmd
            # Simulate the installer having done its job.
            self._write_installed_artifacts(pin["version"])
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(build_server, "_download", fake_download), \
             mock.patch.object(build_server.subprocess, "run", fake_run):
            build_server.ensure_neoforge_installed(lock)

        self.assertTrue(build_server.neoforge_already_installed(pin["version"]))
        self.assertIn(str(self.java_bin), ran["cmd"])
        self.assertIn("--installServer", ran["cmd"])

    def test_checksum_mismatch_aborts_before_install(self):
        pin = _pin()
        lock = {"loader_installer": pin}

        def fake_download(url, dest, timeout=300):
            dest.write_bytes(b"not the real jar, wrong checksum")

        with mock.patch.object(build_server, "_download", fake_download), \
             mock.patch.object(build_server.subprocess, "run") as run_mock:
            with self.assertRaises(SystemExit) as ctx:
                build_server.ensure_neoforge_installed(lock)

        self.assertIn("checksum mismatch", str(ctx.exception))
        run_mock.assert_not_called()
        # the bad download must not be left behind under a trusted name
        self.assertFalse((self.tools / pin["filename"]).exists())
        self.assertFalse(self.server.exists() and any(self.server.iterdir()))

    def test_idempotent_noop_when_already_installed(self):
        pin = _pin()
        lock = {"loader_installer": pin}
        self._write_installed_artifacts(pin["version"])

        with mock.patch.object(build_server, "_download") as download_mock, \
             mock.patch.object(build_server.subprocess, "run") as run_mock:
            build_server.ensure_neoforge_installed(lock)

        download_mock.assert_not_called()
        run_mock.assert_not_called()

    def test_cached_installer_with_matching_checksum_is_reused_not_redownloaded(self):
        pin = _pin()
        lock = {"loader_installer": pin}

        installer_bytes = b"cached installer jar"
        pin["hashes"]["sha256"] = hashlib.sha256(installer_bytes).hexdigest()
        (self.tools / pin["filename"]).write_bytes(installer_bytes)

        def fake_run(cmd, cwd=None, capture_output=None, text=None):
            self._write_installed_artifacts(pin["version"])
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(build_server, "_download") as download_mock, \
             mock.patch.object(build_server.subprocess, "run", fake_run):
            build_server.ensure_neoforge_installed(lock)

        download_mock.assert_not_called()

    def test_missing_jdk_hard_fails(self):
        self.java_bin.unlink()
        pin = _pin()
        lock = {"loader_installer": pin}

        def fake_download(url, dest, timeout=300):
            dest.write_bytes(b"x")

        with mock.patch.object(build_server, "_download", fake_download):
            with self.assertRaises(SystemExit) as ctx:
                build_server.ensure_neoforge_installed(lock)
        self.assertIn("JDK", str(ctx.exception))

    def test_installer_success_but_artifacts_still_missing_hard_fails(self):
        pin = _pin()
        lock = {"loader_installer": pin}

        def fake_download(url, dest, timeout=300):
            dest.write_bytes(b"x" * 10)

        pin["hashes"]["sha256"] = hashlib.sha256(b"x" * 10).hexdigest()

        def fake_run(cmd, cwd=None, capture_output=None, text=None):
            # Installer claims success but doesn't actually write artifacts.
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(build_server, "_download", fake_download), \
             mock.patch.object(build_server.subprocess, "run", fake_run):
            with self.assertRaises(SystemExit) as ctx:
                build_server.ensure_neoforge_installed(lock)
        self.assertIn("still", str(ctx.exception))

    def test_installer_nonzero_exit_hard_fails(self):
        pin = _pin()
        lock = {"loader_installer": pin}

        def fake_download(url, dest, timeout=300):
            dest.write_bytes(b"x" * 10)

        pin["hashes"]["sha256"] = hashlib.sha256(b"x" * 10).hexdigest()

        def fake_run(cmd, cwd=None, capture_output=None, text=None):
            return mock.Mock(returncode=1, stdout="boom", stderr="err")

        with mock.patch.object(build_server, "_download", fake_download), \
             mock.patch.object(build_server.subprocess, "run", fake_run):
            with self.assertRaises(SystemExit) as ctx:
                build_server.ensure_neoforge_installed(lock)
        self.assertIn("failed", str(ctx.exception))

    def test_version_mismatch_against_pack_toml_hard_fails(self):
        toml_path = self.root / "pack.toml"
        toml_path.write_text('[versions]\nneoforge = "999.0.0"\n')
        with mock.patch.object(build_server, "PACK_TOML", toml_path):
            pin = _pin()
            lock = {"loader_installer": pin}
            with self.assertRaises(SystemExit) as ctx:
                build_server.ensure_neoforge_installed(lock)
        self.assertIn("mismatch", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
