@echo off
echo 🚀 Building Madrasati with local frontend build...

REM Set your DockerHub username
set DOCKERHUB_USERNAME=ihebdhouib

echo 📦 Step 1: Building Angular frontend locally...
cd ..\madrasati\madrassati
call npm run build --prod

if %ERRORLEVEL% neq 0 (
    echo ❌ Frontend build failed!
    pause
    exit /b 1
)

echo ✅ Frontend build completed!

cd ..\..\docker-setup

echo 📦 Step 2: Building Docker images...

echo Building backend...
docker build -t %DOCKERHUB_USERNAME%/madrasati-backend:latest -f Dockerfile.backend ../madrasati

echo Building frontend (using pre-built files)...
docker build -t %DOCKERHUB_USERNAME%/madrasati-frontend:latest -f Dockerfile.frontend.simple ../../

echo Building face detection...
docker build -t %DOCKERHUB_USERNAME%/madrasati-face-fused:latest -f Dockerfile.face-fused ../

echo 📤 Step 3: Pushing images to DockerHub...
docker push %DOCKERHUB_USERNAME%/madrasati-backend:latest
docker push %DOCKERHUB_USERNAME%/madrasati-frontend:latest
docker push %DOCKERHUB_USERNAME%/madrasati-face-fused:latest

echo ✅ All images built and pushed successfully!
echo 🔗 Images available at:
echo    - %DOCKERHUB_USERNAME%/madrasati-backend:latest
echo    - %DOCKERHUB_USERNAME%/madrasati-frontend:latest
echo    - %DOCKERHUB_USERNAME%/madrasati-face-fused:latest
pause
