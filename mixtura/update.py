import hashlib
import os
import sys
import urllib.request
import json
import base64
import ssl

from mixtura.utils import Style


def is_nuitka_compiled():
    """Detects if the application is running as a Nuitka compiled executable."""
    # Nuitka sets __compiled__ attribute when compiled
    return "__compiled__" in dir() or getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS')


def check_for_updates():
    """Checks if there is a new version available by comparing versions."""
    is_compiled = is_nuitka_compiled()
    
    github_version_url = "https://api.github.com/repos/miguel-b-p/mixtura/contents/bin/VERSION"
    github_hash_url = "https://api.github.com/repos/miguel-b-p/mixtura/contents/bin/HASH"
    
    try:
        # 1. Get local version
        executable_dir = os.path.dirname(sys.argv[0])
        executable_path = os.path.join(executable_dir, "mixtura")
        version_path = os.path.join(os.path.dirname(__file__), "VERSION")
        
        with open(version_path, "r") as f:
            local_version = f.read().strip()

        # 2. Fetch remote version from GitHub API
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(github_version_url)
        with urllib.request.urlopen(req, context=ctx) as response:
            data = json.loads(response.read().decode())
            content = data.get("content", "")
            remote_version = base64.b64decode(content).decode().strip()

        # 3. Compare versions
        if local_version != remote_version:
            print(f"{Style.BOLD}{Style.WARNING}NOTICE: A new version of Mixtura is available! ({local_version} → {remote_version}){Style.RESET}")
            
            # If running as Python module, only show notice (can't self-update)
            if not is_compiled:
                print(f"{Style.INFO}Update via: pip install --upgrade mixtura{Style.RESET}")
                print()
                return
            
            # Interactive update (only for compiled executables)
            try:
                choice = input(f"Do you want to update to the latest version? ({Style.BOLD}y/N{Style.RESET}): ")
            except EOFError:
                choice = 'n'

            if choice.lower() == 'y':
                print(f"{Style.INFO}Downloading update...{Style.RESET}")
                update_url = "https://raw.githubusercontent.com/miguel-b-p/mixtura/master/bin/mixtura"
                
                try:
                    # Fetch expected hash from GitHub
                    req_hash = urllib.request.Request(github_hash_url)
                    with urllib.request.urlopen(req_hash, context=ctx) as response:
                        data = json.loads(response.read().decode())
                        content = data.get("content", "")
                        expected_hash = base64.b64decode(content).decode().strip()
                    
                    # Download new binary
                    with urllib.request.urlopen(update_url, context=ctx) as response:
                        new_content = response.read()
                    
                    # Verify hash of downloaded content
                    sha256_hash = hashlib.sha256()
                    sha256_hash.update(new_content)
                    downloaded_hash = sha256_hash.hexdigest()
                    
                    if downloaded_hash.lower() != expected_hash.lower():
                        print(f"{Style.ERROR}Update failed: Hash mismatch! The downloaded file may be corrupted.{Style.RESET}")
                        return
                    
                    # Write to a temp file first
                    temp_path = executable_path + ".tmp"
                    with open(temp_path, 'wb') as f:
                        f.write(new_content)
                    
                    # Make executable
                    os.chmod(temp_path, 0o755)
                    
                    # Atomically replace (this works on Linux even if file is busy)
                    os.replace(temp_path, executable_path)
                    
                    print(f"{Style.SUCCESS}Update successful! Please restart Mixtura.{Style.RESET}")
                    sys.exit(0)
                    
                except Exception as e:
                    print(f"{Style.ERROR}Update failed: {e}{Style.RESET}")
            else:
                 print(f"Update skipped.")
                 print()
            
    except Exception as e:
        # Fail silently on network errors or other issues to not disrupt usage
        print(e)
        pass
