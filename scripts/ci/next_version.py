#!/usr/bin/env python3
"""Computes the next SemVer version for a release, from the repo's existing
`vX.Y.Z` git tags plus a bump type (major/minor/patch).

Used by .github/workflows/mint-release.yml (GitHub issue #27, "Async Way to
Mint Release") as the very first real step of minting a release: the
workflow checks out the repo (with full tag history), pipes its `git tag
--list "v*"` output into this script via --bump, and captures the bare
"X.Y.Z" string this prints to stdout to compute both the release tag
("v" + that string) and the new contents of pack/VERSION for the build
steps that follow.

Design notes:
  - Only tags of the exact form v<major>.<minor>.<patch> (all three
    non-negative integers, no pre-release/build suffix) are recognised as
    release tags; anything else (a stray annotated tag, a typo, a future
    v1.2.3-rc1 someone creates by hand) is silently ignored for the "what
    was the last release" computation rather than crashing the mint
    workflow. Ground-truthed against this repo's actual tags (`git tag -l`:
    v0.1.0, v0.1.1, v0.2.0) and SPEC.md/publish-modrinth.yml: this project
    does not use SemVer pre-release suffixes in the *tag* itself at all -
    "prerelease-ness" is conveyed purely by the GitHub Release's own
    isPrerelease flag (every release cut so far is tagged plainly but
    shipped as a beta prerelease - see publish-modrinth.yml's own
    isPrerelease-driven version_type logic for the same convention read
    back on the publish side).
  - "Next version" is always strictly greater than every existing valid
    tag: bump_version() only increments, so compute_next_version() can
    never legitimately collide with an existing tag - there is no need
    for (and this script deliberately omits) a defensive re-check against
    the tag list, since latest_release_version() already found the true
    maximum among every parseable tag before bumping it.
  - No tags at all (a from-scratch repo) bumps from an implicit v0.0.0, so
    a first-ever "minor" mint produces 0.1.0 and a first-ever "patch" mint
    produces 0.0.1 - the standard SemVer-tooling convention, not special-
    cased here.

Usage:
  python3 scripts/ci/next_version.py --bump patch
  python3 scripts/ci/next_version.py --bump minor --tag v0.1.0 --tag v0.2.0
Exit code / output: 0 and the bare "X.Y.Z" string on stdout on success;
1 and an error on stderr if --bump is invalid or tags could not be
determined (git not found/not a repo and --tag not given at all).
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
BUMPS = ("major", "minor", "patch")


def parse_semver(tag: str):
    """'vX.Y.Z' -> (X, Y, Z) ints, or None if tag isn't in that exact form."""
    m = TAG_RE.match(tag.strip())
    if not m:
        return None
    return tuple(int(g) for g in m.groups())


def latest_release_version(tags):
    """Highest (major, minor, patch) among tags parseable by parse_semver,
    or None if none parse."""
    parsed = [v for v in (parse_semver(t) for t in tags) if v is not None]
    return max(parsed) if parsed else None


def bump_version(version, bump):
    """(major, minor, patch) + bump in {"major","minor","patch"} -> the
    bumped (major, minor, patch), following standard SemVer bump rules (a
    minor bump resets patch to 0; a major bump resets minor and patch to
    0)."""
    if bump not in BUMPS:
        raise ValueError(f"invalid bump {bump!r}, expected one of {BUMPS}")
    major, minor, patch = version
    if bump == "major":
        return (major + 1, 0, 0)
    if bump == "minor":
        return (major, minor + 1, 0)
    return (major, minor, patch + 1)


def format_version(version) -> str:
    return "{}.{}.{}".format(*version)


def compute_next_version(tags, bump) -> str:
    """The full computation the workflow needs: latest valid tag among
    `tags` (or an implicit v0.0.0 if none), bumped by `bump`, formatted as
    a bare "X.Y.Z" string (no "v" prefix - the workflow prefixes that
    itself for the actual git tag / GitHub release name)."""
    base = latest_release_version(tags) or (0, 0, 0)
    return format_version(bump_version(base, bump))


def git_tags(root: Path):
    result = subprocess.run(
        ["git", "tag", "--list", "v*"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git tag --list failed: {result.stderr.strip()}")
    return [line for line in result.stdout.splitlines() if line.strip()]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bump", required=True, choices=BUMPS)
    ap.add_argument(
        "--tag",
        action="append",
        default=None,
        help="an existing tag to consider (repeatable). If omitted, reads "
             "every tag in this repo via `git tag --list \"v*\"`.",
    )
    args = ap.parse_args(argv)

    if args.tag is not None:
        tags = args.tag
    else:
        try:
            tags = git_tags(ROOT)
        except RuntimeError as e:
            print(f"next_version: FAIL - {e}", file=sys.stderr)
            return 1

    try:
        next_version = compute_next_version(tags, args.bump)
    except ValueError as e:
        print(f"next_version: FAIL - {e}", file=sys.stderr)
        return 1

    print(next_version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
