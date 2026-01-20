"""
Logging functions for Mixtura.

Provides styled console output for different message types.
"""

import sys

from mixtura.views.style import Style


def log_info(msg: str) -> None:
    """Output an informational message."""
    print(f"{Style.INFO}ℹ{Style.RESET}  {msg}")


def log_task(msg: str) -> None:
    """Output a task/action header."""
    print(f"{Style.BOLD}{Style.MAIN}==>{Style.RESET} {msg}")


def log_success(msg: str) -> None:
    """Output a success message."""
    print(f"{Style.SUCCESS}✔{Style.RESET}  {msg}")


def log_warn(msg: str) -> None:
    """Output a warning message."""
    print(f"{Style.WARNING}⚠{Style.RESET}  {msg}")


def log_error(msg: str) -> None:
    """Output an error message to stderr."""
    print(f"{Style.ERROR}✖  Error:{Style.RESET} {msg}", file=sys.stderr)
