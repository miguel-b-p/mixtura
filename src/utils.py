import sys
import subprocess
from typing import List

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
    """Executes a subprocess command with visual error handling."""
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
        print() # Blank line to separate
        log_error(f"Failed to execute command.")
        log_info(f"Command: {cmd_str}")
        log_info(f"Exit code: {e.returncode}")
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        print()
        log_warn("Operation cancelled by user.")
        sys.exit(130)

def parse_package_args(packages: List[str]) -> tuple[List[str], List[str]]:
    """
    Parses a list of package arguments, handling prefixes and splitting by comma.
    Returns a tuple (nix_packages, flatpak_packages).
    
    Supported formats:
      - pkg1,pkg2 (defaults to nixpkgs)
      - nixpkgs#pkg1,pkg2
      - flatpak#pkg1,pkg2
    """
    nix_pkgs = []
    flatpak_pkgs = []

    for arg in packages:
        if arg.startswith("flatpak#"):
            # Strip prefix and split by comma
            content = arg.split("#", 1)[1]
            items = [p.strip() for p in content.split(",") if p.strip()]
            flatpak_pkgs.extend(items)
        elif arg.startswith("nixpkgs#"):
            content = arg.split("#", 1)[1]
            items = [p.strip() for p in content.split(",") if p.strip()]
            nix_pkgs.extend(items)
        else:
            # Default to nixpkgs, just split by comma
            items = [p.strip() for p in arg.split(",") if p.strip()]
            nix_pkgs.extend(items)
            
    return nix_pkgs, flatpak_pkgs
