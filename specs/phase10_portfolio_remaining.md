# Finance App — Portfolio: Allocation, Income, Transactions, Alerts Update Plan
## Phase 10: Portfolio — Remaining Sub-Tabs

**Prepared by:** Planner (March 5, 2026)
**Recipient:** PM Agent
**Scope:** Portfolio → Allocation (unknown sector fix), Income (major upgrade), Transactions (CSV import link), Alerts (no changes)

---

## PLAN SUMMARY

Three workstreams (Alerts is unchanged):

1. **Allocation — Unknown Sector Fix** — Eliminate "Unknown" classifications by ensuring all positions have company profile data; ETFs get proper classification
2. **Income — Major Upgrade** — Transform from basic dividend log into a useful income analysis tool with projections, yield-on-cost, dividend growth, and monthly calendar
3. **Transactions — CSV Import Access** — Add easy access to the transaction import flow from the Transactions tab

---

## AREA 1: ALLOCATION — UNKNOWN SECTOR FIX

### Current Problem
The Sector Donut and Treemap show most positions as "Unknown" sector. Root cause is the same as Holdings missing names — company profiles not auto-fetched on position add. This is already being fixed in session 10C (auto-fetch profiles on position create + backfill on startup).

### Additional Fix for ETFs
ETFs (like SPY, QQQ, VTI) don't have a "sector" in the traditional sense — Yahoo Finance returns sector as empty or "Financial Services" for ETF tickers. These need special handling:

- Detect ETF positions (Yahoo Finance `quoteType` field returns `"ETF"` for ETFs)
- Classify ETFs separately: show as "ETF" in the sector donut instead of lumping them into a wrong sector
- For the Treemap: ETFs appear as their own group
- Optional future enhancement: break ETFs into their underlying sector exposure (would require ETF holdings data, out of scope for now but noted)

### Changes
- Backend: when fetching company profile for an ETF ticker, set sector to "ETF" and industry to the ETF's category (e.g., "Large Blend", "Technology Select")
- Frontend: Allocation visualizations handle "ETF" as a valid sector with its own color in the donut

**Files touched:**
- `backend/services/company_service.py` — detect ETF quoteType, set sector appropriately
- `backend/providers/yahoo_finance.py` — include quoteType in company info response
- `frontend/src/pages/Portfolio/Allocation/SectorDonut.tsx` — add "ETF" color, handle gracefully
- `frontend/src/pages/Portfolio/Allocation/Treemap.tsx` — ETF grouping

---

## AREA 2: INCOME — MAJOR UPGRADE

### Current State
- Summary: annual income, monthly income, weighted yield, YTD income
- Monthly bar chart of dividend income for current year
- Dividend history table (sortable)
- Placeholder: "Upcoming Dividend Events" says "Phase 5"

### Problems
- Not useful for growth stock holders (no dividends = empty tab)
- No forward-looking projections
- No yield-on-cost tracking
- No dividend growth analysis
- Upcoming events placeholder never connected to the events system
- "Yield on Cost" column in dividend history shows "--" for every row

### New Income Tab Design

#### 2A. Income Summary Header (Enhanced)
Keep existing metrics, add:
- **Projected Annual Income** — based on current holdings × current dividend rates, annualized
- **Yield on Cost (Portfolio)** — total annual dividends / total cost basis
- **Yield on Market (Portfolio)** — total annual dividends / total market value (this is the existing weighted yield)
- **Income Growth YoY** — compare this year's income to last year's (if data available)

#### 2B. Monthly Income Calendar
Replace the basic monthly bar chart with a richer view:
- **Monthly bar chart** stays but improves: show stacked bars by ticker (so you can see which stocks contribute to each month's income)
- **Below the chart:** a month-by-month breakdown table:
  ```
  January     $142.50    AAPL ($52.00), JNJ ($45.50), KO ($45.00)
  February    $87.00     MSFT ($87.00)
  March       $142.50    AAPL ($52.00), JNJ ($45.50), KO ($45.00)
  ...
  ```
- This tells you which months are light and which are heavy — useful for income planning

#### 2C. Yield-on-Cost per Position
The income positions table currently shows: ticker, shares, dividend rate, yield, annual income, monthly income. Add:
- **Cost Basis** column
- **Yield on Cost** column — `dividend_rate / cost_basis_per_share` (this is the actual yield you locked in based on your purchase price, not today's market yield)
- **Dividend Growth (5Y)** — if historical dividend data is available from Yahoo Finance, show the 5-year dividend CAGR per position
- Sort by yield-on-cost to find your best income positions

**Backend:** Yield-on-cost requires joining income data with position cost basis data. The income endpoint needs to include cost basis per position. Dividend growth requires historical dividend data from Yahoo Finance (available via `Ticker.dividends` in yfinance).

#### 2D. Upcoming Dividend Events (Connect to Events System)
Replace the placeholder with real data from the events system built in Phase 7:
- Show upcoming ex-dividend dates for positions in the portfolio
- Pulls from the same `company_events` cache used by the Dashboard Upcoming Events widget
- Filter to `event_type = 'ex_dividend'` and `ticker IN (portfolio tickers)`
- Show: date, ticker, expected amount per share, shares held, expected income

**This is a lightweight integration** — the events backend already exists from Phase 7. Just need a frontend component that fetches filtered events.

#### 2E. For Non-Dividend Portfolios
If the portfolio has no dividend-paying positions:
- Show a meaningful empty state: "No dividend income from current holdings"
- Show the portfolio's total return comparison instead: "Your portfolio generates returns through capital appreciation"
- Optionally suggest: "Consider adding dividend-paying positions for income diversification"
- Don't make the tab feel broken — it should feel intentional that this portfolio is growth-focused

**Files touched:**
- `frontend/src/pages/Portfolio/Income/IncomeTab.tsx` — enhanced summary, calendar, yield-on-cost, events integration, non-dividend empty state
- `frontend/src/pages/Portfolio/Income/IncomeTab.module.css` — new section styles
- `frontend/src/pages/Portfolio/Income/DividendChart.tsx` — stacked bars by ticker
- `frontend/src/pages/Portfolio/Income/DividendChart.module.css` — stacked bar styles
- `frontend/src/pages/Portfolio/Income/DividendCalendar.tsx` — new component (monthly breakdown table)
- `frontend/src/pages/Portfolio/Income/DividendCalendar.module.css` — new styles
- `frontend/src/pages/Portfolio/Income/UpcomingDividends.tsx` — new component (replaces placeholder)
- `frontend/src/pages/Portfolio/Income/UpcomingDividends.module.css` — new styles
- `backend/routers/portfolio_router.py` — update income endpoint to include cost basis, dividend growth
- `backend/services/portfolio/income_service.py` — new or extended service for yield-on-cost, dividend growth calc
- `backend/providers/yahoo_finance.py` — add method to fetch historical dividend data per ticker

---

## AREA 3: TRANSACTIONS — CSV IMPORT ACCESS

### Current State
The Transactions tab has a "Record Transaction" button but no way to import transactions from CSV. The Import CSV button is only on the main Portfolio header and currently only imports positions (not transactions). Session 10A adds transaction import mode to the ImportModal.

### Change
Add an "Import Transactions" button to the Transactions tab header, next to "Record Transaction":

```
Transactions    [+ Record Transaction]  [📥 Import Transactions]
```

Clicking "Import Transactions" opens the same ImportModal from Holdings but pre-selects "Transactions" as the import type (skipping the position/transaction selector in step 1).

**Files touched:**
- `frontend/src/pages/Portfolio/Transactions/TransactionsTab.tsx` — add Import button, open ImportModal with transaction mode pre-selected
- `frontend/src/pages/Portfolio/Holdings/ImportModal.tsx` — accept optional `defaultImportType` prop to pre-select mode

---

## SESSION ORGANIZATION (Recommended for PM)

### Session 10E — Income Backend + Allocation ETF Fix (Backend Only)
**Scope:** Areas 1 backend, 2 backend (2A, 2C, 2D backend)
**Files:**
- `backend/services/company_service.py` — ETF detection and classification
- `backend/providers/yahoo_finance.py` — quoteType in company info, historical dividend data method
- `backend/routers/portfolio_router.py` — update income endpoint
- `backend/services/portfolio/income_service.py` — yield-on-cost, dividend growth calculations
**Complexity:** Medium (ETF detection is straightforward, dividend growth requires new Yahoo data fetch)
**Estimated acceptance criteria:** 12–15

### Session 10F — Income + Allocation + Transactions Frontend (Frontend Only)
**Scope:** Areas 1 frontend, 2 frontend (2A–2E), 3
**Files:**
- `SectorDonut.tsx` — ETF color handling
- `Treemap.tsx` — ETF grouping
- `IncomeTab.tsx` — enhanced summary, yield-on-cost table, non-dividend empty state
- `IncomeTab.module.css` — new styles
- `DividendChart.tsx` — stacked bars
- `DividendCalendar.tsx` — new component
- `UpcomingDividends.tsx` — new component (events integration)
- `TransactionsTab.tsx` — Import button
- `ImportModal.tsx` — accept defaultImportType prop
**Complexity:** Medium-High (new components, stacked chart, events integration)
**Estimated acceptance criteria:** 20–25
**Depends on:** Session 10E (backend income data), Phase 7 events backend (for upcoming dividends)

---

## DEPENDENCIES & RISKS

| Risk | Mitigation |
|------|------------|
| ETF sector classification varies across providers | Use quoteType as primary detector; fallback: if sector is empty or "Financial Services" and the ticker matches known ETF patterns (3-4 letter uppercase, no dots), classify as ETF |
| Historical dividend data not available for all tickers | Show "N/A" for dividend growth when data is missing; don't block the rest of the income tab |
| Stacked bar chart with many tickers becomes unreadable | Cap at top 8 tickers by income contribution; group rest as "Other" |
| Yield-on-cost calculation incorrect for positions with multiple lots at different prices | Use weighted average cost basis across all lots (already computed in position data) |
| Upcoming dividends integration depends on Phase 7 events backend | The events service and cache already exist from Phase 7. If Phase 7 hasn't been built yet, show the placeholder with "Enable events to see upcoming dividends" |

---

## DECISIONS MADE

1. ETFs classified as sector "ETF" with industry set to ETF category
2. Allocation donut/treemap get distinct "ETF" color and grouping
3. Income tab gets: projected income, yield-on-cost per position, dividend growth (5Y CAGR), monthly calendar breakdown, upcoming dividend events
4. Monthly bar chart becomes stacked by ticker (top 8 + "Other")
5. Non-dividend portfolios get a meaningful empty state, not a broken-looking tab
6. Yield-on-cost uses weighted average cost basis across lots
7. Upcoming dividends pulls from Phase 7 events cache (ex_dividend events for portfolio tickers)
8. Transaction import accessible from Transactions tab via pre-configured ImportModal
9. Alerts tab: no changes needed

---

*End of Portfolio — Allocation, Income, Transactions, Alerts Update Plan*
*Phase 10E–10F · Prepared March 5, 2026*
