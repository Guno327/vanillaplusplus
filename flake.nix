{
  description = ''
    Vanilla++ dedicated server -- a NixOS module (primary deliverable) plus
    an optional standalone unpack helper, never deployed from this repo's
    working tree. The server bundle is fetched declaratively straight from
    this repo's own GitHub release asset, verified via pkgs.fetchurl's
    sha256 check -- a manually downloaded release zip remains supported as
    an explicit override for a custom/older/different build.

    nix/release.json is a REGISTRY: `releases` maps every published tag ->
    its asset + pinned sha256, and `latest` is an alias naming the current
    RECOMMENDED tag. The module's `releaseTag` option (default "latest")
    resolves through that alias, so operators get the recommended build with
    no edits, or can pin any specific tag (e.g. "v0.5.1"). Every mint APPENDS
    its release to the registry (scripts/update_nix_release.py); moving
    `latest` to a chosen recommended release is a deliberate separate edit
    (--set-latest). Keeping all hashes on hand is why the registry lists
    even old/broken releases.

    A flake cannot resolve "whatever is newest right now" during a pure
    evaluation (pkgs.fetchurl needs the hash up front), so consumers pick up
    a moved `latest` the ordinary Nix way -- `nix flake update` on the input
    that points at this repo. A Modrinth CDN fetch was tried first (#28) and
    abandoned: it depends on Modrinth's own project-review status, still
    pending (#44), while this repo is public so its asset URL needs no
    credentials. See README.md's "Running on NixOS" section for host setup.
  '';

  inputs = {
    # Pinned to a real, verified-current NixOS stable branch (see
    # /tmp/vpp-agent-checkpoints/nixos-flake.md for how "current" was
    # confirmed at write time: nixos-25.11 exists, 26.05 backport branches
    # exist implying 25.11 is the latest numbered stable release). Bump by
    # hand when it goes stale; this is unrelated to the server-release
    # pinning in nix/release.json.
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
  };

  outputs =
    { self, nixpkgs }:
    let
      release = builtins.fromJSON (builtins.readFile ./nix/release.json);

      # GitHub #141: the released server archive no longer bundles
      # third-party mod jars (see scripts/build_server_bundle.py) - the
      # module fetches each one itself as a fixed-output derivation, keyed
      # off the sha512 already pinned here. Read directly rather than via a
      # generated intermediate file, so pack/mods.lock.json stays the one
      # single source of truth for every mod's URL+hash, same as it always
      # has been for build_server.py/build_mrpack.py.
      modsLock = builtins.fromJSON (builtins.readFile ./pack/mods.lock.json);

      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAllSystems = f: nixpkgs.lib.genAttrs supportedSystems f;

      # Unpacks a manually-downloaded release-bundle zip into a plain
      # derivation. `archivePath` is a path to the zip you downloaded from
      # https://github.com/Guno327/vanillaplusplus/releases (see README).
      #
      # This is a standalone convenience, NOT what nixosModules.default
      # uses internally -- the module's systemd service unzips the archive
      # directly at service-start time instead (see nix/module.nix), so a
      # ~380MB bundle is never duplicated into the Nix store on top of
      # its unpacked copy in the service's dataDir. Use this if you just
      # want to inspect/build the unpacked tree standalone, e.g.:
      #   nix build --impure --expr \
      #     '(builtins.getFlake (toString ./.)).packages.${builtins.currentSystem}.server /path/to/vanilla-plus-plus-server-0.1.0.zip'
      # (a plain `nix build .#server` will NOT work since this is a
      # function of one argument, not a fixed derivation -- there is no
      # pure default zip to build from).
      #
      # GitHub #141: the archive this unpacks no longer contains third-party
      # mod jars at all (see scripts/build_server_bundle.py) -- this helper
      # does NOT run install_mods.py or fetch the per-mod derivations
      # nixosModules.default uses, so its output's mods/ will be empty (or
      # absent). It remains useful purely for inspecting the non-mod
      # contents of a release archive; use the module (or run
      # install_mods.py by hand against this package's output) for anything
      # that needs to actually boot.
      mkServerPackage =
        pkgs: archivePath:
        pkgs.runCommand "vanilla-plus-plus-server-${release.releases.${release.latest}.version}"
          { nativeBuildInputs = [ pkgs.unzip ]; }
          ''
            mkdir -p "$out"
            cd "$out"
            unzip -q ${archivePath}
            chmod +x run.sh run.bat 2>/dev/null || true
          '';
    in
    {
      packages = forAllSystems (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          server = mkServerPackage pkgs;
        }
      );

      devShells = forAllSystems (
        system:
        let
          pkgs = import nixpkgs { inherit system; };
        in
        {
          default = pkgs.mkShell {
            packages = [
              pkgs.jdk21_headless
              pkgs.python3
              pkgs.unzip
            ];
          };
        }
      );

      nixosModules.default = import ./nix/module.nix { inherit release modsLock; };
      nixosModules.vanillaplusplus = self.nixosModules.default;
    };
}
