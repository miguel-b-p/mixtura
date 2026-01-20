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


class Style:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Logo Palette -> Semantic Names
    ERROR = "\033[38;2;255;110;199m"     # Soup Pink (was RED)
    SUCCESS = "\033[38;2;120;220;180m"   # Mint/Rainbow (was GREEN)
    WARNING = "\033[38;2;210;160;100m"  # Wood/Gold (was YELLOW)
    INFO = "\033[38;2;100;200;255m"    # Sparkle Blue (was BLUE)
    MAIN = "\033[38;2;200;160;255m"    # Lavender/Mix (was CYAN)

    ASCII = f"""{MAIN}
    ▙▗▌ ▗      ▐              
    ▌▘▌ ▄  ▚▗▘ ▜▀  ▌ ▌ ▙▀▖ ▝▀▖
    ▌ ▌ ▐  ▗▚  ▐ ▖ ▌ ▌ ▌   ▞▀▌
    ▘ ▘ ▀▘ ▘ ▘  ▀  ▝▀▘ ▘   ▝▀▘
{RESET}"""


def log_info(msg: str) -> None:
    print(f"{Style.INFO}ℹ{Style.RESET}  {msg}")

def log_task(msg: str) -> None:
    print(f"{Style.BOLD}{Style.MAIN}==>{Style.RESET} {msg}")

def log_success(msg: str) -> None:
    print(f"{Style.SUCCESS}✔{Style.RESET}  {msg}")

def log_warn(msg: str) -> None:
    print(f"{Style.WARNING}⚠{Style.RESET}  {msg}")

def log_error(msg: str) -> None:
    print(f"{Style.ERROR}✖  Error:{Style.RESET} {msg}", file=sys.stderr)


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
