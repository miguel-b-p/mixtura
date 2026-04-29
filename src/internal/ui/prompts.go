package ui

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"

	"mixtura/internal/core"
)

func SelectPackages(packages []core.Package, prompt string, allowAll bool) []core.Package {
	if len(packages) == 0 {
		return nil
	}
	if len(packages) == 1 {
		return []core.Package{packages[0]}
	}

	DisplayPackageList(packages, prompt)
	if allowAll {
		fmt.Print("Select number(s), comma-separated, or 'all' [1]: ")
	} else {
		fmt.Print("Select number(s), comma-separated [1]: ")
	}

	reader := bufio.NewReader(os.Stdin)
	raw, err := reader.ReadString('\n')
	if err != nil {
		return []core.Package{packages[0]}
	}
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return []core.Package{packages[0]}
	}
	if allowAll && strings.EqualFold(raw, "all") {
		return packages
	}

	var selected []core.Package
	seen := map[int]bool{}
	for _, part := range strings.Split(raw, ",") {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}
		index, err := strconv.Atoi(part)
		if err != nil || index < 1 || index > len(packages) {
			Warn("Ignoring invalid selection %q", part)
			continue
		}
		if seen[index] {
			continue
		}
		seen[index] = true
		selected = append(selected, packages[index-1])
	}
	return selected
}

func Confirm(prompt string, defaultYes bool) bool {
	suffix := " [Y/n]: "
	if !defaultYes {
		suffix = " [y/N]: "
	}
	fmt.Print(prompt + suffix)

	reader := bufio.NewReader(os.Stdin)
	raw, err := reader.ReadString('\n')
	if err != nil {
		return defaultYes
	}
	raw = strings.TrimSpace(strings.ToLower(raw))
	if raw == "" {
		return defaultYes
	}
	return raw == "y" || raw == "yes" || raw == "s" || raw == "sim"
}
