"""
Clean controller for Mixtura.

Handles cleanup and garbage collection commands.
"""

import argparse
from typing import List, Tuple

from mixtura.models.base import PackageManager
from mixtura.controllers.base import BaseController
from mixtura.views import log_info, log_warn
from mixtura.utils import CommandError


class CleanController(BaseController):
    """
    Controller for the 'clean' command.
    
    Handles garbage collection for one or more providers.
    """
    
    @staticmethod
    def _clean_provider(mgr: PackageManager) -> Tuple[str, bool, str]:
        """Worker function for cleaning a single provider."""
        try:
            mgr.clean()
            return (mgr.name, True, f"Cleaned {mgr.name}")
        except CommandError as e:
            return (mgr.name, False, f"Failed to clean {mgr.name}: {e}")
        except Exception as e:
            return (mgr.name, False, f"Failed to clean {mgr.name}: {e}")

    def execute(self, args: argparse.Namespace) -> None:
        """
        Execute the clean command.
        
        Args:
            args: Parsed command arguments with 'modules' attribute
        """
        modules = getattr(args, 'modules', [])
        
        if not modules:
            # Clean all available providers in parallel
            available = self.manager.get_available_managers()
            if not available:
                log_warn("No package managers available.")
                return
            
            for mgr in available:
                log_info(f"Will clean: {mgr.name}")
            print()
            
            tasks = [(mgr,) for mgr in available]
            results = self.run_parallel_tasks(tasks, self._clean_provider, "Cleaning all providers")
            self.report_parallel_results(results, "Clean complete.", "Clean completed with errors.")
            return
        
        # Clean specific providers in parallel
        managers_to_clean = []
        for mod_name in modules:
            mgr = self.get_manager(mod_name)
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
        
        print()
        tasks = [(mgr,) for mgr in managers_to_clean]
        results = self.run_parallel_tasks(tasks, self._clean_provider, "Cleaning providers")
        self.report_parallel_results(results, "Clean complete.", "Clean completed with errors.")


# Module-level function for argparse compatibility
_controller = None

def cmd_clean(args: argparse.Namespace) -> None:
    """Command function for argparse integration."""
    global _controller
    if _controller is None:
        _controller = CleanController()
    _controller.execute(args)
