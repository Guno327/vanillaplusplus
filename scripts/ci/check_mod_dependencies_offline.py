#!/usr/bin/env python3
"""Fast-tier CI check: the OFFLINE counterpart to check_mod_dependencies.py.

WHY THIS EXISTS (v0.5.0 follow-up hardening). check_mod_dependencies.py
closed the gap where every boot tier boots only the dedicated SERVER and so
never notices a missing CLIENT-side required dependency (the actual v0.5.0
regression: sodium-options-api hard-required reeses_sodium_options, never
installed). But that check needs the real mod jars (network download +
zipfile read), so it only runs in boot.yml - weekly/on-dispatch/at-mint, not
on every PR. Fast-tier (ci.yml / run_all.py) runs on EVERY PR and push, but
is fully offline: no mod jars, no network. This check brings the SAME
resolve() logic to fast-tier by reading a committed, jar-derived snapshot
(pack/mod_registries/mod_dependencies.json, produced by
scripts/gen_mod_dependencies.py) instead of the jars themselves.

TWO THINGS THIS CHECK GUARDS:
  1. SYNC: the committed snapshot must describe EXACTLY the mod set (by
     slug) currently pinned in pack/mods.lock.json, at the SAME
     version_number per slug. A mod added/removed/bumped without re-running
     scripts/gen_mod_dependencies.py is caught here - same "regenerate the
     snapshot" discipline as check_storage_tiers.py's sophisticatedstorage.
     json cross-check - rather than silently validating stale data forever.
  2. RESOLUTION: the exact same check_mod_dependencies.resolve() pure
     function is run against the committed snapshot's provided/required
     data. Any unsatisfied REQUIRED dependency (client- or server-side,
     incl. Jar-in-Jar providers) fails fast-tier immediately, on every PR -
     closing the v0.5.0 gap without needing network or jars in CI.

Usage: python3 scripts/ci/check_mod_dependencies_offline.py [root]
Exit code: 0 if the snapshot is in sync and all required deps resolve, 1
otherwise.
"""
import json
import sys
from pathlib import Path

CI_DIR = Path(__file__).resolve().parent
REPO_ROOT = CI_DIR.parent.parent
sys.path.insert(0, str(CI_DIR))
import check_mod_dependencies as cmd  # noqa: E402

LOCKFILE_REL = Path("pack") / "mods.lock.json"
SNAPSHOT_REL = Path("pack") / "mod_registries" / "mod_dependencies.json"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_sync(lock, snapshot, errors):
    """Snapshot's mod set (slug -> version_number) must exactly match the
    lockfile's. Returns nothing; appends problems to errors."""
    lock_mods = {m["slug"]: m.get("version_number") for m in lock.get("mods", [])}
    snap_mods = snapshot.get("mods", {})

    missing = sorted(set(lock_mods) - set(snap_mods))
    stale = sorted(set(snap_mods) - set(lock_mods))
    if missing:
        errors.append(
            f"{SNAPSHOT_REL}: missing {len(missing)} mod(s) pinned in {LOCKFILE_REL}: "
            f"{missing} - run 'python3 scripts/gen_mod_dependencies.py'"
        )
    if stale:
        errors.append(
            f"{SNAPSHOT_REL}: has {len(stale)} stale mod(s) no longer in {LOCKFILE_REL}: "
            f"{stale} - run 'python3 scripts/gen_mod_dependencies.py'"
        )
    for slug in sorted(set(lock_mods) & set(snap_mods)):
        lock_version = lock_mods[slug]
        snap_version = snap_mods[slug].get("version_number")
        if lock_version != snap_version:
            errors.append(
                f"{SNAPSHOT_REL}: {slug!r} snapshot was generated from version "
                f"{snap_version!r} but {LOCKFILE_REL} now pins {lock_version!r} - "
                f"re-run 'python3 scripts/gen_mod_dependencies.py'"
            )


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else REPO_ROOT

    errors = []
    lock_path = root / LOCKFILE_REL
    snapshot_path = root / SNAPSHOT_REL

    if not lock_path.is_file():
        errors.append(f"{lock_path} missing")
    if not snapshot_path.is_file():
        errors.append(
            f"{snapshot_path} missing - run 'python3 scripts/gen_mod_dependencies.py'"
        )
    if errors:
        print("check_mod_dependencies_offline: FAIL:")
        for e in errors:
            print("  " + e)
        return 1

    lock = load_json(lock_path)
    snapshot = load_json(snapshot_path)

    check_sync(lock, snapshot, errors)
    if errors:
        print("check_mod_dependencies_offline: FAIL - snapshot out of sync:")
        for e in errors:
            print("  " + e)
        return 1

    parsed = [
        {"slug": slug, "provided": set(m.get("provided", [])), "required": m.get("required", [])}
        for slug, m in snapshot.get("mods", {}).items()
    ]
    problems = cmd.resolve(parsed)
    if problems:
        print(f"check_mod_dependencies_offline: FAIL - {len(problems)} unsatisfied required "
              f"dependenc{'y' if len(problems) == 1 else 'ies'} (from committed snapshot "
              f"{SNAPSHOT_REL}):")
        for p in problems:
            print("  ! " + p)
        return 1

    print(f"check_mod_dependencies_offline: PASS - snapshot in sync with {LOCKFILE_REL} "
          f"({len(parsed)} mod(s)), all required dependencies satisfied (incl. Jar-in-Jar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
