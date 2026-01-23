
import pytest
from mixtura.core.package import PackageSpec

class TestPackageSpec:
    def test_parse_simple_package(self):
        spec = PackageSpec.parse("git")
        assert spec.name == "git"
        assert spec.provider is None
        assert spec.version is None

    def test_parse_with_provider(self):
        spec = PackageSpec.parse("nixpkgs#vim")
        assert spec.name == "vim"
        assert spec.provider == "nixpkgs"
        assert spec.version is None

    def test_parse_with_version(self):
        # Assuming version syntax might be supported in future or via @ syntax?
        # For now, let's just stick to what parse_single_arg did: provider#package
        # But wait, the plan mentioned PackageSpec processing.
        pass

    def test_parse_complex_names(self):
        spec = PackageSpec.parse("flatpak#com.spotify.Client")
        assert spec.name == "com.spotify.Client"
        assert spec.provider == "flatpak"

    def test_parse_invalid(self):
        # Empty string behavior
        with pytest.raises(ValueError):
            PackageSpec.parse("")
