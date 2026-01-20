import os
import importlib.util
import sys
import glob
from typing import Dict, List, Type, Any

from mixtura.core import PackageManager
from mixtura.utils import log_warn, log_info

class ModuleManager:
    _instance = None
    
    def __init__(self):
        self.managers: Dict[str, PackageManager] = {}
        self.discover_modules()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def discover_modules(self):
        """
        Dynamically discovers and loads modules from src/modules/*
        Uses pkgutil to ensure compatibility with Nuitka/frozen builds and pure Python.
        """
        from mixtura import modules
        import pkgutil
        
        # Iterate over all packages in the modules directory
        # This yields names like 'modules.flatpak', 'modules.nixpkgs' if prefix is set,
        # or just 'flatpak', 'nixpkgs' if not.
        for importer, modname, ispkg in pkgutil.iter_modules(modules.__path__, modules.__name__ + "."):
            if ispkg:
                # We interpret each subpackage as a manager/provider container
                # We expect a 'provider' submodule inside it: e.g. modules.flatpak.provider
                provider_module_name = f"{modname}.provider"
                self._load_module(provider_module_name)

    def _load_module(self, module_name: str):
        try:
            # Try to import the module by name
            # This works for both filesystem and frozen (Nuitka) modules
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
            # It's okay if a subpackage doesn't have a provider.py (though expected in this structure)
            pass
        except Exception as e:
            log_warn(f"Failed to load module {module_name}: {e}")

    def get_manager(self, name: str) -> PackageManager:
        return self.managers.get(name)

    def get_all_managers(self) -> List[PackageManager]:
        return list(self.managers.values())
        
    def resolve_packages(self, args: List[str]) -> Dict[str, List[str]]:
        """
        Groups packages by their provider based on prefixes.
        e.g. ['git', 'flatpak#spotify'] -> {'nixpkgs': ['git'], 'flatpak': ['spotify']}
        
        Assumes 'nixpkgs' is the default if no prefix is given (can be configured later).
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
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        available_managers = [m for m in self.get_all_managers() if m.is_available()]
        
        if not available_managers:
            return []
        
        def _search_provider(mgr: PackageManager) -> List[Dict[str, Any]]:
            try:
                return mgr.search(query) or []
            except Exception as e:
                log_warn(f"Search failed in {mgr.name}: {e}")
                return []
        
        all_results = []
        with ThreadPoolExecutor(max_workers=len(available_managers)) as executor:
            futures = {executor.submit(_search_provider, mgr): mgr.name for mgr in available_managers}
            for future in as_completed(futures):
                results = future.result()
                if results:
                    all_results.extend(results)
        
        return all_results
