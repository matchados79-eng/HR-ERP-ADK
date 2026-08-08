#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "==========================================================="
echo " Starting Saudi HR ERP System Local Production Server..."
echo "==========================================================="

# Seed Database if not already seeded
echo "Checking & Seeding Database..."
python3 seed_data.py

PORT=${PORT:-8000}
HOST=${HOST:-"0.0.0.0"}

echo "Launching FastAPI application via Uvicorn on http://$HOST:$PORT ..."
exec python3 -m uvicorn app:app --host "$HOST" --port "$PORT" --reload
