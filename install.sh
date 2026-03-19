#!/bin/bash
set -euo pipefail

echo "=== SocialClipper — Installer ==="
echo ""

# 1. Install system dependencies via Homebrew
echo "[1/3] Installing system tools (ffmpeg, yt-dlp)..."
if ! command -v ffmpeg &> /dev/null; then
    brew install ffmpeg
else
    echo "  ffmpeg already installed"
fi

if ! command -v yt-dlp &> /dev/null; then
    brew install yt-dlp
else
    echo "  yt-dlp already installed"
fi

# 2. Create virtual environment
echo ""
echo "[2/3] Setting up Python environment..."
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "  Created virtual environment"
else
    echo "  Virtual environment already exists"
fi

source .venv/bin/activate

# 3. Install Python package
echo ""
echo "[3/3] Installing Python dependencies..."
pip install -e . --quiet

echo ""
echo "============================================"
echo "  Installation complete!"
echo "============================================"
echo ""
echo "To start the server:"
echo "  ./run.sh"
echo ""
echo "Then open: http://localhost:8000"
echo ""
echo "REQUIRED: Set your Anthropic API key first:"
echo "  export ANTHROPIC_API_KEY='sk-ant-...'"
echo ""
