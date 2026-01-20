import shutil
import subprocess
import argparse
from typing import List, Dict, Any, Optional

from mixtura.core import PackageManager
from mixtura.models import Package
from mixtura.utils import log_info, log_error, log_warn, log_task, run, Style

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

    def list_packages(self) -> List[Package]:
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

            packages: List[Package] = []
            lines = ver_result.stdout.strip().split('\n')
            
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 2:
                    name = parts[0]
                    # Check if this package was requested
                    if name in requested_pkgs:
                        version = parts[1]
                        packages.append(Package(
                            name=name,
                            provider=self.name,
                            id=name,  # brew doesn't really have IDs like flatpak, use name
                            version=version,
                            installed=True
                        ))

            return packages

        except Exception as e:
            log_error(f"Failed to list homebrew packages: {e}")
            return []

    def search(self, query: str) -> List[Package]:
        if not self.is_available():
            return []
        log_info(f"Searching for '{Style.BOLD}{query}{Style.RESET}' in Homebrew...")
        
        # brew search <query> --desc --eval-all
        # but output format is messy.
        # brew search --json is not available, but 'brew info --json=v2 <pkg>' works for known pkgs.
        # Efficient search with details is tricky with brew.
        # We'll parse the text output of 'brew search --eval-all --desc <query>'
        # content format:
        # ==> Formulae
        # pkgname: description
        # ...
        # ==> Casks
        # ...

        try:
             # --eval-all might be slow, maybe skip? But we need descriptions? 
             # Let's just use 'brew search <query>' and then maybe 'brew info' for details? Too slow.
             # Actually 'brew search --desc <query>' gives "name: description"
             
             cmd = ["brew", "search", "--desc", query]
             result = subprocess.run(cmd, capture_output=True, text=True)
             
             packages: List[Package] = []
             if result.returncode != 0 and not result.stdout:
                 return []
             
             lines = result.stdout.strip().split('\n')
             
             # section helper
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
                 
                 # Line format: "name: description"
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
                     version="unknown",  # Getting version requires brew info, expensive for all results
                     description=desc,
                     extra={"type": current_type}
                 ))
             
             return packages

        except Exception as e:
            log_warn(f"Homebrew search failed: {e}")
            return []

    def clean(self) -> None:
        if not self.is_available():
            log_error("Homebrew is not installed.")
            return
        log_info("Running Homebrew cleanup...")
        run(["brew", "cleanup"])

