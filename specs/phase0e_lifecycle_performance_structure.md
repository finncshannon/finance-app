# Phase 0E — App Lifecycle, Performance & Project Structure
> Designer Agent | February 25, 2026
> Status: COMPLETE — APPROVED BY FINN
> Depends on: Phase 0A (Foundation), Phase 0B (Database Schema), Phase 0C (API Layer), Phase 0D (UI/UX Framework)

---

## Overview

This document defines three interconnected concerns:
1. **App Lifecycle** — what happens from first launch through daily use to shutdown
2. **Performance** — how fast everything should be and how heavy operations are handled
3. **Project Structure** — folder organization and dev workflow

**Key decisions:**
- Empty dashboard on first launch with inviting prompts (not a wizard)
- eDEX-UI inspired startup animation — the app "boots up" like an engine
- Clean break from existing tools — no data migration, standalone product
- No AI/LLM required — all intelligence is algorithmic
- Three-folder monorepo: `frontend/`, `backend/`, `electron/`
- Performance targets defined per operation type

---

## Part 1: App Lifecycle

### 1.1 Startup Animation — "Engine Boot"

Inspired by eDEX-UI and sci-fi system initialization sequences. The app doesn't
just open — it *activates*. This runs once on every launch, takes 1.5-2.5 seconds
total (real initialization happens behind the animation).

**Boot Sequence (what the user sees):**

```
Phase 1 — Black Screen (0ms - 200ms)
  App window opens. Pure black (#0D0D0D). Brief pause.

Phase 2 — System Text (200ms - 800ms)
  Monospace text streams in, top-left, terminal-style:

    VALUATION ENGINE v1.0
    ─────────────────────────────
    Initializing core systems...
    ├── Database connected          ✓
    ├── Market data service          ✓
    ├── Model engine loaded          ✓
    ├── Portfolio sync               ✓
    └── UI components ready          ✓

  Each line appears with a 60-80ms stagger.
  Checkmarks animate in as each real system check completes.
  Text color: --text-tertiary (#737373), checkmarks: --accent-primary (#3B82F6)

Phase 3 — Grid Assembly (800ms - 1500ms)
  The terminal text fades to 30% opacity and shifts up.
  Dashboard panels/cards fade in from 0% opacity with a subtle
  scale transform (0.97 → 1.0), staggered 80ms apart.
  Navigation bar slides down from top (transform: translateY(-100%) → 0).
  Each element has a faint blue glow on arrival that fades after 300ms.

Phase 4 — Live (1500ms+)
  All elements at full opacity. Data begins populating.
  Price numbers count up to their values (fast, 400ms) rather than
  appearing instantly — gives a "systems coming online" feel.
  App is fully interactive.
```

**Technical notes:**
- The animation is NOT blocking — real initialization runs concurrently
- If FastAPI server takes longer than the animation, Phase 2 checkmarks
  wait for real confirmation before showing ✓
- Animation is pure CSS/JS — no external library needed
- Subsequent launches after the first use the same animation (it's part of
  the app's identity, not a one-time thing)
- Animation cannot be skipped but is fast enough that it never feels like waiting

**Typography for boot sequence:**
- Font: JetBrains Mono, 12px
- Line height: 1.6
- Color: --text-tertiary for text, --accent-primary for checkmarks and highlights
- Background: --bg-primary (#0D0D0D)

### 1.2 First Launch — Empty Dashboard

No wizard. No onboarding flow. The dashboard loads with its normal layout,
but widgets show inviting empty states instead of data.

**Empty State Design (per widget):**

```
Watchlist Widget:
  ┌─────────────────────────────────┐
  │  WATCHLIST                      │
  │                                 │
  │       📡                        │
  │  No tickers yet                 │
  │  Search for a company to start  │
  │                                 │
  │  [ + Add Ticker ]               │
  └─────────────────────────────────┘

Portfolio Widget:
  ┌─────────────────────────────────┐
  │  PORTFOLIO                      │
  │                                 │
  │       📊                        │
  │  No positions tracked           │
  │  Add holdings to track your     │
  │  portfolio performance          │
  │                                 │
  │  [ + Add Position ]             │
  └─────────────────────────────────┘

Recent Models Widget:
  ┌─────────────────────────────────┐
  │  RECENT MODELS                  │
  │                                 │
  │       🔧                        │
  │  No models built yet            │
  │  Pick a company and build your  │
  │  first valuation model          │
  │                                 │
  │  [ Start a Model ]              │
  └─────────────────────────────────┘

Market Overview Widget:
  (This one populates immediately from Yahoo Finance
   — it doesn't depend on user data)
```

**Design rules for empty states:**
- Icon: simple, monochrome, centered — NOT emoji (the above are placeholders,
  actual icons will be minimal SVG line art in --text-tertiary color)
- Headline: 14px Inter Semi-Bold, --text-primary
- Subtext: 12px Inter Regular, --text-secondary
- CTA button: secondary style (border only, --accent-primary), 12px
- Overall feel: calm, inviting, not overwhelming
- The Market Overview widget loading with live data on first launch
  immediately makes the app feel alive and functional

### 1.3 Normal Startup Sequence (Technical)

What actually happens behind the boot animation:

```
1. User launches app (double-click / dock icon / taskbar)
2. Electron main process starts
3. Electron creates BrowserWindow (hidden initially)
4. Electron spawns Python FastAPI server:
     python -m uvicorn main:app --host 127.0.0.1 --port 8000
5. Electron polls GET /api/v1/system/health every 100ms
6. While polling: renderer shows boot animation Phase 1-2
7. FastAPI responds 200 → server ready
8. FastAPI runs database migrations if needed (first launch or update)
9. Electron signals renderer via IPC: "backend ready"
10. Renderer begins API calls:
     - GET /api/v1/dashboard/summary (portfolio, watchlist, recent models)
     - WebSocket connect: ws://127.0.0.1:8000/ws/prices
     - WebSocket connect: ws://127.0.0.1:8000/ws/status
11. Boot animation Phase 3-4 plays as data arrives
12. Price refresh timer starts (60s cycle during market hours)
13. App fully interactive
```

**Timing targets:**
- Electron window visible: < 500ms
- FastAPI server ready: < 1500ms
- Dashboard data loaded: < 2000ms
- Full boot animation complete: ~2000ms
- Total time to interactive: < 2500ms

### 1.4 Shutdown

```
1. User closes window (Cmd+Q / Alt+F4 / close button)
2. Electron main process intercepts close event
3. Save window state (position, size, active tab) to settings
4. Send shutdown signal to FastAPI server
5. FastAPI:
   a. Stop price refresh timer
   b. Close WebSocket connections
   c. Close database connections
   d. Shut down gracefully (2 second timeout, then force kill)
6. Electron app exits
```

No unsaved data risk — all user actions (model saves, assumption changes,
portfolio edits) write to the database immediately via API calls. There's
no "unsaved changes" state.

### 1.5 Automatic Backups

**Strategy:** SQLite file copy — simple, reliable, zero dependencies.

- **Frequency:** Daily, on first app launch of the day
- **What's backed up:** user_data.db only (market_cache.db is regeneratable)
- **Location:** `[app_data]/backups/` directory
- **Naming:** `user_data_2026-02-25.db`
- **Retention:** Last 30 daily backups (auto-delete older ones)
- **Size:** SQLite files are small — 30 backups is likely < 500MB total

**Restore process:**
- Settings → Data → Restore from Backup
- Shows list of available backups with dates and file sizes
- Select one → app copies it over current user_data.db → restarts

**Manual backup:**
- Settings → Data → Export Backup
- Saves a copy to user-chosen location (Save dialog)

### 1.6 Data Reset

- Settings → Data → Reset All Data
- Confirmation dialog: "This will delete all models, portfolio data, watchlists,
  and settings. Market data cache will be cleared. This cannot be undone."
- Requires typing "RESET" to confirm (prevents accidental clicks)
- Deletes user_data.db, deletes market_cache.db
- App restarts → first launch experience again

### 1.7 App Updates

**MVP approach:** Manual updates.
- App has a version number displayed in Settings
- Settings → About → Check for Updates
- Links to GitHub releases page (or wherever builds are hosted)
- User downloads new version and installs over existing
- Database migrations run automatically on next launch if schema changed

**Future enhancement (post-MVP):**
- Electron auto-updater (electron-updater) for seamless background updates
- Not worth the complexity for v1

### 1.8 Data Migration — Not Applicable

Clean break from existing tools. The Finance App is a standalone product.
Existing Screening Tool and MasterValuation.xlsm serve as reference and
inspiration for feature design, but no data is imported from them.

The codebase may reuse logic patterns from existing Python scripts
(SEC parsing, financial data extraction, screening algorithms), but these
are re-implemented in the new backend architecture, not imported wholesale.

---

## Part 2: Performance Requirements

### 2.1 Performance Tiers

All operations fall into one of three tiers based on expected duration:

| Tier | Duration | UI Behavior | Examples |
|------|----------|-------------|---------|
| Instant | < 200ms | No loading indicator | Tab switch, settings change, assumption edit |
| Quick | 200ms - 2s | Inline spinner or skeleton | Data table load, ticker search, chart render |
| Heavy | 2s - 30s | Full loading screen with progress | Model calculation, Monte Carlo, bulk data refresh |

### 2.2 Specific Performance Targets

**Startup:**
- App launch to boot animation visible: < 500ms
- Boot animation to interactive dashboard: < 2500ms

**Navigation:**
- Module tab switch (Dashboard → Model Builder): < 100ms
- Sub-tab switch within module: < 50ms
- Ticker header bar update after search: < 200ms

**Data Loading:**
- Company financial data (first load from Yahoo): < 3s
- Company financial data (cached): < 200ms
- Dashboard summary load: < 1s
- Scanner results (full universe, ~500 tickers): < 5s
- Portfolio summary calculation: < 500ms

**Model Operations:**
- DCF model full calculation: < 5s typical, < 10s worst case
- Monte Carlo simulation (10,000 iterations): < 15s
- Sensitivity table generation: < 2s
- Model save (version snapshot): < 500ms
- Auto-detection (all models scored): < 3s

**Export:**
- Excel export (single model): < 3s
- PDF export (single model): < 5s
- Portfolio export: < 2s

**Price Updates:**
- WebSocket price push to UI render: < 100ms
- Full watchlist refresh (50 tickers): background, < 30s total

### 2.3 Heavy Operation Handling

For operations in the Heavy tier, the full loading screen (defined in Phase 0C)
displays with progress stages. Key principles:

- **Never block the entire app** — heavy operations run in the backend.
  The loading screen is a frontend overlay on the relevant panel only.
  User can still switch to other modules during a model calculation.
- **Always show progress** — no indeterminate spinners for operations > 2s.
  Either a progress bar with stages or a live counter (Monte Carlo iterations).
- **Cancellable** — heavy operations show a "Cancel" button. Backend supports
  graceful cancellation via a flag check between calculation stages.
- **Results persist** — if a model calculation completes while user is on
  another tab, results are saved and available when they return.

### 2.4 Memory Management

**Targets:**
- App idle (dashboard, no models open): < 300MB
- Active use (model open, data loaded): < 500MB
- Heavy use (multiple models, scanner running): < 800MB
- Absolute ceiling: 1GB

**Strategies:**
- Table virtualization (react-window) for all tables > 50 rows
- Lazy-load module code — only load Model Builder JS when user navigates there
- Chart data downsampling for large datasets
- Release model data from memory when switching away from Model Builder
  (reload from DB cache when returning)
- Backend: FastAPI is lightweight; Python calculation engines release memory
  after returning results

### 2.5 Database Performance

- All reads: < 50ms for single-record queries
- All writes: < 100ms for single-record inserts/updates
- Complex queries (scanner filters across 500+ companies): < 2s
- Database vacuum/optimize: runs during daily backup, < 5s

---

## Part 3: Project Structure

### 3.1 Repository Layout

Single monorepo, three top-level application folders plus shared config:

```
finance-app/
├── electron/                  # Electron main process
│   ├── main.ts                # App entry point, window management
│   ├── preload.ts             # Context bridge for renderer
│   ├── ipc/                   # IPC handlers (frontend ↔ main process)
│   │   ├── server.ts          # FastAPI server lifecycle management
│   │   ├── files.ts           # File dialogs (save, export)
│   │   └── window.ts          # Window state persistence
│   ├── updater.ts             # Future: auto-update logic
│   └── tsconfig.json
│
├── frontend/                  # React application (Electron renderer)
│   ├── src/
│   │   ├── app/               # App shell, routing, providers
│   │   │   ├── App.tsx
│   │   │   ├── Router.tsx
│   │   │   └── Providers.tsx
│   │   │
│   │   ├── modules/           # One folder per top-level module
│   │   │   ├── dashboard/
│   │   │   │   ├── Dashboard.tsx
│   │   │   │   ├── widgets/
│   │   │   │   │   ├── WatchlistWidget.tsx
│   │   │   │   │   ├── PortfolioWidget.tsx
│   │   │   │   │   ├── RecentModelsWidget.tsx
│   │   │   │   │   └── MarketOverviewWidget.tsx
│   │   │   │   └── dashboard.css
│   │   │   │
│   │   │   ├── model-builder/
│   │   │   │   ├── ModelBuilder.tsx
│   │   │   │   ├── tabs/
│   │   │   │   │   ├── OverviewTab.tsx
│   │   │   │   │   ├── HistoricalDataTab.tsx
│   │   │   │   │   ├── AssumptionsTab.tsx
│   │   │   │   │   ├── DCFModelTab.tsx
│   │   │   │   │   ├── SensitivityTab.tsx
│   │   │   │   │   └── HistoryTab.tsx
│   │   │   │   ├── components/
│   │   │   │   │   ├── TickerSearch.tsx
│   │   │   │   │   ├── WaterfallChart.tsx
│   │   │   │   │   ├── TornadoChart.tsx
│   │   │   │   │   ├── MonteCarloChart.tsx
│   │   │   │   │   └── ProjectionTable.tsx
│   │   │   │   └── model-builder.css
│   │   │   │
│   │   │   ├── scanner/
│   │   │   ├── portfolio/
│   │   │   ├── research/
│   │   │   └── settings/
│   │   │
│   │   ├── components/        # Shared/reusable components
│   │   │   ├── navigation/
│   │   │   │   ├── ModuleTabBar.tsx
│   │   │   │   ├── TabBar.tsx
│   │   │   │   ├── SubTabBar.tsx
│   │   │   │   └── TickerHeaderBar.tsx
│   │   │   ├── data/
│   │   │   │   ├── DataTable.tsx
│   │   │   │   ├── MetricCard.tsx
│   │   │   │   ├── PriceDisplay.tsx
│   │   │   │   └── EmptyState.tsx
│   │   │   ├── charts/
│   │   │   │   ├── LineChart.tsx
│   │   │   │   ├── BarChart.tsx
│   │   │   │   └── BaseChart.tsx
│   │   │   ├── inputs/
│   │   │   │   ├── TextInput.tsx
│   │   │   │   ├── NumberInput.tsx
│   │   │   │   ├── SelectDropdown.tsx
│   │   │   │   └── Slider.tsx
│   │   │   ├── feedback/
│   │   │   │   ├── LoadingScreen.tsx
│   │   │   │   ├── BootAnimation.tsx
│   │   │   │   ├── SkeletonLoader.tsx
│   │   │   │   └── Toast.tsx
│   │   │   └── layout/
│   │   │       ├── PageContainer.tsx
│   │   │       ├── SplitPanel.tsx
│   │   │       └── Modal.tsx
│   │   │
│   │   ├── services/          # API communication layer
│   │   │   ├── api.ts         # Base fetch wrapper, error handling
│   │   │   ├── websocket.ts   # WebSocket connection manager
│   │   │   ├── companies.ts   # /api/v1/companies/* calls
│   │   │   ├── models.ts      # /api/v1/model-builder/* calls
│   │   │   ├── scanner.ts     # /api/v1/scanner/* calls
│   │   │   ├── portfolio.ts   # /api/v1/portfolio/* calls
│   │   │   ├── research.ts    # /api/v1/research/* calls
│   │   │   └── dashboard.ts   # /api/v1/dashboard/* calls
│   │   │
│   │   ├── hooks/             # Custom React hooks
│   │   │   ├── useApi.ts      # Generic API call hook with loading/error
│   │   │   ├── usePrices.ts   # WebSocket price subscription
│   │   │   ├── useSettings.ts
│   │   │   └── useDebounce.ts
│   │   │
│   │   ├── stores/            # State management (Zustand or similar)
│   │   │   ├── appStore.ts    # Global app state (active module, ticker)
│   │   │   ├── priceStore.ts  # Live price cache
│   │   │   └── settingsStore.ts
│   │   │
│   │   ├── styles/            # Global styles and design tokens
│   │   │   ├── tokens.css     # All CSS custom properties from Phase 0D
│   │   │   ├── reset.css      # CSS reset / normalize
│   │   │   ├── typography.css # Font faces, type scale
│   │   │   ├── tables.css     # Shared table styles
│   │   │   └── animations.css # Boot animation, transitions
│   │   │
│   │   ├── utils/             # Pure utility functions
│   │   │   ├── formatNumber.ts    # Currency, percentage, ratio formatting
│   │   │   ├── formatDate.ts
│   │   │   └── constants.ts       # App-wide constants
│   │   │
│   │   ├── types/             # TypeScript type definitions
│   │   │   ├── api.ts         # API request/response types
│   │   │   ├── models.ts      # Domain types (Company, Model, etc.)
│   │   │   └── components.ts  # Component prop types
│   │   │
│   │   └── index.tsx          # React entry point
│   │
│   ├── public/
│   │   └── fonts/             # Inter + JetBrains Mono bundled
│   ├── package.json
│   └── tsconfig.json
│
├── backend/                   # Python FastAPI server
│   ├── main.py                # FastAPI app creation, startup/shutdown
│   ├── config.py              # App configuration, paths, constants
│   │
│   ├── routers/               # API endpoint definitions (one per module)
│   │   ├── companies.py       # /api/v1/companies/*
│   │   ├── model_builder.py   # /api/v1/model-builder/*
│   │   ├── scanner.py         # /api/v1/scanner/*
│   │   ├── portfolio.py       # /api/v1/portfolio/*
│   │   ├── research.py        # /api/v1/research/*
│   │   ├── dashboard.py       # /api/v1/dashboard/*
│   │   ├── settings.py        # /api/v1/settings/*
│   │   ├── export.py          # /api/v1/export/*
│   │   └── system.py          # /api/v1/system/*
│   │
│   ├── services/              # Business logic layer
│   │   ├── company_service.py
│   │   ├── model_service.py
│   │   ├── scanner_service.py
│   │   ├── portfolio_service.py
│   │   ├── research_service.py
│   │   ├── export_service.py
│   │   └── backup_service.py
│   │
│   ├── engines/               # Calculation engines (the math)
│   │   ├── dcf_engine.py
│   │   ├── ddm_engine.py
│   │   ├── comps_engine.py
│   │   ├── revenue_engine.py
│   │   ├── assumption_engine.py   # The "brain" — generates assumptions
│   │   ├── detector_engine.py     # Model auto-detection & scoring
│   │   ├── sensitivity_engine.py  # Monte Carlo, tornado, tables
│   │   └── base_engine.py         # Shared engine interface/contract
│   │
│   ├── data/                  # Data access layer
│   │   ├── database.py        # SQLite connection manager, migrations
│   │   ├── repositories/      # One per entity group
│   │   │   ├── company_repo.py
│   │   │   ├── financial_repo.py
│   │   │   ├── model_repo.py
│   │   │   ├── portfolio_repo.py
│   │   │   ├── research_repo.py
│   │   │   ├── scanner_repo.py
│   │   │   └── settings_repo.py
│   │   └── migrations/        # SQL migration scripts
│   │       ├── 001_initial_schema.sql
│   │       └── 002_add_indexes.sql
│   │
│   ├── providers/             # External data sources
│   │   ├── yahoo_finance.py   # yfinance wrapper
│   │   ├── sec_edgar.py       # SEC filing fetcher
│   │   ├── xbrl_parser.py     # XBRL financial statement parser
│   │   ├── treasury.py        # Risk-free rate from Treasury API
│   │   └── base_provider.py   # Provider interface (for future swap)
│   │
│   ├── models/                # Pydantic data models (API contracts)
│   │   ├── company.py
│   │   ├── financial.py
│   │   ├── valuation.py
│   │   ├── portfolio.py
│   │   ├── scanner.py
│   │   ├── research.py
│   │   └── common.py          # Shared response envelope, pagination
│   │
│   ├── websocket/             # WebSocket management
│   │   ├── manager.py         # Connection lifecycle, subscriptions
│   │   └── price_feed.py      # 60-second price refresh loop
│   │
│   ├── utils/                 # Shared utilities
│   │   ├── formatting.py      # Number formatting (mirrors frontend)
│   │   └── logging.py         # Structured logging config
│   │
│   ├── requirements.txt       # Python dependencies
│   └── pyproject.toml
│
├── specs/                     # Design specifications (what we're writing now)
│   ├── phase0_foundation.md
│   ├── phase0b_database_schema.md
│   ├── phase0c_api_layer.md
│   ├── phase0d_ui_ux_framework.md
│   ├── phase0e_lifecycle_performance_structure.md   # ← This document
│   └── brainstorm_plan.md
│
├── .gitignore
├── README.md
├── package.json               # Root package.json (workspace config)
└── LICENSE
```

### 3.2 Key Architectural Boundaries

**The Three-Layer Rule:** Every module follows the same pattern:

```
Router (HTTP) → Service (logic) → Repository (database)
                    ↓
              Engine (math)        ← only for calculation-heavy modules
                    ↓
              Provider (external)  ← only when external data needed
```

- **Routers** only handle HTTP concerns (parsing requests, formatting responses)
- **Services** contain all business logic (validation, orchestration, caching)
- **Repositories** only talk to the database (SQL queries, no business logic)
- **Engines** are pure calculation functions (take data in, return results)
- **Providers** wrap external APIs (Yahoo Finance, SEC EDGAR)

No layer skips another. A router never calls a repository directly.
An engine never makes an API call. This keeps everything testable and swappable.

### 3.3 Frontend Architecture Rules

- **One folder per module** in `modules/` — each is self-contained
- **Shared components** go in `components/` — only if used by 2+ modules
- **Services mirror API structure** — one service file per backend router
- **Styles co-locate with components** — each module has its own .css file
- **Global styles** only in `styles/` — tokens, reset, typography
- **Types mirror Pydantic models** — frontend TypeScript types match backend
  Python models exactly (same field names, same structures)
- **No prop drilling deeper than 2 levels** — use stores or context

### 3.4 Development Workflow

**Dev Mode (daily development):**

```bash
# Terminal 1: Start backend
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2: Start frontend (Vite dev server with HMR)
cd frontend
npm run dev

# Terminal 3: Start Electron (points to Vite dev server)
cd electron
npm run dev
```

Hot reload on both frontend and backend. Changes appear instantly.

**Build Mode (create distributable app):**

```bash
# From root
npm run build        # Builds frontend → static files
                     # Bundles backend with PyInstaller → single executable
                     # Packages everything into Electron app
npm run package      # Creates .dmg (Mac) / .exe (Windows) installer
```

**Testing:**

```bash
# Backend tests
cd backend
pytest                        # All tests
pytest tests/engines/         # Engine tests only
pytest tests/routers/         # API endpoint tests only

# Frontend tests
cd frontend
npm test                      # Component + integration tests
npm run test:e2e              # End-to-end with Playwright
```

**Testing strategy:**
- **Engines get the most tests** — these are pure math, easy to test,
  critical to get right. Every DCF calculation path has a test case.
- **Routers get integration tests** — real HTTP calls against a test database
- **Frontend components get snapshot + interaction tests** — verify rendering
  and user interactions
- **E2E tests cover critical paths** — "search ticker → build model → see result"

### 3.5 Git Conventions

- **Branch naming:** `feature/module-name`, `fix/description`, `spec/phase-name`
- **Commits:** Conventional Commits format
  - `feat(model-builder): add DCF calculation engine`
  - `fix(scanner): correct filter logic for negative EPS`
  - `spec(0e): add lifecycle and performance spec`
- **Main branch:** `main` — always deployable
- **No long-lived branches** — merge frequently, small PRs

### 3.6 Dependency Management

**Frontend (package.json):**
- React, React-DOM, TypeScript
- Recharts or D3 (charting)
- Zustand (state management)
- react-window (table virtualization)
- date-fns (date formatting)
- No CSS framework — custom CSS with design tokens

**Backend (requirements.txt):**
- FastAPI, uvicorn
- aiosqlite (async SQLite)
- pydantic (data validation)
- yfinance (market data)
- openpyxl (Excel export)
- weasyprint or reportlab (PDF export)
- numpy (Monte Carlo, statistical calculations)
- python-multipart (file handling)

**Electron:**
- electron, electron-builder (packaging)
- electron-updater (future: auto-updates)

---

## Appendix: Checklist for New Module Development

When adding a new module to the app, create these files:

**Backend:**
- [ ] `routers/new_module.py` — endpoint definitions
- [ ] `services/new_module_service.py` — business logic
- [ ] `data/repositories/new_module_repo.py` — database queries
- [ ] `models/new_module.py` — Pydantic request/response models
- [ ] `engines/new_engine.py` — if calculation-heavy
- [ ] Migration script if new tables needed

**Frontend:**
- [ ] `modules/new-module/NewModule.tsx` — main component
- [ ] `modules/new-module/tabs/` — sub-tab components
- [ ] `modules/new-module/components/` — module-specific components
- [ ] `modules/new-module/new-module.css` — module styles
- [ ] `services/new-module.ts` — API service functions
- [ ] `types/` updates — new TypeScript types
- [ ] Add route to Router.tsx
- [ ] Add tab to ModuleTabBar

---

*End of Phase 0E specification.*
