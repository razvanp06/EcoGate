#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

# Cleanup all background processes on Ctrl+C
cleanup() {
    echo ""
    echo "Stopping all services..."
    kill "$AZURITE_PID" "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
    wait 2>/dev/null
    exit 0
}
trap cleanup INT TERM

# 1. Azurite (local storage emulator required by Azure Functions)
mkdir -p /tmp/azurite
echo "[1/3] Starting Azurite..."
npx --yes azurite --silent --location /tmp/azurite &
AZURITE_PID=$!
sleep 2

# 2. Backend (Azure Functions)
echo "[2/3] Starting backend..."
cd "$BACKEND"
source .venv/bin/activate
func start &
BACKEND_PID=$!
sleep 3

# 3. Frontend (Vite dev server)
echo "[3/3] Starting frontend..."
cd "$FRONTEND"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "  Backend:  http://localhost:7071"
echo "  Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all services."

wait
