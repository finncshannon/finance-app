process.on('uncaughtException', (error) => {
  console.error('[main] Uncaught exception:', error);
});
process.on('unhandledRejection', (reason) => {
  console.error('[main] Unhandled rejection:', reason);
});

import { app, BrowserWindow, ipcMain, dialog } from 'electron';
import { spawn, execSync, ChildProcess } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import * as http from 'http';

// --- Configuration ---
const BACKEND_HOST = '127.0.0.1';
const BACKEND_PORT = 8000;
const HEALTH_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}/api/v1/system/health`;
const HEALTH_POLL_INTERVAL_MS = 100;
const BACKEND_START_TIMEOUT_MS = 30000;
const SHUTDOWN_GRACE_PERIOD_MS = 2000;
const DEV_SERVER_URL = 'http://localhost:5174';

// --- Layout breakpoints ---
const LAYOUT_COMPACT = 1200;
const LAYOUT_WIDE = 1600;

// --- State ---
let mainWindow: BrowserWindow | null = null;
let backendProcess: ChildProcess | null = null;
let backendReady = false;
let backendStderr = '';
let resolvedPythonCmd = 'python';

// --- Embedded Python Resolution ---
function getEmbeddedPythonPath(): string | null {
  const binaryName = process.platform === 'win32' ? 'python.exe' : 'python3';
  const resourcesPath = process.resourcesPath || path.join(__dirname, '..', 'resources');
  const embeddedPath = path.join(resourcesPath, 'python', binaryName);
  if (fs.existsSync(embeddedPath)) {
    return embeddedPath;
  }
  // Also check dev-time location (electron/resources/python/)
  const devPath = path.join(__dirname, '..', 'resources', 'python', binaryName);
  if (fs.existsSync(devPath)) {
    return devPath;
  }
  return null;
}

// --- Python Dependency Check ---
interface PythonCheckResult {
  ok: boolean;
  pythonCmd: string;
  version: string;
  source: 'embedded' | 'system';
  error?: string;
}

function checkPython(): PythonCheckResult {
  // 1. Try embedded Python first
  const embeddedPath = getEmbeddedPythonPath();
  if (embeddedPath) {
    try {
      const output = execSync(`"${embeddedPath}" --version`, {
        encoding: 'utf-8',
        timeout: 5000,
        windowsHide: true,
      }).trim();

      const match = output.match(/Python\s+(\d+)\.(\d+)\.(\d+)/);
      if (match) {
        const version = `${match[1]}.${match[2]}.${match[3]}`;
        console.log(`[python] Found embedded Python ${version} at ${embeddedPath}`);
        return { ok: true, pythonCmd: embeddedPath, version, source: 'embedded' };
      }
    } catch {
      console.log('[python] Embedded Python found but failed to execute, falling back to system');
    }
  }

  // 2. Fall back to system Python
  const candidates = process.platform === 'win32'
    ? ['py -3', 'python', 'python3']
    : ['python3', 'python'];

  for (const cmd of candidates) {
    try {
      const output = execSync(`${cmd} --version`, {
        encoding: 'utf-8',
        timeout: 5000,
        windowsHide: true,
      }).trim();

      const match = output.match(/Python\s+(\d+)\.(\d+)\.(\d+)/);
      if (!match) continue;

      const major = parseInt(match[1]!, 10);
      const minor = parseInt(match[2]!, 10);
      const version = `${match[1]}.${match[2]}.${match[3]}`;

      if (major < 3 || (major === 3 && minor < 11)) {
        return {
          ok: false,
          pythonCmd: cmd,
          version,
          source: 'system',
          error: `Python ${version} found but 3.11+ is required.`,
        };
      }

      // Check critical imports
      try {
        execSync(
          `${cmd} -c "import fastapi, uvicorn, aiosqlite"`,
          { encoding: 'utf-8', timeout: 30000, windowsHide: true }
        );
      } catch {
        return {
          ok: false,
          pythonCmd: cmd,
          version,
          source: 'system',
          error: `Python ${version} found but required packages are missing.\n\nRun:\n  ${cmd} -m pip install -r requirements.txt`,
        };
      }

      console.log(`[python] Using system Python ${version} (${cmd})`);
      return { ok: true, pythonCmd: cmd, version, source: 'system' };
    } catch {
      continue;
    }
  }

  return {
    ok: false,
    pythonCmd: '',
    version: '',
    source: 'system',
    error: 'Python 3.11+ not found on your system.\n\nInstall from: https://www.python.org/downloads/\nEnsure Python is added to your system PATH.',
  };
}

// --- Auto-Update Check (Stub) ---
const GITHUB_OWNER = 'finncshannon';
const GITHUB_REPO = 'finance-app';

async function checkForUpdates(): Promise<void> {
  try {
    const { net } = require('electron');
    const response = await net.fetch(
      `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/releases/latest`,
      { headers: { 'User-Agent': 'FinanceApp' } }
    );
    if (!response.ok) return;
    const release = await response.json();
    const latestVersion = release.tag_name?.replace(/^v/, '');
    const currentVersion = app.getVersion();
    if (latestVersion && latestVersion !== currentVersion) {
      console.log(`[update] New version available: v${latestVersion} (current: v${currentVersion})`);
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

// --- Window State Persistence ---
interface WindowState {
  x?: number;
  y?: number;
  width: number;
  height: number;
  isMaximized: boolean;
}

function getWindowStatePath(): string {
  return path.join(app.getPath('userData'), 'window-state.json');
}

function loadWindowState(): WindowState {
  const defaults: WindowState = {
    width: 1400,
    height: 900,
    isMaximized: false,
  };

  try {
    const statePath = getWindowStatePath();
    if (fs.existsSync(statePath)) {
      const data = fs.readFileSync(statePath, 'utf-8');
      const saved = JSON.parse(data) as Partial<WindowState>;
      return { ...defaults, ...saved };
    }
  } catch {
    // Fall through to defaults
  }

  return defaults;
}

function saveWindowState(): void {
  if (!mainWindow || mainWindow.isDestroyed()) return;

  const state: WindowState = {
    isMaximized: mainWindow.isMaximized(),
    width: 1400,
    height: 900,
  };

  if (!mainWindow.isMaximized()) {
    const bounds = mainWindow.getBounds();
    state.x = bounds.x;
    state.y = bounds.y;
    state.width = bounds.width;
    state.height = bounds.height;
  }

  try {
    fs.writeFileSync(getWindowStatePath(), JSON.stringify(state, null, 2));
  } catch {
    // Silently fail — non-critical
  }
}

// --- Layout Detection ---
function getLayoutMode(width: number): string {
  if (width < LAYOUT_COMPACT) return 'compact';
  if (width > LAYOUT_WIDE) return 'wide';
  return 'standard';
}

function notifyLayoutChange(): void {
  if (!mainWindow) return;
  const [width] = mainWindow.getSize();
  const mode = getLayoutMode(width);
  mainWindow.webContents.send('layout-change', mode);
}

// --- Backend Process Management ---
function startBackend(): void {
  const isDev = !app.isPackaged;
  const backendDir = isDev
    ? path.join(__dirname, '..', '..', 'backend')
    : path.join(process.resourcesPath, 'backend');

  backendStderr = '';

  // Resolve executable and args. Embedded Python is an absolute path;
  // system Python may be 'py -3' (needs splitting) or just 'python'.
  let executable: string;
  let extraArgs: string[];
  if (fs.existsSync(resolvedPythonCmd)) {
    // Absolute path to embedded python.exe — don't split
    executable = resolvedPythonCmd;
    extraArgs = [];
  } else {
    // System command — may be 'py -3'
    const cmdParts = resolvedPythonCmd.split(' ');
    executable = cmdParts[0]!;
    extraArgs = cmdParts.slice(1);
  }

  backendProcess = spawn(
    executable,
    [...extraArgs, '-m', 'uvicorn', 'main:app', '--host', BACKEND_HOST, '--port', String(BACKEND_PORT)],
    {
      cwd: backendDir,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    }
  );

  backendProcess.stdout?.on('data', (data: Buffer) => {
    console.log(`[backend] ${data.toString().trim()}`);
  });

  backendProcess.stderr?.on('data', (data: Buffer) => {
    const text = data.toString().trim();
    console.error(`[backend] ${text}`);
    backendStderr += text + '\n';
  });

  backendProcess.on('exit', (code, signal) => {
    console.log(`[backend] exited with code=${code} signal=${signal}`);
    if (backendReady && mainWindow && !mainWindow.isDestroyed()) {
      // Backend crashed while running — attempt restart
      console.log('[backend] Unexpected exit, restarting...');
      backendReady = false;
      startBackend();
      waitForBackend();
    }
  });
}

function waitForBackend(): Promise<void> {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    let resolved = false;

    const poll = () => {
      if (resolved) return;
      if (Date.now() - startTime > BACKEND_START_TIMEOUT_MS) {
        reject(new Error(`Backend failed to start within ${BACKEND_START_TIMEOUT_MS}ms`));
        return;
      }

      const req = http.get(HEALTH_URL, (res) => {
        if (resolved) return;
        if (res.statusCode === 200) {
          resolved = true;
          backendReady = true;
          console.log('[backend] Health check passed — backend ready');
          resolve();
        } else {
          setTimeout(poll, HEALTH_POLL_INTERVAL_MS);
        }
      });

      req.on('error', () => {
        if (!resolved) setTimeout(poll, HEALTH_POLL_INTERVAL_MS);
      });

      req.setTimeout(500, () => {
        if (!resolved) {
          req.destroy();
          setTimeout(poll, HEALTH_POLL_INTERVAL_MS);
        }
      });
    };

    poll();
  });
}

function stopBackend(): Promise<void> {
  return new Promise((resolve) => {
    if (!backendProcess || backendProcess.killed) {
      resolve();
      return;
    }

    const forceKillTimer = setTimeout(() => {
      if (backendProcess && !backendProcess.killed) {
        console.log('[backend] Force killing after grace period');
        backendProcess.kill('SIGKILL');
      }
      resolve();
    }, SHUTDOWN_GRACE_PERIOD_MS);

    backendProcess.once('exit', () => {
      clearTimeout(forceKillTimer);
      resolve();
    });

    // Send SIGTERM for graceful shutdown
    backendProcess.kill('SIGTERM');
  });
}

// --- Window Creation ---
function createWindow(): void {
  const state = loadWindowState();

  mainWindow = new BrowserWindow({
    width: state.width,
    height: state.height,
    x: state.x,
    y: state.y,
    minWidth: 800,
    minHeight: 600,
    backgroundColor: '#0D0D0D',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  if (state.isMaximized) {
    mainWindow.maximize();
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
  });

  // Debug: log page load events
  mainWindow.webContents.on('did-fail-load', (_e, code, desc, url) => {
    console.error(`[window] Failed to load: ${url} (${code}: ${desc})`);
  });

  mainWindow.on('resize', () => {
    notifyLayoutChange();
  });

  mainWindow.on('close', () => {
    saveWindowState();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

async function loadApp(): Promise<void> {
  if (!mainWindow) return;

  const isDev = !app.isPackaged;

  if (isDev) {
    mainWindow.loadURL(DEV_SERVER_URL);
  } else {
    mainWindow.loadFile(path.join(process.resourcesPath, 'frontend', 'dist', 'index.html'));
  }
}

// --- IPC Handlers ---
function setupIPC(): void {
  ipcMain.handle('get-backend-url', () => {
    return `http://${BACKEND_HOST}:${BACKEND_PORT}`;
  });

  ipcMain.handle('get-layout-mode', () => {
    if (!mainWindow) return 'standard';
    const [width] = mainWindow.getSize();
    return getLayoutMode(width);
  });

  ipcMain.handle('is-backend-ready', () => {
    return backendReady;
  });
}

// --- App Lifecycle ---
app.whenReady().then(async () => {
  setupIPC();
  createWindow();

  // Check Python before starting backend
  const pythonCheck = checkPython();
  if (!pythonCheck.ok) {
    dialog.showErrorBox('Python Setup Required', pythonCheck.error!);
    app.quit();
    return;
  }

  resolvedPythonCmd = pythonCheck.pythonCmd;
  console.log(`[startup] Using ${resolvedPythonCmd} (Python ${pythonCheck.version}, source: ${pythonCheck.source})`);

  const isDev = !app.isPackaged;
  const dataDir = isDev
    ? path.join(__dirname, '..', '..', 'backend')
    : path.join(process.resourcesPath, 'backend');
  console.log(`[startup] Data directory: ${dataDir}`);

  // Load frontend first so boot sequence shows immediately
  await loadApp();
  console.log('[startup] Frontend loaded');

  // Start backend and wait for health check
  startBackend();

  try {
    await waitForBackend();
    console.log(`[startup] Backend ready (Python: ${pythonCheck.source}, v${pythonCheck.version})`);
    mainWindow?.webContents.send('backend-ready');
    // Check for updates after app is loaded (non-blocking)
    checkForUpdates();
  } catch {
    dialog.showErrorBox(
      'Backend Startup Failed',
      `The FastAPI backend failed to start within ${BACKEND_START_TIMEOUT_MS / 1000} seconds.\n\n` +
      `Error output:\n${backendStderr || 'No error output captured.'}`
    );
    app.quit();
  }
});

app.on('window-all-closed', async () => {
  saveWindowState();
  if (process.platform !== 'darwin') {
    await stopBackend();
    app.quit();
  }
});

app.on('before-quit', async () => {
  await stopBackend();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
