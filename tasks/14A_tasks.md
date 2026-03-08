# Session 14A — Bundle Python + GitHub Releases Distribution
## Phase 14: Packaging & Distribution

**Priority:** Last (runs after ALL feature phases are complete and tested)
**Type:** Mixed (Build Tooling + Electron Config)
**Depends On:** All feature phases (7–11) complete
**Spec Reference:** `specs/phase14_packaging_distribution.md` → Areas 1, 2

---

## SCOPE SUMMARY

Bundle an embedded Python distribution into the Electron app so users don't need Python installed separately. Update Electron's backend spawning to use the bundled Python. Set up GitHub Releases for distribution with a shareable download link. Add a build/release script.

---

## TASKS

### Task 1: Embedded Python Build Script
**Description:** Create a build script that downloads the Python 3.11 embeddable package, installs pip and all backend dependencies into it, and places it in `electron/resources/python/` for bundling.

**Subtasks:**
- [ ] 1.1 — Create `scripts/bundle-python.js` (or `.sh`):
  - Download Python 3.11.x embeddable package (`python-3.11.x-embed-amd64.zip`, ~15MB) from python.org
  - Extract to `electron/resources/python/`
  - Install pip into the embedded distribution (download `get-pip.py`, run with embedded python)
  - Uncomment `import site` in `python311._pth` file (required for pip to work in embeddable mode)
  - Run `pip install -r backend/requirements.txt --target electron/resources/python/Lib/site-packages`
  - Verify all key packages installed: `fastapi`, `uvicorn`, `yfinance`, `pandas`, `aiosqlite`, `pydantic`
- [ ] 1.2 — Verify `backend/requirements.txt` is complete — every dependency the backend uses must be listed.
- [ ] 1.3 — Add a `.gitignore` entry for `electron/resources/python/` (don't commit the bundled Python to git).

---

### Task 2: Electron Backend Spawning Update
**Description:** Update `electron/main.ts` to spawn the backend using the bundled Python instead of requiring system Python.

**Subtasks:**
- [ ] 2.1 — In `electron/main.ts`, update the Python path resolution:
  ```typescript
  function getPythonPath(): string {
    // Try embedded Python first
    const embeddedPath = path.join(
      process.resourcesPath || path.join(__dirname, '..', 'resources'),
      'python', 'python.exe'
    );
    if (fs.existsSync(embeddedPath)) {
      return embeddedPath;
    }
    // Fallback to system Python
    return 'python';
  }
  ```
  Use this in the spawn call instead of hardcoded `'python'`.

- [ ] 2.2 — Update the `checkPython()` function to report which Python is being used (embedded vs system) in its log output.
- [ ] 2.3 — Update the health check / startup log to show the Python version and path being used.

---

### Task 3: Electron Builder Configuration
**Description:** Configure electron-builder to include the bundled Python in the installer and set up GitHub Releases publishing.

**Subtasks:**
- [ ] 3.1 — In `electron/electron-builder.yml`, add the Python distribution to `extraResources`:
  ```yaml
  extraResources:
    - from: "resources/python"
      to: "python"
      filter:
        - "**/*"
    - from: "../backend"
      to: "backend"
      filter:
        - "**/*"
        - "!**/__pycache__"
        - "!**/*.pyc"
  ```

- [ ] 3.2 — Add GitHub Releases publish configuration:
  ```yaml
  publish:
    provider: github
    owner: "{github-username}"
    repo: "finance-app"
    releaseType: release
  ```

- [ ] 3.3 — Update `package.json` with a release script:
  ```json
  "scripts": {
    "bundle-python": "node scripts/bundle-python.js",
    "build": "npm run bundle-python && electron-builder --win",
    "release": "npm run bundle-python && electron-builder --win --publish always"
  }
  ```

---

### Task 4: Release Automation Script
**Description:** Create a script that builds the app and publishes to GitHub Releases.

**Subtasks:**
- [ ] 4.1 — Create `scripts/release.sh` (or `.bat` for Windows):
  ```bash
  #!/bin/bash
  set -e
  echo "=== Finance App Release Build ==="
  echo "1. Bundling Python..."
  node scripts/bundle-python.js
  echo "2. Building Electron app..."
  npx electron-builder --win --publish always
  echo "=== Release complete ==="
  ```

- [ ] 4.2 — Add a version bump step: read version from `package.json`, ensure it matches the `electron-builder.yml` version, and tag the git commit.

---

### Task 5: Auto-Update Stub (Optional)
**Description:** Add a minimal auto-update check on app startup that checks GitHub Releases for a newer version. Does NOT auto-install — just notifies the user.

**Subtasks:**
- [ ] 5.1 — In `electron/main.ts`, add a version check on startup:
  ```typescript
  async function checkForUpdates() {
    try {
      const response = await fetch('https://api.github.com/repos/{owner}/{repo}/releases/latest');
      const release = await response.json();
      const latestVersion = release.tag_name?.replace('v', '');
      const currentVersion = app.getVersion();
      if (latestVersion && latestVersion !== currentVersion) {
        // Send notification to renderer
        mainWindow?.webContents.send('update-available', {
          currentVersion,
          latestVersion,
          downloadUrl: release.html_url,
        });
      }
    } catch {
      // Silently fail — update check is non-critical
    }
  }
  ```
  Call after the main window is loaded. This is a stub — full auto-download/install can be added later with `electron-updater`.

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: `scripts/bundle-python.js` successfully downloads and sets up embedded Python 3.11 with all backend dependencies.
- [ ] AC-2: Embedded Python located at `electron/resources/python/python.exe` after build.
- [ ] AC-3: All backend dependencies installed in embedded Python's site-packages.
- [ ] AC-4: `electron/main.ts` uses embedded Python when available, falls back to system Python.
- [ ] AC-5: App launches and backend starts successfully using embedded Python on a clean machine (no system Python).
- [ ] AC-6: All backend features work with embedded Python: Yahoo Finance, SEC EDGAR, SQLite, WebSocket.
- [ ] AC-7: Installer size is reasonable (<150MB).
- [ ] AC-8: `electron-builder.yml` includes Python in extraResources.
- [ ] AC-9: GitHub Releases publish configuration present.
- [ ] AC-10: `npm run build` produces a working installer.
- [ ] AC-11: `npm run release` builds and publishes to GitHub Releases.
- [ ] AC-12: Health check reports which Python is being used (embedded vs system).

---

## FILES TOUCHED

**New files:**
- `scripts/bundle-python.js` — Python embedding build script
- `scripts/release.sh` — release automation script

**Modified files:**
- `electron/main.ts` — embedded Python path resolution, checkPython update, optional auto-update stub
- `electron/electron-builder.yml` — extraResources for Python + backend, GitHub Releases publish config
- `package.json` — add bundle-python, build, release scripts
- `.gitignore` — add `electron/resources/python/`

---

## BUILDER PROMPT

> **Session 14A — Bundle Python + GitHub Releases Distribution**
>
> You are building session 14A of the Finance App v2.0 update. **This session runs LAST after all features are complete and tested.**
>
> **What you're doing:** Making the app self-contained and distributable: (1) Bundle an embedded Python distribution so users don't need Python installed, (2) Update Electron to use bundled Python, (3) Set up GitHub Releases for distribution.
>
> **Context:** Currently the installer requires users to have Python 3.11+ installed separately. `electron/main.ts` spawns `python main.py` using system Python. This makes sharing impractical. The fix: ship Python inside the app.
>
> **Existing code:**
>
> `electron/main.ts`:
> - `checkPython()` — verifies Python is available on PATH, shows error dialog if not
> - Backend spawn: `spawn('python', ['main.py'], { cwd: backendDir })` — uses system Python
> - Health check: pings `http://localhost:8000/api/v1/system/health` until backend responds
>
> `electron/electron-builder.yml`:
> - Existing build configuration for Windows (NSIS installer)
> - Has `extraResources` for the backend directory
> - Does NOT currently bundle Python
>
> `backend/requirements.txt` — lists all Python dependencies
>
> `package.json` — has existing build scripts for Electron
>
> **Cross-cutting rules:**
> - This session has no display name or data format rules — it's purely build tooling.
>
> **Task 1: Bundle Script** — `scripts/bundle-python.js`: download Python 3.11 embeddable, install pip, install requirements into it, output to `electron/resources/python/`.
>
> **Task 2: Electron Update** — `main.ts`: try embedded Python first (`resources/python/python.exe`), fall back to system Python. Log which is used.
>
> **Task 3: Builder Config** — `electron-builder.yml`: add Python to extraResources, add GitHub Releases publish config.
>
> **Task 4: Release Script** — `scripts/release.sh`: bundle Python → build Electron → publish.
>
> **Task 5: Auto-Update Stub** — Optional: check GitHub Releases API for newer version on startup, notify user (don't auto-install).
>
> **Acceptance criteria:**
> 1. Embedded Python bundled with all dependencies
> 2. App works on clean Windows (no system Python)
> 3. All backend features work
> 4. Installer < 150MB
> 5. GitHub Releases publish configured
> 6. Build + release scripts work
>
> **Files to create:** `scripts/bundle-python.js`, `scripts/release.sh`
> **Files to modify:** `electron/main.ts`, `electron/electron-builder.yml`, `package.json`, `.gitignore`
>
> **Technical constraints:**
> - Python embeddable package: `python-3.11.x-embed-amd64.zip` from python.org/downloads
> - Must uncomment `import site` in `python311._pth` for pip/site-packages to work
> - `pip install --target` puts packages in specified directory
> - `process.resourcesPath` in Electron points to the resources directory in packaged app
> - `fs.existsSync()` for checking embedded Python presence
> - GitHub Releases API: `https://api.github.com/repos/{owner}/{repo}/releases/latest`
> - electron-builder publish: `provider: github` with owner + repo
> - Keep system Python fallback for development mode (when running unpackaged)
