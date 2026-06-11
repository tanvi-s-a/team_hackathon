#!/bin/bash

echo "===================================================="
echo "      LAUNCHING CARBON ACCOUNT WEB APP & AGENT"
echo "===================================================="

ports=(8000 5173)
for port in "${ports[@]}"; do
  if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Warning: Port $port is already in use."
  fi
done

echo "Launching Backend (FastAPI on 0.0.0.0:8000)..."
PYTHONIOENCODING=utf-8 python3 -m backend.main &
BACKEND_PID=$!

echo "Launching Frontend (Vite preview on 0.0.0.0:5173)..."
cd frontend && npm run preview -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit
}
trap cleanup SIGINT

echo "----------------------------------------------------"
echo "Backend:  http://0.0.0.0:8000"
echo "Frontend: http://0.0.0.0:5173"
echo "Press Ctrl+C to stop both servers."
echo "===================================================="

wait