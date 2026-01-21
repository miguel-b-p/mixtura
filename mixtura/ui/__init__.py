"""
Mixtura UI Layer.

Contains all presentation logic using Rich for beautiful terminal output.
"""

from rich.console import Console
from rich.theme import Theme

# Custom theme matching the original Mixtura color palette
# Original ANSI: MAIN=#c8a0ff, SUCCESS=#78dcb4, ERROR=#ff6ec7, INFO=#64c8ff, WARNING=#d2a064
MIXTURA_THEME = Theme({
    "main": "#c8a0ff bold",
    "main.dim": "#c8a0ff dim",
    "success": "#78dcb4",
    "success.bold": "#78dcb4 bold",
    "error": "#ff6ec7",
    "error.bold": "#ff6ec7 bold",
    "info": "#64c8ff",
    "info.bold": "#64c8ff bold",
    "warning": "#d2a064",
    "warning.bold": "#d2a064 bold",
    "dim": "dim",
    "pkg.name": "bold",
    "pkg.provider": "dim",
    "pkg.version": "dim",
})

# Global console instance
console = Console(theme=MIXTURA_THEME, highlight=False)

# ASCII Logo
ASCII_LOGO = """[main]
    ▙▗▌ ▗      ▐              
    ▌▘▌ ▄  ▚▗▘ ▜▀  ▌ ▌ ▙▀▖ ▝▀▖
    ▌ ▌ ▐  ▗▚  ▐ ▖ ▌ ▌ ▌   ▞▀▌
    ▘ ▘ ▀▘ ▘ ▘  ▀  ▝▀▘ ▘   ▝▀▘
[/main]"""


def log_info(msg: str) -> None:
    """Output an informational message."""
    console.print(f"[info]ℹ[/info]  {msg}")


def log_task(msg: str) -> None:
    """Output a task/action header."""
    console.print(f"[main]==>[/main] {msg}")


def log_success(msg: str) -> None:
    """Output a success message."""
    console.print(f"[success]✔[/success]  {msg}")


def log_warn(msg: str) -> None:
    """Output a warning message."""
    console.print(f"[warning]⚠[/warning]  {msg}")


def log_error(msg: str) -> None:
    """Output an error message to stderr."""
    import sys
    err_console = Console(theme=MIXTURA_THEME, stderr=True, highlight=False)
    err_console.print(f"[error]✖  Error:[/error] {msg}")


def print_logo() -> None:
    """Print the Mixtura ASCII logo."""
    console.print(ASCII_LOGO)


# Re-exports
__all__ = [
    "console",
    "log_info",
    "log_task",
    "log_success",
    "log_warn",
    "log_error",
    "print_logo",
    "ASCII_LOGO",
    "MIXTURA_THEME",
]
