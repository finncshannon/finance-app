# Finance App — Packaging & Distribution Plan
## Phase 14: Packaging & Distribution

**Prepared by:** Planner (March 5, 2026)
**Recipient:** PM Agent
**Scope:** Bundle Python into installer, cross-platform builds, distribution mechanism. macOS is optional/deferred.

---

## PLAN SUMMARY

Three workstreams:

1. **Bundle Python into Windows Installer** — Eliminate the external Python dependency so the .exe is fully self-contained
2. **Distribution Setup** — GitHub Releases or simple hosting so the app can be downloaded via a shareable link
3. **macOS Build (Optional/Deferred)** — Electron + Python build for macOS with .dmg output and code signing

---

## AREA 1: BUNDLE PYTHON INTO WINDOWS INSTALLER

### Current Problem
The installer (`Finance App Setup 1.0.0.exe`) requires the user to have Python 3.11+ installed separately. The `electron/main.ts` has a `checkPython()` function that verifies Python is available on startup, but if it's not installed, the app can't run. This makes sharing the app impractical.

### Solution Options

**Option A — Embedded Python Distribution (Recommended):**
- Download the official Python embeddable package (python-3.11.x-embed-amd64.zip, ~15MB)
- Bundle it in `electron/resources/python/` alongside the backend code
- Electron's `main.ts` spawns the backend using this embedded Python instead of the system Python
- The backend's `requirements.txt` dependencies are pre-installed into the embedded distribution via `pip install --target`
- Installer size increases by ~50–80MB (Python + dependencies)

**Option B — PyInstaller:**
- Use PyInstaller to compile the entire FastAPI backend into a standalone `.exe`
- Electron spawns the backend `.exe` instead of `python main.py`
- Cleaner separation but PyInstaller can be finicky with some packages (yfinance, pandas, aiosqlite)
- Installer size similar (~60–100MB)

**Recommend Option A** — more reliable, easier to debug, and allows updating Python packages without rebuilding the entire backend.

### Implementation

#### 1A. Embedded Python Setup
- Download Python 3.11 embeddable package
- Create a build script: `scripts/bundle-python.js` (or `.sh`) that:
  1. Downloads/extracts the embeddable Python
  2. Installs pip into the embedded distribution
  3. Runs `pip install -r backend/requirements.txt --target python/Lib/site-packages`
  4. Copies the result into `electron/resources/python/`
- Add to `electron-builder.yml` extraResources so the Python distribution is included in the installer

#### 1B. Electron Backend Spawning Update
- Modify `electron/main.ts` to use the bundled Python:
  ```typescript
  // Current: spawns system python
  const proc = spawn('python', ['main.py'], { cwd: backendDir });
  
  // New: spawns embedded python
  const pythonPath = path.join(resourcesPath, 'python', 'python.exe');
  const proc = spawn(pythonPath, ['main.py'], { cwd: backendDir });
  ```
- Keep the `checkPython()` fallback: if embedded Python isn't found, try system Python
- Update health check to report which Python is being used

#### 1C. Testing
- Test fresh install on a clean Windows machine (no Python installed)
- Test that all backend features work (Yahoo Finance, SEC EDGAR, SQLite, WebSocket)
- Test that the installer size is reasonable (<150MB total)

**Files touched:**
- `scripts/bundle-python.js` — new build script
- `electron/main.ts` — update Python path resolution
- `electron/electron-builder.yml` — add Python to extraResources
- `backend/requirements.txt` — verify all dependencies are listed

---

## AREA 2: DISTRIBUTION SETUP

### Goal
A shareable download link that anyone (or you on another machine) can use to get the installer.

### Option A — GitHub Releases (Recommended)
- Create a GitHub repository (private or public) for the Finance App
- Use GitHub Releases to host versioned installers
- Each release gets a permanent download URL: `https://github.com/user/finance-app/releases/download/v1.1.0/Finance-App-Setup-1.1.0.exe`
- Share this URL with anyone who needs the app

**Optional: Auto-updater**
- Electron has built-in auto-update support via `electron-updater`
- On app startup, check GitHub Releases for a newer version
- If found, prompt the user to update (download + install in background)
- This means you push a new release to GitHub and everyone's app updates automatically

### Option B — Simple File Hosting
- Upload the `.exe` to Google Drive, Dropbox, or any file host
- Share the link
- No auto-update, manual distribution each time

**Recommend Option A** — GitHub Releases is free, reliable, and enables auto-update for the future.

### Implementation
- Set up GitHub repo (if not already)
- Configure `electron-builder` publish settings for GitHub Releases
- Add a `scripts/release.sh` script that builds the app and publishes to GitHub Releases
- Optionally add `electron-updater` to the app for future auto-update support (can be a stub that just checks, doesn't auto-install)

**Files touched:**
- `electron/electron-builder.yml` — add publish config for GitHub Releases
- `electron/main.ts` — optional: add auto-update check on startup
- `scripts/release.sh` — new release automation script
- `package.json` — add release script

---

## AREA 3: macOS BUILD (OPTIONAL / DEFERRED)

### What's Needed (When You're Ready)
- Electron supports macOS natively — the frontend and Electron layer work as-is
- Python backend also works on macOS (same code, different paths)
- Build configuration for `.dmg` output via `electron-builder`
- **Code signing:** Apple requires notarization for apps distributed outside the App Store. Without it, macOS Gatekeeper blocks the app with "unidentified developer" warning. Notarization requires an Apple Developer account ($99/year) and a signing certificate.
- **Build environment:** macOS builds must run on macOS (or a macOS CI runner like GitHub Actions macOS)

### Estimated Effort
- 1 session: electron-builder macOS config + Python bundling for macOS (use Python framework build instead of embeddable)
- 1 session: Code signing + notarization setup + testing
- Ongoing: CI pipeline for automated macOS builds (GitHub Actions)

### Deferred Until
Finn decides to set up macOS distribution. Can be triggered anytime after Phase 14 Areas 1-2 are complete.

---

## SESSION ORGANIZATION (Recommended for PM)

### Session 14A — Bundle Python + Distribution (Mixed)
**Scope:** Areas 1, 2
**Files:**
- `scripts/bundle-python.js` — new build script
- `electron/main.ts` — embedded Python path
- `electron/electron-builder.yml` — extraResources, publish config
- `backend/requirements.txt` — verify completeness
- `scripts/release.sh` — new release script
- `package.json` — release script
**Complexity:** Medium (build tooling, path resolution, installer testing)
**Estimated acceptance criteria:** 12–15
**Note:** Requires testing on a clean Windows machine

### Session 14B — macOS Build (Optional, Deferred)
**Scope:** Area 3
**Files:** electron-builder macOS config, Python framework bundling, code signing scripts
**Complexity:** Medium-High (code signing is the hard part)
**Estimated acceptance criteria:** 10–12
**Prerequisites:** Apple Developer account, access to macOS build machine
**Status:** DEFERRED until Finn initiates

---

## DECISIONS MADE

1. Embedded Python distribution (not PyInstaller) for Windows bundling
2. GitHub Releases for distribution — shareable download links, enables future auto-update
3. macOS build deferred — can be done anytime after Windows distribution works
4. Auto-updater is optional/future — stub it now, implement fully later
5. Target installer size: <150MB (Python + dependencies + frontend + Electron)
6. Fallback: if embedded Python not found, try system Python (backward compatible)

---

*End of Packaging & Distribution Plan*
*Phase 14A (14B deferred) · Prepared March 5, 2026*
