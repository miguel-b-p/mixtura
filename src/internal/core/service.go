package core

import (
	"fmt"
	"strings"
	"sync"
)

type PackageService struct {
	registry Registry
}

func NewPackageService(registry Registry) PackageService {
	return PackageService{registry: registry}
}

func (s PackageService) Search(query string) []Package {
	available := s.registry.Available()
	results := make([]Package, 0)
	resultCh := make(chan []Package, len(available))
	var wg sync.WaitGroup

	for _, provider := range available {
		wg.Add(1)
		go func(provider Provider) {
			defer wg.Done()
			resultCh <- provider.Search(query)
		}(provider)
	}

	wg.Wait()
	close(resultCh)
	for packages := range resultCh {
		results = append(results, packages...)
	}
	return results
}

func (s PackageService) Install(specs []PackageSpec) []OperationResult {
	grouped := map[string][]string{}
	var results []OperationResult
	for _, spec := range specs {
		if spec.Provider == "" {
			results = append(results, OperationResult{"unknown", false, fmt.Sprintf("Cannot install %q: provider not specified", spec.Name)})
			continue
		}
		grouped[spec.Provider] = append(grouped[spec.Provider], spec.Name)
	}
	return append(results, s.runGrouped(grouped, func(provider Provider, packages []string) error {
		return provider.Install(packages)
	}, "Successfully installed")...)
}

func (s PackageService) Remove(specs []PackageSpec) []OperationResult {
	grouped := map[string][]string{}
	var results []OperationResult
	for _, spec := range specs {
		if spec.Provider == "" {
			results = append(results, OperationResult{"unknown", false, fmt.Sprintf("Provider missing for removal of %s", spec.Name)})
			continue
		}
		grouped[spec.Provider] = append(grouped[spec.Provider], spec.Name)
	}
	return append(results, s.runGrouped(grouped, func(provider Provider, packages []string) error {
		return provider.Uninstall(packages)
	}, "Removal successful")...)
}

func (s PackageService) Upgrade(specs []PackageSpec) []OperationResult {
	if len(specs) == 0 {
		grouped := map[string][]string{}
		for name := range s.registry.Available() {
			grouped[name] = nil
		}
		return s.runGrouped(grouped, func(provider Provider, packages []string) error {
			return provider.Upgrade(packages)
		}, "Upgrade successful")
	}

	grouped := map[string][]string{}
	for _, spec := range specs {
		if spec.Provider != "" {
			grouped[spec.Provider] = append(grouped[spec.Provider], spec.Name)
			continue
		}
		if _, ok := s.registry.Get(spec.Name); ok {
			grouped[spec.Name] = nil
		}
	}
	return s.runGrouped(grouped, func(provider Provider, packages []string) error {
		return provider.Upgrade(packages)
	}, "Upgrade successful")
}

func (s PackageService) runGrouped(grouped map[string][]string, fn func(Provider, []string) error, successPrefix string) []OperationResult {
	results := make([]OperationResult, 0, len(grouped))
	resultCh := make(chan OperationResult, len(grouped))
	var wg sync.WaitGroup

	for providerName, packages := range grouped {
		provider, ok := s.registry.Get(providerName)
		if !ok || !provider.IsAvailable() {
			results = append(results, OperationResult{providerName, false, "Provider unavailable"})
			continue
		}
		wg.Add(1)
		go func(provider Provider, packages []string) {
			defer wg.Done()
			if err := fn(provider, packages); err != nil {
				resultCh <- OperationResult{provider.Name(), false, err.Error()}
				return
			}
			message := successPrefix
			if len(packages) > 0 {
				message = fmt.Sprintf("%s: %s", successPrefix, strings.Join(packages, ", "))
			}
			resultCh <- OperationResult{provider.Name(), true, message}
		}(provider, packages)
	}

	wg.Wait()
	close(resultCh)
	for result := range resultCh {
		results = append(results, result)
	}
	return results
}
