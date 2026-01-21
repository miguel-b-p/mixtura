"""
Display functions for Mixtura using Rich.

Provides beautiful formatted output for packages and operation results.
"""

from typing import List, Union, TYPE_CHECKING

from mixtura.ui import console, log_success, log_error, log_warn

if TYPE_CHECKING:
    from mixtura.core.package import Package


def display_package_list(
    packages: List[Union["Package", dict]],
    title: str,
    show_index: bool = True,
    max_desc_length: int = 60
) -> None:
    """
    Display a formatted list of packages using Rich.
    
    Args:
        packages: List of Package objects or dicts with package info
        title: Header text to display above the list
        show_index: Whether to show numbered indices
        max_desc_length: Maximum description length before truncation
    """
    console.print()
    console.print(f"[main bold]{title}:[/main bold]")
    
    for i, pkg in enumerate(packages, 1):
        # Support both Package objects and legacy dicts
        if hasattr(pkg, 'name'):
            name = pkg.name
            provider = pkg.provider
            version = pkg.version
            desc = pkg.description
        else:
            name = pkg.get('name', 'unknown')
            provider = pkg.get('provider', 'unknown')
            version = pkg.get('version', '')
            desc = pkg.get('description', '')
        
        # Truncate description if needed
        if len(desc) > max_desc_length:
            desc = desc[:max_desc_length] + "..."
        
        # Format output
        if show_index:
            console.print(f" [success]{i}.[/success] [bold]{name}[/bold] [dim]({provider} {version})[/dim]")
        else:
            console.print(f"  [success]•[/success] [bold]{name}[/bold] [dim]({version})[/dim]")
        
        if desc:
            console.print(f"    {desc}")


def display_installed_packages(
    packages: List[Union["Package", dict]],
    provider_name: str
) -> None:
    """
    Display a list of installed packages for a provider.
    
    Args:
        packages: List of Package objects or dicts
        provider_name: Name of the provider
    """
    if not packages:
        console.print(f"[dim]No packages found in {provider_name}[/dim]")
        return
    
    console.print(f"[info bold]:: {provider_name} ({len(packages)})[/info bold]")
    
    for pkg in packages:
        # Support both Package objects and legacy dicts
        if hasattr(pkg, 'name'):
            name = pkg.name
            extra = pkg.version or pkg.id or getattr(pkg, 'origin', '') or ''
        else:
            name = pkg.get('name', 'unknown')
            extra = pkg.get('version') or pkg.get('id') or pkg.get('origin') or ''
        
        console.print(f"  [success]•[/success] [bold]{name}[/bold] [dim]({extra})[/dim]")


def display_operation_results(
    results: List[tuple],
    success_msg: str = "Operation completed successfully.",
    partial_msg: str = "Operation completed with errors."
) -> None:
    """
    Display results of operations (install/upgrade/etc).
    
    Args:
        results: List of (name, success, message) tuples
        success_msg: Message to show if all succeeded
        partial_msg: Message to show if some failed
    """
    console.print()
    success_count = 0
    
    for name, success, message in results:
        if success:
            log_success(message)
            success_count += 1
        else:
            log_error(message)
    
    total = len(results)
    if success_count == total:
        log_success(success_msg)
    else:
        log_warn(f"{partial_msg} ({total - success_count} error(s))")
