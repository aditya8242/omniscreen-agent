@echo off
title OmniScreen Reality Hub
cd /d "%~dp0"

echo ======================================================================
echo              OMNISCREEN: CROSS-DEVICE REALITY HUB
echo ======================================================================

if not exist ".venv\Scripts\python.exe" (
    echo Python virtual environment not found in .venv.
    echo Creating virtual environment and installing dependencies...
    python -m venv .venv
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install -r requirements.txt
)

echo Starting Reality Hub, Win32 Agent, TV Sensor, and Desktop Widget...
.venv\Scripts\python.exe main.py

pause
