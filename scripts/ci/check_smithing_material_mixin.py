#!/usr/bin/env python3
"""Fast-tier CI check: GitHub #171 regression guard for
AbstractSmithingAnvilBlockEntityMixin's forged-material correction loop.

The bug (#171): the mixin's result-slot loop filtered candidate slots with
`slotStack.getItem() instanceof GearItem` before writing the corrected
material. Every forged head/blade this pack's Phase 1/2 Overgeared forging
recipes actually produce (silentgear:pickaxe_head/axe_head/shovel_head/
sword_blade) is a `MainPartItem`, which extends `CompoundPartItem`, which
extends plain `Item` - none of that chain implements
`net.silentchaos512.gear.api.item.GearItem` (confirmed via `javap -p` against
the pinned silent-gear jar; only fully-assembled tool items like
GearPickaxeItem do). So the filter never matched and the material write was
dead code. A second, independent no-op: the old code then called
`GearData.recalculateGearData(slotStack, player)`, which reads
SgDataComponents.GEAR_CONSTRUCTION first and returns immediately if it's
null - a bare forged part/head stack never has that component either.

This is a source-level check (a mixin only runs inside a live Minecraft
server, out of reach of the fast tier) that would have FAILED against the
old buggy idiom and PASSES against the fix: it asserts the mixin source does
NOT filter results by `instanceof GearItem` and does NOT call
GearData.recalculateGearData (nor import GearData at all), and DOES match
results by `instanceof CompoundPartItem` and writes
SgDataComponents.MATERIAL_LIST directly.

Usage: python3 scripts/ci/check_smithing_material_mixin.py [root]
Exit code: 0 if all checks pass, 1 otherwise.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

MIXIN_REL = (
    Path("mods-src") / "vppintegration" / "src" / "main" / "java" / "dev"
    / "vanillaplusplus" / "vppintegration" / "mixin"
    / "AbstractSmithingAnvilBlockEntityMixin.java"
)

GEAR_ITEM_INSTANCEOF_RE = re.compile(r"instanceof\s+GearItem")
COMPOUND_PART_ITEM_INSTANCEOF_RE = re.compile(r"instanceof\s+CompoundPartItem")
RECALCULATE_CALL_RE = re.compile(r"GearData\s*\.\s*recalculateGearData")
GEAR_DATA_IMPORT_RE = re.compile(r"^import\s+net\.silentchaos512\.gear\.util\.GearData\s*;", re.MULTILINE)
COMPOUND_PART_ITEM_IMPORT_RE = re.compile(
    r"^import\s+net\.silentchaos512\.gear\.item\.CompoundPartItem\s*;", re.MULTILINE
)
MATERIAL_LIST_SET_RE = re.compile(r"\.set\(\s*SgDataComponents\.MATERIAL_LIST\.get\(\)")

BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
LINE_COMMENT_RE = re.compile(r"//[^\n]*")


def strip_comments(text):
    """Masks /** javadoc */, /* block */ and // line comments before the
    dead-idiom regexes run. This class's own javadoc deliberately quotes the
    old buggy idiom (`instanceof GearItem`, `GearData.recalculateGearData`)
    in prose to explain GitHub #171 - without this, that prose would
    false-positive as if the bug were still present in code."""
    return LINE_COMMENT_RE.sub("", BLOCK_COMMENT_RE.sub("", text))


def fail(errors):
    print(f"check_smithing_material_mixin: FAIL - {len(errors)} problem(s):")
    for e in errors:
        print(f"  {e}")
    return 1


def check_source(text, errors):
    code_only = strip_comments(text)
    if GEAR_ITEM_INSTANCEOF_RE.search(code_only):
        errors.append(
            "mixin still filters result slots with 'instanceof GearItem' - this never "
            "matches a forged head/blade (MainPartItem/CompoundPartItem does not implement "
            "GearItem), so material correction stays dead code (GitHub #171)"
        )
    if not COMPOUND_PART_ITEM_INSTANCEOF_RE.search(code_only):
        errors.append(
            "mixin does not match result slots with 'instanceof CompoundPartItem' - the "
            "real class of every forged head/blade result (GitHub #171 fix)"
        )
    if not COMPOUND_PART_ITEM_IMPORT_RE.search(text):
        errors.append("mixin does not import net.silentchaos512.gear.item.CompoundPartItem")
    if RECALCULATE_CALL_RE.search(code_only):
        errors.append(
            "mixin still calls GearData.recalculateGearData(...) - a guaranteed no-op on a "
            "bare forged part/head stack (SgDataComponents.GEAR_CONSTRUCTION is always null "
            "there), and unnecessary since CompoundPartItem reads MATERIAL_LIST directly off "
            "the stack on demand (GitHub #171)"
        )
    if GEAR_DATA_IMPORT_RE.search(text):
        errors.append(
            "mixin still imports net.silentchaos512.gear.util.GearData - unused now that "
            "recalculateGearData is no longer called (GitHub #171)"
        )
    if not MATERIAL_LIST_SET_RE.search(code_only):
        errors.append(
            "mixin does not write SgDataComponents.MATERIAL_LIST via ItemStack.set(...) - "
            "the actual material correction this mixin exists to perform"
        )


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else REPO_ROOT

    errors = []
    mixin_path = root / MIXIN_REL
    if not mixin_path.is_file():
        errors.append(f"{mixin_path} missing")
        return fail(errors)

    text = mixin_path.read_text(encoding="utf-8")
    check_source(text, errors)

    if errors:
        return fail(errors)

    print(
        "check_smithing_material_mixin: PASS - AbstractSmithingAnvilBlockEntityMixin matches "
        "forged results by CompoundPartItem and writes MATERIAL_LIST directly (GitHub #171)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
