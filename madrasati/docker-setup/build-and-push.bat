@echo off
echo 🚀 Building and pushing Madrasati Docker images...

REM Set your DockerHub username here
set DOCKERHUB_USERNAME=ihebdhouib

REM Build and tag images
echo 📦 Building Docker images...

echo Building backend...
docker build -t %DOCKERHUB_USERNAME%/madrasati-backend:latest -f Dockerfile.backend ../madrasati

echo Building frontend...
docker build -t %DOCKERHUB_USERNAME%/madrasati-frontend:latest -f Dockerfile.frontend ../../

echo Building face detection...
docker build -t %DOCKERHUB_USERNAME%/madrasati-face-fused:latest -f Dockerfile.face-fused ../

REM Push to DockerHub
echo 📤 Pushing images to DockerHub...
docker push %DOCKERHUB_USERNAME%/madrasati-backend:latest
docker push %DOCKERHUB_USERNAME%/madrasati-frontend:latest
docker push %DOCKERHUB_USERNAME%/madrasati-face-fused:latest

echo ✅ All images built and pushed successfully!
echo 🔗 Images available at:
echo    - %DOCKERHUB_USERNAME%/madrasati-backend:latest
echo    - %DOCKERHUB_USERNAME%/madrasati-frontend:latest
echo    - %DOCKERHUB_USERNAME%/madrasati-face-fused:latest
pause
