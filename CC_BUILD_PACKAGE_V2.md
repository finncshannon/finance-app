# Finance App v2.0 — Build & Package Prompt

You are packaging the Finance App v2.0 for distribution. All code changes are already implemented. Your job is to compile the frontend, build the Electron app, and produce a working installer.

## Project Location
```
C:\Claude Access Point\StockValuation\Finance App
```

## What You're Doing

1. Bump the version from 1.0.0 to 2.0.0
2. Build the frontend (Vite)
3. Build the Electron main process (TypeScript → JS)
4. Verify embedded Python is bundled (should already be at `electron/resources/python/`)
5. Package the full app into an NSIS installer
6. Verify the installer was produced

## Steps

### Step 1: Version Bump

Update version to `2.0.0` in these files:
- `package.json` (root)
- `electron/package.json`
- `frontend/package.json` (if it has a version field)

### Step 2: Install Dependencies (if needed)

```bash
cd "C:\Claude Access Point\StockValuation\Finance App"
npm install
cd frontend && npm install && cd ..
cd electron && npm install && cd ..
```

### Step 3: Build Frontend

```bash
cd "C:\Claude Access Point\StockValuation\Finance App\frontend"
npm run build
```

This compiles React + TypeScript into `frontend/dist/`. Verify `frontend/dist/index.html` exists after.

### Step 4: Build Electron

```bash
cd "C:\Claude Access Point\StockValuation\Finance App\electron"
npm run build
```

This compiles `main.ts` → `dist/main.js`. Verify `electron/dist/main.js` exists after.

### Step 5: Verify Embedded Python

Check that `electron/resources/python/python.exe` exists. If it does, skip this step. If it doesn't:

```bash
cd "C:\Claude Access Point\StockValuation\Finance App"
node scripts/bundle-python.js
```

This downloads Python 3.11 embeddable and installs all backend dependencies into it. Takes a few minutes.

### Step 6: Package

```bash
cd "C:\Claude Access Point\StockValuation\Finance App\electron"
npx electron-builder --config electron-builder.yml --win
```

This produces:
- `electron/release/Finance App Setup 2.0.0.exe` — the NSIS installer
- `electron/release/win-unpacked/` — the unpacked app

### Step 7: Verify

Confirm these exist:
- `electron/release/Finance App Setup 2.0.0.exe`
- `electron/release/win-unpacked/Finance App.exe`

Report the installer file size.

## Important Notes

- The `electron-builder.yml` has `publish: provider: github` with `owner: your-username`. This is a placeholder — the build will still work locally, it just won't publish to GitHub. That's fine for now.
- If any build step fails, read the error carefully. Common issues:
  - Missing node_modules → run `npm install` in the relevant directory
  - TypeScript errors → these would indicate code issues, report them
  - Python bundle issues → check if `electron/resources/python/python.exe` already exists
- Do NOT run `--publish always` — we're just building locally, not publishing to GitHub.

## After Building

Run the installer (`Finance App Setup 2.0.0.exe`) to install the updated app. It creates a Start Menu shortcut and optionally a desktop shortcut. Click the shortcut → the app opens with all v2.0 features.
