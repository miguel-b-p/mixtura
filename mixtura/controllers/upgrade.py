"""
Upgrade controller for Mixtura.

Handles package upgrade commands.
"""

import argparse
from typing import Dict, List, Tuple, Optional

from mixtura.controllers.base import BaseController
from mixtura.models.base import PackageManager
from mixtura.views import log_task, log_info, log_warn
from mixtura.utils import CommandError


class UpgradeController(BaseController):
    """
    Controller for the 'upgrade' command.
    
    Handles upgrading packages for one or more providers.
    """
    
    def execute(self, args: argparse.Namespace) -> None:
        """
        Execute the upgrade command.
        
        Args:
            args: Parsed command arguments with 'packages' attribute
        """
        # Upgrade ALL if no packages specified
        if not args.packages:
            self._upgrade_all()
            return
        
        # Upgrade specific providers or packages
        self._upgrade_specific(args.packages)
    
    def _upgrade_all(self) -> None:
        """Upgrade all packages from all available providers."""
        available_managers = self.manager.get_available_managers()
        
        if not available_managers:
            log_warn("No package managers available.")
            return
        
        for mgr in available_managers:
            log_info(f"Will upgrade: {mgr.name}")
        print()
        
        tasks = [(mgr, None) for mgr in available_managers]
        results = self.run_parallel_tasks(tasks, self._upgrade_provider, "Upgrading all providers")
        self.report_parallel_results(results, "Upgrade complete.", "Upgrade completed with errors.")
    
    def _upgrade_specific(self, packages: List[str]) -> None:
        """Upgrade specific providers or packages."""
        packages_map: Dict[str, List[str]] = {}
        providers_full = []
        
        for arg in packages:
            # Check if arg is a provider name (upgrade entire provider)
            if self.manager.get_manager(arg):
                providers_full.append(arg)
                continue
            
            # Parse provider#package or use default provider
            prov, items = self.manager.parse_single_arg(arg)
            if prov not in packages_map:
                packages_map[prov] = []
            packages_map[prov].extend(items)

        if not packages_map and not providers_full:
            log_warn("No packages or providers specified for upgrade.")
            return

        # Prepare tasks
        tasks: List[Tuple[PackageManager, Optional[List[str]]]] = []
        
        for prov in providers_full:
            mgr = self.get_manager(prov)
            if mgr and mgr.is_available():
                log_info(f"Will upgrade all in: {prov}")
                tasks.append((mgr, None))
            else:
                log_warn(f"Package manager '{prov}' is not available or not found.")

        for prov, pkgs in packages_map.items():
            mgr = self.get_manager(prov)
            if mgr and mgr.is_available():
                log_info(f"Will upgrade in {prov}: {', '.join(pkgs)}")
                tasks.append((mgr, pkgs))
            else:
                log_warn(f"Package manager '{prov}' is not available or not found.")
        
        if not tasks:
            log_warn("No valid providers found for upgrade.")
            return
        
        print()
        results = self.run_parallel_tasks(tasks, self._upgrade_provider, "Upgrading providers")
        self.report_parallel_results(results, "Upgrade complete.", "Upgrade completed with errors.")
    
    @staticmethod
    def _upgrade_provider(mgr: PackageManager, packages: Optional[List[str]]) -> Tuple[str, bool, str]:
        """Worker function for upgrading a single provider."""
        try:
            mgr.upgrade(packages)
            if packages:
                return (mgr.name, True, f"Upgraded {len(packages)} package(s) via {mgr.name}")
            else:
                return (mgr.name, True, f"Upgraded all packages in {mgr.name}")
        except CommandError as e:
            return (mgr.name, False, f"Failed to upgrade {mgr.name}: {e}")
        except Exception as e:
            return (mgr.name, False, f"Failed to upgrade {mgr.name}: {e}")


# Module-level function for argparse compatibility
_controller = None

def cmd_upgrade(args: argparse.Namespace) -> None:
    """Command function for argparse integration."""
    global _controller
    if _controller is None:
        _controller = UpgradeController()
    _controller.execute(args)
