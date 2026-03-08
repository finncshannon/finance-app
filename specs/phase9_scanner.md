# Finance App — Scanner Update Plan
## Phase 9: Scanner

**Prepared by:** Planner (March 5, 2026)
**Recipient:** PM Agent
**Scope:** Scanner tab — FilterPanel, ResultsTable, universe expansion

---

## PLAN SUMMARY

Four workstreams:

1. **Universe Expansion** — Load Russell 3000, S&P 500, and DOW with company names; background data hydration for financials and market data so the scanner has a real universe to scan against
2. **Filter Panel UX** — Wider metric labels, auto-formatted filter values (%, x, $), better readability
3. **Dynamic Results Columns** — Filtered metrics auto-appear as columns in results; last 3 columns become variable based on active filters
4. **Results Table Polish** — Number formatting consistency across the table

---

## AREA 1: UNIVERSE EXPANSION

### Current Problem
The `companies` table gets populated via `load_universe()` from SEC EDGAR CIK mapping (~13K tickers), but:
- Company names aren't fetched — they're set to the raw ticker string
- `cache.financial_data` and `cache.market_data` are only populated when a user manually researches a ticker
- Result: the scanner universe shows "X companies" but only ~10 actually have data to scan against

### What's Needed

#### 1A. Static Universe Lists
Ship curated ticker lists with company names as JSON files (same pattern as the S&P 500 list from the Dashboard events plan):

- `backend/data/sp500_tickers.json` — ~503 tickers with names (already planned in Phase 7)
- `backend/data/dow_tickers.json` — 30 tickers with names
- `backend/data/russell3000_tickers.json` — ~3000 tickers with names

Format:
```json
[
  {"ticker": "AAPL", "company_name": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics"},
  {"ticker": "MSFT", "company_name": "Microsoft Corporation", "sector": "Technology", "industry": "Software"},
  ...
]
```

Including sector/industry enables the scanner's sector filter to work immediately without needing to fetch each company's profile from Yahoo Finance.

**Source for initial data:** One-time generation via yfinance or a public data source. This is a build-time asset, not a runtime fetch.

#### 1B. Universe Loader Enhancement
Update `UniverseService` to load from the static JSON files:

- `load_curated_universe(name: str)` — reads the JSON file, bulk-inserts into `companies` table with proper company names, sectors, industries
- Tag each company with `universe_source`: `"sp500"`, `"dow"`, `"r3000"`
- Companies can belong to multiple universes (AAPL is in all three)
- Add a `universe_memberships` table or a comma-separated `universe_tags` column on `companies`

#### 1C. Background Data Hydration
**Goal:** After loading the universe, progressively fetch financials and market data for all tickers so the scanner has real data.

**Strategy (tiered, same pattern as events fetcher from Phase 7):**
1. **Priority 1 — DOW (30 tickers):** Fetch immediately on first load. Takes ~1-2 minutes.
2. **Priority 2 — S&P 500 (500 tickers):** Background task after DOW completes. Takes ~15-20 minutes.
3. **Priority 3 — Russell 3000 (3000 tickers):** Background task, only fetch stale/missing. Takes several hours on first run, minutes on subsequent startups.

**Staleness:** Same 24-hour threshold as existing `FINANCIAL_STALE_SECONDS`. Only refetch tickers where data is missing or older than 24 hours.

**Implementation:**
- New `UniverseHydrationService` (or extend `UniverseService`) with `run_hydration()` method
- Called as `asyncio.create_task()` in `main.py` lifespan after services are initialized
- Fetches: market quote data (`get_live_quote`) + financials (`get_financials`) per ticker
- Rate limiting: respect Yahoo Finance's ~2000 req/hour limit (existing `_RateLimiter`)
- Progress logging: "Hydrating universe: 142/500 S&P 500 tickers..."
- Dashboard can show hydration progress (optional)

**Endpoint:** `GET /api/v1/universe/hydration-status` — returns progress of background hydration

#### 1D. Universe Selector in Scanner
**Current:** A `universe` dropdown with "all" as the only real option.
**New options:**
- All (everything in DB)
- S&P 500
- DOW 30
- Russell 3000
- Custom (from watchlists — scan only tickers in a selected watchlist)

The scanner already supports `universe` as a request parameter. The backend just needs to filter by `universe_source` tag.

**Files touched (all of Area 1):**
- `backend/data/sp500_tickers.json` — new (or shared with Phase 7)
- `backend/data/dow_tickers.json` — new
- `backend/data/russell3000_tickers.json` — new
- `backend/services/universe_service.py` — curated universe loader, universe tags
- `backend/services/universe_hydration_service.py` — new file, background hydration
- `backend/routers/universe_router.py` — hydration status endpoint, load curated endpoint
- `backend/main.py` — hydration startup task
- `backend/db/init_user_db.py` — add `universe_tags` column to companies table (or new membership table)
- `frontend/src/pages/Scanner/FilterPanel/FilterPanel.tsx` — universe selector with DOW/S&P/R3000/Custom options
- `frontend/src/pages/Scanner/ScannerPage.tsx` — pass universe selection to scan request

---

## AREA 2: FILTER PANEL UX

### Current Problems
- Metric names in the filter dropdown are truncated — not enough width to read "EV/EBITDA" or "Revenue Growth YoY"
- Filter value inputs are raw numbers — user types `0.15` when they mean 15%, or `12` when they mean 12x

### Changes

#### 2A. Wider Metric Picker
- Increase the FilterRow metric dropdown width from its current constrained size
- Show full metric labels without truncation
- Add the metric category as a subtle prefix or group header in the dropdown: "Valuation > EV/EBITDA"
- The MetricPicker component already has categories — ensure they render clearly with enough space

#### 2B. Auto-Formatted Filter Values
- When a metric is selected, the filter value input should auto-format based on the metric's `format` field:
  - `format: "percent"` → input shows `%` suffix, user types `15` and it means 0.15 internally
  - `format: "ratio"` → input shows `x` suffix, user types `12` and it means 12.0x
  - `format: "currency"` → input shows `$` prefix with compact formatting
  - `format: "integer"` → plain number, no suffix
- The conversion between display format and internal value happens at the input boundary (same pattern as AssumptionCard's `toDisplay`/`fromDisplay`)
- For "Between" operator: both low and high inputs get the same formatting

#### 2C. Filter Summary Tags
Show active filters as small summary tags above the results table:
```
Filters: [P/E < 20x] [Market Cap > $10B] [Revenue Growth > 15%] [Sector: Technology]
```
This gives quick visibility into what's filtering the results without scrolling the filter panel.

**Files touched:**
- `frontend/src/pages/Scanner/FilterPanel/FilterRow.tsx` — wider dropdown, auto-format value inputs
- `frontend/src/pages/Scanner/FilterPanel/FilterRow.module.css` — width adjustments
- `frontend/src/pages/Scanner/FilterPanel/MetricPicker.tsx` — wider dropdown, category labels
- `frontend/src/pages/Scanner/FilterPanel/MetricPicker.module.css` — width/spacing
- `frontend/src/pages/Scanner/ResultsTable/ResultsHeader.tsx` — filter summary tags
- `frontend/src/pages/Scanner/types.ts` — add display format helpers for filter values

---

## AREA 3: DYNAMIC RESULTS COLUMNS

### Current Behavior
The ResultsTable always shows the same 7 default columns: Price, Market Cap, P/E, EV/EBITDA, ROE, Revenue Growth, Dividend Yield. The user can manually toggle column visibility via the column selector, but it doesn't react to filter changes.

### New Behavior
When a filter is applied for a metric that isn't already in the visible columns, that metric automatically appears as a column in the results table. This way you always see the data you're filtering on.

**Logic:**
- Maintain 4 "fixed" columns: Ticker, Company, Sector + 1 core metric (Price or Market Cap)
- The next columns are the default set (P/E, EV/EBITDA, ROE, Revenue Growth)
- The last 3 columns are **variable**: they change to show whatever metrics are in the active filters
- If a filter metric is already in the default columns, no duplication — the variable slots fill with the next unique filter metric
- When filters are cleared, the variable columns revert to defaults (Dividend Yield, Op Margin, FCF or similar)

**Implementation:**
- In `ScannerPage.tsx`, compute `effectiveColumns` based on `filters` + `DEFAULT_COLUMNS`
- Pass `effectiveColumns` to `ResultsTable` instead of the static `visibleColumns`
- The manual column selector still works as an override — if the user manually configures columns, that takes priority over auto-detection

**Files touched:**
- `frontend/src/pages/Scanner/ScannerPage.tsx` — compute effective columns from filters
- `frontend/src/pages/Scanner/ResultsTable/ResultsTable.tsx` — accept dynamic columns
- `frontend/src/pages/Scanner/types.ts` — update DEFAULT_COLUMNS logic

---

## AREA 4: RESULTS TABLE POLISH

### Changes

#### 4A. Consistent Number Formatting
Ensure all metric values in the table use the same formatting as the filter panel:
- Percentages show as `15.2%` not `0.152`
- Ratios show as `12.5x` not `12.5`
- Currency shows as `$245.3B` not `245300000000`

The `formatMetricValue` function already handles this — verify it's applied consistently to all cells including the detail panel and any dynamic columns.

#### 4B. Negative Value Highlighting
Negative values should be colored red (`--color-negative`) across all metric columns, not just specific ones.

#### 4C. Row Count and Scan Summary
Improve the results header to show a clearer summary:
"Showing 1–100 of 342 matches from S&P 500 (503 companies scanned) · 3 filters applied · 245ms"

**Files touched:**
- `frontend/src/pages/Scanner/ResultsTable/ResultsTable.tsx` — formatting verification, negative highlighting
- `frontend/src/pages/Scanner/ResultsTable/ResultsHeader.tsx` — improved summary text
- `frontend/src/pages/Scanner/ResultsTable/DetailPanel.tsx` — formatting consistency

---

## SESSION ORGANIZATION (Recommended for PM)

### Session 9A — Universe Data Files + Backend Loader (Backend Only)
**Scope:** Areas 1A, 1B, 1D backend
**Files:**
- `backend/data/sp500_tickers.json` — new (or shared with Phase 7)
- `backend/data/dow_tickers.json` — new
- `backend/data/russell3000_tickers.json` — new
- `backend/services/universe_service.py` — curated loader, universe tags
- `backend/db/init_user_db.py` — universe tags schema
- `backend/routers/universe_router.py` — load curated endpoint
- `backend/services/scanner/scanner_service.py` — filter by universe tag
**Complexity:** Medium (data file generation is the main effort; loader is straightforward)
**Estimated acceptance criteria:** 10–12

### Session 9B — Universe Hydration Service (Backend Only)
**Scope:** Area 1C
**Files:**
- `backend/services/universe_hydration_service.py` — new file
- `backend/main.py` — startup hydration task
- `backend/routers/universe_router.py` — hydration status endpoint
**Complexity:** Medium-High (rate-limited background fetching, progress tracking, staleness logic)
**Estimated acceptance criteria:** 12–15
**Depends on:** Session 9A (universe tickers must be loaded)

### Session 9C — Scanner Frontend (Frontend Only)
**Scope:** Areas 1D frontend, 2, 3, 4
**Files:**
- `FilterPanel.tsx` — universe selector
- `FilterRow.tsx` — wider metrics, auto-format values
- `FilterRow.module.css` — width adjustments
- `MetricPicker.tsx` — wider dropdown, category labels
- `MetricPicker.module.css` — width/spacing
- `ScannerPage.tsx` — dynamic columns logic, universe param
- `ResultsTable.tsx` — dynamic columns, formatting, negative highlight
- `ResultsHeader.tsx` — filter tags, improved summary
- `DetailPanel.tsx` — formatting consistency
- `types.ts` — format helpers, column logic
**Complexity:** Medium (filter UX improvements, dynamic column logic)
**Estimated acceptance criteria:** 18–22
**Depends on:** Session 9A (universe options in selector)

---

## DEPENDENCIES & RISKS

| Risk | Mitigation |
|------|------------|
| Russell 3000 JSON file is large (~3000 entries with names/sectors) | Still only ~500KB as JSON; loaded once on startup, cached in memory |
| Background hydration hits Yahoo Finance rate limit | Existing rate limiter caps at 2000 req/hour; hydration respects this. DOW finishes fast, S&P 500 in ~15 min, R3000 takes hours but is background |
| First-time startup with empty cache takes hours to hydrate | Scanner works immediately with whatever data exists; shows "X of Y companies have data" indicator. User can start scanning S&P 500 after ~15 min. |
| Universe selector "Custom (Watchlist)" adds complexity | Use existing watchlist service to get ticker list; pass as filter to scanner. Simple integration. |
| Dynamic columns cause table to jump around as filters change | Transition smoothly: only add/remove variable columns, keep fixed columns stable. Debounce column changes with filter debounce. |
| Auto-format values confuse users who expect raw decimals | Show the format suffix clearly (%, x, $) and allow raw input with auto-conversion. Tooltip: "Enter 15 for 15%" |

---

## DECISIONS MADE

1. Ship curated ticker lists as static JSON files (S&P 500, DOW 30, Russell 3000) with company names, sectors, industries
2. Background hydration runs on startup with priority tiers: DOW → S&P 500 → R3000
3. Hydration respects existing Yahoo Finance rate limiter (~2000 req/hour)
4. Universe selector options: All, S&P 500, DOW 30, Russell 3000, Custom (Watchlist)
5. Filter value inputs auto-format based on metric type (%, x, $)
6. Metric picker widened to show full labels with category grouping
7. Last 3 results columns are variable — auto-populated from active filter metrics
8. Manual column selector overrides auto-detection
9. Filter summary tags shown above results table
10. Consistent number formatting across all table cells and panels

---

*End of Scanner Update Plan*
*Phase 9A–9C · Prepared March 5, 2026*
