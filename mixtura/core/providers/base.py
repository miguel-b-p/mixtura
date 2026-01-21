"""
Abstract base class for package managers.

Defines the interface that all package providers must implement.
This is the Model layer - no UI/print logic should be here.
"""

from abc import ABC, abstractmethod
from functools import wraps
from typing import List, Optional, Dict, Any, Tuple

from mixtura.utils import run as utils_run, run_capture as utils_run_capture


def require_availability(func):
    """
    Decorator that ensures the package manager is available before executing.
    
    Use this on methods that should fail if the package manager is not installed.
    Methods like `list_packages` and `search` that return empty lists when unavailable
    should NOT use this decorator.
    
    Raises:
        RuntimeError: If the package manager is not available
    """
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self.is_available():
            raise RuntimeError(f"{self.name} is not installed.")
        return func(self, *args, **kwargs)
    return wrapper


class PackageManager(ABC):
    """
    Abstract base class for all package manager modules.
    
    All methods should return data or raise exceptions.
    Provides helper methods for command execution with consistent behavior.
    """
    
    # Default settings for command execution
    _show_commands: bool = True  # Whether to show command output visually
    
    def run_command(
        self,
        cmd: List[str],
        silent: bool = False,
        check_warnings: bool = False,
        show_output: bool = True,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        timeout: Optional[int] = None
    ) -> None:
        """
        Execute a command with visual feedback.
        
        This is a convenience wrapper around utils.run() that respects
        the provider's display settings.
        
        Args:
            cmd: Command and arguments as a list
            silent: If True, don't print the command being run
            check_warnings: If True, capture output and check for warning patterns
            show_output: If True, show stdout/stderr
            cwd: Working directory for the command
            env: Environment variables
            timeout: Timeout in seconds
        
        Raises:
            CommandError: If the command fails
        """
        # Use provider's display setting, but can be overridden by silent
        effective_silent = silent if silent else not self._show_commands
        
        utils_run(
            cmd=cmd,
            silent=effective_silent,
            check_warnings=check_warnings,
            show_output=show_output,
            cwd=cwd,
            env=env,
            timeout=timeout
        )
    
    def run_capture(
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
        timeout: Optional[int] = None,
        check: bool = False
    ) -> Tuple[int, str, str]:
        """
        Execute a command and capture its output.
        
        This is for commands where you need to parse the output
        (e.g., listing packages, searching).
        
        Args:
            cmd: Command and arguments as a list
            cwd: Working directory for the command
            env: Environment variables
            timeout: Timeout in seconds
            check: If True, raise CommandError on non-zero exit code
        
        Returns:
            Tuple of (return_code, stdout, stderr)
        
        Raises:
            CommandError: If check=True and command fails
        """
        return utils_run_capture(
            cmd=cmd,
            cwd=cwd,
            env=env,
            timeout=timeout,
            check=check
        )
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the package manager (e.g. 'nixpkgs', 'flatpak')."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the package manager is installed and usable on the system."""
        pass

    @abstractmethod
    def install(self, packages: List[str]) -> None:
        """
        Install the specified packages.
        
        Raises:
            CommandError: If installation fails
        """
        pass

    @abstractmethod
    def uninstall(self, packages: List[str]) -> None:
        """
        Uninstall the specified packages.
        
        Raises:
            CommandError: If uninstallation fails
        """
        pass

    @abstractmethod
    def upgrade(self, packages: Optional[List[str]] = None) -> None:
        """
        Upgrade specified packages, or all if packages is None or empty.
        
        Raises:
            CommandError: If upgrade fails
        """
        pass

    @abstractmethod
    def list_packages(self) -> List[Dict[str, Any]]:
        """
        Return a list of installed packages.
        Each package should be a dict with at least 'name' and 'version'/'id' keys.
        """
        pass

    @abstractmethod
    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for packages matching the query and return results.
        Returns a list of dicts, each containing at least 'name', 'version', 'description'.
        """
        pass

    @abstractmethod
    def clean(self) -> None:
        """
        Clean up unused packages and cached data.
        This performs garbage collection specific to each package manager.
        
        Raises:
            CommandError: If cleanup fails
        """
        pass
