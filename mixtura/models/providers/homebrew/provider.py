"""
Homebrew package provider for Mixtura.

Provides integration with Homebrew package manager (macOS/Linux).
"""

import shutil
from typing import List, Optional

from mixtura.models.base import PackageManager
from mixtura.models.package import Package
from mixtura.cache import SearchCache


class HomebrewProvider(PackageManager):
    @property
    def name(self) -> str:
        return "homebrew"

    def is_available(self) -> bool:
        return shutil.which("brew") is not None

    def install(self, packages: List[str]) -> None:
        """
        Install packages via Homebrew.
        
        Raises:
            CommandError: If installation fails
        """
        if not self.is_available():
            raise RuntimeError("Homebrew is not installed.")

        self.run_command(["brew", "install"] + packages)

    def uninstall(self, packages: List[str]) -> None:
        """
        Remove Homebrew packages.
        
        Raises:
            CommandError: If uninstall fails
        """
        if not self.is_available():
            raise RuntimeError("Homebrew is not installed.")
        
        self.run_command(["brew", "uninstall"] + packages)

    def upgrade(self, packages: Optional[List[str]] = None) -> None:
        """
        Upgrade Homebrew packages.
        
        Raises:
            CommandError: If upgrade fails
        """
        if not self.is_available():
            raise RuntimeError("Homebrew is not installed.")

        if not packages:
            self.run_command(["brew", "upgrade"])
        else:
            self.run_command(["brew", "upgrade"] + packages)

    def list_packages(self) -> List[Package]:
        """Return list of installed Homebrew packages (installed on request only)."""
        if not self.is_available():
            return []

        try:
            # Get packages installed on request
            rc1, req_stdout, _ = self.run_capture(
                ["brew", "list", "--installed-on-request"]
            )
            if rc1 != 0:
                return []
            
            requested_pkgs = set(req_stdout.strip().split('\n'))
            requested_pkgs = {p.strip() for p in requested_pkgs if p.strip()}
            
            # Get versions
            rc2, ver_stdout, _ = self.run_capture(
                ["brew", "list", "--versions"]
            )
            
            if rc2 != 0:
                return []

            packages: List[Package] = []
            lines = ver_stdout.strip().split('\n')
            
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 2:
                    name = parts[0]
                    if name in requested_pkgs:
                        version = parts[1]
                        packages.append(Package(
                            name=name,
                            provider=self.name,
                            id=name,
                            version=version,
                            installed=True
                        ))

            return packages

        except Exception:
            return []

    def search(self, query: str) -> List[Package]:
        """Search for packages in Homebrew."""
        if not self.is_available():
            return []
        
        # Check cache first
        cache = SearchCache(self.name)
        cached = cache.get(query)
        if cached is not None:
            return cached
        
        try:
            returncode, stdout, stderr = self.run_capture(
                ["brew", "search", "--desc", query]
            )
             
            packages: List[Package] = []
            if returncode != 0 and not stdout:
                return []
             
            lines = stdout.strip().split('\n')
             
            current_type = "formula" 
             
            for line in lines:
                line = line.strip()
                if not line: continue
                if line.startswith("==> Formulae"):
                    current_type = "formula"
                    continue
                if line.startswith("==> Casks"):
                    current_type = "cask"
                    continue
                 
                if ": " in line:
                    parts = line.split(": ", 1)
                    name = parts[0]
                    desc = parts[1]
                else:
                    name = line
                    desc = "No description"
                 
                packages.append(Package(
                    name=name,
                    provider=self.name,
                    id=name,
                    version="unknown",
                    description=desc,
                    extra={"type": current_type}
                ))
             
            # Save to cache
            cache.set(query, packages)
            return packages

        except Exception:
            return []

    def clean(self) -> None:
        """
        Run Homebrew cleanup.
        
        Raises:
            CommandError: If cleanup fails
        """
        if not self.is_available():
            raise RuntimeError("Homebrew is not installed.")
        self.run_command(["brew", "cleanup"])
