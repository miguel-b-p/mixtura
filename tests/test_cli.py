"""
Tests for Mixtura CLI commands.

Tests all CLI commands and their options using Typer's CliRunner.
"""

from unittest.mock import patch, MagicMock

from mixtura.cli import app


class TestCLIHelp:
    """Test CLI help and version commands."""
    
    def test_main_help(self, cli_runner):
        """Test that main --help shows help text."""
        result = cli_runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Mixtura" in result.stdout or "mixtura" in result.stdout
        assert "add" in result.stdout
        assert "remove" in result.stdout
        assert "upgrade" in result.stdout
        assert "list" in result.stdout
        assert "search" in result.stdout
        assert "clean" in result.stdout
    
    def test_version(self, cli_runner):
        """Test that --version shows version."""
        result = cli_runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "Mixtura" in result.stdout or "version" in result.stdout.lower()


class TestAddCommand:
    """Test the 'add' command."""
    
    def test_add_help(self, cli_runner):
        """Test add --help shows correct options."""
        result = cli_runner.invoke(app, ["add", "--help"])
        assert result.exit_code == 0
        assert "--yes" in result.stdout or "-y" in result.stdout
        assert "--all" in result.stdout or "-a" in result.stdout
        assert "PACKAGES" in result.stdout or "packages" in result.stdout.lower()
    
    def test_add_requires_packages(self, cli_runner):
        """Test add fails without packages argument."""
        result = cli_runner.invoke(app, ["add"])
        assert result.exit_code != 0
    
    @patch('mixtura.cli.orchestrator')
    @patch('mixtura.cli.check_for_updates')
    def test_add_with_package(self, mock_update, mock_orch, cli_runner):
        """Test add with a package name."""
        _result = cli_runner.invoke(app, ["add", "git"])
        mock_orch.install_flow.assert_called_once()
        args = mock_orch.install_flow.call_args
        assert "git" in args[0][0]  # packages list
    
    @patch('mixtura.cli.orchestrator')
    @patch('mixtura.cli.check_for_updates')
    def test_add_with_yes_flag(self, mock_update, mock_orch, cli_runner):
        """Test add with --yes flag."""
        _result = cli_runner.invoke(app, ["add", "--yes", "git"])
        mock_orch.install_flow.assert_called_once()
        args, kwargs = mock_orch.install_flow.call_args
        assert kwargs.get('auto_confirm') == True or args[1] == True
    
    @patch('mixtura.cli.orchestrator')
    @patch('mixtura.cli.check_for_updates')
    def test_add_with_all_flag(self, mock_update, mock_orch, cli_runner):
        """Test add with --all flag."""
        _result = cli_runner.invoke(app, ["add", "--all", "git"])
        mock_orch.install_flow.assert_called_once()
        args, kwargs = mock_orch.install_flow.call_args
        assert kwargs.get('show_all') == True or args[2] == True
    
    @patch('mixtura.cli.orchestrator')
    @patch('mixtura.cli.check_for_updates')
    def test_add_with_provider_prefix(self, mock_update, mock_orch, cli_runner):
        """Test add with provider#package syntax."""
        _result = cli_runner.invoke(app, ["add", "flatpak#Spotify"])
        mock_orch.install_flow.assert_called_once()
        args = mock_orch.install_flow.call_args
        assert "flatpak#Spotify" in args[0][0]


class TestRemoveCommand:
    """Test the 'remove' command."""
    
    def test_remove_help(self, cli_runner):
        """Test remove --help shows correct options."""
        result = cli_runner.invoke(app, ["remove", "--help"])
        assert result.exit_code == 0
        assert "--yes" in result.stdout or "-y" in result.stdout
        assert "--all" in result.stdout or "-a" in result.stdout
    
    def test_remove_requires_packages(self, cli_runner):
        """Test remove fails without packages argument."""
        result = cli_runner.invoke(app, ["remove"])
        assert result.exit_code != 0
    
    @patch('mixtura.cli.orchestrator')
    @patch('mixtura.cli.check_for_updates')
    def test_remove_with_package(self, mock_update, mock_orch, cli_runner):
        """Test remove with a package name."""
        _result = cli_runner.invoke(app, ["remove", "git"])
        mock_orch.remove_flow.assert_called_once()


class TestUpgradeCommand:
    """Test the 'upgrade' command."""
    
    def test_upgrade_help(self, cli_runner):
        """Test upgrade --help."""
        result = cli_runner.invoke(app, ["upgrade", "--help"])
        assert result.exit_code == 0
    
    @patch('mixtura.cli.orchestrator')
    @patch('mixtura.cli.check_for_updates')
    def test_upgrade_all(self, mock_update, mock_orch, cli_runner):
        """Test upgrade without arguments upgrades all."""
        _result = cli_runner.invoke(app, ["upgrade"])
        mock_orch.upgrade_flow.assert_called_once()
        args = mock_orch.upgrade_flow.call_args
        assert args[0][0] == [] or args[0][0] is None
    
    @patch('mixtura.cli.orchestrator')
    @patch('mixtura.cli.check_for_updates')
    def test_upgrade_specific_provider(self, mock_update, mock_orch, cli_runner):
        """Test upgrade with specific provider."""
        _result = cli_runner.invoke(app, ["upgrade", "nixpkgs"])
        mock_orch.upgrade_flow.assert_called_once()
        args = mock_orch.upgrade_flow.call_args
        assert "nixpkgs" in args[0][0]


class TestListCommand:
    """Test the 'list' command."""
    
    def test_list_help(self, cli_runner):
        """Test list --help."""
        result = cli_runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0
    
    @patch('mixtura.cli.orchestrator')
    @patch('mixtura.cli.check_for_updates')
    def test_list_all(self, mock_update, mock_orch, cli_runner):
        """Test list without arguments lists all."""
        _result = cli_runner.invoke(app, ["list"])
        mock_orch.list_flow.assert_called_once()
        args = mock_orch.list_flow.call_args
        assert args[0][0] is None
    
    @patch('mixtura.cli.orchestrator')
    @patch('mixtura.cli.check_for_updates')
    def test_list_specific_provider(self, mock_update, mock_orch, cli_runner):
        """Test list with specific provider filter."""
        _result = cli_runner.invoke(app, ["list", "flatpak"])
        mock_orch.list_flow.assert_called_once()
        args = mock_orch.list_flow.call_args
        assert args[0][0] == "flatpak"


class TestSearchCommand:
    """Test the 'search' command."""
    
    def test_search_help(self, cli_runner):
        """Test search --help shows correct options."""
        result = cli_runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "--all" in result.stdout or "-a" in result.stdout
    
    def test_search_requires_query(self, cli_runner):
        """Test search fails without query argument."""
        result = cli_runner.invoke(app, ["search"])
        assert result.exit_code != 0
    
    @patch('mixtura.cli.orchestrator')
    @patch('mixtura.cli.check_for_updates')
    def test_search_with_query(self, mock_update, mock_orch, cli_runner):
        """Test search with a query."""
        _result = cli_runner.invoke(app, ["search", "git"])
        mock_orch.search_flow.assert_called_once()
        args = mock_orch.search_flow.call_args
        assert "git" in args[0][0]
    
    @patch('mixtura.cli.orchestrator')
    @patch('mixtura.cli.check_for_updates')
    def test_search_with_all_flag(self, mock_update, mock_orch, cli_runner):
        """Test search with --all flag."""
        _result = cli_runner.invoke(app, ["search", "--all", "git"])
        mock_orch.search_flow.assert_called_once()
        args, kwargs = mock_orch.search_flow.call_args
        assert kwargs.get('show_all') == True
    
    @patch('mixtura.cli.orchestrator')
    @patch('mixtura.cli.check_for_updates')
    def test_search_provider_specific(self, mock_update, mock_orch, cli_runner):
        """Test search with provider#query syntax."""
        _result = cli_runner.invoke(app, ["search", "flatpak#spotify"])
        mock_orch.search_flow.assert_called_once()
        args = mock_orch.search_flow.call_args
        assert "flatpak#spotify" in args[0][0]


class TestCleanCommand:
    """Test the 'clean' command."""
    
    def test_clean_help(self, cli_runner):
        """Test clean --help."""
        result = cli_runner.invoke(app, ["clean", "--help"])
        assert result.exit_code == 0
    
    @patch('mixtura.cli.orchestrator')
    @patch('mixtura.cli.check_for_updates')
    def test_clean_all(self, mock_update, mock_orch, cli_runner):
        """Test clean without arguments cleans all."""
        _result = cli_runner.invoke(app, ["clean"])
        mock_orch.clean_flow.assert_called_once()
    
    @patch('mixtura.cli.orchestrator')
    @patch('mixtura.cli.check_for_updates')
    def test_clean_specific_provider(self, mock_update, mock_orch, cli_runner):
        """Test clean with specific provider."""
        _result = cli_runner.invoke(app, ["clean", "nixpkgs"])
        mock_orch.clean_flow.assert_called_once()
        args = mock_orch.clean_flow.call_args
        assert "nixpkgs" in args[0][0]


class TestInfoCommand:
    """Test the 'info' command."""
    
    def test_info_help(self, cli_runner):
        """Test info --help."""
        result = cli_runner.invoke(app, ["info", "--help"])
        assert result.exit_code == 0
    
    @patch('mixtura.cli.check_for_updates')
    @patch('mixtura.cli.get_all_providers')
    @patch('mixtura.cli.get_available_providers')
    def test_info_shows_providers(self, mock_available, mock_all, mock_update, cli_runner):
        """Test info shows available providers."""
        mock_nix = MagicMock()
        mock_nix.name = "nixpkgs"
        mock_flatpak = MagicMock()
        mock_flatpak.name = "flatpak"
        
        mock_all.return_value = {"nixpkgs": mock_nix, "flatpak": mock_flatpak}
        mock_available.return_value = {"nixpkgs": mock_nix}
        
        result = cli_runner.invoke(app, ["info"])
        assert result.exit_code == 0
        assert "nixpkgs" in result.stdout
        assert "flatpak" in result.stdout
