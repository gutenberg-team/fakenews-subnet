#!/bin/bash

CHECK_INTERVAL=3600  # 60 minutes

while true; do
    # Log the start of the script execution
    echo "$(date): Checking for updates in the Git repository..."

    # Fetch the latest changes from the remote
    git fetch origin

    # Check if the local branch is behind the remote
    LOCAL_HASH=$(git rev-parse HEAD)
    REMOTE_HASH=$(git rev-parse origin/main)

    if [ "$LOCAL_HASH" != "$REMOTE_HASH" ]; then
        # The HEAD has changed, meaning there's a new version
        echo "$(date): "New updates found. Pulling changes and restarting the process...""
        
        # Stash any local changes
        git stash
        
        # Pull changes
        git pull -f
        git reset --hard origin/main

        # Restart the validator process
        bash scripts/start_validator.sh

    else
        echo "No updates found."
    fi

    # Sleep until the beginning of the next hour
    echo "$(date): Sleeping for $CHECK_INTERVAL seconds..."
    sleep $CHECK_INTERVAL
done
