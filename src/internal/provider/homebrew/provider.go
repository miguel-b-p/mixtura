package homebrew

import (
	"strings"

	"mixtura/internal/core"
	"mixtura/internal/system"
)

type Provider struct{}

func (Provider) Name() string { return "homebrew" }

func (Provider) IsAvailable() bool { return system.CommandExists("brew") }

func (Provider) Install(packages []string) error {
	args := append([]string{"brew", "install"}, packages...)
	return system.RunCommand(args...)
}

func (Provider) Uninstall(packages []string) error {
	args := append([]string{"brew", "uninstall"}, packages...)
	return system.RunCommand(args...)
}

func (Provider) Upgrade(packages []string) error {
	args := []string{"brew", "upgrade"}
	args = append(args, packages...)
	return system.RunCommand(args...)
}

func (p Provider) ListPackages() []core.Package {
	if !p.IsAvailable() {
		return nil
	}

	rc, requestedOut, _ := system.CaptureCommand("brew", "list", "--installed-on-request")
	if rc != 0 {
		return nil
	}
	requested := map[string]bool{}
	for _, line := range strings.Split(requestedOut, "\n") {
		name := strings.TrimSpace(line)
		if name != "" {
			requested[name] = true
		}
	}

	rc, versionsOut, _ := system.CaptureCommand("brew", "list", "--versions")
	if rc != 0 {
		return nil
	}

	var packages []core.Package
	for _, line := range strings.Split(strings.TrimSpace(versionsOut), "\n") {
		parts := strings.Fields(line)
		if len(parts) < 2 || !requested[parts[0]] {
			continue
		}
		packages = append(packages, core.Package{
			Name:      parts[0],
			Provider:  p.Name(),
			ID:        parts[0],
			Version:   parts[1],
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
	rc, stdout, _ := system.CaptureCommand("brew", "search", "--desc", query)
	if rc != 0 && strings.TrimSpace(stdout) == "" {
		return nil
	}

	currentType := "formula"
	var packages []core.Package
	for _, line := range strings.Split(strings.TrimSpace(stdout), "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		if strings.HasPrefix(line, "==> Formulae") {
			currentType = "formula"
			continue
		}
		if strings.HasPrefix(line, "==> Casks") {
			currentType = "cask"
			continue
		}

		name := line
		description := "No description"
		if parts := strings.SplitN(line, ": ", 2); len(parts) == 2 {
			name = parts[0]
			description = parts[1]
		}
		packages = append(packages, core.Package{
			Name:        name,
			Provider:    p.Name(),
			ID:          name,
			Version:     "unknown",
			Description: description,
			Extra:       map[string]string{"type": currentType},
		})
	}
	return packages
}

func (Provider) Clean() error {
	return system.RunCommand("brew", "cleanup")
}
