"""
Search cache module for Mixtura.

Provides caching for package searches with 5-minute TTL using pickle.
Cache files are stored in $HOME/mixtura/cache/.
"""

import pickle
import time
from pathlib import Path
from typing import List, Optional, Any, Dict


class SearchCache:
    """
    Cache de busca com expiração de 5 minutos.
    
    Cada provider tem seu próprio arquivo de cache.
    O cache armazena {query: (timestamp, results)}.
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
        self.cache_file = self.CACHE_DIR / f"{provider_name}_search.pkl"
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist."""
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_cache(self) -> Dict[str, tuple]:
        """Load cache from disk."""
        if not self.cache_file.exists():
            return {}
        try:
            with open(self.cache_file, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return {}
    
    def _save_cache(self, cache: Dict[str, tuple]) -> None:
        """Save cache to disk."""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(cache, f)
        except Exception:
            pass  # Silently fail if we can't write cache
    
    def get(self, query: str) -> Optional[List[Any]]:
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
        
        timestamp, results = cache[query]
        current_time = time.time()
        
        if current_time - timestamp > self.TTL_SECONDS:
            # Cache expired, remove entry
            del cache[query]
            self._save_cache(cache)
            return None
        
        return results
    
    def set(self, query: str, results: List[Any]) -> None:
        """
        Save results to cache.
        
        Args:
            query: Search query string
            results: List of package results to cache
        """
        cache = self._load_cache()
        cache[query] = (time.time(), results)
        self._save_cache(cache)
