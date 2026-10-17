#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "=========================================================="
echo " Deploying Huawei EMS B1 Battery Manager (Production)"
echo " Root directory: $PROJECT_ROOT"
echo "=========================================================="

# 1. Build Production Frontend
echo "Building optimized React frontend..."
cd "$PROJECT_ROOT/frontend"
npm ci
npm run build

# 2. Setup Python Virtual Environment & Dependencies
echo "Verifying backend dependencies..."
cd "$PROJECT_ROOT"
if [ ! -d "$PROJECT_ROOT/backend/venv" ]; then
    python3 -m venv "$PROJECT_ROOT/backend/venv"
fi
"$PROJECT_ROOT/backend/venv/bin/pip" install --upgrade pip --quiet
"$PROJECT_ROOT/backend/venv/bin/pip" install -r "$PROJECT_ROOT/backend/requirements.txt" --quiet

# 3. Run Automated Tests
echo "Executing test suite..."
export PYTHONPATH="$PROJECT_ROOT/backend"
"$PROJECT_ROOT/backend/venv/bin/pytest" "$PROJECT_ROOT/backend/tests" -q

echo "=========================================================="
echo " Build & verification successful!"
echo " Starting production server on http://0.0.0.0:8000"
echo " Both UI and REST/WebSocket API are served on port 8000."
echo "=========================================================="

# 4. Start Unified Production Server
exec "$PROJECT_ROOT/backend/venv/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
