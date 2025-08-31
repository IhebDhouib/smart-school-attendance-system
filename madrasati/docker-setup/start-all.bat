@echo off
echo Starting Madrasati School Management System...
echo.

echo Building and starting all services...
docker-compose up -d

echo.
echo Waiting for services to start...
timeout /t 10 /nobreak >nul

echo.
echo Checking service status...
docker-compose ps

echo.
echo Services should be available at:
echo - Frontend: http://localhost
echo - Backend API: http://localhost:3000
echo - WebSocket: ws://localhost:3001  
echo - Face Detection API: http://localhost:5001
echo - Face API: http://localhost:5000
echo.

echo To view logs: docker-compose logs -f [service-name]
echo To stop all: docker-compose down
echo.
