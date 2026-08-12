#!/usr/bin/env python3
"""Enumerates the first-party Gradle mod projects under `mods-src/` (GitHub
issue #183, "ci: mods-src JUnit suites never run in CI").

WHY THIS EXISTS: `mods-src/` holds four first-party NeoForge mods
(vppfixes, vppintegration, vppquests, vppskills), each its own standalone
Gradle project (has its own `gradlew`). Their JUnit suites had never run in
CI - only ci.yml's Python static validators over `pack/` ran on every PR.
`.github/workflows/mods-tests.yml` needs to build a GitHub Actions matrix
(one job per mod) without hardcoding the mod list, so a fifth mod added
later is picked up automatically instead of requiring a workflow edit. This
script is that single source of truth: it is imported directly by
scripts/ci/tests/test_discover_mod_gradle_projects.py and invoked as a CLI
(with --json) by the `discover` job in mods-tests.yml to populate
`strategy.matrix.mod` via `fromJSON(...)`.

A directory under mods-src/ is considered a Gradle project iff it directly
contains a `gradlew` file - this is deliberately the same, minimal signal
Gradle itself relies on (the wrapper script every real Gradle project
commits), so junk directories (__pycache__, dotfiles, a stray non-directory
entry, a mod missing its wrapper) are all silently excluded rather than
crashing. A missing `mods-src/` entirely (e.g. a stripped-down checkout)
returns an empty list rather than raising.

Usage:
  python3 scripts/ci/discover_mod_gradle_projects.py [root]
  python3 scripts/ci/discover_mod_gradle_projects.py --json [root]
Output: one mod directory name per line (sorted), or (with --json) a JSON
array of the same names. Exit code: always 0 - "no mods found" is a valid,
non-error result (an empty list/no output), not a failure.
"""
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MODS_SRC_DIRNAME = "mods-src"


def discover(repo_root) -> list[str]:
    """Return the sorted list of directory names directly under
    `<repo_root>/mods-src/` that contain a `gradlew` file. Missing
    `mods-src/` (or an empty/junk-only one) yields an empty list rather than
    raising."""
    mods_src = Path(repo_root) / MODS_SRC_DIRNAME
    if not mods_src.is_dir():
        return []

    mods = []
    for entry in mods_src.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.startswith(".") or entry.name == "__pycache__":
            continue
        if (entry / "gradlew").is_file():
            mods.append(entry.name)

    return sorted(mods)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", default=str(REPO_ROOT), help="repo root (default: this repo)")
    ap.add_argument("--json", action="store_true", help="emit a JSON array instead of one name per line")
    args = ap.parse_args(argv)

    mods = discover(Path(args.root))

    if args.json:
        print(json.dumps(mods))
    else:
        for mod in mods:
            print(mod)

    return 0


if __name__ == "__main__":
    sys.exit(main())
