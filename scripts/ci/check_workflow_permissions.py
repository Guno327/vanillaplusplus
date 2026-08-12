#!/usr/bin/env python3
"""Fast-tier CI check: every GitHub Actions workflow under .github/workflows/
declares an explicit `permissions:` scope (never falls back to the repo
default) and never grants more than it uses.

GitHub issue #188, a follow-up to #184 ("least-privilege token" pass over
this repo's workflows): #184 hand-audited every workflow once and pinned
explicit `permissions:` blocks, but nothing enforced that pin going
forward - a future PR could add a workflow with no `permissions:` at all
(silently falling back to the *repository's* default token permissions,
which is write-all unless an org/repo admin has hardened it - not
something this repo's own YAML controls or CI can see), or add a `gh
release create`/`gh pr create`/... call to an existing read-only workflow
without remembering to widen its scope. This script is the regression
guard for both directions.

PyYAML is NOT available (stdlib-only, no pip installs - see repo CI
conventions). Rather than hand-roll a general YAML parser (a rabbit hole:
flow collections, anchors, multi-document streams, ambiguous scalar
folding, ...), this is a deliberately NARROW, indentation-based
line scanner that only understands the handful of shapes GitHub Actions
workflow YAML actually uses for the three things this check needs:

  1. A top-level `permissions:` key (scalar `write-all`/`read-all`, an
     explicit empty flow mapping `{}`, or a block mapping of
     `scope: read|write|none`).
  2. Each top-level job under `jobs:` and that job's own (optional)
     `permissions:` key, in the same three shapes.
  3. Every `run:` step script's text within each job (single-line scalar
     or a `|`/`>`-style block scalar), to scan for GitHub write
     operations.

Anything this scanner can't confidently make sense of (tabs, a
`permissions:` block whose shape it doesn't recognise, a `jobs:` key it
can't find) is a LOUD parse failure (raises WorkflowParseError, caught in
main() and reported as a FAIL) - never a silent pass. A validator that
quietly no-ops on a file it couldn't parse is worse than no validator at
all, because it looks green.

KNOWN LIMITATIONS of this narrow parser (acceptable for this repo's own
workflows, ground-truthed by running it against all six of them - see
this file's CLI and scripts/ci/tests/test_check_workflow_permissions.py's
"real .github/workflows/ passes" case):
  - Does not understand YAML anchors/aliases, multi-document streams, or
    flow-style mappings other than the literal empty `{}`.
  - `run:` extraction is a blind textual scan for a `run:` key at any
    depth inside a job's body - it does not verify the key is actually
    sitting inside a `steps:` list item map (vs., hypothetically, some
    other job-level key named `run` - GitHub Actions workflow schema has
    no such key today, so this is a theoretical gap, not an observed one).
  - Only inspects `run:` step script text for the write-operation
    patterns below; it does not follow `uses: some/action@vN` third-party
    actions (those need their own review, out of scope for this script -
    a job that ONLY calls actions and never runs a `gh`/`curl` command
    that this scanner recognises will simply have no detected write ops).

Usage: python3 scripts/ci/check_workflow_permissions.py [root]
Exit code: 0 if every workflow passes, 1 otherwise.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORKFLOWS_DIR_REL = Path(".github") / "workflows"

# Scopes this check understands, and the exact `gh`/`gh api` invocation
# shapes that require each one. Order doesn't matter; every pattern is
# checked against every run: script independently.
#
# `gh api -X POST/PATCH/PUT/DELETE` (or --method) is deliberately treated
# as "needs ANY one write scope" rather than mapped to a specific scope:
# `gh api` can hit arbitrary REST endpoints (issues, PRs, releases,
# arbitrary repo content, org resources, ...) and this script has no way
# to know which one from the command line alone. Requiring at least one
# write scope catches the "read: only, no write scope declared, does a
# raw POST anyway" case (the actual #184 failure mode) without guessing
# a specific (and possibly wrong) scope. See _GENERIC_API_WRITE_RE below.
_WRITE_OP_PATTERNS = [
    # (label, compiled regex, required scope)
    ("gh release create/upload/edit/delete",
     re.compile(r"\bgh\s+release\s+(create|upload|edit|delete)\b"), "contents"),
    ("gh pr create/merge/edit/close",
     re.compile(r"\bgh\s+pr\s+(create|merge|edit|close)\b"), "pull-requests"),
    ("gh issue create/comment/edit/close",
     re.compile(r"\bgh\s+issue\s+(create|comment|edit|close)\b"), "issues"),
    ("gh workflow run",
     re.compile(r"\bgh\s+workflow\s+run\b"), "actions"),
]

# `gh api ... -X POST|PATCH|PUT|DELETE` or `--method POST|...` - see the
# "generic gh api" comment above for why this maps to "any write scope"
# rather than one specific scope.
_GENERIC_API_WRITE_RE = re.compile(
    r"\bgh\s+api\b.*?(?:-X|--method)\s+(POST|PATCH|PUT|DELETE)\b", re.IGNORECASE)

# The scopes recognised above, in the order they're reported when a
# generic `gh api` write needs "any one of" them.
_ALL_WRITE_SCOPES = ("contents", "pull-requests", "issues", "actions")

_WRITE_VALUES = {"write", "write-all"}


class WorkflowParseError(Exception):
    """Raised when this narrow scanner cannot confidently make sense of a
    workflow file's structure. Caller must treat this as a hard FAIL, not
    swallow it - see this module's docstring."""


def _indent(line):
    stripped = line.lstrip(" ")
    return len(line) - len(stripped)


def _line_is_blank_or_comment(line):
    s = line.strip()
    return s == "" or s.startswith("#")


def _split_lines(text, filename):
    if "\t" in text:
        raise WorkflowParseError(
            f"{filename}: contains a tab character - this scanner only understands "
            "space-indented YAML (GitHub Actions workflows never use tabs anyway)")
    return text.split("\n")


def _key_and_inline_value(line):
    """If `line` (after stripping an optional leading '- ' list-item
    marker) is of the form `key:` or `key: value`, returns
    (key, inline_value_or_None, key_column). Otherwise returns None.
    key_column is the column the key itself starts at, i.e. after any
    '- ' prefix - this is the indent used to find this key's children."""
    stripped = line.lstrip(" ")
    leading = len(line) - len(stripped)
    if stripped.startswith("- "):
        stripped = stripped[2:]
        leading += 2
    elif stripped == "-":
        return None
    m = re.match(r"^([A-Za-z0-9_.\-]+):(?:\s+(.*))?$", stripped)
    if not m:
        return None
    key, value = m.group(1), m.group(2)
    if value is not None:
        value = value.strip()
        if value == "":
            value = None
    return key, value, leading


def _collect_block(lines, start_idx, key_indent):
    """Given lines[start_idx] is a `key:` line at column key_indent whose
    value is on following lines, returns (block_lines_with_orig_indent,
    end_idx) where block_lines are every subsequent line more indented
    than key_indent (blank/comment lines inside are kept verbatim so
    block-scalar content isn't corrupted), stopping at the first line
    whose indent is <= key_indent (or EOF)."""
    block = []
    i = start_idx + 1
    while i < len(lines):
        line = lines[i]
        if line.strip() == "":
            block.append(line)
            i += 1
            continue
        if _indent(line) <= key_indent:
            break
        block.append(line)
        i += 1
    return block, i


def _parse_permissions_value(lines, idx, filename, context):
    """lines[idx] is a `permissions:` line (already located). Returns
    (permissions_result, next_idx) where permissions_result is one of:
      - "write-all" / "read-all"  (scalar shorthand)
      - {}                        (explicit empty mapping - grants nothing)
      - {scope: value, ...}       (block mapping)
    Raises WorkflowParseError if the shape isn't one of the above."""
    parsed = _key_and_inline_value(lines[idx])
    if parsed is None:
        raise WorkflowParseError(f"{filename}: {context}: could not parse 'permissions:' line: {lines[idx]!r}")
    _key, inline_value, key_col = parsed

    if inline_value is not None:
        if inline_value == "{}":
            return {}, idx + 1
        if inline_value in ("write-all", "read-all"):
            return inline_value, idx + 1
        raise WorkflowParseError(
            f"{filename}: {context}: 'permissions:' has an inline value this scanner "
            f"doesn't recognise ({inline_value!r}) - expected 'write-all', 'read-all', "
            "'{}', or a block mapping of scope: value on following lines")

    block, next_idx = _collect_block(lines, idx, key_col)
    result = {}
    for line in block:
        if _line_is_blank_or_comment(line):
            continue
        parsed_child = _key_and_inline_value(line)
        if parsed_child is None:
            raise WorkflowParseError(
                f"{filename}: {context}: unrecognised line inside 'permissions:' block: {line!r}")
        scope, value, _col = parsed_child
        if value is None:
            raise WorkflowParseError(
                f"{filename}: {context}: permissions scope {scope!r} has no value on line: {line!r}")
        result[scope] = value.strip('"\'')
    return result, next_idx


def _find_top_level_key(lines, key):
    """Returns the index of a line declaring `key:` at column 0, or None.
    Only the FIRST such occurrence is used - a repeated top-level key is a
    YAML error we don't need to specially detect (later value would just
    silently win in real YAML too)."""
    for i, line in enumerate(lines):
        if _line_is_blank_or_comment(line):
            continue
        if _indent(line) != 0:
            continue
        parsed = _key_and_inline_value(line)
        if parsed and parsed[0] == key:
            return i
    return None


def _extract_run_texts(job_body_lines):
    """Scans every line of a job's body (already de-indented as raw text)
    for `run:` keys at ANY depth (see module docstring's "KNOWN
    LIMITATIONS" for why this is deliberately loose) and returns a single
    concatenated string of every run script's text, for write-op
    scanning."""
    texts = []
    i = 0
    n = len(job_body_lines)
    while i < n:
        line = job_body_lines[i]
        if not _line_is_blank_or_comment(line):
            parsed = _key_and_inline_value(line)
            if parsed and parsed[0] == "run":
                _key, inline_value, key_col = parsed
                if inline_value is None:
                    # `run:` with no inline value and no block scalar
                    # indicator - nothing follows on this line; treat the
                    # (rare/malformed) case as "no script text" rather
                    # than guessing.
                    i += 1
                    continue
                if inline_value[0] in "|>":
                    block, next_i = _collect_block(job_body_lines, i, key_col)
                    texts.append("\n".join(block))
                    i = next_i
                    continue
                texts.append(inline_value)
        i += 1
    return "\n".join(texts)


def _parse_jobs(lines, filename):
    """Returns {job_name: {"permissions": <see _parse_permissions_value>
    or None, "run_text": str}}. Raises WorkflowParseError if `jobs:`
    itself can't be found/parsed - every workflow in this repo has one."""
    jobs_idx = _find_top_level_key(lines, "jobs")
    if jobs_idx is None:
        raise WorkflowParseError(f"{filename}: no top-level 'jobs:' key found")

    jobs_block, _end = _collect_block(lines, jobs_idx, 0)
    if not jobs_block:
        raise WorkflowParseError(f"{filename}: 'jobs:' block is empty")

    # The first non-blank line's indent is the job-name indent; every
    # sibling job name must sit at that same column.
    job_indent = None
    for line in jobs_block:
        if _line_is_blank_or_comment(line):
            continue
        job_indent = _indent(line)
        break
    if job_indent is None:
        raise WorkflowParseError(f"{filename}: 'jobs:' block has no content")

    jobs = {}
    i = 0
    n = len(jobs_block)
    while i < n:
        line = jobs_block[i]
        if _line_is_blank_or_comment(line) or _indent(line) != job_indent:
            i += 1
            continue
        parsed = _key_and_inline_value(line)
        if parsed is None:
            raise WorkflowParseError(f"{filename}: expected a job name at 'jobs:' line: {line!r}")
        job_name, inline_value, key_col = parsed
        if inline_value is not None:
            raise WorkflowParseError(
                f"{filename}: job {job_name!r} has an unexpected inline value {inline_value!r}")
        job_body, next_i = _collect_block(jobs_block, i, key_col)

        # A job's OWN permissions: key must be a direct child of the job
        # (i.e. at the same indent as the job body's first line, e.g.
        # `runs-on:`/`uses:`/`needs:`) - not some unrelated nested
        # `permissions:` several levels deeper (no such key exists in this
        # repo's workflows today, but guard the column match anyway).
        job_direct_child_indent = None
        for jline in job_body:
            if not _line_is_blank_or_comment(jline):
                job_direct_child_indent = _indent(jline)
                break

        job_permissions = None
        for j, jline in enumerate(job_body):
            if _line_is_blank_or_comment(jline):
                continue
            if _indent(jline) != job_direct_child_indent:
                continue
            jparsed = _key_and_inline_value(jline)
            if jparsed and jparsed[0] == "permissions":
                job_permissions, _ = _parse_permissions_value(job_body, j, filename, f"job {job_name!r}")
                break

        run_text = _extract_run_texts(job_body)
        jobs[job_name] = {"permissions": job_permissions, "run_text": run_text}
        i = next_i

    return jobs


def parse_workflow(text, filename):
    """Returns (top_permissions, jobs) - see _parse_permissions_value /
    _parse_jobs for shapes. Raises WorkflowParseError on anything this
    narrow scanner can't confidently make sense of."""
    lines = _split_lines(text, filename)

    top_permissions = None
    perm_idx = _find_top_level_key(lines, "permissions")
    if perm_idx is not None:
        top_permissions, _ = _parse_permissions_value(lines, perm_idx, filename, "top-level")

    jobs = _parse_jobs(lines, filename)
    return top_permissions, jobs


def _effective_scopes(permissions):
    """permissions is whatever _parse_permissions_value returned (or
    None). Returns the set of scopes that are actually granted WRITE
    access, for write-op sufficiency checks. write-all grants everything;
    read-all/None/{} grant nothing; a block mapping grants exactly the
    scopes whose value is 'write' (or, degenerately, 'write-all' as a
    per-scope value, which isn't real GHA syntax but treated the same if
    seen)."""
    if permissions == "write-all":
        return set(_ALL_WRITE_SCOPES) | {"*"}
    if permissions in (None, "read-all") or not isinstance(permissions, dict):
        return set()
    return {scope for scope, value in permissions.items() if value in _WRITE_VALUES}


def _has_explicit_declaration(permissions):
    """True if `permissions` represents an ACTUAL explicit declaration -
    including an explicit empty mapping {} (which deliberately grants
    nothing) - as opposed to None (key absent entirely)."""
    return permissions is not None


def check_workflow_permissions(root):
    """Returns (errors, stats). errors is a list of human-readable
    strings (empty == every workflow in .github/workflows/ passes)."""
    errors = []
    stats = {"files": 0}

    workflows_dir = root / WORKFLOWS_DIR_REL
    if not workflows_dir.is_dir():
        return ([f".github/workflows directory not found: {workflows_dir}"], stats)

    paths = sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml"))
    if not paths:
        return ([f"no *.yml/*.yaml files found under {workflows_dir}"], stats)

    for path in paths:
        stats["files"] += 1
        rel = path.name
        text = path.read_text(encoding="utf-8")

        try:
            top_permissions, jobs = parse_workflow(text, rel)
        except WorkflowParseError as e:
            errors.append(f"{rel}: PARSE FAILURE - {e}")
            continue

        # ---- rule (a): every job must be covered by an explicit grant ----
        # Strict form: a workflow passes only if it has a top-level
        # permissions: block (which covers every job in the file, since a
        # job without its own block inherits it) OR every single job
        # declares its own permissions: block. A top-level block that's
        # missing while even ONE job has no block of its own means that
        # job silently falls back to the repository default token - the
        # #184 failure mode this check exists to catch - so that's a
        # per-job FAIL naming the specific job.
        #
        # This used to be relaxed to a file-level "at least one
        # declaration somewhere" check because this repo's own
        # mint-release.yml had no top-level block and left three jobs
        # (compute-version/fast-tier/boot-tier) with no permissions: of
        # their own - a real, silent fallback, not a false positive. #188
        # fixed that workflow (added a `contents: read` top-level floor,
        # with the one write-performing job opting up via its own
        # job-level block) instead of relaxing this check further, so the
        # strict rule is achievable and enforced here. Do not re-relax
        # this without fixing the underlying workflow first - a passing
        # validator that tolerates a silent-fallback job is worse than a
        # failing one.
        if not _has_explicit_declaration(top_permissions):
            uncovered_jobs = [name for name, job in jobs.items() if job["permissions"] is None]
            for job_name in uncovered_jobs:
                errors.append(
                    f"{rel}: job {job_name!r} has no 'permissions:' block of its own and "
                    "the file has no top-level 'permissions:' block either - this job's "
                    "token falls back to the repository default, which is write-all "
                    "unless hardened outside this repo's own YAML; declare an explicit "
                    "permissions: block (top-level, covering every job, or on this job "
                    "specifically)")
            if uncovered_jobs:
                continue

        # ---- rule (b): write-all is always a FAIL ----
        if top_permissions == "write-all":
            errors.append(f"{rel}: top-level permissions: write-all - grants every write scope, must be scoped down")
        for job_name, job in jobs.items():
            if job["permissions"] == "write-all":
                errors.append(f"{rel}: job {job_name!r} permissions: write-all - grants every write scope, must be scoped down")

        # ---- rule (c): every write op must have a matching write scope ----
        for job_name, job in jobs.items():
            effective = job["permissions"] if job["permissions"] is not None else top_permissions
            granted_write_scopes = _effective_scopes(effective)
            run_text = job["run_text"]

            for label, pattern, needed_scope in _WRITE_OP_PATTERNS:
                m = pattern.search(run_text)
                if not m:
                    continue
                if needed_scope not in granted_write_scopes and "*" not in granted_write_scopes:
                    errors.append(
                        f"{rel}: job {job_name!r} runs {label!r} ({m.group(0)!r}) but its "
                        f"effective permissions do not grant '{needed_scope}: write' "
                        f"(effective permissions: {effective!r})")

            api_match = _GENERIC_API_WRITE_RE.search(run_text)
            if api_match and not granted_write_scopes:
                errors.append(
                    f"{rel}: job {job_name!r} runs a write 'gh api' call ({api_match.group(0)!r}) "
                    "but its effective permissions grant no write scope at all "
                    f"(need at least one of {_ALL_WRITE_SCOPES}; effective permissions: {effective!r})")

    return errors, stats


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else REPO_ROOT

    errors, stats = check_workflow_permissions(root)

    if errors:
        print(f"check_workflow_permissions: FAIL - {len(errors)} issue(s):")
        for err in errors:
            print(f"  {err}")
        return 1

    print(f"check_workflow_permissions: PASS - {stats['files']} workflow file(s), "
          "all declare explicit permissions and no under-scoped write operations found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
