#!/usr/bin/env python3
"""Standalone third-party mod installer, SHIPPED INSIDE the server release
zip (see scripts/build_server_bundle.py) alongside a trimmed
server-mods.lock.json.

GitHub #141: the released server distribution no longer bundles third-party
mod jars directly -- many of the 113 mods this pack installs are under
all-rights-reserved/custom licenses that don't clearly permit
redistribution (see THIRD_PARTY.md in the source repo). Instead this
script downloads each mod straight from its own origin (Modrinth CDN or
CurseForge CDN, whichever `server-mods.lock.json` points at) and verifies
it against the pinned sha1 before use -- the same URL+hash model the
client `.mrpack` has always used.

This file is intentionally self-contained (stdlib only, no imports from any
other file in this repo) since it ships standalone inside the release zip,
divorced from the rest of the source tree. Run it once after extracting the
zip and before first boot:

    python3 install_mods.py

Idempotent: re-running only (re)downloads mods whose jar is missing or
whose sha1 doesn't match the pin -- safe to run again after a partial/failed
run, or after swapping in a newer release zip with an updated
server-mods.lock.json.
"""
import hashlib
import json
import shutil
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOCKFILE = HERE / "server-mods.lock.json"
MODS_DIR = HERE / "mods"
UA = {"User-Agent": "vanilla-plus-plus-install-mods/1.0 (+github.com/Guno327/vanillaplusplus)"}


def sha1_of(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, timeout: int = 300) -> None:
    """Download url to dest via a .part temp file, so a killed/failed
    download never leaves a file at `dest` that looks complete."""
    part = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r, open(part, "wb") as f:
        shutil.copyfileobj(r, f)
    part.replace(dest)


def main() -> int:
    if not LOCKFILE.is_file():
        sys.stderr.write(
            f"install_mods.py: {LOCKFILE} not found -- run this script from "
            "inside the extracted server release zip, next to run.sh\n"
        )
        return 1

    lock = json.loads(LOCKFILE.read_text())
    mods = lock["mods"]
    MODS_DIR.mkdir(exist_ok=True)

    ok = 0
    downloaded = 0
    failed = []
    for mod in mods:
        dest = MODS_DIR / mod["filename"]
        if dest.exists() and sha1_of(dest) == mod["hashes"]["sha1"]:
            print(f"ok       {mod['filename']}")
            ok += 1
            continue
        print(f"download {mod['filename']}")
        try:
            download(mod["url"], dest)
        except Exception as e:  # noqa: BLE001 -- best-effort installer, report and continue
            sys.stderr.write(f"install_mods.py: failed to download {mod['filename']}: {e}\n")
            failed.append(mod["filename"])
            continue
        actual = sha1_of(dest)
        if actual != mod["hashes"]["sha1"]:
            dest.unlink(missing_ok=True)
            sys.stderr.write(
                f"install_mods.py: checksum mismatch for {mod['filename']}: "
                f"expected sha1 {mod['hashes']['sha1']}, got {actual} -- "
                "removed, refusing to keep an unverified jar\n"
            )
            failed.append(mod["filename"])
            continue
        downloaded += 1

    print(f"\ninstall_mods.py: {ok} already present, {downloaded} downloaded, {len(failed)} failed")
    if failed:
        sys.stderr.write(
            "install_mods.py: FAILED to install: " + ", ".join(failed) + "\n"
            "Re-run this script to retry (safe/idempotent) -- the server will "
            "not boot correctly with mods missing.\n"
        )
        return 1

    print("install_mods.py: all mods present and verified in ./mods/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
