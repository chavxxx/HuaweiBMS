#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "=========================================================="
echo " Starting Huawei EMS B1 Battery Manager"
echo " Project root: $PROJECT_ROOT"
echo "=========================================================="

# 1. Activate Python Backend Environment
if [ ! -d "$PROJECT_ROOT/backend/venv" ]; then
    echo "Creating Python virtual environment in backend/venv..."
    python3 -m venv "$PROJECT_ROOT/backend/venv"
    "$PROJECT_ROOT/backend/venv/bin/pip" install -r "$PROJECT_ROOT/backend/requirements.txt"
fi

# 2. Start Backend Service
echo "Starting FastAPI Serial & Backend Service on http://127.0.0.1:8000..."
export PYTHONPATH="$PROJECT_ROOT/backend"
"$PROJECT_ROOT/backend/venv/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Trap signals for graceful shutdown
cleanup() {
    echo ""
    echo "Shutting down Huawei EMS B1 Battery Manager..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID 2>/dev/null || true
    wait $FRONTEND_PID 2>/dev/null || true
    echo "Shutdown complete."
}
trap cleanup SIGINT SIGTERM EXIT

# 3. Start Frontend
echo "Starting React Frontend on http://localhost:5173..."
cd "$PROJECT_ROOT/frontend"
npm run dev -- --host 127.0.0.1 &
FRONTEND_PID=$!

echo ""
echo "=========================================================="
echo " Application running!"
echo " UI URL:      http://localhost:5173"
echo " Backend API: http://127.0.0.1:8000/docs"
echo " Press Ctrl+C to terminate both servers."
echo "=========================================================="

wait
