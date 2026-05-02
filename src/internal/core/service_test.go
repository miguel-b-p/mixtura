package core

import (
	"testing"
	"time"
)

type fakeProvider struct {
	name    string
	delay   time.Duration
	results []Package
}

func (p fakeProvider) Name() string             { return p.name }
func (p fakeProvider) IsAvailable() bool        { return true }
func (p fakeProvider) Install([]string) error   { return nil }
func (p fakeProvider) Uninstall([]string) error { return nil }
func (p fakeProvider) Upgrade([]string) error   { return nil }
func (p fakeProvider) ListPackages() []Package  { return nil }
func (p fakeProvider) Clean() error             { return nil }

func (p fakeProvider) Search(string) []Package {
	time.Sleep(p.delay)
	return p.results
}

func TestSearchReturnsResultsInProviderOrder(t *testing.T) {
	service := NewPackageService(NewRegistry(
		fakeProvider{name: "slow", delay: 20 * time.Millisecond, results: []Package{{Name: "slow-result"}}},
		fakeProvider{name: "fast", results: []Package{{Name: "fast-result"}}},
	))

	got := service.Search("vim")
	if len(got) != 2 {
		t.Fatalf("expected two results, got %#v", got)
	}
	if got[0].Name != "slow-result" || got[1].Name != "fast-result" {
		t.Fatalf("results are not in provider order: %#v", got)
	}
}
