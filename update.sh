#!/bin/bash
# Move to codebase directory
cd /home/nba/rpi-led-sports-scoreboard

# Verify if online (check ping to github)
if ! ping -c 1 github.com &> /dev/null; then
    echo "No internet connection to GitHub. Skipping update."
    exit 0
fi

# Helper to run git as the repo owner
run_git() {
    sudo -u nba git "$@"
}

# Fetch remote changes
run_git fetch origin main &> /dev/null

# Compare local head with remote head
LOCAL=$(run_git rev-parse HEAD)
REMOTE=$(run_git rev-parse @{u})

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "New updates found on GitHub! Updating local repository..."
    
    # Pull changes
    run_git pull origin main
    
    # Sync dependencies if requirements.txt changed
    if run_git diff --name-only HEAD@{1} HEAD | grep -q "requirements.txt"; then
        echo "requirements.txt updated. Reinstalling dependencies..."
        /home/nba/rpi-led-sports-scoreboard/venv/bin/pip install -r requirements.txt
    fi
else
    echo "Scoreboard is up to date."
fi
