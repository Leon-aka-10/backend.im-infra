package services

import (
	"encoding/json"
	"fmt"
	"log"
	"os/exec"
	"path/filepath"
)

type TestService struct {
	ScriptPath string
}

func NewTestService() *TestService {
	return &TestService{
		ScriptPath: filepath.Join("scripts", "test-runner.py"),
	}
}

func (s *TestService) RunTests(namespace, repoURL, commit, testCmd string) (map[string]interface{}, error) {
	cmdArgs := []string{
		s.ScriptPath,
		"-n", namespace,
		"-r", repoURL,
		"-c", commit,
	}

	if testCmd != "" {
		cmdArgs = append(cmdArgs, "-t", testCmd)
	}

	log.Printf("Executing test command: %v", cmdArgs)
	cmd := exec.Command("python3", cmdArgs...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		log.Printf("Test execution failed. Raw output:\n%s", string(output))
		return nil, fmt.Errorf("test runner error: %w", err)
	}

	var result map[string]interface{}
	if err := json.Unmarshal(output, &result); err != nil {
		return nil, fmt.Errorf("failed to parse test results: %w", err)
	}

	return result, nil
}