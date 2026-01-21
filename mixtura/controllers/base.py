"""
Base controller for Mixtura.

Provides common functionality for all controllers.
"""

import argparse
import fnmatch
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Union, Tuple, Callable

from mixtura.models.manager import ModuleManager
from mixtura.models.base import PackageManager
from mixtura.models.package import Package
from mixtura.views import log_task, log_success, log_error, log_warn


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
            description: Description for logging (e.g. "Installing packages")
            
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
    
    def report_parallel_results(
        self, 
        results: List[Tuple[str, bool, str]], 
        success_message: str = "Operation complete.",
        partial_message: str = "Operation completed with errors."
    ) -> None:
        """
        Report results from run_parallel_tasks.
        
        Args:
            results: List of (name, success, message) tuples from run_parallel_tasks
            success_message: Message to show if all tasks succeeded
            partial_message: Message to show if some tasks failed
        """
        print()
        success_count = 0
        for name, success, message in results:
            if success:
                log_success(message)
                success_count += 1
            else:
                log_error(message)
        
        if success_count == len(results):
            log_success(success_message)
        else:
            log_warn(f"{partial_message} ({len(results) - success_count} error(s))")

    def execute(self, args: argparse.Namespace) -> None:
        """
        Execute the controller action.
        
        Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement execute()")
