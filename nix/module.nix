{ release }:
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.services.vanillaplusplus;

  # Ground-truthed verbatim from server/user_jvm_args.txt (the released
  # bundle's own shipped default): -Xms6G/-Xmx6G + the full Aikar's-flags
  # G1GC tuning preset (https://docs.papermc.io/paper/aikars-flags).
  defaultJvmOpts = [
    "-Xms6G"
    "-Xmx6G"
    "-XX:+UseG1GC"
    "-XX:+ParallelRefProcEnabled"
    "-XX:MaxGCPauseMillis=200"
    "-XX:+UnlockExperimentalVMOptions"
    "-XX:+DisableExplicitGC"
    "-XX:+AlwaysPreTouch"
    "-XX:G1NewSizePercent=30"
    "-XX:G1MaxNewSizePercent=40"
    "-XX:G1HeapRegionSize=8M"
    "-XX:G1ReservePercent=20"
    "-XX:G1HeapWastePercent=5"
    "-XX:G1MixedGCCountTarget=4"
    "-XX:InitiatingHeapOccupancyPercent=15"
    "-XX:G1MixedGCLiveThresholdPercent=90"
    "-XX:G1RSetUpdatingPauseTimePercent=5"
    "-XX:SurvivorRatio=32"
    "-XX:+PerfDisableSharedMem"
    "-XX:MaxTenuringThreshold=1"
  ];

  # NeoForge's shipped unix_args.txt path is version-specific (the bundle
  # ships its own libraries/ tree) -- read from the release pin rather than
  # hardcoded, so a future release bump only requires re-running
  # scripts/update_nix_release.py (which auto-detects this from the zip)
  # rather than editing this module.
  neoforgeVersion = release.neoforgeVersion or "21.1.235";
  unixArgsRelPath = "libraries/net/neoforged/neoforge/${neoforgeVersion}/unix_args.txt";

  expectedSha256Hex = release.sha256Hex or null;
  expectedTag = release.tag or release.version or "unknown";

  # #28: fetch the pinned release's server bundle straight from its GitHub
  # release asset -- a REAL declarative fetch (pkgs.fetchurl, a
  # fixed-output derivation Nix verifies against the pinned sha256 itself
  # at build time and refuses to proceed on mismatch), unconditionally
  # available for every release since nix/release.json always carries
  # repo/tag/assetName/sha256 (unlike the optional `modrinth` pin, which
  # depends on Modrinth's own async publish + project-review status and
  # was 404ing as of this writing -- see DECISIONS.md's dated entry).
  # This used to require a manually downloaded zip because the repo was
  # private (no unauthenticated URL to fetch from); the repo has since
  # gone public, so the plain release-asset URL works unauthenticated --
  # confirmed live (HEAD request, 200, correct byte size) before relying
  # on it here. `release.sha256` is already SRI-formatted
  # (`sha256-...`), which pkgs.fetchurl accepts directly.
  githubServerArchive = pkgs.fetchurl {
    url = "https://github.com/${release.repo}/releases/download/${release.tag}/${release.assetName}";
    sha256 = release.sha256;
  };

  propType = lib.types.oneOf [
    lib.types.str
    lib.types.bool
    lib.types.int
  ];
  propToString = v: if builtins.isBool v then (if v then "true" else "false") else toString v;

  serverPropertiesOverlayScript =
    let
      lines = lib.mapAttrsToList (
        k: v: ''props[${lib.escapeShellArg k}]=${lib.escapeShellArg (propToString v)}''
      ) cfg.serverProperties;
    in
    lib.concatStringsSep "\n" lines;

  # Unzips + syncs services.vanillaplusplus.serverArchive (defaults to a
  # pkgs.fetchurl-fetched Nix store path from GitHub, see
  # githubServerArchive above; may instead be a manually downloaded
  # release zip if the operator overrode it -- see README's "Running on
  # NixOS" section) into dataDir, preserving world/, logs/,
  # crash-reports/, server.properties, and eula.txt across upgrades.
  # Unzips into an isolated /tmp staging dir
  # (PrivateTmp=true means this never collides with anything, and it's
  # never left inside dataDir where it could confuse the rsync
  # source/destination relationship) rather than through a Nix-store
  # derivation, so the ~380MB+ bundle is never duplicated into the store on
  # top of its unpacked copy in dataDir.
  syncScript = pkgs.writeShellScript "vanillaplusplus-sync" ''
    set -euo pipefail

    ARCHIVE=${lib.escapeShellArg cfg.serverArchive}
    DATA_DIR=${lib.escapeShellArg cfg.dataDir}
    STAMP="$DATA_DIR/.vpp-installed-archive"

    if [ ! -f "$ARCHIVE" ]; then
      echo "vanillaplusplus: services.vanillaplusplus.serverArchive ($ARCHIVE) does not exist or is not a regular file -- see README.md's 'Running on NixOS' section" >&2
      exit 1
    fi

    mkdir -p "$DATA_DIR"

    # Cheap size+mtime fingerprint to decide whether a re-sync is needed at
    # all -- avoids re-unzipping/re-rsyncing a ~380MB tree on every plain
    # restart when nothing changed.
    FINGERPRINT="$(${pkgs.coreutils}/bin/stat -c '%s %Y' "$ARCHIVE")"

    if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$FINGERPRINT" ]; then
      echo "vanillaplusplus: serverArchive changed (or first run) -- unpacking + syncing into $DATA_DIR"

      STAGING="$(${pkgs.coreutils}/bin/mktemp -d)"
      trap 'rm -rf "$STAGING"' EXIT
      ${pkgs.unzip}/bin/unzip -q "$ARCHIVE" -d "$STAGING"

      ${lib.optionalString (expectedSha256Hex != null) ''
        ACTUAL_SHA256="$(${pkgs.coreutils}/bin/sha256sum "$ARCHIVE" | cut -d' ' -f1)"
        if [ "$ACTUAL_SHA256" = ${lib.escapeShellArg expectedSha256Hex} ]; then
          echo "vanillaplusplus: serverArchive sha256 matches nix/release.json's pinned release (${expectedTag})"
        else
          echo "vanillaplusplus: WARNING -- serverArchive's sha256 ($ACTUAL_SHA256) does NOT match nix/release.json's pinned hash for ${expectedTag} (expected ${expectedSha256Hex}). Proceeding anyway -- this is fine if you're intentionally running a different/custom/older build, otherwise you may not be running the release you expect." >&2
        fi
      ''}

      # world/, logs/, crash-reports/, server.properties, eula.txt,
      # user_jvm_args.txt (nix-declared, see below), and our own state
      # files are NEVER touched by this sync -- only the bundle's own
      # mods/config/kubejs/defaultconfigs/libraries/run.sh/run.bat.
      ${pkgs.rsync}/bin/rsync -a --delete \
        --exclude=/world \
        --exclude=/logs \
        --exclude=/crash-reports \
        --exclude=/server.properties \
        --exclude=/eula.txt \
        --exclude=/user_jvm_args.txt \
        --exclude=/cmd_fifo \
        --exclude=/.vpp-installed-archive \
        "$STAGING"/ "$DATA_DIR"/

      # server.properties is deliberately excluded from the rsync above (so
      # upgrades never clobber the operator's live copy) -- stash the
      # shipped default here, before $STAGING is torn down, purely so the
      # server.properties merge step below has something to seed a
      # genuinely first-ever boot from. Removed again once that step
      # consumes it.
      cp "$STAGING/server.properties" "$DATA_DIR/.vpp-shipped-server.properties"

      echo "$FINGERPRINT" > "$STAMP"
    else
      echo "vanillaplusplus: serverArchive unchanged, skipping unpack+sync"
    fi

    # eula.txt: the shipped bundle deliberately never pre-accepts this (see
    # README.md / scripts/build_server_bundle.py's own README string) --
    # the NixOS module mirrors that stance via the `eula` option's
    # assertion (see options below): the service simply refuses to
    # evaluate unless the operator has explicitly set eula = true, at which
    # point writing exactly "eula=true" here is safe and intentional.
    echo "eula=true" > "$DATA_DIR/eula.txt"

    # user_jvm_args.txt is fully nix-declared (services.vanillaplusplus.jvmOpts)
    # rather than synced from the bundle -- regenerated fresh every start so
    # it's never stale runtime state.
    {
      ${lib.concatMapStringsSep "\n      " (o: "echo ${lib.escapeShellArg o}") cfg.jvmOpts}
    } > "$DATA_DIR/user_jvm_args.txt"

    # server.properties: merge cfg.serverProperties onto whatever's
    # currently on disk (the shipped default on first boot, or the
    # operator's own hand-edited copy on every boot after) -- nix-declared
    # keys always win, everything else (including manual edits outside of
    # this module) survives untouched.
    PROPS="$DATA_DIR/server.properties"
    SRC="$PROPS"
    if [ ! -f "$PROPS" ]; then
      SRC="$DATA_DIR/.vpp-shipped-server.properties"
    fi
    if [ ! -f "$SRC" ]; then
      SRC=/dev/null
    fi
    ${pkgs.gawk}/bin/awk -F= '
      /^[[:space:]]*#/ { next }
      /^[[:space:]]*$/ { next }
      { key=$1; sub(/^[^=]*=/, "", $0); print key "\x01" $0 }
    ' "$SRC" > "$DATA_DIR/.vpp-props.tmp"

    declare -A props
    while IFS=$'\x01' read -r k v; do
      [ -z "$k" ] && continue
      props["$k"]="$v"
    done < "$DATA_DIR/.vpp-props.tmp"
    rm -f "$DATA_DIR/.vpp-props.tmp"

    ${serverPropertiesOverlayScript}

    {
      for k in "''${!props[@]}"; do
        printf '%s=%s\n' "$k" "''${props[$k]}"
      done
    } | sort > "$PROPS.new"
    mv "$PROPS.new" "$PROPS"
    rm -f "$DATA_DIR/.vpp-shipped-server.properties"

    # Fresh fifo every start (stale one from a prior boot, if any, is not
    # reusable once its reader/writer pair is gone).
    rm -f "$DATA_DIR/cmd_fifo"
    ${pkgs.coreutils}/bin/mkfifo "$DATA_DIR/cmd_fifo"
  '';

  # Launch: replicates run.sh's own java invocation
  # (`java @user_jvm_args.txt @libraries/.../unix_args.txt "$@"`) using the
  # nix-provided JDK rather than relying on run.sh/PATH `java` at all. Feeds
  # stdin from cmd_fifo via process substitution (bash-only, hence
  # writeShellScript not a plain sh script) so ExecStop can send a clean
  # "stop" console command -- the exact mechanism this repo's own dev
  # boot-testing already validated (HANDOFF.md) as the reliable clean-stop
  # path, in preference to relying solely on SIGTERM semantics.
  # `exec java ...` replaces this wrapper script's own process with java,
  # so systemd's main PID for the unit IS java (not a lingering wrapper
  # shell waiting on the tail-in-a-process-substitution, which never exits
  # on its own -- that orphaned reader gets reaped by systemd's normal
  # cgroup cleanup once the unit stops).
  launchScript = pkgs.writeShellScript "vanillaplusplus-launch" ''
    set -euo pipefail
    cd ${lib.escapeShellArg cfg.dataDir}
    exec ${pkgs.jdk21_headless}/bin/java @user_jvm_args.txt @${unixArgsRelPath} nogui < <(${pkgs.coreutils}/bin/tail -f cmd_fifo)
  '';

  stopScript = pkgs.writeShellScript "vanillaplusplus-stop" ''
    set -euo pipefail
    echo stop > ${lib.escapeShellArg cfg.dataDir}/cmd_fifo
  '';

in
{
  options.services.vanillaplusplus = {
    enable = lib.mkEnableOption "the Vanilla++ Minecraft dedicated server";

    eula = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = ''
        Whether you agree to Mojang's EULA (https://aka.ms/MinecraftEULA).
        This MUST be explicitly set to `true` -- mirrors both upstream
        NixOS's own `services.minecraft-server.eula` option and the
        released server bundle's own refusal to start without an
        eula.txt containing `eula=true` (see README.md's "Server setup"
        section / scripts/build_server_bundle.py). Leaving this at its
        default `false` makes the service fail to evaluate (assertion),
        not fail at runtime.
      '';
    };

    serverArchive = lib.mkOption {
      type = lib.types.path;
      default = githubServerArchive;
      defaultText = lib.literalExpression ''
        # a pkgs.fetchurl derivation pulling the pinned release's server
        # bundle straight from its GitHub release asset (repo/tag/
        # assetName/sha256 in nix/release.json)
        pkgs.fetchurl {
          url = "https://github.com/Guno327/vanillaplusplus/releases/download/...";
          sha256 = "sha256-...";
        }
      '';
      example = "/root/vanilla-plus-plus-server-0.1.0.zip";
      description = ''
        Path to a Vanilla++ server release zip. **Defaults to a real,
        declarative `pkgs.fetchurl` fetch straight from the pinned
        release's GitHub asset** (`nix/release.json`, currently pinned at
        version ${release.version}) -- Nix verifies the download against
        the pinned `sha256` itself as part of evaluating this
        fixed-output derivation and refuses to proceed on a mismatch, no
        separate runtime check needed for the default path.

        Override this (a manually downloaded
        `vanilla-plus-plus-server-*.zip` from
        https://github.com/Guno327/vanillaplusplus/releases, or any other
        build) if you want a different/custom/older bundle than what's
        currently pinned -- give it a **plain string path** if you don't
        want that build copied into the Nix store (stays a live reference
        to wherever it is on disk), or a **Nix path literal** (e.g.
        `./vanilla-plus-plus-server-0.1.0.zip`) if you're fine with that
        store copy. The module unzips whatever this resolves to itself at
        service-start time (not at build time), and additionally checks
        it against `nix/release.json`'s pinned sha256 on every (re)sync,
        logging a warning (not a failure) on a mismatch -- this runtime
        check is now mostly relevant to the override path, since the
        default is already verified at build time.
      '';
    };

    jvmOpts = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = defaultJvmOpts;
      defaultText = lib.literalExpression ''
        # verbatim from the released bundle's user_jvm_args.txt:
        [ "-Xms6G" "-Xmx6G" "-XX:+UseG1GC" ... Aikar's flags ... ]
      '';
      description = ''
        JVM arguments written to `user_jvm_args.txt` in `dataDir` on every
        start (fully nix-declared -- not synced from the release bundle).
        Defaults to the exact `-Xms6G -Xmx6G` + Aikar's-flags G1GC preset
        (https://docs.papermc.io/paper/aikars-flags) the release bundle
        itself ships. Raise `-Xmx`/`-Xms` together, not separately, if you
        have more RAM and see GC pauses in the logs (per README.md's own
        guidance -- this pack realistically wants 6-8GB).
      '';
    };

    dataDir = lib.mkOption {
      type = lib.types.path;
      default = "/var/lib/vanillaplusplus";
      description = ''
        Directory holding all persistent server state: `world/`, `logs/`,
        `crash-reports/`, `server.properties`, `eula.txt`, plus a synced
        (and upgrade-preserving) copy of the release bundle's `mods/`,
        `config/`, `kubejs/`, `defaultconfigs/`, `libraries/`.
      '';
    };

    openFirewall = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Whether to open `port` in the firewall.";
    };

    port = lib.mkOption {
      type = lib.types.port;
      default = 25565;
      description = ''
        TCP port the server listens on. Also written into
        `server.properties`'s `server-port` key (via `serverProperties`,
        merged automatically -- you do not need to duplicate this in
        `serverProperties` yourself).
      '';
    };

    user = lib.mkOption {
      type = lib.types.str;
      default = "vanillaplusplus";
      description = ''
        Static (not DynamicUser) system user the server runs as. Static by
        design: DynamicUser's ephemeral-UID/tmpfs-backed state handling is
        a poor fit for a ~400MB+ dataDir (mods/libraries/world) that must
        persist byte-identically across restarts and reboots.
      '';
    };

    group = lib.mkOption {
      type = lib.types.str;
      default = "vanillaplusplus";
      description = "Static system group the server runs as.";
    };

    serverProperties = lib.mkOption {
      type = lib.types.attrsOf propType;
      default = { };
      example = lib.literalExpression ''
        {
          motd = "Vanilla++ - Create-centric progression overhaul";
          max-players = 20;
          difficulty = "normal";
          online-mode = true;
        }
      '';
      description = ''
        Attrset merged onto the release bundle's shipped
        `server.properties` (which ships with `online-mode=true` -- see
        README.md's "Server setup" step 5 for the security tradeoff of
        flipping that). Merged non-destructively on every start: these
        keys always win, but any other key already present in
        `dataDir/server.properties` (from the shipped default on first
        boot, or the operator's own manual edits afterward) is preserved
        untouched. `server-port` is set automatically from the `port`
        option unless you override it here too.
      '';
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = cfg.eula;
        message = ''
          services.vanillaplusplus.eula must be set to true to indicate
          agreement with the Minecraft EULA (https://aka.ms/MinecraftEULA).
          This mirrors both the shipped bundle's own refusal to start
          without eula.txt containing eula=true, and NixOS's own upstream
          services.minecraft-server.eula option.
        '';
      }
    ];

    services.vanillaplusplus.serverProperties."server-port" = lib.mkDefault cfg.port;

    users.users.${cfg.user} = {
      isSystemUser = true;
      group = cfg.group;
      home = cfg.dataDir;
      createHome = false;
      description = "Vanilla++ Minecraft server";
    };
    users.groups.${cfg.group} = { };

    systemd.tmpfiles.rules = [
      "d ${cfg.dataDir} 0750 ${cfg.user} ${cfg.group} - -"
    ];

    networking.firewall = lib.mkIf cfg.openFirewall {
      allowedTCPPorts = [ cfg.port ];
    };

    systemd.services.vanillaplusplus = {
      description = "Vanilla++ Minecraft dedicated server";
      wantedBy = [ "multi-user.target" ];
      after = [ "network.target" ];

      # Belt-and-suspenders SIGTERM handling stays as the fallback path
      # (vanilla/NeoForge servers register a JVM shutdown hook that saves
      # + stops cleanly on SIGTERM too), but the PRIMARY, verified-working
      # stop mechanism replicates this repo's own dev boot-test tooling
      # exactly (HANDOFF.md's boot-test methodology: `echo "stop" >
      # cmd_fifo` for a clean shutdown) via ExecStop below, since that is
      # the one mechanism this project has actually exercised repeatedly
      # and confirmed clean (HANDOFF.md explicitly warns that an UNCLEAN
      # stop leaves a stale world/ DirectoryLock).
      serviceConfig = {
        Type = "simple";
        User = cfg.user;
        Group = cfg.group;
        WorkingDirectory = cfg.dataDir;
        ExecStartPre = "${syncScript}";
        ExecStart = "${launchScript}";
        ExecStop = "${stopScript}";
        Restart = "on-failure";
        RestartSec = 10;
        # Generous: world saves on a ~400MB+ world can take real time; only
        # escalates to SIGKILL (KillSignal default) if the clean "stop"
        # path above somehow never completes.
        TimeoutStopSec = 120;
        KillSignal = "SIGTERM";

        # Hardening basics. No DynamicUser (see the `user` option's
        # description); a static user is the right tradeoff here.
        NoNewPrivileges = true;
        PrivateTmp = true;
        ProtectSystem = "strict";
        ProtectHome = true;
        ReadWritePaths = [ cfg.dataDir ];
        ProtectKernelTunables = true;
        ProtectKernelModules = true;
        ProtectControlGroups = true;
        RestrictSUIDSGID = true;
        LockPersonality = true;
      };
    };
  };
}
