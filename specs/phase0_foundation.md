# DESIGN BRIEF — Phase 0: Foundation & Architecture
> Produced by Designer Agent | February 22, 2026
> Revised: February 26, 2026 — Updated to reflect all completed design sessions
> Status: ✅ COMPLETE — APPROVED BY FINN

---

## Product Vision

A personal-use, professional-grade desktop finance application that consolidates
valuation modeling, stock screening, portfolio tracking, and company research
into a single unified tool.

Think of it as what a Wall Street trader would have running in their vacation
house — not the full Bloomberg Terminal with six monitors, but a single clean
app that covers the fundamentals well enough to check a position, run a quick
model, screen for ideas, or pull up filings if something breaks on a Sunday
night. It's not meant to replace a trading desk, but it's absolutely good
enough for an emergency business call. Real analytical depth, zero clutter.

Designed to look and feel like **Apple Stocks meets Bloomberg Terminal** —
Bloomberg's functional density and analytical power, Apple's visual restraint
and polish. Data-rich, dark-themed, smooth, and elegant.

The app replaces a fragmented workflow across Excel models, Bloomberg EQS,
Fidelity dashboards, and a custom Python screening tool with one cohesive
desktop application.

## Target User
- Finn — solo investor/analyst, personal use only
- Low code skills but comfortable with code-assisted development
- Current tools: Excel (.xlsm) valuation workbook with VBA/Python integration,
  custom Python screening tool (tkinter), Bloomberg EQS, Fidelity brokerage dashboard
- Goal: professional-grade tool built the way a real dev team would build it

---

## Tech Stack (Locked)

### Frontend
- **Framework:** Electron (desktop shell)
- **UI Library:** React + TypeScript
- **Styling:** Custom CSS recommended (Phase 0D) — TBD by Architect
- **Charting:** TBD by Architect (candidates: Recharts, TradingView Lightweight Charts, D3)
- **State Management:** TBD by Architect (candidates: Zustand, Redux Toolkit)

### Backend
- **Language:** Python 3.11+
- **API Framework:** FastAPI (local HTTP server, localhost:8000)
- **Communication:** REST + WebSocket hybrid (Phase 0C)
  - REST for 95% of operations (87 endpoints across 9 modules)
  - WebSocket for live price streaming (60s push during market hours)
- **Existing Code:** Screening Tool core modules, valuation scripts, data extractors
  migrate into backend service layer

### Database
- **Engine:** SQLite
- **Architecture:** Two database files (Phase 0B):
  - `user_data.db` — user work product (models, portfolio, watchlists, settings)
  - `market_cache.db` — regenerable data (financials, prices, filings)
- **Tables:** 23 tables total (Phase 0B + Integration Review amendments)
- **ORM:** SQLAlchemy or raw SQL — TBD by Architect

### Market Data
- **Primary Source:** Yahoo Finance (yfinance library) — free, sufficient for personal use
- **Design Principle:** Provider-agnostic data layer so sources can be swapped later
  (Polygon.io, Finnhub, Alpha Vantage) without touching module code
- **Refresh Strategy (Phase 0E):**
  - During market hours (9:30 AM – 4:00 PM ET): auto-refresh every 60 seconds
  - Outside market hours: manual refresh only
  - Refresh tiers: Tier 1 (portfolio/watchlist, 60s), Tier 2 (S&P 500, weekly),
    Tier 3 (full R3000, monthly)
- **SEC Data:** SEC EDGAR client for filing retrieval and parsing
- **XBRL Financials:** XBRL parser for structured financial data extraction

---

## App Shell & Navigation (Locked)

### Window Behavior
- Single-window application (no pop-out panels)
- Flexible resize — works fullscreen, windowed, or minimized
- Remembers last window position, size, and maximized state on relaunch
- Responsive layout: Compact (<1200px), Standard (1200-1600px), Wide (>1600px)

### Navigation Model (Phase 0D — Three-Tier Horizontal)
- **Tier 1 — Module Tabs** (always visible, top of window):
  1. **Dashboard** — Home screen, market overview, watchlists, recent work
  2. **Model Builder** — Valuation modeling (DCF, DDM, Comps, Revenue-Based)
  3. **Scanner** — Stock screening with 100+ filters and filing text search
  4. **Portfolio** — Holdings, performance analytics, income tracking
  5. **Research** — Company fundamentals, filings, financial statements
  6. **Settings** — Configuration hub for all app options
- **Tier 2 — Tabs** (contextual per module):
  - Model Builder: Overview | Historical Data | Assumptions | [Model] | Sensitivity | History
  - Scanner: Screens | Filters | Results | Universe
  - Portfolio: Holdings | Performance | Allocation | Income | Transactions | Alerts
  - Research: Profile | Financials | Ratios | Filings | Segments | Peers
  - Settings: General | Data Sources | Model Defaults | Portfolio | Scanner | About
- **Tier 3 — Sub-Tabs** (used by Sensitivity: Sliders | Tornado | Monte Carlo | Tables)
- Tab bar is always visible, active tab highlighted with blue underline
- Each tab maintains its own state (switching tabs doesn't reset your work)

### Boot Sequence (Phase 0E)
- eDEX-UI inspired "engine boot" animation (~2 seconds)
- Four phases: System Init → Data Load → Market Connect → Ready
- Target: < 2.5 seconds from launch to interactive dashboard

### Home Screen (Dashboard Tab — Phase 5)
- Widget-based layout (fixed for MVP, architecture supports customization)
- Market Overview: major indices, 10Y Treasury, VIX, market status
- Portfolio Summary: total value, day change, total gain/loss
- Watchlists: multiple named watchlists with live prices
- Recent Models: last 5 valuations with upside/downside
- Upcoming Events: earnings and ex-dividend dates

---

## Visual Design Direction (Locked — Phase 0D)

### Aesthetic
- **Primary Reference:** Apple Stocks app — clean cards, smooth transitions,
  elegant typography, high-contrast data on dark background
- **Secondary Reference:** Bloomberg Terminal — data density, professional feel,
  information hierarchy
- **Philosophy:** Data-rich but never cluttered. Every pixel earns its place.

### Theme
- Dark mode only — no light mode
- Dark background (#0D0D0D to #1A1A1A range)
- Monochrome + single blue accent (#3B82F6) for all interactive elements
- Green (#22C55E) and Red (#EF4444) ONLY for financial gains/losses
- Warning amber (#F59E0B) ONLY for data staleness indicators
- No gradients, no shadows — flat colors, border-based depth
- Smooth transitions: 150ms micro, 200ms panel, 300ms page

### Typography
- **Inter** — primary UI font for all text (labels, descriptions, headings)
- **JetBrains Mono** — all financial numbers, prices, percentages, table data
- Clear hierarchy: Module Tab (13px bold uppercase) → Section Header (14px semi-bold)
  → Body (13px regular) → Caption (11px regular)

### Core Components (35+ defined in Phase 0D)
- Bloomberg-style data tables: zebra-striped, years across top, metrics down rows
- Cards with 6px border-radius, --bg-secondary background
- Primary/Secondary/Danger button variants
- Ticker Header Bar with cross-module navigation ([Model] [Research] [+ Watchlist])

---

## Module Summary

### Model Builder (Phases 1A-1G)
- **4 valuation models:** DCF, DDM, Comps, Revenue-Based
- **2 future models:** LBO, NAV (plugin architecture ready)
- **Assumption Engine:** 11-part specification covering auto-generation, confidence
  scoring, scenario creation, missing data handling, reasoning generation
- **Model Overview:** Football field chart for cross-model comparison, weighted composite
- **Sensitivity:** Sliders, Tornado, Monte Carlo, 2D Tables
- **Version History:** Compressed snapshots with diff view
- **Export:** Excel with live formulas + PDF reports

### Scanner (Phase 2)
- **Universe:** Russell 3000 base (~3,000 companies), expandable
- **Filters:** 100+ financial filters across 8 categories
- **Filing Search:** Full-text search across 10-K/10-Q with boolean/proximity syntax
- **Presets:** 15+ built-in screens (Value, Growth, Quality, Sector-specific)
- **Custom Filters:** Formula-based custom metric builder

### Portfolio (Phase 3)
- **Data Entry:** Manual + CSV import (Fidelity, Schwab, IBKR) + future broker API
- **Tracking:** Per-position value, cost basis, shares, weight, gain/loss
- **Performance:** TWR, MWRR/IRR, Sharpe, Sortino, max drawdown, beta
- **Attribution:** Brinson sector attribution analysis
- **Income:** Dividend tracking, upcoming ex-dates, projected annual income
- **Lot-Level:** Individual tax lots with holding period classification

### Research (Phase 4)
- **Filings:** Parsed 10-K/10-Q section viewer, filing comparison (diff)
- **Financials:** IS/BS/CF in Bloomberg-style tables, custom view builder
- **Ratios:** Full dashboard (profitability, returns, leverage, liquidity, valuation, efficiency)
- **Segments:** Revenue/profit by segment and geography
- **Peers:** Peer comparison table with relative metrics

### Dashboard (Phase 5)
- **Widgets:** Market Overview, Portfolio Summary, Watchlists, Recent Models, Upcoming Events
- **Layout:** Fixed grid (widget architecture for future customization)
- **Watchlists:** Multiple named lists, configurable columns, up to 20 lists

### Settings (Phase 2E)
- **Sections:** General, Data Sources, Model Defaults, Portfolio, Scanner, About
- **Key configs:** Refresh interval, ERP, projection period, scenario weights,
  Monte Carlo iterations, benchmark, tax lot method, backup settings
- **Auto-persist:** Changes take effect immediately, no save button

### Export (Phase 2F)
- **Excel:** Multi-sheet workbooks with live formulas (change WACC → model recalculates)
- **PDF:** Professional reports with embedded charts
- **CSV:** Simple export for scanner results
- **Available from:** Model Builder, Scanner, Portfolio, Research

---

## Data Architecture Overview

### Database Structure (Phase 0B — 23 Tables)

**user_data.db (17 tables):**
companies, models, dcf_assumptions, ddm_assumptions, revbased_assumptions,
comps_assumptions, model_outputs, model_versions, portfolio_positions,
portfolio_lots, portfolio_transactions, portfolio_accounts, watchlists,
watchlist_items, scanner_presets, price_alerts, settings

**market_cache.db (6 tables):**
financial_data, market_data, filing_cache, filing_sections, company_events,
research_notes

### API Layer (Phase 0C — 87 Endpoints)
- REST: 85 endpoints across Companies, Model Builder, Scanner, Portfolio,
  Research, Dashboard, Settings, Export, System
- WebSocket: 2 channels (prices, system status)
- Consistent JSON response envelope on all endpoints
- Full loading screen with progress bar for heavy operations (2s+)

### Cross-Module Data Flow
- Scanner finds companies → opens in Model Builder or Research
- Model Builder outputs → visible in Portfolio (valuation overlay) and Dashboard
- Portfolio holdings → enriched with model valuations and scanner signals
- Dashboard → aggregates from all modules
- Ticker Header Bar → universal cross-module navigation from any company context

### Performance Targets (Phase 0E)
- App launch: < 2.5 seconds to interactive
- Tab switch: < 200ms
- Data table render: < 300ms
- Model calculation (no Monte Carlo): 500ms - 3s
- Model calculation (Monte Carlo 10K): 3-8s
- Scanner screen (financial only): < 2s
- Memory: < 300MB idle, < 500MB active, < 800MB heavy, 1GB ceiling

### Backup Strategy (Phase 0E)
- Daily automatic backup of user_data.db
- 30-day retention
- SQLite .backup() API
- Manual backup/restore available in Settings

---

## Existing Code Migration Plan

### From Screening_Tool/
| Module | Migration Path |
|--------|---------------|
| core/sec_client.py | → Backend: services/sec_service.py |
| core/search_engine.py | → Backend: services/scanner_service.py |
| core/filter_engine.py | → Backend: services/filter_service.py |
| core/model_checker.py | → Backend: services/model_checker_service.py |
| core/company_store.py | → Backend: repositories/company_repo.py (SQLite) |
| core/xbrl_parser.py | → Backend: services/xbrl_service.py |
| core/yahoo_metrics.py | → Backend: services/market_data_service.py |
| core/universe.py | → Backend: services/universe_service.py |
| gui/* | → Replaced entirely by React frontend |

### From python_scripts/
| Module | Migration Path |
|--------|---------------|
| auto_detect_model.py | → Backend: services/model_detection_service.py |
| data_extractor.py | → Backend: services/data_extraction_service.py |
| excel_writer.py | → Backend: services/export_service.py (Excel export) |
| config.py | → Backend: config/settings.py |
| data_cache.py | → Replaced by SQLite + market_data_service.py |

### From MasterValuation_F.xlsm
| Component | Migration Path |
|-----------|---------------|
| DCF model logic | → Backend: engines/dcf_engine.py |
| DDM model logic | → Backend: engines/ddm_engine.py |
| RevBased model logic | → Backend: engines/revbased_engine.py |
| Comps model logic | → Backend: engines/comps_engine.py |
| VBA macros | → Replaced by Python calculation engines |
| Excel as output | → Export feature: generate .xlsx from model results |

---

## Project Structure (Phase 0E)

```
finance-app/
├── electron/         # Electron main process
├── frontend/         # React + TypeScript UI
└── backend/          # Python FastAPI server
    ├── engines/      # Valuation calculation engines
    ├── services/     # Business logic layer
    ├── repositories/ # Database access layer
    ├── providers/    # External data providers (Yahoo, EDGAR)
    ├── routers/      # FastAPI route handlers (1 per module)
    └── models/       # Pydantic request/response models
```

Three-folder monorepo. Each folder independently buildable.

---

## Constraints & Requirements
- **Platform:** Windows desktop (primary), macOS compatibility desirable
- **Offline capability:** Core features work without internet (cached data);
  market data refresh and filing fetch require connection
- **Performance:** App launch < 2.5s, tab switch < 200ms, data refresh non-blocking
- **Data safety:** Daily automatic backup, 30-day retention
- **No authentication:** Single-user app, no login required
- **No cloud sync:** All data local, no server dependency

---

## Open Questions (For Architect Agent)
1. Exact charting library selection (Recharts vs TradingView Lightweight Charts vs D3)
2. State management approach (Zustand vs Redux Toolkit)
3. CSS approach (custom CSS recommended, Architect may choose alternative)
4. SQLite ORM choice (SQLAlchemy vs raw SQL)
5. IPC strategy: Electron ↔ FastAPI communication pattern
6. Build/packaging tool (electron-builder vs electron-forge)
7. PDF generation library (ReportLab vs WeasyPrint)
8. Testing framework selection

---

## Handoff Notes
- Phase 0 decisions are FINAL — do not revisit framework, database, or navigation choices
- All 19 spec documents are complete and cross-referenced
- Phase 6 (Integration Review) audited all specs and applied all fixes
- This document should be referenced by the Architect as the binding technical foundation
- The existing Screening Tool codebase is production-quality Python — migration is
  refactoring into service layers, not rewriting from scratch
- The Excel workbook (MasterValuation_F.xlsm) valuation logic WILL be migrated to
  Python calculation engines — Excel becomes an export format only

---

## Complete Spec Index

| Phase | Document | Description |
|-------|----------|-------------|
| 0A | phase0_foundation.md | This file — tech stack, vision, architecture |
| 0B | phase0b_database_schema.md | 23 tables, two-DB architecture |
| 0C | phase0c_api_layer.md | 87 REST endpoints, 2 WebSocket channels |
| 0D | phase0d_ui_ux_framework.md | Color system, typography, components |
| 0E | phase0e_lifecycle_performance_structure.md | Boot, performance, monorepo |
| 1A | phase1a_dcf_model.md | Full institutional DCF |
| 1B | phase1b_ddm_model.md | 3-stage DDM |
| 1C | phase1c_comps_model.md | Auto peer selection, comps table |
| 1D | phase1d_revbased_model.md | Revenue multiples, exit method |
| 1E | phase1e_assumption_engine.md | 11-part analytical brain |
| 1F | phase1f_model_overview.md | Football field, cross-model synthesis |
| 1G | phase1g_future_models.md | Plugin architecture, LBO + NAV |
| 2 | phase2_scanner.md | R3000 universe, 100+ filters |
| 2E | phase2e_settings.md | All configurable options |
| 2F | phase2f_export.md | Excel (live formulas) + PDF exports |
| 3 | phase3_portfolio.md | Holdings, TWR/MWRR, attribution |
| 4 | phase4_research.md | Filings, financials, ratios |
| 5 | phase5_dashboard.md | Widget-based home screen |
| 6 | phase6_integration_review.md | Cross-spec audit, all issues resolved |
