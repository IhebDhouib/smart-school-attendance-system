# =============================================================================
# Production Deployment Script for Madrasati
# =============================================================================
# This script safely deploys updates while preserving data
# =============================================================================

param(
    [switch]$Backup = $true,
    [switch]$SkipBuild = $false,
    [switch]$SkipPull = $false,
    [string]$Environment = "prod"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Madrasati Production Deployment" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
Write-Host ""

# Navigate to docker-setup directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "❌ ERROR: .env file not found!" -ForegroundColor Red
    Write-Host "Please create .env from .env.example" -ForegroundColor Yellow
    exit 1
}

# Load environment variables
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim()
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

# Step 1: Backup database
if ($Backup) {
    Write-Host "📦 Step 1: Backing up database..." -ForegroundColor Cyan
    $backupDate = Get-Date -Format "yyyy-MM-dd-HHmmss"
    $backupDir = "backups\mongodb-$backupDate"
    
    try {
        docker exec madrasati_mongodb mongodump `
            --out=/data/db/backup-$backupDate `
            --authenticationDatabase=admin `
            -u admin `
            -p $env:MONGO_PASSWORD 2>$null
        
        Write-Host "✅ Database backup created: backup-$backupDate" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  Warning: Could not backup database (might not exist yet)" -ForegroundColor Yellow
    }
} else {
    Write-Host "⏭️  Skipping database backup" -ForegroundColor Yellow
}

# Step 2: Pull latest code
if (-not $SkipPull) {
    Write-Host ""
    Write-Host "🔽 Step 2: Pulling latest code..." -ForegroundColor Cyan
    git pull origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Git pull failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Code updated" -ForegroundColor Green
} else {
    Write-Host "⏭️  Skipping git pull" -ForegroundColor Yellow
}

# Step 3: Stop containers
Write-Host ""
Write-Host "🛑 Step 3: Stopping containers..." -ForegroundColor Cyan
docker-compose -f docker-compose.base.yml -f docker-compose.prod.new.yml down
Write-Host "✅ Containers stopped" -ForegroundColor Green

# Step 4: Build images (optional)
if (-not $SkipBuild) {
    Write-Host ""
    Write-Host "🔨 Step 4: Building images..." -ForegroundColor Cyan
    docker-compose -f docker-compose.base.yml -f docker-compose.prod.new.yml build --parallel
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Build failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Images built" -ForegroundColor Green
} else {
    Write-Host "⏭️  Skipping image build" -ForegroundColor Yellow
}

# Step 5: Start containers
Write-Host ""
Write-Host "🚀 Step 5: Starting containers..." -ForegroundColor Cyan
docker-compose -f docker-compose.base.yml -f docker-compose.prod.new.yml up -d --remove-orphans
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start containers!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Containers started" -ForegroundColor Green

# Step 6: Wait for health checks
Write-Host ""
Write-Host "⏳ Step 6: Waiting for services to be healthy..." -ForegroundColor Cyan
Start-Sleep -Seconds 15

# Step 7: Verify services
Write-Host ""
Write-Host "🏥 Step 7: Verifying services..." -ForegroundColor Cyan
docker-compose -f docker-compose.base.yml -f docker-compose.prod.new.yml ps

$runningContainers = docker-compose -f docker-compose.base.yml -f docker-compose.prod.new.yml ps -q | Measure-Object
if ($runningContainers.Count -eq 0) {
    Write-Host "❌ No containers are running!" -ForegroundColor Red
    exit 1
}

# Step 8: Show logs
Write-Host ""
Write-Host "📋 Step 8: Recent logs..." -ForegroundColor Cyan
docker-compose -f docker-compose.base.yml -f docker-compose.prod.new.yml logs --tail=20

# Step 9: Cleanup
Write-Host ""
Write-Host "🧹 Step 9: Cleaning up..." -ForegroundColor Cyan
docker system prune -f
Write-Host "✅ Cleanup complete" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ DEPLOYMENT COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Application URLs:" -ForegroundColor Cyan
Write-Host "   Frontend:      http://localhost:$env:FRONTEND_PORT" -ForegroundColor White
Write-Host "   Backend API:   http://localhost:$env:BACKEND_HTTP_PORT" -ForegroundColor White
Write-Host "   Face API:      http://localhost:$env:FACE_API_PORT" -ForegroundColor White
Write-Host "   Mongo Express: http://localhost:$env:MONGO_EXPRESS_PORT" -ForegroundColor White
Write-Host ""
Write-Host "📊 Useful commands:" -ForegroundColor Cyan
Write-Host "   View logs:     docker-compose -f docker-compose.base.yml -f docker-compose.prod.new.yml logs -f" -ForegroundColor White
Write-Host "   Stop all:      docker-compose -f docker-compose.base.yml -f docker-compose.prod.new.yml down" -ForegroundColor White
Write-Host "   Restart:       docker-compose -f docker-compose.base.yml -f docker-compose.prod.new.yml restart" -ForegroundColor White
Write-Host ""
