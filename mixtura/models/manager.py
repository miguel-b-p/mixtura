"""
Module Manager for Mixtura.

Discovers and manages package provider modules.
This is the Model layer - no UI/print logic should be here.
"""

import importlib
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from mixtura.models.base import PackageManager


class ModuleManager:
    """
    Manages discovery and access to package provider modules.
    
    Singleton pattern ensures consistent state across the application.
    """
    _instance = None
    
    def __init__(self):
        self.managers: Dict[str, PackageManager] = {}
        self._discovery_errors: List[str] = []
        self.discover_modules()

    @classmethod
    def get_instance(cls) -> "ModuleManager":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def discover_modules(self) -> None:
        """
        Dynamically discovers and loads modules from models/providers/*
        Uses pkgutil to ensure compatibility with Nuitka/frozen builds and pure Python.
        """
        from mixtura.models import providers
        import pkgutil
        
        # Iterate over all packages in the providers directory
        for importer, modname, ispkg in pkgutil.iter_modules(providers.__path__, providers.__name__ + "."):
            if ispkg:
                # We expect a 'provider' submodule inside it: e.g. models.providers.flatpak.provider
                provider_module_name = f"{modname}.provider"
                self._load_module(provider_module_name)

    def _load_module(self, module_name: str) -> None:
        """Load a provider module and register it."""
        if not module_name.startswith("mixtura.models.providers."):
            raise ValueError(f"Invalid module name: {module_name}. Only 'mixtura.models.providers.*' modules are allowed.")


        try:
            # Try to import the module by name
            module = importlib.import_module(module_name)
            
            # Find the PackageManager subclass
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, PackageManager) and 
                    attr is not PackageManager):
                    
                    # Instantiate
                    instance = attr()
                    self.managers[instance.name] = instance
        except ImportError:
            # It's okay if a subpackage doesn't have a provider.py
            pass
        except Exception as e:
            # Store errors for later retrieval if needed
            self._discovery_errors.append(f"Failed to load module {module_name}: {e}")

    def get_manager(self, name: str) -> PackageManager:
        """Get a specific package manager by name."""
        return self.managers.get(name)

    def get_all_managers(self) -> List[PackageManager]:
        """Get all registered package managers."""
        return list(self.managers.values())
    
    def get_available_managers(self) -> List[PackageManager]:
        """Get all available (installed) package managers."""
        return [m for m in self.managers.values() if m.is_available()]
    
    def get_discovery_errors(self) -> List[str]:
        """Get any errors that occurred during module discovery."""
        return self._discovery_errors.copy()
        
    def resolve_packages(self, args: List[str]) -> Dict[str, List[str]]:
        """
        Groups packages by their provider based on prefixes.
        e.g. ['git', 'flatpak#spotify'] -> {'nixpkgs': ['git'], 'flatpak': ['spotify']}
        
        Assumes 'nixpkgs' is the default if no prefix is given.
        """
        grouped = {}
        
        # Determine default provider - usually nixpkgs, or the first one available
        default_manager_name = 'nixpkgs'
        if default_manager_name not in self.managers and self.managers:
             default_manager_name = next(iter(self.managers))

        for arg in args:
            if '#' in arg:
                provider, pkg = arg.split('#', 1)
                # Handle comma separated values if any
                items = [p.strip() for p in pkg.split(',') if p.strip()]
                
                if provider not in grouped:
                    grouped[provider] = []
                grouped[provider].extend(items)
            else:
                # Default provider
                items = [p.strip() for p in arg.split(',') if p.strip()]
                if default_manager_name not in grouped:
                    grouped[default_manager_name] = []
                grouped[default_manager_name].extend(items)
                
        return grouped

    def search_all(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for query in all available package managers in parallel.
        Returns an aggregated list of results.
        
        Note: This is a pure data operation - no logging or printing.
        """
        available_managers = self.get_available_managers()
        
        if not available_managers:
            return []
        
        def _search_provider(mgr: PackageManager) -> List[Dict[str, Any]]:
            try:
                return mgr.search(query) or []
            except Exception:
                return []
        
        all_results = []
        with ThreadPoolExecutor(max_workers=len(available_managers)) as executor:
            futures = {executor.submit(_search_provider, mgr): mgr.name for mgr in available_managers}
            for future in as_completed(futures):
                results = future.result()
                if results:
                    all_results.extend(results)
        
        return all_results
