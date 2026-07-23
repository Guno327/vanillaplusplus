#!/usr/bin/env python3
"""Driver for the L3 live client-join test on the Incus `vpp-l3` host
(GitHub client-test-harness follow-up to the v0.5.0/v0.5.1 client-only
launch regressions - see DESIGN.md's "L3 release gate" section and the
`project_incus_l3_test_host` / `project_vanilla_plus_plus` memory notes for
the full history).

`scripts/tests/l3_client_join.py` already boots a real dedicated server and
drives a real HeadlessMC client into a joined world on that host - but it
has to actually run there, and `vpp-l3` is NOT a git checkout (`find /home
-name .git` on it is empty; files exist only because something pushed them).
Before this script existed, that push step didn't exist either, so the
container silently tested whatever mod set someone last happened to copy
onto it - confirmed stale against current `main` by a live diff before this
script was written (missing `sophisticatedstorage`, `epictweaks`, and 11
other mods added since, see this branch's PR description). A driver that
does not re-sync the pack before every run cannot be trusted as a release
gate: it would "pass" a build it never actually looked at.

What this script does, in order:
  1. sync_to_l3()   - tars up the CURRENT `pack/` and `scripts/` trees
                       (the only two trees the L3 boot path reads - see
                       that function's docstring for why the sync set is
                       "all of both", not a hand-picked subset), pushes the
                       tarball over the Incus REST API, and replaces those
                       two directories on the container atomically (extract
                       to a scratch dir, then `rm -rf` + `mv`).
  2. run_l3()       - runs `/usr/local/bin/run_l3.sh` as `ubuntu` (never
                       root - see l3_client_join.py's own module docstring
                       for why: HeadlessMC derives the game dir from the
                       JDK's user.home, i.e. the passwd entry), polling and
                       printing the server/client log tails as they grow so
                       a long run isn't a silent black box, then captures
                       the final PASS/FAIL.
  3. evaluate_result() - turns (exit code, captured stdout) into a
                       PASS/FAIL verdict a caller (a human or a release
                       script) can trust - never just "exit code was 0".

Usage:
    python3 scripts/tests/run_l3_incus.py            # sync + run, print verdict
    python3 scripts/tests/run_l3_incus.py --no-sync   # skip the push (debugging only)
    python3 scripts/tests/run_l3_incus.py --skip-preclean

Exit code 0 = L3 PASS, nonzero = L3 FAIL or a driver/harness error. This is
the intended one-command entry point for the release gate documented in
DESIGN.md: a human (or the PM) runs this against `candidate` before
promoting it to `main`, and it must print "L3 GATE: PASS" for the promotion
to proceed.
"""
import argparse
import hashlib
import sys
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from incus_api import Incus, IncusError  # noqa: E402

INSTANCE = "vpp-l3"
PROJECT = "vpp"
REMOTE_ROOT = "/home/ubuntu/vanilla++"
REMOTE_STAGING = "/tmp/vpp_l3_sync_staging"
REMOTE_TARBALL = "/tmp/vpp_l3_sync.tar.gz"
RUN_SCRIPT = "/usr/local/bin/run_l3.sh"
REMOTE_USER = "ubuntu"

# The two trees the L3 boot path actually reads, end to end:
#   pack/    - build_server.py's LOCKFILE/PACK_TOML/VERSION_FILE, the
#              config/kubejs/defaultconfigs overrides both build_server.py
#              and l3_client_join.py's sync_client_overrides() copy, and
#              user_jvm_args.txt/server.properties.
#   scripts/ - l3_client_join.py itself, l2_client_smoke.py (imported for
#              load_lock()/assemble_mods_dir()), lib/boot_lock.py (imported),
#              build_server.py, and version_kubejs.py (imported by
#              build_server.py).
# Deliberately synced as whole trees rather than a hand-picked file list:
# the file list has already drifted once (this driver's own predecessor
# would have needed hand-updating for lib/boot_lock.py, added after L3 first
# shipped) and a missed addition fails silently - the container just runs
# stale code with no error. Both trees are small (~1.2MB / ~400KB) so the
# blanket sync costs nothing.
SYNC_DIRS = ("pack", "scripts")
EXCLUDE_DIR_NAMES = {"__pycache__"}
EXCLUDE_SUFFIXES = (".pyc", ".pyo")


def compute_worktree_tag(remote_root: str) -> str:
    """Mirror l3_client_join.py's own _WORKTREE_TAG derivation exactly (see
    that module: `f"{ROOT.name}_{hashlib.sha1(str(ROOT).encode()).hexdigest()[:10]}"`),
    so this driver can tail the same log files the remote run is writing.
    Deterministic because REMOTE_ROOT is a fixed path on vpp-l3 (it is not a
    git checkout with a variable worktree name - see module docstring).

    >>> compute_worktree_tag("/home/ubuntu/vanilla++")
    'vanilla++_2d4a2f0fa3'
    """
    name = remote_root.rstrip("/").rsplit("/", 1)[-1]
    digest = hashlib.sha1(remote_root.encode()).hexdigest()[:10]
    return f"{name}_{digest}"


def should_sync(rel_parts) -> bool:
    """True if a relative path (as a tuple of parts) should be included in
    the sync tarball. Excludes bytecode caches and their contents - nothing
    the container needs to run has to come from a stale .pyc, and shipping
    them risks a version-mismatched cache shadowing the freshly-synced .py.

    >>> should_sync(("scripts", "tests", "l3_client_join.py"))
    True
    >>> should_sync(("scripts", "tests", "__pycache__", "l3_client_join.cpython-312.pyc"))
    False
    >>> should_sync(("scripts", "__pycache__"))
    False
    >>> should_sync(("pack", "mods.lock.json"))
    True
    >>> should_sync(("scripts", "incus_api.cpython-312.pyc"))
    False
    """
    if any(part in EXCLUDE_DIR_NAMES for part in rel_parts):
        return False
    if rel_parts[-1].endswith(EXCLUDE_SUFFIXES):
        return False
    return True


def iter_sync_files(root: Path, sync_dirs=SYNC_DIRS):
    """Yield (absolute_path, arcname) for every file under `root`/<dir> for
    dir in sync_dirs that should_sync() keeps. arcname is the path relative
    to `root`, using forward slashes, so the tarball extracts as
    `<dir>/...` regardless of the local OS path separator.
    """
    for sub in sync_dirs:
        base = root / sub
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root)
            if should_sync(rel.parts):
                yield path, "/".join(rel.parts)


def build_sync_tarball(root: Path, dest: Path, sync_dirs=SYNC_DIRS) -> int:
    """Write a gzip tarball of iter_sync_files() to `dest`. Returns the file
    count actually included (so callers can sanity-check "0 files" rather
    than silently pushing an empty pack)."""
    count = 0
    with tarfile.open(dest, "w:gz") as tf:
        for path, arcname in iter_sync_files(root, sync_dirs):
            tf.add(path, arcname=arcname)
            count += 1
    return count


def evaluate_result(rc: int, stdout: str, stderr: str = ""):
    """Turn a captured run_l3.sh (rc, stdout, stderr) into a (passed, verdict)
    pair. Deliberately requires BOTH rc == 0 AND the literal "L3 PASS:"
    marker l3_client_join.py's main() prints on success - never trusts exit
    code alone. This is exactly the discipline the task brief warns about:
    a driver that calls rc == 0 a pass without checking what actually
    happened is how a false PASS ships.

    >>> passed, verdict = evaluate_result(0, "== L3: ... ==\\nL3 PASS: a real client joined ...\\n")
    >>> passed
    True
    >>> passed, verdict = evaluate_result(1, "== L3: ... ==\\nL3 FAIL: fatal client error\\n", "")
    >>> passed
    False
    >>> passed, verdict = evaluate_result(0, "no marker printed at all\\n")
    >>> passed
    False
    """
    combined = stdout + "\n" + stderr
    has_pass_marker = "L3 PASS:" in combined
    has_fail_marker = "L3 FAIL:" in combined
    if rc == 0 and has_pass_marker and not has_fail_marker:
        tail = combined.strip().splitlines()
        summary = next((ln for ln in reversed(tail) if ln.startswith("L3 PASS:")), tail[-1] if tail else "")
        return True, summary
    # Anything else is a FAIL, including "rc==0 but no PASS marker" (the
    # process could have been killed/truncated in a way that still reports
    # rc 0 for the wrapping shell - e.g. the ssh/exec transport, not the
    # test itself).
    lines = [ln for ln in combined.strip().splitlines() if ln.strip()]
    fail_line = next((ln for ln in reversed(lines) if ln.startswith("L3 FAIL:")), None)
    if fail_line:
        summary = fail_line
    elif lines:
        summary = "rc=%d, no L3 PASS/FAIL marker found - last output line: %s" % (rc, lines[-1])
    else:
        summary = "rc=%d, no output captured at all" % rc
    return False, summary


def sync_to_l3(api: Incus, verbose=True) -> int:
    """Push the current pack/ + scripts/ trees to vpp-l3, replacing whatever
    was there. Extraction lands in a scratch dir first and is only moved
    into place with a single `rm -rf` + `mv` swap, so a run that dies
    mid-sync can't leave the container with half-old/half-new files."""
    with tempfile.TemporaryDirectory() as tmp:
        tarball = Path(tmp) / "sync.tar.gz"
        count = build_sync_tarball(ROOT, tarball)
        if count == 0:
            raise IncusError("refusing to sync an empty tarball - pack/ and scripts/ both missing?")
        size = tarball.stat().st_size
        if verbose:
            print(f"== L3 driver: built sync tarball ({count} files, {size} bytes) ==")

        api.run(INSTANCE, ["rm", "-rf", REMOTE_STAGING], project=PROJECT, check=False, quiet=not verbose)
        api.run(INSTANCE, ["mkdir", "-p", REMOTE_STAGING], project=PROJECT, quiet=not verbose)

        if verbose:
            print(f"== L3 driver: pushing tarball to {INSTANCE}:{REMOTE_TARBALL} ==")
        api.push_file(INSTANCE, tarball, REMOTE_TARBALL, project=PROJECT, mode="0644", uid=0, gid=0)

        if verbose:
            print("== L3 driver: extracting + swapping pack/ and scripts/ into place ==")
        remote_cmd = (
            f"set -e; "
            f"tar xzf {REMOTE_TARBALL} -C {REMOTE_STAGING}; "
            f"rm -rf {REMOTE_ROOT}/pack {REMOTE_ROOT}/scripts; "
            f"mv {REMOTE_STAGING}/pack {REMOTE_STAGING}/scripts {REMOTE_ROOT}/; "
            f"chown -R {REMOTE_USER}:{REMOTE_USER} {REMOTE_ROOT}/pack {REMOTE_ROOT}/scripts; "
            f"rm -f {REMOTE_TARBALL}; rm -rf {REMOTE_STAGING}"
        )
        api.run(INSTANCE, ["sh", "-c", remote_cmd], project=PROJECT, quiet=not verbose)
        if verbose:
            print("== L3 driver: sync complete ==")
    return count


def preclean(api: Incus, verbose=True):
    """Defensive cleanup of anything a previous cut-off run might have left
    behind - a hung java/Xvfb process or a stale FIFO would otherwise make
    THIS run's boot fail in a way that looks like a pack regression. Safe
    to run even when nothing is stale (every command is best-effort).

    Also removes the tagged server/client log files from any prior run.
    l3_client_join.py truncates both on a healthy run (`open(..., "w")`),
    but only after boot/version-resolution succeeds - a run that failed
    before that point leaves the previous run's full log sitting on disk,
    and this driver's own log-tailing (_tail_new) has no way to tell
    "stale leftover content" from "this run's own new output" if it starts
    polling before that truncation happens (ground-truthed: a poll that
    starts early enough sees the previous run's crash trace and reports it
    as if it just happened)."""
    if verbose:
        print("== L3 driver: pre-clean (stale java/Xvfb processes, FIFOs, tagged logs) ==")
    tag = compute_worktree_tag(REMOTE_ROOT)
    # The bracket-around-first-char trick (`[h]eadlessmc...`) is load-bearing,
    # not cosmetic: this whole command line is itself passed to `sh -c`, so
    # without it `pkill -f` would find its own invoking shell's argv containing
    # the literal pattern string and SIGTERM itself mid-script (confirmed the
    # hard way - a plain 'headlessmc-launcher.jar' pattern here killed the
    # exec'd shell with rc=143 before any of the later cleanup commands ran).
    # pkill's own well-known self-exclusion only covers the pkill process
    # itself, not its parent shell.
    remote_cmd = (
        "pkill -f '[h]eadlessmc-launcher.jar' 2>/dev/null; "
        # The dedicated server's real argv (`java @user_jvm_args.txt
        # @libraries/net/neoforged/neoforge/<ver>/unix_args.txt nogui`) does
        # NOT contain the literal substring "server" anywhere - ground-
        # truthed the hard way: an earlier 'neoforge.*server' pattern here
        # silently matched nothing and left the dedicated server running
        # across driver invocations. unix_args.txt is the NeoForge
        # installer's own fixed arg-file name for this launch shape.
        "pkill -f '[u]nix_args.txt' 2>/dev/null; "
        "pkill -f '[X]vfb :99' 2>/dev/null; "
        "rm -f /home/ubuntu/vanilla++/server/cmd_fifo "
        "/tmp/vpp-research/headlessmc/l3_client_cmd_fifo "
        f"/tmp/vpp_l3_server_{tag}.log /tmp/vpp_l3_client_{tag}.log; "
        "true"
    )
    api.run(INSTANCE, ["sh", "-c", remote_cmd], project=PROJECT, check=False, quiet=not verbose)


def _tail_new(api: Incus, path: str, seen_len: int):
    """Fetch `path` from the container and print/return whatever is past
    seen_len, so a long run streams progress instead of going silent for
    ~15 minutes. Best-effort in two ways: a file that doesn't exist yet is
    not an error (the server/client haven't started writing it yet), and a
    transient Incus API hiccup on this side-channel poll (observed in
    practice: a concurrent exec's operation-wait occasionally overruns a
    30s window under this host's load) must never abort the run the driver
    is actually waiting on - it just means this one tick doesn't print
    anything new, and the next tick tries again.

    Also handles truncation: l3_client_join.py reopens each log with
    `open(..., "w")` partway through its own run (only after boot/version
    resolution succeeds), so a file that's now SHORTER than seen_len was
    truncated out from under this poll rather than left stale - treat that
    as "start over from 0" instead of silently going quiet until new
    content happens to outgrow the old length (preclean() also removes
    both tagged logs up front so this should be rare in practice, but a
    poll racing the exact moment of truncation is still possible)."""
    try:
        rc, out, _ = api.exec(
            INSTANCE, ["sh", "-c", f"cat {path} 2>/dev/null || true"],
            project=PROJECT, timeout_s=30,
        )
    except IncusError as e:
        print(f"  [{Path(path).name}] (tail poll skipped: {e})")
        return seen_len
    if len(out) < seen_len:
        print(f"  [{Path(path).name}] (log was truncated/reopened - resuming tail from 0)")
        seen_len = 0
    if len(out) > seen_len:
        new = out[seen_len:]
        for line in new.splitlines():
            print(f"  [{Path(path).name}] {line}")
        return len(out)
    return seen_len


def run_l3(api: Incus, timeout_s=2400, poll_s=20, verbose=True):
    """Run run_l3.sh on vpp-l3 as `ubuntu` (never root - see module
    docstring), polling and streaming the server/client log tails while the
    async operation runs, then returning (rc, stdout, stderr) once it's
    done. Uses `su - ubuntu -c ...` rather than an Incus exec `user` field
    (this stdlib client's exec() has no such parameter - see incus_api.py)
    so HeadlessMC's user.home resolution matches a real ubuntu login shell
    exactly."""
    tag = compute_worktree_tag(REMOTE_ROOT)
    server_log = f"/tmp/vpp_l3_server_{tag}.log"
    client_log = f"/tmp/vpp_l3_client_{tag}.log"

    if verbose:
        print(f"== L3 driver: launching {RUN_SCRIPT} as {REMOTE_USER} on {INSTANCE} "
              f"(timeout {timeout_s}s) ==")
        print(f"== L3 driver: tailing {server_log} / {client_log} as they grow ==")

    body = {
        "command": ["su", "-", REMOTE_USER, "-c", f"sh {RUN_SCRIPT}"],
        "wait-for-websocket": False,
        "record-output": True,
        "interactive": False,
        "environment": {"HOME": f"/home/{REMOTE_USER}"},
    }
    resp = api.post(f"/1.0/instances/{INSTANCE}/exec?project={PROJECT}", body)
    if resp.get("error"):
        raise IncusError(f"{resp.get('error_code')}: {resp['error']}")
    op_path = resp["operation"].split("?")[0]

    seen = {"server": 0, "client": 0}
    deadline = time.time() + timeout_s
    status = None
    md = {}
    while time.time() < deadline:
        # A transient hiccup polling the operation itself must not be
        # mistaken for the operation finishing badly - the real L3 run
        # keeps executing on the container regardless of whether THIS poll
        # succeeded, so a failed poll just retries next tick rather than
        # raising (see _tail_new's docstring for the same reasoning, and
        # this exact failure mode ground-truthed once during development:
        # a side-channel log-tail poll overran its 30s window and crashed
        # the driver while the actual test kept running unattended).
        try:
            r = api.get(f"{op_path}/wait?timeout={poll_s}&project={PROJECT}", timeout=poll_s + 15)
        except IncusError as e:
            if verbose:
                print(f"== L3 driver: operation-status poll hiccup, retrying ({e}) ==")
            continue
        md = r.get("metadata") or {}
        status = md.get("status")
        if verbose:
            seen["server"] = _tail_new(api, server_log, seen["server"])
            seen["client"] = _tail_new(api, client_log, seen["client"])
        if status in ("Success", "Failure", "Cancelled"):
            break
    else:
        raise IncusError(f"L3 run did not finish within {timeout_s}s (still {status})")

    if status != "Success":
        # "Success" here means the exec OPERATION completed, not that the
        # wrapped command exited 0 - Incus still reports the operation
        # Success even for a nonzero exit code. Anything else (Failure/
        # Cancelled/timeout) is a harness-level problem, not a test verdict.
        raise IncusError(f"L3 exec operation did not complete cleanly: status={status} metadata={md}")

    meta = md.get("metadata") or {}
    out = meta.get("output") or {}

    def fetch(key):
        path = out.get(key)
        if not path:
            return ""
        return api.request_raw("GET", f"{path}?project={PROJECT}")

    rc = meta.get("return", -1)
    stdout, stderr = fetch("1"), fetch("2")
    return rc, stdout, stderr


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-sync", action="store_true",
                         help="Skip pushing pack/+scripts/ (debugging only - the whole point of "
                              "this driver is that a real gate always syncs first).")
    parser.add_argument("--skip-preclean", action="store_true",
                         help="Skip killing stale java/Xvfb processes before running.")
    parser.add_argument("--timeout", type=int, default=2400,
                         help="Max seconds to wait for the remote run (default 2400).")
    args = parser.parse_args()

    api = Incus()
    if not api.is_trusted():
        print("L3 driver FAIL: Incus client certificate is not trusted by the server", file=sys.stderr)
        sys.exit(2)

    if not args.skip_preclean:
        preclean(api)

    if args.no_sync:
        print("== L3 driver: --no-sync given, running against WHATEVER is currently on vpp-l3 ==")
    else:
        sync_to_l3(api)

    try:
        rc, stdout, stderr = run_l3(api, timeout_s=args.timeout)
    except IncusError as e:
        print(f"L3 GATE: FAIL (harness error: {e})", file=sys.stderr)
        sys.exit(2)

    passed, summary = evaluate_result(rc, stdout, stderr)
    print("\n" + "=" * 72)
    print(f"L3 GATE: {'PASS' if passed else 'FAIL'}")
    print(summary)
    print("=" * 72)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
