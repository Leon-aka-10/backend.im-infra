#!/bin/bash
set -eo pipefail

# Configuration paths
AZURE_CONFIG_DIR="/home/backenduser/.kube/azure"
MANUAL_CONFIG_DIR="/home/backenduser/.kube/manual"
AZURE_CONFIG="${AZURE_CONFIG_DIR}/config"
MANUAL_CONFIG="${MANUAL_CONFIG_DIR}/config"

# Ensure directories exist
mkdir -p "${AZURE_CONFIG_DIR}" "${MANUAL_CONFIG_DIR}"

if [ "$KUBECONFIG_MODE" = "azure" ]; then
  echo "Initializing Azure AKS configuration..."
  
  # Validate required Azure variables
  required_vars=(AZURE_SUBSCRIPTION_ID AZURE_RESOURCE_GROUP AKS_CLUSTER_NAME)
  for var in "${required_vars[@]}"; do
      if [[ -z "${!var}" ]]; then
          echo "ERROR: Missing required environment variable $var" >&2
          exit 1
      fi
  done
  
  # Clean existing Azure config
  rm -f "${AZURE_CONFIG}"
  
  # Login to Azure if not already logged in
  if ! az account show &>/dev/null; then
      echo "Logging into Azure..."
      az login --use-device-code
  fi
  
  # Set the correct subscription
  az account set --subscription "${AZURE_SUBSCRIPTION_ID}"
  
  # Verify AKS cluster exists
  if ! az aks show --resource-group "${AZURE_RESOURCE_GROUP}" --name "${AKS_CLUSTER_NAME}" &>/dev/null; then
      echo "ERROR: Failed to access AKS cluster '${AKS_CLUSTER_NAME}'" >&2
      exit 1
  fi
  
  # Generate fresh kubeconfig
  az aks get-credentials \
    --resource-group "${AZURE_RESOURCE_GROUP}" \
    --name "${AKS_CLUSTER_NAME}" \
    --file "${AZURE_CONFIG}"
    
  export KUBECONFIG="${AZURE_CONFIG}"

elif [ "$KUBECONFIG_MODE" = "manual" ]; then
  echo "Using manual kubeconfig..."
  
  if [ ! -f "${MANUAL_CONFIG}" ]; then
    echo "ERROR: Manual config not found at ${MANUAL_CONFIG}"
    exit 1
  fi
  
  export KUBECONFIG="${MANUAL_CONFIG}"

else
  echo "ERROR: Invalid KUBECONFIG_MODE '${KUBECONFIG_MODE}'"
  exit 1
fi

# Verify cluster access
if ! kubectl cluster-info --request-timeout=10s; then
  echo "Failed to connect to Kubernetes cluster"
  exit 1
fi

# Verify kubectl version
echo "Kubectl Version:"
kubectl version --client -o json | jq -r '.clientVersion.gitVersion'

exec "$@"