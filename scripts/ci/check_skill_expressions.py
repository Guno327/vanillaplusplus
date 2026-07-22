#!/usr/bin/env python3
"""Fast-tier CI check: every expression string emitted into the
puffish_skills datapack (pack/kubejs/data/puffish_skills/puffish_skills/)
only uses identifiers puffish_skills' own expression engine actually
understands.

Written for issue #79 ("skill-tree datapack does not load at all on
main"): issue #71 set `EXPERIENCE_EXPR = "70 * pow(1.13, level)"` in
scripts/gen_skill_tree.py, assuming `pow` was a function in puffish_skills'
expression grammar. It is not. At boot, puffish_skills' parser
(net.puffish.skillsmod.expression.DefaultParser) rejects the WHOLE
datapack entry for any category whose expression references an unknown
identifier - "Unknown variable `pow`" - once per category, so all 23
categories vanished at runtime with no other symptom in the boot log
besides that one line repeated 23 times. Nothing in the previously-existing
CI suite caught this: check_skill_trees.py's own experience-curve sampler
(_eval_experience_expr) hand-implements just enough arithmetic to sample
the curve's shape and would happily "evaluate" `pow(...)` using Python's
own builtin if it were still spelled that way - it was never a vocabulary
check against the real engine, so a typo'd/invented identifier sailed
through it silently. This script is that missing vocabulary check: static,
pre-boot, and it fails loudly on any identifier the mod's parser would
reject, instead of a full-pack blackout only visible in a live L1 boot log.

Usage: python3 scripts/ci/check_skill_expressions.py [root]
Exit code: 0 if every expression only references known vocabulary, 1
otherwise.
"""
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# The complete identifier vocabulary net.puffish.skillsmod.expression.
# DefaultParser registers, extracted by javap'ing
# puffish_skills-0.18.1-1.21-neoforge.jar's DefaultParser.class (its static
# initializer builds CONSTANTS/BINARY_OPERATORS/UNARY_OPERATORS/FUNCTIONS
# from literal String constants - read directly off the bytecode, not
# guessed or copied from docs). `pow` is deliberately NOT in this set - see
# this file's module docstring for why that matters (issue #79). Only
# alphabetic identifiers are listed here; symbolic operators (`^`, `!`,
# `&`, `|`, `=`, `<>`, `>=`, `<=`, `>`, `<`, `+`, `-`, `*`, `/`) aren't
# identifiers and this checker's tokenizer never extracts them as one.
PUFFISH_EXPRESSION_VOCAB = frozenset({
    # constants (DefaultParser.CONSTANTS)
    "e", "pi", "tau",
    # functions (DefaultParser.FUNCTIONS, all 26 registered FunctionOperators)
    "abs", "acos", "asin", "atan", "atan2", "cbrt", "ceil", "clamp", "cos",
    "cosh", "exp", "floor", "fract", "log", "max", "min", "mix", "mod",
    "round", "sign", "sin", "sinh", "sqrt", "tan", "tanh", "trunc",
})

# Matches one identifier token: a leading letter or underscore, then any
# run of letters/digits/underscores (variable names in this repo's
# generated expressions are snake_case, e.g. `silk_touch`, `dropped_xp` -
# see gen_skill_tree.py's ExperienceSource helpers). A leading digit is
# deliberately excluded so a numeric literal like `1.13` is never
# misparsed as touching an identifier; `^`, `!`, `&`, `.`, etc. simply
# aren't in the character class, so they never show up as "identifiers"
# here either.
_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _skills_root(root):
    return root / "pack" / "kubejs" / "data" / "puffish_skills" / "puffish_skills"


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path, root):
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _check_expression(expr, in_scope_vars, location, errors):
    """Tokenizes `expr` and flags any identifier that is neither in
    PUFFISH_EXPRESSION_VOCAB nor a name in `in_scope_vars` (the variables
    legitimately declared for this expression's own scope)."""
    if not isinstance(expr, str):
        errors.append(f"{location}: expected a string expression, got {expr!r}")
        return
    for identifier in _IDENTIFIER_RE.findall(expr):
        if identifier in PUFFISH_EXPRESSION_VOCAB or identifier in in_scope_vars:
            continue
        errors.append(
            f"{location}: expression {expr!r} references unknown identifier "
            f"{identifier!r} - it is not one of puffish_skills' own constants/"
            "functions (PUFFISH_EXPRESSION_VOCAB, javap'd from DefaultParser) "
            f"and not one of this expression's in-scope variables {sorted(in_scope_vars)} "
            "- puffish_skills' parser rejects the WHOLE category's datapack "
            "entry on an unknown identifier at boot (issue #79's exact bug)"
        )


def check_skill_expressions(root):
    """Returns (errors, stats) - errors is a list of human-readable
    strings (empty == every expression only uses known vocabulary)."""
    errors = []
    stats = {"files": 0, "expressions": 0}

    skills_root = _skills_root(root)
    if not skills_root.is_dir():
        return ([f"puffish_skills datapack root not found: {skills_root}"], stats)

    for experience_json in sorted(skills_root.glob("categories/*/experience.json")):
        stats["files"] += 1
        try:
            experience = _load_json(experience_json)
        except json.JSONDecodeError as e:
            errors.append(f"{_rel(experience_json, root)}: JSON parse error: {e}")
            continue
        if not isinstance(experience, dict):
            errors.append(f"{_rel(experience_json, root)}: not a JSON object")
            continue

        rel = _rel(experience_json, root)

        # ---- experience_per_level.data.expression: scope is just `level` ----
        epl = experience.get("experience_per_level")
        if isinstance(epl, dict):
            epl_data = epl.get("data", {}) or {}
            expr = epl_data.get("expression")
            if expr is not None:
                stats["expressions"] += 1
                _check_expression(
                    expr, {"level"},
                    f"{rel}: experience_per_level.data.expression", errors,
                )

        # ---- sources[*].data.{variables,experience[*].condition/expression} ----
        for src_idx, source in enumerate(experience.get("sources", []) or []):
            if not isinstance(source, dict):
                continue
            src_data = source.get("data", {}) or {}
            if not isinstance(src_data, dict):
                continue
            variables = src_data.get("variables", {}) or {}
            in_scope = set(variables) if isinstance(variables, dict) else set()

            for xp_idx, entry in enumerate(src_data.get("experience", []) or []):
                if not isinstance(entry, dict):
                    continue
                location_prefix = f"{rel}: sources[{src_idx}].data.experience[{xp_idx}]"
                if "condition" in entry:
                    stats["expressions"] += 1
                    _check_expression(
                        entry["condition"], in_scope,
                        f"{location_prefix}.condition", errors,
                    )
                if "expression" in entry:
                    stats["expressions"] += 1
                    _check_expression(
                        entry["expression"], in_scope,
                        f"{location_prefix}.expression", errors,
                    )

    return errors, stats


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else REPO_ROOT

    errors, stats = check_skill_expressions(root)

    if errors:
        print(f"check_skill_expressions: FAIL - {len(errors)} issue(s):")
        for err in errors:
            print(f"  {err}")
        return 1

    print(
        "check_skill_expressions: PASS - "
        f"{stats['files']} experience.json file(s), "
        f"{stats['expressions']} expression(s) checked, all use known vocabulary"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
