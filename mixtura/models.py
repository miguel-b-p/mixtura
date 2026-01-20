"""
Data models for Mixtura.

Provides type-safe representations of packages and requests,
replacing loose Dict[str, Any] usage throughout the codebase.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class Package:
    """
    Represents a package from any provider.
    
    This is the standard data structure returned by search() and list_packages()
    methods across all providers, ensuring consistent data access.
    """
    name: str
    provider: str
    id: str  # The identifier used for install/uninstall operations
    version: str = "unknown"
    description: str = ""
    installed: bool = False
    origin: Optional[str] = None  # Useful for Nix (attrPath)
    extra: Dict[str, Any] = field(default_factory=dict)  # Provider-specific data
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for backwards compatibility.
        
        This allows gradual migration - existing code expecting dicts
        can still work while we transition to the dataclass.
        """
        return {
            "name": self.name,
            "provider": self.provider,
            "id": self.id,
            "version": self.version,
            "description": self.description,
            "installed": self.installed,
            "origin": self.origin,
            **self.extra,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], provider: str = "unknown") -> "Package":
        """
        Create Package from a dictionary.
        
        This helper allows providers to gradually migrate from returning
        dicts to returning Package objects.
        """
        return cls(
            name=data.get("name", "unknown"),
            provider=data.get("provider", provider),
            id=data.get("id") or data.get("name", "unknown"),
            version=data.get("version", "unknown"),
            description=data.get("description", ""),
            installed=data.get("installed", False),
            origin=data.get("origin"),
            extra={k: v for k, v in data.items() 
                   if k not in ("name", "provider", "id", "version", "description", "installed", "origin")},
        )
    
    def __str__(self) -> str:
        return f"{self.name} ({self.provider} {self.version})"
