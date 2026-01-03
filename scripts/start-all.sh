#!/usr/bin/env bash
API_PORT=${1:-8000}
UI_PORT=${2:-3000}

echo "Starting backend on port $API_PORT and frontend on port $UI_PORT"

# Start backend in background
./scripts/start-backend.sh $API_PORT &
BACK_PID=$!
echo "Backend PID: $BACK_PID"

# Start frontend in background
./scripts/start-frontend.sh $UI_PORT &
FRONT_PID=$!
echo "Frontend PID: $FRONT_PID"

wait $BACK_PID $FRONT_PID
