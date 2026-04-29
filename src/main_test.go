package main

import (
	"testing"

	"mixtura/internal/core"
	"mixtura/internal/provider/flatpak"
	"mixtura/internal/system"
)

func TestParsePackageSpec(t *testing.T) {
	spec, err := core.ParsePackageSpec("nixpkgs#vim")
	if err != nil {
		t.Fatalf("ParsePackageSpec returned error: %v", err)
	}
	if spec.Provider != "nixpkgs" || spec.Name != "vim" {
		t.Fatalf("unexpected spec: %#v", spec)
	}

	spec, err = core.ParsePackageSpec("git")
	if err != nil {
		t.Fatalf("ParsePackageSpec returned error: %v", err)
	}
	if spec.Provider != "" || spec.Name != "git" {
		t.Fatalf("unexpected spec: %#v", spec)
	}
}

func TestParsePackageSpecRejectsIncompleteProviderSpec(t *testing.T) {
	for _, input := range []string{"", "nixpkgs#", "#vim"} {
		if _, err := core.ParsePackageSpec(input); err == nil {
			t.Fatalf("expected %q to be rejected", input)
		}
	}
}

func TestFilterExact(t *testing.T) {
	packages := []core.Package{
		{Name: "vim-airline"},
		{Name: "vim"},
	}
	filtered := filterExact(packages, "vim", false)
	if len(filtered) != 1 || filtered[0].Name != "vim" {
		t.Fatalf("unexpected filtered packages: %#v", filtered)
	}

	all := filterExact(packages, "vim", true)
	if len(all) != 2 {
		t.Fatalf("expected showAll to keep all packages, got %#v", all)
	}
}

func TestSplitFlags(t *testing.T) {
	flags, positional := splitFlags([]string{"--yes", "-a", "vim", "--unknown"})
	if !flags["yes"] || !flags["all"] {
		t.Fatalf("expected yes/all flags, got %#v", flags)
	}
	if len(positional) != 2 || positional[0] != "vim" || positional[1] != "--unknown" {
		t.Fatalf("unexpected positional args: %#v", positional)
	}
}

func TestProviderRegistryOrder(t *testing.T) {
	got := providerRegistry().Order()
	want := []string{"nixpkgs", "flatpak", "homebrew"}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("provider order = %#v, want %#v", got, want)
		}
	}
}

func TestFlatpakParseRowsIgnoresNoMatches(t *testing.T) {
	provider := flatpak.Provider{}
	if got := provider.ParseRows("No matches found\n", false); len(got) != 0 {
		t.Fatalf("expected no packages, got %#v", got)
	}
}

func TestFlatpakFallbackParser(t *testing.T) {
	provider := flatpak.Provider{}
	got := provider.ParseRows("Visual Studio Code com.visualstudio.code Code editor\n", false)
	if len(got) != 1 {
		t.Fatalf("expected one package, got %#v", got)
	}
	if got[0].Name != "Visual Studio Code" || got[0].ID != "com.visualstudio.code" {
		t.Fatalf("unexpected package: %#v", got[0])
	}
}

func TestVersion(t *testing.T) {
	if version() == "" || version() == "unknown" {
		t.Fatalf("expected embedded version, got %q", version())
	}
}

func TestCompareVersions(t *testing.T) {
	tests := []struct {
		left  string
		right string
		want  int
	}{
		{"1.31", "1.30", 1},
		{"1.30", "1.30", 0},
		{"1.29", "1.30", -1},
		{"2.0", "1.99", 1},
		{"1.30.1", "1.30", 1},
	}

	for _, test := range tests {
		if got := system.CompareVersions(test.left, test.right); got != test.want {
			t.Fatalf("CompareVersions(%q, %q) = %d, want %d", test.left, test.right, got, test.want)
		}
	}
}

func TestFriendlyNixPackageNotFound(t *testing.T) {
	err := system.CommandError{
		Cmd:      []string{"nix", "profile", "add", "--impure", "nixpkgs#nope"},
		ExitCode: 1,
		Output:   "error: flake 'flake:nixpkgs' does not provide attribute 'legacyPackages.x86_64-linux.nope'",
	}
	got := err.Error()
	if got != `Package "nope" was not found in nixpkgs. Try `+"`mixtura search nope`"+` to find the correct name.` {
		t.Fatalf("unexpected friendly error: %q", got)
	}
}

func TestFriendlyNixDaemonUnavailable(t *testing.T) {
	err := system.CommandError{
		Cmd:      []string{"nix", "profile", "add", "--impure", "nixpkgs#hello"},
		ExitCode: 1,
		Output:   "error: cannot connect to socket at '/var/nix/daemon-socket/socket': Operation not permitted",
	}
	got := err.Error()
	want := "Nix is installed, but Mixtura could not reach the Nix daemon. Check whether the daemon is running and whether your user has permission to access it."
	if got != want {
		t.Fatalf("unexpected friendly error: %q", got)
	}
}
