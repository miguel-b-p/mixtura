"""
System utilities for Mixtura.

Contains subprocess execution helpers and error types.
Note: Style and log_* functions have been moved to the views layer.
"""

import sys
import subprocess
import shlex
from typing import List, Optional, Tuple, Union


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

def run(
    cmd: List[str],
    silent: bool = False,
    check_warnings: bool = False,
    show_output: bool = True,
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    timeout: Optional[int] = None
) -> None:
    """
    Execute a subprocess command with visual feedback (for interactive commands).
    
    This function is designed for commands where you want to display the command
    being run and show output in real-time (e.g., package installation).
    
    Args:
        cmd: Command and arguments as a list (NEVER pass a string - use shlex.split if needed)
        silent: If True, don't print the command being run
        check_warnings: If True, capture output and check for warning patterns
        show_output: If True, show stdout/stderr (only applies when check_warnings=True)
        cwd: Working directory for the command
        env: Environment variables (merged with current env if provided)
        timeout: Timeout in seconds (None = no timeout)
    
    Raises:
        CommandError: If the command fails (non-zero exit code)
        ValueError: If cmd is not a list
    
    Security notes:
        - Always pass cmd as a list to prevent shell injection
        - shell=False is always used (safer)
        - Never interpolate user input directly into commands
    """
    # Import here to avoid circular imports
    from mixtura.ui import console, log_error, log_info, log_warn
    
    # Security: Ensure cmd is a list, not a string
    if isinstance(cmd, str):
        raise ValueError(
            "cmd must be a list, not a string. Use shlex.split() to convert strings safely."
        )
    
    # Security: Validate that cmd is not empty
    if not cmd:
        raise ValueError("cmd cannot be empty")
    
    cmd_str = " ".join(shlex.quote(arg) for arg in cmd)
    
    if not silent:
        console.print(f"\n   [dim]$ {cmd_str}[/dim]")

    # Prepare environment
    run_env = None
    if env:
        import os
        run_env = os.environ.copy()
        run_env.update(env)

    try:
        # If we need to check warnings, we must capture output
        if check_warnings:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=cwd,
                env=run_env,
                timeout=timeout
            )
            
            if show_output:
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
            subprocess.run(
                cmd,
                check=True,
                cwd=cwd,
                env=run_env,
                timeout=timeout
            )

    except subprocess.TimeoutExpired:
        log_error(f"Command timed out after {timeout} seconds.")
        log_info(f"Command: {cmd_str}")
        raise CommandError(
            f"Command timed out after {timeout}s",
            returncode=124,
            cmd=cmd_str
        )
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


def run_capture(
    cmd: List[str],
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    timeout: Optional[int] = None,
    check: bool = False
) -> Tuple[int, str, str]:
    """
    Execute a subprocess command and capture its output (for non-interactive commands).
    
    This function is designed for commands where you need to capture and parse
    the output (e.g., listing packages, searching).
    
    Args:
        cmd: Command and arguments as a list
        cwd: Working directory for the command
        env: Environment variables (merged with current env if provided)
        timeout: Timeout in seconds (None = no timeout)
        check: If True, raise CommandError on non-zero exit code
    
    Returns:
        Tuple of (return_code, stdout, stderr)
    
    Raises:
        CommandError: If check=True and command fails
        ValueError: If cmd is not a list
    
    Security notes:
        - Always pass cmd as a list to prevent shell injection
        - shell=False is always used (safer)
    """
    # Security: Ensure cmd is a list, not a string
    if isinstance(cmd, str):
        raise ValueError(
            "cmd must be a list, not a string. Use shlex.split() to convert strings safely."
        )
    
    if not cmd:
        raise ValueError("cmd cannot be empty")
    
    # Prepare environment
    run_env = None
    if env:
        import os
        run_env = os.environ.copy()
        run_env.update(env)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            env=run_env,
            timeout=timeout
        )
        
        if check and result.returncode != 0:
            cmd_str = " ".join(shlex.quote(arg) for arg in cmd)
            raise CommandError(
                f"Command failed with exit code {result.returncode}",
                returncode=result.returncode,
                cmd=cmd_str
            )
        
        return result.returncode, result.stdout, result.stderr
        
    except subprocess.TimeoutExpired:
        cmd_str = " ".join(shlex.quote(arg) for arg in cmd)
        raise CommandError(
            f"Command timed out after {timeout}s",
            returncode=124,
            cmd=cmd_str
        )
