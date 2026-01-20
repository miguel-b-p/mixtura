import shutil
import subprocess
import sys
import argparse
from typing import List, Dict, Any, Optional

from mixtura.core import PackageManager
from mixtura.models import Package
from mixtura.utils import log_info, log_error, log_warn, log_task, run, Style

class FlatpakProvider(PackageManager):
    @property
    def name(self) -> str:
        return "flatpak"
    
    def setup_parser(self, parser: argparse.ArgumentParser) -> None:
        # No custom args for now
        pass

    def execute(self, args: argparse.Namespace) -> None:
        print(f"{Style.BOLD}Flatpak Package Manager{Style.RESET}")

    def is_available(self) -> bool:
        return shutil.which("flatpak") is not None

    def install(self, packages: List[str]) -> None:
        if not self.is_available():
            log_error("Flatpak is not installed.")
            return

        # Flatpak install can take multiple arguments
        # If the input is an ID (e.g. com.spotify.Client), it works directly.
        # If it is a name (e.g. spotify), flatpak might be interactive or find it.
        # Since we might have resolved it via cmd_add interactive search, we assume best effort.
        # We use -y to avoid flatpak's own confirmation (we are the wrapper).
        
        log_info(f"Installing: {', '.join(packages)} (flatpak)...")
        run(["flatpak", "install", "-y"] + packages)

    def uninstall(self, packages: List[str]) -> None:
        if not self.is_available():
            return

        for pkg in packages:
             log_info(f"Removing '{Style.BOLD}{pkg}{Style.RESET}' (flatpak)...")
             run(["flatpak", "uninstall", pkg])

    def upgrade(self, packages: Optional[List[str]] = None) -> None:
        if not self.is_available():
            return

        if not packages:
            log_info("Upgrading all Flatpak packages...")
            run(["flatpak", "update", "-y"])
        else:
            log_info(f"Updating: {', '.join(packages)}")
            run(["flatpak", "update", "-y"] + packages)

    def list_packages(self) -> List[Package]:
        if not self.is_available():
            return []
            
        try:
            result = subprocess.run(
                ["flatpak", "list", "--app", "--columns=name,application,description,version"],
                capture_output=True,
                text=True
            )
            packages: List[Package] = []
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
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
        if not self.is_available():
            return []
        
        log_info(f"Searching for '{Style.BOLD}{query}{Style.RESET}' in flathub...")
        
        try:
            # We use --columns to ensure consistent output format
            result = subprocess.run(
                ["flatpak", "search", query, "--columns=name,application,description,version"], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode != 0:
                return []

            lines = result.stdout.strip().split('\n')
            packages: List[Package] = []
            
            # Skip header if present (flatpak usually prints header if tty, but maybe not with pipe, checking just in case)
            if lines and "Application ID" in lines[0]:
                lines = lines[1:]

            for line in lines:
                if not line.strip(): continue
                parts = line.split('\t')
                
                # Fallback for splitting if tabs aren't reliable (rare with --columns but possible)
                if len(parts) < 2:
                    parts = line.split(maxsplit=3) # naive fallback

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
            return packages

        except Exception as e:
            log_warn(f"Flatpak search failed: {e}")
            return []

    def _install_interactive(self, term: str) -> None:
        log_task(f"Searching for '{Style.BOLD}{term}{Style.RESET}' in flathub...")
        
        try:
            result = subprocess.run(
                ["flatpak", "search", term, "--columns=name,application,description"], 
                capture_output=True, 
                text=True
            )
            
            if result.returncode != 0:
                log_error("Failed to search flatpak.")
                return

            lines = result.stdout.strip().split('\n')
            lines = [line for line in lines if line.strip()]

            if not lines:
                log_warn(f"No matches found for '{term}'.")
                return

            if lines and "Application ID" in lines[0]:
                lines = lines[1:]
            
            if not lines:
                 log_warn(f"No matches found for '{term}'.")
                 return

            packages = []
            for line in lines:
                parts = line.split('\t')
                if len(parts) < 2: 
                     parts = line.split("   ")
                
                parts = [p.strip() for p in parts if p.strip()]
                
                if len(parts) >= 2:
                    name = parts[0]
                    app_id = parts[1]
                    desc = parts[2] if len(parts) > 2 else "No description"
                    packages.append({'name': name, 'id': app_id, 'desc': desc})

            if not packages:
                log_warn(f"No matches found for '{term}'.")
                return

            # Display menu
            print(f"\n{Style.BOLD}Available packages:{Style.RESET}")
            for i, pkg in enumerate(packages):
                idx = i + 1
                print(f" {Style.SUCCESS}{idx}.{Style.RESET} {Style.BOLD}{pkg['name']}{Style.RESET} ({Style.DIM}{pkg['id']}{Style.RESET})")
                print(f"    {pkg['desc']}")
            
            print()
            try:
                choice = input(f"{Style.INFO}Select a package (1-{len(packages)}) or 'q' to cancel: {Style.RESET}")
                if choice.lower() == 'q':
                    log_warn("Operation cancelled.")
                    return
                
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(packages):
                    selected = packages[choice_idx]
                    log_task(f"Installing {selected['name']} ({selected['id']})...")
                    run(["flatpak", "install", selected['id']])
                else:
                    log_error("Invalid selection.")
            except ValueError:
                 log_error("Invalid input. Please enter a number.")

        except Exception as e:
            log_error(f"An error occurred: {e}")

    def clean(self) -> None:
        if not self.is_available():
            log_error("Flatpak is not installed.")
            return
        log_info("Removing unused Flatpak packages...")
        run(["flatpak", "uninstall", "--unused", "-y"])

