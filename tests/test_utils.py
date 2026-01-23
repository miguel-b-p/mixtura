"""
Tests for Mixtura utils module.

Tests the command execution utilities and error handling.
"""

import pytest
from unittest.mock import patch, MagicMock
import subprocess

from mixtura.utils import run, run_capture, CommandError


class TestCommandError:
    """Test CommandError exception."""
    
    def test_command_error_creation(self):
        """Test CommandError can be created with message."""
        error = CommandError("Command failed")
        assert str(error) == "Command failed"
    
    def test_command_error_inheritance(self):
        """Test CommandError inherits from Exception."""
        error = CommandError("test")
        assert isinstance(error, Exception)


class TestRunCapture:
    """Test run_capture function."""
    
    @patch('subprocess.run')
    def test_run_capture_success(self, mock_run):
        """Test run_capture returns output on success."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="output",
            stderr=""
        )
        
        returncode, stdout, stderr = run_capture(["echo", "hello"])
        
        assert returncode == 0
        assert stdout == "output"
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_run_capture_failure(self, mock_run):
        """Test run_capture returns non-zero on failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error message"
        )
        
        returncode, stdout, stderr = run_capture(["false"])
        
        assert returncode == 1
        assert stderr == "error message"
    
    @patch('subprocess.run')
    def test_run_capture_with_check(self, mock_run):
        """Test run_capture raises on failure with check=True."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error"
        )
        
        # With check=True, should raise CommandError
        with pytest.raises(CommandError):
            run_capture(["false"], check=True)
    
    @patch('subprocess.run')
    def test_run_capture_passes_env(self, mock_run):
        """Test run_capture passes environment variables."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        custom_env = {"MY_VAR": "value"}
        run_capture(["cmd"], env=custom_env)
        
        # Check env was passed (merged with os.environ)
        call_kwargs = mock_run.call_args.kwargs
        assert "env" in call_kwargs
    
    @patch('subprocess.run')
    def test_run_capture_with_timeout(self, mock_run):
        """Test run_capture passes timeout."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        run_capture(["cmd"], timeout=30)
        
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs.get("timeout") == 30
    
    @patch('subprocess.run')
    def test_run_capture_with_cwd(self, mock_run):
        """Test run_capture passes working directory."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        import tempfile
        run_capture(["cmd"], cwd=tempfile.gettempdir())
        
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs.get("cwd") == tempfile.gettempdir()


class TestRun:
    """Test run function (visual execution)."""
    
    @patch('mixtura.utils.subprocess.run')
    @patch('mixtura.ui.console')
    @patch('mixtura.ui.log_info')
    @patch('mixtura.ui.log_error')
    @patch('mixtura.ui.log_warn')
    def test_run_success(self, mock_warn, mock_error, mock_info, mock_console, mock_subrun):
        """Test run executes command successfully."""
        mock_subrun.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        # Should not raise
        run(["echo", "hello"], silent=True)
        mock_subrun.assert_called()
    
    @patch('mixtura.utils.subprocess.run')
    @patch('mixtura.ui.console')
    @patch('mixtura.ui.log_info')
    @patch('mixtura.ui.log_error')
    def test_run_failure_raises(self, mock_error, mock_info, mock_console, mock_subrun):
        """Test run raises CommandError on failure."""
        mock_subrun.side_effect = subprocess.CalledProcessError(1, ["false"])
        
        with pytest.raises(CommandError):
            run(["false"], silent=True)
    
    @patch('mixtura.utils.subprocess.run')
    @patch('mixtura.utils.console')
    def test_run_prints_command_when_not_silent(self, mock_console, mock_subrun):
        """Test run prints command when silent=False."""
        mock_subrun.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        run(["echo", "test"], silent=False)
        
        # Console should have been called to print the command
        assert mock_console.print.called
    
    def test_run_rejects_string_command(self):
        """Test run rejects string commands for security."""
        # Should raise TypeError or similar for string commands
        with pytest.raises((TypeError, ValueError)):
            run("echo hello")  # type: ignore - intentionally wrong type


class TestRunEdgeCases:
    """Test edge cases for run functions."""
    
    @patch('subprocess.run')
    def test_run_capture_empty_command(self, mock_run):
        """Test run_capture handles empty command list."""
        mock_run.side_effect = FileNotFoundError("No such file")
        
        # Should handle gracefully
        with pytest.raises((FileNotFoundError, CommandError, Exception)):
            run_capture([])
    
    @patch('subprocess.run')
    def test_run_capture_timeout_handling(self, mock_run):
        """Test run_capture handles timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 30)
        
        with pytest.raises((subprocess.TimeoutExpired, CommandError, Exception)):
            run_capture(["long_running_cmd"], timeout=1)
    
    @patch('subprocess.run')
    def test_run_capture_keyboard_interrupt(self, mock_run):
        """Test run_capture handles keyboard interrupt."""
        mock_run.side_effect = KeyboardInterrupt()
        
        with pytest.raises(KeyboardInterrupt):
            run_capture(["cmd"])
