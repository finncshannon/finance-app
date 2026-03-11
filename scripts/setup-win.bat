@echo off
setlocal enabledelayedexpansion

echo.
echo Finance App — Windows Developer Setup
echo =======================================
echo.

:: ─── Navigate to project root ───────────────────────────────────────────────
cd /d "%~dp0\.."

:: ─── 1. Check Node.js 18+ ──────────────────────────────────────────────────
echo [*] Checking for Node.js 18+...
where node >nul 2>&1
if errorlevel 1 (
    echo [X] Node.js is not installed.
    echo.
    echo     Download it from: https://nodejs.org/
    echo     Install the LTS version ^(18+^) and ensure it is added to PATH.
    echo.
    exit /b 1
)

for /f "tokens=1 delims=v" %%a in ('node -v') do set "NODE_RAW=%%a"
for /f "tokens=1 delims=v." %%a in ('node -v') do set "NODE_MAJOR=%%a"
:: node -v returns "v18.x.x" — strip the v prefix for major version
for /f "tokens=2 delims=v." %%a in ('node -v') do set "NODE_MAJOR=%%a"

node -e "process.exit(parseInt(process.version.slice(1))<18?1:0)"
if errorlevel 1 (
    echo [X] Node.js is installed but version is below 18.
    echo     Current:
    node -v
    echo     Download 18+ from: https://nodejs.org/
    exit /b 1
)

for /f "delims=" %%v in ('node -v') do echo [OK] Node.js found: %%v

:: ─── 2. Check Python 3.11+ ─────────────────────────────────────────────────
echo [*] Checking for Python 3.11+...

:: Try 'py -3' first (Windows launcher), then 'python'
set "PYTHON_CMD="

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
    goto :check_py_version
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :check_py_version
)

echo [X] Python is not installed.
echo.
echo     Download it from: https://www.python.org/downloads/
echo     Install Python 3.11+ and check "Add Python to PATH" during install.
echo.
exit /b 1

:check_py_version
:: Verify version is 3.11+
%PYTHON_CMD% -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
    echo [X] Python is installed but version is below 3.11.
    for /f "delims=" %%v in ('%PYTHON_CMD% --version') do echo     Current: %%v
    echo     Download 3.11+ from: https://www.python.org/downloads/
    exit /b 1
)

for /f "delims=" %%v in ('%PYTHON_CMD% --version') do echo [OK] Python found: %%v

:: ─── 3. Install pip dependencies ────────────────────────────────────────────
echo [*] Installing Python dependencies...
if not exist "backend\requirements.txt" (
    echo [X] backend\requirements.txt not found. Are you in the project root?
    exit /b 1
)
%PYTHON_CMD% -m pip install -r backend\requirements.txt
if errorlevel 1 (
    echo [X] Failed to install Python dependencies.
    exit /b 1
)
echo [OK] Python dependencies installed

:: ─── 4. Install npm dependencies ────────────────────────────────────────────
echo [*] Installing npm dependencies...
call npm install
if errorlevel 1 (
    echo [X] Failed to install npm dependencies.
    exit /b 1
)
echo [OK] npm dependencies installed

:: ─── 5. Verify critical Python imports ──────────────────────────────────────
echo [*] Verifying critical Python imports...
%PYTHON_CMD% -c "import fastapi, uvicorn, aiosqlite"
if errorlevel 1 (
    echo [X] Failed to import one or more critical packages.
    echo     Try running: %PYTHON_CMD% -m pip install fastapi uvicorn aiosqlite
    exit /b 1
)
echo [OK] All critical imports verified (fastapi, uvicorn, aiosqlite)

:: ─── Done ───────────────────────────────────────────────────────────────────
echo.
echo =======================================
echo [OK] Setup complete! To start the app:
echo.
echo   Terminal 1: npm run dev:frontend
echo   Terminal 2: npm run dev:electron
echo.

endlocal
