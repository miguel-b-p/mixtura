"""
Display functions for Mixtura.

Handles formatted output of packages and operation results.
"""

from typing import List, Union, TYPE_CHECKING

from mixtura.views.style import Style
from mixtura.views.logger import log_success, log_error, log_warn

if TYPE_CHECKING:
    from mixtura.models.package import Package
    from mixtura.models.results import OperationResult


def display_package_list(
    packages: List[Union["Package", dict]],
    title: str,
    show_index: bool = True,
    max_desc_length: int = 60
) -> None:
    """
    Display a formatted list of packages.
    
    Args:
        packages: List of Package objects or dicts with package info
        title: Header text to display above the list
        show_index: Whether to show numbered indices
        max_desc_length: Maximum description length before truncation
    """
    print(f"\n{Style.BOLD}{title}:{Style.RESET}")
    
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
            print(f" {Style.SUCCESS}{i}.{Style.RESET} {Style.BOLD}{name}{Style.RESET} "
                  f"{Style.DIM}({provider} {version}){Style.RESET}")
        else:
            print(f"  {Style.SUCCESS}•{Style.RESET} {Style.BOLD}{name}{Style.RESET} "
                  f"{Style.DIM}({version}){Style.RESET}")
        
        if desc:
            print(f"    {desc}")


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
        print(f"{Style.DIM}No packages found in {provider_name}{Style.RESET}")
        return
    
    print(f"{Style.BOLD}{Style.INFO}:: {provider_name} ({len(packages)}){Style.RESET}")
    
    for pkg in packages:
        # Support both Package objects and legacy dicts
        if hasattr(pkg, 'name'):
            name = pkg.name
            extra = pkg.version or pkg.id or pkg.origin or ''
        else:
            name = pkg.get('name', 'unknown')
            extra = pkg.get('version') or pkg.get('id') or pkg.get('origin') or ''
        
        print(f"  {Style.SUCCESS}•{Style.RESET} {Style.BOLD}{name}{Style.RESET} "
              f"{Style.DIM}({extra}){Style.RESET}")


def display_operation_results(
    results: List["OperationResult"],
    success_msg: str = "Operation completed successfully.",
    partial_msg: str = "Operation completed with errors."
) -> None:
    """
    Display results of operations (install/upgrade/etc).
    
    Args:
        results: List of OperationResult objects
        success_msg: Message to show if all succeeded
        partial_msg: Message to show if some failed
    """
    print()
    success_count = 0
    
    for result in results:
        if result.success:
            log_success(result.message)
            success_count += 1
        else:
            log_error(result.message)
    
    total = len(results)
    if success_count == total:
        log_success(success_msg)
    else:
        log_warn(f"{partial_msg} ({total - success_count} error(s))")


def print_results_summary(
    results: List[tuple],
    success_msg: str = "Operation completed successfully.",
    partial_msg: str = "Operation completed with errors."
) -> None:
    """
    Print a summary of operation results.
    
    Args:
        results: List of (name, success, message) tuples
        success_msg: Message to show if all succeeded
        partial_msg: Message to show if some failed
    """
    print()
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
