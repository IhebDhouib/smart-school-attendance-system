#!/bin/bash
# Build and deploy the face-fused container with all updated components
# This script rebuilds only the face-fused service with InsightFace integration

set -e

echo "🔧 Madrasati Face-Fused Container Rebuild Script"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is running${NC}"
echo ""

# Navigate to docker-setup directory
cd "$(dirname "$0")"

echo "📁 Current directory: $(pwd)"
echo ""

# Stop existing face-fused container if running
echo "🛑 Stopping existing face-fused container..."
docker-compose stop face-fused 2>/dev/null || true
docker-compose rm -f face-fused 2>/dev/null || true
echo -e "${GREEN}✅ Stopped and removed old container${NC}"
echo ""

# Remove old image to force rebuild
echo "🗑️  Removing old face-fused image..."
docker rmi madrasati_face_fused 2>/dev/null || true
echo -e "${GREEN}✅ Old image removed${NC}"
echo ""

# Build the new face-fused image
echo "🔨 Building face-fused container with InsightFace..."
echo "   This may take several minutes on first build..."
echo ""
docker-compose build --no-cache face-fused

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Face-fused container built successfully!${NC}"
else
    echo ""
    echo -e "${RED}❌ Build failed. Please check the errors above.${NC}"
    exit 1
fi

echo ""
echo "🚀 Starting face-fused container..."
docker-compose up -d face-fused

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Face-fused container started successfully!${NC}"
else
    echo ""
    echo -e "${RED}❌ Failed to start container. Please check logs.${NC}"
    exit 1
fi

# Wait a few seconds and show status
echo ""
echo "⏳ Waiting for services to initialize..."
sleep 5

echo ""
echo "📊 Container Status:"
docker-compose ps face-fused

echo ""
echo "📝 Recent logs:"
echo "=================================================="
docker-compose logs --tail=30 face-fused

echo ""
echo "=================================================="
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo ""
echo "📡 Services available at:"
echo "   - Face Encoding API:    http://localhost:8000"
echo "   - Unknown Faces API:    http://localhost:5001"
echo "   - API Documentation:    http://localhost:8000/docs"
echo ""
echo "🔍 Useful commands:"
echo "   - View logs:            docker-compose logs -f face-fused"
echo "   - Check status:         docker-compose ps face-fused"
echo "   - Restart service:      docker-compose restart face-fused"
echo "   - Stop service:         docker-compose stop face-fused"
echo "   - Enter container:      docker exec -it madrasati_face_fused bash"
echo ""
echo "📋 Next steps:"
echo "   1. Test Face API:       curl http://localhost:8000/students/encodings/status"
echo "   2. Test Unknown API:    curl http://localhost:5001/api/unknown-faces"
echo "   3. Upload student photo via Angular frontend"
echo "   4. Check encoding status"
echo ""
echo "=================================================="
