@echo off
echo ========================================
echo Madrasati Face-Fused Development Runner
echo ========================================
echo.

cd /d "%~dp0"

echo Checking if development image exists...
docker images | findstr "madrasati_face_fused" >nul
if %ERRORLEVEL% NEQ 0 (
    echo Development image not found. Building first...
    call build-dev.bat
    if %ERRORLEVEL% NEQ 0 (
        echo Build failed. Exiting.
        pause
        exit /b 1
    )
) else (
    echo ✅ Development image found.
)

echo.
echo 🚀 Starting face-fused in development mode...
echo    (Press Ctrl+C to stop)
echo.

docker-compose -f docker-compose.dev.yml up face-fused

echo.
echo 🛑 Service stopped.
echo 💡 Your code changes are automatically reflected!
pause
