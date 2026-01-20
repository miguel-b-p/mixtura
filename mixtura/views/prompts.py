"""
Interactive prompts for Mixtura.

Handles user input for package selection and confirmations.
"""

from typing import List, Optional, Union, TYPE_CHECKING

from mixtura.views.style import Style
from mixtura.views.logger import log_error

if TYPE_CHECKING:
    from mixtura.models.package import Package


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
