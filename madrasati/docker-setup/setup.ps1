# =============================================================================
# Initial Setup Script for Madrasati
# =============================================================================
# Run this ONCE when setting up the project for the first time
# =============================================================================

param(
    [switch]$SkipVolumes = $false,
    [switch]$SkipEnv = $false
)

$ErrorActionPreference = "Stop"

Write-Host "🎯 Madrasati Initial Setup" -ForegroundColor Green
Write-Host "==========================" -ForegroundColor Green
Write-Host ""

# Navigate to docker-setup directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Step 1: Create .env file
if (-not $SkipEnv) {
    Write-Host "📝 Step 1: Setting up environment variables..." -ForegroundColor Cyan
    
    if (Test-Path ".env") {
        Write-Host "⚠️  .env file already exists!" -ForegroundColor Yellow
        $response = Read-Host "Do you want to overwrite it? (y/N)"
        if ($response -ne "y") {
            Write-Host "Keeping existing .env file" -ForegroundColor Yellow
        } else {
            Copy-Item ".env.example" ".env" -Force
            Write-Host "✅ .env file created from template" -ForegroundColor Green
            Write-Host "⚠️  IMPORTANT: Edit .env and update the following:" -ForegroundColor Yellow
            Write-Host "   - MONGO_PASSWORD" -ForegroundColor White
            Write-Host "   - JWT_SECRET" -ForegroundColor White
            Write-Host "   - CAMERA_URL" -ForegroundColor White
        }
    } else {
        Copy-Item ".env.example" ".env"
        Write-Host "✅ .env file created from template" -ForegroundColor Green
        Write-Host "⚠️  IMPORTANT: Edit .env and update the following:" -ForegroundColor Yellow
        Write-Host "   - MONGO_PASSWORD" -ForegroundColor White
        Write-Host "   - JWT_SECRET" -ForegroundColor White
        Write-Host "   - CAMERA_URL" -ForegroundColor White
    }
} else {
    Write-Host "⏭️  Skipping .env setup" -ForegroundColor Yellow
}

# Step 2: Create Docker volumes
if (-not $SkipVolumes) {
    Write-Host ""
    Write-Host "🗄️  Step 2: Creating Docker volumes..." -ForegroundColor Cyan
    
    $volumes = @(
        "madrasati_mongodb_data",
        "madrasati_face_encodings",
        "madrasati_backend_uploads",
        "madrasati_face_unknown",
        "madrasati_backend_logs",
        "madrasati_face_logs",
        "madrasati_face_dataset"
    )
    
    foreach ($volume in $volumes) {
        try {
            docker volume create $volume | Out-Null
            Write-Host "  ✅ Created volume: $volume" -ForegroundColor Green
        } catch {
            Write-Host "  ⚠️  Volume $volume already exists" -ForegroundColor Yellow
        }
    }
    
    Write-Host "✅ All volumes created" -ForegroundColor Green
} else {
    Write-Host "⏭️  Skipping volume creation" -ForegroundColor Yellow
}

# Step 3: Create config directories
Write-Host ""
Write-Host "📁 Step 3: Creating config directories..." -ForegroundColor Cyan

$configDirs = @(
    "config",
    "config\nginx",
    "config\python",
    "backups"
)

foreach ($dir in $configDirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  ✅ Created: $dir" -ForegroundColor Green
    } else {
        Write-Host "  ℹ️  Already exists: $dir" -ForegroundColor Gray
    }
}

# Step 4: Copy config templates
Write-Host ""
Write-Host "📋 Step 4: Setting up config templates..." -ForegroundColor Cyan

if (Test-Path "nginx.conf") {
    if (-not (Test-Path "config\nginx\nginx.conf")) {
        Copy-Item "nginx.conf" "config\nginx\nginx.conf"
        Write-Host "  ✅ Copied nginx.conf to config/nginx/" -ForegroundColor Green
    }
}

# Step 5: Update .gitignore
Write-Host ""
Write-Host "🔒 Step 5: Verifying .gitignore..." -ForegroundColor Cyan

$gitignoreEntries = @(
    ".env",
    "data/",
    "docker-compose.local.yml",
    "config/nginx/nginx.conf",
    "backups/*.sql",
    "backups/*.dump"
)

$gitignorePath = ".gitignore"
if (Test-Path $gitignorePath) {
    $existingGitignore = Get-Content $gitignorePath
    $updated = $false
    
    foreach ($entry in $gitignoreEntries) {
        if ($existingGitignore -notcontains $entry) {
            Add-Content $gitignorePath $entry
            $updated = $true
            Write-Host "  ✅ Added to .gitignore: $entry" -ForegroundColor Green
        }
    }
    
    if (-not $updated) {
        Write-Host "  ℹ️  .gitignore is already up to date" -ForegroundColor Gray
    }
} else {
    Write-Host "  ⚠️  .gitignore not found" -ForegroundColor Yellow
}

# Step 6: Check Docker
Write-Host ""
Write-Host "🐳 Step 6: Verifying Docker..." -ForegroundColor Cyan

try {
    $dockerVersion = docker --version
    Write-Host "  ✅ Docker is installed: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Docker is not installed or not running!" -ForegroundColor Red
    Write-Host "     Please install Docker Desktop first" -ForegroundColor Yellow
    exit 1
}

try {
    $dockerComposeVersion = docker-compose --version
    Write-Host "  ✅ Docker Compose is installed: $dockerComposeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Docker Compose is not installed!" -ForegroundColor Red
    exit 1
}

# Step 7: Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ SETUP COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1️⃣  Edit .env file with your configuration:" -ForegroundColor Yellow
Write-Host "    code .env" -ForegroundColor White
Write-Host ""
Write-Host "2️⃣  Review and customize nginx.conf (if needed):" -ForegroundColor Yellow
Write-Host "    code config\nginx\nginx.conf" -ForegroundColor White
Write-Host ""
Write-Host "3️⃣  Start the application:" -ForegroundColor Yellow
Write-Host "    Development:  docker-compose -f docker-compose.base.yml -f docker-compose.dev.new.yml up" -ForegroundColor White
Write-Host "    Production:   docker-compose -f docker-compose.base.yml -f docker-compose.prod.new.yml up -d" -ForegroundColor White
Write-Host ""
Write-Host "4️⃣  Or use the deployment script:" -ForegroundColor Yellow
Write-Host "    .\deploy-production.ps1" -ForegroundColor White
Write-Host ""
Write-Host "📖 For more information, see REFACTORING_GUIDE.md" -ForegroundColor Cyan
Write-Host ""
