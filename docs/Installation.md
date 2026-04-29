# Installation

Mixtura is now a Go application. It ships as a single native binary and does not require Python.

## Installation Methods Overview

| Method        | Auto-Update            | Requires Go | Best For        |
| ------------- | ---------------------- | ----------- | --------------- |
| Binary        | Yes                    | No          | End users       |
| Nix Flake     | Yes (via flake update) | No          | NixOS/Nix users |
| Source Build  | No                     | Yes         | Development     |

## 1. Binary

The pre-built binary is the simplest way to install Mixtura.

```bash
curl -fsSL https://github.com/miguel-b-p/mixtura/raw/refs/heads/master/install.sh | bash
```

Ensure that `$HOME/.local/bin` is in your shell `PATH`.

## 2. Nix Flake

Try without installing:

```bash
nix run github:miguel-b-p/mixtura
```

Install to your profile:

```bash
nix profile install github:miguel-b-p/mixtura
```

Use in a NixOS configuration:

```nix
inputs.mixtura.url = "github:miguel-b-p/mixtura";

environment.systemPackages = [
  inputs.mixtura.packages.${pkgs.system}.default
];
```

Development shell:

```bash
nix develop github:miguel-b-p/mixtura
```

## 3. Source Build

```bash
git clone https://github.com/miguel-b-p/mixtura.git
cd mixtura/src
go test ./...
./build.sh
```

The binary is written to `bin/mixtura` at the repository root.

## Verify

```bash
mixtura --version
mix --version
```
