#!/bin/bash
set -eo pipefail

# Create isolated virtual environment
python3 -m venv /opt/awscli
source /opt/awscli/bin/activate

# Install AWS CLI within virtual environment
pip install --no-cache-dir awscli

# Create symlink for system-wide access
ln -sf /opt/awscli/bin/aws /usr/local/bin/aws

# Verify installation
aws --version || { echo "AWS CLI installation failed"; exit 1; }