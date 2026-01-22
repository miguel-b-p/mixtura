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


# =============================================================================
# Helper Functions
# =============================================================================

def _get_pkg_attr(pkg: Union[Package, dict], attr: str, default: str = '') -> str:
    """Get attribute from Package object or dict."""
    if hasattr(pkg, attr):
        return getattr(pkg, attr)
    return pkg.get(attr, default)


def _clean_provider_worker(mgr: PackageManager) -> Tuple[str, bool, str]:
    """Worker function for cleaning a single provider."""
    try:
        mgr.clean()
        return (mgr.name, True, f"Cleaned {mgr.name}")
    except CommandError as e:
        return (mgr.name, False, f"Failed to clean {mgr.name}: {e}")
    except Exception as e:
        return (mgr.name, False, f"Failed to clean {mgr.name}: {e}")


def _upgrade_provider_worker(mgr: PackageManager, packages: Optional[List[str]]) -> Tuple[str, bool, str]:
    """Worker function for upgrading a single provider."""
    try:
        mgr.upgrade(packages)
        if packages:
            return (mgr.name, True, f"Upgraded {len(packages)} package(s) via {mgr.name}")
        return (mgr.name, True, f"Upgraded all packages in {mgr.name}")
    except CommandError as e:
        return (mgr.name, False, f"Failed to upgrade {mgr.name}: {e}")
    except Exception as e:
        return (mgr.name, False, f"Failed to upgrade {mgr.name}: {e}")


def _install_provider_worker(provider_name: str, pkgs: List[str]) -> Tuple[str, bool, str]:
    """Worker function for installing packages via a provider."""
    mgr = get_provider(provider_name)
    if not mgr:
        return (provider_name, False, f"Provider '{provider_name}' unknown.")
    if not mgr.is_available():
        return (provider_name, False, f"Provider '{mgr.name}' is not available.")
    try:
        mgr.install(pkgs)
        return (provider_name, True, f"Installed {len(pkgs)} package(s) via {mgr.name}")
    except (CommandError, Exception) as e:
        return (provider_name, False, f"Failed to install via {mgr.name}: {e}")


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
        items = [p.strip() for p in arg.split(',') if p.strip()]
        return (get_default_provider_name(), items)
    
    def _parse_explicit_packages(self, packages: List[str]) -> Dict[str, List[str]]:
        """
        Parse package arguments that have explicit provider prefixes.
        
        Returns dict of provider -> list of packages (only for args with '#').
        """
        result: Dict[str, List[str]] = {}
        for arg in packages:
            if '#' in arg:
                prov, items = self.parse_single_arg(arg)
                result.setdefault(prov, []).extend(items)
        return result
    
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
        
        # Check if pattern has wildcards
        if '*' in pattern or '?' in pattern:
            regex_pattern = fnmatch.translate(pattern)
            regex = re.compile(regex_pattern, re.IGNORECASE)
            filtered = [r for r in results if regex.match(_get_pkg_attr(r, 'name'))]
            return filtered if filtered else results
        
        # Exact match first
        exact = [r for r in results if _get_pkg_attr(r, 'name').lower() == pattern.lower()]
        return exact if exact else results
    
    def search_all(self, query: str) -> List[Package]:
        """Search for query in all available package managers in parallel."""
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
    
    def _run_parallel_tasks(
        self,
        tasks: List[Tuple],
        worker_func: Callable[..., Tuple[str, bool, str]],
        description: str = "Running tasks"
    ) -> List[Tuple[str, bool, str]]:
        """Execute tasks in parallel using ThreadPoolExecutor."""
        if not tasks:
            return []
        
        log_task(f"{description} ({len(tasks)} task(s) in parallel)...")
        
        results = []
        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = {executor.submit(worker_func, *task): task for task in tasks}
            for future in as_completed(futures):
                results.append(future.result())
        
        return results
    
    def _search_installed_packages(self, pattern: str) -> List[Package]:
        """Search for installed packages matching a pattern across all providers."""
        matches: List[Package] = []
        for mgr in get_available_providers().values():
            try:
                installed = mgr.list_packages()
                for pkg in installed:
                    p_name = _get_pkg_attr(pkg, 'name')
                    if pattern.lower() in p_name.lower():
                        if hasattr(pkg, 'provider'):
                            matches.append(pkg)
                        else:
                            pkg['provider'] = mgr.name
                            matches.append(Package.from_dict(pkg))
            except Exception as e:
                log_warn(f"Failed to list packages from {mgr.name}: {e}")
        return matches
    
    def _select_packages(
        self,
        results: List[Package],
        pattern: str,
        auto_confirm: bool,
        show_all: bool,
        prompt: str,
        allow_all: bool = False
    ) -> Optional[List[Package]]:
        """
        Handle package selection UI flow.
        Returns None to skip, empty list to cancel, or selected packages.
        """
        if not results:
            log_warn(f"No packages found for '{pattern}'.")
            return None
        
        results = self.filter_results_smart(results, pattern, show_all)
        
        if auto_confirm and len(results) == 1:
            log_info(f"Auto-selecting the only match for '{pattern}'")
            return results
        
        display_package_list(results, f"Found {len(results)} matches for '{pattern}'")
        selected = select_package(results, prompt, allow_all=allow_all)
        
        if selected is None:
            return None
        if not selected:
            console.print("Skipping...")
            return None
        
        return selected
    
    # =========================================================================
    # Command Flows
    # =========================================================================
    
    def install_flow(
        self, 
        packages: List[str], 
        auto_confirm: bool = False, 
        show_all: bool = False
    ) -> None:
        """Install packages flow."""
        packages_to_install: Dict[str, List[str]] = self._parse_explicit_packages(packages)
        
        # Process ambiguous packages (no provider prefix)
        for arg in packages:
            if '#' in arg:
                continue
            
            for item in [p.strip() for p in arg.split(',') if p.strip()]:
                log_task(f"Searching for '[bold]{item}[/bold]' across all providers...")
                results = self.search_all(item)
                
                selected = self._select_packages(
                    results, item, auto_confirm, show_all, "Select a package to add"
                )
                if not selected:
                    continue
                
                pkg = selected[0]
                prov = _get_pkg_attr(pkg, 'provider', 'unknown')
                pkg_id = _get_pkg_attr(pkg, 'id') or _get_pkg_attr(pkg, 'name')
                pkg_name = _get_pkg_attr(pkg, 'name', 'unknown')
                
                packages_to_install.setdefault(prov, []).append(pkg_id)
                log_info(f"Selected {pkg_name} from {prov}")
        
        if not packages_to_install:
            log_warn("No packages selected for installation.")
            return
        
        console.print()
        self._do_install(packages_to_install)
    
    def _do_install(self, packages_to_install: Dict[str, List[str]]) -> None:
        """Execute installation for resolved packages."""
        for prov, pkgs in packages_to_install.items():
            log_info(f"{prov}: {', '.join(pkgs)}")
        console.print()
        
        tasks = [(prov, pkgs) for prov, pkgs in packages_to_install.items()]
        results = self._run_parallel_tasks(tasks, _install_provider_worker, "Installing packages")
        display_operation_results(results, "Installation process finished.", "Installation completed with errors.")
    
    def remove_flow(
        self, 
        packages: List[str], 
        auto_confirm: bool = False, 
        show_all: bool = False
    ) -> None:
        """Remove packages flow."""
        packages_to_remove: Dict[str, List[str]] = self._parse_explicit_packages(packages)
        
        # Process ambiguous packages (no provider prefix)
        for arg in packages:
            if '#' in arg:
                continue
            
            for item in [p.strip() for p in arg.split(',') if p.strip()]:
                log_task(f"Searching for installed package '[bold]{item}[/bold]'...")
                matches = self._search_installed_packages(item)
                
                # Filter out already selected
                matches = [
                    m for m in matches
                    if (m.id or m.name) not in packages_to_remove.get(m.provider, [])
                ]
                
                if not matches:
                    log_warn(f"No installed packages found matching '{item}'.")
                    continue
                
                selected = self._select_packages(
                    matches, item, auto_confirm, show_all, 
                    "Select a package to remove", allow_all=True
                )
                if not selected:
                    continue
                
                for pkg in selected:
                    pkg_id = pkg.id or pkg.name
                    packages_to_remove.setdefault(pkg.provider, []).append(pkg_id)
                    log_info(f"Selected {pkg.name} from {pkg.provider} for removal")
        
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
        """Upgrade packages flow."""
        if not packages:
            self._do_upgrade_all()
        else:
            self._do_upgrade_specific(packages)
    
    def _do_upgrade_all(self) -> None:
        """Upgrade all packages from all available providers."""
        available = get_available_providers()
        if not available:
            log_warn("No package managers available.")
            return
        
        for mgr in available.values():
            log_info(f"Will upgrade: {mgr.name}")
        console.print()
        
        tasks = [(mgr, None) for mgr in available.values()]
        results = self._run_parallel_tasks(tasks, _upgrade_provider_worker, "Upgrading all providers")
        display_operation_results(results, "Upgrade complete.", "Upgrade completed with errors.")
    
    def _do_upgrade_specific(self, packages: List[str]) -> None:
        """Upgrade specific providers or packages."""
        tasks: List[Tuple[PackageManager, Optional[List[str]]]] = []
        packages_map: Dict[str, List[str]] = {}
        
        for arg in packages:
            mgr = get_provider(arg)
            if mgr:
                # Arg is a provider name - upgrade all in that provider
                if mgr.is_available():
                    log_info(f"Will upgrade all in: {arg}")
                    tasks.append((mgr, None))
                else:
                    log_warn(f"Package manager '{arg}' is not available.")
            else:
                # Parse as provider#packages
                prov, items = self.parse_single_arg(arg)
                packages_map.setdefault(prov, []).extend(items)
        
        # Add package-specific tasks
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
        results = self._run_parallel_tasks(tasks, _upgrade_provider_worker, "Upgrading providers")
        display_operation_results(results, "Upgrade complete.", "Upgrade completed with errors.")
    
    def list_flow(self, provider_type: Optional[str] = None) -> None:
        """List installed packages flow."""
        if provider_type:
            mgr = get_provider(provider_type)
            if not mgr:
                log_warn(f"Unknown provider '{provider_type}'")
                return
            managers = [mgr]
        else:
            managers = list(get_all_providers().values())
        
        if not managers:
            log_warn("No package managers found.")
            return
        
        first = True
        for mgr in managers:
            if not mgr.is_available():
                continue
            
            if not first:
                console.print()
            first = False
            
            log_task(f"Fetching packages from {mgr.name}...")
            pkgs = mgr.list_packages()
            display_installed_packages(pkgs, mgr.name)
    
    def search_flow(self, queries: List[str], show_all: bool = False) -> None:
        """Search for packages flow."""
        for q in queries:
            if '#' in q:
                prov, term = q.split('#', 1)
                mgr = get_provider(prov)
                
                if not mgr or not mgr.is_available():
                    log_warn(f"Package manager '{prov}' is not available or not found.")
                    continue
                
                results = mgr.search(term)
                results = self.filter_results_smart(results, term, show_all)
                
                if results:
                    display_package_list(results, f"Found {len(results)} matches for '{term}' in {prov}")
                else:
                    log_warn(f"No results for '{term}' in {prov}")
            else:
                log_task(f"Searching for '{q}'...")
                results = self.search_all(q)
                results = self.filter_results_smart(results, q, show_all)
                
                if results:
                    display_package_list(results, f"Found {len(results)} matches for '{q}'")
                else:
                    log_warn(f"No results for '{q}'")
    
    def clean_flow(self, modules: Optional[List[str]] = None) -> None:
        """Clean/garbage collection flow."""
        if not modules:
            available = get_available_providers()
            if not available:
                log_warn("No package managers available.")
                return
            
            for mgr in available.values():
                log_info(f"Will clean: {mgr.name}")
            console.print()
            
            tasks = [(mgr,) for mgr in available.values()]
            results = self._run_parallel_tasks(tasks, _clean_provider_worker, "Cleaning all providers")
            display_operation_results(results, "Clean complete.", "Clean completed with errors.")
            return
        
        # Clean specific providers
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
        results = self._run_parallel_tasks(tasks, _clean_provider_worker, "Cleaning providers")
        display_operation_results(results, "Clean complete.", "Clean completed with errors.")
