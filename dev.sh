#!/bin/bash
# Local dev: starts backend (FastAPI) and frontend (Next.js) together.
# Usage: ./dev.sh
# Stop with Ctrl+C — kills both processes.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load backend env
if [ -f "$HOME/.claude/credentials/supabase-clubdejazz.env" ]; then
  source "$HOME/.claude/credentials/supabase-clubdejazz.env"
fi
if [ -f "$SCRIPT_DIR/backend/.env" ]; then
  source "$SCRIPT_DIR/backend/.env"
fi

echo "Starting backend on http://localhost:8000 ..."
cd "$SCRIPT_DIR/backend"
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "Starting frontend on http://localhost:3000 ..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo "  API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM
wait
