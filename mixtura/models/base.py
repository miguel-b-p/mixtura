"""
Abstract base class for package managers.

Defines the interface that all package providers must implement.
This is the Model layer - no UI/print logic should be here.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class PackageManager(ABC):
    """
    Abstract base class for all package manager modules.
    
    All methods should return data or raise exceptions.
    No print() or logging calls should be made here - that's the View's job.
    """
    
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
