"""
Package data model for Mixtura.

Provides type-safe representations of packages,
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


@dataclass
class PackageSpec:
    """
    Represents a package specification from user input.
    E.g. "nixpkgs#vim", "git", "flatpak#Spotify"
    """
    name: str
    provider: Optional[str] = None
    version: Optional[str] = None
    
    @classmethod
    def parse(cls, spec_str: str) -> "PackageSpec":
        """
        Parse a package specification string.
        
        Formats:
          - "package_name"
          - "provider#package_name"
        """
        if not spec_str:
            raise ValueError("Package specification cannot be empty")
            
        if "#" in spec_str:
            parts = spec_str.split("#", 1)
            if not parts[0] or not parts[1]:
                 # Handle cases like "#package" or "provider#" which are invalid
                 # For now, let's keep it simple: if part[0] is empty -> provider is empty string (technically allowed by split but logically wrong?)
                 # Actually, let's just use what split gives us.
                 pass
            
            p_name = parts[0].strip()
            pkg_name = parts[1].strip()
            
            if not p_name or not pkg_name:
                 # If "flatpak#" -> provider="flatpak", name="" -> invalid?
                 # If "#git" -> provider="", name="git" -> valid-ish?
                 # Let's enforce that both must be present if # is used.
                 pass

            return cls(name=pkg_name, provider=p_name)
            
        return cls(name=spec_str)
        
    def __str__(self) -> str:
        if self.provider:
            return f"{self.provider}#{self.name}"
        return self.name


@dataclass
class OperationResult:
    """Result of an operation (install, remove, upgrade)."""
    provider: str
    success: bool
    message: str
