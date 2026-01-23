"""
Update checker for Mixtura.

Checks for new versions on GitHub.
"""

import hashlib
import os
import sys
import urllib.request
import json
import base64
import ssl
import stat

from mixtura.ui import console


def is_nuitka_compiled() -> bool:
    """Detects if the application is running as a Nuitka compiled executable."""
    return "__compiled__" in globals() or getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS')


def check_for_updates() -> None:
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

        if not github_version_url.startswith("https://"):
             raise ValueError("Update URL must be HTTPS")

        req = urllib.request.Request(github_version_url)
        with urllib.request.urlopen(req, context=ctx) as response:
            data = json.loads(response.read().decode())
            content = data.get("content", "")
            remote_version = base64.b64decode(content).decode().strip()

        # 3. Compare versions
        if local_version != remote_version:
            console.print(f"[warning bold]NOTICE: A new version of Mixtura is available! ({local_version} → {remote_version})[/warning bold]")
            
            # If running as Python module, only show notice (can't self-update)
            if not is_compiled:
                console.print("[info]Update via: pip install --upgrade mixtura (Soon on PyPI)[/info]")
                console.print()
                return
            
            # Interactive update (only for compiled executables)
            try:
                choice = input("Do you want to update to the latest version? (y/N): ")
            except EOFError:
                choice = 'n'

            if choice.lower() == 'y':
                console.print("[info]Downloading update...[/info]")
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
                        console.print("[error]Update failed: Hash mismatch! The downloaded file may be corrupted.[/error]")
                        return
                    
                    # Write to a temp file first
                    temp_path = executable_path + ".tmp"
                    with open(temp_path, 'wb') as f:
                        f.write(new_content)
                    
                    # Make executable
                    os.chmod(temp_path, stat.S_IRWXU)
                    
                    # Atomically replace (this works on Linux even if file is busy)
                    os.replace(temp_path, executable_path)
                    
                    console.print("[success]Update successful! Please restart Mixtura.[/success]")
                    sys.exit(0)
                    
                except Exception as e:
                    console.print(f"[error]Update failed: {e}[/error]")
            else:
                 console.print("Update skipped.")
                 console.print()
            
    except (urllib.error.URLError, json.JSONDecodeError, OSError, ValueError):
        # Intentionally silent: update check failures should not disrupt normal CLI usage.
        # Network errors, missing VERSION file, or API changes are non-critical.
        pass

