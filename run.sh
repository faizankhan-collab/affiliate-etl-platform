#!/bin/bash
# Start the Affiliate ETL & RPC Web Platform
set -e

PORT=${PORT:-8000}
HOST=${HOST:-"127.0.0.1"}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH}"

echo "========================================================"
echo " Starting Affiliate ETL & RPC Automator on http://${HOST}:${PORT}"
echo "========================================================"

python3 -m uvicorn backend.app:app --host "${HOST}" --port "${PORT}" --reload
