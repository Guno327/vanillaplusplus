#!/usr/bin/env python3
"""Deterministic SHA-256 fingerprint of a mods-src/<modid>/ tree's build
inputs (GitHub #198).

The gap this closes: pack/mods.lock.json pins a local mod's *jar* by hash
(hashes.sha1/sha512 - see scripts/resolve_mods.py's resolve_one_local()),
but nothing ever tied that jar back to the source it was supposedly built
from. Editing mods-src/<modid>/src/** without rebuilding + re-pinning passed
every existing CI tier green. This module computes a second, independent
fingerprint - this time over the *source* rather than the jar - so
scripts/ci/check_local_mod_sources.py can catch that drift.

The rule is **jar build inputs only** - what Gradle's `jar` task actually
packages, not everything that happens to live under mod_dir. What gets
hashed, per mod_dir (e.g. mods-src/vppquests/):
  - everything under mod_dir/src/main/** (recursively) - this is the only
    source set the `jar` task consumes (src/main/java + src/main/resources
    and any other src/main/<sourceSet> Gradle happens to define).
  - mod_dir/build.gradle, mod_dir/gradle.properties, mod_dir/settings.gradle,
    mod_dir/libs.json - each only if present.

mod_dir/src/test/** (and any other non-"main" source set under src/) is
deliberately EXCLUDED (GitHub #202): it feeds Gradle's `test` task, never
the `jar` task, so it is not a build input for the committed jar this
fingerprint is meant to pin against. Before #202 this hashed all of src/**,
which meant adding or editing a JUnit test for a local mod - something this
project's tests-first charter requires - always tripped the drift check in
check_local_mod_sources.py even though the resulting jar (and its
hashes.sha1/sha512 pin) would not actually change. That's a real cost paid
on every test change, unlike the deliberately-asymmetric choice below.

build.gradle stays included even though it also configures the `test` task,
because it can genuinely change the jar too - dependencies, jarJar/shadow
relocation, resource processing, manifest attributes, etc. all live there.
Over-including build.gradle costs an occasional unnecessary re-pin (only
when a build.gradle edit happens to be test-task-only); over-including
src/test/** costs one on *every* test change, which is the common case for
a tests-first project. That asymmetry is why build.gradle stays in but
src/test/** does not: the false-positive rate from build.gradle is low and
the file is small/rare to touch, while src/test/** churns constantly and in
exactly the direction (adding tests) this project wants to encourage.

What's excluded even if it somehow appears under those paths: anything under
a build/, .gradle/, run/, or libs/ directory component, and anything matched
by mod_dir/.gitignore (a small, dependency-free glob matcher - this repo has
no PyYAML/requests/etc. available in the fast CI tier, so no pathspec
either). None of mods-src/*/'s current .gitignore-excluded paths actually
live under src/main/ or the four named top-level files, so this is a belt-
and-braces guard against future drift, not something the current trees rely
on.

The digest is over (path, content) pairs, sorted by repo-relative POSIX path
so it's independent of filesystem iteration order, and length-prefixed so a
rename (path change) or a content move across files cannot collide with a
different (path, content) set. mtimes are never read, so touching a file
without changing its bytes never changes the fingerprint.

Usable both as a library (fingerprint(mod_dir) -> hex str) and as a CLI:
    python3 scripts/ci/local_mod_source_hash.py mods-src/vppquests
"""
import fnmatch
import hashlib
import sys
from pathlib import Path

# Directory names that are never part of a mod's build inputs even if a stray
# copy shows up under src/ (e.g. a test fixture that itself contains a
# "build" directory) - matches this repo's mods-src/*/.gitignore convention
# (.gradle/, build/, run/, libs/*.jar) at the directory-name level.
_ALWAYS_EXCLUDED_DIR_NAMES = {"build", ".gradle", "run", "libs"}

# The fixed set of top-level files (besides src/**) that feed a gradle build,
# per resolve_mods.py's resolve_one_local() docstring / this repo's actual
# mods-src/<modid>/ layout (build.gradle, gradle.properties, settings.gradle,
# libs.json).
_TOP_LEVEL_CANDIDATES = ("build.gradle", "gradle.properties", "settings.gradle", "libs.json")


def _gitignore_patterns(mod_dir):
    gi = mod_dir / ".gitignore"
    if not gi.is_file():
        return []
    patterns = []
    for line in gi.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line.rstrip("/"))
    return patterns


def _is_gitignored(rel_posix, patterns):
    parts = rel_posix.split("/")
    basename = parts[-1]
    for pat in patterns:
        if fnmatch.fnmatch(rel_posix, pat) or fnmatch.fnmatch(basename, pat):
            return True
        # A directory-shaped pattern (e.g. "build", ".gradle") excludes
        # anything nested under a same-named path component.
        if pat in parts[:-1]:
            return True
    return False


def source_files(mod_dir):
    """Return the sorted list of absolute Paths that make up mod_dir's build
    inputs, per this module's docstring. Deterministic order (sorted by
    repo-relative POSIX path)."""
    mod_dir = Path(mod_dir)
    patterns = _gitignore_patterns(mod_dir)
    candidates = []

    # Only src/main/** feeds Gradle's `jar` task; src/test/** (and any other
    # non-"main" source set) feeds `test` only and is not a build input for
    # the committed jar - see module docstring (GitHub #202).
    main_src_dir = mod_dir / "src" / "main"
    if main_src_dir.is_dir():
        for p in main_src_dir.rglob("*"):
            if p.is_file():
                candidates.append(p)

    for name in _TOP_LEVEL_CANDIDATES:
        f = mod_dir / name
        if f.is_file():
            candidates.append(f)

    kept = []
    for p in candidates:
        rel = p.relative_to(mod_dir)
        parts = rel.parts
        if _ALWAYS_EXCLUDED_DIR_NAMES & set(parts[:-1]):
            continue
        rel_posix = rel.as_posix()
        if _is_gitignored(rel_posix, patterns):
            continue
        kept.append(p)

    kept.sort(key=lambda p: p.relative_to(mod_dir).as_posix())
    return kept


def fingerprint(mod_dir):
    """SHA-256 hex digest over mod_dir's build inputs. See module docstring
    for exactly what's included/excluded and the framing that makes this
    collision-safe against renames."""
    mod_dir = Path(mod_dir)
    h = hashlib.sha256()
    for p in source_files(mod_dir):
        rel_bytes = p.relative_to(mod_dir).as_posix().encode("utf-8")
        data = p.read_bytes()
        # Length-prefixed framing (both path and content) so that e.g.
        # path="ab", content="cd" cannot collide with path="a", content="bcd".
        h.update(len(rel_bytes).to_bytes(8, "big"))
        h.update(rel_bytes)
        h.update(len(data).to_bytes(8, "big"))
        h.update(data)
    return h.hexdigest()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python3 scripts/ci/local_mod_source_hash.py <mod_dir>", file=sys.stderr)
        return 2
    mod_dir = Path(argv[0])
    if not mod_dir.is_dir():
        print(f"local_mod_source_hash: not a directory: {mod_dir}", file=sys.stderr)
        return 1
    print(fingerprint(mod_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
