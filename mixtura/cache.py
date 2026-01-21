"""
Search cache module for Mixtura.

Provides caching for package searches with 5-minute TTL using JSON.
Cache files are stored in $HOME/mixtura/cache/.
"""

import json
import time
from pathlib import Path
from typing import List, Optional, Any, Dict

from mixtura.models.package import Package


class SearchCache:
    """
    Cache de busca com expiração de 5 minutos.
    
    Cada provider tem seu próprio arquivo de cache.
    O cache armazena {query: {"timestamp": float, "results": [...]}}
    """
    
    CACHE_DIR = Path.home() / "mixtura" / "cache"
    TTL_SECONDS = 300  # 5 minutos
    
    def __init__(self, provider_name: str):
        """
        Initialize cache for a specific provider.
        
        Args:
            provider_name: Name of the provider (e.g., 'nixpkgs', 'flatpak')
        """
        self.provider_name = provider_name
        self.cache_file = self.CACHE_DIR / f"{provider_name}_search.json"
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist."""
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        """Load cache from disk."""
        if not self.cache_file.exists():
            return {}
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    
    def _save_cache(self, cache: Dict[str, Dict[str, Any]]) -> None:
        """Save cache to disk."""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except IOError:
            pass  # Silently fail if we can't write cache
    
    def _serialize_results(self, results: List[Package]) -> List[Dict[str, Any]]:
        """Convert Package objects to JSON-serializable dicts."""
        return [pkg.to_dict() if hasattr(pkg, 'to_dict') else pkg for pkg in results]
    
    def _deserialize_results(self, data: List[Dict[str, Any]]) -> List[Package]:
        """Convert dicts back to Package objects."""
        return [Package.from_dict(item) for item in data]
    
    def get(self, query: str) -> Optional[List[Package]]:
        """
        Get cached results if valid (not expired).
        
        Args:
            query: Search query string
            
        Returns:
            Cached results if valid, None if expired or not found
        """
        cache = self._load_cache()
        
        if query not in cache:
            return None
        
        entry = cache[query]
        timestamp = entry.get("timestamp", 0)
        results_data = entry.get("results", [])
        current_time = time.time()
        
        if current_time - timestamp > self.TTL_SECONDS:
            # Cache expired, remove entry
            del cache[query]
            self._save_cache(cache)
            return None
        
        return self._deserialize_results(results_data)
    
    def set(self, query: str, results: List[Package]) -> None:
        """
        Save results to cache.
        
        Args:
            query: Search query string
            results: List of Package objects to cache
        """
        cache = self._load_cache()
        cache[query] = {
            "timestamp": time.time(),
            "results": self._serialize_results(results)
        }
        self._save_cache(cache)
    
    def clear(self) -> None:
        """Clear all cached entries for this provider."""
        try:
            if self.cache_file.exists():
                self.cache_file.unlink()
        except IOError:
            pass
    
    def clear_expired(self) -> None:
        """Remove only expired entries from cache."""
        cache = self._load_cache()
        current_time = time.time()
        
        expired_keys = [
            key for key, entry in cache.items()
            if current_time - entry.get("timestamp", 0) > self.TTL_SECONDS
        ]
        
        for key in expired_keys:
            del cache[key]
        
        if expired_keys:
            self._save_cache(cache)
