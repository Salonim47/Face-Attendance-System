@echo off
title Biometric Attendance System Launcher
echo ===================================================
echo        BIOMETRIC ATTENDANCE SYSTEM LAUNCHER
echo ===================================================
echo Checking Python installation...

py --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python launcher (py) was not found.
    echo Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

echo [OK] Python detected.
echo.
echo Verifying package manager (pip)...
py -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Pip package manager not ready.
    pause
    exit /b 1
)

echo.
echo Installing/Verifying Biometric Dependencies...
echo [IMPORTANT]: Standard 'opencv-python' is replaced with 'opencv-contrib-python' 
echo to enable local LBPH face recognition libraries. Uninstalling conflicts...
echo.
py -m pip uninstall -y opencv-python >nul 2>&1
py -m pip install opencv-contrib-python fastapi uvicorn
if %errorlevel% neq 0 (
    echo [ERROR] Dependency installation failed. Check internet access.
    pause
    exit /b 1
)

echo.
echo ===================================================
echo Starting Biometric Backend Server...
echo Server starting on: http://127.0.0.1:8000
echo.
echo [INSTRUCTION]:
echo Open "index.html" in your web browser to view the attendance dashboard!
echo ===================================================
echo.
py app.py
pause
