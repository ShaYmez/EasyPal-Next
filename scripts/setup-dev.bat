@echo off
REM EasyPal-Next development environment setup (Windows)
REM Copyright (c) 2026 Shane Daley M0VUB (ShaYmez) <shane@freestar.network>

setlocal
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
    echo Python Launcher not found. Install Python 3.12 from https://www.python.org/downloads/
    echo Or run: winget install Python.Python.3.12
    exit /b 1
)

py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.12 not found. Install with: winget install Python.Python.3.12
    exit /b 1
)

echo Creating virtual environment with Python 3.12...
py -3.12 -m venv .venv

echo Installing dependencies...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -e ".[dev]"

echo.
echo Setup complete. Activate with:
echo   .venv\Scripts\activate
echo.
echo Run the app:
echo   python -m easypal_next
echo.
echo Run tests:
echo   pytest
