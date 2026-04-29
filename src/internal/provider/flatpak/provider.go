package flatpak

import (
	"strings"

	"mixtura/internal/core"
	"mixtura/internal/system"
)

type Provider struct{}

func (Provider) Name() string { return "flatpak" }

func (Provider) IsAvailable() bool { return system.CommandExists("flatpak") }

func (Provider) Install(packages []string) error {
	args := append([]string{"flatpak", "install", "-y"}, packages...)
	return system.RunCommand(args...)
}

func (Provider) Uninstall(packages []string) error {
	for _, pkg := range packages {
		if err := system.RunCommand("flatpak", "uninstall", pkg); err != nil {
			return err
		}
	}
	return nil
}

func (Provider) Upgrade(packages []string) error {
	args := []string{"flatpak", "update", "-y"}
	args = append(args, packages...)
	return system.RunCommand(args...)
}

func (p Provider) ListPackages() []core.Package {
	if !p.IsAvailable() {
		return nil
	}
	rc, stdout, _ := system.CaptureCommand("flatpak", "list", "--app", "--columns=name,application,description,version")
	if rc != 0 {
		return nil
	}
	return p.ParseRows(stdout, true)
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
	rc, stdout, _ := system.CaptureCommand("flatpak", "search", query, "--columns=name,application,description,version")
	if rc != 0 {
		return nil
	}
	return p.ParseRows(stdout, false)
}

func (p Provider) ParseRows(stdout string, installed bool) []core.Package {
	var packages []core.Package
	for _, line := range strings.Split(strings.TrimSpace(stdout), "\n") {
		line = strings.TrimSpace(line)
		lowerLine := strings.ToLower(line)
		if line == "" || strings.Contains(line, "Application ID") || strings.Contains(lowerLine, "no matches") || strings.Contains(lowerLine, "no results") {
			continue
		}
		parts := strings.Split(line, "\t")
		if len(parts) < 2 {
			parts = splitFallback(line)
		}
		if len(parts) < 2 {
			continue
		}
		description := ""
		if len(parts) > 2 {
			description = parts[2]
		}
		version := "unknown"
		if len(parts) > 3 && parts[3] != "" {
			version = parts[3]
		}
		packages = append(packages, core.Package{
			Name:        parts[0],
			Provider:    p.Name(),
			ID:          parts[1],
			Version:     version,
			Description: description,
			Installed:   installed,
		})
	}
	return packages
}

func splitFallback(line string) []string {
	fields := strings.Fields(line)
	if len(fields) < 2 {
		return nil
	}
	appIDIndex := -1
	for i, field := range fields {
		if strings.Count(field, ".") >= 2 {
			appIDIndex = i
			break
		}
	}
	if appIDIndex <= 0 {
		return nil
	}

	name := strings.Join(fields[:appIDIndex], " ")
	appID := fields[appIDIndex]
	description := ""
	version := "unknown"
	if appIDIndex+1 < len(fields) {
		description = strings.Join(fields[appIDIndex+1:], " ")
	}
	return []string{name, appID, description, version}
}

func (Provider) Clean() error {
	return system.RunCommand("flatpak", "uninstall", "--unused", "-y")
}
