"""
Nixpkgs package provider for Mixtura.

Provides integration with Nix package manager.
"""

import shutil
import json
import sys

from typing import List, Optional, Dict, Any

from mixtura.core.providers.base import PackageManager, require_availability
from mixtura.core.package import Package
from mixtura.cache import SearchCache
from mixtura.ui import log_warn
from mixtura.ui.prompts import confirm_action
from mixtura.utils import run, run_capture, CommandError


class NixProvider(PackageManager):
    @property
    def name(self) -> str:
        return "nixpkgs"

    def is_available(self) -> bool:
        return shutil.which("nix") is not None
        
    @require_availability
    def install(self, packages: List[str]) -> None:
        """
        Install packages via Nix profile.
        
        Raises:
            CommandError: If installation fails
        """
        for pkg in packages:
            target = pkg if "#" in pkg else f"nixpkgs#{pkg}"
            run(["nix", "profile", "add", "--impure", target])

    @require_availability
    def uninstall(self, packages: List[str]) -> None:
        """
        Remove packages from Nix profile.
        
        Raises:
            CommandError: If uninstall fails
        """
        for pkg in packages:
            run(["nix", "profile", "remove", pkg], check_warnings=True)

    @require_availability
    def upgrade(self, packages: Optional[List[str]] = None) -> None:
        """
        Upgrade Nix profile packages.
        
        Raises:
            CommandError: If upgrade fails
        """
        if not packages:
            # Upgrade all
            self._upgrade_with_lock_retry(["nix", "profile", "upgrade", "--impure", "--all"])
        else:
            # Upgrade specific
            for pkg in packages:
                self._upgrade_with_lock_retry(
                    ["nix", "profile", "upgrade", "--impure", pkg],
                    check_warnings=True
                )

    def _upgrade_with_lock_retry(
        self,
        cmd: List[str],
        check_warnings: bool = False
    ) -> None:
        """
        Execute upgrade command with lock file error detection and retry.
        
        If the command fails with "cannot write modified lock file" error,
        ask the user if they want to retry with --no-write-lock-file flag.
        """

        
        # First, try running with output capture to detect lock file error
        returncode, stdout, stderr = run_capture(cmd)
        
        if returncode == 0:
            # Success on first try
            if stdout:
                print(stdout, end='')
            return
        
        # Check if it's the lock file error
        if "cannot write modified lock file" in stderr:
            log_warn("Nix could not write the lock file for a remote flake.")
            
            if confirm_action(
                "Continue ignoring the lock file write? (--no-write-lock-file)",
                default=True
            ):
                # Retry with --no-write-lock-file flag
                # Insert the flag after "upgrade"
                retry_cmd = cmd.copy()
                upgrade_idx = retry_cmd.index("upgrade")
                retry_cmd.insert(upgrade_idx + 1, "--no-write-lock-file")
                
                run(retry_cmd, check_warnings=check_warnings)
            else:
                # User declined, raise the original error
                raise CommandError(
                    "Upgrade cancelled by user",
                    returncode=returncode,
                    cmd=" ".join(cmd)
                )
        else:
            # Some other error, show it and raise
            if stdout:
                print(stdout, end='')
            if stderr:
                print(stderr, file=sys.stderr, end='')
            raise CommandError(
                f"Command failed with exit code {returncode}",
                returncode=returncode,
                cmd=" ".join(cmd)
            )

    def list_packages(self) -> List[Package]:
        """Return list of installed Nix packages."""
        if not self.is_available():
            return []
            
        try:
            returncode, stdout, stderr = run_capture(
                ["nix", "profile", "list", "--json"]
            )
            if returncode != 0:
                return []
            
            data = json.loads(stdout)
            packages = []
            elements = data.get("elements", {})
            
            def _get_version_from_store_path(store_path: str) -> str:
                """
                Extract version from a Nix store path by parsing the path directly.
                Store path format: /nix/store/HASH-package-name-version
                This is more robust than assuming fixed hash lengths.
                """
                if not store_path:
                    return "unknown"
                
                try:
                    # Extract the last component of the path
                    # e.g., /nix/store/abc123...-cachix-1.10.1-bin -> abc123...-cachix-1.10.1-bin
                    parts = store_path.rstrip('/').split('/')
                    if not parts:
                        return "unknown"
                    
                    filename = parts[-1]
                    
                    # Split by '-' and find the first part that starts with a hash
                    # Then reconstruct the package name without the hash
                    dash_parts = filename.split('-')
                    if len(dash_parts) < 2:
                        return "unknown"
                    
                    # First part is always the hash, skip it
                    # Remaining parts form: package-name-version or package-name or just name
                    name_version_parts = dash_parts[1:]
                    pkg_full_name = '-'.join(name_version_parts)
                    
                    if not pkg_full_name:
                        return "unknown"
                    
                    # Find the last occurrence of '-' followed by a digit
                    # This is more reliable than hard-coded index positions
                    for i in range(len(pkg_full_name) - 1, -1, -1):
                        if pkg_full_name[i] == '-' and i + 1 < len(pkg_full_name) and pkg_full_name[i+1].isdigit():
                            return pkg_full_name[i+1:]
                    
                    # No version found in the name
                    return "unknown"
                except Exception:
                    return "unknown"

            def _get_version_from_references(store_path: str, package_name: str) -> str:
                """
                Extract version from package references using nix-store --query --references.
                This is used as a fallback when the primary version extraction fails.
                
                Args:
                    store_path: The Nix store path to query
                    package_name: The package name to search for in references
                
                Returns:
                    Version string or "unknown" if not found
                """
                try:
                    returncode, stdout, stderr = run_capture(
                        ["nix-store", "--query", "--references", store_path]
                    )
                    if returncode != 0:
                        return "unknown"
                    
                    # Parse each reference line
                    for line in stdout.strip().split('\n'):
                        line = line.strip()
                        if not line or package_name not in line:
                            continue
                        
                        # Extract version from the reference path
                        # e.g., /nix/store/hash-bottles-60.1-bwrap -> 60.1
                        parts = line.rstrip('/').split('/')
                        if not parts:
                            continue
                        
                        filename = parts[-1]
                        dash_parts = filename.split('-')
                        if len(dash_parts) < 2:
                            continue
                        
                        # Skip the hash (first part) and reconstruct the name-version
                        name_version_parts = dash_parts[1:]
                        pkg_full_name = '-'.join(name_version_parts)
                        
                        # Find version: look for '-' followed by a digit
                        for i in range(len(pkg_full_name) - 1, -1, -1):
                            if pkg_full_name[i] == '-' and i + 1 < len(pkg_full_name) and pkg_full_name[i+1].isdigit():
                                version = pkg_full_name[i+1:]
                                # Remove common suffixes like -bwrap, -unwrapped
                                for suffix in ['-bwrap', '-unwrapped', '-bin', '-cli']:
                                    if version.endswith(suffix):
                                        version = version[:version.rfind(suffix)]
                                return version
                    
                    return "unknown"
                except Exception:
                    return "unknown"

            def _extract_version(element_details: Dict[str, Any], store_paths: List[str]) -> str:
                """
                Extract version from Nix profile element details.
                
                Priority:
                1. Use 'version' field from JSON if available
                2. Parse version from store path name
                3. Query references using nix-store --query --references
                4. Fall back to "unknown"
                """
                # First, check if JSON already has version info
                if "version" in element_details:
                    version = element_details["version"]
                    if version:
                        return str(version)
                
                # Fall back to querying the store path
                if not store_paths:
                    return "unknown"
                
                # Try to extract from store path first
                version = _get_version_from_store_path(store_paths[0])
                if version != "unknown":
                    return version
                
                # Final fallback: query references
                # Extract package name from element details to use in reference search
                package_name = element_details.get("attrPath", "").split('.')[-1]
                if not package_name:
                    package_name = element_details.get("originalUrl", "").split('#')[-1]
                
                if package_name:
                    return _get_version_from_references(store_paths[0], package_name)
                
                return "unknown"

            # Handle dict structure (common in newer Nix versions)
            if isinstance(elements, dict):
                for name, details in elements.items():
                    origin = details.get("originalUrl") or details.get("attrPath", "unknown")
                    store_paths = details.get("storePaths", [])
                    version = _extract_version(details, store_paths)
                    packages.append(Package(
                        name=name,
                        provider=self.name,
                        id=name,
                        version=version,
                        origin=origin,
                        installed=True
                    ))

            # Fallback for potential list structure (older versions?)
            elif isinstance(elements, list):
                for element in elements:
                    attr_path = element.get("attrPath") or element.get("url", "unknown")
                    name = attr_path.split('.')[-1] if '.' in attr_path else attr_path
                    store_paths = element.get("storePaths", [])
                    version = _extract_version(element, store_paths)
                    packages.append(Package(
                        name=name,
                        provider=self.name,
                        id=name,
                        version=version,
                        origin=attr_path,
                        installed=True
                    ))
                    
            return packages
        except Exception:
            return []

    def search(self, query: str) -> List[Package]:
        """Search for packages in Nixpkgs."""
        if not self.is_available():
            return []
        
        # Check cache first
        cache = SearchCache(self.name)
        cached = cache.get(query)
        if cached is not None:
            return cached
        
        try:
            returncode, stdout, stderr = run_capture(
                ["nix", "search", "nixpkgs", query, "--json"]
            )
            
            if returncode != 0:
                return []
            
            data = json.loads(stdout)
            packages: List[Package] = []
            
            # Structure: { "legacyPackages.x86_64-linux.pkgName": { "description": "...", "version": "..." } }
            for key, details in data.items():
                name = key.split('.')[-1]
                version = details.get('version', 'unknown')
                desc = details.get('description', '')
                
                packages.append(Package(
                    name=name,
                    provider=self.name,
                    id=key,  # Provide full attribute path as ID
                    version=version,
                    description=desc
                ))
            
            # Save to cache
            cache.set(query, packages)
            return packages

        except Exception:
            return []

    @require_availability
    def clean(self) -> None:
        """
        Run Nix garbage collection.
        
        Raises:
            CommandError: If cleanup fails
        """
        run(["nix-collect-garbage", "-d"])
