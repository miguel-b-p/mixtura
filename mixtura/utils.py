"""
System utilities for Mixtura.

Contains subprocess execution helpers and error types.
Note: Style and log_* functions have been moved to the views layer.
"""

import sys
import subprocess
from typing import List


class CommandError(Exception):
    """
    Exception raised when a subprocess command fails.
    
    This replaces the previous behavior of calling sys.exit() directly,
    allowing callers to catch and handle errors gracefully (e.g., continue
    installing other packages even if one fails).
    """
    def __init__(self, message: str, returncode: int = 1, cmd: str = ""):
        super().__init__(message)
        self.returncode = returncode
        self.cmd = cmd

# -----------------------------------------------------------------------------
# System Helpers
# -----------------------------------------------------------------------------

def run(cmd: List[str], silent: bool = False, check_warnings: bool = False) -> None:
    """
    Execute a subprocess command with visual feedback.
    
    Args:
        cmd: Command and arguments as a list
        silent: If True, don't print the command being run
        check_warnings: If True, capture output and check for warning patterns
    
    Raises:
        CommandError: If the command fails (non-zero exit code)
    """
    # Import here to avoid circular imports
    from mixtura.views.style import Style
    from mixtura.views.logger import log_error, log_info, log_warn
    
    cmd_str = " ".join(cmd)
    
    if not silent:
        print(f"   {Style.DIM}$ {cmd_str}{Style.RESET}")

    try:
        # If we need to check warnings, we must capture output
        if check_warnings:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.stdout:
                print(result.stdout, end='')
            if result.stderr:
                print(result.stderr, file=sys.stderr, end='')
            
            if result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, cmd)
            
            err_output = result.stderr
            if "does not match any packages" in err_output or "No packages to" in err_output:
                raise subprocess.CalledProcessError(1, cmd)
        else:
            subprocess.run(cmd, check=True)

    except subprocess.CalledProcessError as e:
        print()  # Blank line to separate
        log_error(f"Failed to execute command.")
        log_info(f"Command: {cmd_str}")
        log_info(f"Exit code: {e.returncode}")
        raise CommandError(
            f"Command failed with exit code {e.returncode}",
            returncode=e.returncode,
            cmd=cmd_str
        ) from e
    except KeyboardInterrupt:
        print()
        log_warn("Operation cancelled by user.")
        raise CommandError("Operation cancelled by user.", returncode=130, cmd=cmd_str)
