import shutil
import subprocess
import sys
import argparse
from typing import List, Dict, Any, Optional
from core import PackageManager
from utils import log_info, log_error, log_warn, log_task, run, Style

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

        for query in packages:
             self._install_interactive(query)

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

    def list_packages(self) -> List[Dict[str, Any]]:
        if not self.is_available():
            return []
            
        try:
            result = subprocess.run(
                ["flatpak", "list", "--app", "--columns=name,application,description,version"],
                capture_output=True,
                text=True
            )
            packages = []
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        packages.append({
                            "name": parts[0],
                            "id": parts[1],
                            "version": parts[3] if len(parts) > 3 else "unknown"
                        })
            return packages
        except Exception:
            return []

    def search(self, query: str) -> None:
        if not self.is_available():
            return
        log_info(f"Searching for '{Style.BOLD}{query}{Style.RESET}' in flathub...")
        run(["flatpak", "search", query])

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
