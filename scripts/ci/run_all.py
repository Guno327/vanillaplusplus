#!/usr/bin/env python3
"""Fast-tier CI entry point: runs every check in scripts/ci/ as its own
subprocess (exactly as CI invokes each individually), prints each check's
own output, then a summary table, and exits nonzero if any check failed.

Usage: python3 scripts/ci/run_all.py [root]
Exit code: 0 if every check passed, 1 if any failed.
"""
import subprocess
import sys
from pathlib import Path

CI_DIR = Path(__file__).resolve().parent
REPO_ROOT = CI_DIR.parent.parent

# Order matters only for readability; check_quests.py is listed after
# validate_snbt.py since it depends on the same SNBT parser being sane.
CHECKS = [
    "validate_json.py",
    "validate_snbt.py",
    "check_lockfile.py",
    "lint_rhino.py",
    "check_quests.py",
    "check_vppquests.py",
    "check_advancements.py",
    "check_skill_trees.py",
    "check_skill_expressions.py",
    "check_selftest_skill_sync.py",
    "check_storage_tiers.py",
    "check_mod_dependencies_offline.py",
]


def run_check(script_name, root):
    script_path = CI_DIR / script_name
    result = subprocess.run(
        [sys.executable, str(script_path), str(root)],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    return result


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else REPO_ROOT

    results = []
    for script_name in CHECKS:
        print(f"===== {script_name} =====")
        result = run_check(script_name, root)
        if result.stdout:
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        if result.stderr:
            print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)
        results.append((script_name, result.returncode))
        print()

    name_width = max(len(name) for name, _ in results)
    print("===== summary =====")
    any_failed = False
    for name, code in results:
        status = "PASS" if code == 0 else "FAIL"
        if code != 0:
            any_failed = True
        print(f"  {name:<{name_width}}  {status}")

    if any_failed:
        print("\nrun_all: FAIL - one or more checks failed")
        return 1

    print("\nrun_all: PASS - all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
