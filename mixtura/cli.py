"""
Mixtura CLI - Mixed together. Running everywhere.

A unified package manager CLI that supports Nix, Flatpak, and Homebrew.
Built with Typer for a modern CLI experience.
"""

from pathlib import Path
from typing import List, Optional

import typer
from typing_extensions import Annotated

from mixtura.core.service import PackageService
from mixtura.core.package import PackageSpec, Package
from mixtura.core.providers import get_all_providers, get_available_providers
from mixtura.ui import console, print_logo, log_warn, log_info, log_task, log_error, log_success
from mixtura.ui.display import display_package_list, display_installed_packages, display_operation_results
from mixtura.ui.prompts import select_package
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

# Create service instance (stateless business logic)
service = PackageService()


def version_callback(value: bool) -> None:
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
) -> None:
    """
    [bold #c8a0ff]Mixtura[/bold #c8a0ff] - Mixed together. Running everywhere.
    
    A unified package manager CLI that supports [bold]Nix[/bold], [bold]Flatpak[/bold], and [bold]Homebrew[/bold].

    Args:
        ctx: Typer context.
        version: Flag to show version and exit.
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
) -> None:
    """
    [#78dcb4]Install[/#78dcb4] packages from Nix, Flatpak, or Homebrew.
    
    Use [bold]provider#package[/bold] syntax to specify a provider explicitly.
    Without a prefix, Mixtura searches all providers and asks you to choose.

    Args:
        packages: List of packages to install.
        yes: Auto-select if only one high-confidence result found.
        show_all: Show all search results instead of filtering fuzzy matches.
    """
    print_logo()
    
    params_for_install: List[PackageSpec] = []
    
    for arg in packages:
        # Handle comma-separated input if user does "git,vim"
        items = [p.strip() for p in arg.split(',') if p.strip()]
        
        for item in items:
            try:
                # Parse user input
                spec = PackageSpec.parse(item)
                
                # Case 1: Provider is explicit (e.g. "nixpkgs#vim")
                if spec.provider:
                    params_for_install.append(spec)
                    continue
                
                # Case 2: Ambiguous (e.g. "vim") - Search and Prompt
                log_task(f"Searching for '[bold]{spec.name}[/bold]' across all providers...")
                search_results = service.search(spec.name)
                
                if not search_results:
                    log_warn(f"No packages found for '{spec.name}'.")
                    continue

                # Filter results (simple exact match logic or show all)
                filtered = search_results
                if not show_all:
                    exact = [p for p in search_results if p.name.lower() == spec.name.lower()]
                    if exact:
                        filtered = exact

                # Auto-confirm or prompt
                if yes and len(filtered) == 1:
                    log_info(f"Auto-selecting: {filtered[0].name} ({filtered[0].provider})")
                    selected_pkg = filtered[0]
                else:
                    display_package_list(filtered, f"Found matches for '{spec.name}'")
                    # select_package returns List[Package] or None
                    user_selection = select_package(filtered, "Select specific package to install")
                    if not user_selection:
                        continue
                    selected_pkg = user_selection[0]
                    # The prompt allows checking multiple. Let's support it.
                    for p in user_selection:
                         params_for_install.append(PackageSpec(name=p.id or p.name, provider=p.provider))
                    continue # handled via loop

                # Add single selection
                params_for_install.append(PackageSpec(name=selected_pkg.id or selected_pkg.name, provider=selected_pkg.provider))

            except ValueError as e:
                log_error(f"Invalid package format '{item}': {e}")
            except Exception as e:
                log_error(f"Error processing '{item}': {e}")

    if not params_for_install:
        log_warn("No packages selected for installation.")
        return

    # Execute Installation
    console.print()
    log_task(f"Installing {len(params_for_install)} package(s)...")
    op_results = service.install(params_for_install)
    
    # Convert OperationResult to tuple format for display_operation_results
    # display expects: (name, success, message)
    display_results = [(r.provider, r.success, r.message) for r in op_results]
    display_operation_results(display_results, "Installation finished.", "Installation completed with errors.")


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
) -> None:
    """
    [#ff6ec7]Remove[/#ff6ec7] installed packages.

    Args:
        packages: List of packages to remove.
        yes: Auto-confirm actions.
        show_all: Show all matches instead of filtering.
    """
    print_logo()
    params_for_removal: List[PackageSpec] = []
    
    for arg in packages:
        items = [p.strip() for p in arg.split(',') if p.strip()]
        for item in items:
            try:
                spec = PackageSpec.parse(item)
                
                if spec.provider:
                    params_for_removal.append(spec)
                    continue
                
                # Search installed
                log_task(f"Searching installed packages for '[bold]{spec.name}[/bold]'...")
                # We need a way to list installed and filter? Or just search?
                # Service layer doesn't have "search_installed" explicitly efficiently, 
                # but list_packages is per provider.
                # Let's iterate providers via service.
                
                matches = []
                for provider_name in ["nixpkgs", "flatpak", "homebrew"]: # or get_available
                    mgr = service.get_provider(provider_name)
                    if mgr and mgr.is_available():
                        # optimize: list only if needed? list is expensive.
                        # Maybe we should assume user knows? Or implement search_installed in service?
                        # For now, let's just create generic specs if 'yes' is explicit?
                        # No, we must find where it is installed to remove it.
                        pkgs = mgr.list_packages()
                        for p in pkgs:
                            if spec.name.lower() in p.name.lower():
                                matches.append(p)
                
                if not matches:
                    log_warn(f"No installed package found matching '{spec.name}'")
                    continue
                
                # Prompt
                selected: Optional[List[Package]] = matches
                if not yes or len(matches) > 1:
                    display_package_list(matches, f"Installed matches for '{spec.name}'")
                    selected = select_package(matches, "Select packages to remove", allow_all=True)
                
                if selected:
                     for p in selected:
                         params_for_removal.append(PackageSpec(name=p.id or p.name, provider=p.provider))

            except Exception as e:
                log_error(f"Error processing '{item}': {e}")

    if not params_for_removal:
        log_warn("No packages selected for removal.")
        return

    console.print()
    log_task(f"Removing {len(params_for_removal)} package(s)...")
    results = service.remove(params_for_removal)
    
    display_results = [(r.provider, r.success, r.message) for r in results]
    display_operation_results(display_results, "Removal finished.", "Removal completed with errors.")


@app.command()
def upgrade(
    packages: Annotated[
        Optional[List[str]],
        typer.Argument(help="Packages or providers to upgrade. Empty = upgrade all.")
    ] = None,
) -> None:
    """
    [#64c8ff]Upgrade[/#64c8ff] installed packages.

    Args:
        packages: Optional list of packages or providers (e.g. 'nixpkgs') to upgrade.
    """
    print_logo()
    specs = []
    if packages:
        for arg in packages:
            try:
                specs.append(PackageSpec.parse(arg))
            except ValueError:
                specs.append(PackageSpec(name=arg)) # treat as provider name or package

    log_task("Running upgrade...")
    results = service.upgrade(specs if specs else None)
    
    display_results = [(r.provider, r.success, r.message) for r in results]
    display_operation_results(display_results, "Upgrade finished.", "Upgrade completed with errors.")


@app.command("list")
def list_packages(
    provider: Annotated[
        Optional[str],
        typer.Argument(help="Filter by provider: nixpkgs, flatpak, or homebrew")
    ] = None,
) -> None:
    """
    [#64c8ff]List[/#64c8ff] installed packages.

    Args:
        provider: Optional provider name to filter by.
    """
    print_logo()
    
    mgrs = []
    if provider:
        mgr = service.get_provider(provider)
        if mgr:
            mgrs.append(mgr)
        else:
            log_warn(f"Unknown provider '{provider}'")
            return
    else:
        # Get all available
        all_provs = get_available_providers()
        mgrs = list(all_provs.values())
        
    if not mgrs:
        log_warn("No available package managers found.")
        return
        
    for mgr in mgrs:
        if not mgr.is_available():
            continue
        log_task(f"Fetching packages from {mgr.name}...")
        pkgs = mgr.list_packages()
        display_installed_packages(pkgs, mgr.name)


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
) -> None:
    """
    [#d2a064]Search[/#d2a064] for packages across all providers.

    Args:
        query: Search terms.
        show_all: Show all results instead of filtering.
    """
    print_logo()
    
    for q in query:
        # Simple search logic
        spec = PackageSpec.parse(q)
        # Search all or specific
        if spec.provider:
            mgr = service.get_provider(spec.provider)
            if mgr:
                 results = mgr.search(spec.name)
            else:
                 results = []
        else:
            results = service.search(spec.name)
            
        if not results:
            log_warn(f"No results for '{q}'")
            continue
            
        display_package_list(results, f"Matches for '{q}'")


@app.command()
def clean(
    modules: Annotated[
        Optional[List[str]],
        typer.Argument(help="Specific providers to clean. Empty = clean all.")
    ] = None,
) -> None:
    """
    [#d2a064]Clean[/#d2a064] up unused packages.

    Args:
        modules: Specific providers to clean. If empty, cleans all.
    """
    print_logo()
    
    available = get_available_providers()
    target_provers = []
    
    if modules:
        for m in modules:
            if m in available:
                target_provers.append(available[m])
            else:
                log_warn(f"Provider '{m}' not available.")
    else:
        target_provers = list(available.values())
        
    if not target_provers:
        return

    results = []
    for mgr in target_provers:
        log_task(f"Cleaning {mgr.name}...")
        try:
            mgr.clean()
            results.append((mgr.name, True, "Cleaned"))
        except Exception as e:
            results.append((mgr.name, False, str(e)))
            
    display_operation_results(results, "Clean finished.")


@app.command()
def info() -> None:
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

if __name__ == "__main__":
    app()
