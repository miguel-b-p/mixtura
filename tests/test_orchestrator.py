"""
Tests for Mixtura Orchestrator (Service Layer).

Tests the business logic for package management operations.
"""

import pytest
from unittest.mock import MagicMock, patch

from mixtura.core.orchestrator import Orchestrator
from mixtura.core.package import Package


class TestOrchestratorInit:
    """Test orchestrator initialization."""
    
    @patch('mixtura.core.orchestrator.get_all_providers')
    def test_init_loads_providers(self, mock_providers):
        """Test that orchestrator loads providers on init."""
        mock_providers.return_value = {"nixpkgs": MagicMock()}
        orch = Orchestrator()
        mock_providers.assert_called_once()
        assert orch.providers == {"nixpkgs": mock_providers.return_value["nixpkgs"]}


class TestParseSingleArg:
    """Test argument parsing logic."""
    
    @patch('mixtura.core.orchestrator.get_all_providers')
    @patch('mixtura.core.orchestrator.get_default_provider_name')
    def test_parse_with_provider_prefix(self, mock_default, mock_providers):
        """Test parsing provider#package syntax."""
        mock_providers.return_value = {}
        orch = Orchestrator()
        
        provider, packages = orch.parse_single_arg("flatpak#Spotify")
        assert provider == "flatpak"
        assert packages == ["Spotify"]
    
    @patch('mixtura.core.orchestrator.get_all_providers')
    @patch('mixtura.core.orchestrator.get_default_provider_name')
    def test_parse_with_comma_separated(self, mock_default, mock_providers):
        """Test parsing comma-separated packages."""
        mock_providers.return_value = {}
        orch = Orchestrator()
        
        provider, packages = orch.parse_single_arg("nixpkgs#git,vim,micro")
        assert provider == "nixpkgs"
        assert packages == ["git", "vim", "micro"]
    
    @patch('mixtura.core.orchestrator.get_all_providers')
    @patch('mixtura.core.orchestrator.get_default_provider_name')
    def test_parse_without_prefix_uses_default(self, mock_default, mock_providers):
        """Test that packages without prefix use default provider."""
        mock_providers.return_value = {}
        mock_default.return_value = "nixpkgs"
        orch = Orchestrator()
        
        provider, packages = orch.parse_single_arg("git")
        assert provider == "nixpkgs"
        assert packages == ["git"]


class TestFilterResultsSmart:
    """Test smart filtering logic."""
    
    @patch('mixtura.core.orchestrator.get_all_providers')
    def test_show_all_returns_all(self, mock_providers):
        """Test that show_all=True returns all results."""
        mock_providers.return_value = {}
        orch = Orchestrator()
        
        packages = [
            Package(name="git", provider="nixpkgs", id="git", version="2.43.0"),
            Package(name="git-lfs", provider="nixpkgs", id="git-lfs", version="3.4.0"),
            Package(name="gitui", provider="nixpkgs", id="gitui", version="0.24.0"),
        ]
        
        result = orch.filter_results_smart(packages, "git", show_all=True)
        assert len(result) == 3
    
    @patch('mixtura.core.orchestrator.get_all_providers')
    def test_exact_match_priority(self, mock_providers):
        """Test that exact name match is prioritized."""
        mock_providers.return_value = {}
        orch = Orchestrator()
        
        packages = [
            Package(name="git", provider="nixpkgs", id="git", version="2.43.0"),
            Package(name="git-lfs", provider="nixpkgs", id="git-lfs", version="3.4.0"),
            Package(name="gitui", provider="nixpkgs", id="gitui", version="0.24.0"),
        ]
        
        result = orch.filter_results_smart(packages, "git", show_all=False)
        assert len(result) == 1
        assert result[0].name == "git"
    
    @patch('mixtura.core.orchestrator.get_all_providers')
    def test_wildcard_pattern(self, mock_providers):
        """Test wildcard pattern matching."""
        mock_providers.return_value = {}
        orch = Orchestrator()
        
        packages = [
            Package(name="git", provider="nixpkgs", id="git", version="2.43.0"),
            Package(name="git-lfs", provider="nixpkgs", id="git-lfs", version="3.4.0"),
            Package(name="gitui", provider="nixpkgs", id="gitui", version="0.24.0"),
            Package(name="vim", provider="nixpkgs", id="vim", version="9.0"),
        ]
        
        result = orch.filter_results_smart(packages, "git*", show_all=False)
        assert len(result) == 3
        assert all(p.name.startswith("git") for p in result)
    
    @patch('mixtura.core.orchestrator.get_all_providers')
    def test_empty_results(self, mock_providers):
        """Test that empty results returns empty list."""
        mock_providers.return_value = {}
        orch = Orchestrator()
        
        result = orch.filter_results_smart([], "git", show_all=False)
        assert result == []


class TestSearchAll:
    """Test parallel search across providers."""
    
    @patch('mixtura.core.orchestrator.get_all_providers')
    @patch('mixtura.core.orchestrator.get_available_providers')
    def test_search_all_aggregates_results(self, mock_available, mock_all):
        """Test that search_all aggregates results from all providers."""
        mock_nix = MagicMock()
        mock_nix.search.return_value = [
            Package(name="git", provider="nixpkgs", id="git", version="2.43.0")
        ]
        
        mock_flatpak = MagicMock()
        mock_flatpak.search.return_value = [
            Package(name="GitKraken", provider="flatpak", id="com.axosoft.GitKraken", version="9.0")
        ]
        
        mock_all.return_value = {"nixpkgs": mock_nix, "flatpak": mock_flatpak}
        mock_available.return_value = {"nixpkgs": mock_nix, "flatpak": mock_flatpak}
        
        orch = Orchestrator()
        results = orch.search_all("git")
        
        assert len(results) == 2
        providers = {r.provider for r in results}
        assert "nixpkgs" in providers
        assert "flatpak" in providers
    
    @patch('mixtura.core.orchestrator.get_all_providers')
    @patch('mixtura.core.orchestrator.get_available_providers')
    def test_search_all_handles_provider_errors(self, mock_available, mock_all):
        """Test that search_all handles provider errors gracefully."""
        mock_nix = MagicMock()
        mock_nix.search.side_effect = Exception("Network error")
        
        mock_flatpak = MagicMock()
        mock_flatpak.search.return_value = [
            Package(name="Spotify", provider="flatpak", id="com.spotify.Client", version="1.2.0")
        ]
        
        mock_all.return_value = {"nixpkgs": mock_nix, "flatpak": mock_flatpak}
        mock_available.return_value = {"nixpkgs": mock_nix, "flatpak": mock_flatpak}
        
        orch = Orchestrator()
        results = orch.search_all("spotify")
        
        # Should still return flatpak results despite nix error
        assert len(results) == 1
        assert results[0].provider == "flatpak"


class TestInstallFlow:
    """Test install flow logic."""
    
    @patch('mixtura.core.orchestrator.get_all_providers')
    @patch('mixtura.core.orchestrator.get_provider')
    @patch('mixtura.core.orchestrator.log_info')
    @patch('mixtura.core.orchestrator.log_task')
    @patch('mixtura.core.orchestrator.log_warn')
    @patch('mixtura.core.orchestrator.console')
    @patch('mixtura.core.orchestrator.display_operation_results')
    def test_install_with_provider_prefix(
        self, mock_display, mock_console, mock_warn, mock_task, mock_info, mock_get, mock_all
    ):
        """Test install with explicit provider prefix."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.name = "flatpak"
        mock_get.return_value = mock_provider
        mock_all.return_value = {"flatpak": mock_provider}
        
        orch = Orchestrator()
        orch.install_flow(["flatpak#Spotify"])
        
        mock_provider.install.assert_called_once()
        args = mock_provider.install.call_args[0][0]
        assert "Spotify" in args


class TestUpgradeFlow:
    """Test upgrade flow logic."""
    
    @patch('mixtura.core.orchestrator.get_all_providers')
    @patch('mixtura.core.orchestrator.get_available_providers')
    @patch('mixtura.core.orchestrator.log_info')
    @patch('mixtura.core.orchestrator.log_warn')
    @patch('mixtura.core.orchestrator.console')
    @patch('mixtura.core.orchestrator.display_operation_results')
    def test_upgrade_all(
        self, mock_display, mock_console, mock_warn, mock_info, mock_available, mock_all
    ):
        """Test upgrade all providers."""
        mock_nix = MagicMock()
        mock_nix.name = "nixpkgs"
        mock_nix.is_available.return_value = True
        
        mock_all.return_value = {"nixpkgs": mock_nix}
        mock_available.return_value = {"nixpkgs": mock_nix}
        
        orch = Orchestrator()
        orch.upgrade_flow([])
        
        # Should have called upgrade
        mock_nix.upgrade.assert_called()


class TestListFlow:
    """Test list flow logic."""
    
    @patch('mixtura.core.orchestrator.get_all_providers')
    @patch('mixtura.core.orchestrator.get_provider')
    @patch('mixtura.core.orchestrator.log_task')
    @patch('mixtura.core.orchestrator.log_warn')
    @patch('mixtura.core.orchestrator.console')
    @patch('mixtura.core.orchestrator.display_installed_packages')
    def test_list_specific_provider(
        self, mock_display, mock_console, mock_warn, mock_task, mock_get, mock_all
    ):
        """Test listing packages from specific provider."""
        mock_provider = MagicMock()
        mock_provider.name = "nixpkgs"
        mock_provider.is_available.return_value = True
        mock_provider.list_packages.return_value = [
            Package(name="git", provider="nixpkgs", id="git", version="2.43.0", installed=True)
        ]
        
        mock_all.return_value = {"nixpkgs": mock_provider}
        mock_get.return_value = mock_provider
        
        orch = Orchestrator()
        orch.list_flow("nixpkgs")
        
        mock_provider.list_packages.assert_called_once()
        mock_display.assert_called_once()
