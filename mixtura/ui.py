"""
User interface utilities for Mixtura.

Separates UI concerns (printing, prompts, menus) from business logic,
making the codebase more testable and maintainable.
"""

from typing import List, Optional, Union, TYPE_CHECKING

from mixtura.utils import Style, log_info, log_warn, log_error

if TYPE_CHECKING:
    from mixtura.models import Package


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


def select_package(
    packages: List[Union["Package", dict]],
    prompt: str = "Select a package",
    allow_all: bool = False,
    allow_skip: bool = True
) -> Optional[List[Union["Package", dict]]]:
    """
    Interactive menu for package selection.
    
    Args:
        packages: List of packages to choose from
        prompt: The prompt message to display
        allow_all: Whether to allow selecting all packages with 'a'
        allow_skip: Whether to allow skipping with 's'
    
    Returns:
        - List with selected package(s) if valid selection
        - Empty list if user chose to skip
        - None if invalid input or cancelled
    """
    if not packages:
        return []
    
    # Build options hint
    options = f"1-{len(packages)}"
    if allow_all:
        options += ", 'a' for all"
    if allow_skip:
        options += ", 's' to skip"
    
    try:
        choice = input(f"{Style.INFO}{prompt} ({options}): {Style.RESET}")
        choice = choice.strip().lower()
        
        # Handle skip
        if allow_skip and choice in ('s', 'q', ''):
            return []
        
        # Handle select all
        if allow_all and choice == 'a':
            return list(packages)
        
        # Handle numeric selection
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(packages):
                return [packages[idx]]
            else:
                log_error("Invalid selection.")
                return None
        except ValueError:
            log_error("Invalid input. Please enter a number.")
            return None
            
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def confirm_action(
    message: str,
    default: bool = False
) -> bool:
    """
    Ask user for confirmation.
    
    Args:
        message: The confirmation message
        default: Default value if user just presses Enter
    
    Returns:
        True if confirmed, False otherwise
    """
    default_hint = "Y/n" if default else "y/N"
    
    try:
        choice = input(f"{Style.WARNING}{message} ({default_hint}): {Style.RESET}")
        choice = choice.strip().lower()
        
        if not choice:
            return default
        
        return choice in ('y', 'yes')
        
    except (EOFError, KeyboardInterrupt):
        print()
        return False


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
    from mixtura.utils import log_success, log_error, log_warn
    
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
