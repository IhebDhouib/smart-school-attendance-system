#!/bin/bash

# Madrasati Production Deployment Script
echo "🚀 Deploying Madrasati to production server..."

# Create deployment directory
mkdir -p ~/madrasati-deploy
cd ~/madrasati-deploy

# Download the production docker-compose file
echo "📥 Downloading production configuration..."
curl -O https://raw.githubusercontent.com/IhebDhouib/madrasatiarabe/new-version/madrasati/docker-setup/docker-compose.production.yml
curl -O https://raw.githubusercontent.com/IhebDhouib/madrasatiarabe/new-version/madrasati/docker-setup/init-mongo.js

# Create environment file
echo "⚙️ Creating environment configuration..."
cat > .env << EOF
# MongoDB Configuration
MONGO_PASSWORD=madrasati123

# JWT Secret (change this in production!)
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production-$(date +%s)

# Docker Compose Project Name
COMPOSE_PROJECT_NAME=madrasati
EOF

# Pull latest images
echo "📦 Pulling latest Docker images..."
docker-compose -f docker-compose.production.yml pull

# Start services
echo "🚀 Starting Madrasati services..."
docker-compose -f docker-compose.production.yml up -d

# Check status
echo "📊 Checking service status..."
docker-compose -f docker-compose.production.yml ps

echo ""
echo "✅ Deployment completed!"
echo "🌐 Frontend: http://$(hostname -I | awk '{print $1}')"
echo "🗄️  Database Admin: http://$(hostname -I | awk '{print $1}'):8081"
echo "🔧 Backend API: http://$(hostname -I | awk '{print $1}'):3000"
echo ""
echo "📋 Useful commands:"
echo "  View logs: docker-compose -f docker-compose.production.yml logs -f"
echo "  Stop all:  docker-compose -f docker-compose.production.yml down"
echo "  Restart:   docker-compose -f docker-compose.production.yml restart"
