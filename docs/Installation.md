# Installation

Mixtura offers three installation methods, each suited for different use cases and environments.

---

## Installation Methods Overview

| Method        | Auto-Update            | Requires Python | Best For        |
| ------------- | ---------------------- | --------------- | --------------- |
| Nuitka Binary | Yes                    | No              | End users       |
| Nix Flake     | Yes (via flake update) | No              | NixOS/Nix users |
| pip           | No                     | Yes             | Development     |

---

## 1. Nuitka Binary (Recommended, but depends of your OS.)

The pre-compiled binary is the simplest way to get started. It's a standalone executable that runs without any Python installation.

### Download and Install

```bash
curl -fsSL https://github.com/miguel-b-p/mixtura/raw/refs/heads/master/install.sh | bash
```

> [!IMPORTANT]
> Ensure that `$HOME/.local/bin` is in your shell's `PATH`.

### Why Choose This Method

- **Self-updating**: Mixtura will notify you and offer to update automatically when a new version is available
- **Zero dependencies**: No need to have Python installed on your system
- **Optimized performance**: Pre-compiled for faster startup times

---

## 2. Nix Flake

If you're on NixOS or use the Nix package manager, this is the most natural way to install Mixtura.

### Try Without Installing

```bash
nix run github:miguel-b-p/mixtura
```

### Install to Your Profile

```bash
nix profile install github:miguel-b-p/mixtura
```

### Add to NixOS Configuration

```nix
# In your flake.nix inputs:
inputs.mixtura.url = "github:miguel-b-p/mixtura";

# In your system configuration:
environment.systemPackages = [
  inputs.mixtura.packages.${pkgs.system}.default
];
```

### Development Shell

```bash
nix develop github:miguel-b-p/mixtura
```

---

## 3. pip (Python Package)

Install Mixtura as a standard Python package. This is ideal for development or if you prefer managing packages through pip.

> [!IMPORTANT]
> Mixtura will soon be published to PyPI. For now, you can install directly from GitHub.

### Install from GitHub

```bash
pip install git+https://github.com/miguel-b-p/mixtura.git
```

### Install from Source

For development purposes, clone the repository and install in editable mode:

```bash
git clone https://github.com/miguel-b-p/mixtura.git
cd mixtura
pip install -e .
```

### Important Note on Updates

When installed via pip, Mixtura cannot update itself automatically. You'll still receive a notification when a new version is available, but you'll need to run the update command manually:

```bash
pip install --upgrade git+https://github.com/miguel-b-p/mixtura.git
```

---

## Verifying Your Installation

After installing, confirm everything is working:

```bash
mixtura --version
```

You can also use the shorter alias:

```bash
mix --version
```

## Done!

You can now use Mixtura to manage your packages.
