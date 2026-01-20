import shutil
import subprocess
import json
import sys
import argparse
from typing import List, Dict, Any, Optional

from mixtura.core import PackageManager
from mixtura.utils import log_info, log_error, log_warn, run, Style

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
            
            def _resolve_version_fallback(store_path: str, pkg_name: str) -> str:
                if not store_path or not pkg_name:
                    return "unknown"
                try:
                    # Run: nix-store --query --references <store_path> | grep <pkg_name>
                    # We'll do the grep in python to avoid shell pipes security issues if any
                    res = subprocess.run(
                        ["nix-store", "--query", "--references", store_path],
                        capture_output=True,
                        text=True
                    )
                    if res.returncode != 0:
                        return "unknown"
                    
                    # Output is list of /nix/store/hash-name-ver
                    # We filter for ones containing pkg_name
                    candidates = []
                    for line in res.stdout.splitlines():
                        if pkg_name in line:
                            candidates.append(line.strip())
                    
                    # Attempt to parse version from candidates
                    # Example candidate: /nix/store/78562fr80k3r1wp7djvxvmm8s5p9m50z-bottles-unwrapped-60.1
                    # Strategies:
                    # 1. Look for one that seems to end in version numbers
                    # 2. Heuristic: take the one that is NOT just the same as input if possible, 
                    #    or matches name-version pattern.
                    
                    found_version = "unknown"
                    
                    for candidate in candidates:
                        # Extract the filename part
                        parts = candidate.split('/')
                        if len(parts) < 4: continue
                        filename = parts[3] 
                        
                        # Remove hash (32 chars) + dash = 33 chars
                        if len(filename) <= 33: continue
                        name_ver = filename[33:]
                        
                        # We want to extract version. 
                        # name_ver like "bottles-unwrapped-60.1" or "bottles-60.1-bwrap" or "bottles-cli-60.1-bwrap"
                        
                        # Try to find the version part
                        # Heuristic from before: first dash followed by digit
                        ver_candidate = "unknown"
                        for i in range(len(name_ver)):
                             if name_ver[i] == '-' and i + 1 < len(name_ver) and name_ver[i+1].isdigit():
                                 ver_candidate = name_ver[i+1:]
                                 break
                        
                        if ver_candidate != "unknown":
                             # If we found a version, we might want to prefer the Main package if we can identify it,
                             # but usually just getting ANY version is better than unknown.
                             # If we find multiple, maybe pick the shortest one assuming it is the main package?
                             # Or just return the first one found.
                             return ver_candidate

                    return found_version
                except Exception:
                    return "unknown"

            def _extract_version(store_paths: List[str], pkg_name: str) -> str:
                if not store_paths: return "unknown"
                
                # Try from the main store path first (fast)
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
                    
                # Fallback: query references
                return _resolve_version_fallback(path, pkg_name)

            # Handle dict structure (common in newer Nix versions)
            if isinstance(elements, dict):
                for name, details in elements.items():
                    origin = details.get("originalUrl") or details.get("attrPath", "unknown")
                    store_paths = details.get("storePaths", [])
                    version = _extract_version(store_paths, name)
                    packages.append({"name": name, "origin": origin, "version": version})

            # Fallback for potential list structure (older versions?)
            elif isinstance(elements, list):
                for element in elements:
                    attr_path = element.get("attrPath") or element.get("url", "unknown")
                    name = attr_path.split('.')[-1] if '.' in attr_path else attr_path
                    store_paths = element.get("storePaths", [])
                    version = _extract_version(store_paths, name)
                    packages.append({"name": name, "origin": attr_path, "version": version})
                    
            return packages
        except Exception:
            return []

    def search(self, query: str) -> List[Dict[str, Any]]:
        if not self.is_available():
            return []
        log_info(f"Searching for '{Style.BOLD}{query}{Style.RESET}' in nixpkgs...")
        
        try:
            # nix search nixpkgs <query> --json
            # Note: Experimental feature, might need --extra-experimental-features 'nix-command flakes'
            # But the existing code suggests 'nix profile' usage which implies 2.4+
            cmd = ["nix", "search", "nixpkgs", query, "--json"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                # Fallback or just return empty?
                # Sometimes nix return non-zero if no matches?
                return []
            
            data = json.loads(result.stdout)
            packages = []
            
            # Structure: { "legacyPackages.x86_64-linux.pkgName": { "description": "...", "version": "..." } }
            for key, details in data.items():
                # key is usually something like "legacyPackages.x86_64-linux.git"
                # we want the last part as name usually
                name = key.split('.')[-1]
                version = details.get('version', 'unknown')
                desc = details.get('description', '')
                
                packages.append({
                    "name": name,
                    "id": key, # Provide full attribute path as ID
                    "description": desc,
                    "version": version,
                    "provider": self.name
                })
            
            return packages

        except Exception as e:
            log_warn(f"Nix search failed: {e}")
            return []

    def clean(self) -> None:
        if not self.is_available():
            log_error("Nix is not installed.")
            return
        log_info("Running Nix garbage collection...")
        run(["nix-collect-garbage", "-d"])

