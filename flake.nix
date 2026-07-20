{
  description = ''
    Vanilla++ dedicated server -- a NixOS module (primary deliverable) plus
    an optional standalone unpack helper, never deployed from this repo's
    working tree. As of #28, the server bundle is fetched declaratively
    straight from its GitHub release asset by default (nix/release.json's
    repo/tag/assetName/sha256, verified via pkgs.fetchurl's sha256 check)
    -- a manually downloaded release zip remains supported as an explicit
    override for a custom/older/different build. A Modrinth CDN fetch was
    tried first but depends on the Modrinth project's own review status,
    which stalled; GitHub's asset URL only became usable unauthenticated
    once this repo went public (see DECISIONS.md for the full history).
    See README.md's "Running on NixOS" section for host setup.
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
      mkServerPackage =
        pkgs: archivePath:
        pkgs.runCommand "vanilla-plus-plus-server-${release.version}"
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

      nixosModules.default = import ./nix/module.nix { inherit release; };
      nixosModules.vanillaplusplus = self.nixosModules.default;
    };
}
