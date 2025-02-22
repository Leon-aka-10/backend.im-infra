#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from datetime import datetime

def main():
    try:
        if len(sys.argv) != 4:
            print(json.dumps({
                "status": "error",
                "message": "Required arguments: chatID userID projectType"
            }))
            sys.exit(1)

        chat_id, user_id, project_type = sys.argv[1], sys.argv[2], sys.argv[3].lower()
        namespace = f"im-{chat_id}-{user_id}".lower()
        yaml_path = f"deployments/templates/{project_type}/test-pod.yaml"

        # Validate YAML file exists
        if not os.path.exists(yaml_path):
            print(json.dumps({
                "status": "error",
                "message": f"Missing deployment template for {project_type}",
                "details": f"Could not find {yaml_path}"
            }))
            sys.exit(1)

        timestamp = datetime.utcnow().isoformat() + "Z"

        # Check namespace existence
        check = subprocess.run(
            ["kubectl", "get", "namespace", namespace],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Only log errors if the check wasn't a normal "not found" case
        if check.returncode != 0 and "NotFound" not in check.stderr:
            sys.stderr.write(f"kubectl check error: {check.stderr.strip()}\n")

        if check.returncode == 0:
            print(json.dumps({
                "status": "exists",
                "namespace": namespace,
                "timestamp": timestamp
            }))
            sys.exit(0)

        # Create namespace
        create = subprocess.run(
            ["kubectl", "create", "namespace", namespace],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if create.returncode != 0:
            print(json.dumps({
                "status": "error", 
                "message": create.stderr.strip(),
                "namespace": namespace
            }))
            sys.exit(1)

        # Deploy project-specific pod
        deploy = subprocess.run(
            ["kubectl", "apply", "-n", namespace, "-f", yaml_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if deploy.returncode != 0:
            print(json.dumps({
                "status": "error",
                "message": deploy.stderr.strip(),
                "namespace": namespace
            }))
            sys.exit(1)

        print(json.dumps({
            "status": "created",
            "namespace": namespace,
            "project_type": project_type,
            "timestamp": timestamp
        }))
        sys.exit(0)

    except Exception as e:
        print(json.dumps({
            "status": "error",
            "message": f"Script execution failed: {str(e)}",
            "python_error": str(e)
        }))
        sys.exit(1)

if __name__ == "__main__":
    main()