"""
Mixtura CLI - Mixed together. Running everywhere.

A unified package manager CLI that supports Nix, Flatpak, and Homebrew.
Built with Typer for a modern CLI experience.
"""

from pathlib import Path
from typing import List, Optional

import typer
from typing_extensions import Annotated

from mixtura.core.orchestrator import Orchestrator
from mixtura.core.providers import get_all_providers, get_available_providers
from mixtura.ui import console, print_logo, log_warn
from mixtura.update import check_for_updates

# Create main Typer app with Rich markup support
app = typer.Typer(
    name="mixtura",
    help="Mixed together. Running everywhere.",
    rich_markup_mode="rich",
    no_args_is_help=True,
    add_completion=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)

# Create orchestrator instance
orchestrator = Orchestrator()


def version_callback(value: bool):
    """Show version and exit."""
    if value:
        version_path = Path(__file__).parent / "VERSION"
        version = version_path.read_text().strip() if version_path.exists() else "unknown"
        console.print(f"[main]Mixtura[/main] version [bold]{version}[/bold]")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-v", callback=version_callback, is_eager=True, help="Show version")
    ] = None,
):
    """
    [bold #c8a0ff]Mixtura[/bold #c8a0ff] - Mixed together. Running everywhere.
    
    A unified package manager CLI that supports [bold]Nix[/bold], [bold]Flatpak[/bold], and [bold]Homebrew[/bold].
    """
    # Check for updates at startup
    check_for_updates()
    
    # Print logo when showing help (no subcommand)
    if ctx.invoked_subcommand is None:
        print_logo()


@app.command()
def add(
    packages: Annotated[
        List[str],
        typer.Argument(help="Package names. E.g. 'git', 'nixpkgs#vim', 'flatpak#Spotify'")
    ],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Auto-select if only one high-confidence result")
    ] = False,
    show_all: Annotated[
        bool,
        typer.Option("--all", "-a", help="Show all search results instead of filtering")
    ] = False,
):
    """
    [#78dcb4]Install[/#78dcb4] packages from Nix, Flatpak, or Homebrew.
    
    Use [bold]provider#package[/bold] syntax to specify a provider explicitly.
    Without a prefix, Mixtura searches all providers and asks you to choose.
    
    [dim]Examples:[/dim]
      mixtura add git micro          [dim]# Search and select[/dim]
      mixtura add nixpkgs#vim        [dim]# Install from Nix[/dim]
      mixtura add flatpak#Spotify    [dim]# Install from Flatpak[/dim]
    """
    print_logo()
    orchestrator.install_flow(packages, auto_confirm=yes, show_all=show_all)


@app.command()
def remove(
    packages: Annotated[
        List[str],
        typer.Argument(help="Package names to remove. E.g. 'git', 'flatpak#Spotify'")
    ],
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Auto-select if only one match")
    ] = False,
    show_all: Annotated[
        bool,
        typer.Option("--all", "-a", help="Show all matches instead of filtering")
    ] = False,
):
    """
    [#ff6ec7]Remove[/#ff6ec7] installed packages.
    
    Searches installed packages and prompts for selection.
    Use [bold]provider#package[/bold] to remove directly without search.
    """
    print_logo()
    orchestrator.remove_flow(packages, auto_confirm=yes, show_all=show_all)


@app.command()
def upgrade(
    packages: Annotated[
        Optional[List[str]],
        typer.Argument(help="Packages or providers to upgrade. Empty = upgrade all.")
    ] = None,
):
    """
    [#64c8ff]Upgrade[/#64c8ff] installed packages.
    
    Without arguments, upgrades all packages from all providers.
    Specify provider names (nixpkgs, flatpak) to upgrade a specific provider.
    
    [dim]Examples:[/dim]
      mixtura upgrade              [dim]# Upgrade everything[/dim]
      mixtura upgrade nixpkgs      [dim]# Upgrade Nix packages only[/dim]
      mixtura upgrade flatpak      [dim]# Upgrade Flatpak packages only[/dim]
    """
    print_logo()
    orchestrator.upgrade_flow(packages or [])


@app.command("list")
def list_packages(
    provider: Annotated[
        Optional[str],
        typer.Argument(help="Filter by provider: nixpkgs, flatpak, or homebrew")
    ] = None,
):
    """
    [#64c8ff]List[/#64c8ff] installed packages.
    
    Shows packages from all available providers, or filter by a specific one.
    """
    print_logo()
    orchestrator.list_flow(provider)


@app.command()
def search(
    query: Annotated[
        List[str],
        typer.Argument(help="Search terms. Use 'flatpak#term' for provider-specific search.")
    ],
    show_all: Annotated[
        bool,
        typer.Option("--all", "-a", help="Show all results instead of filtering")
    ] = False,
):
    """
    [#d2a064]Search[/#d2a064] for packages across all providers.
    
    Use [bold]provider#query[/bold] to search a specific provider.
    
    [dim]Examples:[/dim]
      mixtura search git           [dim]# Search all providers[/dim]
      mixtura search flatpak#code  [dim]# Search Flatpak only[/dim]
    """
    print_logo()
    orchestrator.search_flow(query, show_all=show_all)


@app.command()
def clean(
    modules: Annotated[
        Optional[List[str]],
        typer.Argument(help="Specific providers to clean. Empty = clean all.")
    ] = None,
):
    """
    [#d2a064]Clean[/#d2a064] up unused packages and cached data.
    
    Performs garbage collection on package managers to free up disk space.
    
    [dim]Examples:[/dim]
      mixtura clean                [dim]# Clean all providers[/dim]
      mixtura clean nixpkgs        [dim]# Clean Nix only[/dim]
    """
    print_logo()
    orchestrator.clean_flow(modules or [])


# Add info command to show available providers
@app.command()
def info():
    """
    Show information about available package managers.
    """
    print_logo()
    all_providers = get_all_providers()
    available = get_available_providers()
    
    console.print("[main bold]Available Package Managers:[/main bold]")
    console.print()
    
    for name, provider in all_providers.items():
        if name in available:
            console.print(f"  [success]●[/success] [bold]{name}[/bold] [dim](available)[/dim]")
        else:
            console.print(f"  [dim]○ {name} (not installed)[/dim]")
    
    console.print()
    
    if not available:
        log_warn("No package managers are available. Install nix, flatpak, or brew.")


if __name__ == "__main__":
    app()
