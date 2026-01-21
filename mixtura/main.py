"""
Mixtura - Mixed together. Running everywhere.

A unified package manager CLI that supports Nix, Flatpak, and Homebrew.
"""

import argparse
import difflib
import sys

from mixtura.views import Style
from mixtura.controllers.add import cmd_add
from mixtura.controllers.remove import cmd_remove
from mixtura.controllers.upgrade import cmd_upgrade
from mixtura.controllers.list import cmd_list
from mixtura.controllers.search import cmd_search
from mixtura.controllers.clean import cmd_clean
from mixtura.models.manager import ModuleManager
from mixtura.update import check_for_updates


class ColoredHelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Custom formatter with colored output."""
    
    def start_section(self, heading):
        if heading:
            heading = f"{Style.BOLD}{Style.MAIN}{heading.title()}{Style.RESET}"
        super().start_section(heading)

    def _format_usage(self, usage, actions, groups, prefix):
        if prefix is None:
            prefix = 'usage: '
        prefix = f"{Style.BOLD}{Style.SUCCESS}{prefix}{Style.RESET}"
        return super()._format_usage(usage, actions, groups, prefix)


class SuggestingArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that suggests similar commands and arguments on typos."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._valid_commands = []
    
    def set_valid_commands(self, commands: list):
        """Set the list of valid subcommands for suggestions."""
        self._valid_commands = commands
    
    def _get_all_options(self) -> list:
        """Get all valid option strings from this parser and all subparsers."""
        options = []
        # Get options from main parser
        for action in self._actions:
            options.extend(action.option_strings)
            # Check if this action is a subparsers action
            if isinstance(action, argparse._SubParsersAction):
                # Get options from each subparser
                for subparser in action.choices.values():
                    for sub_action in subparser._actions:
                        options.extend(sub_action.option_strings)
        return list(set(options))  # Remove duplicates
    
    def error(self, message):
        """Override error to add 'Did you mean?' suggestions."""
        import re
        
        # Check if it's an unrecognized arguments error (for options like --hep)
        unrecognized_match = re.search(r"unrecognized arguments?: (.+)", message)
        if unrecognized_match:
            invalid_arg = unrecognized_match.group(1).split()[0]  # Get first unrecognized arg
            if invalid_arg.startswith('-'):
                valid_options = self._get_all_options()
                suggestions = difflib.get_close_matches(
                    invalid_arg, 
                    valid_options, 
                    n=1, 
                    cutoff=0.5
                )
                if suggestions:
                    self.print_usage(sys.stderr)
                    print(
                        f"{Style.ERROR}error:{Style.RESET} Unrecognized argument '{Style.BOLD}{invalid_arg}{Style.RESET}'. "
                        f"Did you mean '{Style.SUCCESS}{suggestions[0]}{Style.RESET}'?",
                        file=sys.stderr
                    )
                    sys.exit(2)
        
        # Check if it's an invalid choice error for the command
        if "invalid choice:" in message and self._valid_commands:
            match = re.search(r"invalid choice: ['\"]?([^'\"\s]+)['\"]?", message)
            if match:
                invalid_cmd = match.group(1)
                # Find similar commands using difflib
                suggestions = difflib.get_close_matches(
                    invalid_cmd, 
                    self._valid_commands, 
                    n=1, 
                    cutoff=0.5
                )
                if suggestions:
                    self.print_usage(sys.stderr)
                    print(
                        f"{Style.ERROR}error:{Style.RESET} Command '{Style.BOLD}{invalid_cmd}{Style.RESET}' not found. "
                        f"Did you mean '{Style.SUCCESS}{suggestions[0]}{Style.RESET}'?",
                        file=sys.stderr
                    )
                    sys.exit(2)
        
        # Fall back to default error handling
        super().error(message)


def main() -> None:
    """Main entry point for Mixtura CLI."""
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
{Style.BOLD}{Style.MAIN}Available Managers:{Style.RESET}
{mgr_help_str}

{Style.BOLD}EXAMPLES:{Style.RESET}
  {Style.SUCCESS}#{Style.RESET} Install packages from Nix (default)
  {Style.DIM}$ mixtura add micro git{Style.RESET}

  {Style.SUCCESS}#{Style.RESET} Install packages from Flatpak
  {Style.DIM}$ mixtura add flatpak#Spotify,"OBS Studio"{Style.RESET}

  {Style.SUCCESS}#{Style.RESET} Install mixed packages
  {Style.DIM}$ mixtura add nixpkgs#vim flatpak#equibop{Style.RESET}

  {Style.SUCCESS}#{Style.RESET} Search for packages
  {Style.DIM}$ mixtura search "web browser" flatpak#spotify{Style.RESET}

  {Style.SUCCESS}#{Style.RESET} Upgrade all packages
  {Style.DIM}$ mixtura upgrade{Style.RESET}
"""

    parser = SuggestingArgumentParser(
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
    p_add.add_argument(
        "--all", "-a",
        action="store_true",
        dest="all",
        help="Show all search results instead of filtering by exact match"
    )
    p_add.add_argument(
        "--yes", "-y",
        action="store_true",
        dest="yes",
        help="Auto-select if only one high-confidence result (e.g. exact name match)"
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
    p_remove.add_argument(
        "--all", "-a",
        action="store_true",
        dest="all",
        help="Show all search results instead of filtering by exact match"
    )
    p_remove.add_argument(
        "--yes", "-y",
        action="store_true",
        dest="yes",
        help="Auto-select if only one high-confidence result (e.g. exact name match)"
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
        choices=["nixpkgs", "flatpak", "homebrew"], 
        help="Optional: filter list by provider"
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
    p_search.add_argument(
        "--all", "-a",
        action="store_true",
        dest="all",
        help="Show all search results instead of filtering by exact match"
    )
    p_search.set_defaults(func=cmd_search)

    # CLEAN
    p_clean = sub.add_parser(
        "clean", 
        help="Clean up unused packages and cached data",
        description="Performs garbage collection on package managers to free up disk space.", 
        formatter_class=ColoredHelpFormatter
    )
    p_clean.add_argument(
        "modules", 
        nargs="*", 
        help="Specific modules to clean (e.g. 'nixpkgs', 'flatpak'). Empty = clean all."
    )
    p_clean.set_defaults(func=cmd_clean)

    # Dynamically set valid commands for "Did you mean?" suggestions
    # This includes all registered subcommands automatically
    parser.set_valid_commands(list(sub.choices.keys()))

    try:
        args = parser.parse_args()
        print(Style.ASCII)
        args.func(args)
    except KeyboardInterrupt:
        print()
        sys.exit(0)


if __name__ == "__main__":
    main()
