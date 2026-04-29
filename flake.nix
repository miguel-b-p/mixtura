{
  description = "Mixtura - A mixed package manager wrapper";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        packages.default = pkgs.buildGoModule {
          pname = "mixtura";
          version = "1.31";
          pyproject = true;

          src = ./src;
          vendorHash = null;

          postInstall = ''
            ln -s $out/bin/mixtura $out/bin/mix
          '';

          meta = with pkgs.lib; {
            description = "Mixed together. Running everywhere.";
            license = licenses.asl20;
            maintainers = with maintainers; [ ];
            mainProgram = "mixtura";
          };
        };

        devShells.default = pkgs.mkShell {
          packages = [
            pkgs.go
            pkgs.gotools
            pkgs.golangci-lint
          ];
        };
      }
    );
}
