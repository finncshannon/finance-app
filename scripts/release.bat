@echo off
setlocal

set SCRIPT_DIR=%~dp0
set ROOT_DIR=%SCRIPT_DIR%..

echo === Finance App Release Build ===
echo.

rem Step 1: Bundle Python
echo 1. Bundling embedded Python...
node "%SCRIPT_DIR%bundle-python.js"
if errorlevel 1 goto :error
echo.

rem Step 2: Build frontend
echo 2. Building frontend...
cd /d "%ROOT_DIR%\frontend"
call npm run build
if errorlevel 1 goto :error
echo.

rem Step 3: Build Electron TypeScript
echo 3. Compiling Electron main process...
cd /d "%ROOT_DIR%\electron"
call npx tsc
if errorlevel 1 goto :error
echo.

rem Step 4: Package with electron-builder
echo 4. Packaging Electron app...
cd /d "%ROOT_DIR%\electron"
call npx electron-builder --config electron-builder.yml --win --publish always
if errorlevel 1 goto :error
echo.

echo === Release complete ===
echo Check electron\release\ for the installer.
goto :eof

:error
echo.
echo !!! Build failed !!!
exit /b 1
