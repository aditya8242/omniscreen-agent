@echo off
title Build OmniScreen Single-File Windows App
cd /d "%~dp0"

echo ======================================================================
echo       OMNISCREEN WINDOWS STANDALONE BUILDER (Single-File .exe)
echo ======================================================================

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found in .venv. Run run.bat once first.
    pause
    exit /b 1
)

echo Ensuring PyInstaller and pystray are installed...
.venv\Scripts\python.exe -m pip show pyinstaller >nul 2>&1 || .venv\Scripts\python.exe -m pip install pyinstaller
.venv\Scripts\python.exe -m pip show pystray >nul 2>&1 || .venv\Scripts\python.exe -m pip install pystray

echo Building single-file, zero-terminal dist\OmniScreen.exe...
.venv\Scripts\pyinstaller.exe ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --noconsole ^
    --name "OmniScreen" ^
    --icon "assets\omniscreen.ico" ^
    --add-data "assets\logo.svg;assets" ^
    --add-data "assets\icon-192.png;assets" ^
    --hidden-import "pystray._win32" ^
    --hidden-import "PIL._tkinter_finder" ^
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

echo Generating SHA-256 checksum for dist\OmniScreen.exe...
powershell -NoProfile -Command "(Get-FileHash 'dist\OmniScreen.exe' -Algorithm SHA256).Hash.ToLower() + '  OmniScreen.exe' | Out-File -Encoding ascii 'dist\OmniScreen.exe.sha256'"

echo.
echo [SUCCESS] Single-file Windows app ready at: dist\OmniScreen.exe
echo [CHECKSUM] dist\OmniScreen.exe.sha256
echo Upload dist\OmniScreen.exe + OmniScreenAgent-release.apk to GitHub Releases.
pause
