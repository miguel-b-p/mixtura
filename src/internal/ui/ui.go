package ui

import (
	"bufio"
	"fmt"
	"os"
	"strings"
	"time"

	"mixtura/internal/core"
)

const PackagePageSize = 10

const logo = `
    ▙▗▌ ▗      ▐
    ▌▘▌ ▄  ▚▗▘ ▜▀  ▌ ▌ ▙▀▖ ▝▀▖
    ▌ ▌ ▐  ▗▚  ▐ ▖ ▌ ▌ ▌   ▞▀▌
    ▘ ▘ ▀▘ ▘ ▘  ▀  ▝▀▘ ▘   ▝▀▘
`

func PrintLogo() {
	fmt.Print(logo)
}

func Warn(format string, args ...any) {
	fmt.Printf("!  "+format+"\n", args...)
}

func Error(format string, args ...any) {
	fmt.Fprintf(os.Stderr, "x  Error: "+format+"\n", args...)
}

func WithSpinner[T any](message string, work func() T) T {
	if !isTerminal(os.Stdout) {
		fmt.Println(message + "...")
		return work()
	}

	result := make(chan T, 1)
	go func() {
		result <- work()
	}()

	frames := []rune{'|', '/', '-', '\\'}
	ticker := time.NewTicker(100 * time.Millisecond)
	defer ticker.Stop()

	i := 0
	for {
		select {
		case value := <-result:
			fmt.Print("\r\033[K")
			return value
		case <-ticker.C:
			fmt.Printf("\r%c %s", frames[i%len(frames)], message)
			i++
		}
	}
}

func isTerminal(file *os.File) bool {
	info, err := file.Stat()
	if err != nil {
		return false
	}
	return info.Mode()&os.ModeCharDevice != 0
}

func DisplayPackageList(packages []core.Package, title string) {
	fmt.Println(title)
	for i, pkg := range packages {
		printPackage(i+1, pkg)
	}
}

func DisplayPackageListPaginated(packages []core.Package, title string) {
	if len(packages) <= PackagePageSize {
		DisplayPackageList(packages, title)
		return
	}
	reader := bufio.NewReader(os.Stdin)
	for page := 0; ; page++ {
		start, end := PackagePageBounds(len(packages), page, PackagePageSize)
		printPackagePage(packages, title, start, end)
		if end >= len(packages) {
			return
		}
		if !isTerminal(os.Stdin) || !isTerminal(os.Stdout) {
			fmt.Printf("Showing first %d of %d results. Run in a terminal to page through all results.\n", end, len(packages))
			return
		}
		fmt.Print("Press Enter for more, or q to stop: ")
		raw, err := reader.ReadString('\n')
		if err != nil || strings.EqualFold(strings.TrimSpace(raw), "q") {
			return
		}
	}
}

func PackagePageBounds(total, page, pageSize int) (int, int) {
	if pageSize <= 0 {
		pageSize = PackagePageSize
	}
	start := page * pageSize
	if start > total {
		start = total
	}
	end := start + pageSize
	if end > total {
		end = total
	}
	return start, end
}

func printPackagePage(packages []core.Package, title string, start, end int) {
	fmt.Printf("%s (%d-%d of %d)\n", title, start+1, end, len(packages))
	for i := start; i < end; i++ {
		printPackage(i+1, packages[i])
	}
}

func printPackage(index int, pkg core.Package) {
	extra := pkg.Version
	if extra == "" || extra == "unknown" {
		extra = pkg.ID
	}
	if pkg.Description != "" {
		fmt.Printf(" %d. %s (%s %s) - %s\n", index, pkg.Name, pkg.Provider, extra, pkg.Description)
	} else {
		fmt.Printf(" %d. %s (%s %s)\n", index, pkg.Name, pkg.Provider, extra)
	}
}

func DisplayInstalledPackages(packages []core.Package, provider string) {
	fmt.Printf("%s installed packages\n", provider)
	if len(packages) == 0 {
		fmt.Println("  No packages found.")
		return
	}
	for _, pkg := range packages {
		fmt.Printf("  - %s (%s)\n", pkg.Name, pkg.Version)
	}
}

func DisplayOperationResults(results []core.OperationResult, successTitle, failureTitle string) {
	hasFailure := false
	for _, result := range results {
		if !result.Success {
			hasFailure = true
			break
		}
	}
	if hasFailure {
		fmt.Println(failureTitle)
	} else {
		fmt.Println(successTitle)
	}

	for _, result := range results {
		marker := "OK"
		if !result.Success {
			marker = "FAIL"
		}
		fmt.Printf("  [%s] %s: %s\n", marker, result.Provider, result.Message)
	}
}
