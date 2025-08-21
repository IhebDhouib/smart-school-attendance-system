#!/bin/bash

# Madrasati Docker Setup Script
# This script helps you set up the Madrasati system quickly

set -e

echo "🚀 Madrasati Docker Setup"
echo "========================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Please run this script from the docker-setup directory"
    exit 1
fi

# Check if the main project exists
if [ ! -d "../madrasati" ]; then
    echo "❌ Main project directory not found. Please extract madrasati.rar first."
    echo "   Expected structure: madrasati/docker-setup/"
    exit 1
fi

echo "✅ Project structure looks good"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created. Please edit it with your camera URLs and settings."
    echo "   Important: Change MONGO_PASSWORD and JWT_SECRET for production!"
else
    echo "✅ .env file already exists"
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p ../madrasati/madrasati/madrasati/face/dataset
mkdir -p ../madrasati/madrasati/madrasati/face/unknown_faces
mkdir -p ../madrasati/madrasati/madrasati/face/logs
mkdir -p ../madrasati/madrasati/madrasati/backend/uploads
mkdir -p ../madrasati/madrasati/madrasati/backend/logs

echo "✅ Directories created"

# Build and start services
echo "🔨 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 30

# Check service status
echo "📊 Service Status:"
docker-compose ps

# Check if services are healthy
echo ""
echo "🔍 Testing service connectivity..."

# Test backend
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Backend is responding"
else
    echo "⚠️  Backend might still be starting up"
fi

# Test frontend
if curl -s http://localhost > /dev/null; then
    echo "✅ Frontend is responding"
else
    echo "⚠️  Frontend might still be starting up"
fi

# Test face API
if curl -s http://localhost:8000 > /dev/null; then
    echo "✅ Face API is responding"
else
    echo "⚠️  Face API might still be starting up"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your camera URLs"
echo "2. Add student photos to face dataset"
echo "3. Generate face encodings"
echo "4. Access the application at http://localhost"
echo ""
echo "📚 For detailed instructions, see README.md"
echo ""
echo "🔧 Useful commands:"
echo "   docker-compose logs -f          # View logs"
echo "   docker-compose down             # Stop services"
echo "   docker-compose up -d --build    # Rebuild and restart"

