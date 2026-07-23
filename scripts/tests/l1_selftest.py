#!/usr/bin/env python3
"""L1 self-test runner (release test architecture, DECISIONS.md "Release
test + bundling architecture - ADOPTED"). Boots the server, issues
`/vpp_selftest` via cmd_fifo (the same console-command channel every boot
test in this project already uses), waits for the command's machine-
readable summary line, and exits nonzero on FAIL or timeout.

The actual assertions live in pack/kubejs/server_scripts/selftest.js - this
script is just the driver + result parser, matching L0's shape
(scripts/tests/l0_boot_smoke.sh boots + greps the vanilla server log; this
boots + greps the KubeJS command's own summary line).

Usage: python3 scripts/tests/l1_selftest.py
Exit code 0 = PASS, nonzero = FAIL.
"""
import hashlib
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import boot_lock  # noqa: E402  (see scripts/tests/lib/boot_lock.py - #80)

ROOT = Path(__file__).resolve().parent.parent.parent
SERVER = ROOT / "server"
JDK_BIN = ROOT / ".tools" / "jdk-21.0.11+10" / "bin"
# Unique per worktree/checkout (see l0_boot_smoke.sh's LOG comment for why:
# concurrent worktrees on this machine can otherwise clobber each other's
# fixed-path /tmp log mid-boot and destroy evidence).
_WORKTREE_TAG = f"{ROOT.name}_{hashlib.sha1(str(ROOT).encode()).hexdigest()[:10]}"
LOG = Path(f"/tmp/vpp_l1_selftest_{_WORKTREE_TAG}.log")
FIFO = SERVER / "cmd_fifo"
BOOT_TIMEOUT_S = 200
COMMAND_TIMEOUT_S = 30
SHUTDOWN_TIMEOUT_S = 40

DONE_RE = re.compile(r"Done \(")
FATAL_RE = re.compile(r"Loading errors|ModLoadingException|FATAL|DirectoryLock|already locked")
RESULT_RE = re.compile(r"VPP_SELFTEST: (PASS|FAIL) \((\d+)/(\d+), (\d+) skipped\)")
LINE_RE = re.compile(r"\[(PASS|FAIL|SKIP)\] (.+?) - (.+)")


def fail(msg):
    print(f"L1 FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def run_build_server():
    print("== L1: build server/ from pack/mods.lock.json ==")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_server.py")], cwd=ROOT)
    if r.returncode != 0:
        fail("build_server.py failed")


def strip_ansi(text):
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _run_boot_and_test():
    """Everything that actually contends for the shared machine's CPU/RAM -
    run while holding the machine-wide boot lock (#80), with BOOT_TIMEOUT_S
    timed from lock acquisition, not from script/process start."""
    if FIFO.exists():
        FIFO.unlink()
    subprocess.run(["mkfifo", str(FIFO)], check=True)

    import os
    env = dict(os.environ)
    env["PATH"] = f"{JDK_BIN}:{env.get('PATH', '')}"

    print("== L1: boot server (nogui) ==")
    with open(LOG, "w") as logf:
        tail_proc = subprocess.Popen(["tail", "-f", str(FIFO)], stdout=subprocess.PIPE, cwd=SERVER)
        # Guarantee this reader dies with the process - on normal exit, an
        # uncaught exception, or a signal - so a cut-off session never
        # leaves an orphaned `tail -f cmd_fifo` holding the FIFO open (#80).
        boot_lock.register_process_cleanup(tail_proc, extra_pkill_pattern=f"tail -f {FIFO}")
        server_proc = subprocess.Popen(
            ["timeout", "240", "sh", "run.sh", "nogui"],
            cwd=SERVER, stdin=tail_proc.stdout, stdout=logf, stderr=subprocess.STDOUT, env=env,
        )

    def send_command(cmd):
        # Fresh open-write-close per command (via a subshell redirect),
        # matching this project's own proven boot-test idiom
        # (`echo "stop" > cmd_fifo`) exactly rather than holding one
        # long-lived Python file handle open across the whole boot wait -
        # a persistent handle was tried first and silently never delivered
        # any command to the running server.
        subprocess.run(["sh", "-c", f"echo {cmd!r} > {FIFO}"], check=True, timeout=10)

    try:
        print("== L1: poll for Done/fatal-error markers ==")
        deadline = time.time() + BOOT_TIMEOUT_S
        booted = False
        while time.time() < deadline:
            text = LOG.read_text(errors="replace") if LOG.exists() else ""
            clean = strip_ansi(text)
            if FATAL_RE.search(clean):
                fail(f"fatal boot error - see {LOG}")
            if DONE_RE.search(clean):
                booted = True
                break
            time.sleep(5)
        if not booted:
            fail(f"server did not reach Done( within {BOOT_TIMEOUT_S}s - see {LOG}")

        print("== L1: issue /vpp_selftest via cmd_fifo ==")
        pre_len = len(LOG.read_text(errors="replace"))
        send_command("vpp_selftest")

        deadline = time.time() + COMMAND_TIMEOUT_S
        result_line = None
        while time.time() < deadline:
            text = strip_ansi(LOG.read_text(errors="replace"))
            new_text = text[pre_len:]
            m = RESULT_RE.search(new_text)
            if m:
                # log4j's async appender can lag slightly behind the
                # console output the match was found in - settle briefly
                # and re-read so the per-assertion report below is complete.
                time.sleep(1)
                new_text = strip_ansi(LOG.read_text(errors="replace"))[pre_len:]
                result_line = RESULT_RE.search(new_text)
                full_text = new_text
                break
            time.sleep(2)
        if result_line is None:
            fail(f"no VPP_SELFTEST result line within {COMMAND_TIMEOUT_S}s - see {LOG}")

        status, passed, executed, skipped = result_line.groups()
        print(f"\n== L1 per-assertion results ==")
        for line_match in LINE_RE.finditer(full_text):
            tag, name, detail = line_match.groups()
            print(f"  [{tag}] {name} - {detail}")

        print(f"\nVPP_SELFTEST: {status} ({passed}/{executed}, {skipped} skipped)")

        if status != "PASS":
            fail(f"self-test reported FAIL ({passed}/{executed} passed, {skipped} skipped) - see per-assertion detail above")

    finally:
        print("== L1: clean stop ==")
        try:
            send_command("stop")
        except Exception:
            pass
        deadline = time.time() + SHUTDOWN_TIMEOUT_S
        while time.time() < deadline:
            if server_proc.poll() is not None:
                break
            time.sleep(2)
        if server_proc.poll() is None:
            print("L1 WARNING: server did not exit within shutdown timeout, terminating", file=sys.stderr)
            server_proc.terminate()
        tail_proc.terminate()

    print("L1 PASS: /vpp_selftest reported PASS, clean stop")


def main():
    print(f"== L1: log file for this run: {LOG} ==")
    run_build_server()

    print("== L1: acquire machine-wide boot lock (queues behind any other worktree's boot tier) ==")
    with boot_lock.BootLock():
        # BOOT_TIMEOUT_S starts counting inside _run_boot_and_test(), i.e.
        # AFTER lock acquisition - per #80, queueing behind another
        # worktree's boot must never itself cause a timeout failure.
        _run_boot_and_test()
    sys.exit(0)


if __name__ == "__main__":
    main()
