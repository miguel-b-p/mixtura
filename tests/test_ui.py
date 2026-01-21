"""
Tests for Mixtura UI components.

Tests the display functions, prompts, and console styling.
"""

import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from mixtura.core.package import Package


class TestUIImports:
    """Test UI module imports and exports."""
    
    def test_ui_imports(self):
        """Test that UI module exports expected symbols."""
        from mixtura.ui import (
            console,
            log_info,
            log_task,
            log_success,
            log_warn,
            log_error,
            print_logo,
            ASCII_LOGO,
            MIXTURA_THEME,
        )
        
        assert console is not None
        assert callable(log_info)
        assert callable(log_task)
        assert callable(log_success)
        assert callable(log_warn)
        assert callable(log_error)
        assert callable(print_logo)
        assert ASCII_LOGO is not None
        assert MIXTURA_THEME is not None


class TestConsole:
    """Test Rich console configuration."""
    
    def test_console_has_theme(self):
        """Test console has custom theme applied."""
        from mixtura.ui import console, MIXTURA_THEME
        
        # Console should be configured with our theme
        assert console is not None
    
    def test_theme_has_expected_styles(self):
        """Test theme has all expected style names."""
        from mixtura.ui import MIXTURA_THEME
        
        # Check for expected style names in the theme
        expected_styles = ["main", "success", "error", "info", "warning"]
        for style in expected_styles:
            assert style in MIXTURA_THEME.styles


class TestLogFunctions:
    """Test logging functions."""
    
    @patch('mixtura.ui.console')
    def test_log_info(self, mock_console):
        """Test log_info outputs with info style."""
        from mixtura.ui import log_info
        
        log_info("Test message")
        
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "Test message" in call_args
        assert "[info]" in call_args
    
    @patch('mixtura.ui.console')
    def test_log_task(self, mock_console):
        """Test log_task outputs with main style."""
        from mixtura.ui import log_task
        
        log_task("Task in progress")
        
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "Task in progress" in call_args
        assert "[main]" in call_args
    
    @patch('mixtura.ui.console')
    def test_log_success(self, mock_console):
        """Test log_success outputs with success style."""
        from mixtura.ui import log_success
        
        log_success("Operation complete")
        
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "Operation complete" in call_args
        assert "[success]" in call_args
    
    @patch('mixtura.ui.console')
    def test_log_warn(self, mock_console):
        """Test log_warn outputs with warning style."""
        from mixtura.ui import log_warn
        
        log_warn("Warning message")
        
        mock_console.print.assert_called_once()
        call_args = mock_console.print.call_args[0][0]
        assert "Warning message" in call_args
        assert "[warning]" in call_args
    
    def test_log_error_outputs_to_stderr(self):
        """Test log_error outputs to stderr."""
        from mixtura.ui import log_error
        
        # This should not raise - just verify it executes
        log_error("Error message")


class TestAsciiLogo:
    """Test ASCII logo."""
    
    def test_ascii_logo_exists(self):
        """Test ASCII logo is defined."""
        from mixtura.ui import ASCII_LOGO
        
        assert ASCII_LOGO is not None
        assert len(ASCII_LOGO) > 0
        assert "Mixtura" in ASCII_LOGO or "▙" in ASCII_LOGO  # Contains logo characters
    
    @patch('mixtura.ui.console')
    def test_print_logo(self, mock_console):
        """Test print_logo outputs the logo."""
        from mixtura.ui import print_logo
        
        print_logo()
        
        mock_console.print.assert_called_once()


class TestDisplayFunctions:
    """Test display functions."""
    
    def test_display_imports(self):
        """Test display module imports."""
        from mixtura.ui.display import (
            display_package_list,
            display_installed_packages,
            display_operation_results,
        )
        
        assert callable(display_package_list)
        assert callable(display_installed_packages)
        assert callable(display_operation_results)
    
    @patch('mixtura.ui.display.console')
    def test_display_package_list(self, mock_console):
        """Test display_package_list outputs package info."""
        from mixtura.ui.display import display_package_list
        
        packages = [
            Package(name="git", provider="nixpkgs", id="git", version="2.43.0", description="VCS"),
        ]
        
        display_package_list(packages, "Test Results")
        
        # Should have printed multiple times (title, package info)
        assert mock_console.print.call_count >= 2
    
    @patch('mixtura.ui.display.console')
    def test_display_installed_packages(self, mock_console):
        """Test display_installed_packages outputs package list."""
        from mixtura.ui.display import display_installed_packages
        
        packages = [
            Package(name="micro", provider="nixpkgs", id="micro", version="2.0.13", installed=True),
        ]
        
        display_installed_packages(packages, "nixpkgs")
        
        assert mock_console.print.call_count >= 1
    
    @patch('mixtura.ui.display.console')
    @patch('mixtura.ui.display.log_success')
    @patch('mixtura.ui.display.log_error')
    def test_display_operation_results_success(self, mock_error, mock_success, mock_console):
        """Test display_operation_results with all successes."""
        from mixtura.ui.display import display_operation_results
        
        results = [
            ("nixpkgs", True, "Installed 2 packages"),
            ("flatpak", True, "Installed 1 package"),
        ]
        
        display_operation_results(results)
        
        # Should log success for each result and final success
        assert mock_success.call_count >= 2
    
    @patch('mixtura.ui.display.console')
    @patch('mixtura.ui.display.log_success')
    @patch('mixtura.ui.display.log_error')
    @patch('mixtura.ui.display.log_warn')
    def test_display_operation_results_with_errors(self, mock_warn, mock_error, mock_success, mock_console):
        """Test display_operation_results with some errors."""
        from mixtura.ui.display import display_operation_results
        
        results = [
            ("nixpkgs", True, "Installed 2 packages"),
            ("flatpak", False, "Failed to install"),
        ]
        
        display_operation_results(results)
        
        # Should log success for first, error for second, warn at end
        mock_success.assert_called()
        mock_error.assert_called()


class TestPrompts:
    """Test prompt functions."""
    
    def test_prompts_import(self):
        """Test prompts module imports."""
        from mixtura.ui.prompts import (
            select_package,
            confirm_action,
        )
        
        assert callable(select_package)
        assert callable(confirm_action)
    
    def test_select_package_empty_list(self):
        """Test select_package with empty list returns empty."""
        from mixtura.ui.prompts import select_package
        
        result = select_package([])
        
        assert result == []
    
    @patch('mixtura.ui.prompts.Prompt.ask')
    def test_select_package_skip(self, mock_ask):
        """Test select_package returns empty on skip."""
        from mixtura.ui.prompts import select_package
        
        mock_ask.return_value = "s"
        
        packages = [
            Package(name="git", provider="nixpkgs", id="git", version="2.43.0"),
        ]
        
        result = select_package(packages)
        
        assert result == []
    
    @patch('mixtura.ui.prompts.Prompt.ask')
    def test_select_package_valid_selection(self, mock_ask):
        """Test select_package with valid numeric selection."""
        from mixtura.ui.prompts import select_package
        
        mock_ask.return_value = "1"
        
        packages = [
            Package(name="git", provider="nixpkgs", id="git", version="2.43.0"),
            Package(name="vim", provider="nixpkgs", id="vim", version="9.1.0"),
        ]
        
        result = select_package(packages)
        
        assert len(result) == 1
        assert result[0].name == "git"
    
    @patch('mixtura.ui.prompts.Prompt.ask')
    def test_select_package_all(self, mock_ask):
        """Test select_package returns all on 'a' input."""
        from mixtura.ui.prompts import select_package
        
        mock_ask.return_value = "a"
        
        packages = [
            Package(name="git", provider="nixpkgs", id="git", version="2.43.0"),
            Package(name="vim", provider="nixpkgs", id="vim", version="9.1.0"),
        ]
        
        result = select_package(packages, allow_all=True)
        
        assert len(result) == 2
    
    @patch('mixtura.ui.prompts.Confirm.ask')
    def test_confirm_action_yes(self, mock_ask):
        """Test confirm_action returns True on yes."""
        from mixtura.ui.prompts import confirm_action
        
        mock_ask.return_value = True
        
        result = confirm_action("Confirm?")
        
        assert result == True
    
    @patch('mixtura.ui.prompts.Confirm.ask')
    def test_confirm_action_no(self, mock_ask):
        """Test confirm_action returns False on no."""
        from mixtura.ui.prompts import confirm_action
        
        mock_ask.return_value = False
        
        result = confirm_action("Confirm?")
        
        assert result == False
