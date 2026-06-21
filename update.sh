#!/bin/bash
# Move to codebase directory
cd /home/nba/rpi-led-sports-scoreboard

# Verify if online (check ping to github)
if ! ping -c 1 github.com &> /dev/null; then
    echo "No internet connection to GitHub. Skipping update."
    exit 0
fi

# Fetch remote changes
git fetch origin main &> /dev/null

# Compare local head with remote head
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse @{u})

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "New updates found on GitHub! Updating local repository..."
    
    # Pull changes
    git pull origin main
    
    # Sync dependencies if requirements.txt changed
    if git diff --name-only HEAD@{1} HEAD | grep -q "requirements.txt"; then
        echo "requirements.txt updated. Reinstalling dependencies..."
        /home/nba/rpi-led-sports-scoreboard/venv/bin/pip install -r requirements.txt
    fi
else
    echo "Scoreboard is up to date."
fi
