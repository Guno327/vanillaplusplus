{
  description = ''
    Vanilla++ dedicated server -- a NixOS module (primary deliverable) plus
    an optional standalone unpack helper, never deployed from this repo's
    working tree. The server bundle is fetched declaratively straight from
    this repo's own GitHub release asset (nix/release.json's
    repo/tag/assetName/sha256, verified via pkgs.fetchurl's sha256 check)
    -- a manually downloaded release zip remains supported as an explicit
    override for a custom/older/different build.

    "Latest release" here means the newest release AS PINNED by
    nix/release.json, which scripts/update_nix_release.py rewrites on every
    mint. That indirection is not incidental: a flake cannot resolve
    "whatever is newest right now" during a pure evaluation, because
    pkgs.fetchurl needs the hash up front. Consumers therefore pick up a new
    release the ordinary Nix way -- `nix flake update` on the input that
    points at this repo -- rather than by the flake silently changing under
    them. A Modrinth CDN fetch was tried first (#28) and abandoned: it
    depends on Modrinth's own project-review status, which is still pending
    (#44), while this repo is public so its asset URL needs no credentials.
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
