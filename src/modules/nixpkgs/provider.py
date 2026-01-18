import shutil
import subprocess
import json
import sys
import argparse
from typing import List, Dict, Any, Optional
from core import PackageManager
from utils import log_info, log_error, log_warn, run, Style

class NixProvider(PackageManager):
    @property
    def name(self) -> str:
        return "nixpkgs"

    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--gc", action="store_true", help="Garbage collect the Nix store")

    def execute(self, args: argparse.Namespace) -> None:
        if getattr(args, "gc", False):
            if not self.is_available():
                log_error("Nix is not installed.")
                return
            log_info("Running Nix garbage collection...")
            run(["nix", "store", "gc"])
        else:
             print(f"{Style.BOLD}Nix Package Manager{Style.RESET}")
             print("Use 'poly nixpkgs --gc' to garbage collect.")

    def is_available(self) -> bool:
        return shutil.which("nix") is not None
        
    def install(self, packages: List[str]) -> None:
        if not self.is_available():
            log_error("Nix is not installed.")
            return

        for pkg in packages:
            target = pkg if "#" in pkg else f"nixpkgs#{pkg}"
            log_info(f"Adding '{Style.BOLD}{pkg}{Style.RESET}' (nix)...")
            run(["nix", "profile", "add", "--impure", target])

    def uninstall(self, packages: List[str]) -> None:
        if not self.is_available():
            return
            
        for pkg in packages:
            log_info(f"Removing '{Style.BOLD}{pkg}{Style.RESET}' (nix)...")
            # Using check_warnings=True mostly to catch "no match" errors nicely
            run(["nix", "profile", "remove", pkg], check_warnings=True)

    def upgrade(self, packages: Optional[List[str]] = None) -> None:
        if not self.is_available():
            return

        if not packages:
            # Upgrade all
            log_info("Upgrading all Nix profile packages...")
            run(["nix", "profile", "upgrade", "--impure", "--all"])
        else:
            # Upgrade specific
            for pkg in packages:
                log_info(f"Upgrading '{pkg}' (nix)...")
                run(["nix", "profile", "upgrade", "--impure", pkg], check_warnings=True)

    def list_packages(self) -> List[Dict[str, Any]]:
        if not self.is_available():
            return []
            
        try:
            result = subprocess.run(
                ["nix", "profile", "list", "--json"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                return []
            
            data = json.loads(result.stdout)
            packages = []
            elements = data.get("elements", {})
            
            # Handle dict structure (common in newer Nix versions)
            if isinstance(elements, dict):
                for name, details in elements.items():
                    origin = details.get("originalUrl") or details.get("attrPath", "unknown")
                    packages.append({"name": name, "origin": origin, "version": "unknown"})
            # Fallback for potential list structure (older versions?)
            elif isinstance(elements, list):
                for element in elements:
                    attr_path = element.get("attrPath") or element.get("url", "unknown")
                    name = attr_path.split('.')[-1] if '.' in attr_path else attr_path
                    packages.append({"name": name, "origin": attr_path, "version": "unknown"})
                    
            return packages
        except Exception:
            return []

    def search(self, query: str) -> None:
        if not self.is_available():
            return
        log_info(f"Searching for '{Style.BOLD}{query}{Style.RESET}' in nixpkgs...")
        run(["nix", "search", "nixpkgs", query])
