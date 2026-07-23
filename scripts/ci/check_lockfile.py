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
  4. No slug appears more than once within manifest.json (a real bug found
     the hard way, 2026-07-20: a merge-conflict resolution duplicated the
     architectury-api entry - {slug: entry} dict-building silently
     collapsed it before this check existed, so the duplicate went
     undetected by checks 1-3 above (both files still had matching slug
     *sets*) until L0's boot smoke test caught a server/mods jar-count
     mismatch downstream. resolve_mods.py's own {slug: info} accumulation
     has the identical blind spot, so mods.lock.json is checked here too.

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

    for label, mods in (("manifest.json", manifest_mods), ("mods.lock.json", lock_mods)):
        seen = {}
        for m in mods:
            seen[m["slug"]] = seen.get(m["slug"], 0) + 1
        for slug, count in sorted(seen.items()):
            if count > 1:
                errors.append(f"slug {slug!r} appears {count} times in {label} (should be listed once)")

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

    # loader_installer (issue #64/#82): a manually-pinned NeoForge
    # server-installer spec whose source of truth is the manifest and which
    # resolve_mods.py must carry into the generated lockfile verbatim.
    # build_server.py hard-fails without it in the lock, but boot-tier only
    # runs weekly/on-dispatch - so guard it here in fast-tier (every PR).
    # This exact gap shipped once: resolve_mods.py dropped the pin on
    # regeneration and it wasn't caught until a mint's boot-tier failed.
    m_installer = manifest.get("loader_installer")
    l_installer = lock.get("loader_installer")
    if m_installer is None:
        errors.append("manifest.json is missing the 'loader_installer' pin (source of truth for the NeoForge server installer)")
    if l_installer is None:
        errors.append("mods.lock.json is missing the 'loader_installer' pin - build_server.py cannot bootstrap the server without it (resolve_mods.py must copy it from the manifest)")
    if m_installer is not None and l_installer is not None:
        # Compare functional fields only - "_note"/"_comment"-style keys are
        # human annotations and may legitimately differ between the manifest
        # (source of truth) and the generated lock.
        def _functional(d):
            return {k: v for k, v in d.items() if not k.startswith("_")}
        if _functional(m_installer) != _functional(l_installer):
            errors.append("loader_installer differs between manifest.json and mods.lock.json (version/url/filename/hashes/filesize) - the lock must copy the manifest's pin (rerun resolve_mods.py)")

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

    # Cross-check the pinned installer version against pack.toml's
    # [versions].neoforge - build_server.py hard-fails on this drift at boot
    # time, so surface it in fast-tier instead. (Done in main(), not
    # check_lockfile(), since it needs a third file off `root`.)
    installer = lock.get("loader_installer") or manifest.get("loader_installer")
    pack_toml = root / "pack" / "pack.toml"
    if installer and pack_toml.is_file():
        try:
            import tomllib
            neoforge = tomllib.loads(pack_toml.read_text(encoding="utf-8")).get("versions", {}).get("neoforge")
        except Exception as e:  # tomllib parse error - report, don't crash the check
            neoforge = None
            errors.append(f"could not read pack.toml [versions].neoforge: {e}")
        if neoforge is not None and installer.get("version") != neoforge:
            errors.append(
                f"loader_installer.version ({installer.get('version')!r}) does not match "
                f"pack.toml [versions].neoforge ({neoforge!r}) - build_server.py will hard-fail on this drift")

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
