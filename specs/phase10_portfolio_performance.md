# Finance App — Portfolio: Performance Sub-Tab + Live Data Fix Plan
## Phase 10: Portfolio — Performance + Cross-Cutting Data Issues

**Prepared by:** Planner (March 5, 2026)
**Recipient:** PM Agent
**Scope:** Portfolio → Performance sub-tab, plus cross-cutting fixes for live data refresh, stale prices, missing company names/sectors, and tab-level refresh button

---

## PLAN SUMMARY

This plan covers Performance-specific issues plus critical cross-cutting data problems that affect the entire app:

1. **Benchmark Chart Fidelity Upgrade** — Fix the sloppy graph, responsive formatting, proper labels
2. **Attribution "Unknown" Sector Fix** — Investigate and fix 70% unknown in attribution table
3. **Shorter Timeframes** — Add 1D, 3D, 5D, 2W period options
4. **Holdings Missing Names/Sectors** — Company names and sectors not populated for most positions
5. **Live Data / Price Refresh Fix** — Critical: prices not updating, market status wrong, SPY showing 85% gain, no refresh outside market hours
6. **Tab-Level Refresh Button** — Add refresh button to Portfolio (and other modules) since only Dashboard has one

---

## AREA 1: BENCHMARK CHART FIDELITY UPGRADE

### Current Problems
- The benchmark comparison chart (BenchmarkChart.tsx) has responsive formatting issues — numbers get smushed or overlap when the window resizes
- Labels aren't clear enough — hard to tell which line is portfolio vs benchmark at a glance
- No interactive features (hover to see exact values at a point in time)
- General "sloppy" feel — needs the same Fidelity-level upgrade as other charts

### Changes
- Use Recharts LineChart with proper responsive handling — Y-axis labels should use compact format ($100K not $100,000) and have adequate padding
- Add clear line legend: portfolio line in accent blue, benchmark (SPY) in a distinct color (gray or orange)
- Add tooltip on hover: shows date, portfolio value, benchmark value, and the difference (alpha) at that point
- Add crosshair cursor that follows mouse along the time axis
- Y-axis should auto-scale with padding so lines don't touch the edges
- X-axis should show readable date labels (not overlapping) — thin out labels at longer timeframes
- Add a shaded area between the two lines when portfolio outperforms (green tint) vs underperforms (red tint) — optional but impactful visual
- Fix responsive behavior: test at compact (1024px), standard (1280px), wide (1600px+)

### Return Metrics and Risk Metrics Formatting
- These panels also have formatting issues at different window sizes
- Numbers should use responsive font sizing or stack vertically on narrow viewports
- Ensure consistent number formatting: percentages as `+12.3%` not `0.123`, dollar values in compact format

**Files touched:**
- `frontend/src/pages/Portfolio/Performance/BenchmarkChart.tsx` — chart overhaul
- `frontend/src/pages/Portfolio/Performance/BenchmarkChart.module.css` — responsive styles
- `frontend/src/pages/Portfolio/Performance/ReturnMetrics.tsx` — formatting fix
- `frontend/src/pages/Portfolio/Performance/ReturnMetrics.module.css` — responsive layout
- `frontend/src/pages/Portfolio/Performance/RiskMetrics.tsx` — formatting fix
- `frontend/src/pages/Portfolio/Performance/RiskMetrics.module.css` — responsive layout

---

## AREA 2: ATTRIBUTION "UNKNOWN" SECTOR FIX

### Current Problem
The Performance Attribution table shows ~70% as "Unknown" sector. This is because the `positions` table stores sector from company profile data, but most positions don't have their company profile fetched/cached yet (same root cause as the missing names issue in Area 4).

### Root Cause
When a position is added via manual entry or CSV import, only the ticker is stored. The company name, sector, and industry are only populated if/when the company profile is fetched from Yahoo Finance — which happens on demand (when you research or model that ticker), not automatically when you add a position.

### Fix (Shared with Area 4)
When a position is added, auto-fetch the company profile in the background. See Area 4 for full details.

### Attribution Table Improvements
Even with sector data fixed, the attribution table could be more informative:
- Show the sector weight and return data more clearly
- Add a bar chart visualization of allocation vs selection effects per sector
- Make sure the total row is prominent and the math adds up visibly
- If sectors are still partially unknown, show "Unknown ({N} positions)" with a note: "Fetch company data to classify these positions"

**Files touched:**
- `frontend/src/pages/Portfolio/Performance/AttributionTable.tsx` — layout improvements, unknown handling
- `frontend/src/pages/Portfolio/Performance/AttributionTable.module.css` — bar chart, emphasis styles

---

## AREA 3: SHORTER TIMEFRAMES

### Current
Period options: 1M, 3M, 6M, YTD, 1Y, 3Y, ALL

### New
Add: **1D, 3D, 5D, 2W** before the existing options.

Full list: `1D, 3D, 5D, 2W, 1M, 3M, 6M, YTD, 1Y, 3Y, ALL`

### Backend Implications
The performance calculation endpoints (`/api/v1/portfolio/performance`, `/api/v1/portfolio/benchmark`) accept a `period` query parameter. The backend needs to:
- Map `1D`, `3D`, `5D`, `2W` to the correct date ranges
- For the benchmark chart, fetch intraday or daily historical data for SPY at these short timeframes
- The portfolio daily values (`DailySnapshot`) may not have sub-daily granularity — for 1D/3D, we'd need to either show daily close values or note "Intraday data not available — showing daily close"

### Performance Data for Short Periods
- `1D`: Today's portfolio value vs yesterday's close. If market is open, use current live prices.
- `3D`, `5D`: Last 3/5 trading days of daily closes.
- `2W`: Last 10 trading days.
- TWR/MWRR calculations at these short periods may not be meaningful — show raw return instead (just % change from start to end)

**Files touched:**
- `frontend/src/pages/Portfolio/Performance/PerformanceTab.tsx` — add new period options
- `backend/routers/portfolio_router.py` — handle new period values
- `backend/services/portfolio/analytics.py` — short-period return calculation
- `backend/services/portfolio/benchmark.py` — short-period benchmark data

---

## AREA 4: HOLDINGS MISSING NAMES / SECTORS

### Current Problem
Most positions in Holdings show no company name and no sector. The `companies` table only gets populated with full profile data (name, sector, industry) when the user explicitly researches or models a ticker. Positions added via manual entry or CSV import only have the ticker stored.

### Fix — Auto-Fetch on Position Add
When a position is created (via Add Position modal, CSV import, or transaction import):
1. After the position record is created, queue a background task to fetch the company profile
2. Call `CompanyService.get_or_create_company(ticker)` which fetches from Yahoo Finance and caches
3. This populates company_name, sector, industry in the `companies` table
4. The holdings table joins against `companies` for display — once the profile is cached, names/sectors appear

### Also: Batch Fetch for Existing Positions
For positions already in the DB without profile data:
- Add a one-time migration/fix endpoint: `POST /api/v1/portfolio/refresh-profiles`
- This iterates all unique tickers in positions, checks if they have a company profile, and fetches missing ones
- Run automatically on app startup as a background task (low priority, after event hydration)

**Files touched:**
- `backend/services/portfolio/portfolio_service.py` — add auto-fetch on position create
- `backend/routers/portfolio_router.py` — add refresh-profiles endpoint
- `backend/main.py` — add startup task for profile backfill
- `frontend/src/pages/Portfolio/Holdings/HoldingsTable.tsx` — verify name/sector display from company data

---

## AREA 5: LIVE DATA / PRICE REFRESH FIX (CRITICAL)

### Current Problems

**Problem 1: No refresh outside market hours.**
The `PriceRefreshService.run_refresh_loop()` has `if MarketDataService.is_market_open()` — outside market hours, it does nothing. So if you open the app after hours or on a weekend, you see whatever stale data was last cached. There's no initial refresh on startup.

**Problem 2: Dashboard market status wrong.**
"After hours ending in 2 hours" showing at wrong times. The `DashboardService.get_market_status()` calculates based on ET time but may have timezone/DST bugs, or the status isn't being refreshed (status broadcast loop sends the status, but the dashboard may not be consuming it properly).

**Problem 3: SPY showing 85% gain.**
This is almost certainly a `day_change_pct` format mismatch. Yahoo Finance returns `day_change_pct` as a percentage (e.g., `0.85` meaning `0.85%`), but the frontend's `fmtPct` function multiplies by 100 (treating it as a decimal ratio). So `0.85` becomes `85%` instead of `0.85%`. Need to verify the data format at each layer: Yahoo → cache → API response → frontend display.

**Problem 4: Portfolio tab has no way to trigger a refresh.**
Only the Dashboard has a refresh button. Portfolio shows whatever was loaded on first render.

### Fixes

#### 5A. Startup Refresh
Add a one-time price refresh on app startup regardless of market hours:
- In `main.py` lifespan, after all services initialize, call `market_data_svc.refresh_batch()` for all portfolio tickers + watchlist tickers
- This ensures fresh data on every app launch
- The existing 60-second loop continues to handle live updates during market hours

#### 5B. After-Hours Refresh
Modify `run_refresh_loop()`:
- During market hours: refresh every 60 seconds (existing)
- Outside market hours: refresh every 15 minutes (new) — prices still change in after-hours trading, and stale cache from hours ago is bad
- On weekends: refresh once on startup, then every hour (very low frequency, just to catch any corrections)

#### 5C. Market Status Fix
Audit `DashboardService.get_market_status()`:
- Verify timezone handling (DST transitions, `ZoneInfo("America/New_York")` fallback to UTC-5)
- The status WebSocket broadcasts every 30 seconds — verify the frontend is consuming `system_status` messages and updating the dashboard's market status indicator
- Add logging to the status calculation so we can debug time-based issues

#### 5D. Day Change Percentage Fix
Trace the `day_change_pct` value through the entire pipeline:
1. **Yahoo Finance provider:** `get_quote()` returns `day_change_pct` — check if this is already a percentage (0.85) or a ratio (0.0085)
2. **Market data cache:** stored in `cache.market_data.day_change_pct` — what format?
3. **Dashboard service:** reads from cache, returns in API response — what format?
4. **Frontend:** `fmtPct()` multiplies by 100 — if the value is already a percentage, this double-multiplies

The fix depends on where the format mismatch is. Most likely: Yahoo returns it as a percentage already, the cache stores it as-is, and the frontend's `fmtPct(value * 100)` pattern double-multiplies. The fix is to normalize: either store as a decimal ratio everywhere and let `fmtPct` multiply, or store as a percentage and don't multiply.

#### 5E. WebSocket Subscription for Portfolio
Currently, the WebSocket price subscription is only triggered when the frontend explicitly calls `wsManager.subscribeTickers()`. The portfolio page doesn't do this — it fetches positions via REST on mount and that's it.

Fix: When PortfolioPage loads, subscribe all position tickers to the WebSocket price feed so they get live updates. When prices update via WebSocket, the holdings table should reactively show the new values.

**Files touched:**
- `backend/services/price_refresh_service.py` — startup refresh, after-hours refresh interval
- `backend/services/dashboard_service.py` — market status audit and fix
- `backend/main.py` — add startup price refresh task
- `backend/providers/yahoo_finance.py` — verify day_change_pct format
- `backend/services/market_data_service.py` — normalize day_change_pct format
- `frontend/src/pages/Portfolio/PortfolioPage.tsx` — WebSocket subscription for position tickers
- `frontend/src/pages/Dashboard/DashboardPage.tsx` — verify market status consumption from WebSocket
- `frontend/src/pages/Dashboard/MarketOverview/MarketOverviewWidget.tsx` — verify day_change_pct display

---

## AREA 6: TAB-LEVEL REFRESH BUTTON

### Current Problem
Only the Dashboard has a Refresh button. Portfolio, Scanner, Research, and Model Builder have no way to trigger a data refresh without reloading the app.

### Fix
Add a refresh button to the Portfolio page header (and as a pattern, other module headers too):

```
Portfolio    [All Accounts ▾]  [Export ▾]  [Import CSV]  [+ Add Position]  [↻ Refresh]
```

**Behavior:**
- Refreshes all position data (re-fetches from backend, which refreshes from Yahoo if stale)
- Also refreshes performance, allocation, income data for the active sub-tab
- Shows a brief loading indicator while refreshing
- Can be extended to other modules later (add to Scanner header, Research header, etc.)

**Files touched:**
- `frontend/src/pages/Portfolio/PortfolioPage.tsx` — add Refresh button, loading state
- `frontend/src/pages/Portfolio/PortfolioPage.module.css` — button styles

---

## SESSION ORGANIZATION (Recommended for PM)

### Session 10C — Live Data Fix (Backend Critical)
**Scope:** Areas 5A–5D, 4 (profile backfill backend)
**Files:**
- `backend/services/price_refresh_service.py` — startup refresh, after-hours interval
- `backend/services/dashboard_service.py` — market status fix
- `backend/services/market_data_service.py` — day_change_pct normalization
- `backend/providers/yahoo_finance.py` — verify format
- `backend/services/portfolio/portfolio_service.py` — auto-fetch profile on position create
- `backend/routers/portfolio_router.py` — refresh-profiles endpoint
- `backend/main.py` — startup tasks (price refresh, profile backfill)
**Complexity:** High (multiple interacting systems, format tracing, background task coordination)
**Estimated acceptance criteria:** 18–22
**Priority:** CRITICAL — this affects all modules
**Coordination:** Session 11A (Data Accuracy Normalization) addresses the same root cause (format mismatch) at a broader scope. PM should either: (a) merge 10C and 11A into one comprehensive "Data Integrity" session, or (b) run 11A first as the full audit, then 10C adds the live refresh / startup / WebSocket fixes on top. Do NOT run them independently without coordination — they modify the same files.

### Session 10D — Performance Frontend + Refresh + Live Subscription (Frontend Only)
**Scope:** Areas 1, 2, 3, 5E, 6
**Files:**
- `BenchmarkChart.tsx` — chart overhaul
- `BenchmarkChart.module.css` — responsive styles
- `ReturnMetrics.tsx` — formatting fix
- `RiskMetrics.tsx` — formatting fix
- `AttributionTable.tsx` — unknown handling, layout improvements
- `PerformanceTab.tsx` — new period options
- `PortfolioPage.tsx` — Refresh button, WebSocket subscription
- `PortfolioPage.module.css` — button styles
- `DashboardPage.tsx` — verify market status consumption (minor)
- `MarketOverviewWidget.tsx` — verify day_change_pct display (minor)
**Complexity:** Medium-High (chart overhaul, responsive fixes, WebSocket integration)
**Estimated acceptance criteria:** 22–28
**Depends on:** Session 10C (backend data fixes must exist)

---

## DEPENDENCIES & RISKS

| Risk | Mitigation |
|------|------------|
| day_change_pct format fix breaks other consumers of the data | Audit all places that read day_change_pct before changing; normalize at the storage layer so all consumers get consistent format |
| Startup refresh for all portfolio tickers slow with many positions | Batch refresh is already sequential with rate limiting; 30 tickers takes ~30 seconds. Show loading indicator. |
| Short timeframes (1D, 3D) produce empty benchmark charts if no recent data | Show "Market data not available for this period" message; fall back to daily close if intraday not available |
| After-hours refresh every 15 minutes increases Yahoo API usage | 15 minutes × ~30 tickers = ~120 req/hour outside market hours, well within 2000/hour limit |
| Profile auto-fetch on position add adds latency to the add flow | Fetch asynchronously after the position is created — don't block the UI |
| Attribution sector fix depends on Area 4 profile data being populated | Run profile backfill before attribution is calculated; show "Refreshing company data..." on first run |

---

## DECISIONS MADE

1. Benchmark chart gets full Fidelity upgrade — hover tooltips, crosshair, proper legends, responsive
2. Attribution table handles "Unknown" gracefully with count and suggestion to refresh
3. Short periods added: 1D, 3D, 5D, 2W — TWR/MWRR replaced with simple % return for sub-monthly periods
4. Company profiles auto-fetched when positions are created
5. One-time profile backfill runs on startup for existing positions
6. Price refresh runs on startup regardless of market hours
7. After-hours refresh interval: every 15 minutes (down from "never")
8. Weekend refresh: once on startup, then hourly
9. day_change_pct normalized to decimal ratio throughout (0.0085 not 0.85) — frontend multiplies by 100
10. Portfolio page subscribes position tickers to WebSocket for live updates
11. Refresh button added to Portfolio header (pattern for other modules too)

---

*End of Portfolio — Performance + Live Data Fix Plan*
*Phase 10C–10D · Prepared March 5, 2026*
