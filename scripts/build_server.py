#!/usr/bin/env python3
"""Download mods from pack/mods.lock.json into server/mods/ and sync config/kubejs overrides."""
import hashlib
import json
import shutil
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCKFILE = ROOT / "pack" / "mods.lock.json"
SERVER = ROOT / "server"
UA = {"User-Agent": "vanilla-plus-plus/0.1 (+github.com/gunnarhovik327)"}


def sha1_of(path: Path) -> str:
    h = hashlib.sha1()
    h.update(path.read_bytes())
    return h.hexdigest()


def main():
    lock = json.loads(LOCKFILE.read_text())
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

    print("server/ is up to date")


if __name__ == "__main__":
    main()
