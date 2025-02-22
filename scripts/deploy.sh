#!/bin/bash
set -e

# Pull latest code
cd "$(dirname "$0")/.."
git reset --hard HEAD
git pull origin main

# Build and restart Docker container
docker compose down
docker compose up -d --build