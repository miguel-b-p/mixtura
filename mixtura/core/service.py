
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Tuple, Dict

from mixtura.core.package import Package, PackageSpec, OperationResult
from mixtura.core.providers import get_all_providers, get_available_providers, get_provider
from mixtura.core.providers.base import PackageManager


class PackageService:
    """
    Pure business logic layer for package management.
    Handles orchestration of providers without UI coupling.
    """
    
    def __init__(self) -> None:
        self._providers = get_all_providers()

    def get_provider(self, name: str) -> Optional[PackageManager]:
        return get_provider(name)

    def search(self, query: str) -> List[Package]:
        """
        Search for packages across all available providers.

        Args:
            query: The search query string.

        Returns:
            List[Package]: A list of found packages.
        """
        available = get_available_providers()
        results: List[Package] = []
        
        # Parallel search
        with ThreadPoolExecutor(max_workers=max(1, len(available))) as executor:
            futures = {
                executor.submit(mgr.search, query): mgr 
                for mgr in available.values()
            }
            
            for future in as_completed(futures):
                try:
                    # Providers should return List[Package]
                    # We accept that failures return empty list
                    results.extend(future.result())
                except Exception:
                    # Log internally if we had a logger, or ignore
                    # Preventing thread crash from affecting main process
                    pass
                    
        return results

    def resolve_package(self, spec: PackageSpec) -> List[Package]:
        """
        Resolve a PackageSpec to concrete found Packages.
        If provider is specified, search there. If not, search all.

        Args:
            spec: The package specification to resolve.

        Returns:
            List[Package]: A list of matching packages.
        """
        if spec.provider:
            mgr = get_provider(spec.provider)
            if not mgr or not mgr.is_available():
                return [] # Or raise error?
            
            # Since providers don't have "get_exact", we rely on search.
            # Ideally providers should have 'get' but search is close enough for now.
            try:
                results = mgr.search(spec.name)
                # Filter for exact match if possible?
                # The Orchestrator had smart filter logic. We should reproduce it here or in CLI?
                # Service should probably return all matches and let CLI decide?
                # But 'resolve' generally implies finding the specific thing.
                
                # Let's simple filter for name match
                exact = [p for p in results if p.name == spec.name]
                return exact if exact else results
            except Exception:
                return []
        
        # Search all
        results = self.search(spec.name)
        exact = [p for p in results if p.name == spec.name]
        return exact if exact else results

    def install(self, specs: List[PackageSpec]) -> List[OperationResult]:
        """
        Install packages based on specifications.
        Assumes specs are fully resolved (provider is set) or tries best effort.

        Args:
            specs: List of package specifications to install.

        Returns:
            List[OperationResult]: Results of the installation operations.
        """
        # Group by provider
        by_provider: Dict[str, List[str]] = {}
        results: List[OperationResult] = []
        
        for spec in specs:
            if not spec.provider:
                results.append(OperationResult(
                    provider="unknown", 
                    success=False, 
                    message=f"Cannot install '{spec.name}': Provider not specified."
                ))
                continue
                
            by_provider.setdefault(spec.provider, []).append(spec.name)
            
        # Execute in parallel
        with ThreadPoolExecutor(max_workers=max(1, len(by_provider))) as executor:
            futures = {}
            for prov_name, pkg_names in by_provider.items():
                mgr = get_provider(prov_name)
                if not mgr or not mgr.is_available():
                    msg = f"Provider '{prov_name}' not available"
                    results.append(OperationResult(prov_name, False, msg))
                    continue
                    
                futures[executor.submit(mgr.install, pkg_names)] = (prov_name, pkg_names)
                
            for future in as_completed(futures):
                prov_name, pkg_names = futures[future]
                try:
                    future.result()
                    results.append(OperationResult(
                        prov_name, 
                        True, 
                        f"Successfully installed: {', '.join(pkg_names)}"
                    ))
                except Exception as e:
                    results.append(OperationResult(
                        prov_name, 
                        False, 
                        f"Failed to install: {str(e)}"
                    ))
                    
        return results

    def remove(self, specs: List[PackageSpec]) -> List[OperationResult]:
        """
        Remove packages.

        Args:
            specs: List of package specifications to remove.

        Returns:
            List[OperationResult]: Results of the removal operations.
        """
        by_provider: Dict[str, List[str]] = {}
        results: List[OperationResult] = []
        
        for spec in specs:
            if not spec.provider:
                # Try to find which provider has it installed?
                # Or require provider? Orchestrator searched installed packages.
                # Here we assume caller (CLI) has resolved it.
                results.append(OperationResult(
                    "unknown", False, f"Provider missing for removal of {spec.name}"
                ))
                continue
            by_provider.setdefault(spec.provider, []).append(spec.name)
            
        with ThreadPoolExecutor(max_workers=max(1, len(by_provider))) as executor:
            futures = {}
            for prov_name, pkg_names in by_provider.items():
                mgr = get_provider(prov_name)
                if not mgr or not mgr.is_available():
                    results.append(OperationResult(prov_name, False, "Provider unavailable"))
                    continue
                futures[executor.submit(mgr.uninstall, pkg_names)] = prov_name
                
            for future in as_completed(futures):
                prov_name = futures[future]
                try:
                    future.result()
                    results.append(OperationResult(prov_name, True, "Removal successful"))
                except Exception as e:
                    results.append(OperationResult(prov_name, False, str(e)))
                    
        return results

    def upgrade(self, specs: Optional[List[PackageSpec]] = None) -> List[OperationResult]:
        """
        Upgrade packages. If specs is None, upgrade all providers.

        Args:
            specs: Optional list of packages/providers to upgrade. If None, upgrades all.

        Returns:
            List[OperationResult]: Results of the upgrade operations.
        """
        results: List[OperationResult] = []
        tasks: List[Tuple[PackageManager, Optional[List[str]]]] = []

        if not specs:
            # Upgrade all
            for mgr in get_available_providers().values():
                tasks.append((mgr, None))
        else:
            # Group by provider
            by_provider: Dict[str, List[str]] = {}
            for spec in specs:
                if spec.provider and spec.provider != "unknown":
                    by_provider.setdefault(spec.provider, []).append(spec.name)
                elif spec.name in get_available_providers():
                    # Spec name IS the provider name (e.g. "mixtura upgrade nixpkgs")
                    target_mgr = get_provider(spec.name)
                    if target_mgr:
                        tasks.append((target_mgr, None))
            
            for prov, names in by_provider.items():
                p_mgr = get_provider(prov)
                if p_mgr and p_mgr.is_available():
                    tasks.append((p_mgr, names))
                    
        # Execute
        with ThreadPoolExecutor() as executor:
            futures = {}
            for mgr, pkg_names in tasks:
                futures[executor.submit(mgr.upgrade, pkg_names)] = mgr
                
            for future in as_completed(futures):
                mgr = futures[future]
                try:
                    future.result()
                    msg = "Upgrade successful" if not pkg_names else f"Upgraded {len(pkg_names)} packages"
                    results.append(OperationResult(mgr.name, True, msg))
                except Exception as e:
                    results.append(OperationResult(mgr.name, False, str(e)))

        return results
