#!/bin/bash
# Fail on any error
set -eo pipefail

# Check WebSocket endpoint
status_code=$(curl -sS -o /dev/null -w '%{http_code}' http://localhost:8080/ws)

# Additional Kubernetes cluster health check
kubectl get nodes --request-timeout=5s >/dev/null 2>&1

# Return appropriate exit code
[[ $status_code -eq 400 ]] && exit 0 || exit 1