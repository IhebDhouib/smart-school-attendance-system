# Build and deploy the face-fused container (Windows PowerShell version)
# This script rebuilds only the face-fused service with InsightFace integration

Write-Host "🔧 Madrasati Face-Fused Container Rebuild Script" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check if docker is running
try {
    docker info | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running. Please start Docker first." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Navigate to docker-setup directory
Set-Location $PSScriptRoot

Write-Host "📁 Current directory: $(Get-Location)" -ForegroundColor Yellow
Write-Host ""

# Stop existing face-fused container if running
Write-Host "🛑 Stopping existing face-fused container..." -ForegroundColor Yellow
docker-compose stop face-fused 2>$null
docker-compose rm -f face-fused 2>$null
Write-Host "✅ Stopped and removed old container" -ForegroundColor Green
Write-Host ""

# Remove old image to force rebuild
Write-Host "🗑️  Removing old face-fused image..." -ForegroundColor Yellow
docker rmi madrasati_face_fused 2>$null
Write-Host "✅ Old image removed" -ForegroundColor Green
Write-Host ""

# Build the new face-fused image
Write-Host "🔨 Building face-fused container with InsightFace..." -ForegroundColor Cyan
Write-Host "   This may take several minutes on first build..." -ForegroundColor Yellow
Write-Host ""

docker-compose build --no-cache face-fused

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Face-fused container built successfully!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ Build failed. Please check the errors above." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🚀 Starting face-fused container..." -ForegroundColor Cyan
docker-compose up -d face-fused

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Face-fused container started successfully!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ Failed to start container. Please check logs." -ForegroundColor Red
    exit 1
}

# Wait a few seconds and show status
Write-Host ""
Write-Host "⏳ Waiting for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "📊 Container Status:" -ForegroundColor Cyan
docker-compose ps face-fused

Write-Host ""
Write-Host "📝 Recent logs:" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
docker-compose logs --tail=30 face-fused

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "✅ Deployment Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📡 Services available at:" -ForegroundColor Cyan
Write-Host "   - Face Encoding API:    http://localhost:8000"
Write-Host "   - Unknown Faces API:    http://localhost:5001"
Write-Host "   - API Documentation:    http://localhost:8000/docs"
Write-Host ""
Write-Host "🔍 Useful commands:" -ForegroundColor Cyan
Write-Host "   - View logs:            docker-compose logs -f face-fused"
Write-Host "   - Check status:         docker-compose ps face-fused"
Write-Host "   - Restart service:      docker-compose restart face-fused"
Write-Host "   - Stop service:         docker-compose stop face-fused"
Write-Host "   - Enter container:      docker exec -it madrasati_face_fused bash"
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Test Face API:       Invoke-WebRequest http://localhost:8000/students/encodings/status"
Write-Host "   2. Test Unknown API:    Invoke-WebRequest http://localhost:5001/api/unknown-faces"
Write-Host "   3. Upload student photo via Angular frontend"
Write-Host "   4. Check encoding status"
Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
