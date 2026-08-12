#!/usr/bin/env python3
"""Fast-tier CI check (GitHub #198): guard against mods-src/<modid>/ source
drifting from the committed/pinned local-mod jar.

The gap this closes: this repo ships three locally-built Minecraft mods as
jars committed to git (pack/mods.lock.json entries with "local_path" -
resolve_one_local() in scripts/resolve_mods.py). Each is pinned by
hashes.sha1/hashes.sha512, but nothing tied that pin back to the source it
was built from - the JUnit tier compiles from source directly and
check_lockfile.py never opens a jar. Editing mods-src/<modid>/src/** without
rebuilding + re-pinning passed every existing check green.

This check adds a second pin, "source_sha256" (scripts/ci/local_mod_source_
hash.py's fingerprint() over the mod's build inputs), written by
resolve_one_local() alongside "hashes", and verifies it here.

For every pack/mods.lock.json entry:
  - no "local_path": skipped, UNLESS it carries a "source_sha256" anyway,
    which is itself inconsistent (that field only makes sense paired with a
    local_path) and is reported as an error.
  - has "local_path": the jar must exist, its sha1 must match
    hashes.sha1, "source_sha256" must be present, and it must match the
    live fingerprint of the mod's source tree (mods-src/<modid>/, derived
    from local_path itself - not assumed from the lock slug - since
    local_path is the field build_server.py/build_mrpack.py actually use).

Usage: python3 scripts/ci/check_local_mod_sources.py [root]
Exit code: 0 if every local-mod entry is consistent, 1 otherwise.
"""
import hashlib
import json
import sys
from pathlib import Path

CI_DIR = Path(__file__).resolve().parent
REPO_ROOT = CI_DIR.parent.parent

sys.path.insert(0, str(CI_DIR))
import local_mod_source_hash  # noqa: E402

REMEDY = "run `python3 scripts/resolve_mods.py`, then commit the rebuilt jar together with the updated lockfile"


def _mod_dir_from_local_path(root, local_path):
    """local_path is repo-relative, e.g.
    "mods-src/vppquests/build/libs/vppquests-0.1.0.jar". The mod's source
    tree is that jar's build/libs/ grandparent - derived structurally rather
    than assumed to equal the lock slug, since local_path (not slug) is the
    field build_server.py/build_mrpack.py actually resolve from."""
    jar_path = root / local_path
    return jar_path.parent.parent.parent


def check_local_mod_sources(lock, root):
    """lock is an already-parsed dict (pack/mods.lock.json). root is the
    repo root Path used to resolve local_path/mod-source-dir. Returns a list
    of human-readable error strings (empty list == consistent)."""
    errors = []
    for entry in lock.get("mods", []):
        slug = entry.get("slug", "<unknown>")
        local_path = entry.get("local_path")
        source_sha256 = entry.get("source_sha256")

        if not local_path:
            if source_sha256:
                errors.append(
                    f"slug {slug!r}: lock entry has 'source_sha256' but no 'local_path' - "
                    f"source_sha256 only makes sense for a local mod entry (inconsistent)")
            continue

        jar_path = root / local_path
        if not jar_path.is_file():
            errors.append(
                f"slug {slug!r}: local mod jar not found at {local_path!r} - {REMEDY}")
            continue

        data = jar_path.read_bytes()
        actual_sha1 = hashlib.sha1(data).hexdigest()
        pinned_sha1 = entry.get("hashes", {}).get("sha1") if isinstance(entry.get("hashes"), dict) else None
        if actual_sha1 != pinned_sha1:
            errors.append(
                f"slug {slug!r}: jar at {local_path!r} does not match pinned hashes.sha1 "
                f"(pinned={pinned_sha1!r} actual={actual_sha1!r}) - {REMEDY}")

        if not source_sha256:
            errors.append(
                f"slug {slug!r}: local mod lock entry is missing 'source_sha256' - {REMEDY}")
            continue

        mod_dir = _mod_dir_from_local_path(root, local_path)
        if not mod_dir.is_dir():
            errors.append(
                f"slug {slug!r}: could not locate mod source tree at {mod_dir} (derived from "
                f"local_path {local_path!r}) - {REMEDY}")
            continue

        actual_source_sha256 = local_mod_source_hash.fingerprint(mod_dir)
        if actual_source_sha256 != source_sha256:
            errors.append(
                f"slug {slug!r}: source at {mod_dir.relative_to(root)} has drifted from the "
                f"pinned jar (source_sha256 pinned={source_sha256!r} actual={actual_source_sha256!r}) "
                f"- {REMEDY}")

    return errors


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else REPO_ROOT
    lock_path = root / "pack" / "mods.lock.json"

    if not lock_path.is_file():
        print(f"check_local_mod_sources: FAIL - required file not found: {lock_path}", file=sys.stderr)
        return 1

    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"check_local_mod_sources: FAIL - could not parse {lock_path}: {e}", file=sys.stderr)
        return 1

    errors = check_local_mod_sources(lock, root)

    if errors:
        print(f"check_local_mod_sources: FAIL - {len(errors)} inconsistenc{'y' if len(errors) == 1 else 'ies'}:")
        for err in errors:
            print(f"  {err}")
        return 1

    local_count = sum(1 for m in lock.get("mods", []) if m.get("local_path"))
    print(f"check_local_mod_sources: PASS - {local_count} local mod(s) source-verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
