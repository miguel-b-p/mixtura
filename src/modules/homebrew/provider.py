import shutil
import subprocess
from typing import List, Dict, Any, Optional
import argparse
from core import PackageManager
from utils import log_info, log_error, log_warn, log_task, run, Style

class HomebrewProvider(PackageManager):
    @property
    def name(self) -> str:
        return "homebrew"

    def is_available(self) -> bool:
        return shutil.which("brew") is not None

    def install(self, packages: List[str]) -> None:
        if not self.is_available():
            log_error("Homebrew is not installed.")
            return

        run(["brew", "install"] + packages)

    def uninstall(self, packages: List[str]) -> None:
        if not self.is_available():
            return
        
        run(["brew", "uninstall"] + packages)

    def upgrade(self, packages: Optional[List[str]] = None) -> None:
        if not self.is_available():
            return

        if not packages:
            log_info("Upgrading all Homebrew packages...")
            run(["brew", "upgrade"])
        else:
            log_info(f"Upgrading: {', '.join(packages)}")
            run(["brew", "upgrade"] + packages)

    def list_packages(self) -> List[Dict[str, Any]]:
        if not self.is_available():
            return []

        # 1. Get installed on request
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
            
            # 2. Get versions
            ver_result = subprocess.run(
                ["brew", "list", "--versions"],
                capture_output=True,
                text=True
            )
            
            if ver_result.returncode != 0:
                return []

            packages = []
            lines = ver_result.stdout.strip().split('\n')
            
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 2:
                    name = parts[0]
                    # Check if this package was requested
                    if name in requested_pkgs:
                        version = parts[1]
                        packages.append({
                            "name": name,
                            "version": version,
                            "id": name # brew doesn't really have IDs like flatpak, use name
                        })

            return packages

        except Exception as e:
            log_error(f"Failed to list homebrew packages: {e}")
            return []

    def search(self, query: str) -> None:
        if not self.is_available():
            return
        log_info(f"Searching for '{Style.BOLD}{query}{Style.RESET}' in Homebrew...")
        # brew search prints directly to stdout
        run(["brew", "search", query])
