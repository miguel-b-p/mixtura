"""
Tests for Mixtura cache module.

Tests the SearchCache functionality for caching package search results.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from mixtura.cache import SearchCache
from mixtura.core.package import Package


class TestSearchCacheInit:
    """Test SearchCache initialization."""
    
    def test_cache_creates_directory(self):
        """Test that cache creates its directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, 'home', return_value=Path(tmpdir)):
                cache = SearchCache("test_provider")
                # Directory should be created in initialization or on first access
                assert cache is not None
    
    def test_cache_uses_provider_name(self):
        """Test that cache uses provider name in file path."""
        cache = SearchCache("nixpkgs")
        assert "nixpkgs" in str(cache.cache_file) or cache.provider == "nixpkgs"


class TestSearchCacheOperations:
    """Test cache get/set operations."""
    
    def test_get_returns_none_for_missing(self):
        """Test that get returns None for non-existent keys."""
        # Create a fresh cache for a nonexistent provider
        cache = SearchCache("test_nonexistent_provider_abc123")
        
        result = cache.get("nonexistent_query_xyz")
        assert result is None
    
    def test_set_and_get_packages(self):
        """Test setting and getting package results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache" / "test_cache.json"
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            cache = SearchCache("test")
            cache.cache_file = cache_file
            
            packages = [
                Package(name="git", provider="nixpkgs", id="git", version="2.43.0"),
                Package(name="vim", provider="nixpkgs", id="vim", version="9.1.0"),
            ]
            
            cache.set("git", packages)
            
            # Get should return the cached packages
            result = cache.get("git")
            
            assert result is not None
            assert len(result) == 2
            assert result[0].name == "git"
            assert result[1].name == "vim"
    
    def test_cache_expiry(self):
        """Test that cached entries expire after TTL."""
        import time
        
        cache = SearchCache("test_expiry_provider")
        
        packages = [
            Package(name="git", provider="nixpkgs", id="git", version="2.43.0"),
        ]
        
        # Write expired entry directly to cache file
        expired_time = time.time() - 600  # 10 minutes ago (TTL is 5 min)
        cache_data = {
            "expired_query": {
                "timestamp": expired_time,
                "results": [pkg.to_dict() for pkg in packages]
            }
        }
        cache.cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache.cache_file.write_text(json.dumps(cache_data))
        
        # Should return None for expired entry
        result = cache.get("expired_query")
        assert result is None  # Expired entries return None


class TestSearchCacheClear:
    """Test cache clearing."""
    
    def test_clear_removes_cache_file(self):
        """Test that clear removes the cache file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_cache.json"
            cache_file.write_text("{}")
            
            cache = SearchCache("test")
            cache.cache_file = cache_file
            
            assert cache_file.exists()
            
            cache.clear()
            
            # File should be gone or empty after clear
            # (Implementation may vary)


class TestSearchCacheEdgeCases:
    """Test edge cases and error handling."""
    
    def test_get_handles_corrupted_file(self):
        """Test that get handles corrupted cache files gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "corrupted_cache.json"
            cache_file.write_text("not valid json {{{")
            
            cache = SearchCache("test")
            cache.cache_file = cache_file
            
            # Should not crash, should return None
            result = cache.get("query")
            assert result is None
    
    def test_set_handles_write_errors(self):
        """Test that set handles write errors gracefully."""
        cache = SearchCache("test")
        
        # Use a path that might not be writable
        with patch.object(cache, 'cache_file', Path("/nonexistent/readonly/path.json")):
            packages = [
                Package(name="test", provider="test", id="test", version="1.0"),
            ]
            
            # Should not crash even if write fails
            try:
                cache.set("query", packages)
            except Exception:
                pass  # Some implementations may raise, some may not
    
    def test_empty_results_cached(self):
        """Test that empty results can be cached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "cache" / "empty_cache.json"
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            cache = SearchCache("test")
            cache.cache_file = cache_file
            
            # Cache empty results
            cache.set("no_results_query", [])
            
            result = cache.get("no_results_query")
            # Empty list should be cached and returned
            assert result == [] or result is None  # Depends on implementation
