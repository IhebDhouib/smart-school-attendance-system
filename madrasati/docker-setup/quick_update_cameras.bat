@echo off
echo ===================================================================
echo MADRASATI CAMERA IP QUICK UPDATE
echo ===================================================================
echo.
echo This script helps you quickly update camera IP addresses.
echo.
echo Current camera configuration:
echo.
findstr "CAMERA" .env
echo.
echo ===================================================================
echo QUICK UPDATE OPTIONS:
echo ===================================================================
echo.
set /p entry_ip="Enter new Entry Camera IP (or press Enter to skip): "
set /p exit_ip="Enter new Exit Camera IP (or press Enter to skip): "

if not "%entry_ip%"=="" (
    echo Updating Entry Camera IP to %entry_ip%...
    powershell -Command "(Get-Content .env) -replace '^ENTRY_CAMERA_1=.*', 'ENTRY_CAMERA_1=%entry_ip%' | Set-Content .env"
    echo ✅ Entry camera updated
)

if not "%exit_ip%"=="" (
    echo Updating Exit Camera IP to %exit_ip%...
    powershell -Command "(Get-Content .env) -replace '^EXIT_CAMERA_1=.*', 'EXIT_CAMERA_1=%exit_ip%' | Set-Content .env"
    echo ✅ Exit camera updated
)

if not "%entry_ip%"=="" if not "%exit_ip%"=="" (
    echo.
    echo ===================================================================
    echo NEW CAMERA CONFIGURATION:
    echo ===================================================================
    findstr "CAMERA" .env
    echo.
    echo ===================================================================
    set /p restart="Restart face-detection container now? (y/N): "
    if /i "%restart%"=="y" (
        echo.
        echo 🔄 Restarting face-detection container...
        docker-compose restart face-detection
        echo.
        echo ✅ Container restarted! Showing recent logs:
        echo.
        docker-compose logs --tail=10 face-detection
    ) else (
        echo.
        echo ⚠️ Remember to restart the container to apply changes:
        echo    docker-compose restart face-detection
    )
) else (
    echo.
    echo No changes made.
)

echo.
echo Press any key to exit...
pause >nul
