package services

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log"
	"os/exec"
	"path/filepath"
)

type NamespaceService struct {
	ScriptPath string
}

func NewNamespaceService() *NamespaceService {
	return &NamespaceService{
		ScriptPath: filepath.Join("scripts", "namespace_handler.py"),
	}
}

func (s *NamespaceService) HandleNamespace(chatID, userID, projectType string) (map[string]interface{}, error) {
	cmd := exec.Command("python3", s.ScriptPath, chatID, userID, projectType)
	output, err := cmd.CombinedOutput()
	
	// Enhanced error logging
	if err != nil {
		log.Printf("Script execution failed. Raw error: %v\nFull output:\n%s", err, string(output))
		return nil, fmt.Errorf("script execution failed: %w (output: %s)", err, string(output))
	}

	// Clean output and filter for JSON lines
	cleanedOutput := bytes.TrimSpace(output)
	if lines := bytes.Split(cleanedOutput, []byte{'\n'}); len(lines) > 1 {
		for _, line := range lines {
			if bytes.HasPrefix(line, []byte{'{'}) {
				cleanedOutput = line
				break
			}
		}
	}
	log.Printf("Namespace handler raw output: %q", cleanedOutput)

	var result map[string]interface{}
	if err := json.Unmarshal(cleanedOutput, &result); err != nil {
		log.Printf("JSON parsing failed. Raw output: %s", cleanedOutput)
		return nil, fmt.Errorf("failed to parse JSON output: %v", err)
	}

	if status, ok := result["status"]; ok && status == "error" {
		log.Printf("Namespace handler error details: %+v", result)
		if kubectlErr, exists := result["kubectl_error"]; exists {
			return result, fmt.Errorf("kubectl error: %v", kubectlErr)
		}
		return result, fmt.Errorf("namespace handler error: %v (full response: %+v)", result["message"], result)
	}

	return result, nil
}