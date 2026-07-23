#!/usr/bin/env python3
"""Download mods from pack/mods.lock.json into server/mods/ and sync
config/kubejs overrides. Also bootstraps the NeoForge server install itself
(run.sh, run.bat, libraries/) if it's missing, so a fresh checkout of this
repo can produce a bootable server without any hand-run, uncaptured
installer step (GitHub #64).
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tomllib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCKFILE = ROOT / "pack" / "mods.lock.json"
PACK_TOML = ROOT / "pack" / "pack.toml"
SERVER = ROOT / "server"
TOOLS_DIR = ROOT / ".tools"
JDK_JAVA_BIN = TOOLS_DIR / "jdk-21.0.11+10" / "bin" / "java"
UA = {"User-Agent": "vanilla-plus-plus/0.1 (+github.com/gunnarhovik327)"}


def sha1_of(path: Path) -> str:
    h = hashlib.sha1()
    h.update(path.read_bytes())
    return h.hexdigest()


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: Path, timeout: int = 300) -> None:
    """Download url to dest via a .part temp file, so a killed/failed
    download never leaves a file at `dest` that looks complete."""
    part = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r, open(part, "wb") as f:
        shutil.copyfileobj(r, f)
    part.replace(dest)


def neoforge_artifact_paths(version: str):
    """The set of files that must exist for a NeoForge server install of
    `version` to be considered present. Ground-truthed against a real
    --installServer run: the installer writes run.sh/run.bat at the
    server root and the patched server jar + arg files under
    libraries/net/neoforged/neoforge/<version>/."""
    lib_dir = SERVER / "libraries" / "net" / "neoforged" / "neoforge" / version
    return [
        SERVER / "run.sh",
        lib_dir / "unix_args.txt",
        lib_dir / f"neoforge-{version}-server.jar",
    ]


def neoforge_already_installed(version: str) -> bool:
    return all(p.is_file() for p in neoforge_artifact_paths(version))


def ensure_neoforge_installed(lock: dict) -> None:
    """Idempotent: if server/run.sh + server/libraries/.../<version>/ are
    already present for the pinned version, does nothing (no re-download,
    no re-run of the installer). Otherwise fetches the checksum-pinned
    installer jar and runs --installServer with the repo's .tools JDK."""
    pin = lock.get("loader_installer")
    if not pin:
        raise SystemExit(
            "pack/mods.lock.json is missing a 'loader_installer' pin - "
            "cannot bootstrap the NeoForge server install"
        )

    version = pin["version"]

    # Single source of truth check: pack/pack.toml's [versions].neoforge
    # is the pre-existing pin for the loader version (predates #64); the
    # lockfile's loader_installer.version must never drift from it.
    if PACK_TOML.is_file():
        pack_versions = tomllib.loads(PACK_TOML.read_text()).get("versions", {})
        toml_version = pack_versions.get("neoforge")
        if toml_version and toml_version != version:
            raise SystemExit(
                f"version mismatch: pack/mods.lock.json loader_installer.version "
                f"({version}) != pack/pack.toml [versions].neoforge ({toml_version}) "
                "- these must be kept in sync, fix one of them"
            )

    if neoforge_already_installed(version):
        print(f"ok      neoforge {version} server install already present")
        return

    print(f"neoforge {version} server install missing/incomplete, bootstrapping")

    if not JDK_JAVA_BIN.is_file():
        raise SystemExit(
            f"cannot bootstrap NeoForge: no JDK at {JDK_JAVA_BIN} - this repo "
            "expects a .tools/ JDK to already be provisioned (see HANDOFF.md)"
        )

    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    installer_path = TOOLS_DIR / pin["filename"]

    if installer_path.is_file() and sha256_of(installer_path) == pin["hashes"]["sha256"]:
        print(f"ok      cached installer {pin['filename']} (checksum verified)")
    else:
        print(f"download {pin['url']}")
        _download(pin["url"], installer_path)
        actual = sha256_of(installer_path)
        expected = pin["hashes"]["sha256"]
        if actual != expected:
            installer_path.unlink(missing_ok=True)
            raise SystemExit(
                f"checksum mismatch for NeoForge installer {pin['filename']}: "
                f"expected sha256 {expected}, got {actual} - refusing to run an "
                "unverified installer jar, download removed"
            )
        print(f"ok      downloaded and verified {pin['filename']}")

    SERVER.mkdir(parents=True, exist_ok=True)
    print(f"install  running --installServer with {JDK_JAVA_BIN}")
    result = subprocess.run(
        [str(JDK_JAVA_BIN), "-jar", str(installer_path), "--installServer", str(SERVER)],
        cwd=str(SERVER),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout[-4000:])
        sys.stderr.write(result.stderr[-4000:])
        raise SystemExit(f"NeoForge --installServer failed (exit {result.returncode}) - see output above")

    if not neoforge_already_installed(version):
        missing = [str(p) for p in neoforge_artifact_paths(version) if not p.is_file()]
        raise SystemExit(
            "NeoForge installer reported success but expected artifacts are still "
            f"missing: {missing}"
        )
    print(f"ok      neoforge {version} server install verified")


def main():
    lock = json.loads(LOCKFILE.read_text())

    ensure_neoforge_installed(lock)

    mods_dir = SERVER / "mods"
    mods_dir.mkdir(parents=True, exist_ok=True)

    keep = set()
    for mod in lock["mods"]:
        if mod["side"] == "client":
            continue
        dest = mods_dir / mod["filename"]
        keep.add(dest.name)
        if dest.exists() and sha1_of(dest) == mod["hashes"]["sha1"]:
            print(f"ok      {mod['filename']}")
            continue
        if mod.get("local_path"):
            # GitHub #67: this pack's own hand-rolled mods (mods-src/<modid>/)
            # have no remote URL - copy the already-built jar the lockfile's
            # hash was taken from instead of downloading it.
            src = ROOT / mod["local_path"]
            if not src.is_file():
                raise SystemExit(
                    f"{mod['slug']}: local_path {mod['local_path']!r} not found - "
                    f"build it first (see mods-src/{mod['slug']}/README.md)"
                )
            print(f"copy     {mod['filename']} (local)")
            shutil.copyfile(src, dest)
        else:
            print(f"download {mod['filename']}")
            req = urllib.request.Request(mod["url"], headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
                shutil.copyfileobj(r, f)
        actual = sha1_of(dest)
        if actual != mod["hashes"]["sha1"]:
            raise SystemExit(f"hash mismatch for {mod['filename']}: expected {mod['hashes']['sha1']} got {actual}")

    # remove stale jars no longer in the lockfile
    for existing in mods_dir.glob("*.jar"):
        if existing.name not in keep:
            print(f"remove   {existing.name}")
            existing.unlink()

    for sub in ("config", "kubejs", "defaultconfigs"):
        src = ROOT / "pack" / sub
        if src.exists():
            dst = SERVER / sub
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"synced   {sub}/")

    # Performance-tuned JVM args / server.properties (Phase 9) - tracked
    # source files, not the gitignored server/ copies, so the tuning survives
    # a fresh build_server.py run on another machine.
    for filename in ("user_jvm_args.txt", "server.properties"):
        src = ROOT / "pack" / filename
        if src.exists():
            shutil.copyfile(src, SERVER / filename)
            print(f"synced   {filename}")

    print("server/ is up to date")


if __name__ == "__main__":
    main()
