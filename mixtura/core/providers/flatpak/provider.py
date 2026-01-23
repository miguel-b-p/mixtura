"""
Flatpak package provider for Mixtura.

Provides integration with Flatpak package manager.
"""

import shutil
from typing import List, Optional

from mixtura.core.providers.base import PackageManager, require_availability
from mixtura.core.package import Package
from mixtura.cache import SearchCache
from mixtura.utils import run, run_capture


class FlatpakProvider(PackageManager):
    @property
    def name(self) -> str:
        return "flatpak"

    def is_available(self) -> bool:
        return shutil.which("flatpak") is not None

    @require_availability
    def install(self, packages: List[str]) -> None:
        """
        Install packages via Flatpak.
        
        Args:
            packages: List of packages to install.

        Raises:
            CommandError: If installation fails.
        """
        # Flatpak may prompt for remote selection (interactive) even with -y.
        # We request exclusive mode to pause other providers and prevent output mixing/input races.
        with self.exclusive_mode():
            run(["flatpak", "install", "-y"] + packages)

    @require_availability
    def uninstall(self, packages: List[str]) -> None:
        """
        Remove Flatpak packages.
        
        Args:
            packages: List of packages to remove.

        Raises:
            CommandError: If uninstall fails.
        """
        for pkg in packages:
            run(["flatpak", "uninstall", pkg])

    @require_availability
    def upgrade(self, packages: Optional[List[str]] = None) -> None:
        """
        Upgrade Flatpak packages.
        
        Args:
            packages: Optional list of packages to upgrade.

        Raises:
            CommandError: If upgrade fails.
        """
        if not packages:
            run(["flatpak", "update", "-y"])
        else:
            run(["flatpak", "update", "-y"] + packages)

    def list_packages(self) -> List[Package]:
        """
        Return list of installed Flatpak apps.

        Returns:
            List[Package]: Installed Flatpak packages.
        """
        if not self.is_available():
            return []
            
        try:
            returncode, stdout, stderr = run_capture(
                ["flatpak", "list", "--app", "--columns=name,application,description,version"]
            )
            
            packages: List[Package] = []
            if returncode == 0:
                lines = stdout.strip().split('\n')
                for line in lines:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        packages.append(Package(
                            name=parts[0],
                            provider=self.name,
                            id=parts[1],
                            version=parts[3] if len(parts) > 3 else "unknown",
                            installed=True
                        ))
            return packages
        except Exception:
            return []

    def search(self, query: str) -> List[Package]:
        """
        Search for packages in Flathub.

        Args:
            query: The search query.

        Returns:
            List[Package]: Found packages.
        """
        if not self.is_available():
            return []
        
        # Check cache first
        cache = SearchCache(self.name)
        cached = cache.get(query)
        if cached is not None:
            return cached
        
        try:
            returncode, stdout, stderr = run_capture(
                ["flatpak", "search", query, "--columns=name,application,description,version"]
            )
            
            if returncode != 0:
                return []

            lines = stdout.strip().split('\n')
            packages: List[Package] = []
            
            # Skip header if present
            if lines and "Application ID" in lines[0]:
                lines = lines[1:]

            for line in lines:
                if not line.strip():
                    continue
                parts = line.split('\t')
                
                # Fallback for splitting if tabs aren't reliable
                if len(parts) < 2:
                    parts = line.split(maxsplit=3)

                if len(parts) >= 2:
                    name = parts[0]
                    app_id = parts[1]
                    desc = parts[2] if len(parts) > 2 else ""
                    version = parts[3] if len(parts) > 3 else "unknown"
                    
                    packages.append(Package(
                        name=name,
                        provider=self.name,
                        id=app_id,
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
        Remove unused Flatpak packages and data.
        
        Raises:
            CommandError: If cleanup fails.
        """
        run(["flatpak", "uninstall", "--unused", "-y"])
