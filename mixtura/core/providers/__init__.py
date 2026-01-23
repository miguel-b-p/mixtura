"""
Package providers for Mixtura.

Explicit loading of all available package manager providers.
"""

from typing import Dict, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from mixtura.core.providers.base import PackageManager

# Lazy loading to avoid import errors if a provider has issues
_providers_cache: Dict[str, "PackageManager"] = {}
_loaded = False


def _load_providers() -> None:
    """Load all providers explicitly."""
    global _loaded
    
    if _loaded:
        return
    
    # Import providers explicitly - no magic discovery
    try:
        from mixtura.core.providers.nixpkgs.provider import NixProvider
        _providers_cache["nixpkgs"] = NixProvider()
    except ImportError:
        pass
    
    try:
        from mixtura.core.providers.flatpak.provider import FlatpakProvider
        _providers_cache["flatpak"] = FlatpakProvider()
    except ImportError:
        pass
    
    try:
        from mixtura.core.providers.homebrew.provider import HomebrewProvider
        _providers_cache["homebrew"] = HomebrewProvider()
    except ImportError:
        pass
    
    _loaded = True


def get_all_providers() -> Dict[str, "PackageManager"]:
    """
    Get all registered package manager providers.
    
    Returns:
        Dictionary mapping provider names to their instances
    """
    _load_providers()
    return _providers_cache.copy()


def get_provider(name: str) -> Optional["PackageManager"]:
    """
    Get a specific provider by name.
    
    Args:
        name: Provider name (e.g., 'nixpkgs', 'flatpak')
    
    Returns:
        PackageManager instance or None if not found
    """
    _load_providers()
    return _providers_cache.get(name)


def get_available_providers() -> Dict[str, "PackageManager"]:
    """
    Get all providers that are currently available (installed on system).
    
    Returns:
        Dictionary of available providers
    """
    _load_providers()
    return {name: prov for name, prov in _providers_cache.items() if prov.is_available()}


def get_default_provider_name() -> str:
    """Get the default provider name (usually 'nixpkgs')."""
    _load_providers()
    if "nixpkgs" in _providers_cache:
        return "nixpkgs"
    if _providers_cache:
        return next(iter(_providers_cache))
    return "nixpkgs"  # Fallback
