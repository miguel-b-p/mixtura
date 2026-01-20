"""
Upgrade controller for Mixtura.

Handles package upgrade commands.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional

from mixtura.controllers.base import BaseController
from mixtura.models.base import PackageManager
from mixtura.views import log_task, log_info, log_warn, log_success, log_error
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
        log_task("Upgrading all available providers in parallel...")
        
        available_managers = self.manager.get_available_managers()
        
        if not available_managers:
            log_warn("No package managers available.")
            return
        
        for mgr in available_managers:
            log_info(f"Will upgrade: {mgr.name}")
        print()
        
        results = self._run_upgrades_parallel([(mgr, None) for mgr in available_managers])
        self._report_results(results, len(available_managers))
    
    def _upgrade_specific(self, packages: List[str]) -> None:
        """Upgrade specific providers or packages."""
        packages_map: Dict[str, List[str]] = {}
        providers_full = []
        
        for arg in packages:
            # Check if arg is a provider name
            if self.manager.get_manager(arg):
                providers_full.append(arg)
                continue
                
            if '#' in arg:
                prov, pkg = arg.split('#', 1)
                if prov not in packages_map:
                    packages_map[prov] = []
                packages_map[prov].append(pkg)
            else:
                prov = 'nixpkgs'
                if prov not in packages_map:
                    packages_map[prov] = []
                packages_map[prov].append(arg)

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
        log_task(f"Upgrading {len(tasks)} provider(s) in parallel...")
        
        results = self._run_upgrades_parallel(tasks)
        self._report_results(results, len(tasks))
    
    def _run_upgrades_parallel(
        self, 
        tasks: List[Tuple[PackageManager, Optional[List[str]]]]
    ) -> List[Tuple[str, bool, str]]:
        """
        Run upgrade tasks in parallel.
        
        Args:
            tasks: List of (manager, packages) tuples
            
        Returns:
            List of (provider_name, success, message) tuples
        """
        def _upgrade_provider(mgr: PackageManager, packages: Optional[List[str]]) -> Tuple[str, bool, str]:
            try:
                mgr.upgrade(packages)
                if packages:
                    return (mgr.name, True, f"Upgraded {len(packages)} packages via {mgr.name}")
                else:
                    return (mgr.name, True, f"Upgraded all packages in {mgr.name}")
            except CommandError as e:
                return (mgr.name, False, f"Failed to upgrade {mgr.name}: {e}")
            except Exception as e:
                return (mgr.name, False, f"Failed to upgrade {mgr.name}: {e}")
        
        results = []
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = {executor.submit(_upgrade_provider, mgr, pkgs): mgr.name for mgr, pkgs in tasks}
            for future in as_completed(futures):
                results.append(future.result())
        
        return results
    
    def _report_results(self, results: List[Tuple[str, bool, str]], total: int) -> None:
        """Report upgrade results using View."""
        print()
        success_count = 0
        for provider_name, success, message in results:
            if success:
                log_success(message)
                success_count += 1
            else:
                log_error(message)
        
        if success_count == total:
            log_success("Upgrade complete.")
        else:
            log_warn(f"Upgrade completed with {total - success_count} error(s).")


# Module-level function for argparse compatibility
_controller = None

def cmd_upgrade(args: argparse.Namespace) -> None:
    """Command function for argparse integration."""
    global _controller
    if _controller is None:
        _controller = UpgradeController()
    _controller.execute(args)
