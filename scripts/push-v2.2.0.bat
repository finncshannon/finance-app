@echo off
cd /d "G:\Claude Access Point\StockValuation\Finance App"

echo === Spectre v2.2.0 — Git Push ===
echo.

echo 1. Staging all changes...
git add -A
echo.

echo 2. Committing...
git commit -m "v2.2.0 — World Markets globe, international news engine, boot sequence, macOS support"
echo.

echo 3. Tagging v2.2.0...
git tag -a v2.2.0 -m "Spectre v2.2.0"
echo.

echo 4. Pushing to GitHub...
git push origin main
git push origin v2.2.0
echo.

echo === Done ===
echo.
echo Next steps:
echo   1. Go to https://github.com/finncshannon/finance-app/releases/new
echo   2. Select tag v2.2.0
echo   3. Paste release notes
echo   4. Publish
echo.
pause
