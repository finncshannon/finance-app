# Finance App — Research Update Plan
## Phase 11: Research

**Prepared by:** Planner (March 5, 2026)
**Recipient:** PM Agent
**Scope:** Research tab — Profile, Financials, Ratios, Filings, Peers

---

## PLAN SUMMARY

Six workstreams:

1. **Data Accuracy Audit & Fix (CRITICAL)** — Systemic format normalization across the entire data pipeline; fixes incorrect dividend yield, ROE, growth rates, and all percentage-format fields. This is the same root cause as the SPY 85% gain issue from Phase 10C but broader in scope.
2. **Profile Enhancements** — Add shares outstanding and enterprise value to key stats, add 10-K business model / segment information
3. **Filings — Fetch New Filings** — Add ability to trigger a fresh filing fetch for companies with no cached filings
4. **Peers Tab — Accuracy Pass** — Ensure peer comparison metrics are formatted correctly after the normalization fix
5. **Ratios Tab — Trend Chart Fidelity Upgrade + DuPont ROE Fix** — Better trend analysis chart with more detail and clarity; DuPont decomposition needs context for extreme ROE values
6. **Stock Price Charts** — Add interactive price charts to Research, making it more of a full research/analysis hub

---

## AREA 1: DATA ACCURACY AUDIT & FIX (CRITICAL)

### Root Cause
The data pipeline has a systemic format inconsistency for percentage-type values. Yahoo Finance returns some fields as ratios (0.0051 meaning 0.51%) and others as percentages (0.51 meaning 0.51%). The cache stores them as-is. The `DataExtractionService` computes additional metrics from these cached values. The frontend's `fmtPct()` function always multiplies by 100 (assuming ratio input). When a value is already a percentage, it gets double-multiplied.

**Known broken values:**
- Apple dividend yield showing 39% (should be ~0.5%)
- ROE showing 150% (Apple's ROE is legitimately high at ~150% because of negative book equity from buybacks — this might actually be correct, but needs verification)
- Net income growth showing 190% (likely a one-year spike or format issue)
- SPY day_change_pct showing 85% (Phase 10C issue, same root cause)

### Fix — Full Pipeline Normalization

#### 1A. Audit Every Field in the Pipeline
Create a normalization specification document that defines the canonical format for every numerical field at every layer:

**Layer definitions:**
1. **Yahoo Finance Provider** (`yahoo_finance.py`) — what format does yfinance return?
2. **Cache DB** (`cache.market_data`, `cache.financial_data`) — what format do we store?
3. **Data Extraction Service** — what format does `compute_all_metrics()` return?
4. **API Response** — what format does the endpoint return to the frontend?
5. **Frontend Display** — what does `fmtPct()` / `fmtRatio()` expect?

**Canonical rule:** All ratios/percentages stored as **decimal ratios** (0.15 meaning 15%). Frontend `fmtPct()` multiplies by 100. This is already the intended convention — the bug is fields that violate it.

**Fields to audit (high-risk for format mismatch):**
- `dividend_yield` — Yahoo may return as 0.0051 (ratio) or 0.51 (percentage) depending on the endpoint
- `day_change_pct` — Yahoo returns as percentage in some cases
- `revenue_growth` — computed in `yahoo_finance.py`, verify formula
- `gross_margin`, `operating_margin`, `net_margin` — computed as `gross_profit / revenue`, should be ratio
- `roe` — `net_income / stockholders_equity` — can legitimately be >100% for companies with negative equity
- `payout_ratio` — `abs(dividends_paid) / abs(net_income)` — verify
- All `_growth` and `_cagr` metrics in DataExtractionService

#### 1B. Backend Normalization Pass
For each field identified as misformatted:
- Fix at the **storage layer** (in the provider or upsert logic) so the cache always stores decimal ratios
- Add normalization helpers: `ensure_ratio(value, source_format)` that converts percentage→ratio if needed
- Add validation: clamp obviously wrong values (dividend yield > 1.0 as a ratio → cap or flag as suspicious)

#### 1C. Frontend Verification
After backend normalization:
- Verify `fmtPct()` consistently receives ratios and multiplies by 100
- Verify `KeyStatsCard`, `RatioPanel`, `ReturnMetrics`, `AttributionTable` all use the correct formatter
- Add a sanity check: if a "percentage" field has a value > 5.0 (meaning >500%), show a warning indicator rather than displaying it as-is. Legitimate values >500% exist (ROE for negative-equity companies) but they should be flagged.

#### 1D. ROE Edge Case Handling
Apple's ROE really is ~150% because stockholders_equity is very small (even briefly negative from massive buybacks). This is mathematically correct but misleading without context.

**Fix:** When ROE > 100% or < -100%, show the value but add a note: "Elevated due to low/negative equity from share buybacks" or similar context. The Ratios tab should explain extreme values rather than just showing a number that looks wrong.

**Files touched:**
- `backend/providers/yahoo_finance.py` — audit all returned values, add normalization
- `backend/services/market_data_service.py` — add normalization on cache write
- `backend/services/data_extraction_service.py` — audit all computed metrics, add ratio validation
- `backend/repositories/market_data_repo.py` — optional: add normalization on upsert
- `frontend/src/pages/Research/Profile/KeyStatsCard.tsx` — verify formatting
- `frontend/src/pages/Research/Ratios/RatioPanel.tsx` — add extreme value handling
- `frontend/src/pages/Portfolio/Performance/ReturnMetrics.tsx` — verify formatting
- `frontend/src/pages/Dashboard/MarketOverview/MarketOverviewWidget.tsx` — verify day_change_pct

**Note:** This overlaps with Phase 10C (live data fix) which also addresses `day_change_pct`. The two plans should be coordinated — ideally this normalization audit runs first as a single comprehensive pass, and 10C's specific fixes become part of it.

---

## AREA 2: PROFILE ENHANCEMENTS

### 2A. Missing Key Stats
**Current:** Key stats shows Market Cap, EV (from metrics), Shares Outstanding (from metrics), Avg Volume, 52W High/Low, Beta, Dividend Yield, P/E TTM, P/E Forward.

**Problem:** Enterprise Value and Shares Outstanding show "--" because `profile.metrics` may not have them. These values exist in `cache.market_data` (enterprise_value) and `cache.financial_data` (shares_outstanding) but may not be surfaced in the `metrics` dict from `CompanyService.get_company_with_metrics()`.

**Fix:** Ensure the profile endpoint includes `enterprise_value` and `shares_outstanding` from the market data and financial data caches. Add them to the `metrics` dict if not already present.

**Files touched:**
- `backend/services/company_service.py` — ensure enterprise_value and shares_outstanding included in metrics
- `frontend/src/pages/Research/Profile/KeyStatsCard.tsx` — verify they render (they're already in the template, just need data)

### 2B. 10-K Business Model & Segments
**Goal:** Show key business information extracted from 10-K filings on the Profile tab — specifically the Business Description (Item 1) and segment information.

**Implementation:**
- When the profile loads, check if we have a cached 10-K filing for this ticker
- If yes, pull the "Item 1" / "Business" section content
- Display a "Business Overview" card on the Profile tab below the company overview, showing:
  - A summarized version of the business description (first ~500 words or a key excerpt)
  - Identified business segments (if the 10-K has a "Segment Information" section)
  - Revenue breakdown by segment (if available in the filing text)
- If no 10-K filing is cached: show "No 10-K filing available. [Fetch Latest →]" with a button to trigger a fetch

**This is read-only display** — we're not parsing structured segment data, just surfacing the relevant text sections from cached filings in a readable format on the Profile page.

**Files touched:**
- `frontend/src/pages/Research/Profile/ProfileTab.tsx` — add BusinessOverview component
- `frontend/src/pages/Research/Profile/BusinessOverview.tsx` — new component
- `frontend/src/pages/Research/Profile/BusinessOverview.module.css` — new styles
- `backend/routers/research_router.py` — optional: add a `/profile/{ticker}/business-summary` endpoint that returns Item 1 text

---

## AREA 3: FILINGS — FETCH NEW FILINGS

### Current Problem
If you go to the Filings tab for a company and no filings are cached, it shows "No filings" with no way to trigger a fetch. The SEC EDGAR provider can fetch filings, but it's only triggered during certain backend flows (model building, research service initialization).

### Fix
Add a "Fetch Filings" button on the Filings tab that triggers a fresh fetch from SEC EDGAR:

**UI:**
```
[All] [10-K] [10-Q] [8-K]  [Compare]          [🔄 Fetch Latest Filings]
```

**Behavior:**
- Button visible when: no filings exist, OR the most recent filing is older than 90 days (likely stale)
- On click: POSTs to a new endpoint `/api/v1/research/{ticker}/filings/fetch`
- Backend: calls `SECEdgarProvider` to fetch the latest filings for the ticker, parse them, and cache in `filing_cache` + `filing_sections`
- Shows a loading state while fetching ("Fetching filings from SEC EDGAR...")
- On completion: refreshes the filing list
- If SEC EDGAR returns nothing: show "No filings found on SEC EDGAR for {ticker}. This may be a non-US company or a recently listed company."

**Backend:**
- New endpoint: `POST /api/v1/research/{ticker}/filings/fetch` — triggers EDGAR fetch + XBRL parsing
- Uses existing `SECEdgarProvider.get_filings()` and `XBRLService` for parsing
- Stores results in `filing_cache` and `filing_sections` tables

**Files touched:**
- `frontend/src/pages/Research/Filings/FilingsTab.tsx` — add Fetch button, loading state
- `frontend/src/pages/Research/Filings/FilingsTab.module.css` — button styles
- `backend/routers/research_router.py` — add filings fetch endpoint
- `backend/services/research_service.py` — add `fetch_filings()` method that coordinates SEC fetch + parse + cache

---

## AREA 4: PEERS — ACCURACY PASS

### Post-Normalization
After the Area 1 data normalization fix, the Peers tab metrics should automatically be correct since they pull from the same data pipeline. However, verify:
- P/E ratios are reasonable (not showing raw values)
- Revenue growth percentages are formatted correctly
- Operating margins make sense
- Day change percentages aren't showing the 85x multiplier bug

### Additional Fix
The Peers tab `day_change_pct` is surfaced from `research_service.get_peers()` which reads directly from `cache.market_data.day_change_pct`. After normalization (Area 1), this should be correct. Verify and test.

**Files touched:**
- `frontend/src/pages/Research/Peers/PeerTable.tsx` — verify metric formatting after normalization
- No dedicated session needed — this is a verification pass that happens alongside Area 1

---

## SESSION ORGANIZATION (Recommended for PM)

### Session 11A — Data Accuracy Normalization (Backend Critical)
**Scope:** Area 1 (full pipeline audit and fix)
**Files:**
- `backend/providers/yahoo_finance.py` — audit and normalize all returned values
- `backend/services/market_data_service.py` — normalization on cache write
- `backend/services/data_extraction_service.py` — audit all computed metrics
- `backend/repositories/market_data_repo.py` — optional normalization on upsert
**Complexity:** High (requires tracing every numerical field through 4 layers, identifying mismatches, fixing without breaking other consumers)
**Estimated acceptance criteria:** 20–25
**Priority:** CRITICAL — coordinate with Phase 10C (live data fix). Can potentially be merged into 10C as one comprehensive data integrity session.
**Coordination:** Session 10C (Live Data Fix) addresses the same root cause for `day_change_pct` specifically, plus adds startup refresh and WebSocket fixes. PM should either: (a) merge 11A and 10C into one comprehensive "Data Integrity" session, or (b) run 11A first as the full normalization audit, then 10C adds the live refresh / startup / WebSocket layer on top. Do NOT run them independently without coordination — they modify the same files (`yahoo_finance.py`, `market_data_service.py`, `data_extraction_service.py`).

### Session 11B — Profile + Filings + Frontend Accuracy Verification (Mixed)
**Scope:** Areas 1C–1D (frontend verification), 2 (profile enhancements), 3 (filing fetch), 4 (peers accuracy pass)
**Files:**
- `KeyStatsCard.tsx` — formatting verification, ensure EV + shares show
- `RatioPanel.tsx` — extreme value handling
- `ProfileTab.tsx` — add BusinessOverview component
- `BusinessOverview.tsx` — new component
- `BusinessOverview.module.css` — new styles
- `FilingsTab.tsx` — Fetch button
- `PeerTable.tsx` — accuracy verification
- `backend/services/company_service.py` — ensure EV + shares in metrics
- `backend/routers/research_router.py` — filings fetch endpoint, optional business-summary endpoint
- `backend/services/research_service.py` — fetch_filings method
**Complexity:** Medium (profile enhancements are straightforward, filings fetch uses existing infrastructure)
**Estimated acceptance criteria:** 15–20
**Depends on:** Session 11A (normalization must be done before frontend verification makes sense)

### Session 11C — Trend Chart Upgrade + DuPont Fix (Frontend Only)
**Scope:** Area 5 (5A, 5B)
**Files:**
- `RatioTrendChart.tsx` — full chart overhaul
- `RatioTrendChart.module.css` — metric selector redesign, chart sizing
- `ratioConfig.ts` — category grouping for selector
- `DuPontDecomposition.tsx` — context notes, color coding, sparklines
- `DuPontDecomposition.module.css` — note styles, sparkline styles
**Complexity:** Medium-High (chart overhaul with dual Y-axis, DuPont context logic + sparklines)
**Estimated acceptance criteria:** 15–20
**Depends on:** Session 11A (data accuracy must be fixed for chart values to be meaningful)

### Session 11D — Stock Price Charts (Frontend Only)
**Scope:** Area 6 (6A, 6B)
**Files:**
- `frontend/src/pages/Research/PriceChart/PriceChart.tsx` — new component
- `frontend/src/pages/Research/PriceChart/PriceChart.module.css` — new styles
- `frontend/src/pages/Research/ResearchPage.tsx` — add chart between header and tabs
- `frontend/src/pages/Research/ResearchPage.module.css` — chart area styles
**Complexity:** Medium-High (interactive price chart with period selector, line/candlestick toggle, volume bars, moving averages, crosshair)
**Estimated acceptance criteria:** 18–22
**Note:** Backend already has the `/companies/{ticker}/historical` endpoint. No backend changes needed.

---

## AREA 5: RATIOS TAB — TREND CHART UPGRADE + DUPONT FIX

### 5A. Trend Chart Fidelity Upgrade

**Current problems:**
- Chart is bare-bones Recharts LineChart with minimal styling
- Metric toggle buttons are just a row of small buttons that are hard to scan
- No annotations, no reference lines, no period highlighting
- Y-axis formatting is inconsistent (mixes % and x depending on first selected metric)
- Tooltip is basic — just value and label
- Chart height is fixed at 300px regardless of how many metrics are selected

**Changes:**
- **Larger chart:** Increase to 400px+ height. Chart should feel like the focal point of the Ratios tab, not a secondary element.
- **Better metric selector:** Group toggle buttons by category with small category labels (Profitability | Returns | Leverage | etc.). Use pill-style toggles with the line color shown as a dot next to each active metric.
- **Richer tooltip:** On hover, show a vertical crosshair with a card displaying all selected metric values at that year, formatted properly. Include YoY change for each metric.
- **Reference annotations:** Option to show industry median as a dashed horizontal line for the primary selected metric. Data available from the sector benchmarks already in `constants.py`.
- **Period highlights:** Subtle shaded bands for recession years or notable periods (optional, can be a future enhancement).
- **Y-axis improvement:** When mixing % and ratio metrics, use dual Y-axes (left for %, right for x) so both scales are visible.
- **Data point markers:** Show dots on each data point (currently `dot={false}`). On hover, highlight the specific point.
- **Chart title:** Dynamic title showing what's selected: "Margin Trends (10Y)" or "Returns vs Leverage (10Y)".

**Files touched:**
- `frontend/src/pages/Research/Ratios/RatioTrendChart.tsx` — full chart overhaul
- `frontend/src/pages/Research/Ratios/RatioTrendChart.module.css` — metric selector redesign, chart sizing
- `frontend/src/pages/Research/Ratios/ratioConfig.ts` — add category grouping info for the selector UI

### 5B. DuPont ROE Context Fix

**Current problem:**
DuPont shows ROE = Net Margin × Asset Turnover × Equity Multiplier. For Apple:
- Net Margin: ~26%
- Asset Turnover: ~1.1x
- Equity Multiplier: ~5.5x (because equity is tiny from buybacks)
- ROE: ~157% — mathematically correct but alarming without context

**Changes:**
- When Equity Multiplier > 4x OR stockholders_equity is negative: show a contextual note below the DuPont formula:
  > "Elevated ROE driven by high financial leverage. {ticker}'s equity base is reduced by significant share buybacks, amplifying the equity multiplier. This is common for mature companies with aggressive buyback programs."
- Color-code the equity multiplier: green < 2x, yellow 2-4x, red > 4x (to signal leverage risk)
- Add a small historical sparkline for each DuPont component (3-5 year trend) so the user can see if the leverage is increasing or stable
- If stockholders_equity is negative: show "Negative Equity" badge and note that traditional ROE is not meaningful in this case

**Files touched:**
- `frontend/src/pages/Research/Ratios/DuPontDecomposition.tsx` — context notes, color coding, sparklines
- `frontend/src/pages/Research/Ratios/DuPontDecomposition.module.css` — note styles, sparkline styles

---

## AREA 6: STOCK PRICE CHARTS

### Goal
Add interactive stock price charts to the Research page, making it a proper research hub where you can see price action alongside fundamentals. Currently Research has no price visualization at all — just the ticker header bar with a single current price number.

### Implementation

#### 6A. Price Chart Component
New component: `PriceChart.tsx` — an interactive candlestick or line chart showing historical price data.

**Features:**
- **Period selector:** 1D, 5D, 1M, 3M, 6M, YTD, 1Y, 5Y, MAX
- **Chart type toggle:** Line chart (default) or Candlestick (OHLC)
- **Volume bars:** Below the price chart, show volume bars (standard finance chart layout)
- **Interactive:** Crosshair on hover showing date, open, high, low, close, volume at that point
- **Moving averages:** Toggle overlays for 50-day and 200-day simple moving averages
- **Current price reference line:** Horizontal dashed line at current price

**Data source:** Backend already has `/api/v1/companies/{ticker}/historical?period=1y` which returns OHLCV bars from Yahoo Finance via `MarketDataService.get_historical()`. Just need to call it with different period parameters.

#### 6B. Placement
The price chart should be prominent — not buried in a sub-tab. Two options:

**Option A (Recommended):** Add it to the Research page directly, between the TickerHeaderBar and the sub-tabs. It's always visible for whichever ticker is loaded, serving as a visual anchor. Collapsible so it doesn't dominate when you're focused on filings or ratios.

**Option B:** Add it as a new "Charts" sub-tab in Research (6th tab alongside Filings, Financials, Ratios, Profile, Peers).

Recommend Option A because price context is valuable regardless of which sub-tab you're on.

#### 6C. Additional Chart Overlays (Future)
Note for future enhancement (not in this session):
- Earnings dates marked on the price chart
- Dividend ex-dates marked
- Model implied price as a horizontal band (from Model Builder results)
- Volume profile

**Files touched:**
- `frontend/src/pages/Research/PriceChart/PriceChart.tsx` — new component
- `frontend/src/pages/Research/PriceChart/PriceChart.module.css` — new styles
- `frontend/src/pages/Research/ResearchPage.tsx` — add PriceChart between header and tabs (collapsible)
- `frontend/src/pages/Research/ResearchPage.module.css` — chart area styles

---

## DEPENDENCIES & RISKS

| Risk | Mitigation |
|------|------------|
| Normalization fix breaks values that were already correct | Audit before changing — log current values for a test set of tickers, compare before/after normalization |
| Yahoo Finance returns different formats for different tickers or over time | Add defensive normalization: if a "ratio" field has value > 1.0 and is supposed to be a margin, it's probably already a percentage — divide by 100 |
| ROE context note for negative-equity companies seems like an edge case | Apple, Home Depot, McDonald's, Starbucks all have negative equity — it's common for large buyback companies. Worth handling properly. |
| SEC EDGAR fetch may be slow (10+ seconds for parsing a full 10-K) | Show progress indicator, fetch asynchronously, cache result for future |
| Business overview text from 10-K may be very long | Cap at first 500 words with "Read full filing →" link to the Filings tab |
| Candlestick chart adds complexity vs simple line chart | Default to line chart; candlestick is a toggle. Use Recharts custom shapes or lightweight candlestick library |
| Dual Y-axis on trend chart can confuse users | Only enable dual axis when both % and ratio metrics are selected; label axes clearly |
| DuPont sparklines require historical financial data per component | Already available from `/research/{ticker}/financials` — just need last 5 years of net_margin, asset_turnover, equity_multiplier |

---

## DECISIONS MADE

1. Canonical format: all ratios/percentages stored as decimal ratios (0.15 = 15%) throughout the pipeline
2. Frontend `fmtPct()` always multiplies by 100 — no exceptions
3. Normalization happens at the storage layer (provider → cache) not at display time
4. Extreme values (ROE >100%) get contextual notes, not hidden
5. Shares outstanding and enterprise value added to Profile key stats
6. 10-K business description shown on Profile as a read-only text card
7. "Fetch Filings" button on Filings tab triggers SEC EDGAR fetch on demand
8. Data accuracy audit should be coordinated with Phase 10C live data fix — potentially merged into one session
9. Peers accuracy is a verification pass after normalization, not a separate session
10. Trend chart gets Fidelity upgrade: larger, categorized metric selector, dual Y-axis, richer tooltip with YoY change
11. DuPont decomposition shows contextual notes for extreme equity multiplier / negative equity
12. Stock price chart placed between TickerHeaderBar and sub-tabs on Research page (collapsible)
13. Price chart: line (default) + candlestick toggle, period selector, volume bars, 50/200 MA overlays
14. Price chart uses existing `/companies/{ticker}/historical` endpoint — no backend changes needed

---

*End of Research Update Plan*
*Phase 11A–11D · Prepared March 5, 2026*
