@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo Python not found. Install Python and make sure the "py" command is available.
    pause
    exit /b 1
)

where ffmpeg >nul 2>nul
if errorlevel 1 (
    echo FFmpeg not found in PATH. Install FFmpeg and restart your terminal.
    pause
    exit /b 1
)

py main.py %*
if errorlevel 1 (
    echo.
    echo If the script still fails, run this once manually:
    echo py -m pip install -r requirements.txt
    pause
)
