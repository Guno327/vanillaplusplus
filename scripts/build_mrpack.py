#!/usr/bin/env python3
"""Build a Prism Launcher-importable .mrpack from pack/mods.lock.json +
pack/config, pack/kubejs, pack/defaultconfigs.

.mrpack format (Modrinth's pack format, what Prism Launcher imports):
a zip with modrinth.index.json at the root (mod list with direct download
URLs + hashes, matching mods.lock.json's own schema closely enough that this
script is mostly just reshaping it) plus an overrides/ folder for anything
that isn't a downloadable mod jar - our config/kubejs/defaultconfigs, which
matter to both the client (KubeJS's puffish_skills UI, client-side configs)
and a server. server.properties/user_jvm_args.txt are deliberately left out
of the mrpack - those are server-only concerns with no meaning for a Prism
client instance, and are covered separately by build_server.py.

CurseForge-sourced mods (ftb-library/teams/quests/chunks, alltheores,
allthemodium) are NOT interchangeable with Modrinth mods here, despite
mods.lock.json storing the same shape of URL+hashes for everything: Prism
(and any mrpack-*building* client) is happy with a plain HTTPS URL, but
Modrinth's own hosting API rejects a *version upload* whose
modrinth.index.json references a download host outside its allowlist
(cdn.modrinth.com only - confirmed against the real API: "File download
source is not from allowed sources" on every forgecdn.net entry). So for
those specific mods we cannot list them in `files[]` at all if this
.mrpack is ever uploaded to Modrinth (see publish-modrinth.yml) - instead
we download the jar ourselves (hash-verified against mods.lock.json, same
pattern as build_server.py) and bundle it directly under overrides/mods/,
same as the config/kubejs/defaultconfigs overrides below. Prism installs
overrides/ files verbatim, so the end state for the player is identical
either way; only the delivery mechanism differs.
"""
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
LOCKFILE = ROOT / "pack" / "mods.lock.json"
VERSION_FILE = ROOT / "pack" / "VERSION"
PACK_NAME = "Vanilla++"
PACK_VERSION = VERSION_FILE.read_text().strip()
OUT_FILE = ROOT / f"vanilla-plus-plus-client-{PACK_VERSION}.mrpack"
PACK_SUMMARY = "A from-scratch Create-centric RPG modpack: tiered progression, RPG leveling, economy/marketplace, quests, teams/claims, combat/magic variety, mob scaling, dungeons, and space travel. Client bundle - see the matching vanilla-plus-plus-server-*.zip for the dedicated server."
NEOFORGE_VERSION = "21.1.235"
MODRINTH_CDN_HOST = "cdn.modrinth.com"
MOD_CACHE = ROOT / "pack" / "mods"
UA = {"User-Agent": "vanilla-plus-plus/0.1 (+github.com/gunnarhovik327)"}

OVERRIDE_DIRS = ("config", "kubejs", "defaultconfigs")


def sha1_of(path: Path) -> str:
    h = hashlib.sha1()
    h.update(path.read_bytes())
    return h.hexdigest()


def fetch_bundled_mod(mod: dict) -> Path:
    """Download (or reuse a hash-verified cached copy of) a non-Modrinth
    mod jar so it can be embedded under overrides/mods/ instead of
    referenced by external URL."""
    MOD_CACHE.mkdir(parents=True, exist_ok=True)
    dest = MOD_CACHE / mod["filename"]
    if dest.exists() and sha1_of(dest) == mod["hashes"]["sha1"]:
        return dest
    req = urllib.request.Request(mod["url"], headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        f.write(r.read())
    actual = sha1_of(dest)
    if actual != mod["hashes"]["sha1"]:
        raise SystemExit(f"hash mismatch for {mod['filename']}: expected {mod['hashes']['sha1']} got {actual}")
    return dest


def env_for(side: str) -> dict:
    if side == "client":
        return {"client": "required", "server": "unsupported"}
    if side == "server":
        return {"client": "unsupported", "server": "required"}
    return {"client": "required", "server": "required"}


def classify_mods(mods: list) -> tuple:
    """Split lockfile mod entries into (downloadable, bundled): mods hosted
    on Modrinth's own CDN can be referenced by URL in modrinth.index.json;
    anything else must be bundled under overrides/mods/ instead, since
    Modrinth's upload API rejects non-allowlisted download hosts. See the
    module docstring for why this distinction exists at all."""
    downloadable, bundled = [], []
    for mod in mods:
        if urlparse(mod["url"]).hostname == MODRINTH_CDN_HOST:
            downloadable.append(mod)
        else:
            bundled.append(mod)
    return downloadable, bundled


def main():
    lock = json.loads(LOCKFILE.read_text())

    index = {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": PACK_VERSION,
        "name": PACK_NAME,
        "summary": PACK_SUMMARY,
        "files": [],
        "dependencies": {
            "minecraft": lock["minecraft"],
            "neoforge": NEOFORGE_VERSION,
        },
    }

    downloadable, bundled = classify_mods(lock["mods"])
    for mod in downloadable:
        index["files"].append({
            "path": f"mods/{mod['filename']}",
            "hashes": mod["hashes"],
            "env": env_for(mod["side"]),
            "downloads": [mod["url"]],
            "fileSize": mod["filesize"],
        })

    if OUT_FILE.exists():
        OUT_FILE.unlink()

    with zipfile.ZipFile(OUT_FILE, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("modrinth.index.json", json.dumps(index, indent=2))
        for mod in bundled:
            jar = fetch_bundled_mod(mod)
            z.write(jar, f"overrides/mods/{mod['filename']}")
        for sub in OVERRIDE_DIRS:
            src = ROOT / "pack" / sub
            if not src.exists():
                continue
            for path in src.rglob("*"):
                if path.is_file():
                    arcname = f"overrides/{sub}/{path.relative_to(src)}"
                    z.write(path, arcname)

    size_mb = OUT_FILE.stat().st_size / (1024 * 1024)
    sha1 = hashlib.sha1(OUT_FILE.read_bytes()).hexdigest()
    print(f"wrote {OUT_FILE} ({len(index['files'])} downloaded + {len(bundled)} bundled mods, {size_mb:.2f} MB, sha1={sha1})")


if __name__ == "__main__":
    main()
