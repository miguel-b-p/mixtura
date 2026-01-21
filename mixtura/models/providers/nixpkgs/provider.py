"""
Nixpkgs package provider for Mixtura.

Provides integration with Nix package manager.
"""

import shutil
import json
from typing import List, Optional

from mixtura.models.base import PackageManager
from mixtura.models.package import Package
from mixtura.cache import SearchCache


class NixProvider(PackageManager):
    @property
    def name(self) -> str:
        return "nixpkgs"

    def is_available(self) -> bool:
        return shutil.which("nix") is not None
        
    def install(self, packages: List[str]) -> None:
        """
        Install packages via Nix profile.
        
        Raises:
            CommandError: If installation fails
        """
        if not self.is_available():
            raise RuntimeError("Nix is not installed.")

        for pkg in packages:
            target = pkg if "#" in pkg else f"nixpkgs#{pkg}"
            self.run_command(["nix", "profile", "add", "--impure", target])

    def uninstall(self, packages: List[str]) -> None:
        """
        Remove packages from Nix profile.
        
        Raises:
            CommandError: If uninstall fails
        """
        if not self.is_available():
            raise RuntimeError("Nix is not installed.")
            
        for pkg in packages:
            self.run_command(["nix", "profile", "remove", pkg], check_warnings=True)

    def upgrade(self, packages: Optional[List[str]] = None) -> None:
        """
        Upgrade Nix profile packages.
        
        Raises:
            CommandError: If upgrade fails
        """
        if not self.is_available():
            raise RuntimeError("Nix is not installed.")

        if not packages:
            # Upgrade all
            self.run_command(["nix", "profile", "upgrade", "--impure", "--all"])
        else:
            # Upgrade specific
            for pkg in packages:
                self.run_command(["nix", "profile", "upgrade", "--impure", pkg], check_warnings=True)

    def list_packages(self) -> List[Package]:
        """Return list of installed Nix packages."""
        if not self.is_available():
            return []
            
        try:
            returncode, stdout, stderr = self.run_capture(
                ["nix", "profile", "list", "--json"]
            )
            if returncode != 0:
                return []
            
            data = json.loads(stdout)
            packages = []
            elements = data.get("elements", {})
            
            def _resolve_version_fallback(store_path: str, pkg_name: str) -> str:
                if not store_path or not pkg_name:
                    return "unknown"
                try:
                    rc, out, _ = self.run_capture(
                        ["nix-store", "--query", "--references", store_path]
                    )
                    if rc != 0:
                        return "unknown"
                    
                    candidates = []
                    for line in out.splitlines():
                        if pkg_name in line:
                            candidates.append(line.strip())
                    
                    for candidate in candidates:
                        parts = candidate.split('/')
                        if len(parts) < 4: continue
                        filename = parts[3] 
                        
                        if len(filename) <= 33: continue
                        name_ver = filename[33:]
                        
                        for i in range(len(name_ver)):
                             if name_ver[i] == '-' and i + 1 < len(name_ver) and name_ver[i+1].isdigit():
                                 return name_ver[i+1:]
                    
                    return "unknown"
                except Exception:
                    return "unknown"

            def _extract_version(store_paths: List[str], pkg_name: str) -> str:
                if not store_paths: return "unknown"
                
                path = store_paths[0]
                version = "unknown"
                try:
                     parts = path.split('/')
                     if len(parts) > 3 and parts[1] == 'nix' and parts[2] == 'store':
                         filename = parts[3]
                         name_ver = filename[33:] # skip hash and dash
                         
                         for i in range(len(name_ver)):
                             if name_ver[i] == '-' and i + 1 < len(name_ver) and name_ver[i+1].isdigit():
                                 version = name_ver[i+1:]
                                 break
                except Exception:
                    pass
                
                if version != "unknown":
                    return version
                    
                return _resolve_version_fallback(path, pkg_name)

            # Handle dict structure (common in newer Nix versions)
            if isinstance(elements, dict):
                for name, details in elements.items():
                    origin = details.get("originalUrl") or details.get("attrPath", "unknown")
                    store_paths = details.get("storePaths", [])
                    version = _extract_version(store_paths, name)
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
                    version = _extract_version(store_paths, name)
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
            returncode, stdout, stderr = self.run_capture(
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

    def clean(self) -> None:
        """
        Run Nix garbage collection.
        
        Raises:
            CommandError: If cleanup fails
        """
        if not self.is_available():
            raise RuntimeError("Nix is not installed.")
        self.run_command(["nix-collect-garbage", "-d"])
