#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import time
from typing import Dict, Any, List

class TestRunner:
    def __init__(self, namespace: str, repo_url: str, commit: str, test_cmd: str, project_type: str):
        self.namespace = namespace
        self.repo_url = repo_url
        self.commit = commit
        self.test_cmd = test_cmd
        self.project_type = project_type
        self.pod_name = ""
        self.result: Dict[str, Any] = {
            "commit": commit,
            "status": "unknown",
            "success": False,
            "duration": 0.0,
            "output": {
                "stdout": "",
                "stderr": "",
                "kubectl_errors": []
            }
        }

    def run_kubectl(self, command: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Execute kubectl command and capture output"""
        full_command = ["kubectl", "-n", self.namespace] + command
        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            # Capture full command with quotes
            err_cmd = ' '.join([f"'{arg}'" if ' ' in arg else arg for arg in full_command])
            self.result["output"]["kubectl_errors"].append({
                "command": err_cmd,
                "error": e.stderr.strip()
            })
            raise

    def execute_test_run(self) -> Dict[str, Any]:
        """Main execution flow returning JSON results"""
        start_time = time.time()
        
        try:
            self.result["steps"] = []
            
            # Find existing pod
            self._add_step("Locating pod", "setup")
            result = self.run_kubectl(["get", "pod", "-l", "app=test-pod", "-o", "jsonpath={.items[0].metadata.name}"])
            self.pod_name = result.stdout.strip()
            
            # Wait for pod to be fully ready
            self._add_step("Awaiting pod readiness", "pod_ready")
            self.run_kubectl(["wait", "--for=condition=Ready", "pod", self.pod_name, "--timeout=180s"])
            self._add_step("Pod ready", "setup_complete")

            # Check if repo exists
            self._add_step("Checking repository status", "repo_check")
            repo_exists = self.run_kubectl(
                ["exec", self.pod_name, "--", "sh", "-c", "test -d /app/repo/.git && echo exists"],
                check=False
            ).stdout.strip() == "exists"

            if repo_exists:
                # Update existing repo
                self._add_step("Updating repository", "repo_update")
                self.run_kubectl(["exec", self.pod_name, "--", "sh", "-c", 
                                "cd /app/repo && git fetch origin && git reset --hard origin/main"])
            else:
                # Clone new repo
                self._add_step("Cloning repository", "repo_clone")
                self.run_kubectl(["exec", self.pod_name, "--", "sh", "-c", 
                                f"git clone '{self.repo_url}' /app/repo"])

            # Checkout specific commit
            self._add_step("Checking out commit", "commit_checkout")
            checkout_result = self.run_kubectl(["exec", self.pod_name, "--", "sh", "-c", 
                              f"cd /app/repo && git checkout {self.commit} && git log -1 --pretty=format:%s"])
            commit_message = checkout_result.stdout.strip()
            self.result["commit_message"] = commit_message
            self._add_step(f"Checked out: {commit_message}", "commit_verified")

            # Install dependencies
            self._add_step("Installing dependencies", "dependencies")
            self.run_kubectl(["exec", self.pod_name, "--", "sh", "-c", 
                            "cd /app/repo && pip install --quiet -r requirements.txt"])

            # Run tests
            self._add_step("Executing tests", "test_execution")
            test_cmd = f"cd /app/repo && ({self.test_cmd})"  # Wrap in subshell
            test_result = self.run_kubectl(["exec", self.pod_name, "--", "sh", "-c", test_cmd])
            
            # Capture results
            self.result["output"]["stdout"] = test_result.stdout
            self.result["output"]["stderr"] = test_result.stderr
            self.result["success"] = True
            self.result["status"] = "passed"

        except subprocess.CalledProcessError as e:
            self.result["status"] = "failed"
            self.result["success"] = False
            if not self.result["output"]["stdout"]:
                self.result["output"]["stdout"] = e.stdout
            if not self.result["output"]["stderr"]:
                self.result["output"]["stderr"] = e.stderr
        except Exception as e:
            self.result["status"] = "error"
            self.result["output"]["stderr"] = str(e)
        finally:
            self.result["duration"] = round(time.time() - start_time, 2)
        
        return self.result

    def _add_step(self, description: str, step_id: str):
        """Track execution steps"""
        self.result["steps"].append({
            "step": step_id,
            "description": description,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        })

def main():
    parser = argparse.ArgumentParser(description='Single Commit Test Runner')
    parser.add_argument('-n', '--namespace', required=True, help='Target namespace')
    parser.add_argument('-r', '--repo-url', required=True, help='Git repository URL')
    parser.add_argument('-c', '--commit', required=True, help='Commit hash to test')
    parser.add_argument('-t', '--test-cmd', default='pytest tests/', help='Test command')
    
    args = parser.parse_args()
    
    runner = TestRunner(
        namespace=args.namespace,
        repo_url=args.repo_url,
        commit=args.commit,
        test_cmd=args.test_cmd,
        project_type="fastapi"  # Default to fastapi for now
    )
    
    result = runner.execute_test_run()
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()