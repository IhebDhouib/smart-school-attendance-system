#!/bin/bash

echo "========================================"
echo "Madrasati Face-Fused Development Runner"
echo "========================================"
echo

cd "$(dirname "$0")"

echo "Checking if development image exists..."
if ! docker images | grep -q "madrasati_face_fused"; then
    echo "Development image not found. Building first..."
    ./build-dev.sh
    if [ $? -ne 0 ]; then
        echo "Build failed. Exiting."
        exit 1
    fi
else
    echo "✅ Development image found."
fi

echo
echo "🚀 Starting face-fused in development mode..."
echo "   (Press Ctrl+C to stop)"
echo

docker-compose -f docker-compose.dev.yml up face-fused

echo
echo "🛑 Service stopped."
echo "💡 Your code changes are automatically reflected!"
