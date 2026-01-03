#!/bin/bash
# DPOS Full Stack Startup Script
# Starts both backend and frontend servers

echo "=================================================="
echo "DPOS - Data Product Operating System"
echo "Starting Full Stack Application..."
echo "=================================================="
echo ""

PROJECT_DIR="$(dirname "$0")/.."
cd "$PROJECT_DIR"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo "Starting Backend Server..."
python scripts/start_backend.py &
BACKEND_PID=$!

# Wait for backend to start
echo "Waiting for backend to initialize..."
sleep 5

# Start frontend
echo "Starting Frontend Server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "=================================================="
echo "Both servers are running:"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo "  API Docs: http://localhost:8000/docs"
echo "=================================================="
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for processes
wait
