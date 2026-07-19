#!/usr/bin/env python3
"""Fast-tier CI check: pack/manifest.json and pack/mods.lock.json must be
mutually consistent.

Ground-truthed against the actual files in this repo (both read directly
before writing this check, not assumed):

  - Both files list mods under a top-level "mods" array, keyed by "slug".
  - manifest.json entries always have "side" and "phase"; some (the FTB
    suite, a few CurseForge-only mods like ato/allthemodium) additionally
    have "source": "curseforge", "cf_project_slug", "cf_file_id",
    "cf_filename", "cf_version_number" - but these are manifest-only
    provenance fields.
  - mods.lock.json entries all share ONE schema regardless of the
    manifest's declared "source": every entry (Modrinth-resolved or
    CurseForge-resolved alike) has "filename", "url", "hashes" (with at
    least "sha512", plus "sha1" in practice), "filesize", "side", "phase".
    There is no separate "curseforge-source" schema in the lockfile as
    written by scripts/resolve_mods.py - CurseForge entries just have a
    CurseForge CDN URL (mediafilez.forgecdn.net) instead of a Modrinth one.
    This check therefore applies the same required-field rule to every
    lock entry.

Checks performed:
  1. The set of mod slugs in manifest.json and mods.lock.json must match
     exactly (reports any missing-from-lock / extra-in-lock slugs).
  2. Every lock entry must have a non-empty "filename", "url", and
     "hashes"."sha512".
  3. For every slug present in both files, "side" and "phase" must match
     between manifest and lock.

Usage: python3 scripts/ci/check_lockfile.py [root]
Exit code: 0 if consistent, 1 otherwise.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_lockfile(manifest, lock):
    """manifest / lock are already-parsed dicts. Returns a list of
    human-readable error strings (empty list == consistent)."""
    errors = []

    manifest_mods = manifest.get("mods", [])
    lock_mods = lock.get("mods", [])

    manifest_by_slug = {m["slug"]: m for m in manifest_mods}
    lock_by_slug = {m["slug"]: m for m in lock_mods}

    manifest_slugs = set(manifest_by_slug)
    lock_slugs = set(lock_by_slug)

    missing_from_lock = sorted(manifest_slugs - lock_slugs)
    extra_in_lock = sorted(lock_slugs - manifest_slugs)

    for slug in missing_from_lock:
        errors.append(f"slug {slug!r} is in manifest.json but missing from mods.lock.json")
    for slug in extra_in_lock:
        errors.append(f"slug {slug!r} is in mods.lock.json but not in manifest.json")

    for slug in sorted(lock_slugs):
        entry = lock_by_slug[slug]
        filename = entry.get("filename")
        url = entry.get("url")
        sha512 = entry.get("hashes", {}).get("sha512") if isinstance(entry.get("hashes"), dict) else None
        if not filename:
            errors.append(f"slug {slug!r}: lock entry missing non-empty 'filename'")
        if not url:
            errors.append(f"slug {slug!r}: lock entry missing non-empty 'url'")
        if not sha512:
            errors.append(f"slug {slug!r}: lock entry missing non-empty 'hashes.sha512'")

    for slug in sorted(manifest_slugs & lock_slugs):
        m_entry = manifest_by_slug[slug]
        l_entry = lock_by_slug[slug]
        m_side, l_side = m_entry.get("side"), l_entry.get("side")
        m_phase, l_phase = m_entry.get("phase"), l_entry.get("phase")
        if m_side != l_side:
            errors.append(
                f"slug {slug!r}: side mismatch - manifest={m_side!r} lock={l_side!r}")
        if m_phase != l_phase:
            errors.append(
                f"slug {slug!r}: phase mismatch - manifest={m_phase!r} lock={l_phase!r}")

    return errors


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else REPO_ROOT
    manifest_path = root / "pack" / "manifest.json"
    lock_path = root / "pack" / "mods.lock.json"

    for path in (manifest_path, lock_path):
        if not path.is_file():
            print(f"check_lockfile: FAIL - required file not found: {path}", file=sys.stderr)
            return 1

    try:
        manifest = _load(manifest_path)
        lock = _load(lock_path)
    except json.JSONDecodeError as e:
        print(f"check_lockfile: FAIL - could not parse manifest/lock JSON: {e}", file=sys.stderr)
        return 1

    errors = check_lockfile(manifest, lock)

    if errors:
        print(f"check_lockfile: FAIL - {len(errors)} inconsistenc{'y' if len(errors) == 1 else 'ies'}:")
        for err in errors:
            print(f"  {err}")
        return 1

    print(f"check_lockfile: PASS - {len(lock.get('mods', []))} mod(s), "
          f"manifest and lock are consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
