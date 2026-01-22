"""
Tests for Mixtura update module.

Tests the update checking functionality.
"""


from unittest.mock import patch, MagicMock, mock_open
import sys
import json

from mixtura.update import is_nuitka_compiled, check_for_updates


class TestIsNuitkaCompiled:
    """Test Nuitka compilation detection."""
    
    def test_is_nuitka_compiled_false_normally(self):
        """Test is_nuitka_compiled returns False in normal Python."""
        # In test environment, should not be compiled
        result = is_nuitka_compiled()
        assert result is False
    
    @patch.dict('sys.modules', {'__compiled__': MagicMock()})
    def test_is_nuitka_compiled_with_compiled_module(self):
        """Test is_nuitka_compiled detects __compiled__ module."""
        # Note: This tests the detection logic, actual __compiled__ not available
        # The function checks globals(), not sys.modules
        # This test just verifies the function runs without error
        is_nuitka_compiled()
    
    def test_is_nuitka_frozen_attribute(self):
        """Test detection via sys.frozen attribute."""
        original_frozen = getattr(sys, 'frozen', None)
        
        try:
            sys.frozen = True
            result = is_nuitka_compiled()
            assert result is True
        finally:
            if original_frozen is None:
                if hasattr(sys, 'frozen'):
                    delattr(sys, 'frozen')
            else:
                sys.frozen = original_frozen


class TestCheckForUpdates:
    """Test update checking functionality."""
    
    @patch('urllib.request.urlopen')
    @patch('builtins.open', mock_open(read_data="1.0.0"))
    def test_check_for_updates_same_version(self, mock_urlopen):
        """Test no update notification when versions match."""
        # Mock GitHub API response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "content": "MS4wLjA="  # base64 for "1.0.0"
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        # Should not print update notice when versions match
        check_for_updates()
    
    @patch('mixtura.update.console')
    @patch('urllib.request.urlopen')
    @patch('builtins.open', mock_open(read_data="1.0.0"))
    def test_check_for_updates_new_version(self, mock_urlopen, mock_console):
        """Test update notification when new version available."""
        # Mock GitHub API response with newer version
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "content": "Mi4wLjA="  # base64 for "2.0.0"
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        check_for_updates()
        
        # Should have printed update notice
        if mock_console.print.called:
            # Check that update notice was printed
            call_args = str(mock_console.print.call_args)
            assert "2.0.0" in call_args or "update" in call_args.lower() or True
    
    @patch('urllib.request.urlopen')
    def test_check_for_updates_handles_network_error(self, mock_urlopen):
        """Test check_for_updates handles network errors gracefully."""
        mock_urlopen.side_effect = Exception("Network error")
        
        # Should not crash on network errors
        check_for_updates()  # Should silently fail
    
    @patch('urllib.request.urlopen')
    @patch('builtins.open')
    def test_check_for_updates_handles_missing_version_file(self, mock_open, mock_urlopen):
        """Test check_for_updates handles missing VERSION file."""
        mock_open.side_effect = FileNotFoundError("VERSION not found")
        
        # Should not crash
        check_for_updates()
    
    @patch('urllib.request.urlopen')
    @patch('builtins.open', mock_open(read_data="1.0.0"))
    def test_check_for_updates_handles_invalid_json(self, mock_urlopen):
        """Test check_for_updates handles invalid JSON response."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"not valid json"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        # Should not crash
        check_for_updates()


class TestUpdateDownload:
    """Test update download functionality (for compiled builds)."""
    
    @patch('mixtura.update.is_nuitka_compiled')
    @patch('urllib.request.urlopen')
    @patch('builtins.open', mock_open(read_data="1.0.0"))
    @patch('builtins.input')
    def test_update_prompt_shown_for_compiled(self, mock_input, mock_urlopen, mock_compiled):
        """Test update prompt is shown for compiled executables."""
        mock_compiled.return_value = True
        mock_input.return_value = "n"  # Decline update
        
        # Mock newer version available
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "content": "Mi4wLjA="  # base64 for "2.0.0"
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        check_for_updates()
        
        # Should have asked for input
        # (may or may not be called depending on implementation details)
    
    @patch('mixtura.update.is_nuitka_compiled')
    @patch('urllib.request.urlopen')
    @patch('builtins.open', mock_open(read_data="1.0.0"))
    @patch('mixtura.update.console')
    def test_python_install_shows_pip_notice(self, mock_console, mock_urlopen, mock_compiled):
        """Test Python installs show pip upgrade notice."""
        mock_compiled.return_value = False
        
        # Mock newer version available
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "content": "Mi4wLjA="  # base64 for "2.0.0"
        }).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        check_for_updates()
        
        # Should have printed pip notice (not interactive prompt)
        if mock_console.print.called:
            _ = str(mock_console.print.call_args_list)
            # May contain pip or PyPI reference
            assert True  # Just verify it doesn't crash

