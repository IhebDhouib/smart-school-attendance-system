#!/bin/bash
# Startup script to run both face detection and unknown faces API

echo "🚀 Starting face detection services..."

# Create necessary directories
mkdir -p /app/encodings
mkdir -p /app/unknown_faces
mkdir -p /app/logs

# Install Flask and CORS if not installed
pip install flask flask-cors

echo "🔄 Starting Unknown Faces API on port 5001..."
python unknown_faces_api.py &

echo "🎥 Starting Face Detection..."
python app_with_env.py
