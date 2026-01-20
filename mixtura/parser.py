"""
Argument parsing utilities for Mixtura.

Centralizes the logic for parsing user input like "git,vim" or "flatpak#spotify"
into structured PackageRequest objects.
"""

from typing import NamedTuple, List, Dict


class PackageRequest(NamedTuple):
    """
    Represents a user's request for a package.
    
    Attributes:
        provider: The package manager to use (e.g., 'nixpkgs', 'flatpak')
        package_name: The name/query for the package
    """
    provider: str
    package_name: str


def parse_user_input(
    inputs: List[str],
    default_provider: str = 'nixpkgs'
) -> List[PackageRequest]:
    """
    Parse user input into a list of PackageRequest objects.
    
    Supports multiple formats:
    - "git" -> [PackageRequest('nixpkgs', 'git')]
    - "git,vim" -> [PackageRequest('nixpkgs', 'git'), PackageRequest('nixpkgs', 'vim')]
    - "flatpak#spotify" -> [PackageRequest('flatpak', 'spotify')]
    - "nixpkgs#vim,git flatpak#discord" -> multiple requests
    
    Args:
        inputs: List of user-provided package arguments
        default_provider: Provider to use when none specified (default: 'nixpkgs')
    
    Returns:
        List of PackageRequest tuples
    
    Example:
        >>> parse_user_input(['git', 'flatpak#spotify'])
        [PackageRequest('nixpkgs', 'git'), PackageRequest('flatpak', 'spotify')]
    """
    requests: List[PackageRequest] = []
    
    for item in inputs:
        # Handle comma-separated values within the same argument
        sub_items = [x.strip() for x in item.split(',') if x.strip()]
        
        for sub in sub_items:
            if '#' in sub:
                # Explicit provider specified: "provider#package"
                provider, pkg = sub.split('#', 1)
                provider = provider.strip()
                pkg = pkg.strip()
                if provider and pkg:
                    requests.append(PackageRequest(provider, pkg))
            else:
                # No provider specified, use default
                requests.append(PackageRequest(default_provider, sub))
    
    return requests


def group_by_provider(
    inputs: List[str],
    default_provider: str = 'nixpkgs'
) -> Dict[str, List[str]]:
    """
    Group package names by their provider.
    
    This is useful when you need to batch operations per provider.
    
    Args:
        inputs: List of user-provided package arguments
        default_provider: Provider to use when none specified
    
    Returns:
        Dict mapping provider names to lists of package names
    
    Example:
        >>> group_by_provider(['git', 'vim', 'flatpak#spotify'])
        {'nixpkgs': ['git', 'vim'], 'flatpak': ['spotify']}
    """
    grouped: Dict[str, List[str]] = {}
    
    for req in parse_user_input(inputs, default_provider):
        if req.provider not in grouped:
            grouped[req.provider] = []
        grouped[req.provider].append(req.package_name)
    
    return grouped
