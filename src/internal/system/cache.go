package system

import (
	"encoding/json"
	"os"
	"path/filepath"
	"time"

	"mixtura/internal/core"
)

const cacheTTL = 5 * time.Minute

type cacheEntry struct {
	Timestamp int64          `json:"timestamp"`
	Results   []core.Package `json:"results"`
}

func CachedSearch(providerName, query string, load func() []core.Package) []core.Package {
	cache := loadCache(providerName)
	entry, ok := cache[query]
	if ok && time.Since(time.Unix(entry.Timestamp, 0)) <= cacheTTL {
		return entry.Results
	}

	results := load()
	if results == nil {
		return nil
	}
	cache[query] = cacheEntry{
		Timestamp: time.Now().Unix(),
		Results:   results,
	}
	saveCache(providerName, cache)
	return results
}

func loadCache(providerName string) map[string]cacheEntry {
	path, err := cachePath(providerName)
	if err != nil {
		return map[string]cacheEntry{}
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return map[string]cacheEntry{}
	}
	cache := map[string]cacheEntry{}
	if err := json.Unmarshal(data, &cache); err != nil {
		return map[string]cacheEntry{}
	}

	now := time.Now()
	for query, entry := range cache {
		if now.Sub(time.Unix(entry.Timestamp, 0)) > cacheTTL {
			delete(cache, query)
		}
	}
	return cache
}

func saveCache(providerName string, cache map[string]cacheEntry) {
	path, err := cachePath(providerName)
	if err != nil {
		return
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return
	}
	data, err := json.MarshalIndent(cache, "", "  ")
	if err != nil {
		return
	}
	_ = os.WriteFile(path, data, 0o644)
}

func cachePath(providerName string) (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(home, "mixtura", "cache", providerName+"_search_go.json"), nil
}
