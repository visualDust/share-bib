#!/bin/bash

# PACO - Startup Script

SESSION_NAME="PACO"
DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Load backend .env (ports)
set -a
source "$DIR/backend/.env"
set +a

BACKEND_PORT=${BACKEND_PORT:-11550}
FRONTEND_PORT=${FRONTEND_PORT:-11551}

if tmux has-session -t $SESSION_NAME 2>/dev/null; then
    echo "Session '$SESSION_NAME' already exists. Attaching..."
    tmux attach-session -t $SESSION_NAME
    exit 0
fi

echo "Creating new tmux session: $SESSION_NAME"
tmux new-session -d -s $SESSION_NAME -n "backend"

# Window 0: Backend
tmux send-keys -t $SESSION_NAME:0 "cd $DIR/backend && echo 'Starting Backend...' && uv run uvicorn main:app --reload --port $BACKEND_PORT" C-m

# Window 1: Frontend
tmux new-window -t $SESSION_NAME:1 -n "frontend"
tmux send-keys -t $SESSION_NAME:1 "cd $DIR/frontend && echo 'Starting Frontend...' && npx vite --port $FRONTEND_PORT" C-m

# Window 2: Info
tmux new-window -t $SESSION_NAME:2 -n "info"
tmux send-keys -t $SESSION_NAME:2 "echo 'PACO services started!'" C-m
tmux send-keys -t $SESSION_NAME:2 "echo ''" C-m
tmux send-keys -t $SESSION_NAME:2 "echo 'Backend:  http://localhost:$BACKEND_PORT/docs'" C-m
tmux send-keys -t $SESSION_NAME:2 "echo 'Frontend: http://localhost:$FRONTEND_PORT'" C-m
tmux send-keys -t $SESSION_NAME:2 "echo ''" C-m
tmux send-keys -t $SESSION_NAME:2 "echo 'Config:   backend/.env'" C-m
tmux send-keys -t $SESSION_NAME:2 "echo 'Data:     data/'" C-m
tmux send-keys -t $SESSION_NAME:2 "echo ''" C-m
tmux send-keys -t $SESSION_NAME:2 "echo 'Ctrl+B then 0/1/2 to switch windows'" C-m
tmux send-keys -t $SESSION_NAME:2 "echo 'Ctrl+B then D to detach'" C-m
tmux send-keys -t $SESSION_NAME:2 "echo './stop.sh to stop all services'" C-m

tmux select-window -t $SESSION_NAME:2
tmux attach-session -t $SESSION_NAME
