package nix

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"

	"mixtura/internal/core"
	"mixtura/internal/system"
	"mixtura/internal/ui"
)

type Provider struct{}

func (Provider) Name() string { return "nixpkgs" }

func (Provider) IsAvailable() bool { return system.CommandExists("nix") }

func (p Provider) Install(packages []string) error {
	for _, pkg := range packages {
		target := pkg
		if !strings.Contains(pkg, "#") {
			target = "nixpkgs#" + pkg
		}
		if err := system.RunCommand("nix", "profile", "add", "--impure", target); err != nil {
			return err
		}
	}
	return nil
}

func (Provider) Uninstall(packages []string) error {
	for _, pkg := range packages {
		if err := system.RunCommand("nix", "profile", "remove", pkg); err != nil {
			return err
		}
	}
	return nil
}

func (Provider) Upgrade(packages []string) error {
	if len(packages) == 0 {
		return runUpgrade([]string{"nix", "profile", "upgrade", "--impure", "--all"})
	}
	for _, pkg := range packages {
		if err := runUpgrade([]string{"nix", "profile", "upgrade", "--impure", pkg}); err != nil {
			return err
		}
	}
	return nil
}

func runUpgrade(args []string) error {
	rc, stdout, stderr := system.CaptureCommand(args...)
	if rc == 0 {
		if stdout != "" {
			fmt.Print(stdout)
		}
		return nil
	}
	if strings.Contains(stderr, "cannot write modified lock file") {
		ui.Warn("Nix could not write the lock file for a remote flake.")
		if ui.Confirm("Continue ignoring the lock file write? (--no-write-lock-file)", true) {
			retry := make([]string, 0, len(args)+1)
			for _, arg := range args {
				retry = append(retry, arg)
				if arg == "upgrade" {
					retry = append(retry, "--no-write-lock-file")
				}
			}
			return system.RunCommand(retry...)
		}
		return system.CommandError{Cmd: args, ExitCode: rc, Output: stderr}
	}
	if stdout != "" {
		fmt.Print(stdout)
	}
	if stderr != "" {
		fmt.Fprint(os.Stderr, stderr)
	}
	return system.CommandError{Cmd: args, ExitCode: rc, Output: stderr}
}

func (p Provider) ListPackages() []core.Package {
	if !p.IsAvailable() {
		return nil
	}
	rc, stdout, _ := system.CaptureCommand("nix", "profile", "list", "--json")
	if rc != 0 {
		return nil
	}

	var data struct {
		Elements map[string]struct {
			OriginalURL string   `json:"originalUrl"`
			AttrPath    string   `json:"attrPath"`
			StorePaths  []string `json:"storePaths"`
			Version     string   `json:"version"`
		} `json:"elements"`
	}
	if err := json.Unmarshal([]byte(stdout), &data); err != nil {
		return nil
	}

	packages := make([]core.Package, 0, len(data.Elements))
	for name, details := range data.Elements {
		origin := details.OriginalURL
		if origin == "" {
			origin = details.AttrPath
		}
		version := details.Version
		if version == "" && len(details.StorePaths) > 0 {
			version = versionFromStorePath(details.StorePaths[0])
		}
		if version == "" {
			version = "unknown"
		}
		packages = append(packages, core.Package{
			Name:      name,
			Provider:  p.Name(),
			ID:        name,
			Version:   version,
			Origin:    origin,
			Installed: true,
		})
	}
	return packages
}

func (p Provider) Search(query string) []core.Package {
	if !p.IsAvailable() {
		return nil
	}
	return system.CachedSearch(p.Name(), query, func() []core.Package {
		return p.searchUncached(query)
	})
}

func (p Provider) searchUncached(query string) []core.Package {
	rc, stdout, _ := system.CaptureCommand("nix", "search", "nixpkgs", query, "--json")
	if rc != 0 {
		return nil
	}

	var data map[string]struct {
		Description string `json:"description"`
		Version     string `json:"version"`
	}
	if err := json.Unmarshal([]byte(stdout), &data); err != nil {
		return nil
	}

	packages := make([]core.Package, 0, len(data))
	for key, details := range data {
		name := key
		if idx := strings.LastIndex(key, "."); idx >= 0 {
			name = key[idx+1:]
		}
		version := details.Version
		if version == "" {
			version = "unknown"
		}
		packages = append(packages, core.Package{
			Name:        name,
			Provider:    p.Name(),
			ID:          key,
			Version:     version,
			Description: details.Description,
		})
	}
	return packages
}

func (Provider) Clean() error {
	return system.RunCommand("nix-collect-garbage", "-d")
}

func versionFromStorePath(path string) string {
	parts := strings.Split(strings.TrimRight(path, "/"), "/")
	if len(parts) == 0 {
		return "unknown"
	}
	filename := parts[len(parts)-1]
	dashParts := strings.Split(filename, "-")
	if len(dashParts) < 2 {
		return "unknown"
	}
	fullName := strings.Join(dashParts[1:], "-")
	for i := len(fullName) - 2; i >= 0; i-- {
		if fullName[i] == '-' && fullName[i+1] >= '0' && fullName[i+1] <= '9' {
			return fullName[i+1:]
		}
	}
	return "unknown"
}
