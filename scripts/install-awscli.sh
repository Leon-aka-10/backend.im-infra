#!/bin/bash
set -eo pipefail

# Create isolated virtual environment
python3 -m venv /opt/azcli
source /opt/azcli/bin/activate

# Install Azure CLI within virtual environment
pip install --no-cache-dir azure-cli

# Create symlink for system-wide access
ln -sf /opt/azcli/bin/az /usr/local/bin/az

# Verify installation
az version || { echo "Azure CLI installation failed"; exit 1; }