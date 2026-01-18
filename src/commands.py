import argparse
from typing import Dict, List
from utils import log_task, log_info, log_success, log_warn, log_error, Style
from manager import ModuleManager

def _get_manager_or_warn(name: str):
    mgr = ModuleManager.get_instance().get_manager(name)
    if not mgr:
        log_warn(f"Package manager '{name}' is not available or not found.")
    return mgr

def cmd_add(args: argparse.Namespace) -> None:
    manager = ModuleManager.get_instance()
    grouped_packages = manager.resolve_packages(args.packages)
    
    if not grouped_packages:
        log_warn("No packages specified.")
        return

    for provider_name, packages in grouped_packages.items():
        mgr = _get_manager_or_warn(provider_name)
        if mgr:
            if mgr.is_available():
                log_task(f"Installing {len(packages)} packages via {mgr.name}...")
                mgr.install(packages)
            else:
                log_error(f"Provider '{mgr.name}' is not available on this system.")

    log_success("Installation process finished.")

def cmd_remove(args: argparse.Namespace) -> None:
    manager = ModuleManager.get_instance()
    grouped_packages = manager.resolve_packages(args.packages)

    if not grouped_packages:
        log_warn("No packages specified.")
        return

    for provider_name, packages in grouped_packages.items():
        mgr = _get_manager_or_warn(provider_name)
        if mgr:
             log_task(f"Removing {len(packages)} packages via {mgr.name}...")
             mgr.uninstall(packages)

    log_success("Removal process finished.")

def cmd_upgrade(args: argparse.Namespace) -> None:
    manager = ModuleManager.get_instance()
    
    # 1. Upgrade ALL
    if not args.packages:
        log_task("Upgrading all available providers...")
        for mgr in manager.get_all_managers():
            if mgr.is_available():
                log_info(f"Upgrading {mgr.name}...")
                mgr.upgrade(None) # None = all
        log_success("Upgrade complete.")
        return

    # 2. Upgrade specific provider (e.g. 'nixpkgs')
    # Or specific packages
    grouped = manager.resolve_packages(args.packages)
    
    # Special case: user might skip prefix and just say "nixpkgs" to mean "upgrade all in nixpkgs"
    # But parse_package_args logic in resolving assumes it's a package named "nixpkgs" for default provider.
    # We need to detect if arg matches a provider name directly.
    
    # A cleaner approach with the new system:
    # If the arg matches a provider name exactly, upgrade that provider fully.
    # Else, treat it as a package for default provider.
    
    pkgs_to_upgrade: Dict[str, List[str]] = {}
    providers_to_fully_upgrade = []

    for arg in args.packages:
        if manager.get_manager(arg):
            providers_to_fully_upgrade.append(arg)
        elif '#' in arg:
            # explicit provider
            prov, pkg = arg.split('#', 1)
            if prov not in pkgs_to_upgrade: pkgs_to_upgrade[prov] = []
            pkgs_to_upgrade[prov].append(pkg)
        else:
            # check default or fallback
            # In old logic: 'flatpak' was a keyword.
            if arg == 'flatpak': providers_to_fully_upgrade.append('flatpak') # compat
            elif arg == 'nixpkgs': providers_to_fully_upgrade.append('nixpkgs')
            else:
                 # Default logic (resolve via manager helper for default?)
                 # For simplicity, let's assume default is nixpkgs if not specified
                 if 'nixpkgs' not in pkgs_to_upgrade: pkgs_to_upgrade['nixpkgs'] = []
                 pkgs_to_upgrade['nixpkgs'].append(arg)

    # Execute full upgrades
    for prov in providers_to_fully_upgrade:
        mgr = _get_manager_or_warn(prov)
        if mgr and mgr.is_available():
            log_task(f"Upgrading all packages in {prov}...")
            mgr.upgrade(None)

    # Execute package specific upgrades
    for prov, pkgs in pkgs_to_upgrade.items():
        mgr = _get_manager_or_warn(prov)
        if mgr and mgr.is_available():
            log_task(f"Upgrading specific packages in {prov}...")
            mgr.upgrade(pkgs)

    if not pkgs_to_upgrade and not providers_to_fully_upgrade:
        log_warn("No packages or providers specified for upgrade.")
    else:
        log_success("Upgrade process finished.")

def cmd_list(args: argparse.Namespace) -> None:
    manager = ModuleManager.get_instance()
    
    target = args.type
    managers_to_list = []
    
    if target:
        m = manager.get_manager(target)
        if m: 
            managers_to_list.append(m)
        else:
            log_warn(f"Unknown provider '{target}'")
            return
    else:
        managers_to_list = manager.get_all_managers()

    if not managers_to_list:
        log_warn("No package managers found.")
        return

    for mgr in managers_to_list:
        if not mgr.is_available():
            continue
            
        log_task(f"Fetching packages from {mgr.name}...")
        pkgs = mgr.list_packages()
        
        if pkgs:
            print(f"\n{Style.BOLD}{Style.BLUE}:: {mgr.name} ({len(pkgs)}){Style.RESET}")
            for pkg in pkgs:
                # support various keys
                name = pkg.get('name', 'unknown')
                extra = pkg.get('version') or pkg.get('id') or pkg.get('origin') or ''
                print(f"  {Style.GREEN}•{Style.RESET} {Style.BOLD}{name}{Style.RESET} {Style.DIM}({extra}){Style.RESET}")
        else:
             print(f"\n{Style.DIM}No packages found in {mgr.name}{Style.RESET}")

def cmd_search(args: argparse.Namespace) -> None:
    manager = ModuleManager.get_instance()
    grouped = manager.resolve_packages(args.query) # Reusing this logic for "provider#term"

    for provider_name, queries in grouped.items():
        mgr = _get_manager_or_warn(provider_name)
        if mgr:
             if not mgr.is_available():
                 continue
             for q in queries:
                 mgr.search(q)
