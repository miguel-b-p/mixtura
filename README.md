# Mixtura

<div align="center">
<p>
  <img src="assets/logo.png" width="300" alt="Mixtura Logo">

  <h2>Mixed together. Running everywhere.</h2>
</p>
</div>

## Overview

**Mixtura** is a unified wrapper designed to simplify the management of packages across different systems. In a computing environment where developers often rely on multiple package managers—such as Nix for reproducible development environments and Flatpak for desktop applications—monitoring and maintaining these disjointed systems can become cumbersome.

The objective of Mixtura is not to replace these tools but to provide a cohesive command-line interface that delegates tasks to the appropriate backend. By abstracting the specific commands of each underlying system, it allows users to perform common operations like installation, removal, and updates through a single, consistent syntax.

## Why Mixtura?

The name "Mixtura" comes from the combination of the English word **"Mix"** and the Portuguese word **"Mistura"**.

It reflects the project's core philosophy: it **mixes** and unifies disparate package managers (like Nix and Flatpak) into a single, cohesive experience. It's about blending different technologies into one seamless workflow.

## Installation

To install Mixtura, run the following command, which downloads the latest compiled binary and places it in your local binary directory.

```bash
curl -fsSL https://github.com/miguel-b-p/mixtura/raw/refs/heads/master/install.sh | bash
```

Ensure that `$HOME/.local/bin` is in your shell's `PATH`.

## Usage

The syntax is designed to be intuitive and predictable. The command is `mixtura` or `mix`.

### Installing Packages

You can mix and match providers in a single command.

```bash
# Install from the default provider (Nix)
mixtura add nixpkgs#git

# Install with interactive search (if provider not specified)
mixtura add git
# > Searches all providers and prompts for selection

# Install specifically from Flatpak
mixtura add flatpak#Spotify
# Or
mix add flatpak#Spotify

# Install from multiple sources simultaneously
mixtura add nixpkgs#vim flatpak#OBS
# Or
mix add nixpkgs#vim flatpak#OBS
```

### Removing Packages

```bash
mixtura remove git flatpak#Spotify
```

### Upgrading

Upgrading can be performed globally or targeted to a specific provider.

```bash
# Upgrade all packages across all providers
mixtura upgrade

# Upgrade only Nix packages
mixtura upgrade nixpkgs
```

### Searching

```bash
mixtura search "web browser" flatpak#spotify
```
