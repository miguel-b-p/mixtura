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
        packages.default = pkgs.python3Packages.buildPythonApplication {
          pname = "mixtura";
          version = "1.21";
          pyproject = true;

          src = ./.;

          nativeBuildInputs = [
            pkgs.python3Packages.setuptools
          ];

          propagatedBuildInputs = [
            pkgs.python3Packages.typer
          ];

          meta = with pkgs.lib; {
            description = "Mixed together. Running everywhere.";
            license = licenses.asl20;
            maintainers = with maintainers; [ ];
          };
        };

        devShells.default = pkgs.mkShell {
          packages = [
            self.packages.${system}.default
            pkgs.python3
            pkgs.python3Packages.setuptools
          ];
        };
      }
    );
}
