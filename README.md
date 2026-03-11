# Finance App

Professional-grade desktop finance application for valuation modeling, stock screening, portfolio tracking, and company research.

## Architecture

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Desktop Shell | Electron 33 | Window management, backend lifecycle, IPC |
| Frontend | React 19 + TypeScript, Vite | SPA with CSS Modules, Recharts |
| Backend | Python 3.11+ / FastAPI | REST API, valuation engines, data providers |
| Database | SQLite (aiosqlite) | `user_data.db` (portfolios, models) + `market_cache.db` (prices, financials) |

## Prerequisites

- **Node.js** >= 18
- **Python** >= 3.11 (added to PATH)
- **pip** packages: `pip install -r backend/requirements.txt`

## Getting Started

### macOS
```bash
chmod +x scripts/setup-mac.sh
./scripts/setup-mac.sh
```

### Windows
```cmd
scripts\setup-win.bat
```

## Quick Start

```bash
# 1. Install all JS dependencies (workspaces: frontend + electron)
npm install

# 2. Install Python dependencies
cd backend && pip install -r requirements.txt && cd ..

# 3. Start backend (Terminal 1)
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# 4. Start frontend dev server (Terminal 2)
cd frontend
npm run dev          # Vite on http://localhost:5173

# 5. Start Electron (Terminal 3)
cd electron
npm run dev          # Compiles TS then launches Electron
```

## Build & Package

```bash
# Production build (frontend + electron TypeScript)
npm run build

# Package Windows installer (.exe via NSIS)
cd electron
npm run package:win
# Output: electron/dist/Finance App Setup 1.0.0.exe (~163 MB)

# Package macOS installer (.dmg)
cd electron
npm run package:mac
```

## Project Structure

```
finance-app/
├── frontend/                    # React 19 + TypeScript SPA
│   ├── src/
│   │   ├── components/ui/       # Reusable UI components (DataTable, charts, modals)
│   │   ├── pages/
│   │   │   ├── Dashboard/       # Home dashboard with watchlist + market overview
│   │   │   ├── Scanner/         # Multi-factor stock screener
│   │   │   ├── Research/        # Company deep-dive (financials, peers, filings)
│   │   │   ├── ModelBuilder/    # Valuation models (DCF, DDM, Comps, RevBased)
│   │   │   ├── Portfolio/       # Portfolio tracking, holdings, performance
│   │   │   └── Settings/        # App configuration
│   │   ├── hooks/               # Custom React hooks (API, state, layout)
│   │   ├── services/            # API client (apiClient.ts, config.ts)
│   │   └── styles/              # Design tokens (variables.css) + global styles
│   └── vite.config.ts
│
├── backend/                     # Python 3.11+ FastAPI server
│   ├── main.py                  # App entry, CORS, lifespan
│   ├── routers/                 # REST endpoints
│   │   ├── dashboard_router.py  #   /api/v1/dashboard/*
│   │   ├── scanner_router.py    #   /api/v1/scanner/*
│   │   ├── research_router.py   #   /api/v1/research/*
│   │   ├── models_router.py     #   /api/v1/models/*
│   │   ├── portfolio_router.py  #   /api/v1/portfolio/*
│   │   ├── companies_router.py  #   /api/v1/companies/*
│   │   ├── universe_router.py   #   /api/v1/universe/*
│   │   ├── settings_router.py   #   /api/v1/settings/*
│   │   ├── export_router.py     #   /api/v1/export/*
│   │   └── system_router.py     #   /api/v1/system/health
│   ├── engines/                 # Valuation calculation engines
│   │   ├── dcf_engine.py        #   Discounted Cash Flow
│   │   ├── ddm_engine.py        #   Dividend Discount Model
│   │   ├── comps_engine.py      #   Comparable Companies
│   │   └── revbased_engine.py   #   Revenue-Based Valuation
│   ├── providers/               # External data sources
│   │   ├── yahoo_finance.py     #   Yahoo Finance API
│   │   └── sec_edgar.py         #   SEC EDGAR filings
│   ├── services/                # Business logic layer
│   ├── repositories/            # Database access (aiosqlite)
│   ├── models/                  # Pydantic schemas
│   └── db/                      # SQLite init scripts + migrations
│
├── electron/                    # Electron main process
│   ├── main.ts                  # Window creation, backend lifecycle, IPC
│   ├── preload.ts               # Context bridge (backend URL, layout events)
│   ├── electron-builder.yml     # Packaging config (NSIS / DMG)
│   └── resources/               # App icons (icon.ico, icon.png)
│
├── package.json                 # Root workspace config
├── docs/                        # Design docs and plans
└── specs/                       # Feature specifications
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_HOST` | `127.0.0.1` | Backend bind address (set in `electron/main.ts`) |
| `BACKEND_PORT` | `8000` | Backend port |
| `VITE_API_BASE_URL` | `http://localhost:8000` | Frontend API target (dev mode) |

## Modules

### Frontend Pages
| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/` | Watchlist, market overview, quick actions |
| Scanner | `/scanner` | Multi-factor stock screener with filtering |
| Research | `/research/:ticker` | Company financials, peers, SEC filings, history |
| Model Builder | `/models/:ticker` | DCF, DDM, Comps, RevBased models + sensitivity |
| Portfolio | `/portfolio` | Holdings, transactions, performance attribution |
| Settings | `/settings` | API keys, preferences, data management |

### Backend Engines
| Engine | Description |
|--------|-------------|
| DCF | Multi-stage discounted cash flow with terminal value |
| DDM | Dividend discount model (Gordon Growth + H-Model) |
| Comps | Comparable companies analysis (EV/EBITDA, P/E, etc.) |
| RevBased | Revenue multiple and PS-ratio valuation |

### Data Providers
| Provider | Source | Data |
|----------|--------|------|
| Yahoo Finance | yfinance | Prices, financials, company info |
| SEC EDGAR | SEC API | 10-K/10-Q filings, financial statements |

## Troubleshooting

### Backend won't start
```
Python 3.11+ not found on your system.
```
- Ensure Python 3.11+ is installed and on PATH
- On Windows, try `py -3 --version` to verify
- Install missing packages: `pip install -r backend/requirements.txt`

### Port 8000 already in use
```bash
# Find and kill the process using port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# macOS/Linux:
lsof -i :8000
kill -9 <pid>
```

### Electron build fails with EBUSY
- Close any running Electron instances
- Disable antivirus real-time scanning on `node_modules/electron/`
- The `npmRebuild: false` flag in `electron-builder.yml` mitigates most lock issues

### Electron build fails with symlink error
```
Cannot create symbolic link : A required privilege is not held by the client
```
- The `signAndEditExecutable: false` flag in `electron-builder.yml` skips winCodeSign extraction
- Alternatively, enable Windows Developer Mode (Settings > Developer Settings)

### Frontend dev server not connecting to backend
- Verify backend is running on port 8000: `curl http://127.0.0.1:8000/api/v1/system/health`
- Check `frontend/src/services/config.ts` for the correct API base URL
