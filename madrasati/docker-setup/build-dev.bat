@echo off
echo ========================================
echo Madrasati Face-Fused Development Setup
echo ========================================
echo.

echo Building face-fused service in DEVELOPMENT mode...
echo This will enable live code reloading for development.
echo.

cd /d "%~dp0"

echo Step 1: Building Docker image...
docker-compose -f docker-compose.dev.yml build face-fused

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Build successful!
    echo.
    echo 🚀 To start the development environment:
    echo    docker-compose -f docker-compose.dev.yml up face-fused
    echo.
    echo 📝 Development features:
    echo    • Live code reloading (no rebuild needed)
    echo    • Source code mounted as volumes
    echo    • Changes reflect immediately
    echo    • Full debugging capabilities
    echo.
    echo 🛑 To stop: Ctrl+C or docker-compose -f docker-compose.dev.yml down
) else (
    echo.
    echo ❌ Build failed! Check the error messages above.
    pause
)
