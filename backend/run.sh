#!/bin/bash

# VoiceForge Backend Startup Script
# This script sets up the virtual environment and runs the FastAPI server

set -e

echo "=================================="
echo "  VoiceForge Backend"
echo "  Powered by Qwen3-TTS"
echo "=================================="

# Navigate to backend directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "../venv" ]; then
    echo "Creating virtual environment..."
    python3.12 -m venv ../venv || python3 -m venv ../venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source ../venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(dirname "$(pwd)")"

# Optional: Use smaller models for lower memory usage
# export VOICEFORGE_SMALL_MODELS=1
export VOICEFORGE_MODELS_DIR="$(cd .. && pwd)/models"

echo ""
echo "=================================="
echo "  Starting VoiceForge API Server"
echo "  http://localhost:8000"
echo "  Docs: http://localhost:8000/docs"
echo "=================================="
echo ""

# Run the server
# Use --reload for development, remove for production
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
