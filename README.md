# Mixtura

<div align="center">
<p>
  <img src="assets/mixtura_logo.svg" width="500" alt="Mixtura Logo">

  <h2>Mix your favorite package managers in one place.</h2>
</p>
</div>

## Overview

**Mixtura** is a unified wrapper designed to simplify the management of packages across different systems. In a computing environment where developers often rely on multiple package managers—such as Nix for reproducible development environments and Flatpak for desktop applications—monitoring and maintaining these disjointed systems can become cumbersome.

The objective of Mixtura is not to replace these tools but to provide a cohesive command-line interface that delegates tasks to the appropriate backend. By abstracting the specific commands of each underlying system, it allows users to perform common operations like installation, removal, and updates through a single, consistent syntax.

## Why Mixtura?

The name "Mixtura" comes from the combination of the English word **"Mix"**, and the Portuguese word **"Mistura"**.

It reflects the project's core philosophy: it **mixes** and unifies disparate package managers (like Nix and Flatpak) into a single, cohesive experience. It's about blending different technologies into one seamless workflow.

## Installation

To install Mixtura, it's recommended you to see the [Installation Guide](docs/Installation.md).

## Usage

The syntax is designed to be intuitive and predictable. The command is `mixtura` or `mix`.

### Installing Packages

You can mix and match providers in a single command.

```bash
# Install from the default provider (Nix)
mixtura add nixpkgs#git,vim

# Smart search: finds exact match for 'vim' (not vim-*, vimwiki, etc.)
mixtura add vim
# > Finds only the package named 'vim'

# Use wildcards for broader searches
mixtura add "vim-*"
# > Finds all packages starting with 'vim-' (vim-airline, vim-fugitive, etc.)

# Show ALL results (original behavior)
mixtura add --all vim
# > Shows all 3000+ packages containing 'vim'

# Install specifically from Flatpak
mixtura add flatpak#Spotify

# Mix Providers and Search
mixtura add nixpkgs#bottles flatpak#Sober ollama

# Install from multiple sources simultaneously
mixtura add nixpkgs#vim flatpak#OBS
```

### Removing Packages

```bash
# Remove specific packages
mixtura remove nixpkgs#git flatpak#Spotify

# Smart search for removal (exact match first)
mixtura remove vim

# Use --all to see all matching installed packages
mixtura remove --all vim
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
# Smart search: prioritizes exact match
mixtura search vim

# Use wildcards for pattern matching
mixtura search "*-nvim"    # Packages ending with -nvim
mixtura search "neovim-*"  # Packages starting with neovim-

# Show all results
mixtura search --all vim

# Search in specific provider
mixtura search flatpak#spotify
```

### Credits

Special thanks to the following people for their feedback and tips on improving the project, both visually and in terms of flexibility:

- [Leoni Frazão](https://github.com/Gameriano1)
- [Chester Berkeley](https://github.com/pedroldepizzol)
