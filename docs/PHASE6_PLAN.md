# Phase 6 — Final Polish, Packaging & QA

> **Status:** In progress
> **Last updated:** March 4, 2026
> **Tracking:** ClickUp list "Phase 6 — Final Polish, Packaging & QA"

---

## Overview

Phase 6 is the final phase before v1.0 release. It covers codebase quality assurance, runtime bug fixes, UX polish, Electron packaging into a distributable .exe, and final verification. The app has been built across 5 prior phases covering: Model Builder engines (Phase 1), Data Layer & Providers (Phase 2), Scanner/Portfolio/Dashboard (Phase 3-4), and Research/Export/Integration (Phase 5).

---

## Session Plan

| Session | Tasks | Focus | Status |
|---------|-------|-------|--------|
| **6A** | 6.1 + 6.3 | Codebase audit + runtime wiring fixes | ✅ COMPLETE |
| **6B** | 6.2 + 6.5 | Expanded smoke test + UX polish (error boundaries, empty/error/loading states) | 🔲 TODO |
| **6C** | 6.6 + 6.7 | Visual QA + performance audit + TypeScript check | 🔲 TODO |
| **6D** | 6.4 | Electron packaging (icon, Python check, build verification) | 🔲 TODO |
| **6E** | 6.8 + 6.9 | Spec reconciliation + final build verification | 🔲 TODO |

---

## Completed Work (Session 6A)

### 6.1 — Codebase Audit ✅
- **comps_engine.py:** Fixed `book_value` → `stockholders_equity` (3 locations). P/B ratio was always null because the DB field name didn't match.
- **revbased_engine.py:** Fixed `operating_expenses` → `operating_expense` (singular). OpEx lookups were silently failing.
- **engines/models.py:** Added `@computed_field weighted_implied_price` to `CompsResult`. Previously, Comps models saved `intrinsic_value_per_share = 0` to the DB because the router couldn't find the expected field. Now uses quality-adjusted midpoint from football field.

### 6.3 — Runtime Wiring Fixes ✅
- Created `frontend/src/config.ts` with `BASE_URL` and `WS_URL` (uses `VITE_API_URL` env var with localhost fallback).
- Consolidated all 4 hardcoded `http://localhost:8000` references to import from config:
  - `api.ts` — imports from config
  - `exportService.ts` — imports from config
  - `navigationService.ts` — imports from config (in `addToWatchlist`)
  - `settingsStore.ts` — imports from config
- `websocket.ts` already used `WS_URL` from config.
- Note: `settingsStore` still uses raw `fetch()` instead of the `api` service. Functionally correct (handles envelope manually), just a style inconsistency.

---

## Known Architecture Context

### Backend (FastAPI + Python 3.12)
- All services registered on `app.state` in `main.py` lifespan
- Standard response envelope: `{ "success": true, "data": {...}, "error": null }`
- Routers: system, companies, models, scanner, portfolio, research, dashboard, settings, export, universe
- WebSocket: `/ws/prices` (live quotes), `/ws/status` (system health)
- Databases: `user_data.db` (models, portfolio, settings) + `market_cache.db` (financials, filings, prices)

### Frontend (React + TypeScript + Vite + Zustand)
- Zustand stores: ui, model, research, market, portfolio, scanner, settings
- CSS Modules with shared dark theme (`variables.css`)
- Module pages: Dashboard, ModelBuilder, Scanner, Portfolio, Research, Settings
- Shared components: BootSequence, ModuleTabBar, TickerHeaderBar, Tabs, WatchlistPicker
- Navigation: `navigationService.ts` + `useTickerNavigation` hook

### Electron (already scaffolded)
- `electron/main.ts` — backend spawn, health polling, window state persistence, IPC, crash recovery
- `electron/preload.ts` — context bridge (`getBackendUrl`, `onBackendReady`, `onLayoutChange`)
- `electron/electron-builder.yml` — NSIS (Windows) + DMG (Mac) config
- `electron/package.json` — dev/build/package scripts
- Root workspace config links `electron/` and `frontend/`

### What's NOT built yet
- `electron/resources/` directory with app icons (referenced by builder but missing)
- No React ErrorBoundary component — component crashes white-screen the app
- No PyInstaller config — current builder bundles raw .py files (requires Python pre-installed)
- No `tsc --noEmit` verification run
- Smoke test only covers 16 read-only API endpoints (doesn't test engine runs, version save/load, WebSocket)

---

## Gaps Identified During Audit

### Critical
1. **No React ErrorBoundary** — Any component render crash kills the entire UI with no recovery. Must add before packaging.
2. **Smoke test is shallow** — Doesn't test the core Model Builder workflow (detection → assumption generation → engine run → version save). The 20-point test plan in task 6.2 covers this but `smoke_test.py` only implements 16 of those points.
3. **Electron build never actually tested** — All scaffolding exists but `electron-builder` has never been run to produce a .exe.

### Important
4. **App icons missing** — `electron-builder.yml` references `resources/icon.ico` / `resources/icon.icns` but no `resources/` directory exists.
5. **Python bundling undecided** — Task 6.4 says "recommend PyInstaller" but current config bundles raw .py. Decision: require Python pre-installed for v1.0, add startup check, defer PyInstaller to v1.1.
6. **TypeScript not verified** — `tsc --noEmit` hasn't been run across the frontend to catch type errors.
7. **Empty/error/loading states inconsistent** — Each module handles these differently. Needs audit + standardization pass.

### Nice-to-have (defer if needed)
8. **settingsStore uses raw fetch** — Works but inconsistent with other stores using `api` service.
9. **Keyboard shortcuts** — Referenced in 6.5 but low value relative to effort.
10. **Bundle size audit** — Should check `vite build` output size before packaging.

---

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Python bundling for v1.0 | Require pre-installed | PyInstaller adds build complexity + 200MB+ to installer. Users are devs who have Python. Defer PyInstaller to v1.1. |
| settingsStore refactor | Defer | Works correctly with raw fetch. Not worth the risk of breaking settings before packaging. |
| Keyboard shortcuts | Defer | Low user impact, high implementation effort across 6 modules. |
| Model type naming (`revenue_based` vs `revbased`) | Document only | Inconsistent but functional. API path uses `revbased`, model_type field uses `revenue_based`. Fixing would require DB migration. |
