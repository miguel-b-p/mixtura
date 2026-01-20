"""
Mixtura Views Layer.

Contains all UI presentation logic: styling, logging, display, and prompts.
This layer handles all user-facing output and input.
"""

from mixtura.views.style import Style
from mixtura.views.logger import log_info, log_task, log_success, log_warn, log_error
from mixtura.views.display import (
    display_package_list,
    display_installed_packages,
    display_operation_results,
    print_results_summary,
)
from mixtura.views.prompts import select_package, confirm_action

__all__ = [
    # Style
    "Style",
    # Logger
    "log_info",
    "log_task", 
    "log_success",
    "log_warn",
    "log_error",
    # Display
    "display_package_list",
    "display_installed_packages",
    "display_operation_results",
    "print_results_summary",
    # Prompts
    "select_package",
    "confirm_action",
]
