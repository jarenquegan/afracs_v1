#!/bin/bash
# ============================================================
# AFRACS launcher for Raspberry Pi (Linux).
# This script starts both the Admin Dashboard and the UI.
# ============================================================

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Check for virtual environment
if [ ! -f ".venv/bin/activate" ]; then
    echo "[ERROR] Virtual environment not found."
    echo "Please run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    read -p "Press enter to exit..."
    exit 1
fi

# Activate venv
source .venv/bin/activate

# 1. Start the Admin Dashboard in the background
echo "Starting Admin Dashboard..."
python dashboard.py > dashboard.log 2>&1 &
DASHBOARD_PID=$!

# 2. Wait a moment for the dashboard to initialize
sleep 2

# 3. Start the Cabinet UI
echo "Starting Cabinet UI..."
python cabinet.py

# When the UI is closed, kill the dashboard process
echo "Shutting down Dashboard..."
kill $DASHBOARD_PID
