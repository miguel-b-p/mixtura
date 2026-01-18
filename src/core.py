from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import argparse

class PackageManager(ABC):
    """
    Abstract base class for all package manager modules.
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
        """Install the specified packages."""
        pass

    @abstractmethod
    def uninstall(self, packages: List[str]) -> None:
        """Uninstall the specified packages."""
        pass

    @abstractmethod
    def upgrade(self, packages: Optional[List[str]] = None) -> None:
        """
        Upgrade specified packages, or all if packages is None or empty.
        Note: Some implementations might treat empty list as 'upgrade all'.
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
    def search(self, query: str) -> None:
        """
        Search for packages matching the query and display results.
        """
        pass

    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        """
        Configure an argparse subparser for this package manager.
        Override this to add custom arguments (e.g. --gc).
        """
        pass

    def execute(self, args: argparse.Namespace) -> None:
        """
        Execute an action based on the parsed arguments.
        Override this to handle custom arguments.
        """
        pass

