import argparse
from typing import Dict, List

from mixtura.utils import log_task, log_info, log_success, log_warn, log_error, Style
from mixtura.manager import ModuleManager

def _get_manager_or_warn(name: str):
    mgr = ModuleManager.get_instance().get_manager(name)
    if not mgr:
        log_warn(f"Package manager '{name}' is not available or not found.")
    return mgr

def cmd_add(args: argparse.Namespace) -> None:
    manager = ModuleManager.get_instance()
    
    # We need to manually parse args to distinguish "naked" packages
    # resolve_packages forces a default provider which we want to avoid if possible for 'add'
    # Actually, resolve_packages logic: 
    # if '#' not in arg: defaults to 'nixpkgs' (or whatever default)
    
    # New logic: iterate over args. 
    # If arg has '#', use it.
    # If not, search ALL providers.
    
    packages_to_install: Dict[str, List[str]] = {}
    
    for arg in args.packages:
        if '#' in arg:
            # Explicit provider
            provider, pkgs_str = arg.split('#', 1)
            # Handle comma separated values
            items = [p.strip() for p in pkgs_str.split(',') if p.strip()]
            
            if provider not in packages_to_install:
                packages_to_install[provider] = []
            packages_to_install[provider].extend(items)
        else:
            # Ambiguous package - Search Mode
            # Handle commas here too: add git,vim -> [git, vim]
            items = [p.strip() for p in arg.split(',') if p.strip()]
            
            for item in items:
                log_task(f"Searching for '{Style.BOLD}{item}{Style.RESET}' across all providers...")
                results = manager.search_all(item)
                
                if not results:
                    log_warn(f"No packages found for '{item}'.")
                    continue
                
                # Interactive Selection
                print(f"\n{Style.BOLD}Found {len(results)} matches for '{item}':{Style.RESET}")
                
                for i, res in enumerate(results):
                    idx = i + 1
                    name = res.get('name', 'unknown')
                    prov = res.get('provider', 'unknown')
                    ver = res.get('version', '')
                    desc = res.get('description', '')[:60]
                    if len(res.get('description', '')) > 60: desc += "..."
                    
                    print(f" {Style.SUCCESS}{idx}.{Style.RESET} {Style.BOLD}{name}{Style.RESET} {Style.DIM}({prov} {ver}){Style.RESET}")
                    if desc:
                        print(f"    {desc}")
                
                print()
                try:
                    choice = input(f"{Style.INFO}Select a package to add (1-{len(results)}) or 's' to skip: {Style.RESET}")
                    if choice.lower() == 's' or choice.lower() == 'q':
                        print("Skipping...")
                        continue
                    
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(results):
                        selected = results[choice_idx]
                        prov = selected['provider']
                        pkg_id = selected.get('id') or selected.get('name')
                        
                        if prov not in packages_to_install:
                            packages_to_install[prov] = []
                        
                        packages_to_install[prov].append(pkg_id)
                        log_info(f"Selected {selected['name']} from {prov}")
                    else:
                        log_error("Invalid selection.")
                except ValueError:
                    log_error("Invalid input.")

    # Proceed with installation
    if not packages_to_install:
        log_warn("No packages selected for installation.")
        return

    print()
    for provider_name, packages in packages_to_install.items():
        mgr = _get_manager_or_warn(provider_name)
        if mgr and mgr.is_available():
            log_task(f"Installing {len(packages)} packages via {mgr.name}...")
            mgr.install(packages)
        else:
            if mgr:
                log_error(f"Provider '{mgr.name}' is not available.")
            else:
                 log_error(f"Provider '{provider_name}' unknown.")

    log_success("Installation process finished.")

def cmd_remove(args: argparse.Namespace) -> None:
    manager = ModuleManager.get_instance()
    
    packages_to_remove: Dict[str, List[str]] = {}

    for arg in args.packages:
        if '#' in arg:
            # Explicit provider
            provider, pkgs_str = arg.split('#', 1)
            # Handle comma separated values
            items = [p.strip() for p in pkgs_str.split(',') if p.strip()]
            
            if provider not in packages_to_remove:
                packages_to_remove[provider] = []
            packages_to_remove[provider].extend(items)
        else:
            # Ambiguous package - Search Installed Mode
            # Handle commas here too
            items = [p.strip() for p in arg.split(',') if p.strip()]
            
            for item in items:
                log_task(f"Searching for installed package '{Style.BOLD}{item}{Style.RESET}'...")
                
                matches = []
                for mgr in manager.get_all_managers():
                    if not mgr.is_available():
                        continue
                    
                    try:
                        installed = mgr.list_packages() # Assuming this is reasonably fast
                        for pkg in installed:
                            # Fuzzy matching or exact? 
                            # User said "similar names", so substring match is good.
                            # But we should prioritize exact match if possible?
                            p_name = pkg.get('name', '')
                            if item.lower() in p_name.lower():
                                pkg['provider'] = mgr.name
                                matches.append(pkg)
                    except Exception as e:
                        log_warn(f"Failed to list packages from {mgr.name}: {e}")

                if not matches:
                    log_warn(f"No installed packages found matching '{item}'.")
                    continue
                
                # Filter out packages that are already selected for removal
                # from previous arguments or searches in this same command
                filtered_matches = []
                for m in matches:
                    prov = m['provider']
                    pid = m.get('id') or m.get('name')
                    # Check if already in our scheduled list
                    if pid not in packages_to_remove.get(prov, []):
                        filtered_matches.append(m)
                
                if not filtered_matches:
                    # If we found matches but they are all already selected, just skip
                    if len(matches) > 0:
                        log_info(f"Matches for '{item}' are already selected for removal. Skipping prompt.")
                    continue
                
                matches = filtered_matches

                print(f"\n{Style.BOLD}Found {len(matches)} installed matches for '{item}':{Style.RESET}")
                
                for i, res in enumerate(matches):
                    idx = i + 1
                    name = res.get('name', 'unknown')
                    prov = res.get('provider', 'unknown')
                    ver = res.get('version', '')
                    # Some list_packages implementation might not give desc, that's fine.
                    
                    print(f" {Style.SUCCESS}{idx}.{Style.RESET} {Style.BOLD}{name}{Style.RESET} {Style.DIM}({prov} {ver}){Style.RESET}")
                
                print()
                try:
                    choice = input(f"{Style.INFO}Select a package to remove (1-{len(matches)}), 'a' to remove all, or 's' to skip: {Style.RESET}")
                    if choice.lower() == 's' or choice.lower() == 'q':
                        print("Skipping...")
                        continue
                    
                    if choice.lower() == 'a':
                        confirm = input(f"{Style.WARNING}Are you sure you want to remove ALL {len(matches)} packages listed above? (y/N): {Style.RESET}")
                        if confirm.lower() == 'y':
                            for selected in matches:
                                prov = selected['provider']
                                pkg_id = selected.get('id') or selected.get('name')
                                if prov not in packages_to_remove:
                                    packages_to_remove[prov] = []
                                packages_to_remove[prov].append(pkg_id)
                                log_info(f"Selected {selected['name']} from {prov} for removal")
                            continue
                        else:
                             print("Cancelled 'remove all'. Skipping...")
                             continue

                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(matches):
                        selected = matches[choice_idx]
                        prov = selected['provider']
                        
                        pkg_id = selected.get('id') or selected.get('name')
                        
                        if prov not in packages_to_remove:
                            packages_to_remove[prov] = []
                        packages_to_remove[prov].append(pkg_id)
                        log_info(f"Selected {selected['name']} from {prov} for removal")
                    else:
                        log_error("Invalid selection.")
                except ValueError:
                    log_error("Invalid input.")

    if not packages_to_remove:
        log_warn("No packages selected for removal.")
        return

    for provider_name, packages in packages_to_remove.items():
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
    packages_map: Dict[str, List[str]] = {}
    providers_full = []
    
    # Reuse simple logic or custom parsing?
    # Let's use simple manual parsing as resolve_packages forces default.
    
    for arg in args.packages:
        # Check if arg is a provider name
        if manager.get_manager(arg):
            providers_full.append(arg)
            continue
            
        if '#' in arg:
            prov, pkg = arg.split('#', 1)
            if prov not in packages_map: packages_map[prov] = []
            packages_map[prov].append(pkg)
        else:
            # Default fallback for upgrade? 
            # Assume 'nixpkgs' as default for upgrade context if not specified? 
            # Or should we warn?
            # Existing behavior was defaulting to nixpkgs.
            prov = 'nixpkgs'
            if prov not in packages_map: packages_map[prov] = []
            packages_map[prov].append(arg)

    # Execute full upgrades
    for prov in providers_full:
        mgr = _get_manager_or_warn(prov)
        if mgr and mgr.is_available():
            log_task(f"Upgrading all packages in {prov}...")
            mgr.upgrade(None)

    # Execute package specific upgrades
    for prov, pkgs in packages_map.items():
        mgr = _get_manager_or_warn(prov)
        if mgr and mgr.is_available():
            log_task(f"Upgrading specific packages in {prov}...")
            mgr.upgrade(pkgs)

    if not packages_map and not providers_full:
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

    first = True
    for mgr in managers_to_list:
        if not mgr.is_available():
            continue

        if not first:
            print()
        first = False
            
        log_task(f"Fetching packages from {mgr.name}...")
        pkgs = mgr.list_packages()
        
        if pkgs:
            print(f"{Style.BOLD}{Style.INFO}:: {mgr.name} ({len(pkgs)}){Style.RESET}")
            for pkg in pkgs:
                # support various keys
                name = pkg.get('name', 'unknown')
                extra = pkg.get('version') or pkg.get('id') or pkg.get('origin') or ''
                print(f"  {Style.SUCCESS}•{Style.RESET} {Style.BOLD}{name}{Style.RESET} {Style.DIM}({extra}){Style.RESET}")
        else:
             print(f"{Style.DIM}No packages found in {mgr.name}{Style.RESET}")

def cmd_search(args: argparse.Namespace) -> None:
    manager = ModuleManager.get_instance()
    # If args.query is a list, we handle each.
    # Note: argparse definition for 'search' usually takes 'query' as nargs='+'
    
    for q in args.query:
        if '#' in q:
             # Provider specific search
             prov, term = q.split('#', 1)
             mgr = _get_manager_or_warn(prov)
             if mgr and mgr.is_available():
                 results = mgr.search(term)
                 if results:
                     print(f"{Style.BOLD}Results for '{term}' in {prov}:{Style.RESET}")
                     for res in results:
                         print(f"  • {res.get('name')} ({res.get('version')}) - {res.get('description')}")
                 else:
                     log_warn(f"No results for '{term}' in {prov}")
        else:
             # Search all
             log_task(f"Searching for '{q}'...")
             results = manager.search_all(q)
             if results:
                 print(f"{Style.BOLD}Results for '{q}':{Style.RESET}")
                 for res in results:
                      prov = res.get('provider')
                      print(f"  [{prov}] {res.get('name')} ({res.get('version')}) - {res.get('description')}")
             else:
                 log_warn(f"No results for '{q}'")
