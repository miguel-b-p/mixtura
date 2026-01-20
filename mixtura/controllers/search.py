"""
Search controller for Mixtura.

Handles package search commands.
"""

import argparse

from mixtura.controllers.base import BaseController
from mixtura.views import log_task, log_warn, display_package_list


class SearchController(BaseController):
    """
    Controller for the 'search' command.
    
    Handles searching for packages across providers.
    """
    
    def execute(self, args: argparse.Namespace) -> None:
        """
        Execute the search command.
        
        Args:
            args: Parsed command arguments with 'query' and 'all' attributes
        """
        for q in args.query:
            if '#' in q:
                # Provider specific search
                prov, term = q.split('#', 1)
                mgr = self.get_manager(prov)
                
                if not mgr:
                    log_warn(f"Package manager '{prov}' is not available or not found.")
                    continue
                    
                if not mgr.is_available():
                    log_warn(f"Package manager '{prov}' is not available.")
                    continue
                
                results = mgr.search(term)
                
                # Apply smart filtering
                show_all = getattr(args, 'all', False)
                results = self.filter_results_smart(results, term, show_all)
                
                if results:
                    display_package_list(results, f"Found {len(results)} matches for '{term}' in {prov}")
                else:
                    log_warn(f"No results for '{term}' in {prov}")
            else:
                # Search all providers
                log_task(f"Searching for '{q}'...")
                results = self.manager.search_all(q)
                
                # Apply smart filtering
                show_all = getattr(args, 'all', False)
                results = self.filter_results_smart(results, q, show_all)
                
                if results:
                    display_package_list(results, f"Found {len(results)} matches for '{q}'")
                else:
                    log_warn(f"No results for '{q}'")


# Module-level function for argparse compatibility
_controller = None

def cmd_search(args: argparse.Namespace) -> None:
    """Command function for argparse integration."""
    global _controller
    if _controller is None:
        _controller = SearchController()
    _controller.execute(args)
