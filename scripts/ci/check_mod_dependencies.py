#!/usr/bin/env python3
"""Launch-time dependency check: every mod's REQUIRED dependency must be
provided by some other mod in the pack (or bundled inside one via Jar-in-Jar).
Also statically detects two other launch-time failure classes NeoForge
enforces before any mod code runs: Java SPLIT PACKAGES, and mods declaring an
access-transformer file that isn't actually in their jar.

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

SPLIT-PACKAGE DETECTION (v0.5.1 follow-up, 2026-07-23 hardening pass): v0.5.1
shipped a client that would NOT LAUNCH — `sodium-dynamic-lights` directly
shades 11 classes under `dev.lambdaurora.lambdynlights.api`(`.item`), and
`ars-nouveau` Jar-in-Jars its own copy of `lambdynlights_api` (a real,
separately-loaded mod container once extracted) which exports those exact
same two packages. FML builds its module layer with `java.lang.module`, and
two distinct module-path entries exporting the same package is a hard
`ResolutionException` at startup — NOTHING above catches this (it isn't a
missing dependency, both mods' declared deps were fully satisfied). See
`detect_split_packages()` below for the exact selection rule (mods/JIJ-bundles
are de-duplicated by their own declared `modId`, matching how NeoForge's own
Jar-in-Jar mechanism actually resolves duplicate bundled mods — validated
against this pack's real 114-mod set: `create` and `iris-flw-compat` both
JIJ `flywheel` under different Maven coordinates but the SAME modId
"flywheel", and that is correctly NOT flagged, because only one physical
copy is ever loaded; `sodium-dynamic-lights` never declares a `lambdynlights_
api` modId at all — its copy is baked directly into its own jar rather than
JIJ'd — so it can't be de-duplicated against ars-nouveau's JIJ'd copy, and
that IS the real, correctly-flagged conflict).

ACCESS-TRANSFORMER FILE CHECK: the same v0.5.1 incident's log also showed
"Access transformer file accesstransformer.cfg provided by mod irisflw does
not exist!" — a mod's `neoforge.mods.toml` can declare
`[[accessTransformers]] file = "..."`, and NeoForge fails fast if that file
isn't actually packaged. Statically checkable: read every `[[accessTransformers]]`
block and confirm `file` (or `META-INF/<file>`, NeoForge's own resolution
path) exists in the same jar.

Reads the mod jars themselves (downloading+caching to pack/mods/ from the
lockfile if absent), because a mod's real, authoritative dependency list is
in its jar's neoforge.mods.toml — Modrinth's project-level dependency list
does not always match (that mismatch is what misled #112 in the first place).

Usage: python3 scripts/ci/check_mod_dependencies.py [--mods-dir DIR] [--offline]
Exit code: 0 if every check (deps, split-packages, access-transformers) passes.
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


# Packages the platform itself (NeoForge/the JDK/vanilla) always supplies -
# a mod jar should never be the one exporting these, so they're excluded from
# split-package detection even if something odd shows up under them.
PACKAGE_IGNORE_PREFIXES = (
    "java.", "javax.", "jdk.", "sun.",
    "net.minecraft.", "net.neoforged.", "net.minecraftforge.",
    "com.mojang.",
)


def _strip_toml_comments(txt):
    """Drop full-line TOML comments (line's first non-whitespace char is '#').
    Needed for `[[accessTransformers]]` detection specifically: several real
    jars (e.g. create-tfmg, create-marketplace, create-central-kitchen) ship
    that entire block COMMENTED OUT as a template/example - a naive substring
    search for '[[accessTransformers' still matches inside the comment and
    would wrongly flag a "declared but missing" AT file that was never
    actually declared. Doesn't handle inline (`key = 1 # comment`) or
    triple-quoted-string comments, but access-transformer blocks never need
    either."""
    return "\n".join(
        line for line in txt.splitlines() if not line.lstrip().startswith("#")
    )


def _modid_of_toml_text(txt):
    """First declared [[mods]] modId in one mods.toml's text, or None."""
    head = re.split(r"\[\[dependencies", txt)[0]
    m = re.search(r'modId\s*=\s*"([^"]+)"', head)
    return m.group(1).lower() if m else None


def _packages_of(zf):
    """Every dotted package name that has >=1 .class file DIRECTLY in it
    (i.e. the set of packages this jar, as a single module, would export to
    NeoForge's module layer)."""
    dirs = set()
    for n in zf.namelist():
        if n.endswith(".class") and "/" in n:
            dirs.add(n.rsplit("/", 1)[0])
    return {d.replace("/", ".") for d in dirs}


def _at_declared_files(txt):
    """Every `file = "..."` inside a `[[accessTransformers]]` block."""
    files = []
    for block in re.split(r"\[\[accessTransformers", txt)[1:]:
        m = re.search(r'file\s*=\s*"([^"]+)"', block)
        if m:
            files.append(m.group(1))
    return files


def collect_entities_and_ats(jar_bytes, label):
    """Walk one mod jar (+ its Jar-in-Jar bundles, recursively), returning
    (entities, at_records):

    entities: list of (key, label, packages) - one per "thing NeoForge loads
    as its own module": the mod's own jar, plus each JIJ-bundled jar. `key`
    is the bundle's own declared modId (lower-cased) if it has one - this is
    the de-duplication key, matching how NeoForge's real Jar-in-Jar
    resolution keeps exactly one physical copy per modId - or a
    content-hash fallback for a modId-less bundle (e.g. a plain shaded
    library with no mods.toml at all), which is never de-duplicated (safer
    default: flag rather than silently merge something we can't identify).

    at_records: list of (owner_label, declared_file, present:bool) for every
    `[[accessTransformers]]` block found, checked against that same jar's own
    namelist (declared path as-is, or NeoForge's real resolution path
    META-INF/<declared path>).
    """
    import hashlib

    entities = []
    at_records = []
    zf = zipfile.ZipFile(io.BytesIO(jar_bytes))
    names = set(zf.namelist())
    modid = None
    for raw_txt in _iter_tomls(zf):
        txt = _strip_toml_comments(raw_txt)
        modid = modid or _modid_of_toml_text(txt)
        for f in _at_declared_files(txt):
            present = f in names or f"META-INF/{f}" in names
            at_records.append((label, f, present))
    key = modid or ("hash", hashlib.sha256(jar_bytes).hexdigest())
    entities.append((key, label, _packages_of(zf)))
    for n in sorted(names):
        if n.startswith("META-INF/jarjar/") and n.endswith(".jar"):
            try:
                sub_bytes = zf.read(n)
            except Exception:
                continue
            sub_label = f"{label} > {n.rsplit('/', 1)[-1]} (JIJ)"
            try:
                sub_entities, sub_ats = collect_entities_and_ats(sub_bytes, sub_label)
            except Exception:
                continue
            entities.extend(sub_entities)
            at_records.extend(sub_ats)
    return entities, at_records


def detect_split_packages(all_entities):
    """all_entities: list of (key, label, packages) gathered across every
    installed mod (+ their JIJ bundles) - see collect_entities_and_ats.
    Returns a list of human-readable problem strings (empty == none found).
    Pure function - no I/O - unit-testable with synthetic fixtures.

    A package is flagged iff it is exported by entities under TWO OR MORE
    DISTINCT keys (distinct modId, or distinct content-hash for modId-less
    bundles) - same key (same modId, e.g. two mods JIJing the same library)
    is NOT a conflict, because NeoForge's own Jar-in-Jar selection keeps
    only one physical copy per modId; two genuinely different mods/bundles
    exporting the same package is the real, uncaught split-package
    ResolutionException class."""
    pkg_to_entities = {}  # package -> {key: label}
    for key, label, packages in all_entities:
        for p in packages:
            if p.startswith(PACKAGE_IGNORE_PREFIXES):
                continue
            pkg_to_entities.setdefault(p, {}).setdefault(key, label)

    problems = []
    for pkg, by_key in sorted(pkg_to_entities.items()):
        if len(by_key) < 2:
            continue
        labels = sorted(by_key.values())
        problems.append(
            f"split package '{pkg}' is exported by {len(labels)} distinct "
            f"mods/Jar-in-Jar bundles: {', '.join(labels)} - NeoForge's module "
            f"layer will refuse to resolve this (java.lang.module."
            f"ResolutionException) and the client/server will not launch"
        )
    return problems


def check_access_transformers(all_at_records):
    """all_at_records: list of (owner_label, declared_file, present:bool).
    Returns problem strings for every declared AT file NOT found in its own
    jar. Pure function - no I/O - unit-testable with synthetic fixtures."""
    problems = []
    for owner, declared_file, present in all_at_records:
        if not present:
            problems.append(
                f"{owner}: declares access-transformer file {declared_file!r} "
                f"([[accessTransformers]]) but it is not present in the jar - "
                f"NeoForge fails fast at launch (\"Access transformer file "
                f"{declared_file} provided by mod ... does not exist!\")"
            )
    return problems


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

    GitHub #67: a "source": "local" mod (this pack's own hand-rolled
    mods-src/<modid>/ jars) has no fetchable "url" at all - it's the
    repo-relative "local_path" string instead (same convention build_server.py
    and build_mrpack.py already special-case). Read it directly off disk
    rather than attempting a download, exactly like those two do."""
    if mod.get("local_path"):
        src = REPO_ROOT / mod["local_path"]
        if not src.is_file():
            raise FileNotFoundError(
                f"{mod['slug']}: local_path {mod['local_path']!r} not found - "
                f"build it first (e.g. python3 scripts/build_local_mods.py)"
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
    all_entities = []
    all_at_records = []
    errors = []
    for mod in lock["mods"]:
        try:
            data = _load_jar_bytes(mod, mods_dir, args.offline)
            provided, required = parse_mod_jar(data)
            parsed.append({"slug": mod["slug"], "provided": provided, "required": required})
            entities, at_records = collect_entities_and_ats(data, mod["slug"])
            all_entities.extend(entities)
            all_at_records.extend(at_records)
        except Exception as e:
            errors.append(f"{mod['slug']}: could not read jar ({e})")

    if errors:
        print("check_mod_dependencies: FAIL - could not read some jars:")
        for e in errors:
            print("  " + e)
        return 1

    problems = resolve(parsed)
    split_problems = detect_split_packages(all_entities)
    at_problems = check_access_transformers(all_at_records)

    if problems:
        print(f"check_mod_dependencies: FAIL - {len(problems)} unsatisfied required dependenc"
              f"{'y' if len(problems) == 1 else 'ies'}:")
        for p in problems:
            print("  ! " + p)

    if split_problems:
        print(f"check_mod_dependencies: FAIL - {len(split_problems)} split-package conflict"
              f"{'s' if len(split_problems) != 1 else ''}:")
        for p in split_problems:
            print("  ! " + p)

    if at_problems:
        print(f"check_mod_dependencies: FAIL - {len(at_problems)} missing access-transformer "
              f"file{'s' if len(at_problems) != 1 else ''}:")
        for p in at_problems:
            print("  ! " + p)

    if problems or split_problems or at_problems:
        return 1

    print(f"check_mod_dependencies: PASS - all required dependencies of "
          f"{len(parsed)} mod(s) are provided (incl. Jar-in-Jar), no split-package "
          f"conflicts, no missing access-transformer files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
