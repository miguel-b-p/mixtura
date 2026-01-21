"""
Pytest configuration and shared fixtures for Mixtura tests.
"""

import pytest
from typer.testing import CliRunner
from unittest.mock import MagicMock, patch

from mixtura.core.package import Package


@pytest.fixture
def cli_runner():
    """Provide a Typer CLI runner for testing commands."""
    return CliRunner()


@pytest.fixture
def mock_orchestrator():
    """Provide a mocked orchestrator for testing CLI without side effects."""
    with patch('mixtura.cli.orchestrator') as mock:
        yield mock


@pytest.fixture
def sample_packages():
    """Provide sample Package objects for testing."""
    return [
        Package(
            name="git",
            provider="nixpkgs",
            id="legacyPackages.x86_64-linux.git",
            version="2.43.0",
            description="Distributed version control system"
        ),
        Package(
            name="Spotify",
            provider="flatpak",
            id="com.spotify.Client",
            version="1.2.30",
            description="Music streaming service"
        ),
        Package(
            name="vim",
            provider="nixpkgs",
            id="legacyPackages.x86_64-linux.vim",
            version="9.1.0",
            description="The most popular clone of the VI editor"
        ),
    ]


@pytest.fixture
def installed_packages():
    """Provide sample installed packages for testing."""
    return [
        Package(
            name="micro",
            provider="nixpkgs",
            id="micro",
            version="2.0.13",
            installed=True
        ),
        Package(
            name="Firefox",
            provider="flatpak",
            id="org.mozilla.firefox",
            version="121.0",
            installed=True
        ),
    ]


@pytest.fixture
def mock_providers():
    """Mock all providers for isolated testing."""
    with patch('mixtura.core.providers.get_all_providers') as mock_all, \
         patch('mixtura.core.providers.get_available_providers') as mock_available, \
         patch('mixtura.core.providers.get_provider') as mock_get:
        
        # Create mock provider
        mock_nix = MagicMock()
        mock_nix.name = "nixpkgs"
        mock_nix.is_available.return_value = True
        
        mock_flatpak = MagicMock()
        mock_flatpak.name = "flatpak"
        mock_flatpak.is_available.return_value = True
        
        providers = {
            "nixpkgs": mock_nix,
            "flatpak": mock_flatpak,
        }
        
        mock_all.return_value = providers
        mock_available.return_value = providers
        mock_get.side_effect = lambda name: providers.get(name)
        
        yield {
            "all": mock_all,
            "available": mock_available,
            "get": mock_get,
            "nixpkgs": mock_nix,
            "flatpak": mock_flatpak,
        }
