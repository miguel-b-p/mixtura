import argparse
import sys
import hashlib
import os
import subprocess


from utils import Style
from commands import cmd_add, cmd_remove, cmd_upgrade, cmd_list, cmd_search
from manager import ModuleManager

class ColoredHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def start_section(self, heading):
        if heading:
            heading = f"{Style.BOLD}{Style.CYAN}{heading.title()}{Style.RESET}"
        super().start_section(heading)

    def _format_usage(self, usage, actions, groups, prefix):
        if prefix is None:
            prefix = 'usage: '
        prefix = f"{Style.BOLD}{Style.GREEN}{prefix}{Style.RESET}"
        return super()._format_usage(usage, actions, groups, prefix)

def check_for_updates():
    """Checks if there is a new version available by comparing hashes."""
    # Only check if running as a compiled executable (Nuitka)
    #if not getattr(sys, 'frozen', False):
    #    return

    github_hash_url = "https://raw.githubusercontent.com/miguel-b-p/mixtura/refs/heads/master/bin/HASH"
    try:
        # 1. Calculate local hash using system command
        executable_path = os.path.join(os.path.dirname(sys.argv[0])) + "/mixtura"
        print("executable path:", executable_path)

        # Use sha256sum command
        result = subprocess.run(
            ["sha256sum", executable_path], 
            capture_output=True, 
            text=True, 
            check=True
        )
        # Expected output format: "hash  filename"
        local_hash = result.stdout.split()[0]

        # 2. Fetch remote hash
        result = subprocess.run(
            ["curl", "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "-sL", github_hash_url],
            capture_output=True,
            text=True,
            check=True
        )
        remote_hash = result.stdout.strip()
        print("local hash:", local_hash)
        print("remote hash:", remote_hash)

        # 3. Compare
        if local_hash.lower() != remote_hash.lower():
            print(f"{Style.BOLD}{Style.YELLOW}NOTICE: A new version of Mixtura is available!{Style.RESET}")
            print(f"Please update to the latest version.")
            print()
            
    except Exception:
        # Fail silently on network errors or other issues to not disrupt usage
        pass

def main() -> None:
    check_for_updates()

    # Ensure modules are discovered
    manager = ModuleManager.get_instance()
    available_managers = manager.get_all_managers()
    
    # Build list of manager names for help
    mgr_names = [m.name for m in available_managers if m.is_available()]
    mgr_help_str = "\n".join([f"  {Style.BOLD}{name}{Style.RESET}" for name in mgr_names])
    if not mgr_help_str:
        mgr_help_str = "  (none installed)"

    main_epilog = f"""
{Style.BOLD}{Style.CYAN}Available Managers:{Style.RESET}
{mgr_help_str}

{Style.BOLD}EXAMPLES:{Style.RESET}
  {Style.GREEN}#{Style.RESET} Install packages from Nix (default)
  {Style.DIM}$ mixtura add micro git{Style.RESET}

  {Style.GREEN}#{Style.RESET} Install packages from Flatpak
  {Style.DIM}$ mixtura add flatpak#Spotify,"OBS Studio"{Style.RESET}

  {Style.GREEN}#{Style.RESET} Install mixed packages
  {Style.DIM}$ mixtura add nixpkgs#vim flatpak#equibop{Style.RESET}

  {Style.GREEN}#{Style.RESET} Search for packages
  {Style.DIM}$ mixtura search "web browser" flatpak#spotify{Style.RESET}

  {Style.GREEN}#{Style.RESET} Upgrade all packages
  {Style.DIM}$ mixtura upgrade{Style.RESET}

  {Style.GREEN}#{Style.RESET} Run manager specific commands
  {Style.DIM}$ mixtura nixpkgs --gc{Style.RESET}
"""

    parser = argparse.ArgumentParser(
        prog="mixtura",
        description=f"""
{Style.ASCII}
{Style.BOLD}Mixed together. Running everywhere.{Style.RESET}
""",
        epilog=main_epilog,
        formatter_class=ColoredHelpFormatter
    )

    sub = parser.add_subparsers(dest="command", required=True, title="available commands")

    # ADD
    p_add = sub.add_parser(
        "add", 
        help="Installs packages from Nix or Flatpak",
        description=f"Installs packages. Use {Style.BOLD}flatpak#{Style.RESET} prefix for Flatpak packages.",
        formatter_class=ColoredHelpFormatter
    )
    p_add.add_argument(
        "packages", 
        nargs="+", 
        help="Package names. E.g. 'git', 'nixpkgs#vim', 'flatpak#Spotify'"
    )
    p_add.set_defaults(func=cmd_add)

    # UPGRADE
    p_upgrade = sub.add_parser(
        "upgrade", 
        help="Upgrades installed packages", 
        description="Upgrades all installed packages or specific ones.",
        formatter_class=ColoredHelpFormatter
    )
    p_upgrade.add_argument(
        "packages", 
        nargs="*", 
        help="Specific packages to upgrade, or 'nixpkgs'/'flatpak' to upgrade all of that type. Empty = upgrade all."
    )
    p_upgrade.set_defaults(func=cmd_upgrade)

    # REMOVE
    p_remove = sub.add_parser(
        "remove", 
        help="Removes packages",
        description="Removes installed packages from Nix or Flatpak.", 
        formatter_class=ColoredHelpFormatter
    )
    p_remove.add_argument(
        "packages", 
        nargs="+", 
        help="Package names to remove. E.g. 'git', 'flatpak#Spotify'"
    )
    p_remove.set_defaults(func=cmd_remove)

    # LIST
    p_list = sub.add_parser(
        "list", 
        help="Lists installed packages", 
        formatter_class=ColoredHelpFormatter
    )
    p_list.add_argument(
        "type", 
        nargs="?", 
        choices=["nixpkgs", "flatpak"], 
        help="Optional: filter list by 'nixpkgs' or 'flatpak'"
    )
    p_list.set_defaults(func=cmd_list)

    # SEARCH
    p_search = sub.add_parser(
        "search", 
        help="Searches for packages",
        description="Searches in Nixpkgs and/or Flathub.", 
        formatter_class=ColoredHelpFormatter
    )
    p_search.add_argument(
        "query", 
        nargs="+", 
        help="Search terms. Use 'flatpak#term' to search Flathub. Default is Nixpkgs."
    )
    p_search.set_defaults(func=cmd_search)

    # Register Module Subcommands
    for mgr in available_managers:
        if mgr.is_available():
            # Check if manager has custom commands by inspecting a temporary parser
            temp_parser = argparse.ArgumentParser(add_help=False)
            mgr.setup_parser(temp_parser)
            
            # If actions were added (list is not empty), register the subcommand
            if len(temp_parser._actions) > 0:
                 p_mgr = sub.add_parser(
                    mgr.name,
                    help=f"Manage {mgr.name} specific operations",
                    formatter_class=ColoredHelpFormatter
                 )
                 mgr.setup_parser(p_mgr)
                 p_mgr.set_defaults(func=mgr.execute)

    try:
        args = parser.parse_args()
        print(Style.ASCII)
        args.func(args)
    except KeyboardInterrupt:
        print()
        sys.exit(0)

if __name__ == "__main__":
    main()
