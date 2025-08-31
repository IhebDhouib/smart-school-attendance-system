#!/bin/bash

# Madrasati Docker Build and Push Script
echo "🚀 Building and pushing Madrasati Docker images..."

# Set your DockerHub username here
DOCKERHUB_USERNAME="ihebdhouib"

# Build and tag images
echo "📦 Building Docker images..."

# Backend
echo "Building backend..."
docker build -t $DOCKERHUB_USERNAME/madrasati-backend:latest -f Dockerfile.backend ../madrasati

# Frontend
echo "Building frontend..."
docker build -t $DOCKERHUB_USERNAME/madrasati-frontend:latest -f Dockerfile.frontend ../../

# Face Detection
echo "Building face detection..."
docker build -t $DOCKERHUB_USERNAME/madrasati-face-fused:latest -f Dockerfile.face-fused ../

# Push to DockerHub
echo "📤 Pushing images to DockerHub..."
docker push $DOCKERHUB_USERNAME/madrasati-backend:latest
docker push $DOCKERHUB_USERNAME/madrasati-frontend:latest
docker push $DOCKERHUB_USERNAME/madrasati-face-fused:latest

echo "✅ All images built and pushed successfully!"
echo "🔗 Images available at:"
echo "   - $DOCKERHUB_USERNAME/madrasati-backend:latest"
echo "   - $DOCKERHUB_USERNAME/madrasati-frontend:latest"
echo "   - $DOCKERHUB_USERNAME/madrasati-face-fused:latest"
