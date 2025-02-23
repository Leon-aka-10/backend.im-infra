#!/bin/bash
set -eo pipefail

# Configuration paths
KUBECONFIG_PATH="/home/backenduser/.kube/azure/config"

echo "Initializing Azure AKS configuration..."

# Ensure required environment variables exist
if [[ -z "$AZURE_SUBSCRIPTION_ID" || -z "$AZURE_RESOURCE_GROUP" || -z "$AKS_CLUSTER_NAME" ]]; then
    echo "ERROR: Missing required Azure environment variables."
    exit 1
fi

# Ensure kubeconfig directory exists
mkdir -p "$(dirname "$KUBECONFIG_PATH")"

# Remove any corrupted kubeconfig file
if [[ -f "$KUBECONFIG_PATH" ]]; then
    if ! grep -q "apiVersion: v1" "$KUBECONFIG_PATH"; then
        echo "WARNING: Corrupt kubeconfig detected. Removing..."
        rm -f "$KUBECONFIG_PATH"
    fi
fi

# Authenticate with Azure if needed
if ! az account show &>/dev/null; then
    echo "Logging into Azure..."
    az login --use-device-code
fi

# Set correct subscription
az account set --subscription "$AZURE_SUBSCRIPTION_ID"

# Fetch AKS credentials
echo "Fetching kubeconfig from AKS..."
az aks get-credentials --resource-group "$AZURE_RESOURCE_GROUP" --name "$AKS_CLUSTER_NAME" --file "$KUBECONFIG_PATH" --overwrite-existing

# Validate kubeconfig file
if [[ ! -s "$KUBECONFIG_PATH" ]]; then
    echo "ERROR: Failed to generate a valid kubeconfig file!"
    exit 1
fi

echo "Kubernetes configuration successfully initialized!"

exec "$@"