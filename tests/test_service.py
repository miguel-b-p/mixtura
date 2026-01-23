
import pytest
from unittest.mock import MagicMock, patch
from mixtura.core.service import PackageService
from mixtura.core.package import Package, PackageSpec

class TestPackageService:
    @pytest.fixture
    def mock_providers(self):
        with patch('mixtura.core.service.get_all_providers') as mock:
            yield mock

    @pytest.fixture
    def mock_available(self):
        with patch('mixtura.core.service.get_available_providers') as mock:
            yield mock
            
    @pytest.fixture
    def mock_get_provider(self):
        with patch('mixtura.core.service.get_provider') as mock:
            yield mock

    def test_search(self, mock_available):
        mock_nix = MagicMock()
        mock_nix.search.return_value = [Package("git", "nixpkgs", "git")]
        mock_available.return_value = {"nixpkgs": mock_nix}
        
        service = PackageService()
        results = service.search("git")
        
        assert len(results) == 1
        assert results[0].name == "git"
        mock_nix.search.assert_called_with("git")

    def test_install_specific(self, mock_get_provider):
        mock_nix = MagicMock()
        mock_nix.is_available.return_value = True
        mock_get_provider.return_value = mock_nix
        
        service = PackageService()
        specs = [PackageSpec("vim", "nixpkgs")]
        results = service.install(specs)
        
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].provider == "nixpkgs"
        mock_nix.install.assert_called_with(["vim"])

    def test_install_missing_provider(self, mock_get_provider):
        service = PackageService()
        specs = [PackageSpec("vim", None)]
        results = service.install(specs)
        
        assert len(results) == 1
        assert results[0].success is False
        assert "Provider not specified" in results[0].message
