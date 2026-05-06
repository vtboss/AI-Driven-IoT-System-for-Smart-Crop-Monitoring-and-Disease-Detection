@echo off
:: ============================================================
::  run.bat — Start the CropSense AI Backend (Windows)
::  Double-click this file OR run it from terminal
:: ============================================================

title CropSense AI - Backend Server

echo.
echo  =====================================================
echo   CropSense AI - IoT Crop Monitoring System
echo  =====================================================

:: Check if .env exists
if not exist "backend\.env" (
    echo.
    echo  [ERROR] backend\.env not found!
    echo  Please copy backend\.env.example to backend\.env
    echo  and fill in your NVIDIA API key.
    echo.
    pause
    exit /b 1
)

:: Check if venv exists, use it if so
if exist "venv\Scripts\activate.bat" (
    echo  [*] Activating virtual environment...
    call venv\Scripts\activate.bat
)

:: Install/update dependencies silently
echo  [*] Checking dependencies...
pip install -r backend\requirements.txt -q

:: Start the Flask server
echo  [*] Starting Flask server...
echo  [*] Dashboard: http://localhost:5000/dashboard
echo.
python backend\app.py

pause
