#!/usr/bin/env python3
"""GitHub issue #183's test-tier entrypoint: runs one mods-src/<mod>/'s
JUnit suite (`./gradlew test`) on a bare checkout, invoked once per matrix
entry by .github/workflows/mods-tests.yml (matrix.mod comes from
discover_mod_gradle_projects.py --json).

WHY THIS EXISTS AS A SIBLING OF scripts/build_local_mods.py, NOT A COPY: a
fresh checkout is missing the same two gitignored things build_local_mods.py
already knows how to bootstrap for the release/boot path -
gradle/wrapper/gradle-wrapper.jar (a binary nobody commits, fetched+verified
from gradle/gradle's own tag) and, for vppfixes/vppintegration only,
libs/*.jar (Tom's Storage / Silent Gear+Silent Lib - only fetchable via the
already-pinned URL+hash in pack/mods.lock.json, per each mod's libs.json).
build_local_mods.py runs the full `./gradlew build` for the release/boot
path; this script runs `./gradlew test` only, for exactly one mod at a time,
for the PR-facing test tier - so it imports and reuses stage_libs(),
ensure_gradle_wrapper_jar(), and gradle_env() from build_local_mods.py
rather than re-implementing any of that bootstrap logic here.

Usage: python3 scripts/ci/run_mod_tests.py <mod-name>
  e.g. python3 scripts/ci/run_mod_tests.py vppskills
Exit code: 0 if the suite passes, 1 if the mod/gradlew is missing, or
gradle's own exit code if the test run itself fails.
"""
import json
import subprocess
import sys
from pathlib import Path

CI_DIR = Path(__file__).resolve().parent
REPO_ROOT = CI_DIR.parent.parent
MODS_SRC = REPO_ROOT / "mods-src"

# build_local_mods.py lives in scripts/, one level above scripts/ci/ - same
# convention scripts/ci/tests/test_build_local_mods.py already uses to
# import it (scripts/ isn't a package, so this is a plain sys.path insert,
# not a relative import).
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import build_local_mods  # noqa: E402


def run_mod_tests(mod_name):
    """Stage that mod's libs.json deps (if any) + the gradle wrapper jar,
    then run `sh gradlew test` in it. Returns gradle's own process exit
    code (0 on success). Raises SystemExit with a clear message if the mod
    directory or its gradlew is missing."""
    mod_dir = MODS_SRC / mod_name
    if not mod_dir.is_dir():
        raise SystemExit(f"run_mod_tests: no such mod directory {mod_dir}")

    gradlew = mod_dir / "gradlew"
    if not gradlew.is_file():
        raise SystemExit(f"run_mod_tests: {mod_dir} has no gradlew - not a Gradle project")

    libs_json = mod_dir / "libs.json"
    if libs_json.is_file():
        build_local_mods.stage_libs(mod_dir, json.loads(libs_json.read_text()))

    build_local_mods.ensure_gradle_wrapper_jar(mod_dir)

    print(f"running {mod_name} (./gradlew test)...", file=sys.stderr)
    result = subprocess.run(
        ["sh", str(gradlew), "test"],
        cwd=mod_dir,
        env=build_local_mods.gradle_env(),
    )
    return result.returncode


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: run_mod_tests.py <mod-name>", file=sys.stderr)
        return 1
    return run_mod_tests(argv[0])


if __name__ == "__main__":
    sys.exit(main())
