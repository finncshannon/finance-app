/**
 * bundle-python.js
 *
 * Downloads the Python 3.11 embeddable package for Windows (amd64),
 * installs pip, installs all backend dependencies, and places the
 * result in electron/resources/python/ for bundling with electron-builder.
 *
 * Usage: node scripts/bundle-python.js
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const { execSync } = require('child_process');
const { createWriteStream, mkdirSync, existsSync, rmSync } = fs;

// --- Configuration ---
const PYTHON_VERSION = '3.11.9';
const PYTHON_ZIP = `python-${PYTHON_VERSION}-embed-amd64.zip`;
const PYTHON_URL = `https://www.python.org/ftp/python/${PYTHON_VERSION}/${PYTHON_ZIP}`;
const GET_PIP_URL = 'https://bootstrap.pypa.io/get-pip.py';

const ROOT_DIR = path.resolve(__dirname, '..');
const ELECTRON_DIR = path.join(ROOT_DIR, 'electron');
const OUTPUT_DIR = path.join(ELECTRON_DIR, 'resources', 'python');
const BACKEND_DIR = path.join(ROOT_DIR, 'backend');
const REQUIREMENTS = path.join(BACKEND_DIR, 'requirements.txt');
const TEMP_DIR = path.join(ROOT_DIR, '.tmp-python-bundle');

// --- Helpers ---

function log(msg) {
  console.log(`[bundle-python] ${msg}`);
}

function download(url, dest) {
  return new Promise((resolve, reject) => {
    log(`Downloading ${url}`);
    const file = createWriteStream(dest);
    https.get(url, (response) => {
      // Follow redirects
      if (response.statusCode >= 300 && response.statusCode < 400 && response.headers.location) {
        file.close();
        fs.unlinkSync(dest);
        return download(response.headers.location, dest).then(resolve).catch(reject);
      }
      if (response.statusCode !== 200) {
        file.close();
        fs.unlinkSync(dest);
        return reject(new Error(`Download failed: HTTP ${response.statusCode}`));
      }
      const total = parseInt(response.headers['content-length'] || '0', 10);
      let downloaded = 0;
      response.on('data', (chunk) => {
        downloaded += chunk.length;
        if (total > 0) {
          const pct = ((downloaded / total) * 100).toFixed(0);
          process.stdout.write(`\r[bundle-python]   ${pct}% (${(downloaded / 1024 / 1024).toFixed(1)}MB)`);
        }
      });
      response.pipe(file);
      file.on('finish', () => {
        file.close();
        console.log(''); // newline after progress
        resolve();
      });
    }).on('error', (err) => {
      file.close();
      fs.unlinkSync(dest);
      reject(err);
    });
  });
}

function exec(cmd, opts = {}) {
  log(`Running: ${cmd}`);
  execSync(cmd, {
    stdio: 'inherit',
    windowsHide: true,
    ...opts,
  });
}

// --- Main ---

async function main() {
  const startTime = Date.now();
  log('=== Finance App — Python Bundler ===');
  log(`Python version: ${PYTHON_VERSION}`);
  log(`Output: ${OUTPUT_DIR}`);

  // Clean previous output
  if (existsSync(OUTPUT_DIR)) {
    log('Cleaning previous bundle...');
    rmSync(OUTPUT_DIR, { recursive: true, force: true });
  }
  if (existsSync(TEMP_DIR)) {
    rmSync(TEMP_DIR, { recursive: true, force: true });
  }
  mkdirSync(TEMP_DIR, { recursive: true });
  mkdirSync(OUTPUT_DIR, { recursive: true });

  // Step 1: Download Python embeddable
  const zipPath = path.join(TEMP_DIR, PYTHON_ZIP);
  if (!existsSync(zipPath)) {
    await download(PYTHON_URL, zipPath);
  }
  log('Extracting Python embeddable...');
  // Use PowerShell to extract (available on all Windows 10+)
  exec(
    `powershell -Command "Expand-Archive -Path '${zipPath}' -DestinationPath '${OUTPUT_DIR}' -Force"`,
  );

  // Step 2: Uncomment "import site" in python311._pth
  const pthFile = path.join(OUTPUT_DIR, `python311._pth`);
  if (existsSync(pthFile)) {
    log('Enabling site-packages in _pth file...');
    let pthContent = fs.readFileSync(pthFile, 'utf-8');
    // Uncomment "import site" if commented
    pthContent = pthContent.replace(/^#\s*import site/m, 'import site');
    // Also add Lib/site-packages path if not present
    if (!pthContent.includes('Lib/site-packages') && !pthContent.includes('Lib\\site-packages')) {
      pthContent += '\nLib/site-packages\n';
    }
    fs.writeFileSync(pthFile, pthContent);
    log('_pth file updated');
  } else {
    log('WARNING: _pth file not found — site-packages may not work');
  }

  // Step 3: Install pip
  const getPipPath = path.join(TEMP_DIR, 'get-pip.py');
  await download(GET_PIP_URL, getPipPath);

  const pythonExe = path.join(OUTPUT_DIR, 'python.exe');
  if (!existsSync(pythonExe)) {
    throw new Error(`python.exe not found at ${pythonExe}`);
  }

  log('Installing pip...');
  exec(`"${pythonExe}" "${getPipPath}" --no-warn-script-location`);

  // Step 4: Install backend dependencies
  const sitePackages = path.join(OUTPUT_DIR, 'Lib', 'site-packages');
  mkdirSync(sitePackages, { recursive: true });

  log('Installing backend dependencies...');
  exec(
    `"${pythonExe}" -m pip install -r "${REQUIREMENTS}" --target "${sitePackages}" --no-warn-script-location --disable-pip-version-check`,
  );

  // Step 5: Verify critical packages
  log('Verifying critical packages...');
  const criticalPackages = ['fastapi', 'uvicorn', 'yfinance', 'pandas', 'aiosqlite', 'pydantic', 'numpy'];
  for (const pkg of criticalPackages) {
    try {
      execSync(`"${pythonExe}" -c "import ${pkg}"`, { windowsHide: true, stdio: 'pipe' });
      log(`  ✓ ${pkg}`);
    } catch {
      log(`  ✗ ${pkg} — FAILED TO IMPORT`);
      throw new Error(`Critical package ${pkg} failed to import`);
    }
  }

  // Step 6: Clean up temp directory
  log('Cleaning up...');
  rmSync(TEMP_DIR, { recursive: true, force: true });

  // Report size
  const totalSize = getDirSize(OUTPUT_DIR);
  const sizeMB = (totalSize / 1024 / 1024).toFixed(1);
  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

  log('=== Bundle complete ===');
  log(`  Size: ${sizeMB}MB`);
  log(`  Time: ${elapsed}s`);
  log(`  Path: ${OUTPUT_DIR}`);
}

function getDirSize(dir) {
  let total = 0;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      total += getDirSize(full);
    } else {
      total += fs.statSync(full).size;
    }
  }
  return total;
}

main().catch((err) => {
  console.error(`[bundle-python] ERROR: ${err.message}`);
  process.exit(1);
});
