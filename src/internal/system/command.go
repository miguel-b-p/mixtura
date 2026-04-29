package system

import (
	"bytes"
	"fmt"
	"os"
	"os/exec"
	"strings"
)

type CommandError struct {
	Cmd      []string
	ExitCode int
	Output   string
}

func (e CommandError) Error() string {
	return FriendlyCommandError(e)
}

func CommandExists(name string) bool {
	_, err := exec.LookPath(name)
	return err == nil
}

func RunCommand(args ...string) error {
	if len(args) == 0 {
		return fmt.Errorf("empty command")
	}
	fmt.Printf("\n   $ %s\n", strings.Join(args, " "))
	cmd := exec.Command(args[0], args[1:]...)
	cmd.Stdin = os.Stdin
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		exitCode := 1
		if exitErr, ok := err.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		}
		return CommandError{Cmd: args, ExitCode: exitCode, Output: strings.TrimSpace(stdout.String() + "\n" + stderr.String())}
	}
	if stdout.Len() > 0 {
		fmt.Print(stdout.String())
	}
	if stderr.Len() > 0 {
		fmt.Print(stderr.String())
	}
	return nil
}

func CaptureCommand(args ...string) (int, string, string) {
	if len(args) == 0 {
		return 1, "", "empty command"
	}
	cmd := exec.Command(args[0], args[1:]...)
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err := cmd.Run()
	if err == nil {
		return 0, stdout.String(), stderr.String()
	}
	if exitErr, ok := err.(*exec.ExitError); ok {
		return exitErr.ExitCode(), stdout.String(), stderr.String()
	}
	return 1, stdout.String(), err.Error()
}

func FriendlyCommandError(err CommandError) string {
	output := strings.TrimSpace(err.Output)
	cmdText := strings.Join(err.Cmd, " ")

	if len(err.Cmd) >= 4 && err.Cmd[0] == "nix" && err.Cmd[1] == "profile" && err.Cmd[2] == "add" {
		pkg := err.Cmd[len(err.Cmd)-1]
		if strings.Contains(pkg, "#") {
			pkg = pkg[strings.LastIndex(pkg, "#")+1:]
		}
		if strings.Contains(output, "does not provide attribute") {
			return fmt.Sprintf("Package %q was not found in nixpkgs. Try `mixtura search %s` to find the correct name.", pkg, pkg)
		}
	}

	if len(err.Cmd) > 0 && err.Cmd[0] == "nix" && strings.Contains(output, "cannot connect to socket") {
		return "Nix is installed, but Mixtura could not reach the Nix daemon. Check whether the daemon is running and whether your user has permission to access it."
	}

	if strings.Contains(output, "No such keg") || strings.Contains(output, "No available formula") {
		return "Package was not found by Homebrew. Run `mixtura search <name>` and try an exact package name."
	}

	if strings.Contains(output, "No remote refs found") || strings.Contains(output, "No such ref") {
		return "Package was not found by Flatpak. Run `mixtura search flatpak#<name>` and try an application ID."
	}

	if output != "" {
		return fmt.Sprintf("Command failed with exit code %d: %s\n%s", err.ExitCode, cmdText, lastNonEmptyLine(output))
	}
	return fmt.Sprintf("Command failed with exit code %d: %s", err.ExitCode, cmdText)
}

func lastNonEmptyLine(output string) string {
	lines := strings.Split(output, "\n")
	for i := len(lines) - 1; i >= 0; i-- {
		line := strings.TrimSpace(lines[i])
		if line != "" {
			return line
		}
	}
	return strings.TrimSpace(output)
}
