#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install or update dependencies
pip install -r requirements.txt

# Set default values for host and port if not provided in environment
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-8000}

# Run the server
uvicorn app:app --host $HOST --port $PORT --reload 