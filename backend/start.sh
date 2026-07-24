#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Go to that directory
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "../venv/bin/activate" ]; then
    # In case venv is one level up
    source ../venv/bin/activate
else
    echo "❌ Error: Virtual environment not found."
    exit 1
fi

# Check logic for port
PORT=8000
PID=$(lsof -t -i :$PORT)
if [ ! -z "$PID" ]; then
    echo "⚠️  Port $PORT is busy. Killing process $PID..."
    kill -9 $PID
fi

echo "🚀 Starting WealthSense Backend on Port $PORT..."
uvicorn main:app --reload --port $PORT
