"""
List controller for Mixtura.

Handles listing installed packages.
"""

import argparse

from mixtura.controllers.base import BaseController
from mixtura.views import log_task, log_warn, display_installed_packages


class ListController(BaseController):
    """
    Controller for the 'list' command.
    
    Handles listing installed packages from one or more providers.
    """
    
    def execute(self, args: argparse.Namespace) -> None:
        """
        Execute the list command.
        
        Args:
            args: Parsed command arguments with 'type' attribute
        """
        target = args.type
        managers_to_list = []
        
        if target:
            m = self.manager.get_manager(target)
            if m: 
                managers_to_list.append(m)
            else:
                log_warn(f"Unknown provider '{target}'")
                return
        else:
            managers_to_list = self.manager.get_all_managers()

        if not managers_to_list:
            log_warn("No package managers found.")
            return

        first = True
        for mgr in managers_to_list:
            if not mgr.is_available():
                continue

            if not first:
                print()
            first = False
                
            log_task(f"Fetching packages from {mgr.name}...")
            pkgs = mgr.list_packages()
            
            display_installed_packages(pkgs, mgr.name)


# Module-level function for argparse compatibility
_controller = None

def cmd_list(args: argparse.Namespace) -> None:
    """Command function for argparse integration."""
    global _controller
    if _controller is None:
        _controller = ListController()
    _controller.execute(args)
