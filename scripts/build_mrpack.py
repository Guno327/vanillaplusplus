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

CurseForge-sourced mods (ftb-library/teams/quests/chunks) work here the same
as any Modrinth mod: mods.lock.json already stores a plain HTTPS download
URL (the direct CDN link, see resolve_mods.py's docstring) and hashes for
them, and Prism just needs *a* working URL + hash, not specifically a
Modrinth one.
"""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCKFILE = ROOT / "pack" / "mods.lock.json"
VERSION_FILE = ROOT / "pack" / "VERSION"
PACK_NAME = "Vanilla++"
PACK_VERSION = VERSION_FILE.read_text().strip()
OUT_FILE = ROOT / f"vanilla-plus-plus-client-{PACK_VERSION}.mrpack"
PACK_SUMMARY = "A from-scratch Create-centric RPG modpack: tiered progression, RPG leveling, economy/marketplace, quests, teams/claims, combat/magic variety, mob scaling, dungeons, and space travel. Client bundle - see the matching vanilla-plus-plus-server-*.zip for the dedicated server."
NEOFORGE_VERSION = "21.1.235"

OVERRIDE_DIRS = ("config", "kubejs", "defaultconfigs")


def env_for(side: str) -> dict:
    if side == "client":
        return {"client": "required", "server": "unsupported"}
    if side == "server":
        return {"client": "unsupported", "server": "required"}
    return {"client": "required", "server": "required"}


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

    for mod in lock["mods"]:
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
    print(f"wrote {OUT_FILE} ({len(index['files'])} mods, {size_mb:.2f} MB, sha1={sha1})")


if __name__ == "__main__":
    main()
