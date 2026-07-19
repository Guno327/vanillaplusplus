#!/usr/bin/env python3
"""Fast-tier CI check: scan pack/kubejs/**/*.js for the Rhino
const-directly-in-try scoping bug documented in this repo's DECISIONS.md
(GitHub issue #8, "Rhino `const` audit").

Ground truth, and an important correction to the issue's own prose
(DECISIONS.md's "#8 (Rhino `const` audit)" entry literally says "the actual
trigger is any `const`/`let` declared directly inside a `try { }` block
body" - but that phrasing does not survive contact with the same entry's
own evidence, or with the rest of this codebase, so this checker does NOT
implement it literally):

  - The entry's own fix for `skill_respec.js` was converting its `const`s
    (declared directly in a try, and in a nested try) to `let`, and it
    reports that conversion as VERIFIED via the project's own Rhino harness
    ("before: fails on call 1; after: 3 repeated calls succeed") plus a
    clean L0+L1 boot. If `let` genuinely triggered the same throw, that
    fix could not have worked.
  - Every other try body already in this codebase (leaderboard.js,
    tick_accelerator.js, tool_consolidation_sweep.js, food_cck_gap_patch.js,
    selftest.js, ...) uses `let` - never `const` - for every binding
    declared directly inside a try, consistently described in their own
    comments as "this pack's installed Rhino build... throws
    ... for a const/let declared directly inside a try { } body" while
    then using `let` throughout as "this codebase's established
    workaround". The codebase's actual, boot-tested-clean convention is
    unambiguous: `let` directly in a try is fine; `const` directly in a try
    is not.

Given that, and this checker's own hard requirement of zero false positives
against a codebase "believed clean after the #8 fixes", flagging `let` as
well would immediately produce ~25+ false positives against exactly the
already-applied, boot-verified fix - the opposite of the intended check.
This module therefore flags only `const` declared directly inside a try
block's own statement list; DECISIONS.md's "const/let" wording is treated
as an imprecise summary, not a literal spec, superseded by its own
before/after verification and by the codebase's consistent convention.

Rule actually implemented: a `const` appearing DIRECTLY inside a `try {
... }` block's own statement list (any nesting depth of the try itself,
but the declaration must not be inside a further nested function/block
within that try). `catch { }` and `finally { }` bodies are exempt, and
`for (const x of ...)` / `for (let i = ...; ...)` loop headers are exempt
(the binding lives in the for-loop's own header construct, not a bare
statement in the enclosing block) even when the for-loop itself sits
directly in a try.

Implementation approach (deliberately not a full JS parser, per the issue):
a single-pass character scanner that
  1. masks out comments (`//`, `/* */`), quoted strings, and template
     literals (backtick strings, INCLUDING their `${...}` interpolations -
     the whole template literal is blanked as one unit, since this repo's
     interpolations are simple value expressions with no `try`/const of
     their own to miss), replacing their contents with spaces so keywords
     inside them can't be mistaken for real code, while preserving
     character offsets (and newlines, for line numbers);
  2. tokenizes the remaining "clean" text for exactly three keywords
     (`try`, `for`, `const`) plus the structural characters `{ } ( )`,
     tracking two independent stacks:
       - a brace-frame stack: pushing 'try' when a `{` is immediately
         preceded (skipping only whitespace/blanked comments) by the
         keyword `try` - which JS grammar guarantees is always immediately
         followed by that block's own `{`, no parens allowed - and 'other'
         for every other `{` (catch/finally/if/while/function/object-
         literal/destructuring-pattern/... all default to 'other', which
         is exactly the "don't flag" outcome for all of them);
       - a paren stack marking whether the immediately-enclosing `(...)` is
         a `for (...)` header (again guaranteed adjacent by JS grammar) -
         used only to exempt a `const` written inside a for-loop's own
         header.
  3. flags every `const` keyword occurrence whose innermost brace frame is
     'try' AND which is not inside an active for-header paren.

Verified against this repo's actual pack/kubejs tree (believed clean since
issue #8's fix, commit 653a024): zero findings. In particular this
correctly does NOT flag: every `let X = null; try { X = ... } catch``
pattern (leaderboard.js, selftest.js, food_selftest.js, tick_accelerator.js,
skill_respec.js); tick_accelerator.js's `const FALLBACK_KINETIC_IDS = [...]`
(sits directly in a `catch (e) { }` body, correctly exempt); and
skill_respec.js's `for (const nodeId of nodeIds)` (directly in a try body,
correctly exempt as a for-of header).

Usage: python3 scripts/ci/lint_rhino.py [root]
Exit code: 0 if no true positives found, 1 otherwise.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
KUBEJS_DIR_REL = Path("pack") / "kubejs"

_IDENT_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_$")


def _is_ident_char(ch):
    return ch in _IDENT_CHARS


def _skip_simple_string(text, i):
    """i points at an opening ' or ". Returns index just past the matching
    (unescaped) closing quote, or len(text) if unterminated."""
    quote = text[i]
    n = len(text)
    i += 1
    while i < n:
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == quote:
            return i + 1
        i += 1
    return n


def _skip_template_literal(text, i):
    """i points at an opening backtick. Returns index just past the matching
    closing backtick, correctly handling nested `${ ... }` expressions
    (which may themselves contain strings/backticks/comments), without
    treating a backtick found inside such an expression as the terminator.
    Returns len(text) if unterminated."""
    n = len(text)
    i += 1
    depth = 0  # brace depth once inside a ${...} expression
    while i < n:
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if depth == 0:
            if c == "`":
                return i + 1
            if c == "$" and i + 1 < n and text[i + 1] == "{":
                depth = 1
                i += 2
                continue
            i += 1
        else:
            if c == "`":
                i = _skip_template_literal(text, i)
                continue
            if c in "\"'":
                i = _skip_simple_string(text, i)
                continue
            if c == "/" and i + 1 < n and text[i + 1] == "/":
                j = text.find("\n", i)
                i = n if j == -1 else j
                continue
            if c == "/" and i + 1 < n and text[i + 1] == "*":
                j = text.find("*/", i + 2)
                i = n if j == -1 else j + 2
                continue
            if c == "{":
                depth += 1
                i += 1
                continue
            if c == "}":
                depth -= 1
                i += 1
                continue
            i += 1
    return n


def mask_source(text):
    """Return a same-length copy of text with comment/string/template
    contents replaced by spaces (newlines preserved), so a plain keyword
    scan over the result can't be confused by code-shaped text inside
    strings/comments."""
    n = len(text)
    out = list(text)

    def blank_range(start, end):
        for k in range(start, end):
            if out[k] != "\n":
                out[k] = " "

    i = 0
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            end = n if j == -1 else j
            blank_range(i, end)
            i = end
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            end = n if j == -1 else j + 2
            blank_range(i, end)
            i = end
            continue
        if c == '"' or c == "'":
            end = _skip_simple_string(text, i)
            blank_range(i, end)
            i = end
            continue
        if c == "`":
            end = _skip_template_literal(text, i)
            blank_range(i, end)
            i = end
            continue
        i += 1
    return "".join(out)


_TOKEN_RE = re.compile(r"\b(try|for|const)\b|[{}()]")


def find_try_scoped_declarations(text):
    """Return a list of (line, col, keyword) for every `const` occurrence
    that sits directly in a try block's own statement list (not inside a
    nested block/function, not inside a for-header). See module docstring
    for why `let` is deliberately not flagged."""
    clean = mask_source(text)
    findings = []

    brace_stack = []  # entries: 'try' | 'other'
    paren_stack = []  # entries: 'for' | 'other'
    prev_captured = None  # the previous token string from _TOKEN_RE

    # precompute line-start offsets for fast index -> (line, col)
    line_starts = [0]
    for idx, ch in enumerate(text):
        if ch == "\n":
            line_starts.append(idx + 1)

    def pos_of(index):
        # binary search for the line containing `index`
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= index:
                lo = mid
            else:
                hi = mid - 1
        line = lo + 1
        col = index - line_starts[lo] + 1
        return line, col

    for m in _TOKEN_RE.finditer(clean):
        tok = m.group()
        if tok == "{":
            frame = "try" if prev_captured == "try" else "other"
            brace_stack.append(frame)
        elif tok == "}":
            if brace_stack:
                brace_stack.pop()
        elif tok == "(":
            kind = "for" if prev_captured == "for" else "other"
            paren_stack.append(kind)
        elif tok == ")":
            if paren_stack:
                paren_stack.pop()
        elif tok == "const":
            in_for_header = bool(paren_stack) and paren_stack[-1] == "for"
            in_try_body = bool(brace_stack) and brace_stack[-1] == "try"
            if in_try_body and not in_for_header:
                line, col = pos_of(m.start())
                findings.append((line, col, tok))
        prev_captured = tok

    return findings


def _is_excluded(path):
    return False  # see module note below - nothing currently excluded


def find_files(kubejs_dir):
    return sorted(p for p in kubejs_dir.rglob("*.js") if p.is_file() and not _is_excluded(p))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else REPO_ROOT
    kubejs_dir = root / KUBEJS_DIR_REL

    if not kubejs_dir.is_dir():
        print(f"lint_rhino: FAIL - kubejs directory not found at {kubejs_dir}", file=sys.stderr)
        return 1

    files = find_files(kubejs_dir)
    all_findings = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            all_findings.append((path, [(0, 0, f"could not read file: {e}")]))
            continue
        findings = find_try_scoped_declarations(text)
        if findings:
            all_findings.append((path, findings))

    if all_findings:
        total = sum(len(f) for _, f in all_findings)
        print(f"lint_rhino: FAIL - {total} const-directly-in-try occurrence(s) "
              f"in {len(all_findings)} file(s):")
        for path, findings in all_findings:
            try:
                rel = path.relative_to(REPO_ROOT)
            except ValueError:
                rel = path
            for line, col, tok in findings:
                print(f"  {rel}:{line}:{col}: `{tok}` declared directly inside a try block "
                      f"- use `let` instead (Rhino redeclaration bug, see DECISIONS.md #8)")
        return 1

    print(f"lint_rhino: PASS - {len(files)} file(s) scanned, no const directly in a try block")
    return 0


if __name__ == "__main__":
    sys.exit(main())
