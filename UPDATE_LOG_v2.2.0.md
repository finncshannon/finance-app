# Update Log — Spectre v2.2.0

**Status:** Ready for Testing
**Branch:** main
**Started:** 2026-03-09

---

## Changes

### 1. Fix title boost double-counting in news classifier
**Files:** `backend/services/news_service.py`
**Type:** fix
**Description:** Title keywords were scored at 3x (1x in full_text pass + 2x title boost) instead of the documented 2x. Refactored to score title and snippet separately — title at `TITLE_BOOST` weight, snippet at 1x — then merge. Also replaced `_score_all` two-ruleset function with simpler `_score_text` single-ruleset function. Fixed `max()` type warning by using explicit lambda instead of `dict.get`.

### 2. Fix `\b` word boundary failure on trailing punctuation
**Files:** `backend/services/news_service.py`
**Type:** fix
**Description:** Keywords ending in non-word characters (e.g. `u.s.`, `u.s.a.`, `opec+`) caused `\b` at the end of the pattern to fail when followed by whitespace. `_build_pattern` now detects trailing non-alphanumeric characters and uses a `(?=\s|$)` lookahead instead of `\b`.

### 3. Fix `who` false positive in Healthcare keywords
**Files:** `backend/services/news_service.py`
**Type:** fix
**Description:** `"who"` (weight 1.0) matched the English pronoun "who" in virtually every article, inflating Healthcare scores universally. Replaced with `"world health organization"` (weight 3.0) which is unambiguous and high-signal.

### 4. Remove noisy low-weight keywords causing misclassifications
**Files:** `backend/services/news_service.py`
**Type:** fix
**Description:** Removed 16 keywords with weight 1.0 that were too generic and caused false category matches: `app`, `platform`, `fab`, `digital` (Technology); `listing` (Markets); `final`, `season` (Sports); `stores`, `shopping`, `target`, `production`, `supply`, `demand`, `stamps` (Economy); `primary` (Politics); `series`, `fame`, `band`, `gallery` (Entertainment). Reduced `shell` from 1.5→1.0 (Energy, ambiguous noun). Changed `bp` (1.5) to `bp plc` (2.0) to avoid matching the abbreviation in other contexts.

### 5. Increase Python import check timeout from 10s to 30s
**Files:** `electron/main.ts`
**Type:** fix
**Description:** The `execSync` call that verifies critical Python imports (fastapi, uvicorn, aiosqlite) had a 10-second timeout, which can be exceeded on cold starts (antivirus scanning, disk cache misses). Bumped to 30 seconds to match the backend startup timeout.

### 6. Pre-load S&P 500 and Russell 3000 universes before frontend connects
**Files:** `backend/main.py`
**Type:** fix
**Description:** `load_all_curated()` (DOW, S&P 500, Russell 3000) was running inside a background task alongside the slow hydration process, causing a race condition where the frontend could connect before the companies table was populated. Moved the curated universe load to the synchronous startup sequence so all ~3,000 tickers are in the database before the health check passes. Background hydration (market data fetch) remains async.

### 7. Fix dividend yield showing 40%+ due to Yahoo percentage format
**Files:** `backend/providers/yahoo_finance.py`, `backend/services/market_data_service.py`
**Type:** fix
**Description:** Yahoo Finance's `dividendYield` field is always in percentage format (0.4 = 0.4%, 2.72 = 2.72%), but the old normalization only divided by 100 when > 1.0 — so yields under 1% (like AAPL's 0.4%) were stored as-is and displayed 100x too high (e.g., 40% instead of 0.4%). Fixed at the provider level: now uses `trailingAnnualDividendYield` (already decimal) as primary source, falls back to `dividendYield / 100`. Removed the broken conditional normalization from market_data_service.

### 8. SEC EDGAR email enforcement (dynamic User-Agent)
**Files:** `backend/providers/sec_edgar.py`, `backend/main.py`, `backend/routers/research_router.py`, `backend/routers/companies_router.py`, `frontend/src/pages/Settings/sections/DataSourcesSection.tsx`, `frontend/src/pages/Research/Filings/FilingsTab.tsx`
**Type:** enhancement
**Description:** SEC EDGAR User-Agent is now built dynamically from the email configured in Settings (format: `Spectre <email>`). Removed hardcoded email. Added `SECEdgarEmailNotConfigured` exception that blocks requests when no email is set. Frontend shows a warning banner in the Filings tab and validates email format in Settings. All SEC-facing endpoints return `SEC_EMAIL_REQUIRED` error code when email is missing.

### 9. Fix SEC EDGAR "undeclared automated tool" blocking
**Files:** `backend/providers/sec_edgar.py`
**Type:** fix
**Description:** SEC was blocking requests due to missing `Host` header and incorrect User-Agent format (had version slash). Fixed: added per-request `Host` header matching the target domain, changed UA from `Spectre/2.1.0 email` to `Spectre email`. Added `_is_sec_blocked()` detection for SEC's block page (returns HTTP 200 with error HTML). Added 429 retry with backoff and fresh request headers.

### 10. Fix 10-Q filing parser returning 0 sections
**Files:** `backend/providers/sec_edgar.py`
**Type:** fix
**Description:** The `parse_10k_sections` method couldn't match 10-Q section headers because they use HTML entities (`&#160;`) instead of regular spaces. Added entity normalization before pattern matching and extended section patterns to cover 10-Q items (Financial Statements, MD&A, Controls and Procedures). Parser now finds 5 sections for both 10-K and 10-Q filings.

### 11. Add backend logging configuration
**Files:** `backend/main.py`
**Type:** enhancement
**Description:** The `finance_app` logger had no handler configured — all `logger.info()` calls were silently dropped. Added `logging.basicConfig()` with stderr output so backend log messages are visible through Electron's process pipes.

### 12. Research search autocomplete with ticker and company name
**Files:** `frontend/src/pages/Research/TickerSearch.tsx`, `frontend/src/pages/Research/TickerSearch.module.css`, `frontend/src/pages/Research/ResearchPage.tsx`, `backend/repositories/company_repo.py`
**Type:** enhancement
**Description:** Replaced the manual ticker-only input with a live autocomplete search. Suggestions appear after the first keystroke, matching both ticker symbols and full company names. Dropdown shows ticker in blue with the company name beside it. Supports keyboard navigation (arrow keys + Enter), 150ms debounce, and outside-click dismiss. Backend search improved to prioritize exact ticker matches, then ticker prefix, then name matches, returning only the fields needed (ticker, company_name, exchange).

### 13. Fix Portfolio hover card not populating and disappearing on mouse move
**Files:** `frontend/src/pages/Portfolio/Holdings/CompanyInfoCard.tsx`, `frontend/src/pages/Portfolio/Holdings/CompanyInfoCard.module.css`, `frontend/src/pages/Portfolio/Holdings/HoldingsTable.tsx`
**Type:** fix
**Description:** The ticker hover popup in Holdings was broken in two ways: (1) it fetched from a non-existent API endpoint, returning no data, and (2) the card disappeared immediately when moving the mouse toward it because `handleTickerMouseLeave` unconditionally destroyed it after 200ms. Fixed the API calls to use `/api/v1/companies/{ticker}` and `/api/v1/companies/{ticker}/quote` in parallel. Added coordinated hover timing — `HoldingsTable` now uses a cancellable close timer (`hoverCloseRef`) that gets cleared when the mouse enters the card via `onMouseEnterCard`. Card also shows current price with day change percentage and has its own internal mouse leave timer for smooth dismissal.

### 14. Add 1Y price change to Portfolio hover card
**Files:** `frontend/src/pages/Portfolio/Holdings/CompanyInfoCard.tsx`
**Type:** enhancement
**Description:** Added 1-year price change percentage to the hover card metric grid (after Div Yield, before Beta). Fetches 1Y daily historical bars and computes the return internally from first and last close prices in the series, avoiding cross-source mismatches between live quote and historical data.

### 15. Overhaul CSV transaction import parser
**Files:** `backend/services/portfolio/csv_import.py`, `frontend/src/pages/Portfolio/Holdings/ImportModal.tsx`, `.gitignore`
**Type:** fix + enhancement
**Description:** The CSV import parser failed on Fidelity transaction exports due to multiple issues: BOM character (`\ufeff`) at file start broke header detection, two leading blank lines skipped the header row, column names with unit suffixes like `Price ($)` and `Commission ($)` didn't match aliases, `Run Date` wasn't recognized as a date column, and trailing Fidelity disclaimer text created garbage rows. Fixed by adding: BOM stripping, leading blank line removal, trailing footer trimming, header normalization that strips `($)`/`(%)` suffixes before matching, `run date` to date aliases, and expanded transaction type inference (`YOU BOUGHT`/`YOU SOLD`, `REINVEST`, `DISTRIBUTION`). Improved error messages to show which columns matched vs didn't. Frontend manual column mapping now shows transaction-specific fields (Date, Action, Price, Fees) instead of position-only fields when importing transactions. Added `*.csv` to `.gitignore` to exclude user data files.

### 16. Add "Clear All" positions button
**Files:** `backend/repositories/portfolio_repo.py`, `backend/services/portfolio/portfolio_service.py`, `backend/routers/portfolio_router.py`, `frontend/src/pages/Portfolio/PortfolioPage.tsx`, `frontend/src/pages/Portfolio/PortfolioPage.module.css`
**Type:** enhancement
**Description:** Added a "Clear All" button to the Holdings toolbar that deletes all portfolio positions in one action. Requires confirmation dialog before executing. Button styled with red border, turns solid red on hover, and only appears when positions exist. Backend adds `DELETE /api/v1/portfolio/positions` endpoint with cascading lot deletion.

### 17. Add row removal to import preview
**Files:** `frontend/src/pages/Portfolio/Holdings/ImportModal.tsx`, `frontend/src/pages/Portfolio/Holdings/ImportModal.module.css`
**Type:** enhancement
**Description:** Added an X button on the left of each row in the import preview (step 3) for both positions and transactions. Allows users to remove individual rows before executing the import. Button is subtle by default, turns red on hover.

---

## Version Bump Checklist
- [ ] All `package.json` versions updated
- [ ] TypeScript compiles clean
- [ ] App runs without errors
- [ ] Packaged build succeeds
- [ ] Git commit + push
- [ ] GitHub Release created
