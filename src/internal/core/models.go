package core

import (
	"fmt"
	"strings"
)

type Package struct {
	Name        string            `json:"name"`
	Provider    string            `json:"provider"`
	ID          string            `json:"id"`
	Version     string            `json:"version"`
	Description string            `json:"description"`
	Installed   bool              `json:"installed"`
	Origin      string            `json:"origin"`
	Extra       map[string]string `json:"extra,omitempty"`
}

func (p Package) InstallID() string {
	if p.ID != "" {
		return p.ID
	}
	return p.Name
}

type PackageSpec struct {
	Name     string
	Provider string
	Version  string
}

func ParsePackageSpec(raw string) (PackageSpec, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return PackageSpec{}, fmt.Errorf("package specification cannot be empty")
	}

	if strings.Contains(raw, "#") {
		parts := strings.SplitN(raw, "#", 2)
		provider := strings.TrimSpace(parts[0])
		name := strings.TrimSpace(parts[1])
		if provider == "" || name == "" {
			return PackageSpec{}, fmt.Errorf("invalid package specification %q", raw)
		}
		return PackageSpec{Name: name, Provider: provider}, nil
	}

	return PackageSpec{Name: raw}, nil
}

type OperationResult struct {
	Provider string
	Success  bool
	Message  string
}
