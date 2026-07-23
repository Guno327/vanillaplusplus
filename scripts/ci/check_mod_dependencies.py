#!/usr/bin/env python3
"""Launch-time dependency check: every mod's REQUIRED dependency must be
provided by some other mod in the pack (or bundled inside one via Jar-in-Jar).

WHY THIS EXISTS (the v0.5.0 regression, 2026-07-23): #112 added
`sodium-options-api` to the CLIENT bundle, and that mod hard-requires
`reeses_sodium_options` (a well-formed `versionRange="*"` dependency) which
was never installed. NeoForge enforces that on the client and the client
crashed on startup ("Mod sodiumoptionsapi requires reeses_sodium_options").
NOTHING caught it: every automated tier (L0/L1/boot.yml) boots the DEDICATED
SERVER, and both offending mods are `side:client`, so a server boot never
loads them. This check closes that gap by statically resolving EVERY mod's
declared required dependencies against the whole installed set, so a missing
(client- or server-side) dependency fails fast instead of shipping.

WHAT COUNTS AS A REQUIRED DEP (mirroring NeoForge's own enforcement):
  - `type = "required"` (NeoForge style) OR `mandatory = true` (legacy Forge
    style) — both appear in real 1.21.1 mod tomls.
  - The dependency must be WELL-FORMED to be enforced. A block missing
    `versionRange` is malformed and NeoForge silently ignores it — this is
    exactly why `stellaris`'s `sky_aesthetics` dep (no versionRange/ordering/
    side) has never crashed the game despite being `type="required"`, while
    `reeses_sodium_options` (versionRange="*") did. We therefore only enforce
    dependencies that declare a `versionRange`. Any genuinely-tolerated
    exception can also be listed in KNOWN_UNPROVIDED_OK with a justification.

WHAT PROVIDES A modId:
  - each mod jar's own `[[mods]] modId`, PLUS every modId bundled inside it
    via Jar-in-Jar (META-INF/jarjar/*.jar, recursively — this is how Create
    ships `flywheel`/`ponder`, Xaero's ships `xaerolib`, etc.).
  - the platform ids neoforge/minecraft/forge/fml/java are always provided.

Reads the mod jars themselves (downloading+caching to pack/mods/ from the
lockfile if absent), because a mod's real, authoritative dependency list is
in its jar's neoforge.mods.toml — Modrinth's project-level dependency list
does not always match (that mismatch is what misled #112 in the first place).

Usage: python3 scripts/ci/check_mod_dependencies.py [--mods-dir DIR] [--offline]
Exit code: 0 if every required dependency is satisfied, 1 otherwise.
"""
import argparse
import io
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOCKFILE = REPO_ROOT / "pack" / "mods.lock.json"
MOD_CACHE = REPO_ROOT / "pack" / "mods"
UA = {"User-Agent": "vanilla-plus-plus-depcheck/1.0"}

# Platform / always-present modIds NeoForge itself provides.
PLATFORM_IDS = {"neoforge", "minecraft", "forge", "fml", "java", "neoforgemod"}

# Required deps that are declared but empirically NOT enforced by NeoForge,
# with the reason. Keep this list SHORT and JUSTIFIED — every entry is a mod
# shipping a broken dependency declaration that the loader tolerates.
KNOWN_UNPROVIDED_OK = {
    # stellaris' neoforge.mods.toml declares `sky_aesthetics` type="required"
    # but WITHOUT a versionRange/ordering/side - a malformed block NeoForge
    # does not enforce. Verified tolerated: the dedicated server boots clean
    # with stellaris and no sky_aesthetics (L0/L1/boot.yml), and the v0.4.0
    # client ran for hours with the same mod set. Left as documentation; the
    # versionRange rule below already exempts it, this is belt-and-braces.
    "sky_aesthetics": "stellaris declares it required but with a malformed (no versionRange) block NeoForge ignores; tolerated in-game since v0.4.0",
}


def _iter_tomls(zf):
    for n in zf.namelist():
        if n.endswith("neoforge.mods.toml") or n.endswith("mods.toml"):
            yield zf.read(n).decode("utf-8", "ignore")


def parse_mod_jar(jar_bytes):
    """Return (provided_modids:set, required_deps:list) for a mod jar,
    recursing into Jar-in-Jar bundled mods for provided ids.

    required_deps is a list of dicts: {modId, versionRange, enforced:bool}.
    A dep is `enforced` iff it is required (type=required or mandatory=true)
    AND declares a versionRange (well-formed - see module docstring)."""
    provided = set()
    required = []
    zf = zipfile.ZipFile(io.BytesIO(jar_bytes))
    for txt in _iter_tomls(zf):
        head = re.split(r"\[\[dependencies", txt)[0]
        for mid in re.findall(r'modId\s*=\s*"([^"]+)"', head):
            provided.add(mid.lower())
        for block in re.split(r"\[\[dependencies", txt)[1:]:
            mid = re.search(r'modId\s*=\s*"([^"]+)"', block)
            if not mid:
                continue
            typ = re.search(r'type\s*=\s*"([^"]+)"', block)
            mand = re.search(r"mandatory\s*=\s*(true|false)", block)
            vr = re.search(r'versionRange\s*=\s*"([^"]*)"', block)
            is_required = (typ and typ.group(1).lower() == "required") or (
                mand and mand.group(1) == "true"
            )
            if is_required:
                required.append({
                    "modId": mid.group(1).lower(),
                    "versionRange": vr.group(1) if vr else None,
                    "enforced": vr is not None,  # malformed (no versionRange) => not enforced
                })
    # Jar-in-Jar: bundled mods provide their ids too.
    for n in zf.namelist():
        if n.startswith("META-INF/jarjar/") and n.endswith(".jar"):
            try:
                p2, _ = parse_mod_jar(zf.read(n))
                provided |= p2
            except Exception:
                pass
    return provided, required


def resolve(mods):
    """mods: list of {slug, provided:set, required:list(dep dicts)}.
    Returns a list of human-readable problem strings (empty == all satisfied).
    Pure function - no I/O - so it is unit-testable with synthetic fixtures."""
    provided = set(PLATFORM_IDS)
    for m in mods:
        provided |= {p.lower() for p in m["provided"]}
    problems = []
    for m in mods:
        for dep in m["required"]:
            if not dep.get("enforced"):
                continue  # malformed (no versionRange) - NeoForge ignores it
            depid = dep["modId"].lower()
            if depid in provided:
                continue
            if depid in KNOWN_UNPROVIDED_OK:
                continue
            problems.append(
                f"{m['slug']}: REQUIRED dependency '{dep['modId']}' "
                f"(versionRange {dep['versionRange']!r}) is not provided by any "
                f"installed mod (or a Jar-in-Jar bundle) - it would fail at launch"
            )
    return problems


def _load_jar_bytes(mod, mods_dir, offline):
    """Read the mod jar from the local cache; download+cache it if missing
    (unless offline).

    GitHub #143 (mirrors #124 on dev): a "source": "local" mod (this pack's own
    hand-rolled mods-src/<modid>/ jars) has no fetchable "url" at all - its "url"
    is the repo-relative "local_path" string instead, exactly the convention
    build_server.py and build_mrpack.py already special-case. Read it directly
    off disk rather than attempting a download (its "url" is not an HTTP(S) URL,
    so urlopen would raise "unknown url type")."""
    if mod.get("local_path"):
        src = REPO_ROOT / mod["local_path"]
        if not src.is_file():
            raise FileNotFoundError(
                f"{mod['slug']}: local_path {mod['local_path']!r} not found - "
                f"build it first (cd {Path(mod['local_path']).parents[2]} && ./gradlew build)"
            )
        return src.read_bytes()
    dest = mods_dir / mod["filename"]
    if dest.is_file():
        return dest.read_bytes()
    if offline:
        raise FileNotFoundError(f"{mod['slug']}: {dest} not cached and --offline set")
    mods_dir.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(mod["url"], headers=UA), timeout=180) as r:
        data = r.read()
    dest.write_bytes(data)
    return data


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mods-dir", default=str(MOD_CACHE), help="jar cache dir (default pack/mods)")
    ap.add_argument("--lockfile", default=str(LOCKFILE))
    ap.add_argument("--offline", action="store_true", help="fail instead of downloading uncached jars")
    args = ap.parse_args(argv)

    lock = json.loads(Path(args.lockfile).read_text())
    mods_dir = Path(args.mods_dir)

    parsed = []
    errors = []
    for mod in lock["mods"]:
        try:
            data = _load_jar_bytes(mod, mods_dir, args.offline)
            provided, required = parse_mod_jar(data)
            parsed.append({"slug": mod["slug"], "provided": provided, "required": required})
        except Exception as e:
            errors.append(f"{mod['slug']}: could not read jar ({e})")

    if errors:
        print("check_mod_dependencies: FAIL - could not read some jars:")
        for e in errors:
            print("  " + e)
        return 1

    problems = resolve(parsed)
    if problems:
        print(f"check_mod_dependencies: FAIL - {len(problems)} unsatisfied required dependenc"
              f"{'y' if len(problems) == 1 else 'ies'}:")
        for p in problems:
            print("  ! " + p)
        return 1

    print(f"check_mod_dependencies: PASS - all required dependencies of "
          f"{len(parsed)} mod(s) are provided (incl. Jar-in-Jar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
