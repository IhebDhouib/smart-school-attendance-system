#!/bin/bash
# Script de déploiement pour corriger le frontend avec les URLs relatives

set -e  # Exit on error

echo "🚀 Starting frontend deployment..."

# 1. Pull latest changes
echo "📥 Step 1/5: Pulling latest changes from GitHub..."
cd ~/smart-school-attendance-system
git reset --hard HEAD
git pull origin new-version

# 2. Go to docker-setup directory
echo "📂 Step 2/5: Navigating to docker directory..."
cd madrasati/madrasati

# 3. Rebuild frontend container
echo "🔨 Step 3/5: Rebuilding frontend container with production config..."
docker-compose build --no-cache frontend

# 4. Recreate frontend container
echo "🔄 Step 4/5: Restarting frontend container..."
docker-compose up -d --force-recreate frontend

# 5. Wait for container to be ready
echo "⏳ Waiting for frontend container to start..."
sleep 5

# 6. Verify the build
echo "🔍 Step 5/5: Verifying production build..."
echo ""
echo "Checking for hardcoded URLs in build..."
RESULT=$(docker exec madrasati_frontend sh -c "grep -r 'http://.*:3000' /usr/share/nginx/html/*.js 2>/dev/null || echo 'No hardcoded URLs found'")

if [[ "$RESULT" == *"No hardcoded URLs found"* ]]; then
    echo "✅ SUCCESS: Frontend build is correct - using relative URLs!"
    echo ""
    echo "🎉 Deployment completed successfully!"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Clear browser cache (Ctrl+Shift+Delete)"
    echo "   2. Or use Incognito mode"
    echo "   3. Navigate to http://192.168.1.100"
    echo "   4. Try to login"
    echo ""
    echo "Expected behavior: Login should call '/api/auth/login' (relative URL)"
else
    echo "⚠️  WARNING: Found hardcoded URLs in build:"
    echo "$RESULT"
    echo ""
    echo "This might be cached. Try rebuilding again with:"
    echo "docker-compose build --no-cache frontend"
fi

echo ""
echo "📊 Container status:"
docker-compose ps frontend
