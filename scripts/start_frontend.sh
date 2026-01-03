#!/bin/bash
# DPOS Frontend Startup Script
# Starts the React/Vite development server

echo "=================================================="
echo "DPOS - Data Product Operating System"
echo "Starting Frontend Development Server..."
echo "=================================================="

cd "$(dirname "$0")/../frontend"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo ""
    echo "Installing dependencies..."
    npm install
fi

echo ""
echo "=================================================="
echo "Starting Vite dev server on http://localhost:3000"
echo "API requests will be proxied to http://localhost:8000"
echo "=================================================="
echo ""

npm run dev
