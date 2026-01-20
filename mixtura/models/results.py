"""
Result types for Mixtura operations.

Provides structured return types for operations like install, upgrade, etc.
These allow controllers to receive data and pass it to views for display.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from mixtura.models.package import Package


@dataclass
class OperationResult:
    """
    Result of an operation (install/uninstall/upgrade/clean).
    
    Used to communicate operation outcomes from Model to Controller,
    which then passes it to View for display.
    """
    provider: str
    success: bool
    message: str
    packages_affected: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class SearchResults:
    """
    Aggregated search results from one or more providers.
    """
    packages: List[Package] = field(default_factory=list)
    query: str = ""
    providers_searched: List[str] = field(default_factory=list)
    
    @property
    def count(self) -> int:
        return len(self.packages)
    
    @property
    def is_empty(self) -> bool:
        return len(self.packages) == 0


@dataclass  
class ListResults:
    """
    Results from listing installed packages.
    """
    packages: List[Package] = field(default_factory=list)
    provider: str = ""
    
    @property
    def count(self) -> int:
        return len(self.packages)
