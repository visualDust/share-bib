#!/bin/bash

# ShareBib - Stop Script

SESSION_NAME="sharebib"
LEGACY_SESSION_NAME="PACO"
STOPPED=0

for session in "$SESSION_NAME" "$LEGACY_SESSION_NAME"; do
    if tmux has-session -t "$session" 2>/dev/null; then
        echo "Stopping session '$session'..."
        tmux kill-session -t "$session"
        STOPPED=1
    fi
done

if [ "$STOPPED" -eq 1 ]; then
    echo "All ShareBib services stopped."
else
    echo "No ShareBib session found."
fi
