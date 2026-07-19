#!/usr/bin/env python3
"""Fast-tier CI check: every *.json and *.mcmeta file under pack/ must parse
cleanly with the stdlib json module.

Usage: python3 scripts/ci/validate_json.py [root]
    root defaults to the repo root (parent of scripts/), so this also works
    when invoked as `python3 scripts/ci/validate_json.py` from anywhere.
Exit code: 0 if every file parses, 1 if any file fails to parse or decode.

No directories under pack/ are excluded. This repo's pack/ tree (as of
writing) contains only mod config/data/lang text files - no vendored
binaries, no node_modules-style dependency trees, nothing generated at
build time that would need skipping. If a future addition introduces a
directory that should not be JSON-validated (e.g. a vendored third-party
blob), add its path to EXCLUDED_DIRS below and explain why right there -
this module must never skip a directory silently.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PACK_DIR = REPO_ROOT / "pack"

# See module docstring: currently empty on purpose. Paths are relative to
# PACK_DIR.
EXCLUDED_DIRS: set[str] = set()

CHECKED_SUFFIXES = (".json", ".mcmeta")


def _is_excluded(path: Path) -> bool:
    try:
        rel = path.relative_to(PACK_DIR)
    except ValueError:
        return False
    return any(part in EXCLUDED_DIRS for part in rel.parts[:-1])


def find_files(pack_dir: Path):
    files = []
    for suffix in CHECKED_SUFFIXES:
        files.extend(pack_dir.rglob(f"*{suffix}"))
    return sorted(p for p in files if p.is_file() and not _is_excluded(p))


def check_file(path: Path):
    """Return None on success, or a human-readable error string on failure."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        return f"could not decode as UTF-8: {e}"
    except OSError as e:
        return f"could not read file: {e}"
    try:
        json.loads(text)
    except json.JSONDecodeError as e:
        return f"line {e.lineno} column {e.colno}: {e.msg}"
    return None


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    pack_dir = Path(argv[0]) / "pack" if argv else PACK_DIR

    if not pack_dir.is_dir():
        print(f"validate_json: FAIL - pack directory not found at {pack_dir}", file=sys.stderr)
        return 1

    files = find_files(pack_dir)
    failures = []
    for path in files:
        err = check_file(path)
        if err is not None:
            failures.append((path, err))

    if failures:
        print(f"validate_json: FAIL - {len(failures)}/{len(files)} file(s) failed to parse:")
        for path, err in failures:
            try:
                rel = path.relative_to(REPO_ROOT)
            except ValueError:
                rel = path
            print(f"  {rel}: {err}")
        return 1

    print(f"validate_json: PASS - {len(files)} file(s) parsed cleanly ({pack_dir})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
