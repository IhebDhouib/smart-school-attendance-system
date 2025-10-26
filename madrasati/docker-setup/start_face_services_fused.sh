#!/bin/bash
# Startup script for face-fused container
# Runs three services:
# 1. FastAPI face encoding API (port 8000)
# 2. Unknown faces API (port 5001)
# 3. Real-time face detection app (background)

set -e

echo "🚀 Starting Madrasati Face Services (Fused Container)"
echo "=================================================="

# Create required directories with proper paths
mkdir -p /app/madrasati/face/dataset
mkdir -p /app/madrasati/face/unknown_faces
mkdir -p /app/madrasati/face/logs
mkdir -p /root/.insightface/models

# Set proper working directory and permissions
chmod -R 755 /app/madrasati/face

# Check if InsightFace models are downloaded
echo "🔍 Checking InsightFace models..."
if [ ! -d "/root/.insightface/models" ] || [ -z "$(ls -A /root/.insightface/models)" ]; then
    echo "⚠️  InsightFace models not found. They will be downloaded on first run (~280MB)."
else
    echo "✅ InsightFace models found."
fi

# Start FastAPI face encoding service (port 8000) with auto-reload
echo "🔧 Starting Face Encoding API (port 8000) with auto-reload..."
cd /app/madrasati/face
uvicorn faceapi:app --host 0.0.0.0 --port 8000 --reload --log-level info &
FACEAPI_PID=$!
echo "✅ Face API started with PID $FACEAPI_PID (auto-reload enabled)"

# Start Unknown Faces API (port 5001) with auto-reload
echo "🔧 Starting Unknown Faces API (port 5001) with auto-reload..."
cd /app/docker-setup
uvicorn unknown_faces_api_fastapi:app --host 0.0.0.0 --port 5001 --reload --log-level info &
UNKNOWN_API_PID=$!
echo "✅ Unknown Faces API started with PID $UNKNOWN_API_PID (auto-reload enabled)"

# Give APIs time to start
sleep 3

# Start real-time face detection app
echo "🔧 Starting Real-time Face Detection App..."
cd /app/madrasati/face
python app_with_env.py &
APP_PID=$!
echo "✅ Face Detection App started with PID $APP_PID"

# Monitor processes
echo ""
echo "=================================================="
echo "✅ All services started successfully!"
echo "   - Face API:        http://0.0.0.0:8000"
echo "   - Unknown API:     http://0.0.0.0:5001"
echo "   - Detection App:   Running in background"
echo "=================================================="
echo ""
echo "📊 Process monitoring active..."

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $FACEAPI_PID $UNKNOWN_API_PID $APP_PID 2>/dev/null || true
    wait $FACEAPI_PID $UNKNOWN_API_PID $APP_PID 2>/dev/null || true
    echo "✅ All services stopped"
    exit 0
}

trap cleanup SIGTERM SIGINT

# Keep script running and monitor child processes
while true; do
    # Check if any service died
    if ! kill -0 $FACEAPI_PID 2>/dev/null; then
        echo "❌ Face API died! Restarting with auto-reload..."
        cd /app/madrasati/face
        uvicorn faceapi:app --host 0.0.0.0 --port 8000 --reload --log-level info &
        FACEAPI_PID=$!
    fi
    
    if ! kill -0 $UNKNOWN_API_PID 2>/dev/null; then
        echo "❌ Unknown Faces API died! Restarting with auto-reload..."
        cd /app/docker-setup
        uvicorn unknown_faces_api_fastapi:app --host 0.0.0.0 --port 5001 --reload --log-level info &
        UNKNOWN_API_PID=$!
    fi
    
    if ! kill -0 $APP_PID 2>/dev/null; then
        echo "❌ Detection App died! Restarting..."
        cd /app/madrasati/face
        python app_with_env.py &
        APP_PID=$!
    fi
    
    sleep 10
done
