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

	reader := bufio.NewReader(os.Stdin)
	for page := 0; ; page++ {
		start, end := PackagePageBounds(len(packages), page, PackagePageSize)
		printPackagePage(packages, prompt, start, end)
		printSelectionPrompt(allowAll, len(packages) > PackagePageSize && end < len(packages))

		raw, err := reader.ReadString('\n')
		if err != nil {
			return []core.Package{packages[start]}
		}
		raw = strings.TrimSpace(raw)
		if raw == "" {
			if len(packages) > PackagePageSize && end < len(packages) {
				continue
			}
			return []core.Package{packages[start]}
		}
		if strings.EqualFold(raw, "q") {
			return nil
		}
		if allowAll && strings.EqualFold(raw, "all") {
			return packages
		}
		return parsePackageSelection(raw, packages)
	}
}

func parsePackageSelection(raw string, packages []core.Package) []core.Package {
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

func printSelectionPrompt(allowAll, allowNext bool) {
	options := "Select number(s), comma-separated"
	if allowAll {
		options += ", or 'all'"
	}
	if allowNext {
		fmt.Printf("%s; Enter for more; q to cancel: ", options)
		return
	}
	fmt.Printf("%s, or q to cancel [1]: ", options)
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
