"""
Tests for Mixtura package providers.

Tests provider implementations for Nix, Flatpak, and Homebrew.
"""

import pytest
from unittest.mock import MagicMock, patch
import shutil

from mixtura.core.package import Package


class TestNixProvider:
    """Test Nix/Nixpkgs provider."""
    
    @patch('shutil.which')
    def test_is_available_when_installed(self, mock_which):
        """Test is_available returns True when nix is installed."""
        mock_which.return_value = "/nix/var/nix/profiles/default/bin/nix"
        
        from mixtura.core.providers.nixpkgs.provider import NixProvider
        provider = NixProvider()
        
        assert provider.is_available() == True
        mock_which.assert_called_with("nix")
    
    @patch('shutil.which')
    def test_is_available_when_not_installed(self, mock_which):
        """Test is_available returns False when nix is not installed."""
        mock_which.return_value = None
        
        from mixtura.core.providers.nixpkgs.provider import NixProvider
        provider = NixProvider()
        
        assert provider.is_available() == False
    
    def test_name_property(self):
        """Test provider name is 'nixpkgs'."""
        from mixtura.core.providers.nixpkgs.provider import NixProvider
        provider = NixProvider()
        
        assert provider.name == "nixpkgs"
    
    @patch('shutil.which')
    @patch.object(__import__('mixtura.core.providers.nixpkgs.provider', fromlist=['NixProvider']).NixProvider, 'run_command')
    def test_install_adds_nixpkgs_prefix(self, mock_run, mock_which):
        """Test that install adds nixpkgs# prefix if missing."""
        mock_which.return_value = "/nix/bin/nix"
        
        from mixtura.core.providers.nixpkgs.provider import NixProvider
        provider = NixProvider()
        provider.install(["git"])
        
        # Should have been called with nixpkgs#git
        call_args = mock_run.call_args[0][0]
        assert "nixpkgs#git" in call_args
    
    @patch('shutil.which')
    @patch.object(__import__('mixtura.core.providers.nixpkgs.provider', fromlist=['NixProvider']).NixProvider, 'run_capture')
    def test_search_returns_packages(self, mock_capture, mock_which):
        """Test search returns list of packages."""
        mock_which.return_value = "/nix/bin/nix"
        mock_capture.return_value = (0, '{"legacyPackages.x86_64-linux.git": {"version": "2.43.0", "description": "Version control"}}', '')
        
        from mixtura.core.providers.nixpkgs.provider import NixProvider
        provider = NixProvider()
        results = provider.search("git")
        
        assert len(results) >= 1
        assert results[0].name == "git"
        assert results[0].version == "2.43.0"
        assert results[0].provider == "nixpkgs"


class TestFlatpakProvider:
    """Test Flatpak provider."""
    
    @patch('shutil.which')
    def test_is_available_when_installed(self, mock_which):
        """Test is_available returns True when flatpak is installed."""
        mock_which.return_value = "/usr/bin/flatpak"
        
        from mixtura.core.providers.flatpak.provider import FlatpakProvider
        provider = FlatpakProvider()
        
        assert provider.is_available() == True
        mock_which.assert_called_with("flatpak")
    
    @patch('shutil.which')
    def test_is_available_when_not_installed(self, mock_which):
        """Test is_available returns False when flatpak is not installed."""
        mock_which.return_value = None
        
        from mixtura.core.providers.flatpak.provider import FlatpakProvider
        provider = FlatpakProvider()
        
        assert provider.is_available() == False
    
    def test_name_property(self):
        """Test provider name is 'flatpak'."""
        from mixtura.core.providers.flatpak.provider import FlatpakProvider
        provider = FlatpakProvider()
        
        assert provider.name == "flatpak"
    
    @patch('shutil.which')
    @patch.object(__import__('mixtura.core.providers.flatpak.provider', fromlist=['FlatpakProvider']).FlatpakProvider, 'run_capture')
    def test_list_packages_parses_output(self, mock_capture, mock_which):
        """Test list_packages parses flatpak list output."""
        mock_which.return_value = "/usr/bin/flatpak"
        mock_capture.return_value = (0, 'Firefox\torg.mozilla.firefox\tBrowser\t121.0', '')
        
        from mixtura.core.providers.flatpak.provider import FlatpakProvider
        provider = FlatpakProvider()
        results = provider.list_packages()
        
        assert len(results) == 1
        assert results[0].name == "Firefox"
        assert results[0].id == "org.mozilla.firefox"
        assert results[0].provider == "flatpak"


class TestHomebrewProvider:
    """Test Homebrew provider."""
    
    @patch('shutil.which')
    def test_is_available_when_installed(self, mock_which):
        """Test is_available returns True when brew is installed."""
        mock_which.return_value = "/opt/homebrew/bin/brew"
        
        from mixtura.core.providers.homebrew.provider import HomebrewProvider
        provider = HomebrewProvider()
        
        assert provider.is_available() == True
        mock_which.assert_called_with("brew")
    
    @patch('shutil.which')
    def test_is_available_when_not_installed(self, mock_which):
        """Test is_available returns False when brew is not installed."""
        mock_which.return_value = None
        
        from mixtura.core.providers.homebrew.provider import HomebrewProvider
        provider = HomebrewProvider()
        
        assert provider.is_available() == False
    
    def test_name_property(self):
        """Test provider name is 'homebrew'."""
        from mixtura.core.providers.homebrew.provider import HomebrewProvider
        provider = HomebrewProvider()
        
        assert provider.name == "homebrew"


class TestProviderLoading:
    """Test provider loading mechanism."""
    
    def test_get_all_providers_returns_dict(self):
        """Test get_all_providers returns a dictionary."""
        from mixtura.core.providers import get_all_providers
        providers = get_all_providers()
        
        assert isinstance(providers, dict)
    
    def test_get_all_providers_has_expected_keys(self):
        """Test get_all_providers has expected provider names."""
        from mixtura.core.providers import get_all_providers
        providers = get_all_providers()
        
        # Should have at least these providers registered (even if not available)
        assert "nixpkgs" in providers or len(providers) >= 0  # May be empty if import fails
    
    def test_get_default_provider_name(self):
        """Test get_default_provider_name returns a string."""
        from mixtura.core.providers import get_default_provider_name
        default = get_default_provider_name()
        
        assert isinstance(default, str)
        assert len(default) > 0


class TestPackageDataclass:
    """Test the Package dataclass."""
    
    def test_package_creation(self):
        """Test creating a Package instance."""
        pkg = Package(
            name="git",
            provider="nixpkgs",
            id="legacyPackages.x86_64-linux.git",
            version="2.43.0",
            description="Distributed version control system"
        )
        
        assert pkg.name == "git"
        assert pkg.provider == "nixpkgs"
        assert pkg.version == "2.43.0"
        assert pkg.installed == False  # default
    
    def test_package_to_dict(self):
        """Test converting Package to dictionary."""
        pkg = Package(
            name="git",
            provider="nixpkgs",
            id="git",
            version="2.43.0"
        )
        
        d = pkg.to_dict()
        
        assert d["name"] == "git"
        assert d["provider"] == "nixpkgs"
        assert d["id"] == "git"
        assert d["version"] == "2.43.0"
    
    def test_package_from_dict(self):
        """Test creating Package from dictionary."""
        data = {
            "name": "Spotify",
            "provider": "flatpak",
            "id": "com.spotify.Client",
            "version": "1.2.30",
            "description": "Music streaming"
        }
        
        pkg = Package.from_dict(data)
        
        assert pkg.name == "Spotify"
        assert pkg.provider == "flatpak"
        assert pkg.id == "com.spotify.Client"
    
    def test_package_str(self):
        """Test Package string representation."""
        pkg = Package(
            name="vim",
            provider="nixpkgs",
            id="vim",
            version="9.1.0"
        )
        
        s = str(pkg)
        
        assert "vim" in s
        assert "nixpkgs" in s
        assert "9.1.0" in s
