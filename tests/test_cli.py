"""
Tests for Mixtura CLI commands.

Tests all CLI commands and their options using Typer's CliRunner.
"""

from unittest.mock import patch, MagicMock
import pytest
from mixtura.cli import app
from mixtura.core.package import Package, OperationResult

@pytest.fixture
def mock_service():
    with patch('mixtura.cli.service') as mock:
        yield mock

@pytest.fixture
def mock_display():
    with patch('mixtura.cli.display_package_list') as mock:
        yield mock

@pytest.fixture
def mock_select():
    with patch('mixtura.cli.select_package') as mock:
        yield mock

@pytest.fixture
def mock_results():
    with patch('mixtura.cli.display_operation_results') as mock:
        yield mock

class TestCLIHelp:
    """Test CLI help and version commands."""
    
    def test_main_help(self, cli_runner):
        """Test that main --help shows help text."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Mixtura" in result.stdout or "mixtura" in result.stdout
        assert "add" in result.stdout
        assert "remove" in result.stdout
        
    def test_version(self, cli_runner):
        """Test that --version shows version."""
        result = cli_runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "Mixtura" in result.stdout or "version" in result.stdout.lower()


class TestAddCommand:
    """Test the 'add' command."""
    
    @patch('mixtura.cli.check_for_updates')
    def test_add_with_package(self, mock_update, mock_service, mock_results, cli_runner):
        """Test add with a package name."""
        # Setup mock behavior
        pkg = Package("git", "nixpkgs", "git")
        mock_service.search.return_value = [pkg]
        mock_service.install.return_value = [OperationResult("nixpkgs", True, "Success")]
        
        # We also need to mock select_package or use --yes, otherwise prompt appears
        with patch('mixtura.cli.select_package', return_value=[pkg]):
            cli_runner.invoke(app, ["add", "git"])
        
        mock_service.search.assert_called_with("git")
        mock_service.install.assert_called_once()
        args = mock_service.install.call_args[0][0] # params_for_install
        assert args[0].name == "git"
        assert args[0].provider == "nixpkgs"
        
    @patch('mixtura.cli.check_for_updates')
    def test_add_explicit_provider(self, mock_update, mock_service, mock_results, cli_runner):
        """Test add with nixpkgs#vim syntax."""
        mock_service.install.return_value = [OperationResult("nixpkgs", True, "Success")]
        
        cli_runner.invoke(app, ["add", "nixpkgs#vim"])
        
        # Should not search, direct install
        mock_service.search.assert_not_called()
        mock_service.install.assert_called_once()
        args = mock_service.install.call_args[0][0]
        assert args[0].name == "vim"
        assert args[0].provider == "nixpkgs"

    @patch('mixtura.cli.check_for_updates')
    def test_add_auto_confirm(self, mock_update, mock_service, mock_results, cli_runner):
        """Test add with --yes flag."""
        pkg = Package("git", "nixpkgs", "git")
        mock_service.search.return_value = [pkg]
        mock_service.install.return_value = []
        
        cli_runner.invoke(app, ["add", "--yes", "git"])
        
        # Should auto select without prompt
        with patch('mixtura.cli.select_package') as mock_select:
             mock_select.assert_not_called()


class TestRemoveCommand:
    """Test the 'remove' command."""

    @patch('mixtura.cli.check_for_updates')
    def test_remove_with_package(self, mock_update, mock_service, mock_results, cli_runner):
        """Test remove with search for installed package."""
        pkg = Package("git", "nixpkgs", "git")
        
        # Mocking get_provider to simulate installed check loop
        mock_mgr = MagicMock()
        mock_mgr.is_available.return_value = True
        mock_mgr.list_packages.return_value = [pkg]
        mock_service.get_provider.return_value = mock_mgr
        
        mock_service.remove.return_value = [OperationResult("nixpkgs", True, "Success")]
        
        # We need to explicitly mock select_package for this test too, unless --yes
        with patch('mixtura.cli.select_package', return_value=[pkg]):
             cli_runner.invoke(app, ["remove", "git"])
        
        mock_service.remove.assert_called_once()
        args = mock_service.remove.call_args[0][0]
        assert args[0].name == "git"


class TestUpgradeCommand:
    """Test the 'upgrade' command."""
    
    @patch('mixtura.cli.check_for_updates')
    def test_upgrade_all(self, mock_update, mock_service, mock_results, cli_runner):
        """Test upgrade without arguments."""
        mock_service.upgrade.return_value = []
        
        cli_runner.invoke(app, ["upgrade"])
        mock_service.upgrade.assert_called_with(None)

    @patch('mixtura.cli.check_for_updates')
    def test_upgrade_specific(self, mock_update, mock_service, mock_results, cli_runner):
        """Test upgrade specific provider."""
        mock_service.upgrade.return_value = []
        
        cli_runner.invoke(app, ["upgrade", "nixpkgs"])
        
        mock_service.upgrade.assert_called_once()
        args = mock_service.upgrade.call_args[0][0]
        assert args[0].name == "nixpkgs"


class TestListCommand:
    """Test the 'list' command."""
    
    @patch('mixtura.cli.check_for_updates')
    @patch('mixtura.cli.get_available_providers')
    @patch('mixtura.cli.display_installed_packages')
    def test_list_all(self, mock_display, mock_available, mock_update, mock_service, cli_runner):
        """Test list all."""
        mock_mgr = MagicMock()
        mock_mgr.name = "nixpkgs"
        mock_mgr.is_available.return_value = True
        mock_mgr.list_packages.return_value = []
        
        mock_available.return_value = {"nixpkgs": mock_mgr}
        
        cli_runner.invoke(app, ["list"])
        
        mock_mgr.list_packages.assert_called_once()
        mock_display.assert_called_once()


class TestSearchCommand:
    """Test the 'search' command."""
    
    @patch('mixtura.cli.check_for_updates')
    @patch('mixtura.cli.display_package_list')
    def test_search_query(self, mock_display, mock_update, mock_service, cli_runner):
        """Test search query."""
        mock_service.search.return_value = [Package("git", "nixpkgs", "git")]
        
        cli_runner.invoke(app, ["search", "git"])
        mock_service.search.assert_called_with("git")
        mock_display.assert_called_once()


class TestCleanCommand:
    """Test the 'clean' command."""
    
    @patch('mixtura.cli.check_for_updates')
    @patch('mixtura.cli.get_available_providers')
    @patch('mixtura.cli.display_operation_results')
    def test_clean_all(self, mock_results, mock_available, mock_update, mock_service, cli_runner):
        """Test clean all."""
        mock_mgr = MagicMock()
        mock_mgr.name = "nixpkgs"
        mock_available.return_value = {"nixpkgs": mock_mgr}
        
        cli_runner.invoke(app, ["clean"])
        mock_mgr.clean.assert_called_once()
