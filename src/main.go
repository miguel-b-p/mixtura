package main

import (
	"fmt"
	"os"
	"strings"

	"mixtura/internal/core"
	"mixtura/internal/provider/flatpak"
	"mixtura/internal/provider/homebrew"
	"mixtura/internal/provider/nix"
	"mixtura/internal/system"
	"mixtura/internal/ui"
)

func main() {
	registry := providerRegistry()
	service := core.NewPackageService(registry)
	args := os.Args[1:]
	if len(args) == 0 {
		usage()
		return
	}

	switch args[0] {
	case "-h", "--help", "help":
		usage()
	case "-v", "--version", "version":
		fmt.Printf("Mixtura version %s\n", version())
	case "add":
		system.CheckForUpdates(version())
		exitIfFailed(cmdAdd(service, args[1:]))
	case "remove":
		system.CheckForUpdates(version())
		exitIfFailed(cmdRemove(service, args[1:]))
	case "upgrade":
		system.CheckForUpdates(version())
		exitIfFailed(cmdUpgrade(service, args[1:]))
	case "list":
		system.CheckForUpdates(version())
		exitIfFailed(cmdList(registry, args[1:]))
	case "search":
		system.CheckForUpdates(version())
		exitIfFailed(cmdSearch(registry, service, args[1:]))
	case "clean":
		system.CheckForUpdates(version())
		exitIfFailed(cmdClean(registry, args[1:]))
	case "info":
		system.CheckForUpdates(version())
		cmdInfo(registry)
	default:
		ui.Error("Unknown command %q", args[0])
		usage()
		os.Exit(2)
	}
}

func providerRegistry() core.Registry {
	return core.NewRegistry(
		nix.Provider{},
		flatpak.Provider{},
		homebrew.Provider{},
	)
}

func usage() {
	ui.PrintLogo()
	fmt.Println("Mixtura - Mixed together. Running everywhere.")
	fmt.Println()
	fmt.Println("Usage:")
	fmt.Println("  mixtura add [--yes] [--all] <packages...>")
	fmt.Println("  mixtura remove [--yes] [--all] <packages...>")
	fmt.Println("  mixtura upgrade [packages-or-providers...]")
	fmt.Println("  mixtura list [provider]")
	fmt.Println("  mixtura search [--all] <queries...>")
	fmt.Println("  mixtura clean [providers...]")
	fmt.Println("  mixtura info")
}

func cmdAdd(service core.PackageService, args []string) bool {
	ui.PrintLogo()
	flags, packages := splitFlags(args)
	autoYes := flags["yes"] || flags["y"]
	if len(packages) == 0 {
		ui.Warn("No package specified. Usage: mixtura add <package...>")
		return false
	}

	var specs []core.PackageSpec
	for _, arg := range packages {
		for _, item := range splitComma(arg) {
			spec, err := core.ParsePackageSpec(item)
			if err != nil {
				ui.Error("%v", err)
				continue
			}
			if spec.Provider != "" {
				specs = append(specs, spec)
				continue
			}

			results := ui.WithSpinner(fmt.Sprintf("Searching for %q across available providers", spec.Name), func() []core.Package {
				return service.Search(spec.Name)
			})
			results = filterExact(results, spec.Name, flags["all"])
			if len(results) == 0 {
				ui.Warn("No packages found for %q", spec.Name)
				continue
			}
			selected := []core.Package{results[0]}
			if len(results) > 1 && !autoYes {
				selected = ui.SelectPackages(results, fmt.Sprintf("Found matches for %q", spec.Name), false)
			}
			if len(selected) == 0 {
				continue
			}
			for _, pkg := range selected {
				specs = append(specs, core.PackageSpec{Name: pkg.InstallID(), Provider: pkg.Provider})
			}
		}
	}

	if len(specs) == 0 {
		ui.Warn("No packages selected for installation.")
		return false
	}
	results := service.Install(specs)
	ui.DisplayOperationResults(results, "Installation finished.", "Installation completed with errors.")
	return allResultsSuccessful(results)
}

func cmdRemove(service core.PackageService, args []string) bool {
	ui.PrintLogo()
	flags, packages := splitFlags(args)
	autoYes := flags["yes"] || flags["y"]
	if len(packages) == 0 {
		ui.Warn("No package specified. Usage: mixtura remove <package...>")
		return false
	}

	var specs []core.PackageSpec
	for _, arg := range packages {
		for _, item := range splitComma(arg) {
			spec, err := core.ParsePackageSpec(item)
			if err != nil {
				ui.Error("%v", err)
				continue
			}
			if spec.Provider != "" {
				specs = append(specs, spec)
				continue
			}

			matches := ui.WithSpinner(fmt.Sprintf("Searching installed packages for %q", spec.Name), func() []core.Package {
				return installedMatches(spec.Name, flags["all"])
			})
			if len(matches) == 0 {
				ui.Warn("No installed package found matching %q", spec.Name)
				continue
			}
			selected := []core.Package{matches[0]}
			if len(matches) > 1 && !autoYes {
				selected = ui.SelectPackages(matches, fmt.Sprintf("Installed matches for %q", spec.Name), true)
			}
			if len(selected) == 0 {
				continue
			}
			for _, pkg := range selected {
				specs = append(specs, core.PackageSpec{Name: pkg.InstallID(), Provider: pkg.Provider})
			}
		}
	}

	if len(specs) == 0 {
		ui.Warn("No packages selected for removal.")
		return false
	}
	results := service.Remove(specs)
	ui.DisplayOperationResults(results, "Removal finished.", "Removal completed with errors.")
	return allResultsSuccessful(results)
}

func cmdUpgrade(service core.PackageService, args []string) bool {
	ui.PrintLogo()
	var specs []core.PackageSpec
	for _, arg := range args {
		spec, err := core.ParsePackageSpec(arg)
		if err != nil {
			ui.Error("%v", err)
			continue
		}
		specs = append(specs, spec)
	}
	results := service.Upgrade(specs)
	ui.DisplayOperationResults(results, "Upgrade finished.", "Upgrade completed with errors.")
	return allResultsSuccessful(results)
}

func cmdList(registry core.Registry, args []string) bool {
	ui.PrintLogo()
	if len(args) > 0 {
		provider, ok := registry.Get(args[0])
		if !ok {
			ui.Warn("Unknown provider %q", args[0])
			return false
		}
		packages := ui.WithSpinner(fmt.Sprintf("Fetching packages from %s", provider.Name()), provider.ListPackages)
		ui.DisplayInstalledPackages(packages, provider.Name())
		return true
	}
	available := registry.Available()
	if len(available) == 0 {
		ui.Warn("No available package managers found.")
		return false
	}
	for _, name := range registry.Order() {
		provider, ok := available[name]
		if !ok {
			continue
		}
		packages := ui.WithSpinner(fmt.Sprintf("Fetching packages from %s", provider.Name()), provider.ListPackages)
		ui.DisplayInstalledPackages(packages, provider.Name())
	}
	return true
}

func cmdSearch(registry core.Registry, service core.PackageService, args []string) bool {
	ui.PrintLogo()
	flags, queries := splitFlags(args)
	if len(queries) == 0 {
		ui.Warn("No search query specified. Usage: mixtura search <query...>")
		return false
	}
	foundAny := false
	for _, query := range queries {
		spec, err := core.ParsePackageSpec(query)
		if err != nil {
			ui.Error("%v", err)
			continue
		}
		var results []core.Package
		if spec.Provider != "" {
			if provider, ok := registry.Get(spec.Provider); ok {
				results = ui.WithSpinner(fmt.Sprintf("Searching %s for %q", provider.Name(), spec.Name), func() []core.Package {
					return provider.Search(spec.Name)
				})
			} else {
				ui.Warn("Unknown provider %q", spec.Provider)
				continue
			}
		} else {
			results = ui.WithSpinner(fmt.Sprintf("Searching for %q across available providers", spec.Name), func() []core.Package {
				return service.Search(spec.Name)
			})
		}
		results = filterExact(results, spec.Name, flags["all"])
		if len(results) == 0 {
			ui.Warn("No results for %q", query)
			continue
		}
		ui.DisplayPackageListPaginated(results, fmt.Sprintf("Matches for %q", query))
		foundAny = true
	}
	return foundAny
}

func cmdClean(registry core.Registry, args []string) bool {
	ui.PrintLogo()
	targets := args
	if len(targets) == 0 {
		available := registry.Available()
		if len(available) == 0 {
			ui.Warn("No available package managers found.")
			return false
		}
		for _, name := range registry.Order() {
			if _, ok := available[name]; ok {
				targets = append(targets, name)
			}
		}
	}
	var results []core.OperationResult
	for _, name := range targets {
		provider, ok := registry.Get(name)
		if !ok || !provider.IsAvailable() {
			results = append(results, core.OperationResult{Provider: name, Success: false, Message: "Provider unavailable"})
			continue
		}
		if err := provider.Clean(); err != nil {
			results = append(results, core.OperationResult{Provider: name, Success: false, Message: err.Error()})
		} else {
			results = append(results, core.OperationResult{Provider: name, Success: true, Message: "Cleaned"})
		}
	}
	ui.DisplayOperationResults(results, "Clean finished.", "Clean completed with errors.")
	return allResultsSuccessful(results)
}

func cmdInfo(registry core.Registry) {
	ui.PrintLogo()
	statuses := ui.WithSpinner("Checking package managers", func() map[string]string {
		statuses := map[string]string{}
		for _, name := range registry.Order() {
			provider, _ := registry.Get(name)
			status := "not installed"
			if provider.IsAvailable() {
				status = "available"
			}
			statuses[name] = status
		}
		return statuses
	})
	fmt.Println("Available Package Managers:")
	for _, name := range registry.Order() {
		fmt.Printf("  - %s (%s)\n", name, statuses[name])
	}
}

func exitIfFailed(ok bool) {
	if !ok {
		os.Exit(1)
	}
}

func allResultsSuccessful(results []core.OperationResult) bool {
	if len(results) == 0 {
		return false
	}
	for _, result := range results {
		if !result.Success {
			return false
		}
	}
	return true
}

func splitFlags(args []string) (map[string]bool, []string) {
	flags := map[string]bool{}
	var positional []string
	for _, arg := range args {
		switch arg {
		case "--all", "-a":
			flags["all"] = true
			flags["a"] = true
		case "--yes", "-y":
			flags["yes"] = true
			flags["y"] = true
		default:
			positional = append(positional, arg)
		}
	}
	return flags, positional
}

func splitComma(raw string) []string {
	var items []string
	for _, item := range strings.Split(raw, ",") {
		item = strings.TrimSpace(item)
		if item != "" {
			items = append(items, item)
		}
	}
	return items
}

func filterExact(packages []core.Package, query string, showAll bool) []core.Package {
	if showAll {
		return packages
	}
	var exact []core.Package
	for _, pkg := range packages {
		if strings.EqualFold(pkg.Name, query) {
			exact = append(exact, pkg)
		}
	}
	if len(exact) > 0 {
		return exact
	}
	return packages
}

func installedMatches(query string, showAll bool) []core.Package {
	var matches []core.Package
	for _, provider := range providerRegistry().Available() {
		for _, pkg := range provider.ListPackages() {
			if showAll || strings.Contains(strings.ToLower(pkg.Name), strings.ToLower(query)) {
				matches = append(matches, pkg)
			}
		}
	}
	return filterExact(matches, query, showAll)
}
