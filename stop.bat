@echo off
title Stop OmniScreen
cd /d "%~dp0"

echo Stopping any running OmniScreen instances on port 8765...

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8765" ^| findstr "LISTENING"') do (
    echo Terminating process PID %%a listening on port 8765...
    taskkill /F /PID %%a
)

echo OmniScreen stopped.
timeout /t 2 >nul
