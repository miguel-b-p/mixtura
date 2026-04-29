package main

import (
	_ "embed"
	"strings"
)

//go:embed VERSION
var embeddedVersion string

func version() string {
	version := strings.TrimSpace(embeddedVersion)
	if version == "" {
		return "unknown"
	}
	return version
}
