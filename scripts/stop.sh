#!/bin/bash

# Paper Collector - Stop Script

SESSION_NAME="PACO"

if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "Stopping session '$SESSION_NAME'..."
    tmux kill-session -t $SESSION_NAME
    echo "All services stopped."
else
    echo "Session '$SESSION_NAME' not found."
fi
