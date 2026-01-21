"""
Add controller for Mixtura.

Handles package installation commands.
"""

import argparse
from typing import Dict, List, Tuple

from mixtura.controllers.base import BaseController
from mixtura.views import (
    log_task, log_info, log_warn,
    display_package_list, select_package, Style
)
from mixtura.utils import CommandError


class AddController(BaseController):
    """
    Controller for the 'add' command.
    
    Handles searching for packages and installing them.
    """
    
    def execute(self, args: argparse.Namespace) -> None:
        """
        Execute the add command.
        
        Args:
            args: Parsed command arguments with 'packages' and 'all' attributes
        """
        packages_to_install: Dict[str, List[str]] = {}
        
        for arg in args.packages:
            if '#' in arg:
                # Explicit provider - use centralized parsing
                provider, items = self.manager.parse_single_arg(arg)
                
                if provider not in packages_to_install:
                    packages_to_install[provider] = []
                packages_to_install[provider].extend(items)
            else:
                # Ambiguous package - Search Mode (split by comma)
                items = [p.strip() for p in arg.split(',') if p.strip()]
                
                for item in items:
                    log_task(f"Searching for '{Style.BOLD}{item}{Style.RESET}' across all providers...")
                    results = self.manager.search_all(item)
                    
                    if not results:
                        log_warn(f"No packages found for '{item}'.")
                        continue
                    
                    # Apply smart filtering
                    show_all = getattr(args, 'all', False)
                    results = self.filter_results_smart(results, item, show_all)
                    
                    # Auto-select if --yes is set and only one high-confidence result
                    auto_yes = getattr(args, 'yes', False)
                    if auto_yes and len(results) == 1:
                        selected_list = results
                        log_info(f"Auto-selecting the only match for '{item}'")
                    else:
                        # Display results using View
                        display_package_list(results, f"Found {len(results)} matches for '{item}'")
                        
                        # Get selection using View
                        selected_list = select_package(results, "Select a package to add")
                        
                        if selected_list is None:
                            continue
                        elif not selected_list:
                            print("Skipping...")
                            continue
                    
                    selected = selected_list[0]
                    prov = selected.provider if hasattr(selected, 'provider') else selected.get('provider', 'unknown')
                    pkg_id = selected.id if hasattr(selected, 'id') else (selected.get('id') or selected.get('name'))
                    pkg_name = selected.name if hasattr(selected, 'name') else selected.get('name', 'unknown')
                    
                    if prov not in packages_to_install:
                        packages_to_install[prov] = []
                    
                    packages_to_install[prov].append(pkg_id)
                    log_info(f"Selected {pkg_name} from {prov}")

        # Proceed with installation
        if not packages_to_install:
            log_warn("No packages selected for installation.")
            return

        print()
        self._install_parallel(packages_to_install)
    
    def _install_parallel(self, packages_to_install: Dict[str, List[str]]) -> None:
        """
        Install packages from multiple providers in parallel.
        
        Args:
            packages_to_install: Dict mapping provider names to package lists
        """
        def _install_provider(provider_name: str, packages: List[str]) -> Tuple[str, bool, str]:
            """Install packages for a single provider."""
            mgr = self.get_manager(provider_name)
            if not mgr:
                return (provider_name, False, f"Provider '{provider_name}' unknown.")
            if not mgr.is_available():
                return (provider_name, False, f"Provider '{mgr.name}' is not available.")
            try:
                mgr.install(packages)
                return (provider_name, True, f"Installed {len(packages)} package(s) via {mgr.name}")
            except CommandError as e:
                return (provider_name, False, f"Failed to install via {mgr.name}: {e}")
            except Exception as e:
                return (provider_name, False, f"Failed to install via {mgr.name}: {e}")
        
        # Log what we're about to do
        for prov, pkgs in packages_to_install.items():
            log_info(f"{prov}: {', '.join(pkgs)}")
        print()
        
        # Build task list and execute
        tasks = [(prov, pkgs) for prov, pkgs in packages_to_install.items()]
        results = self.run_parallel_tasks(tasks, _install_provider, "Installing packages")
        
        self.report_parallel_results(
            results,
            success_message="Installation process finished.",
            partial_message="Installation completed with errors."
        )


# Module-level function for argparse compatibility
_controller = None

def cmd_add(args: argparse.Namespace) -> None:
    """Command function for argparse integration."""
    global _controller
    if _controller is None:
        _controller = AddController()
    _controller.execute(args)
