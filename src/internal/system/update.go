package system

import (
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"mixtura/internal/ui"
)

const (
	githubVersionURL = "https://api.github.com/repos/miguel-b-p/mixtura/contents/bin/VERSION"
	githubHashURL    = "https://api.github.com/repos/miguel-b-p/mixtura/contents/bin/HASH"
	githubBinaryURL  = "https://raw.githubusercontent.com/miguel-b-p/mixtura/master/bin/mixtura"
)

type githubContentResponse struct {
	Content string `json:"content"`
}

func CheckForUpdates(currentVersion string) {
	remoteVersion, err := fetchGitHubContent(githubVersionURL)
	if err != nil || remoteVersion == "" || CompareVersions(remoteVersion, currentVersion) <= 0 {
		return
	}

	fmt.Printf("NOTICE: A new version of Mixtura is available! (%s -> %s)\n", currentVersion, remoteVersion)
	if !ui.Confirm("Do you want to update to the latest version?", false) {
		fmt.Println("Update skipped.")
		fmt.Println()
		return
	}

	expectedHash, err := fetchGitHubContent(githubHashURL)
	if err != nil || expectedHash == "" {
		ui.Error("Update failed: could not fetch expected hash")
		return
	}

	client := http.Client{Timeout: 2 * time.Minute}
	response, err := client.Get(githubBinaryURL)
	if err != nil {
		ui.Error("Update failed: %v", err)
		return
	}
	defer response.Body.Close()
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		ui.Error("Update failed: HTTP %d", response.StatusCode)
		return
	}

	content, err := io.ReadAll(response.Body)
	if err != nil {
		ui.Error("Update failed: %v", err)
		return
	}

	sum := sha256.Sum256(content)
	downloadedHash := hex.EncodeToString(sum[:])
	if !strings.EqualFold(downloadedHash, strings.TrimSpace(expectedHash)) {
		ui.Error("Update failed: hash mismatch")
		return
	}

	executablePath, err := os.Executable()
	if err != nil {
		ui.Error("Update failed: %v", err)
		return
	}
	tempPath := filepath.Clean(executablePath) + ".tmp"
	if err := os.WriteFile(tempPath, content, 0o755); err != nil {
		ui.Error("Update failed: %v", err)
		return
	}
	if err := os.Rename(tempPath, executablePath); err != nil {
		_ = os.Remove(tempPath)
		ui.Error("Update failed: %v", err)
		return
	}

	fmt.Println("Update successful! Please restart Mixtura.")
	os.Exit(0)
}

func CompareVersions(left, right string) int {
	leftParts := strings.Split(strings.TrimSpace(left), ".")
	rightParts := strings.Split(strings.TrimSpace(right), ".")
	maxLen := len(leftParts)
	if len(rightParts) > maxLen {
		maxLen = len(rightParts)
	}
	for i := 0; i < maxLen; i++ {
		leftValue := versionPart(leftParts, i)
		rightValue := versionPart(rightParts, i)
		if leftValue > rightValue {
			return 1
		}
		if leftValue < rightValue {
			return -1
		}
	}
	return 0
}

func versionPart(parts []string, index int) int {
	if index >= len(parts) {
		return 0
	}
	value, err := strconv.Atoi(parts[index])
	if err != nil {
		return 0
	}
	return value
}

func fetchGitHubContent(url string) (string, error) {
	client := http.Client{Timeout: 5 * time.Second}
	response, err := client.Get(url)
	if err != nil {
		return "", err
	}
	defer response.Body.Close()
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		return "", fmt.Errorf("HTTP %d", response.StatusCode)
	}

	var payload githubContentResponse
	if err := json.NewDecoder(response.Body).Decode(&payload); err != nil {
		return "", err
	}
	content, err := base64.StdEncoding.DecodeString(strings.ReplaceAll(payload.Content, "\n", ""))
	if err != nil {
		return "", err
	}
	return strings.TrimSpace(string(content)), nil
}
