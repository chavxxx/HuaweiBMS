#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Running Huawei EMS B1 Battery Manager Test Suite..."

export PYTHONPATH="$PROJECT_ROOT/backend"
"$PROJECT_ROOT/backend/venv/bin/pytest" "$PROJECT_ROOT/backend/tests" -v

echo ""
echo "Building Frontend to verify TypeScript compilation & bundle integrity..."
cd "$PROJECT_ROOT/frontend"
npm run build

echo ""
echo "All tests and production builds passed successfully!"
