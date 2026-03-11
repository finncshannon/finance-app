#!/bin/bash
set -e

# ─── Colors ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

success() { echo -e "${GREEN}✔ $1${NC}"; }
warn()    { echo -e "${YELLOW}⚠ $1${NC}"; }
error()   { echo -e "${RED}✖ $1${NC}"; }
info()    { echo -e "${BOLD}→ $1${NC}"; }

# ─── Navigate to project root (directory containing this script's parent) ─────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo -e "${BOLD}Finance App — macOS Developer Setup${NC}"
echo "───────────────────────────────────────"
echo ""

# ─── 1. Check Homebrew ───────────────────────────────────────────────────────
info "Checking for Homebrew..."
if ! command -v brew &>/dev/null; then
    error "Homebrew is not installed."
    echo ""
    echo "  Install it with:"
    echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    echo ""
    echo "  Then re-run this script."
    exit 1
fi
success "Homebrew found: $(brew --version | head -n1)"

# ─── 2. Check / Install Node.js 18+ ─────────────────────────────────────────
info "Checking for Node.js 18+..."
if command -v node &>/dev/null; then
    NODE_VERSION=$(node -v | sed 's/v//')
    NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)
    if [ "$NODE_MAJOR" -ge 18 ]; then
        success "Node.js found: v$NODE_VERSION"
    else
        warn "Node.js $NODE_VERSION is too old (need 18+). Installing via Homebrew..."
        brew install node
        success "Node.js installed: $(node -v)"
    fi
else
    warn "Node.js not found. Installing via Homebrew..."
    brew install node
    success "Node.js installed: $(node -v)"
fi

# ─── 3. Check / Install Python 3.11+ ────────────────────────────────────────
info "Checking for Python 3.11+..."
PYTHON_CMD=""

# Try python3 first, then python
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PY_VERSION=$("$cmd" --version 2>&1 | sed 's/Python //')
        PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
        PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
        if [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -ge 11 ]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -n "$PYTHON_CMD" ]; then
    success "Python found: $($PYTHON_CMD --version)"
else
    warn "Python 3.11+ not found. Installing via Homebrew..."
    brew install python@3.11
    PYTHON_CMD="python3"
    success "Python installed: $($PYTHON_CMD --version)"
fi

# ─── 4. Install pip dependencies ─────────────────────────────────────────────
info "Installing Python dependencies..."
if [ ! -f "backend/requirements.txt" ]; then
    error "backend/requirements.txt not found. Are you in the project root?"
    exit 1
fi
$PYTHON_CMD -m pip install -r backend/requirements.txt
success "Python dependencies installed"

# ─── 5. Install npm dependencies ─────────────────────────────────────────────
info "Installing npm dependencies..."
npm install
success "npm dependencies installed"

# ─── 6. Verify critical Python imports ───────────────────────────────────────
info "Verifying critical Python imports..."
if $PYTHON_CMD -c "import fastapi, uvicorn, aiosqlite" 2>/dev/null; then
    success "All critical imports verified (fastapi, uvicorn, aiosqlite)"
else
    error "Failed to import one or more critical packages."
    echo "  Try running: $PYTHON_CMD -m pip install fastapi uvicorn aiosqlite"
    exit 1
fi

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "───────────────────────────────────────"
echo -e "${GREEN}${BOLD}Setup complete!${NC} To start the app:"
echo ""
echo "  Terminal 1: npm run dev:frontend"
echo "  Terminal 2: npm run dev:electron"
echo ""
