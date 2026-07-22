#!/usr/bin/env python3
"""Fast-tier CI check: cross-verifies pack/kubejs/server_scripts/selftest.js's
hand-maintained puffish_skills constants (ST_SKILL_CATEGORIES,
ST_SKILL_NODE_COUNT_PER_CATEGORY) against the actually-generated datapack
under pack/kubejs/data/puffish_skills/puffish_skills/.

GitHub issue #77: issue #71 ("Expand Skill Trees / Categories") expanded the
skill trees from 12 categories x 15 nodes to 23 categories x 34 nodes.
selftest.js was updated for the category LIST but the per-category node
count assertion was left hardcoded at 15 - so every one of the 23 categories
failed the "retained full node count after parsing" L1 check
(scripts/tests/l1_selftest.py) with `count !== 15` reporting `=34` for all
23, right after a PR had *just* shipped 34. ST_SKILL_CATEGORIES itself only
avoided the same drift by luck - nothing enforced it either.

selftest.js is Rhino JS, not Python, so its constants can't be imported
directly; this check textually extracts them the same way
check_advancements.py's _load_quest_ids() pulls `const QUEST_CHAPTERS = `
out of quests.js (see that function for the precedent this follows).

Why this belongs in the fast tier and not just L1: L1 boots a real server
and takes minutes; this is the check that's supposed to catch drift in
seconds, pre-boot, on every commit - the same rationale
check_skill_trees.py's own module docstring gives for why *that* check
exists instead of relying on L1 alone. L1 still separately re-verifies the
live parsed counts (a bad "definition" reference silently drops a node at
runtime without touching the raw generated JSON - see
check_skill_trees.py's docstring and selftest.js's own comment above the
node-count check for the full explanation of why both checks are needed).
This check only proves selftest.js's *source* is honest about what the
generated data actually contains.

Usage: python3 scripts/ci/check_selftest_skill_sync.py [root]
Exit code: 0 if selftest.js's constants match the generated data, 1 otherwise.
"""
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

SELFTEST_JS_REL = Path("pack") / "kubejs" / "server_scripts" / "selftest.js"
SKILLS_CONFIG_REL = Path("pack") / "kubejs" / "data" / "puffish_skills" / "puffish_skills" / "config.json"
CATEGORIES_DIR_REL = Path("pack") / "kubejs" / "data" / "puffish_skills" / "puffish_skills" / "categories"

CATEGORIES_MARKER = "const ST_SKILL_CATEGORIES = "
NODE_COUNT_MARKER = "const ST_SKILL_NODE_COUNT_PER_CATEGORY = "


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_categories(text):
    """Pull the ST_SKILL_CATEGORIES string array out of selftest.js. It's a
    plain JS array literal of single-quoted strings (with a trailing comma
    before `]`), which is NOT valid JSON, so this
    slices out the `[...]` body after the marker and regex-matches every
    quoted string inside it - deliberately not a full JS parser, just enough
    for this one known shape (same "textual extraction, not a real parser"
    approach check_advancements.py's _load_quest_ids() precedent uses,
    adapted because this literal isn't JSON-shaped)."""
    idx = text.find(CATEGORIES_MARKER)
    if idx < 0:
        return None
    start = idx + len(CATEGORIES_MARKER)
    end = text.find("]", start)
    if end < 0:
        return None
    body = text[start:end]
    return [m.group(1) for m in re.finditer(r"'([^']*)'", body)]


def _extract_node_count(text):
    """Pull the ST_SKILL_NODE_COUNT_PER_CATEGORY integer literal out of
    selftest.js."""
    idx = text.find(NODE_COUNT_MARKER)
    if idx < 0:
        return None
    start = idx + len(NODE_COUNT_MARKER)
    m = re.match(r"\s*(\d+)", text[start:start + 32])
    if not m:
        return None
    return int(m.group(1))


def check_selftest_skill_sync(root=REPO_ROOT):
    errors = []
    stats = {}

    selftest_path = root / SELFTEST_JS_REL
    if not selftest_path.is_file():
        return [f"{SELFTEST_JS_REL} does not exist"], stats
    text = selftest_path.read_text(encoding="utf-8")

    js_categories = _extract_categories(text)
    if js_categories is None:
        return [f"could not find `{CATEGORIES_MARKER.strip()}` in {SELFTEST_JS_REL}"], stats
    if not js_categories:
        return [f"{SELFTEST_JS_REL}: ST_SKILL_CATEGORIES parsed as empty"], stats

    js_node_count = _extract_node_count(text)
    if js_node_count is None:
        return [f"could not find `{NODE_COUNT_MARKER.strip()}` in {SELFTEST_JS_REL}"], stats

    stats["selftest_categories"] = len(js_categories)
    stats["selftest_node_count_per_category"] = js_node_count

    config_path = root / SKILLS_CONFIG_REL
    if not config_path.is_file():
        return [f"{SKILLS_CONFIG_REL} does not exist"], stats
    try:
        config = _load_json(config_path)
    except json.JSONDecodeError as e:
        return [f"{SKILLS_CONFIG_REL}: JSON parse error: {e}"], stats

    real_categories = config.get("categories", [])
    if not real_categories:
        return [f"{SKILLS_CONFIG_REL}: 'categories' list is empty"], stats

    stats["generated_categories"] = len(real_categories)

    # ---- category id set: selftest.js's ST_SKILL_CATEGORIES vs the real
    # generated config.json category list ----
    js_set = set(js_categories)
    real_set = set(real_categories)
    if js_set != real_set:
        missing = real_set - js_set
        extra = js_set - real_set
        if missing:
            errors.append(
                f"{SELFTEST_JS_REL}: ST_SKILL_CATEGORIES is missing {len(missing)} "
                f"categories present in the generated data: {sorted(missing)}"
            )
        if extra:
            errors.append(
                f"{SELFTEST_JS_REL}: ST_SKILL_CATEGORIES has {len(extra)} "
                f"categories not present in the generated data (stale/typo'd): {sorted(extra)}"
            )
    if len(js_categories) != len(set(js_categories)):
        dupes = sorted({c for c in js_categories if js_categories.count(c) > 1})
        errors.append(f"{SELFTEST_JS_REL}: ST_SKILL_CATEGORIES has duplicate id(s): {dupes}")

    # ---- per-category node count: selftest.js's
    # ST_SKILL_NODE_COUNT_PER_CATEGORY vs every generated categories/*/
    # skills.json entry count ----
    bad_counts = []
    for cat_id in real_categories:
        skills_json = root / CATEGORIES_DIR_REL / cat_id / "skills.json"
        if not skills_json.is_file():
            errors.append(f"{cat_id}: missing skills.json (expected under {CATEGORIES_DIR_REL})")
            continue
        try:
            skills = _load_json(skills_json)
        except json.JSONDecodeError as e:
            errors.append(f"{CATEGORIES_DIR_REL / cat_id / 'skills.json'}: JSON parse error: {e}")
            continue
        real_count = len(skills) if isinstance(skills, dict) else 0
        if real_count != js_node_count:
            bad_counts.append(f"{cat_id}={real_count}")

    if bad_counts:
        errors.append(
            f"{SELFTEST_JS_REL}: ST_SKILL_NODE_COUNT_PER_CATEGORY is {js_node_count}, but the "
            f"generated skills.json node count doesn't match it for {len(bad_counts)} "
            f"categories: {bad_counts} - this is exactly issue #77's drift class "
            "(selftest.js's hardcoded per-category node count fell out of sync with what "
            "gen_skill_tree.py actually generates); update "
            "ST_SKILL_NODE_COUNT_PER_CATEGORY (and every stale count in its stCheck name/"
            "detail strings) to match"
        )

    return errors, stats


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else REPO_ROOT

    errors, stats = check_selftest_skill_sync(root)

    if errors:
        print(f"check_selftest_skill_sync: FAIL - {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        return 1

    stats_str = ", ".join(f"{v} {k}" for k, v in stats.items())
    print(f"check_selftest_skill_sync: PASS - {stats_str}, selftest.js constants match generated data")
    return 0


if __name__ == "__main__":
    sys.exit(main())
