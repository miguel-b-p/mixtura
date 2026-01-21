"""
Orchestrator for Mixtura - Service Layer.

Centralizes all business logic for package management operations.
This replaces the old controllers/* pattern with a cleaner flow:
CLI (Typer) -> Orchestrator (this) -> Providers
"""

import fnmatch
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple, Union, Any, Callable

from mixtura.core.package import Package
from mixtura.core.providers import (
    get_all_providers,
    get_provider,
    get_available_providers,
    get_default_provider_name,
)
from mixtura.core.providers.base import PackageManager
from mixtura.ui import log_task, log_info, log_warn, log_success, log_error, console
from mixtura.ui.display import display_package_list, display_installed_packages, display_operation_results
from mixtura.ui.prompts import select_package
from mixtura.utils import CommandError


class Orchestrator:
    """
    Service layer that orchestrates all package management operations.
    
    Handles the flow: parse input -> search/resolve -> confirm -> execute
    """
    
    def __init__(self):
        self.providers = get_all_providers()
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def parse_single_arg(self, arg: str) -> Tuple[str, List[str]]:
        """
        Parse a single argument with optional provider prefix.
        
        Args:
            arg: String like 'package', 'provider#package', or 'provider#pkg1,pkg2'
            
        Returns:
            Tuple of (provider_name, list_of_packages)
        """
        if '#' in arg:
            provider, pkg_str = arg.split('#', 1)
            items = [p.strip() for p in pkg_str.split(',') if p.strip()]
            return (provider, items)
        else:
            items = [p.strip() for p in arg.split(',') if p.strip()]
            return (get_default_provider_name(), items)
    
    def filter_results_smart(
        self,
        results: List[Union[Package, Dict[str, Any]]], 
        pattern: str, 
        show_all: bool
    ) -> List[Union[Package, Dict[str, Any]]]:
        """
        Filter search results based on the pattern.
        
        - If show_all is True: returns all results
        - If pattern contains wildcards (* or ?): uses glob pattern matching
        - Otherwise: prioritizes exact name match, falls back to all results
        """
        if show_all or not results:
            return results
        
        def get_name(r: Union[Package, dict]) -> str:
            if hasattr(r, 'name'):
                return r.name
            return r.get('name', '')
        
        # Check if pattern has wildcards
        if '*' in pattern or '?' in pattern:
            regex_pattern = fnmatch.translate(pattern)
            regex = re.compile(regex_pattern, re.IGNORECASE)
            filtered = [r for r in results if regex.match(get_name(r))]
            return filtered if filtered else results
        
        # Exact match first
        exact = [r for r in results if get_name(r).lower() == pattern.lower()]
        if exact:
            return exact
        
        # No exact match found - return all results
        return results
    
    def search_all(self, query: str) -> List[Package]:
        """
        Search for query in all available package managers in parallel.
        """
        available = get_available_providers()
        
        if not available:
            return []
        
        def _search_provider(mgr: PackageManager) -> List[Package]:
            try:
                return mgr.search(query) or []
            except Exception:
                return []
        
        all_results = []
        with ThreadPoolExecutor(max_workers=len(available)) as executor:
            futures = {executor.submit(_search_provider, mgr): mgr.name for mgr in available.values()}
            for future in as_completed(futures):
                results = future.result()
                if results:
                    all_results.extend(results)
        
        return all_results
    
    def run_parallel_tasks(
        self,
        tasks: List[Tuple],
        worker_func: Callable[..., Tuple[str, bool, str]],
        description: str = "Running tasks"
    ) -> List[Tuple[str, bool, str]]:
        """
        Execute tasks in parallel using ThreadPoolExecutor.
        
        Args:
            tasks: List of argument tuples to pass to worker_func
            worker_func: Function that takes *task args and returns (name, success, message)
            description: Description for logging
            
        Returns:
            List of (name, success, message) tuples
        """
        if not tasks:
            return []
        
        log_task(f"{description} ({len(tasks)} task(s) in parallel)...")
        
        results = []
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = {executor.submit(worker_func, *task): task for task in tasks}
            for future in as_completed(futures):
                results.append(future.result())
        
        return results
    
    # =========================================================================
    # Command Flows
    # =========================================================================
    
    def install_flow(
        self, 
        packages: List[str], 
        auto_confirm: bool = False, 
        show_all: bool = False
    ) -> None:
        """
        Install packages flow.
        
        Handles: parsing provider#pkg, searching ambiguous packages, confirmation, installation.
        """
        packages_to_install: Dict[str, List[str]] = {}
        
        for arg in packages:
            if '#' in arg:
                # Explicit provider
                provider, items = self.parse_single_arg(arg)
                if provider not in packages_to_install:
                    packages_to_install[provider] = []
                packages_to_install[provider].extend(items)
            else:
                # Ambiguous package - Search Mode
                items = [p.strip() for p in arg.split(',') if p.strip()]
                
                for item in items:
                    log_task(f"Searching for '[bold]{item}[/bold]' across all providers...")
                    results = self.search_all(item)
                    
                    if not results:
                        log_warn(f"No packages found for '{item}'.")
                        continue
                    
                    # Apply smart filtering
                    results = self.filter_results_smart(results, item, show_all)
                    
                    # Auto-select if --yes and only one result
                    if auto_confirm and len(results) == 1:
                        selected_list = results
                        log_info(f"Auto-selecting the only match for '{item}'")
                    else:
                        display_package_list(results, f"Found {len(results)} matches for '{item}'")
                        selected_list = select_package(results, "Select a package to add")
                        
                        if selected_list is None:
                            continue
                        elif not selected_list:
                            console.print("Skipping...")
                            continue
                    
                    selected = selected_list[0]
                    prov = selected.provider if hasattr(selected, 'provider') else selected.get('provider', 'unknown')
                    pkg_id = selected.id if hasattr(selected, 'id') else (selected.get('id') or selected.get('name'))
                    pkg_name = selected.name if hasattr(selected, 'name') else selected.get('name', 'unknown')
                    
                    if prov not in packages_to_install:
                        packages_to_install[prov] = []
                    packages_to_install[prov].append(pkg_id)
                    log_info(f"Selected {pkg_name} from {prov}")
        
        if not packages_to_install:
            log_warn("No packages selected for installation.")
            return
        
        console.print()
        self._do_install(packages_to_install)
    
    def _do_install(self, packages_to_install: Dict[str, List[str]]) -> None:
        """Execute installation for resolved packages."""
        def _install_provider(provider_name: str, pkgs: List[str]) -> Tuple[str, bool, str]:
            mgr = get_provider(provider_name)
            if not mgr:
                return (provider_name, False, f"Provider '{provider_name}' unknown.")
            if not mgr.is_available():
                return (provider_name, False, f"Provider '{mgr.name}' is not available.")
            try:
                mgr.install(pkgs)
                return (provider_name, True, f"Installed {len(pkgs)} package(s) via {mgr.name}")
            except CommandError as e:
                return (provider_name, False, f"Failed to install via {mgr.name}: {e}")
            except Exception as e:
                return (provider_name, False, f"Failed to install via {mgr.name}: {e}")
        
        # Log what we're about to do
        for prov, pkgs in packages_to_install.items():
            log_info(f"{prov}: {', '.join(pkgs)}")
        console.print()
        
        tasks = [(prov, pkgs) for prov, pkgs in packages_to_install.items()]
        results = self.run_parallel_tasks(tasks, _install_provider, "Installing packages")
        display_operation_results(results, "Installation process finished.", "Installation completed with errors.")
    
    def remove_flow(
        self, 
        packages: List[str], 
        auto_confirm: bool = False, 
        show_all: bool = False
    ) -> None:
        """
        Remove packages flow.
        
        Handles: searching installed packages, confirmation, removal.
        """
        packages_to_remove: Dict[str, List[str]] = {}
        
        for arg in packages:
            if '#' in arg:
                # Explicit provider
                provider, items = self.parse_single_arg(arg)
                if provider not in packages_to_remove:
                    packages_to_remove[provider] = []
                packages_to_remove[provider].extend(items)
            else:
                # Ambiguous package - Search installed
                items = [p.strip() for p in arg.split(',') if p.strip()]
                
                for item in items:
                    log_task(f"Searching for installed package '[bold]{item}[/bold]'...")
                    
                    matches: List[Package] = []
                    for mgr in get_available_providers().values():
                        try:
                            installed = mgr.list_packages()
                            for pkg in installed:
                                p_name = pkg.name if hasattr(pkg, 'name') else pkg.get('name', '')
                                if item.lower() in p_name.lower():
                                    if hasattr(pkg, 'provider'):
                                        matches.append(pkg)
                                    else:
                                        pkg['provider'] = mgr.name
                                        matches.append(Package.from_dict(pkg))
                        except Exception as e:
                            log_warn(f"Failed to list packages from {mgr.name}: {e}")
                    
                    if not matches:
                        log_warn(f"No installed packages found matching '{item}'.")
                        continue
                    
                    # Filter out already selected
                    filtered_matches = []
                    for m in matches:
                        prov = m.provider
                        pid = m.id or m.name
                        if pid not in packages_to_remove.get(prov, []):
                            filtered_matches.append(m)
                    
                    if not filtered_matches:
                        if matches:
                            log_info(f"Matches for '{item}' are already selected for removal.")
                        continue
                    
                    matches = filtered_matches
                    matches = self.filter_results_smart(matches, item, show_all)
                    
                    if auto_confirm and len(matches) == 1:
                        selected_list = matches
                        log_info(f"Auto-selecting the only match for '{item}'")
                    else:
                        display_package_list(matches, f"Found {len(matches)} installed matches for '{item}'")
                        selected_list = select_package(matches, "Select a package to remove", allow_all=True)
                        
                        if selected_list is None:
                            continue
                        elif not selected_list:
                            console.print("Skipping...")
                            continue
                    
                    for selected in selected_list:
                        prov = selected.provider
                        pkg_id = selected.id or selected.name
                        pkg_name = selected.name
                        
                        if prov not in packages_to_remove:
                            packages_to_remove[prov] = []
                        packages_to_remove[prov].append(pkg_id)
                        log_info(f"Selected {pkg_name} from {prov} for removal")
        
        if not packages_to_remove:
            log_warn("No packages selected for removal.")
            return
        
        # Execute removal
        errors = []
        for provider_name, pkgs in packages_to_remove.items():
            mgr = get_provider(provider_name)
            if not mgr:
                log_warn(f"Package manager '{provider_name}' is not available or not found.")
                continue
            
            log_task(f"Removing {len(pkgs)} packages via {mgr.name}...")
            try:
                mgr.uninstall(pkgs)
            except CommandError as e:
                errors.append(f"{mgr.name}: {e}")
        
        if errors:
            for err in errors:
                log_error(err)
            log_warn(f"Removal completed with {len(errors)} error(s).")
        else:
            log_success("Removal process finished.")
    
    def upgrade_flow(self, packages: Optional[List[str]] = None) -> None:
        """
        Upgrade packages flow.
        
        If packages is empty, upgrade all. Otherwise upgrade specific providers/packages.
        """
        if not packages:
            self._upgrade_all()
        else:
            self._upgrade_specific(packages)
    
    def _upgrade_all(self) -> None:
        """Upgrade all packages from all available providers."""
        available = get_available_providers()
        
        if not available:
            log_warn("No package managers available.")
            return
        
        for mgr in available.values():
            log_info(f"Will upgrade: {mgr.name}")
        console.print()
        
        tasks = [(mgr, None) for mgr in available.values()]
        results = self.run_parallel_tasks(tasks, self._upgrade_provider, "Upgrading all providers")
        display_operation_results(results, "Upgrade complete.", "Upgrade completed with errors.")
    
    def _upgrade_specific(self, packages: List[str]) -> None:
        """Upgrade specific providers or packages."""
        packages_map: Dict[str, List[str]] = {}
        providers_full = []
        
        for arg in packages:
            # Check if arg is a provider name
            if get_provider(arg):
                providers_full.append(arg)
                continue
            
            prov, items = self.parse_single_arg(arg)
            if prov not in packages_map:
                packages_map[prov] = []
            packages_map[prov].extend(items)
        
        if not packages_map and not providers_full:
            log_warn("No packages or providers specified for upgrade.")
            return
        
        tasks: List[Tuple[PackageManager, Optional[List[str]]]] = []
        
        for prov in providers_full:
            mgr = get_provider(prov)
            if mgr and mgr.is_available():
                log_info(f"Will upgrade all in: {prov}")
                tasks.append((mgr, None))
            else:
                log_warn(f"Package manager '{prov}' is not available or not found.")
        
        for prov, pkgs in packages_map.items():
            mgr = get_provider(prov)
            if mgr and mgr.is_available():
                log_info(f"Will upgrade in {prov}: {', '.join(pkgs)}")
                tasks.append((mgr, pkgs))
            else:
                log_warn(f"Package manager '{prov}' is not available or not found.")
        
        if not tasks:
            log_warn("No valid providers found for upgrade.")
            return
        
        console.print()
        results = self.run_parallel_tasks(tasks, self._upgrade_provider, "Upgrading providers")
        display_operation_results(results, "Upgrade complete.", "Upgrade completed with errors.")
    
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
    
    def list_flow(self, provider_type: Optional[str] = None) -> None:
        """
        List installed packages flow.
        """
        managers_to_list = []
        
        if provider_type:
            mgr = get_provider(provider_type)
            if mgr:
                managers_to_list.append(mgr)
            else:
                log_warn(f"Unknown provider '{provider_type}'")
                return
        else:
            managers_to_list = list(get_all_providers().values())
        
        if not managers_to_list:
            log_warn("No package managers found.")
            return
        
        first = True
        for mgr in managers_to_list:
            if not mgr.is_available():
                continue
            
            if not first:
                console.print()
            first = False
            
            log_task(f"Fetching packages from {mgr.name}...")
            pkgs = mgr.list_packages()
            display_installed_packages(pkgs, mgr.name)
    
    def search_flow(self, queries: List[str], show_all: bool = False) -> None:
        """
        Search for packages flow.
        """
        for q in queries:
            if '#' in q:
                # Provider-specific search
                prov, term = q.split('#', 1)
                mgr = get_provider(prov)
                
                if not mgr:
                    log_warn(f"Package manager '{prov}' is not available or not found.")
                    continue
                
                if not mgr.is_available():
                    log_warn(f"Package manager '{prov}' is not available.")
                    continue
                
                results = mgr.search(term)
                results = self.filter_results_smart(results, term, show_all)
                
                if results:
                    display_package_list(results, f"Found {len(results)} matches for '{term}' in {prov}")
                else:
                    log_warn(f"No results for '{term}' in {prov}")
            else:
                # Search all providers
                log_task(f"Searching for '{q}'...")
                results = self.search_all(q)
                results = self.filter_results_smart(results, q, show_all)
                
                if results:
                    display_package_list(results, f"Found {len(results)} matches for '{q}'")
                else:
                    log_warn(f"No results for '{q}'")
    
    def clean_flow(self, modules: Optional[List[str]] = None) -> None:
        """
        Clean/garbage collection flow.
        """
        @staticmethod
        def _clean_provider(mgr: PackageManager) -> Tuple[str, bool, str]:
            try:
                mgr.clean()
                return (mgr.name, True, f"Cleaned {mgr.name}")
            except CommandError as e:
                return (mgr.name, False, f"Failed to clean {mgr.name}: {e}")
            except Exception as e:
                return (mgr.name, False, f"Failed to clean {mgr.name}: {e}")
        
        if not modules:
            # Clean all
            available = get_available_providers()
            if not available:
                log_warn("No package managers available.")
                return
            
            for mgr in available.values():
                log_info(f"Will clean: {mgr.name}")
            console.print()
            
            tasks = [(mgr,) for mgr in available.values()]
            results = self.run_parallel_tasks(tasks, _clean_provider, "Cleaning all providers")
            display_operation_results(results, "Clean complete.", "Clean completed with errors.")
            return
        
        # Clean specific
        managers_to_clean = []
        for mod_name in modules:
            mgr = get_provider(mod_name)
            if not mgr:
                log_warn(f"Package manager '{mod_name}' is not available or not found.")
                continue
            
            if not mgr.is_available():
                log_warn(f"Provider '{mgr.name}' is not available.")
                continue
            
            log_info(f"Will clean: {mgr.name}")
            managers_to_clean.append(mgr)
        
        if not managers_to_clean:
            log_warn("No valid providers to clean.")
            return
        
        console.print()
        tasks = [(mgr,) for mgr in managers_to_clean]
        results = self.run_parallel_tasks(tasks, _clean_provider, "Cleaning providers")
        display_operation_results(results, "Clean complete.", "Clean completed with errors.")
