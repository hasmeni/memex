@echo off
title ironyLabs Memex - Standalone
echo.
echo ============================================
echo   ironyLabs Memex - Standalone Setup
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

:: Install dependencies if needed
if not exist "standalone\venv" (
    echo Creating virtual environment...
    python -m venv standalone\venv
    echo Installing dependencies...
    standalone\venv\Scripts\pip install -r standalone\requirements.txt
) else (
    echo Virtual environment found.
)

echo.
echo Starting ironyLabs Memex...
echo.
standalone\venv\Scripts\python standalone\run.py
pause
