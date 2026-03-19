#!/bin/bash
cd "$(dirname "$0")"

# Activate virtual environment
source .venv/bin/activate

echo ""
echo "  SocialClipper"
echo "  http://localhost:8000"
echo ""
echo "  Accessible on your network at:"
# Show local IP for LAN access
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "unknown")
echo "  http://${LOCAL_IP}:8000"
echo ""
echo "  Press Ctrl+C to stop"
echo ""

# Run on 0.0.0.0 so it's accessible from other devices on the network
python -m uvicorn socialclipper.app:app --host 0.0.0.0 --port 8000 --app-dir src
