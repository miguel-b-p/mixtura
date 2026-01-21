"""
Remove controller for Mixtura.

Handles package removal commands.
"""

import argparse
from typing import Dict, List, Union

from mixtura.controllers.base import BaseController
from mixtura.models.package import Package
from mixtura.views import (
    log_task, log_info, log_warn, log_success, log_error,
    display_package_list, select_package, Style
)
from mixtura.utils import CommandError


class RemoveController(BaseController):
    """
    Controller for the 'remove' command.
    
    Handles searching installed packages and removing them.
    """
    
    def execute(self, args: argparse.Namespace) -> None:
        """
        Execute the remove command.
        
        Args:
            args: Parsed command arguments with 'packages' and 'all' attributes
        """
        packages_to_remove: Dict[str, List[str]] = {}

        for arg in args.packages:
            if '#' in arg:
                # Explicit provider - use centralized parsing
                provider, items = self.manager.parse_single_arg(arg)
                
                if provider not in packages_to_remove:
                    packages_to_remove[provider] = []
                packages_to_remove[provider].extend(items)
            else:
                # Ambiguous package - Search Installed Mode
                items = [p.strip() for p in arg.split(',') if p.strip()]
                
                for item in items:
                    log_task(f"Searching for installed package '{Style.BOLD}{item}{Style.RESET}'...")
                    
                    matches: List[Union[Package, dict]] = []
                    for mgr in self.manager.get_all_managers():
                        if not mgr.is_available():
                            continue
                        
                        try:
                            installed = mgr.list_packages()
                            for pkg in installed:
                                p_name = pkg.name if hasattr(pkg, 'name') else pkg.get('name', '')
                                if item.lower() in p_name.lower():
                                    if hasattr(pkg, 'provider'):
                                        matches.append(pkg)
                                    else:
                                        pkg['provider'] = mgr.name
                                        matches.append(pkg)
                        except Exception as e:
                            log_warn(f"Failed to list packages from {mgr.name}: {e}")

                    if not matches:
                        log_warn(f"No installed packages found matching '{item}'.")
                        continue
                    
                    # Filter out packages already selected for removal
                    filtered_matches = []
                    for m in matches:
                        prov = m.provider if hasattr(m, 'provider') else m.get('provider', '')
                        pid = (m.id if hasattr(m, 'id') else m.get('id')) or \
                              (m.name if hasattr(m, 'name') else m.get('name'))
                        if pid not in packages_to_remove.get(prov, []):
                            filtered_matches.append(m)
                    
                    if not filtered_matches:
                        if len(matches) > 0:
                            log_info(f"Matches for '{item}' are already selected for removal. Skipping prompt.")
                        continue
                    
                    matches = filtered_matches
                    
                    # Apply smart filtering
                    show_all = getattr(args, 'all', False)
                    matches = self.filter_results_smart(matches, item, show_all)
                    
                    # Auto-select if --yes is set and only one high-confidence result
                    auto_yes = getattr(args, 'yes', False)
                    if auto_yes and len(matches) == 1:
                        selected_list = matches
                        log_info(f"Auto-selecting the only match for '{item}'")
                    else:
                        # Display using View
                        display_package_list(matches, f"Found {len(matches)} installed matches for '{item}'")
                        
                        # Get selection (allow selecting all)
                        selected_list = select_package(matches, "Select a package to remove", allow_all=True)
                        
                        if selected_list is None:
                            continue
                        elif not selected_list:
                            print("Skipping...")
                            continue
                    
                    for selected in selected_list:
                        prov = selected.provider if hasattr(selected, 'provider') else selected.get('provider', 'unknown')
                        pkg_id = (selected.id if hasattr(selected, 'id') else selected.get('id')) or \
                                 (selected.name if hasattr(selected, 'name') else selected.get('name'))
                        pkg_name = selected.name if hasattr(selected, 'name') else selected.get('name', 'unknown')
                        
                        if prov not in packages_to_remove:
                            packages_to_remove[prov] = []
                        packages_to_remove[prov].append(pkg_id)
                        log_info(f"Selected {pkg_name} from {prov} for removal")

        if not packages_to_remove:
            log_warn("No packages selected for removal.")
            return

        # Execute removal
        errors = []
        for provider_name, packages in packages_to_remove.items():
            mgr = self.get_manager(provider_name)
            if not mgr:
                log_warn(f"Package manager '{provider_name}' is not available or not found.")
                continue
                
            log_task(f"Removing {len(packages)} packages via {mgr.name}...")
            try:
                mgr.uninstall(packages)
            except CommandError as e:
                errors.append(f"{mgr.name}: {e}")

        if errors:
            for err in errors:
                log_error(err)
            log_warn(f"Removal completed with {len(errors)} error(s).")
        else:
            log_success("Removal process finished.")


# Module-level function for argparse compatibility
_controller = None

def cmd_remove(args: argparse.Namespace) -> None:
    """Command function for argparse integration."""
    global _controller
    if _controller is None:
        _controller = RemoveController()
    _controller.execute(args)
