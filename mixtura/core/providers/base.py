"""
Abstract base class for package managers.

Defines the interface that all package providers must implement.
This is the Model layer - no UI/print logic should be here.
"""

from abc import ABC, abstractmethod
from functools import wraps
from typing import List, Optional, Any, TYPE_CHECKING, TypeVar, Callable, ParamSpec, cast

if TYPE_CHECKING:
    from mixtura.core.package import Package

P = ParamSpec("P")
R = TypeVar("R")

def require_availability(func: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator that ensures the package manager is available before executing.
    
    Use this on methods that should fail if the package manager is not installed.
    Methods like `list_packages` and `search` that return empty lists when unavailable
    should NOT use this decorator.
    
    Args:
        func: The function to decorate.

    Returns:
        Callable: The wrapped function.

    Raises:
        RuntimeError: If the package manager is not available.
    """
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        self = cast(Any, args[0])
        if not self.is_available():
            raise RuntimeError(f"{self.name} is not installed.")
        return func(*args, **kwargs)
    return wrapper


class PackageManager(ABC):
    """
    Abstract base class for all package manager modules.
    
    All methods should return data or raise exceptions.
    
    Attributes:
        name (str): The name of the package manager.
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
        
        Args:
            packages: List of package names or specs to install.

        Raises:
            CommandError: If installation fails.
        """
        pass

    @abstractmethod
    def uninstall(self, packages: List[str]) -> None:
        """
        Uninstall the specified packages.
        
        Args:
            packages: List of package names or specs to uninstall.

        Raises:
            CommandError: If uninstallation fails.
        """
        pass

    @abstractmethod
    def upgrade(self, packages: Optional[List[str]] = None) -> None:
        """
        Upgrade specified packages, or all if packages is None or empty.
        
        Args:
            packages: Optional list of packages to upgrade. If None, upgrade all.

        Raises:
            CommandError: If upgrade fails.
        """
        pass

    @abstractmethod
    def list_packages(self) -> List["Package"]:
        """
        Return a list of installed packages.

        Returns:
            List[Package]: A list of installed packages.
        """
        pass

    @abstractmethod
    def search(self, query: str) -> List["Package"]:
        """
        Search for packages matching the query and return results.

        Args:
            query: The search string.

        Returns:
            List[Package]: A list of matching packages.
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
