#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Finance App Release Build ==="
echo "Root: $ROOT_DIR"
echo ""

# Read version from package.json
VERSION=$(node -e "console.log(require('$ROOT_DIR/package.json').version)")
echo "Version: v$VERSION"
echo ""

# Step 1: Bundle Python
echo "1. Bundling embedded Python..."
node "$SCRIPT_DIR/bundle-python.js"
echo ""

# Step 2: Build frontend
echo "2. Building frontend..."
cd "$ROOT_DIR/frontend"
npm run build
echo ""

# Step 3: Build Electron TypeScript
echo "3. Compiling Electron main process..."
cd "$ROOT_DIR/electron"
npx tsc
echo ""

# Step 4: Package with electron-builder
echo "4. Packaging Electron app..."
cd "$ROOT_DIR/electron"
npx electron-builder --config electron-builder.yml --mac --publish always
echo ""

echo "=== Release v$VERSION complete ==="
echo "Check electron/release/ for the installer."
