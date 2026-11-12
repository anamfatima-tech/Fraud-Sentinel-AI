@echo off
title FraudSentinel AI - Credit Card Fraud Detection
echo =======================================================
echo    Starting FraudSentinel AI Enterprise Server
echo =======================================================
echo.

cd /d "%~dp0backend"

:: Check if python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    pause
    exit /b
)

:: Start browser after a brief delay
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:5000"

:: Start Flask server
echo [INFO] Launching Backend Server on http://localhost:5000 ...
python app.py

pause
