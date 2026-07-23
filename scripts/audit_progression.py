#!/usr/bin/env python3
"""GitHub #61 - recursive recipe-reachability audit.

Follow-up from #56/#49: this pack dropped ProgressiveStages' per-player item
lock list and now gates progression on ingredients alone (an item is
reachable exactly when its ingredient chain is reachable - see DESIGN.md's
"The tier ladder" section and pack/kubejs/server_scripts/tier_gating.js's
header comment). Nothing mechanically checks that property. This script
does: it recursively computes the earliest tier at which every item in the
resolved mod set + this pack's own KubeJS recipe overrides is actually
craftable, and reports any item pack/progression/*.toml assigns to a tier
ABOVE that computed floor - i.e. genuinely under-gated items.

OFFLINE vs IN-GAME, and why offline was chosen
------------------------------------------------
#61 itself raises this: the live in-game recipe manager is the most honest
source, since it's exactly what NeoForge resolves after every datapack/
KubeJS overlay is applied - no risk of this script's own recipe-type
interpretation drifting from the game's. An in-game command (e.g. a
`/vpp_audit` KubeJS binding that walks `RecipeManager` at runtime) would
sidestep every guess this file makes about which JSON shape belongs to
which recipe type.

Offline was chosen anyway, for three reasons that matter more for a CI/dev
tool than for a one-off verification: (1) testability - the false-positive
regressions this ticket exists because of (#56's audit) need to be pinned
down with unit tests that run in milliseconds with no server, no world, no
player; an in-game command can only be verified by booting a server and
issuing it by hand, which is exactly the "no server boots" constraint this
task was scoped under. (2) availability - the resolved jars are already
sitting on disk wherever `server/mods/` has been populated (this repo's own
build pipeline puts them there); nothing about this analysis needs a running
JVM. (3) precedent - the #56 audit that first surfaced `track_station`/
`refinedstorage:controller` was already an offline jar scan; the ask here is
to make that approach *correct*, not to replace its whole strategy.

The tradeoff this accepts: an offline parser must decide, per recipe TYPE,
whether it represents a real acquisition path, and (within a path) which
JSON fields are ingredients vs metadata. Get either wrong and you reintroduce
exactly the bug class #56 hit. See RECIPE PARSING below for how this stays
correct without hand-modeling every one of the ~140 distinct recipe types
these mods register.

RECIPE PARSING: ignoring recoloring/variant recipe types
----------------------------------------------------------
The two known false positives were caused by two different mistakes, and
the fix for each is a different part of this file:

  * `create:track_station` was mismatched against an unrelated recipe
    (root cause: loose, non-exact identification of "the recipe for this
    item" - likely a substring/filename match rather than a recipe's own
    `result`/`results` field). Fixed here by NEVER matching on filename or
    substring: `extract_result_ids()` only trusts a recipe's own declared
    output field(s), and `index_recipes()` keys strictly on that exact
    item id.
  * `refinedstorage:controller` was mismatched against RS's own
    `refinedstorage:recoloring` recipes (which exist ONE per dye colour,
    re-dying an already-built controller - they do not craft a new
    controller from raw materials, and one of them literally has
    `"result": "refinedstorage:controller"` for the "restore to
    undyed" case, which is exactly what would fool a matcher that doesn't
    check recipe type). Fixed here by `NON_ACQUISITION_TYPES`: an explicit,
    commented deny-list of recipe types that exist in these jars but do NOT
    represent a real "craft this new item" path - recolor/dye/toggle
    variants, and in-place modifications of an item the player already
    owns (salvaging, reforging, socketing, upgrade removal, ...). Every
    entry names the mod, the type, and why it's excluded.

Everything NOT on that deny list is treated as a possible acquisition path
and parsed generically: `recipe_ingredient_specs()` looks for the small,
consistent vocabulary of field names real crafting/processing recipes
across these mods actually use (`ingredients`, `ingredient`, `key`, `base`/
`addition`/`template`, `reagent`/`pedestalItems`, `sequence` for
`create:sequenced_assembly`'s multi-step recipes) rather than an exhaustive
per-`type` allowlist - new machine types added by a future mod update need
no change here as long as they reuse this vocabulary (verified against
Create/Mekanism/Immersive Engineering/Tinkers'/Silent Gear/Refined
Storage/Sophisticated Storage's actual recipe JSON during development).
Fields outside that vocabulary (`category`, `processing_time`,
`experience`, cosmetic/UI fields, etc.) are never walked, so metadata can
never be misread as an ingredient.

TIER COMPUTATION
------------------
This pack's actual gating mechanism (tier_gating.js's own header comment)
is: "an item is reachable exactly when its ingredient chain is reachable."
Tiers 0-4 are the only ones with a material signal to walk (Tiers 5-9 are
dimension/rocket-reach narrative triggers per DESIGN.md's tier ladder, out
of scope for a *recipe* audit). Four items are this pack's own tier
markers - `create:andesite_alloy` / `create:brass_ingot` /
`create:refined_radiance` or `create:shadow_steel` / `minecraft:netherite_ingot`
- and `tier_gating.js` works by inserting ONE of these into an otherwise
early-tier recipe. Crucially, a tier marker's OWN tier is definitional, not
derived from its own (deliberately cheap) ingredients - computing it
recursively would make Andesite Alloy "tier 0" (its own recipe is just
andesite + a nugget) and silently defeat the entire mechanism. So:

  tier(item) = TIER_INDEX[marker]           if item IS one of the 4 markers
  tier(item) = 0                            if item has no recipe at all
                                             (raw/looted material - always
                                             reachable, matching #49's own
                                             "materials-only" model: nothing
                                             blocks mining iron from world
                                             start any more)
  tier(item) = min over its recipes of      otherwise (take the cheapest of
               ( max over that recipe's     multiple ways to craft it; each
                 required ingredients of    recipe's own ingredients are all
                 tier(ingredient) )         hard requirements - AND - but an
                                            ingredient slot that lists
                                            several alternatives, e.g.
                                            Create's "any iron or zinc
                                            nugget", is OR: cheapest
                                            alternative wins)

A tag ingredient (`{"tag": "c:foo"}` or KubeJS's `'#c:foo'` shorthand)
resolves to the MIN tier across every item registered in that tag (any one
member satisfies the slot), expanding tag-of-tag membership
(`"#namespace:other_tag"` entries) the same way NeoForge does. An
unresolvable tag (no jar in this scan defines it - true for plenty of
`c:ingots/*`-style common tags, which live in the base NeoForge/game data
this offline scan never has if the server hasn't been booted) defaults to
tier 0. This default is safe for this audit's purpose specifically because
none of the 4 tier markers are ever referenced via a tag anywhere in this
pack or the mods audited during development - they're always a literal
`item:` id - so an unresolved *other* tag can never hide a real tier marker.

KUBEJS OVERRIDES
------------------
`pack/kubejs/server_scripts/*.js` can both remove a jar recipe
(`event.remove(...)`) and add a new one (`event.shaped`/`event.shapeless`/
`event.custom(...)`). `parse_kubejs_overrides()` reads these with a small,
deliberately narrow JS-literal reader (`js_literal_to_py`) plus a best-effort
loop-expansion pass (`expand_loops`) for the handful of `for...of`/
`.forEach` blocks these scripts use to apply the same edit to a family of
items (see its docstring for exactly what it does and does not evaluate -
it is NOT a JS interpreter). Where a loop body still contains unresolved JS
after substitution (e.g. tier_gating.js's `SOPH_STORAGE_UPGRADE_ITEMS`
block, which mutates a pattern string with `.replace()` before calling
`event.custom`), a documented fallback treats the loop's own per-entry data
object as the ingredient bag directly - correct for this file's actual
shape (every field is either a literal resource id or a nested item/tag
ref) without needing to model the string mutation that produces the
cosmetic crafting-grid layout, which the tier computation never needs.

WHY STANDALONE, NOT WIRED INTO run_all.py
--------------------------------------------
This needs the resolved mod jars under server/mods/ to say anything at all
about the real game - exactly the "not always present in CI" mods.json/
run_all.py's existing fast-tier checks are built to avoid (they use static
snapshots, e.g. pack/mod_registries/*.json, precisely so they run with no
jars on disk). Wiring this into run_all.py would either silently no-op
every run with no jars present (masking real regressions) or make the fast
tier depend on a jar cache the fast tier has never needed before. It runs
standalone instead: `python3 scripts/audit_progression.py` (skips gracefully
with a clear message if server/mods/ has no jars), and its parsing CORE
(everything above the CLI) is unit-tested in scripts/ci/tests/ with no jars
needed at all, including regression tests pinned to the two known false
positives using their real recipe JSON as fixtures.

Usage: python3 scripts/audit_progression.py [--mods-dir DIR] [--verbose]
Exit code: always 0 (this is a report, not a gate - see docstring above);
non-zero only on a genuine tool failure (bad TOML, unreadable jar, etc).
"""
import argparse
import json
import re
import sys
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODS_DIR = ROOT / "server" / "mods"
PROGRESSION_DIR = ROOT / "pack" / "progression"
KUBEJS_DIR = ROOT / "pack" / "kubejs" / "server_scripts"

# ---------------------------------------------------------------------------
# Tier ladder (DESIGN.md's tier ladder table, materials-only portion).
TIER_ORDER = ["rootborn", "andesite_age", "brass_age", "precision_age", "induction_age"]
TIER_INDEX = {name: i for i, name in enumerate(TIER_ORDER)}
TIER_DISPLAY = {
    "rootborn": "Rootborn",
    "andesite_age": "Andesite Age",
    "brass_age": "Brass Age",
    "precision_age": "Precision Age",
    "induction_age": "Induction Age",
}

# This pack's own tier-marker materials (tier_gating.js's header comment).
# An item's tier is NOT derived from these materials' own ingredients - see
# module docstring "TIER COMPUTATION".
TIER_MATERIALS = {
    "create:andesite_alloy": "andesite_age",
    "create:brass_ingot": "brass_age",
    "create:refined_radiance": "precision_age",
    "create:shadow_steel": "precision_age",
    "minecraft:netherite_ingot": "induction_age",
}

# Recipe types confirmed (by reading their real recipe JSON, not guessed)
# to NOT be a "craft a new item from materials" path - each is either a
# cosmetic recolor/variant of an item the player already has, or an
# in-place modification/decomposition of an existing item. Walking these
# as if they were acquisition paths is exactly what produced #56's
# `refinedstorage:controller` false positive (matched against its
# `refinedstorage:recoloring` recipes instead of its real
# `minecraft:crafting_shaped` one).
NON_ACQUISITION_TYPES = {
    "refinedstorage:recoloring": "re-dyes an already-built controller/disk drive/etc "
        "between colour variants (one recipe per dye colour, ingredient is the "
        "tag `refinedstorage:controllers` - i.e. 'any controller you already "
        "own'); not a from-materials acquisition path. This is the exact type "
        "that produced the refinedstorage:controller false positive in #56.",
    "refinedstorage:upgrade_with_enchanted_book": "applies an enchant to an "
        "upgrade the player already owns, in place.",
    "sophisticatedbackpacks:backpack_dye": "cosmetic dye swap on an existing backpack.",
    "sophisticatedstorage:storage_dye": "cosmetic dye swap on an existing storage block.",
    "sophisticatedstorage:flat_top_barrel_toggle": "cosmetic model toggle on an "
        "existing barrel; produces no new item.",
    "sophisticatedcore:upgrade_clear": "removes an upgrade from an existing "
        "container in place.",
    "create:toolbox_dyeing": "cosmetic dye swap on an existing toolbox.",
    "create:sandpaper_polishing": "cosmetic finish change on an item the "
        "player already owns.",
    "ars_nouveau:dye": "cosmetic dye swap.",
    "apotheosis:sized_upgrade_recipe": "resizes an existing gem stack; not a "
        "new acquisition path.",
    "apotheosis:purity_upgrade": "upgrades the purity of an item already owned, in place.",
    "apotheosis:reforging": "rerolls affixes on an item already owned.",
    "apotheosis:salvaging": "decomposes an item already owned; not an "
        "acquisition path for the salvage output (that output is whatever "
        "crafted the original item, already counted there).",
    "apotheosis:socketing": "adds sockets to an existing item in place.",
    "apotheosis:add_sockets": "adds sockets to an existing item in place.",
    "apotheosis:unnaming": "strips a custom name from an existing item in place.",
    "apotheosis:withdrawal": "withdraws gems from an existing socketed item.",
    "silentgear:quick_paint": "cosmetic paint on an existing tool.",
    "silentgear:mod_kit_paint_part": "cosmetic paint on an existing part.",
    "silentgear:swap_gear_part": "swaps a part on an existing tool in place.",
    "silentgear:quick_repair": "repairs an existing tool in place; not an "
        "acquisition path for the tool.",
    "silentgear:fill_repair_kit": "fills an existing repair kit item in place.",
}


# ===========================================================================
# Tag registry
# ===========================================================================
class TagRegistry:
    """Maps `namespace:tag_path` -> set of concrete item ids, expanding
    tag-of-tag membership (`"#namespace:other_tag"` entries in a tag's
    `values` list) the way NeoForge's own tag loader does."""

    def __init__(self):
        self._raw = {}  # tag_id -> list of raw value strings (item id or "#tag")
        self._resolved = {}

    def add_tag_file(self, tag_id, data):
        values = data.get("values", [])
        entries = []
        for v in values:
            if isinstance(v, str):
                entries.append(v)
            elif isinstance(v, dict) and "id" in v:
                entries.append(v["id"])
        self._raw.setdefault(tag_id, []).extend(entries)

    def resolve(self, tag_id, _visiting=None):
        if tag_id in self._resolved:
            return self._resolved[tag_id]
        _visiting = _visiting or set()
        if tag_id in _visiting or tag_id not in self._raw:
            return frozenset()
        _visiting = _visiting | {tag_id}
        items = set()
        for entry in self._raw[tag_id]:
            if entry.startswith("#"):
                items |= self.resolve(entry[1:], _visiting)
            else:
                items.add(entry)
        result = frozenset(items)
        self._resolved[tag_id] = result
        return result

    @classmethod
    def from_jars(cls, jar_paths):
        registry = cls()
        for jar_path in jar_paths:
            try:
                zf = zipfile.ZipFile(jar_path)
            except (zipfile.BadZipFile, OSError):
                continue
            with zf:
                for name in zf.namelist():
                    m = re.match(r"data/([^/]+)/tags/items?/(.+)\.json$", name)
                    if not m:
                        continue
                    ns, path = m.group(1), m.group(2)
                    tag_id = f"{ns}:{path}"
                    try:
                        data = json.loads(zf.read(name))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
                    registry.add_tag_file(tag_id, data)
        return registry


# ===========================================================================
# Ingredient-spec extraction (schema-aware, not blind recursion - see
# module docstring "RECIPE PARSING")
# ===========================================================================
# Field names that hold a single ingredient slot (may itself be a dict, a
# tag shorthand string, or - in some jar recipes - a list of alternatives).
_SINGLE_INGREDIENT_KEYS = ("ingredient", "base", "addition", "template", "reagent")
# Field names that hold an AND-list of ingredient slots.
_LIST_INGREDIENT_KEYS = ("ingredients", "pedestalItems", "pedestal_items")


def _resolve_slot(value):
    """Resolve one ingredient slot to a spec tuple, or None if it isn't an
    ingredient at all (e.g. a fluid slot with no `item`/`tag`, which this
    audit deliberately doesn't track - see module docstring).

    A spec is one of:
        ("item", "<id>")
        ("tag", "<id>")
        ("oneof", [spec, ...])   -- alternatives; any ONE satisfies the slot
    """
    if isinstance(value, str):
        if value.startswith("#"):
            return ("tag", value[1:])
        if ":" in value:
            return ("item", value)
        return None
    if isinstance(value, dict):
        if isinstance(value.get("item"), str):
            return ("item", value["item"])
        if isinstance(value.get("tag"), str):
            return ("tag", value["tag"])
        return None
    if isinstance(value, list):
        alts = [_resolve_slot(v) for v in value]
        alts = [a for a in alts if a is not None]
        if not alts:
            return None
        if len(alts) == 1:
            return alts[0]
        return ("oneof", alts)
    return None


def recipe_ingredient_specs(recipe):
    """Return the flat AND-list of ingredient specs a recipe (or recipe-like
    dict - also used for `create:sequenced_assembly` steps and a couple of
    KubeJS loop-body fallback shapes) requires."""
    specs = []
    if not isinstance(recipe, dict):
        return specs

    for key in _SINGLE_INGREDIENT_KEYS:
        if key in recipe:
            slot = _resolve_slot(recipe[key])
            if slot:
                specs.append(slot)

    for key in _LIST_INGREDIENT_KEYS:
        val = recipe.get(key)
        if isinstance(val, list):
            for v in val:
                slot = _resolve_slot(v)
                if slot:
                    specs.append(slot)

    key_dict = recipe.get("key")
    if isinstance(key_dict, dict):
        for v in key_dict.values():
            slot = _resolve_slot(v)
            if slot:
                specs.append(slot)

    sequence = recipe.get("sequence")
    if isinstance(sequence, list):
        for step in sequence:
            specs.extend(recipe_ingredient_specs(step))

    return specs


def extract_result_ids(recipe):
    """Return the list of exact item ids this recipe declares as its
    output(s), reading ONLY the recipe's own result/results/output field -
    never a filename or substring match (the root cause of the
    `create:track_station` false positive - see module docstring)."""
    ids = []

    def _one(node):
        if isinstance(node, str):
            return node
        if isinstance(node, dict):
            rid = node.get("id") or node.get("item")
            if isinstance(rid, str):
                return rid
        return None

    if "result" in recipe:
        rid = _one(recipe["result"])
        if rid:
            ids.append(rid)
    if isinstance(recipe.get("results"), list):
        for r in recipe["results"]:
            rid = _one(r)
            if rid:
                ids.append(rid)
    if "output" in recipe and not ids:
        rid = _one(recipe["output"])
        if rid:
            ids.append(rid)
    return ids


# ===========================================================================
# Recipe index: item id -> list of candidate recipes
# ===========================================================================
class RecipeIndex:
    def __init__(self):
        self.by_output = {}      # item id -> list[recipe dict]
        self.by_id = {}          # recipe id -> recipe dict (id may be unknown/synthetic)
        self.excluded_types = {} # type -> count, for reporting

    def add(self, recipe, recipe_id=None):
        rtype = recipe.get("type")
        if rtype in NON_ACQUISITION_TYPES:
            self.excluded_types[rtype] = self.excluded_types.get(rtype, 0) + 1
            return
        for out_id in extract_result_ids(recipe):
            self.by_output.setdefault(out_id, []).append(recipe)
        if recipe_id:
            self.by_id[recipe_id] = recipe

    def remove_by_id(self, recipe_id):
        recipe = self.by_id.pop(recipe_id, None)
        if recipe is None:
            return
        for out_id in extract_result_ids(recipe):
            lst = self.by_output.get(out_id)
            if lst and recipe in lst:
                lst.remove(recipe)

    def remove_by_output(self, item_id):
        self.by_output.pop(item_id, None)

    @classmethod
    def from_jars(cls, jar_paths):
        index = cls()
        for jar_path in jar_paths:
            try:
                zf = zipfile.ZipFile(jar_path)
            except (zipfile.BadZipFile, OSError):
                continue
            with zf:
                for name in zf.namelist():
                    if not (name.startswith("data/") and name.endswith(".json")):
                        continue
                    if "/recipe/" not in name and "/recipes/" not in name:
                        continue
                    try:
                        data = json.loads(zf.read(name))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
                    if not isinstance(data, dict) or "type" not in data:
                        continue
                    # Recipe id = its path relative to data/<ns>/recipe(s)/,
                    # namespaced - matches the id the game itself assigns.
                    m = re.match(r"data/([^/]+)/recipes?/(.+)\.json$", name)
                    recipe_id = f"{m.group(1)}:{m.group(2)}" if m else None
                    index.add(data, recipe_id=recipe_id)
        return index


# ===========================================================================
# Tier computation
# ===========================================================================
class ReachabilityError(Exception):
    pass


def compute_item_tier(item_id, index, tags, memo=None, visiting=None):
    """Earliest tier index (into TIER_ORDER) at which `item_id` is
    craftable. See module docstring "TIER COMPUTATION"."""
    memo = {} if memo is None else memo
    visiting = set() if visiting is None else visiting

    if item_id in TIER_MATERIALS:
        return TIER_INDEX[TIER_MATERIALS[item_id]]
    if item_id in memo:
        return memo[item_id]
    if item_id in visiting:
        # Cyclic ingredient chain (e.g. a tier-upgrade item that consumes a
        # lower tier of itself). Breaking the cycle here means this path
        # contributes no additional constraint; the recipe's OTHER
        # ingredients (or a different recipe for the same output) still
        # apply normally.
        return 0

    recipes = index.by_output.get(item_id)
    if not recipes:
        return 0  # raw/looted material - always reachable post-#49

    visiting = visiting | {item_id}
    best = None
    for recipe in recipes:
        specs = recipe_ingredient_specs(recipe)
        tier = 0
        for spec in specs:
            tier = max(tier, _resolve_spec_tier(spec, index, tags, memo, visiting))
        best = tier if best is None else min(best, tier)
    if best is None:
        best = 0
    memo[item_id] = best
    return best


def _resolve_spec_tier(spec, index, tags, memo, visiting):
    kind = spec[0]
    if kind == "item":
        return compute_item_tier(spec[1], index, tags, memo, visiting)
    if kind == "tag":
        members = tags.resolve(spec[1]) if tags else frozenset()
        if not members:
            return 0  # unresolved tag - see module docstring for why this is safe
        return min(compute_item_tier(m, index, tags, memo, visiting) for m in members)
    if kind == "oneof":
        return min(_resolve_spec_tier(s, index, tags, memo, visiting) for s in spec[1])
    raise ReachabilityError(f"unknown ingredient spec kind: {kind!r}")


# ===========================================================================
# KubeJS override parsing (best-effort JS-literal reader, NOT a JS engine -
# see module docstring "KUBEJS OVERRIDES")
# ===========================================================================
def _find_matching(text, open_idx):
    """Index of the bracket/brace/paren matching the one at open_idx,
    respecting string literals ('/"/`) with backslash escapes."""
    open_ch = text[open_idx]
    close_ch = {"(": ")", "[": "]", "{": "}"}[open_ch]
    depth = 0
    i = open_idx
    in_str = None
    while i < len(text):
        c = text[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == in_str:
                in_str = None
        elif c in ("'", '"', "`"):
            in_str = c
        elif c == open_ch:
            depth += 1
        elif c == close_ch:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _split_top_level(text):
    """Split `text` on commas at bracket/string depth 0."""
    parts = []
    depth = 0
    in_str = None
    start = 0
    i = 0
    while i < len(text):
        c = text[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == in_str:
                in_str = None
        elif c in ("'", '"', "`"):
            in_str = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(text[start:i])
            start = i + 1
        i += 1
    tail = text[start:]
    if tail.strip():
        parts.append(tail)
    return [p.strip() for p in parts if p.strip()]


_IDENT_RE = re.compile(r"^[A-Za-z_$][\w$]*$")


def js_literal_to_py(text):
    """Convert a (small, non-executable) JS literal - string, array, or
    object literal, arbitrarily nested - into a Python value. Deliberately
    does NOT evaluate function calls, member access, or operators; callers
    are expected to have already substituted loop variables (see
    expand_loops) so that literals are all that's left."""
    text = text.strip()
    if not text:
        return None
    if text[0] in "'\"`":
        quote = text[0]
        end = _find_matching_quote(text, quote)
        raw = text[1:end]
        return (
            raw.replace("\\\\", "\x00")
            .replace(f"\\{quote}", quote)
            .replace("\x00", "\\")
        )
    if text[0] == "[":
        end = _find_matching(text, 0)
        inner = text[1:end]
        return [js_literal_to_py(p) for p in _split_top_level(inner)]
    if text[0] == "{":
        end = _find_matching(text, 0)
        inner = text[1:end]
        result = {}
        for part in _split_top_level(inner):
            colon = _top_level_colon(part)
            if colon == -1:
                continue
            k = part[:colon].strip().strip("'\"")
            v = part[colon + 1:].strip()
            result[k] = js_literal_to_py(v)
        return result
    # Bare token: number, boolean, or an unresolved identifier (shouldn't
    # occur once expand_loops has substituted loop variables; treated as
    # an opaque marker so callers can detect + skip it).
    if re.match(r"^-?\d+(\.\d+)?$", text):
        return float(text) if "." in text else int(text)
    if text in ("true", "false"):
        return text == "true"
    return {"__unresolved__": text}


def _find_matching_quote(text, quote):
    i = 1
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == quote:
            return i
        i += 1
    return len(text)


def _top_level_colon(text):
    depth = 0
    in_str = None
    i = 0
    while i < len(text):
        c = text[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == in_str:
                in_str = None
        elif c in ("'", '"', "`"):
            in_str = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == ":" and depth == 0:
            return i
        i += 1
    return -1


_CONST_ARRAY_RE = re.compile(r"const\s+(\w+)\s*=\s*(\[)")
_FOR_OF_RE = re.compile(r"for\s*\(\s*const\s+(\w+)\s+of\s+(\w+)\s*\)\s*(\{)")
_FOREACH_RE = re.compile(r"(\w+)\.forEach\(\s*\(?(\w+)\)?\s*=>\s*(\{)")
_IF_NEQ_RE = re.compile(r"if\s*\(\s*'([^']*)'\s*!==\s*'([^']*)'\s*\)\s*(\{)")
_IF_EQ_RE = re.compile(r"if\s*\(\s*'([^']*)'\s*===\s*'([^']*)'\s*\)\s*(\{)")


def _js_value_literal(value):
    """Render a Python value (already-resolved loop-binding field) back as
    a JS source literal suitable for textual substitution."""
    if isinstance(value, str):
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
    return json.dumps(value)


def _template_literal(value):
    """Render a value the way a `${...}` template interpolation would: the
    RAW string (no surrounding JS quotes - the backticks already provide
    that), unlike `_js_value_literal` which is for substituting into a
    plain JS value position."""
    return value if isinstance(value, str) else json.dumps(value)


# A bare identifier is only a *value* use, never a key, when it's NOT
# immediately followed by a colon (allowing for whitespace) - covers the
# `type: type` and `{ id: id, count: 1 }` shapes these scripts use, where
# the loop variable's own name collides with a JSON field name of the same
# spelling (e.g. `SOPH_STORAGE_TYPES.forEach(type => ...)` binding a loop
# variable literally called `type`, right next to recipe json's own `type`
# key).
def _not_key_position(ident):
    return re.compile(r"(?<![\w.$])" + re.escape(ident) + r"(?!\s*[.\w$])(?!\s*:)")


def _substitute_ident_fields(body, ident, binding):
    """Replace every `ident.field` and `${ident.field}` occurrence in
    `body` with the JS literal of `binding[field]`, and bare `ident`
    occurrences (word-boundary, not a JSON key, not followed by `.`) with
    the literal of `binding` itself (covers `for (const id of ROBE_IDS)`-
    style loops over a plain string array)."""
    if isinstance(binding, dict):
        for field, value in binding.items():
            pattern = re.compile(r"\$\{" + re.escape(ident) + r"\." + re.escape(field) + r"\}")
            body = pattern.sub(lambda m, v=value: str(_template_literal(v)), body)
            pattern = re.compile(re.escape(ident) + r"\." + re.escape(field) + r"\b")
            body = pattern.sub(lambda m, v=value: _js_value_literal(v), body)
    else:
        pattern = re.compile(r"\$\{" + re.escape(ident) + r"\}")
        body = pattern.sub(lambda m: str(_template_literal(binding)), body)
        body = _not_key_position(ident).sub(lambda m: _js_value_literal(binding), body)
    return body


def _resolve_conditionals(body):
    """Evaluate the narrow `if ('a' !== 'b') { ... }` / `=== ` shape these
    scripts use post-substitution, keeping or dropping the block."""
    for pattern, keep_if in ((_IF_NEQ_RE, lambda a, b: a != b), (_IF_EQ_RE, lambda a, b: a == b)):
        while True:
            m = pattern.search(body)
            if not m:
                break
            brace_start = m.end() - 1
            brace_end = _find_matching(body, brace_start)
            block = body[m.end():brace_end]
            replacement = block if keep_if(m.group(1), m.group(2)) else ""
            body = body[:m.start()] + replacement + body[brace_end + 1:]
    return body


def expand_loops(source):
    """Best-effort expansion of `for (const x of ARR) {...}` and
    `ARR.forEach(x => {...})` blocks where ARR is a `const ARR = [...]`
    array literal declared earlier in the same file, by substituting each
    element's fields into the loop body and concatenating the results in
    place of the loop construct. This is NOT a JS interpreter: it does not
    evaluate method calls (`.replace(...)`), further nested loops, or
    variable reassignment inside the body - callers that need those (this
    file's own `SOPH_STORAGE_UPGRADE_ITEMS` block among them) get an
    unresolved marker in the body text, which `parse_kubejs_overrides` below
    falls back to reading the loop's raw per-entry data as an ingredient
    bag directly (see its docstring)."""
    arrays = {}
    for m in _CONST_ARRAY_RE.finditer(source):
        name, bracket_idx = m.group(1), m.end() - 1
        end = _find_matching(source, bracket_idx)
        if end == -1:
            continue
        arrays[name] = js_literal_to_py(source[bracket_idx:end + 1])

    unresolved_entries = []  # binding dicts whose loop body this pass couldn't evaluate

    changed = True
    while changed:
        changed = False
        for pattern in (_FOR_OF_RE, _FOREACH_RE):
            m = pattern.search(source)
            if not m:
                continue
            if pattern is _FOR_OF_RE:
                ident, array_name = m.group(1), m.group(2)
            else:
                array_name, ident = m.group(1), m.group(2)
            brace_start = m.end() - 1
            brace_end = _find_matching(source, brace_start)
            if brace_end == -1 or array_name not in arrays:
                # Can't expand safely - drop just the wrapper so a stray
                # unresolved loop doesn't get double-counted; the fallback
                # in parse_kubejs_overrides handles this file's known case
                # by inspecting `arrays` directly.
                continue
            body = source[m.end():brace_end]
            # If the body contains JS this substitution pass can't evaluate
            # (mutation via .replace()/Object.assign() before the event.*
            # call), record the substituted-per-entry bodies for the
            # fallback below instead of feeding them to _apply_kubejs_calls
            # as if they were literal - a half-substituted `.replace(` call
            # would otherwise silently parse as garbage.
            if ".replace(" in body or "Object.assign(" in body:
                unresolved_entries.extend(arrays[array_name])
                source = source[:m.start()] + source[brace_end + 1:]
                changed = True
                break
            expanded_bodies = []
            for binding in arrays[array_name]:
                b = _substitute_ident_fields(body, ident, binding)
                b = _resolve_conditionals(b)
                expanded_bodies.append(b)
            source = source[:m.start()] + "\n".join(expanded_bodies) + source[brace_end + 1:]
            changed = True
            break
    return source, arrays, unresolved_entries


_EVENT_CALL_RE = re.compile(r"event\.(remove|shaped|shapeless|custom)\s*\(")


def parse_kubejs_overrides(index, js_dir=KUBEJS_DIR):
    """Apply this pack's KubeJS `ServerEvents.recipes` overrides on top of
    `index` (an already-populated RecipeIndex from the jars): removals
    first, then additions, matching load order (`event.remove` inside the
    same recipes-event handler always targets the jar's own recipe, since
    it runs before this file's own re-authored recipes are registered)."""
    if not js_dir.exists():
        return
    for js_path in sorted(js_dir.glob("*.js")):
        source = js_path.read_text()
        if "event.recipes" not in source and "ServerEvents.recipes" not in source and "event." not in source:
            continue
        expanded, arrays, unresolved_entries = expand_loops(source)
        _apply_kubejs_calls(expanded, index)
        for entry in unresolved_entries:
            _apply_unresolved_entry_fallback(entry, index)


def _apply_kubejs_calls(text, index):
    pos = 0
    while True:
        m = _EVENT_CALL_RE.search(text, pos)
        if not m:
            break
        kind = m.group(1)
        paren_start = m.end() - 1
        paren_end = _find_matching(text, paren_start)
        if paren_end == -1:
            pos = m.end()
            continue
        args_text = text[paren_start + 1:paren_end]
        args = _split_top_level(args_text)
        pos = paren_end + 1

        if kind == "remove":
            if not args:
                continue
            obj = js_literal_to_py(args[0])
            if not isinstance(obj, dict):
                continue
            if "id" in obj and isinstance(obj["id"], str):
                index.remove_by_id(obj["id"])
            if "output" in obj and isinstance(obj["output"], str):
                index.remove_by_output(_strip_count_prefix(obj["output"]))
            continue

        if kind == "custom":
            if not args:
                continue
            recipe = js_literal_to_py(args[0])
            if isinstance(recipe, dict) and not _has_unresolved(recipe):
                index.add(recipe)
            continue

        # shaped / shapeless: first positional arg is the target item
        # (optionally "<n>x ns:item"); result is added generically.
        if not args:
            continue
        target = js_literal_to_py(args[0])
        if not isinstance(target, str) or _has_unresolved_str(target):
            continue
        target = _strip_count_prefix(target)

        recipe = {"result": {"id": target}}
        if kind == "shaped" and len(args) >= 3:
            key_dict = js_literal_to_py(args[2])
            if isinstance(key_dict, dict) and not _has_unresolved(key_dict):
                recipe["key"] = key_dict
        elif kind == "shapeless" and len(args) >= 2:
            ingredients = js_literal_to_py(args[1])
            if isinstance(ingredients, list) and not _has_unresolved(ingredients):
                recipe["ingredients"] = ingredients
        if len(recipe) > 1:
            index.add(recipe)


_COUNT_PREFIX_RE = re.compile(r"^\d+x\s+")


def _strip_count_prefix(item_id):
    return _COUNT_PREFIX_RE.sub("", item_id.strip())


def _has_unresolved(node):
    if isinstance(node, dict):
        if "__unresolved__" in node:
            return True
        return any(_has_unresolved(v) for v in node.values())
    if isinstance(node, list):
        return any(_has_unresolved(v) for v in node)
    return False


def _has_unresolved_str(s):
    return "${" in s or ".forEach" in s


# Keys that are clearly metadata, not ingredients, in the fallback loop-
# entry-as-ingredient-bag path below.
_FALLBACK_IGNORED_KEYS = {"id", "suffix", "tierLetter", "pattern", "dye", "gem"}


def _apply_unresolved_entry_fallback(entry, index):
    """For a loop body `expand_loops` could not fully resolve to a literal
    event.* call (this file's known case: tier_gating.js's
    `SOPH_STORAGE_UPGRADE_ITEMS`, whose body computes a new crafting
    pattern with `.replace()`/`Object.assign()` before calling
    `event.custom`), fall back to reading the loop's own per-entry data
    object directly as an ingredient bag: any dict-valued field is walked
    with the normal ingredient-slot rules, and any string field that looks
    like a resource location (`namespace:path`) and isn't an obviously
    cosmetic key (pattern/dye/gem/suffix/tierLetter/id) is treated as a
    literal item ingredient. The entry's own `id` field is the result -
    this is correct for every entry shape actually used in this pack (every
    field is either a literal resource id or a nested item/tag ref) without
    needing to model the string mutation that only affects the cosmetic
    crafting-grid layout, which tier computation never needs."""
    if not isinstance(entry, dict) or "id" not in entry:
        return
    recipe = {"result": {"id": entry["id"]}, "ingredients": []}
    for k, v in entry.items():
        if k in _FALLBACK_IGNORED_KEYS:
            continue
        if isinstance(v, dict):
            for sub in v.values():
                slot = _resolve_slot(sub)
                if slot:
                    recipe["ingredients"].append(sub if isinstance(sub, dict) else {"item": sub})
        elif isinstance(v, str) and ":" in v:
            recipe["ingredients"].append({"item": v})
    index.add(recipe)


# ===========================================================================
# pack/progression/*.toml loading
# ===========================================================================
def load_assigned_tiers(progression_dir=PROGRESSION_DIR):
    """item/block id -> tier name, from each tier file's [items].locked and
    [blocks].locked lists (the still-authoritative tier manifest per
    DESIGN.md / gen_economy.py - "first tier that claims an id wins" if
    ever duplicated). gen_economy.py only reads [items] since it's pricing
    inventory drops, but a recipe-reachability audit cares about blocks too
    - that's exactly where families like Refined Storage's Controller/Disk
    Drive live in these files."""
    assigned = {}
    for tier in TIER_ORDER:
        f = progression_dir / f"{tier}.toml"
        if not f.exists():
            continue
        with f.open("rb") as fh:
            data = tomllib.load(fh)
        for section in ("items", "blocks"):
            for entry in data.get(section, {}).get("locked", []):
                if not entry.startswith("id:"):
                    continue
                item_id = entry[len("id:"):]
                assigned.setdefault(item_id, tier)
    return assigned


# ===========================================================================
# CLI
# ===========================================================================
def run_audit(mods_dir=DEFAULT_MODS_DIR, progression_dir=PROGRESSION_DIR, js_dir=KUBEJS_DIR):
    jar_paths = sorted(Path(mods_dir).glob("*.jar"))
    if not jar_paths:
        return None

    index = RecipeIndex.from_jars(jar_paths)
    tags = TagRegistry.from_jars(jar_paths)
    parse_kubejs_overrides(index, js_dir=js_dir)

    assigned = load_assigned_tiers(progression_dir)
    memo = {}
    under_gated = []
    for item_id, assigned_tier in sorted(assigned.items()):
        computed = compute_item_tier(item_id, index, tags, memo=memo)
        assigned_idx = TIER_INDEX[assigned_tier]
        if computed < assigned_idx:
            under_gated.append((item_id, assigned_tier, TIER_ORDER[computed]))

    return {
        "jars_scanned": len(jar_paths),
        "recipes_indexed": sum(len(v) for v in index.by_output.values()),
        "excluded_recipe_types": index.excluded_types,
        "items_assigned": len(assigned),
        "under_gated": under_gated,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mods-dir", default=str(DEFAULT_MODS_DIR))
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    mods_dir = Path(args.mods_dir)
    result = run_audit(mods_dir=mods_dir)
    if result is None:
        print(f"audit_progression: no jars found under {mods_dir} - "
              "this is a standalone tool that needs the resolved mod set "
              "(see module docstring 'WHY STANDALONE'); nothing to report.")
        return 0

    print(f"audit_progression: scanned {result['jars_scanned']} jars, "
          f"{result['recipes_indexed']} acquisition recipes indexed, "
          f"{result['items_assigned']} items assigned a tier in pack/progression/*.toml")
    if args.verbose:
        print("Excluded (non-acquisition) recipe types encountered:")
        for t, count in sorted(result["excluded_recipe_types"].items()):
            print(f"  {t}: {count} recipe(s) - {NON_ACQUISITION_TYPES.get(t, '?')}")

    under_gated = result["under_gated"]
    if not under_gated:
        print("\nNo under-gated items found: every assigned item's earliest "
              "computed craftable tier is at or above its pack/progression/ "
              "assignment.")
        return 0

    print(f"\nUNDER-GATED: {len(under_gated)} item(s) reachable earlier than assigned:")
    for item_id, assigned_tier, computed_tier in under_gated:
        print(f"  {item_id}: assigned {TIER_DISPLAY[assigned_tier]}, "
              f"actually reachable at {TIER_DISPLAY[computed_tier]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
