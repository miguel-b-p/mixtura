"""
Base controller for Mixtura.

Provides common functionality for all controllers.
"""

import argparse
import fnmatch
import re
from typing import Dict, List, Any, Union

from mixtura.models.manager import ModuleManager
from mixtura.models.base import PackageManager
from mixtura.models.package import Package


class BaseController:
    """
    Base class for all controllers.
    
    Provides common methods for accessing the model layer.
    Controllers should NOT contain print() statements - use View layer.
    """
    
    def __init__(self):
        self.manager = ModuleManager.get_instance()
    
    def get_manager_or_raise(self, name: str) -> PackageManager:
        """
        Get a package manager by name.
        
        Args:
            name: The provider name
            
        Returns:
            The PackageManager instance
            
        Raises:
            ValueError: If provider is not found
        """
        mgr = self.manager.get_manager(name)
        if not mgr:
            raise ValueError(f"Provider '{name}' not found")
        return mgr
    
    def get_manager(self, name: str) -> PackageManager:
        """
        Get a package manager by name, or None if not found.
        
        Args:
            name: The provider name
            
        Returns:
            The PackageManager instance or None
        """
        return self.manager.get_manager(name)
    
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
        
        Works with both Package objects and legacy dicts.
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

    def execute(self, args: argparse.Namespace) -> None:
        """
        Execute the controller action.
        
        Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement execute()")
