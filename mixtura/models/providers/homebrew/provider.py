"""
Homebrew package provider for Mixtura.

Provides integration with Homebrew package manager (macOS/Linux).
"""

import shutil
import subprocess
from typing import List, Optional

from mixtura.models.base import PackageManager
from mixtura.models.package import Package
from mixtura.utils import run


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

        run(["brew", "install"] + packages)

    def uninstall(self, packages: List[str]) -> None:
        """
        Remove Homebrew packages.
        
        Raises:
            CommandError: If uninstall fails
        """
        if not self.is_available():
            raise RuntimeError("Homebrew is not installed.")
        
        run(["brew", "uninstall"] + packages)

    def upgrade(self, packages: Optional[List[str]] = None) -> None:
        """
        Upgrade Homebrew packages.
        
        Raises:
            CommandError: If upgrade fails
        """
        if not self.is_available():
            raise RuntimeError("Homebrew is not installed.")

        if not packages:
            run(["brew", "upgrade"])
        else:
            run(["brew", "upgrade"] + packages)

    def list_packages(self) -> List[Package]:
        """Return list of installed Homebrew packages (installed on request only)."""
        if not self.is_available():
            return []

        try:
            req_result = subprocess.run(
                ["brew", "list", "--installed-on-request"],
                capture_output=True,
                text=True
            )
            if req_result.returncode != 0:
                return []
            
            requested_pkgs = set(req_result.stdout.strip().split('\n'))
            requested_pkgs = {p.strip() for p in requested_pkgs if p.strip()}
            
            ver_result = subprocess.run(
                ["brew", "list", "--versions"],
                capture_output=True,
                text=True
            )
            
            if ver_result.returncode != 0:
                return []

            packages: List[Package] = []
            lines = ver_result.stdout.strip().split('\n')
            
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
        
        try:
             cmd = ["brew", "search", "--desc", query]
             result = subprocess.run(cmd, capture_output=True, text=True)
             
             packages: List[Package] = []
             if result.returncode != 0 and not result.stdout:
                 return []
             
             lines = result.stdout.strip().split('\n')
             
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
        run(["brew", "cleanup"])
