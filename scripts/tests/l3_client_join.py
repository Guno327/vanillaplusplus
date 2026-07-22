#!/usr/bin/env python3
"""L3 live client-join test (issue #47's acceptance criteria; motivated by
#49's "hangs at Loading Terrain, never recovers" bug, retested and still
reproducing on v0.2.1 despite #50's Sable-UDP fix - see DECISIONS.md/
HANDOFF.md for that history). L0-L2 prove server boot, data/registry
sanity, and client mod loading; none of them ever join a world. This does:
boots the dedicated server under a test-only online-mode=false profile,
launches the real HeadlessMC client with the full client mod set (the same
set L2 already proves loads cleanly) plus the hmc-specifics control mod,
drives it through `connect 127.0.0.1:<port>` via HeadlessMC's own in-game
command relay, and then does the one check that actually tests the #49
symptom directly: dumps the client's currently-displayed screen with
hmc-specifics' `gui` command - resent until a real screen dump comes back
rather than trusted on the first try (see issue #62: `gui` loses the same
launcher/game FIFO race `connect` already has to fight, and a line lost to
the launcher used to make this check pass vacuously) - and fails if the
confirmed dump is still a loading/dirt-message screen after a settle window
past Sable's historical ~29s UDP-failure mark.
It does NOT assert `/vpp_selftest` as the joined player, which #47 also asked
for. That turned out not to be reachable with this toolchain; the reasoning is
recorded at the KNOWN GAP comment near the end of main(), and the checks it
would have exercised remain unexercised. L1 still covers the selftest from the
console.

ENVIRONMENT REQUIREMENT: the full client mod set includes Sodium, which
creates a real OpenGL fence object on every render tick regardless of
whether a world is even loaded. Without a real GL context the client dies
with "java.lang.RuntimeException: Failed to create fence object" within
about a tick of reaching a renderable state. (Sable's crash-header
boilerplate about "make sure this isn't caused by Sable" is a red herring
there - the throwing frame is Sodium's mixin, not Sable's.) So this script
requires `xvfb-run` on PATH; Mesa's llvmpipe software renderer is enough.

Getting HeadlessMC to actually *use* that display is the subtle part, and
an earlier revision of this file got it exactly backwards. HeadlessMC
installs its LWJGL redirection layer (headlessmc-lwjgl.jar, stubbing
lwjgl-glfw/lwjgl-opengl into no-ops) BY DEFAULT - that is its entire
purpose. Its `-lwjgl` launch flag does not select that stub; per its own
`help launch`, `-lwjgl` "Removes lwjgl code, causing Minecraft not to
render anything", i.e. it makes things *more* headless, and neither L2 nor
this script passes it. The switch that matters is the config property
`hmc.check.xvfb=true`: it makes HeadlessMC's XvfbService shell out to
`ps aux`, notice an Xvfb process, and skip the redirection layer entirely
("Running with xvfb" / "You are offline but running with xvfb, not using
headless mode"). With it off - the default - the client loads its whole mod
set, reports `OpenGL Vendor:` empty and `Backend API: NO CONTEXT`, and
then dies on Sodium's fence even though Xvfb is running perfectly. With it
on, the same run reports `OpenGL Renderer: llvmpipe` and no fence error at
all. configure_headlessmc() below writes that property, so the requirement
is enforced in-band rather than left to a hand-edited config.

Joining is driven by Minecraft's own quick-play game argument
(`--quickPlayMultiplayer <ip>`, passed via HeadlessMC's `hmc.gameargs`)
rather than by writing `connect <ip>` into the launcher's stdin. The stdin
route was tried first and does not work: the command is not resolved
against hmc-specifics' in-game command context at the time it is written,
and the run fails with "Couldn't find command for '[connect, ...]', did you
mean 'help'?". Quick-play makes the client connect as part of startup, so
there is no relay-timing window to get right.

Local-dev-sandbox-only like L2, with a stricter prerequisite: needs a real
or virtual display in addition to L2's own HeadlessMC + ~/.minecraft
research-instance requirement.

Safety rail: online-mode=false is applied only to the gitignored server/
build artifact's server.properties (rewritten from pack/server.properties
on every build_server.py run anyway) - never to pack/server.properties,
which stays the real shipped default.

Usage: python3 scripts/tests/l3_client_join.py
Exit code 0 = PASS, nonzero = FAIL.
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import l2_client_smoke as l2  # reuse load_lock()/assemble_mods_dir() - same client mod set L2 already proves loads cleanly

ROOT = Path(__file__).resolve().parent.parent.parent
SERVER = ROOT / "server"
JDK_BIN = ROOT / ".tools" / "jdk-21.0.11+10" / "bin"
HEADLESSMC_DIR = Path("/tmp/vpp-research/headlessmc")
LAUNCHER_JAR = HEADLESSMC_DIR / "headlessmc-launcher.jar"

# Unique per worktree/checkout - see l0_boot_smoke.sh's LOG comment: a fixed
# /tmp path lets concurrent worktrees on this machine clobber each other's
# log mid-run and destroy evidence.
_WORKTREE_TAG = f"{ROOT.name}_{hashlib.sha1(str(ROOT).encode()).hexdigest()[:10]}"
SERVER_LOG = Path(f"/tmp/vpp_l3_server_{_WORKTREE_TAG}.log")
CLIENT_LOG = Path(f"/tmp/vpp_l3_client_{_WORKTREE_TAG}.log")
SERVER_FIFO = SERVER / "cmd_fifo"
CLIENT_FIFO = HEADLESSMC_DIR / "l3_client_cmd_fifo"

SERVER_PORT = 25565
NEOFORGE_VERSION = "neoforge-21.1.235"

XVFB_DISPLAY = ":99"
XVFB_LOG = Path(f"/tmp/vpp_l3_xvfb_{_WORKTREE_TAG}.log")

BOOT_TIMEOUT_S = 200
CLIENT_LOAD_TIMEOUT_S = 240
JOIN_TIMEOUT_S = 60
SETTLE_S = 45  # past Sable's historical ~29s UDP-to-TCP failure window (#49) before asserting
SHUTDOWN_TIMEOUT_S = 40
# Hard cap for resending `gui` until it actually lands on the game (#62 - see
# the module docstring and parse_gui_dump()'s docstring for the race). A
# check that can silently pass without ever hearing back from the game is
# worse than no check, so this has to be a fail(), not a longer sleep.
GUI_TIMEOUT_S = 45
# Hard cap on the server process, derived rather than hardcoded: it has to
# outlive every phase that follows the boot, or it exits mid-test and the
# failure surfaces somewhere far away. A hardcoded 300s here used to kill the
# server during the post-join phase, which showed up as a missing assertion
# result rather than as "the server died".
SERVER_LIFETIME_S = (
    BOOT_TIMEOUT_S + CLIENT_LOAD_TIMEOUT_S + JOIN_TIMEOUT_S
    + SETTLE_S + GUI_TIMEOUT_S + SHUTDOWN_TIMEOUT_S + 300
)

JOIN_RE = re.compile(r"(\S+)\[/[\d.]+:\d+\] logged in with entity id")
DISCONNECT_RE = re.compile(r"lost connection|Disconnecting")
FATAL_SERVER_RE = re.compile(r"Loading errors|ModLoadingException|FATAL|DirectoryLock|already locked")
FATAL_CLIENT_RE = re.compile(r'ModLoadingException|Exception in thread "main"|Cowardly refusing')
# Ground truth for a *successful* `gui` relay (jar-verified - see
# parse_gui_dump()'s docstring for the exact javap-decompiled class/method and
# format string this is derived from). A landed `gui` always starts its
# reply with this literal prefix; nothing else in this pack's client log
# produces it.
GUI_SCREEN_PREFIX = "Screen: "
# ModernFix logs this exactly once, when the main menu is up and interactive -
# the only unambiguous "client is ready for commands" marker in this pack's
# client log. ModernFix is a hard dependency of the pack (pack/mods.lock.json),
# so keying on it is safe here even though it is mod-specific.
MAIN_MENU_RE = re.compile(r"Game took [\d.]+ seconds to start")
# #49's second root cause, and the one this tier missed on its first green run:
# ProgressiveStages 3.0.1's JEI plugin registers an ingredient listener that
# calls scheduleRefresh(), while its own refresh re-adds every unlocked fluid
# through IIngredientManager.addIngredientsAtRuntime - which notifies that same
# listener unconditionally. The client then re-adds the pack's ~249 fluids (and
# re-runs JEI's multi-second ingredient-filter rebuild) forever, which reads as
# a permanent "Loading Terrain" freeze with no crash and no stack trace. JEI
# logs one of these lines per pass, so a runaway count is a direct, cheap
# signal for it. A healthy join emits a small handful (JEI's own startup plus
# any legitimate one-shot runtime registration); the broken client emitted them
# continuously for minutes.
RUNTIME_INGREDIENT_ADD_RE = re.compile(r"Ingredients are being added at runtime")
RUNTIME_INGREDIENT_ADD_MAX = 25
# Stage granted post-join to exercise #49's item-path variant (see the probe
# in main()). Any real tier stage works; andesite_age is the first one with
# item locks behind it. Override with VPP_L3_STAGE_PROBE=<stage id>.
STAGE_PROBE = os.environ.get("VPP_L3_STAGE_PROBE", "andesite_age")
STAGE_PROBE_SETTLE_S = 30
# How the probe confirms the grant landed. Deliberately NOT the "Added
# '<stage>' stage for <player>" success line that /kubejs stages add prints:
# StageCommands.addStage only sends that when Stages.add() returns true, i.e.
# when the player did not already hold the stage (javap-confirmed) - and this
# harness reuses its world between runs, so the second run onward is a silent
# no-op and the probe would skip forever. Asking for the resulting stage LIST
# instead is true whether the grant was fresh or already in place.


def fail(msg):
    print(f"L3 FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def strip_ansi(text):
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def read(path):
    return strip_ansi(path.read_text(errors="replace")) if path.exists() else ""


def require_xvfb():
    if shutil.which("Xvfb") is None:
        fail(
            "Xvfb not found on PATH. L3 needs a real (even if software) GL "
            "surface - see this script's module docstring for why HeadlessMC's "
            "LWJGL stub cannot work for this pack's client mod set. "
            "Install Xvfb + a software GL driver (Mesa llvmpipe) and re-run."
        )


def start_xvfb():
    """Run Xvfb as an independent process and point DISPLAY at it.

    Deliberately NOT `xvfb-run <launcher>`: the launcher has to be able to exit
    (see the -quit note at the launch site) while the game keeps rendering, and
    xvfb-run ties the X server's lifetime to the command it wraps, so the
    display would die with the launcher and take the game with it.

    HeadlessMC finds this via `ps aux` + lowercase substring "xvfb", so a bare
    `Xvfb` process is detected even though the binary is capitalised.
    """
    if XVFB_LOG.exists():
        XVFB_LOG.unlink()
    with open(XVFB_LOG, "w") as logf:
        proc = subprocess.Popen(
            ["Xvfb", XVFB_DISPLAY, "-screen", "0", "1280x720x24"],
            stdout=logf, stderr=subprocess.STDOUT,
        )
    # Give the server a moment to create its socket before anything connects.
    for _ in range(20):
        if Path(f"/tmp/.X11-unix/X{XVFB_DISPLAY.lstrip(':')}").exists():
            break
        if proc.poll() is not None:
            fail(f"Xvfb exited immediately (rc={proc.returncode}) - see {XVFB_LOG}")
        time.sleep(0.5)
    else:
        fail(f"Xvfb never created its socket for {XVFB_DISPLAY} - see {XVFB_LOG}")
    print(f"== L3: Xvfb up on {XVFB_DISPLAY} (pid {proc.pid}) ==")
    return proc


def configure_headlessmc():
    """Write the HeadlessMC config properties this test depends on.

    hmc.check.xvfb=true is what stops HeadlessMC from stubbing LWJGL out
    from under Sodium (see module docstring - without it the client has no
    GL context at all and dies on a fence object even under a working Xvfb).

    hmc.keepfiles=true stops the launcher deleting the instrumented runtime
    directory it built for the game. That cleanup normally runs when the
    launcher exits, which with -quit happens while the game is still starting -
    the game then dies before rendering a frame.
    """
    cfg = HEADLESSMC_DIR / "HeadlessMC" / "config.properties"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if cfg.exists():
        for line in cfg.read_text().splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                existing[k.strip()] = v.strip()
    existing["hmc.check.xvfb"] = "true"
    existing["hmc.keepfiles"] = "true"
    existing.pop("hmc.gameargs", None)
    cfg.write_text("".join(f"{k}={v}\n" for k, v in sorted(existing.items())))
    print(f"== L3: HeadlessMC configured (check.xvfb, keepfiles) -> {cfg} ==")


def sync_client_overrides():
    """Copy pack/{config,kubejs,defaultconfigs} into the client instance.

    build_server.py does this for server/, and build_mrpack.py ships the same
    three directories under overrides/ so real players get them - but nothing
    did the equivalent for the local research instance, so the client ran with
    whatever kubejs happened to be in ~/.minecraft. That is not cosmetic: the
    pack registers its own items from pack/kubejs/startup_scripts, so a client
    missing them gets kicked during the join handshake with "The server send
    registries with unknown keys: ResourceKey[minecraft:item /
    vanillaplusplus:...]" - which looks like a pack bug but is purely a stale
    test instance.

    Copied over the top rather than replacing the directories: Prism installs
    overrides/ verbatim on top of an existing instance, and the client's own
    generated per-mod configs must survive, so this mirrors what a player gets.
    """
    print("== L3: sync pack overrides into the client instance ==")
    for sub in ("config", "kubejs", "defaultconfigs"):
        src = ROOT / "pack" / sub
        if src.exists():
            shutil.copytree(src, l2.MC_DIR / sub, dirs_exist_ok=True)
            print(f"  synced   {sub}/")


def run_build_server():
    print("== L3: build server/ from pack/mods.lock.json ==")
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_server.py")], cwd=ROOT)
    if r.returncode != 0:
        fail("build_server.py failed")


def set_test_server_properties():
    props = SERVER / "server.properties"
    text = props.read_text()
    text, n = re.subn(r"(?m)^online-mode=.*$", "online-mode=false", text)
    if n != 1:
        fail("server.properties did not have exactly one online-mode= line to override")
    props.write_text(text)


def boot_server(env):
    if SERVER_FIFO.exists():
        SERVER_FIFO.unlink()
    subprocess.run(["mkfifo", str(SERVER_FIFO)], check=True)
    print("== L3: boot server (nogui, test profile: online-mode=false) ==")
    with open(SERVER_LOG, "w") as logf:
        tail_proc = subprocess.Popen(["tail", "-f", str(SERVER_FIFO)], stdout=subprocess.PIPE, cwd=SERVER)
        subprocess.Popen(
            ["timeout", str(SERVER_LIFETIME_S), "sh", "run.sh", "nogui"],
            cwd=SERVER, stdin=tail_proc.stdout, stdout=logf, stderr=subprocess.STDOUT, env=env,
        )

    deadline = time.time() + BOOT_TIMEOUT_S
    while time.time() < deadline:
        text = read(SERVER_LOG)
        if FATAL_SERVER_RE.search(text):
            fail(f"fatal server boot error - see {SERVER_LOG}")
        if "Done (" in text:
            return
        time.sleep(5)
    fail(f"server did not reach Done( within {BOOT_TIMEOUT_S}s - see {SERVER_LOG}")


def parse_gui_dump(log_slice):
    r"""Extract the most recent complete `gui` screen dump from a client-log
    slice, or return None if no successful dump is present in it yet.

    Ground truth, jar-verified rather than assumed (#62 - see the module
    docstring for the FIFO race this exists to work around). Decompiled with
    `javap -p -c` against hmc-specifics-1.21.1-2.4.0-neoforge-release.jar:

    - me.earth.headlessmc.mc.commands.AbstractGuiCommand.execute(String,
      String...) fetches the current screen and, if one is displayed, calls
      the overridden execute(GuiScreen, String...) in
      me.earth.headlessmc.mc.commands.GuiCommand, whose bytecode loads the
      constant format string "Screen: %s\nButtons:\n%s\nTextFields:\n%s" (arg
      0 is the screen handle's Class.getName()) and passes it to
      HeadlessMc.log(String). If no screen is displayed, AbstractGuiCommand
      instead logs the literal "Minecraft is currently not displaying a
      Gui." - also a successful relay, just not a screen dump, so it is
      correctly NOT matched here.
    - io.github.headlesshq.headlessmc.api.HeadlessMc.log(String) (in
      headlessmc-launcher.jar) is a `default` method whose bytecode is a bare
      InAndOutProvider-sourced PrintStream.println(String) - i.e. no logger
      prefix, no timestamp, the format string above lands in the client log
      verbatim starting at column 0 of its own line.

    So a landed `gui` is unambiguously identified by a line starting with
    "Screen: ". A `gui` line lost to the launcher instead of the game (the
    #62 race) produces no such line at all in the client log - the launcher's
    rejection ("Couldn't find command for '[gui]', did you mean '...'?",
    itself javap-confirmed against CommandContextImpl.execute(), which builds
    that message from Arrays.toString(args)) goes to the launcher's own
    output, not this file, but is harmless here either way since it simply
    fails to match and the caller resends.

    Only the LAST "Screen: " marker in the slice is used, so duplicate
    deliveries (extra copies of `gui` reaching the game after it has already
    answered once) can't corrupt detection - the assertion always runs
    against one complete, most-recent dump.

    >>> dump = "Screen: net.minecraft.client.gui.screens.TitleScreen\nButtons:\n\nTextFields:\n"
    >>> parse_gui_dump(dump) == dump
    True
    >>> parse_gui_dump("Couldn't find command for '[gui]', did you mean 'help'?") is None
    True
    >>> mixed = ("Couldn't find command for '[gui]', did you mean 'help'?\n"
    ...          "Screen: net.minecraft.client.gui.screens.TitleScreen\nButtons:\n")
    >>> parse_gui_dump(mixed).startswith("Screen: net.minecraft.client.gui.screens.TitleScreen")
    True
    >>> parse_gui_dump("") is None
    True
    """
    idx = log_slice.rfind(GUI_SCREEN_PREFIX)
    if idx == -1:
        return None
    return log_slice[idx:]


def assert_no_refresh_loop(since_offset, window_s, phase):
    """#49's guard: a recipe-viewer plugin stuck re-adding ingredients.

    Counted over a slice of the client log rather than the whole file, so
    JEI's own legitimate startup registrations can't trip it. The healthy
    vs broken separation is enormous (0 vs 2506 in a 45s window, measured),
    so the exact cap is not delicate.
    """
    slice_text = read(CLIENT_LOG)[since_offset:]
    adds = len(RUNTIME_INGREDIENT_ADD_RE.findall(slice_text))
    print(f"== L3: {adds} runtime ingredient-add pass(es) {phase} "
          f"(cap {RUNTIME_INGREDIENT_ADD_MAX}) ==")
    if adds > RUNTIME_INGREDIENT_ADD_MAX:
        fail(
            f"{adds} 'Ingredients are being added at runtime' passes in the {window_s}s "
            f"{phase} - a recipe-viewer plugin is in a refresh feedback loop and the "
            f"client will never finish loading terrain (#49). See {CLIENT_LOG}, and "
            f"pack/manifest.json's progressivestages pin note."
        )
    return adds


def send_server_command(cmd):
    subprocess.run(["sh", "-c", f"echo {cmd!r} > {SERVER_FIFO}"], check=True, timeout=10)


def send_client_command(cmd):
    subprocess.run(["sh", "-c", f"echo {cmd!r} > {CLIENT_FIFO}"], check=True, timeout=10)


def resolve_version_id(env):
    r = subprocess.run(["java", "-jar", str(LAUNCHER_JAR)], input="exit\n", cwd=HEADLESSMC_DIR,
                        capture_output=True, text=True, timeout=30, env=env)
    for line in strip_ansi(r.stdout).splitlines():
        m = re.match(rf"^(\d+)\s+{re.escape(NEOFORGE_VERSION)}\s", line.strip())
        if m:
            return m.group(1)
    fail(f"could not find {NEOFORGE_VERSION} in HeadlessMC's own version table - see its startup output")


def ensure_hmc_specifics(version_id, env):
    print(f"== L3: ensure hmc-specifics is installed for {NEOFORGE_VERSION} ==")
    r = subprocess.run(["java", "-jar", str(LAUNCHER_JAR)],
                        input=f"specifics {version_id} hmc-specifics\nexit\n",
                        cwd=HEADLESSMC_DIR, capture_output=True, text=True, timeout=60, env=env)
    out = strip_ansi(r.stdout)
    if "successfully" not in out and "already" not in out.lower():
        fail(f"hmc-specifics install did not report success:\n{out}")


def wait_for_quiescence(logpath, ready_pattern, overall_timeout_s, quiet_s=8, poll_s=3):
    """Readiness proxy: wait for ready_pattern to appear, then for the log to
    stop growing for quiet_s seconds. HeadlessMC exposes no direct 'main
    menu ready' event this script found (see module docstring)."""
    deadline = time.time() + overall_timeout_s
    seen_marker = False
    last_size = -1
    quiet_since = None
    while time.time() < deadline:
        text = read(logpath)
        if not seen_marker:
            if re.search(ready_pattern, text):
                seen_marker = True
            else:
                if FATAL_CLIENT_RE.search(text):
                    fail(f"fatal client error before reaching readiness marker - see {logpath}")
                time.sleep(poll_s)
                continue
        size = len(text)
        if size == last_size:
            if quiet_since is None:
                quiet_since = time.time()
            elif time.time() - quiet_since >= quiet_s:
                return
        else:
            quiet_since = None
        last_size = size
        time.sleep(poll_s)
    fail(f"client log never quiesced after reaching readiness marker within {overall_timeout_s}s - see {logpath}")


def teardown(joined_username):
    if CLIENT_FIFO.exists():
        try:
            if joined_username:
                send_client_command("disconnect")
            send_client_command("quit")
        except Exception:
            pass
    try:
        send_server_command("stop")
    except Exception:
        pass
    deadline = time.time() + SHUTDOWN_TIMEOUT_S
    while time.time() < deadline:
        if subprocess.run(["pgrep", "-f", "java.*neoforge.*server"], capture_output=True).returncode != 0:
            break
        time.sleep(2)
    else:
        print(f"L3 WARN: server did not shut down within {SHUTDOWN_TIMEOUT_S}s of 'stop' - check for a stale process", file=sys.stderr)


def main():
    print(f"== L3: log files for this run: server={SERVER_LOG} client={CLIENT_LOG} xvfb={XVFB_LOG} ==")
    require_xvfb()
    configure_headlessmc()
    run_build_server()
    set_test_server_properties()

    env = dict(os.environ)
    env["PATH"] = f"{JDK_BIN}:{env.get('PATH', '')}"
    xvfb_proc = start_xvfb()
    env["DISPLAY"] = XVFB_DISPLAY

    lock = l2.load_lock()
    client_mods = [m for m in lock["mods"] if m["side"] != "server"]
    l2.assemble_mods_dir(client_mods)
    sync_client_overrides()

    boot_server(env)

    version_id = resolve_version_id(env)
    ensure_hmc_specifics(version_id, env)

    if CLIENT_FIFO.exists():
        CLIENT_FIFO.unlink()
    subprocess.run(["mkfifo", str(CLIENT_FIFO)], check=True)

    print(f"== L3: launch client on {XVFB_DISPLAY} (real, even if software, GL - see module docstring) ==")
    with open(CLIENT_LOG, "w") as logf:
        tail_proc = subprocess.Popen(["tail", "-f", str(CLIENT_FIFO)], stdout=subprocess.PIPE, cwd=HEADLESSMC_DIR)
        subprocess.Popen(
            ["timeout", str(CLIENT_LOAD_TIMEOUT_S + 180), "java", "-jar", str(LAUNCHER_JAR)],
            cwd=HEADLESSMC_DIR, stdin=tail_proc.stdout, stdout=logf, stderr=subprocess.STDOUT, env=env,
        )

    # Do NOT add -quit here in an attempt to stop the launcher competing for
    # this FIFO's stdin. It breaks the run two independent ways, both confirmed:
    # the launcher deletes the game's instrumented runtime dir on the way out
    # (hmc.keepfiles=true fixes only that half), and it relays the game's
    # stdout, so its exit closes that pipe and the game dies before rendering a
    # frame - the client log simply stops after "Game will run in". Commands do
    # reach the game's hmc-specifics context with the launcher left alive, as
    # long as they are sent after the main menu is up (see MAIN_MENU_RE).
    send_client_command(
        f'launch {NEOFORGE_VERSION} -offline -commands --retries 3 --jvm "-Dsodium.checks.issue2561=false"'
    )

    joined_username = None
    try:
        print("== L3: wait for the client to actually reach the main menu ==")
        # Must be a real main-menu marker, not just "the log went quiet". With a
        # true GL context the client renders for ~65s after the resource reload,
        # and the log has long quiet gaps mid-load; keying off quiescence alone
        # fires while the game is still loading, and a `connect` sent then is
        # resolved against the launcher's command context instead of the game's
        # ("Couldn't find command for '[connect, ...]', did you mean 'help'?").
        wait_for_quiescence(CLIENT_LOG, MAIN_MENU_RE.pattern, CLIENT_LOAD_TIMEOUT_S)

        print(f"== L3: connect to 127.0.0.1:{SERVER_PORT} ==")
        # Two non-obvious things about this command, both learned the hard way.
        #
        # 1. ip and port are SEPARATE arguments. Passing "host:port" as one arg
        #    reaches ConnectCommand fine but blows up inside it: Minecraft's
        #    ServerAddress hands the string to Guava's HostAndPort.fromParts(),
        #    which rejects a host that already carries a port. That
        #    IllegalArgumentException surfaces only as a stack trace in the
        #    client log, so the run just looks like "the client never joined".
        #
        # 2. It has to be sent repeatedly. The launcher and the game are both
        #    blocked reading this same FIFO (HeadlessMC gives the game its own
        #    stdin), so each line is delivered to whichever process the kernel
        #    happens to wake - it is a race, with no consistent winner. A line
        #    that lands on the launcher is rejected with "Couldn't find command
        #    for '[connect, ...]', did you mean 'help'?" and is simply lost.
        #    Resending until the server confirms the join is what makes this
        #    deterministic; the extra copies that reach the game after it is
        #    already connected are harmless no-ops.
        deadline = time.time() + JOIN_TIMEOUT_S
        while time.time() < deadline:
            send_client_command(f"connect 127.0.0.1 {SERVER_PORT}")
            for _ in range(4):
                m = JOIN_RE.search(read(SERVER_LOG))
                if m:
                    joined_username = m.group(1)
                    break
                time.sleep(2)
            if joined_username:
                break
        if joined_username is None:
            fail(
                f"no server-side join confirmation within {JOIN_TIMEOUT_S}s - this is exactly "
                f"the #49 failure mode if the client is hung before the server ever completes "
                f"the player-add - see {SERVER_LOG} / {CLIENT_LOG}"
            )
        print(f"== L3: server confirms {joined_username} joined ==")
        pre_len_join_client = len(read(CLIENT_LOG))

        print(f"== L3: settle {SETTLE_S}s (past Sable's historical ~29s UDP failure window, #49) ==")
        time.sleep(SETTLE_S)

        # #49's JEI-refresh-loop check. Counted over the post-join slice only,
        # so JEI's own startup registrations (pre-join) can't trip it.
        assert_no_refresh_loop(pre_len_join_client, SETTLE_S, "since join")

        text = read(SERVER_LOG)
        if DISCONNECT_RE.search(text) and joined_username in text[text.find(joined_username):]:
            fail(f"{joined_username} disconnected during the settle window - see {SERVER_LOG}")

        # #49's item-path variant. The fluid loop that froze v0.2.1 clients is
        # gone with progressivestages pinned to 2.1, but refreshJei()'s ITEM
        # path has the same shape in BOTH 2.1 and 3.0.1: it re-adds every
        # locked item id the player already owns, unconditionally, and JEI
        # notifies its listeners of every add. That is inert for a fresh
        # player only because rootborn.toml locks nothing, so nothing is
        # "owned and locked" yet - which is exactly why joining alone cannot
        # test it. Granting a real tier stage post-join is what puts entries
        # in that set. Failure to grant is a SKIP, not a FAIL: this probe may
        # only report a loop, never invent one.
        print(f"== L3: grant '{STAGE_PROBE}' post-join (#49 item-path probe) ==")
        pre_len_grant_client = len(read(CLIENT_LOG))
        send_server_command(f"kubejs stages add {joined_username} {STAGE_PROBE}")
        time.sleep(3)
        pre_len_list_server = len(read(SERVER_LOG))
        send_server_command(f"kubejs stages list {joined_username}")
        time.sleep(3)
        grant_reply = read(SERVER_LOG)[pre_len_list_server:]
        if STAGE_PROBE in grant_reply:
            print(f"== L3: settle {STAGE_PROBE_SETTLE_S}s after the grant ==")
            time.sleep(STAGE_PROBE_SETTLE_S)
            assert_no_refresh_loop(
                pre_len_grant_client, STAGE_PROBE_SETTLE_S, f"since granting {STAGE_PROBE}"
            )
        else:
            print(f"== L3: item-path probe SKIPPED - no grant confirmation for "
                  f"'{STAGE_PROBE}' (server said: {grant_reply.strip()[-200:]!r}) ==")

        print("== L3: dump the client's currently displayed screen (direct #49 reproduction check) ==")
        # `gui` has to be resent-until-confirmed for exactly the same reason
        # `connect` above does: the launcher and the game both block reading
        # the same FIFO, so a line can land on the launcher instead ("Couldn't
        # find command for '[gui]', did you mean '...'?") and be silently
        # lost. Before #62 this check sent `gui` once, slept a fixed 5s, and
        # asserted on whatever was in the log slice - on a lost line that
        # slice was simply empty, the regex below never matched, and the
        # check "passed" without ever having heard back from the game. A
        # check that cannot fail is worse than no check. parse_gui_dump()
        # holds the jar-verified ground truth for what a landed reply looks
        # like; extra copies of `gui` that land after the first confirmed
        # reply are harmless (it always keys on the last dump in the slice).
        pre_len_client = len(read(CLIENT_LOG))
        gui_deadline = time.time() + GUI_TIMEOUT_S
        gui_dump = None
        while time.time() < gui_deadline:
            send_client_command("gui")
            for _ in range(4):
                gui_dump = parse_gui_dump(read(CLIENT_LOG)[pre_len_client:])
                if gui_dump:
                    break
                time.sleep(2)
            if gui_dump:
                break
        if gui_dump is None:
            fail(
                f"the client never answered a single `gui` command with a screen dump "
                f"within {GUI_TIMEOUT_S}s - every attempt was either lost to the launcher "
                f"or produced nothing (#62: see this script's module docstring for the "
                f"FIFO race, and parse_gui_dump() for the exact ground-truthed success "
                f"format this looked for). This is a harness failure, not a #49 pass - "
                f"see {CLIENT_LOG}."
            )
        print(gui_dump.strip())
        if re.search(r"ReceivingLevelScreen|GenericDirtMessageScreen", gui_dump):
            fail(
                "client is still showing a loading/dirt-message screen after the settle "
                f"window - this IS the #49 symptom reproducing. See {CLIENT_LOG} for the "
                f"full run."
            )

        # KNOWN GAP (2026-07-22): #47 also asked for /vpp_selftest to run as the
        # joined player, so selftest.js's player-gated checks stop reporting
        # SKIP. That is not reachable with this toolchain and is deliberately
        # not asserted here rather than being faked:
        #
        #   - From the server console, `execute run vpp_selftest` works, but
        #     `execute as <player> run vpp_selftest` and the `@a` form silently
        #     produce nothing - no result, no error, no exception - with the
        #     player provably online (`list` probe) and a 150s window.
        #   - From the client, hmc-specifics 2.4.0 does not expose a usable
        #     chat verb. Its MinecraftContext references CommandCommand /
        #     MessageCommand / DotMessageCommand, but the context that actually
        #     receives our input rejects `command`, `./...` and even
        #     `disconnect` while accepting `connect`, `gui` and `menu`.
        #
        # L1 still covers the selftest console-side. The player-gated checks
        # remain unexercised anywhere, which is worth its own issue - it is a
        # gap in coverage, not a failure of this tier.
        print("== L3: in-world /vpp_selftest NOT asserted (see KNOWN GAP above) ==")

    finally:
        print("== L3: teardown ==")
        teardown(joined_username)
        xvfb_proc.terminate()

    print(
        f"L3 PASS: a real client joined, survived a {SETTLE_S}s post-join settle window past "
        f"#49's historical failure window, and was not stuck on a loading/dirt-message screen. "
        f"Does NOT assert /vpp_selftest in-world - see the KNOWN GAP note in this script."
    )


if __name__ == "__main__":
    main()
