#!/usr/bin/env python3
"""Build every mods-src/<modid>/ tree into a real jar before resolve_mods.py
(via resolve_one_local()) hashes it into pack/mods.lock.json.

GitHub #67's mods-src/ convention (DECISIONS.md "#67 - custom-mods convention
established") deliberately kept resolve_mods.py itself from ever shelling out
to a build tool - resolve_one_local() only hashes a jar that ALREADY exists at
"local_path". This script is that missing "make the jar exist" step, run as
its own pass (called from resolve_mods.py's main() below, and directly by CI)
rather than folded into resolve_one_local() itself, so a plain `python3
scripts/resolve_mods.py --no-build` (or running this file solo) stays
possible for anyone iterating on the lockfile without a JDK/network handy.

What it does, per mods-src/<modid>/ directory that contains a build.gradle:
  1. If that directory has a libs.json (a small manifest of pack/mods.lock.json
     slugs the mod's own build.gradle compiles against via a flat `libs/`
     repo - see mods-src/vppintegration/README.md's "Build instructions" for
     why Silent Gear/Silent Lib can't be pulled from any public Maven repo),
     fetch each listed slug's exact jar from the CURRENT pack/mods.lock.json
     (already-resolved URL+hash - reuses whatever the pack itself just
     resolved rather than re-querying Modrinth a second time) into that mod's
     libs/ directory. libs/ is gitignored (a build-time cache, same spirit as
     server/mods/) - see that directory's own note in .gitignore.
  2. If gradle/wrapper/gradle-wrapper.jar is missing (it's a binary, gitignored
     per every mods-src/<modid>/.gitignore, and a fresh CI checkout has never
     run `gradle wrapper` locally the way this sandbox's README instructions
     assume), fetches the exact jar for gradle-wrapper.properties'
     `distributionUrl` version straight from gradle/gradle's own GitHub tag
     (`raw.githubusercontent.com/gradle/gradle/v<version>.0/gradle/wrapper/
     gradle-wrapper.jar`) - confirmed byte-identical (same sha1) to running
     `gradle wrapper --gradle-version <version>` with a real Gradle install,
     without needing one. This is what makes a bare hosted-CI checkout able to
     run `./gradlew build` at all.
  3. Runs `./gradlew build` in that directory, with JAVA_HOME/PATH pointed at
     a JDK 21 - prefers this repo's own .tools/jdk-21.0.11+10 (the dev-sandbox
     convention every scripts/tests/*.sh already hardcodes) if present, else
     falls back to whatever `java`/JAVA_HOME the environment already provides
     (e.g. a hosted CI runner's actions/setup-java step).

Does NOT touch pack/manifest.json or pack/mods.lock.json itself - it only
makes sure the jar resolve_one_local() is about to hash is real and current.
"""
import json
import hashlib
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODS_SRC = ROOT / "mods-src"
LOCKFILE = ROOT / "pack" / "mods.lock.json"
LOCAL_JDK = ROOT / ".tools" / "jdk-21.0.11+10"
UA = {"User-Agent": "vanilla-plus-plus/0.1 (+github.com/gunnarhovik327)"}

# Pinned SHA-256 of gradle/wrapper/gradle-wrapper.jar per Gradle version, as
# published at gradle/gradle's own `v<version>` tag. ensure_gradle_wrapper_jar()
# downloads this jar and then ./gradlew EXECUTES it, so pinning the digest turns
# the docstring's one-time "verified byte-identical" claim into an enforced
# guarantee: any drift or tampering at the source hard-fails the build instead
# of silently running an unexpected binary on the release/boot CI path. To add a
# version: fetch the jar from the same tag, sha256 it, and record it here.
GRADLE_WRAPPER_JAR_SHA256 = {
    "8.10.0": "2db75c40782f5e8ba1fc278a5574bab070adccb2d21ca5a6e5ed840888448046",
}


def _lockfile_mods_by_slug():
    if not LOCKFILE.exists():
        return {}
    return {m["slug"]: m for m in json.loads(LOCKFILE.read_text())["mods"]}


def stage_libs(mod_dir, libs_config):
    """Fetch each slug in libs_config (mods-src/<modid>/libs.json - a plain
    JSON list of pack/mods.lock.json slugs) into mod_dir/libs/, using the
    already-resolved URL+hash from the current lockfile so this never
    queries Modrinth's version API a second time for a mod the pack build
    itself already resolved."""
    libs_dir = mod_dir / "libs"
    libs_dir.mkdir(exist_ok=True)
    by_slug = _lockfile_mods_by_slug()
    for slug in libs_config:
        entry = by_slug.get(slug)
        if entry is None:
            raise SystemExit(
                f"{mod_dir.name}: libs.json lists {slug!r} but pack/mods.lock.json "
                f"has no entry for it - run scripts/resolve_mods.py first (without "
                f"--skip-build) or add {slug!r} to pack/manifest.json"
            )
        dest = libs_dir / entry["filename"]
        if dest.is_file() and len(dest.read_bytes()) == entry["filesize"]:
            print(f"  libs: {dest.name} already staged", file=sys.stderr)
            continue
        print(f"  libs: fetching {entry['filename']} ({slug}) for {mod_dir.name}...", file=sys.stderr)
        req = urllib.request.Request(entry["url"], headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:
            dest.write_bytes(r.read())


def gradle_env():
    env = os.environ.copy()
    if LOCAL_JDK.is_dir():
        env["JAVA_HOME"] = str(LOCAL_JDK)
        env["PATH"] = f"{LOCAL_JDK / 'bin'}:{env.get('PATH', '')}"
    return env


def ensure_gradle_wrapper_jar(mod_dir):
    """gradle/wrapper/gradle-wrapper.jar is a committed-nowhere binary (every
    mods-src/<modid>/.gitignore excludes it - see vppintegration's own for the
    reasoning) that `./gradlew` needs just to bootstrap itself. A persistent
    dev sandbox gets it once via a manual `gradle wrapper` run (this repo's
    READMEs document that), but a fresh hosted-CI checkout has no local
    Gradle install to run that with at all. Fetch the exact jar for whatever
    version gradle-wrapper.properties pins straight from gradle/gradle's own
    tagged source instead - verified byte-for-byte identical (matching sha1)
    to a real `gradle wrapper --gradle-version X` run against the same
    version, so this is not a guess at an alternate artifact."""
    wrapper_jar = mod_dir / "gradle" / "wrapper" / "gradle-wrapper.jar"
    if wrapper_jar.is_file():
        return
    props = mod_dir / "gradle" / "wrapper" / "gradle-wrapper.properties"
    text = props.read_text()
    m = re.search(r"gradle-(\d+\.\d+(?:\.\d+)?)-", text)
    if not m:
        raise SystemExit(f"{mod_dir.name}: could not parse a Gradle version out of {props}")
    version = m.group(1)
    if version.count(".") == 1:
        version += ".0"
    expected_sha256 = GRADLE_WRAPPER_JAR_SHA256.get(version)
    if expected_sha256 is None:
        raise SystemExit(
            f"{mod_dir.name}: no pinned gradle-wrapper.jar SHA-256 for Gradle "
            f"{version} in GRADLE_WRAPPER_JAR_SHA256. Refusing to download-and-"
            f"execute an unverified wrapper jar. Add the pinned digest for this "
            f"version (fetch from the v{version} tag, sha256 it) before building."
        )
    url = f"https://raw.githubusercontent.com/gradle/gradle/v{version}/gradle/wrapper/gradle-wrapper.jar"
    print(f"  gradle wrapper jar missing - fetching {url}", file=sys.stderr)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    actual_sha256 = hashlib.sha256(data).hexdigest()
    if actual_sha256 != expected_sha256:
        raise SystemExit(
            f"{mod_dir.name}: gradle-wrapper.jar SHA-256 mismatch for Gradle "
            f"{version}\n  expected {expected_sha256}\n  got      {actual_sha256}\n"
            f"Refusing to execute an unexpected wrapper binary. If this is a "
            f"legitimate upstream change, verify it and update "
            f"GRADLE_WRAPPER_JAR_SHA256."
        )
    wrapper_jar.write_bytes(data)


def build_one(mod_dir):
    libs_json = mod_dir / "libs.json"
    if libs_json.is_file():
        stage_libs(mod_dir, json.loads(libs_json.read_text()))

    ensure_gradle_wrapper_jar(mod_dir)

    gradlew = mod_dir / "gradlew"
    if not gradlew.is_file():
        raise SystemExit(f"{mod_dir.name}: no gradlew at {gradlew} - cannot build")
    print(f"building {mod_dir.name} (./gradlew build)...", file=sys.stderr)
    subprocess.run(
        ["sh", str(gradlew), "build"],
        cwd=mod_dir,
        env=gradle_env(),
        check=True,
    )


def main():
    if not MODS_SRC.is_dir():
        return
    built_any = False
    for mod_dir in sorted(MODS_SRC.iterdir()):
        if not mod_dir.is_dir():
            continue
        if not (mod_dir / "build.gradle").is_file():
            continue
        build_one(mod_dir)
        built_any = True
    if not built_any:
        print("no mods-src/<modid>/ trees with a build.gradle found - nothing to build", file=sys.stderr)


if __name__ == "__main__":
    main()
