#!/bin/bash

# Carbon Account Launch Script for macOS / Linux

echo "===================================================="
echo "      LAUNCHING CARBON ACCOUNT WEB APP & AGENT"
echo "===================================================="

# Check if ports 8000 or 6006 are in use
ports=(8000 6006)
for port in "${ports[@]}"; do
  if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
    echo "Warning: Port $port is already active. Make sure no other server is running on it."
  fi
done

# Launch Backend in background
echo "Launching Backend (FastAPI + Arize Phoenix Agent Tracing)..."
PYTHONIOENCODING=utf-8 python3 -m backend.main &
BACKEND_PID=$!

# Launch Frontend in background
echo "Launching Frontend (Vite + React Dashboard)..."
cd frontend && npm run dev &
FRONTEND_PID=$!

# Handle shutdown of background processes on Ctrl+C
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit
}
trap cleanup SIGINT

echo "----------------------------------------------------"
echo "Done! The servers are running."
echo "API endpoint: http://127.0.0.1:8000"
echo "Arize Phoenix Console: http://localhost:6006"
echo "Press Ctrl+C in this terminal to stop both servers."
echo "===================================================="

# Keep script running to keep processes alive
wait
