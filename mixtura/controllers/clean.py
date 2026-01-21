"""
Clean controller for Mixtura.

Handles cleanup and garbage collection commands.
"""

import argparse
from typing import List

from mixtura.models.base import PackageManager
from mixtura.controllers.base import BaseController
from mixtura.views import log_task, log_info, log_warn, log_success, log_error
from mixtura.utils import CommandError


class CleanController(BaseController):
    """
    Controller for the 'clean' command.
    
    Handles garbage collection for one or more providers.
    """
    
    def _clean_manager(self, mgr: PackageManager, errors: List[str]) -> None:
        """
        Clean a specific manager and collect errors.
        
        Args:
            mgr: The package manager to clean
            errors: List to append error messages to
        """
        log_task(f"Cleaning {mgr.name}...")
        try:
            mgr.clean()
        except CommandError as e:
            errors.append(f"{mgr.name}: {e}")
        except Exception as e:
            errors.append(f"{mgr.name}: {e}")

    def _report_results(self, errors: List[str]) -> None:
        """
        Report the results of the clean operation.
        
        Args:
            errors: List of error messages collected during clean
        """
        if errors:
            for err in errors:
                log_error(err)
            log_warn(f"Clean completed with {len(errors)} error(s).")
        else:
            log_success("Clean complete.")

    def execute(self, args: argparse.Namespace) -> None:
        """
        Execute the clean command.
        
        Args:
            args: Parsed command arguments with 'modules' attribute
        """
        modules = getattr(args, 'modules', [])
        errors = []
        
        if not modules:
            # Clean all available providers
            log_task("Cleaning all available providers...")
            for mgr in self.manager.get_all_managers():
                if mgr.is_available():
                    self._clean_manager(mgr, errors)
            
            self._report_results(errors)
            return
        
        # Clean specific providers
        for mod_name in modules:
            mgr = self.get_manager(mod_name)
            if not mgr:
                log_warn(f"Package manager '{mod_name}' is not available or not found.")
                continue
                
            if not mgr.is_available():
                log_error(f"Provider '{mgr.name}' is not available.")
                continue
                
            self._clean_manager(mgr, errors)
        
        self._report_results(errors)


# Module-level function for argparse compatibility
_controller = None

def cmd_clean(args: argparse.Namespace) -> None:
    """Command function for argparse integration."""
    global _controller
    if _controller is None:
        _controller = CleanController()
    _controller.execute(args)
