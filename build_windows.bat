@echo off
title Build OmniScreen Windows Standalone Package
cd /d "%~dp0"

echo ======================================================================
echo        OMNISCREEN WINDOWS STANDALONE PACKAGER (PyInstaller)
echo ======================================================================

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found in .venv. Run run.bat once first.
    pause
    exit /b 1
)

echo Checking PyInstaller...
.venv\Scripts\python.exe -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller into .venv...
    .venv\Scripts\python.exe -m pip install pyinstaller
)

echo Building OmniScreen.exe with official icon...
.venv\Scripts\pyinstaller.exe ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --name "OmniScreen" ^
    --icon "assets\omniscreen.ico" ^
    --add-data "assets\logo.svg;assets" ^
    --hidden-import "uvicorn.logging" ^
    --hidden-import "uvicorn.loops" ^
    --hidden-import "uvicorn.loops.auto" ^
    --hidden-import "uvicorn.protocols" ^
    --hidden-import "uvicorn.protocols.http" ^
    --hidden-import "uvicorn.protocols.http.auto" ^
    --hidden-import "uvicorn.lifespan" ^
    --hidden-import "uvicorn.lifespan.on" ^
    main.py

if errorlevel 1 (
    echo [ERROR] Build failed. Check output above.
    pause
    exit /b 1
)

copy /Y "setup_firewall.bat" "dist\OmniScreen\setup_firewall.bat" >nul
copy /Y "stop.bat" "dist\OmniScreen\stop.bat" >nul

echo.
echo [SUCCESS] Standalone Windows build ready at: dist\OmniScreen\OmniScreen.exe
echo Zip the dist\OmniScreen folder (or wrap with Inno Setup) to publish on GitHub Releases.
pause
