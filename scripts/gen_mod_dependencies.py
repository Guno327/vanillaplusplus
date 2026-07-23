#!/usr/bin/env python3
"""Generate a static, offline snapshot of every pinned mod's provided modIds
(incl. Jar-in-Jar) and required dependencies, for the FAST-TIER check
scripts/ci/check_mod_dependencies_offline.py (GitHub issue: v0.5.0 follow-up
hardening).

WHY THIS EXISTS. scripts/ci/check_mod_dependencies.py (added after the
v0.5.0 client-crash regression - see that script's own docstring) resolves
every mod's real, jar-derived required dependencies against the whole
installed set, closing the gap where every automated boot tier only boots
the dedicated SERVER and therefore never notices a missing CLIENT-side
dependency. But that check needs the mod jars themselves (network to
download + read them), and boot.yml (where it now runs) is weekly/on-
dispatch/at-mint only - not on every PR. Fast-tier (ci.yml / run_all.py,
every PR and push) is offline: no mod jars, no network. This script is the
one-time (per lockfile change), network-using step - run by hand locally,
same workflow as scripts/resolve_mods.py and scripts/gen_mod_registry_
snapshot.py - that produces the static ground truth
scripts/ci/check_mod_dependencies_offline.py reads instead of the jars.

Reuses scripts/ci/check_mod_dependencies.parse_mod_jar - the SAME parser
that the boot-tier (jar-reading) check uses - so there is exactly one
neoforge.mods.toml parser in this repo, not two drifting implementations.

Usage: python3 scripts/gen_mod_dependencies.py [--mods-dir DIR]
Reads every mod in pack/mods.lock.json, downloads (or reads cached) jars,
and writes pack/mod_registries/mod_dependencies.json.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CI_DIR = ROOT / "scripts" / "ci"
sys.path.insert(0, str(CI_DIR))
import check_mod_dependencies as cmd  # noqa: E402

LOCKFILE = ROOT / "pack" / "mods.lock.json"
MOD_CACHE = ROOT / "pack" / "mods"
OUT_PATH = ROOT / "pack" / "mod_registries" / "mod_dependencies.json"


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mods-dir", default=str(MOD_CACHE), help="jar cache dir (default pack/mods)")
    ap.add_argument("--lockfile", default=str(LOCKFILE))
    args = ap.parse_args(argv)

    lock = json.loads(Path(args.lockfile).read_text())
    mods_dir = Path(args.mods_dir)

    out_mods = {}
    errors = []
    for mod in lock["mods"]:
        try:
            data = cmd._load_jar_bytes(mod, mods_dir, offline=False)
            provided, required = cmd.parse_mod_jar(data)
        except Exception as e:
            errors.append(f"{mod['slug']}: could not read jar ({e})")
            continue
        out_mods[mod["slug"]] = {
            "version_number": mod.get("version_number"),
            "provided": sorted(provided),
            "required": required,
        }
        print(f"  {mod['slug']}: {len(provided)} provided modId(s), "
              f"{len(required)} required dep(s)", file=sys.stderr)

    if errors:
        print("gen_mod_dependencies: FAILED to read some jars:", file=sys.stderr)
        for e in errors:
            print("  " + e, file=sys.stderr)
        raise SystemExit(1)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps({
        "source_lockfile_mod_count": len(lock["mods"]),
        "mods": out_mods,
    }, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT_PATH} ({len(out_mods)} mod(s))", file=sys.stderr)


if __name__ == "__main__":
    main()
