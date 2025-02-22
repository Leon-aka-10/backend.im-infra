#!/bin/bash

# Check if correct number of parameters are provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <repository_url> <commit_hash>"
    exit 1
fi

REPO_URL=$1
COMMIT_HASH=$2

# Create repos directory if it doesn't exist
REPOS_DIR="repos"
mkdir -p "$REPOS_DIR"

# Extract repo name from URL (removes .git if present)
REPO_NAME=$(basename "$REPO_URL" .git)
REPO_PATH="$REPOS_DIR/$REPO_NAME"

# Check if directory exists
if [ ! -d "$REPO_PATH" ]; then
    echo "Repository doesn't exist locally. Cloning..."
    cd "$REPOS_DIR" || { echo "Failed to enter repos directory"; exit 1; }
    git clone "$REPO_URL" || { echo "Clone failed"; exit 1; }
    cd "$REPO_NAME" || { echo "Failed to enter repository directory"; exit 1; }
else
    echo "Repository exists locally. Fetching latest changes..."
    cd "$REPO_PATH" || { echo "Failed to enter repository directory"; exit 1; }
    git fetch || { echo "Fetch failed"; exit 1; }
fi

# Checkout to specific commit
echo "Checking out to commit: $COMMIT_HASH"
git checkout "$COMMIT_HASH" || { echo "Checkout failed"; exit 1; }

echo "Successfully checked out to commit $COMMIT_HASH in $REPO_PATH"