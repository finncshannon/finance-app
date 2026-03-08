# Phase 6 — Integration & Consistency Review
> Designer Agent | February 26, 2026
> Status: COMPLETE
> Covers: Cross-spec audit of all 15 specification documents

---

## Overview

This document audits all specification files for internal consistency,
identifies gaps, conflicts, and missing connections, and provides
specific amendments. Each issue is categorized and resolved.

---

## Part 1: Issues Found & Resolutions

### ISSUE 1: Database Schema Missing Tables Required by Later Specs

**Severity: HIGH**

Phase 0B defines 17 tables. Later specs reference data structures that
need additional tables or columns.

**Missing tables:**

1. **watchlist_items** — Phase 0B stores watchlist tickers as a JSON array
   in the `watchlists` table (`tickers_json`). Phase 5 (Dashboard) specifies
   multiple watchlists with per-ticker column configuration, ordering, and
   the ability to add/remove from any module via right-click. JSON arrays
   make this cumbersome. Need a proper join table.

   ```sql
   CREATE TABLE watchlist_items (
       id              INTEGER PRIMARY KEY AUTOINCREMENT,
       watchlist_id    INTEGER NOT NULL,       -- FK → watchlists
       ticker          TEXT NOT NULL,           -- FK → companies
       sort_order      INTEGER DEFAULT 0,
       added_at        TEXT NOT NULL,
       UNIQUE(watchlist_id, ticker),
       FOREIGN KEY (watchlist_id) REFERENCES watchlists(id) ON DELETE CASCADE
   );
   ```

   **Amendment:** Replace `tickers_json` in watchlists table with this join table.
   Remove `tickers_json` column from watchlists.

2. **portfolio_lots** — Phase 3 (Portfolio) specifies lot-level tracking with
   individual purchase dates, cost bases, and holding period classification.
   Phase 0B's `portfolio_positions` table only has one row per ticker per
   account. Need a lots table.

   ```sql
   CREATE TABLE portfolio_lots (
       id                  INTEGER PRIMARY KEY AUTOINCREMENT,
       position_id         INTEGER NOT NULL,       -- FK → portfolio_positions
       shares              REAL NOT NULL,
       cost_basis_per_share REAL NOT NULL,
       date_acquired       TEXT NOT NULL,           -- ISO date
       date_sold           TEXT,                    -- ISO date, null if held
       sale_price          REAL,
       realized_gain       REAL,
       lot_method          TEXT DEFAULT 'fifo',     -- "fifo", "lifo", "specific", etc.
       notes               TEXT,
       FOREIGN KEY (position_id) REFERENCES portfolio_positions(id) ON DELETE CASCADE
   );
   ```

   **Amendment:** `portfolio_positions` becomes the aggregate per-ticker-per-account
   record. `portfolio_lots` tracks individual purchases. `shares_held` and
   `cost_basis_per_share` in positions are computed from lots.

3. **portfolio_accounts** — Phase 3 specifies multi-account support with
   tax status per account. Need a dedicated accounts table.

   ```sql
   CREATE TABLE portfolio_accounts (
       id              INTEGER PRIMARY KEY AUTOINCREMENT,
       name            TEXT NOT NULL UNIQUE,       -- "Fidelity IRA"
       account_type    TEXT DEFAULT 'taxable',     -- "taxable", "traditional_ira", "roth_ira", "401k"
       is_default      INTEGER DEFAULT 0,
       created_at      TEXT NOT NULL
   );
   ```

   **Amendment:** `portfolio_positions.account` changes from free-text to
   `account_id INTEGER` referencing this table.

4. **filing_sections** — Phase 4 (Research) specifies a parsed section viewer
   where each 10-K section (Item 1, Item 1A, Item 7, etc.) is individually
   navigable and searchable. Phase 0B's `filing_cache` stores `sections_json`
   as a list of section names, but the actual parsed text needs a proper table.

   ```sql
   CREATE TABLE filing_sections (
       id              INTEGER PRIMARY KEY AUTOINCREMENT,
       filing_id       INTEGER NOT NULL,           -- FK → filing_cache
       section_key     TEXT NOT NULL,              -- "item1", "item1a", "item7", etc.
       section_title   TEXT NOT NULL,              -- "Business", "Risk Factors", etc.
       content_text    TEXT NOT NULL,              -- Full parsed text of this section
       word_count      INTEGER,
       FOREIGN KEY (filing_id) REFERENCES filing_cache(id) ON DELETE CASCADE
   );

   CREATE INDEX idx_filing_sections_filing ON filing_sections(filing_id);
   CREATE INDEX idx_filing_sections_search ON filing_sections(content_text);
   ```

   **Amendment:** `filing_cache.sections_json` becomes a reference to enumerate
   available sections. Actual content moves to `filing_sections` table in
   market_cache.db. This also supports the Scanner's full-text filing search.

5. **earnings_calendar / dividend_calendar** — Phase 5 (Dashboard) references
   these as data sources for the Upcoming Events widget. Phase 3 (Portfolio)
   also references them for the earnings & dividend calendar.

   ```sql
   CREATE TABLE company_events (
       id              INTEGER PRIMARY KEY AUTOINCREMENT,
       ticker          TEXT NOT NULL,
       event_type      TEXT NOT NULL,              -- "earnings", "ex_dividend", "filing"
       event_date      TEXT NOT NULL,              -- ISO date
       event_time      TEXT,                       -- "before_market", "after_market", null
       description     TEXT,
       amount          REAL,                       -- dividend amount, if applicable
       is_estimated    INTEGER DEFAULT 0,          -- 1 if date is estimated
       source          TEXT DEFAULT 'yahoo',
       fetched_at      TEXT NOT NULL,
       UNIQUE(ticker, event_type, event_date)
   );

   CREATE INDEX idx_events_date ON company_events(event_date);
   CREATE INDEX idx_events_ticker ON company_events(ticker);
   ```

   **Amendment:** Single `company_events` table in market_cache.db replaces
   the implicit references to separate calendar tables.

6. **price_alerts** — Phase 3 (Portfolio) specifies price alerts.

   ```sql
   CREATE TABLE price_alerts (
       id              INTEGER PRIMARY KEY AUTOINCREMENT,
       ticker          TEXT NOT NULL,
       alert_type      TEXT NOT NULL,              -- "above", "below", "pct_change", "intrinsic_cross"
       threshold       REAL NOT NULL,
       is_active       INTEGER DEFAULT 1,
       triggered_at    TEXT,                        -- null if not yet triggered
       created_at      TEXT NOT NULL
   );
   ```

   **Amendment:** Add to user_data.db.

---

### ISSUE 2: Scanner Universe Mismatch

**Severity: MEDIUM**

Phase 0B database schema notes: "Total for 500 companies: ~5,500 rows."
Phase 0C API spec references `universe: "sp500" | "custom"`.
Phase 2 (Scanner) specifies Russell 3000 as the base universe.

**Resolution:**

- Update Phase 0B row count estimate: ~33,000 rows for 3,000 companies × 11 periods.
  Still very manageable for SQLite.
- Update Phase 0C scanner endpoint universe enum to: `"r3000" | "sp500" | "custom"`
- Update scanner_presets table: `universe TEXT DEFAULT 'r3000'` (was 'sp500')
- Add `universe_source` column to companies table (already in Phase 2 spec,
  needs to be added to Phase 0B schema definition)

---

### ISSUE 3: API Endpoints Missing for New Features

**Severity: MEDIUM**

Phase 0C defines 57 endpoints. Later specs require additional endpoints.

**Missing endpoints:**

```
Portfolio (Phase 3 additions):
  GET  /api/v1/portfolio/performance          — TWR, MWRR, Sharpe, etc.
  GET  /api/v1/portfolio/attribution          — Brinson sector attribution
  GET  /api/v1/portfolio/income               — Dividend income tracking
  GET  /api/v1/portfolio/lots/{position_id}   — Get lots for a position
  POST /api/v1/portfolio/import               — CSV import endpoint
  GET  /api/v1/portfolio/accounts             — List accounts
  POST /api/v1/portfolio/accounts             — Create account
  PUT  /api/v1/portfolio/accounts/{id}        — Update account
  DELETE /api/v1/portfolio/accounts/{id}      — Delete account
  GET  /api/v1/portfolio/alerts               — Get price alerts
  POST /api/v1/portfolio/alerts               — Create price alert
  DELETE /api/v1/portfolio/alerts/{id}        — Delete price alert

Research (Phase 4 additions):
  GET  /api/v1/research/{ticker}/ratios       — Full ratio dashboard data
  GET  /api/v1/research/{ticker}/segments     — Segment breakdown
  GET  /api/v1/research/{ticker}/peers        — Peer comparison table
  POST /api/v1/research/{ticker}/compare-filings — Filing diff comparison
  GET  /api/v1/research/{ticker}/profile      — Full company profile

Scanner (Phase 2 additions):
  GET  /api/v1/scanner/universe/stats         — Universe size, composition
  POST /api/v1/scanner/universe/add           — Add ticker(s) to universe
  DELETE /api/v1/scanner/universe/{ticker}    — Remove from universe
  POST /api/v1/scanner/rank                   — Composite ranking
  POST /api/v1/scanner/custom-filter          — Custom formula filter

Dashboard (Phase 5 additions):
  GET  /api/v1/dashboard/events               — Upcoming events (earnings, dividends)

Model Builder (Phase 1F additions):
  GET  /api/v1/model-builder/{ticker}/overview — Cross-model comparison data
  PUT  /api/v1/model-builder/{ticker}/weights  — Set model blending weights

System:
  POST /api/v1/system/backup                  — Trigger manual backup
  GET  /api/v1/system/backups                 — List available backups
  POST /api/v1/system/restore                 — Restore from backup
```

**Resolution:** These 30 additional endpoints bring the total to ~87.
The router-per-module architecture accommodates this without restructuring.
Each new endpoint follows the existing response envelope and error code patterns.

---

### ISSUE 4: Phase 0B Backup Strategy Inconsistency

**Severity: LOW**

Phase 0B specifies: "Retention: Keep last 7 daily backups"
Phase 0E specifies: "Retention: Last 30 daily backups"

**Resolution:** Phase 0E is the authoritative spec (written later, more detailed).
Use 30 daily backups. Amend Phase 0B.

---

### ISSUE 5: Companies Table Missing Fields

**Severity: LOW**

Phase 2 (Scanner) requires `universe_source` on companies table.
Phase 3 (Portfolio) references company data for portfolio analytics.
Phase 4 (Research) references `employees`, `segments`, `geographic_regions`.

The companies table in Phase 0B has most of these but is missing:

```sql
  universe_source     TEXT DEFAULT 'manual',   -- "r3000", "manual", "portfolio", "watchlist"
  gics_sector_code    TEXT,                    -- GICS numeric code for precise classification
  gics_industry_code  TEXT,
  fiscal_year_end     TEXT,                    -- "September", "December", etc.
```

**Resolution:** Add these columns to companies table definition.

---

### ISSUE 6: Portfolio Transactions Table Needs More Types

**Severity: LOW**

Phase 0B defines transaction_type as: "buy" / "sell" / "dividend" / "split"
Phase 3 specifies: BUY, SELL, DIVIDEND, DRIP, SPLIT, SPINOFF, TRANSFER, ADJUSTMENT

**Resolution:** Update Phase 0B transaction_type to match Phase 3's full list.
These are just TEXT values so no schema change needed, just documentation alignment.

---

### ISSUE 7: Styling Reference Inconsistency

**Severity: LOW**

Phase 0D defines the color system with CSS variable names.
Later specs occasionally reference colors inconsistently:

- Phase 1E uses `--color-warning` (yellow) — not defined in Phase 0D
- Phase 1B uses `--accent-subtle` — defined in Phase 0D ✓
- Phase 2 references `--bg-hover`, `--bg-active` — defined in Phase 0D ✓

**Resolution:** Add to Phase 0D color system:
```
--color-warning: #EAB308 (yellow-500, for cautionary indicators)
```
Already implicitly used across multiple specs. Making it explicit.

---

### ISSUE 8: Assumption Engine Data Package vs. Database Schema

**Severity: LOW**

Phase 1E's `CompanyDataPackage` references fields that need to come from
the database. Cross-checking against Phase 0B's financial_data wide table:

- `interestExpense` → `interest_expense` ✓
- `taxExpense` → `tax_provision` ✓ (naming mismatch but same field)
- `workingCapital` → `working_capital` ✓
- `capex` → `capital_expenditure` ✓

The package also references `sectorMedians` and `sectorPercentiles` which
are computed at query time from the financial_data table across all companies
in the same sector. No separate table needed — this is a runtime aggregation.

**Resolution:** No schema changes needed. Backend service layer computes
sector statistics on demand and caches them briefly (TTL: 1 hour).

---

## Part 2: Navigation Flow Verification

### Module Tab Bar

All specs consistently reference the top-level tab structure:

```
DASHBOARD │ MODEL BUILDER │ SCANNER │ PORTFOLIO │ RESEARCH │ SETTINGS
```

✅ Dashboard — Phase 5
✅ Model Builder — Phase 1A-1G
✅ Scanner — Phase 2
✅ Portfolio — Phase 3
✅ Research — Phase 4
✅ Settings — Referenced throughout (Phase 0E details contents)

### Sub-Tab Structures (verified per module)

```
Model Builder (per model type):
  DCF:          Overview │ Historical Data │ Assumptions │ DCF Model │ Sensitivity │ History
  DDM:          Overview │ Historical Data │ Dividend Analysis │ Assumptions │ DDM Model │ Sensitivity │ History
  Comps:        Overview │ Historical Data │ Peer Selection │ Comps Table │ Valuation │ Sensitivity │ History
  Revenue-Based: Overview │ Historical Data │ Revenue Analysis │ Assumptions │ Revenue Model │ Sensitivity │ History

Scanner:        Screens │ Filters │ Results │ Universe

Portfolio:      Holdings │ Performance │ Allocation │ Income │ Transactions │ Alerts

Research:       Profile │ Financials │ Ratios │ Filings │ Segments │ Peers
```

**Consistency check:**
- ✅ Every model has Overview, Historical Data, Sensitivity, and History (shared)
- ✅ Each model has 1-2 unique tabs (Dividend Analysis, Peer Selection, Revenue Analysis)
- ✅ Comps drops Monte Carlo from Sensitivity (correctly noted in Phase 1C)
- ✅ All sub-tab names follow same formatting convention (Title Case, short)

### Cross-Module Navigation Flows

Verified these navigation paths work based on specs:

```
Dashboard → Model Builder:   "Open Model Builder" link on Recent Models widget ✓
Dashboard → Portfolio:        "Open Portfolio" link on Portfolio Summary widget ✓
Dashboard → Research:         Click upcoming event → opens Research ✓

Scanner → Model Builder:      Double-click result / right-click "Open in Model Builder" ✓
Scanner → Research:           Right-click "Open in Research" ✓
Scanner → Portfolio:          Right-click "Add to Watchlist" / "Add to Portfolio" ✓

Model Builder → Research:     (implicit — ticker header bar links to Research) — NEEDS EXPLICIT SPEC
Portfolio → Model Builder:    Double-click position / "Open in Model Builder" ✓
Portfolio → Research:         (not explicitly specified) — NEEDS EXPLICIT SPEC
Research → Model Builder:     (not explicitly specified) — NEEDS EXPLICIT SPEC
```

**Amendment:** The ticker header bar (defined in Phase 0D) should include
navigation shortcuts to other modules. When viewing any company in any module,
the ticker header provides quick links:

```
AAPL  Apple Inc.  $182.52 (+0.68%)   [Model] [Research] [Scanner] [+ Watchlist]
```

This provides universal cross-module navigation from any context where a
company is loaded.

---

## Part 3: Data Flow Verification

### Financial Data Pipeline

```
Yahoo Finance API → backend/providers/yahoo_finance.py
  → financial_data table (market_cache.db)
  → Served via: GET /api/v1/companies/{ticker}/financials
  → Consumed by:
    - Model Builder → Historical Data tab (all models)
    - Research → Financials tab
    - Scanner → filter evaluation
    - Assumption Engine → all analysis
  ✅ Consistent across all specs

SEC EDGAR API → backend/providers/sec_edgar.py
  → filing_cache + filing_sections tables (market_cache.db)
  → Served via: GET /api/v1/research/{ticker}/filings
  → Consumed by:
    - Research → Filing viewer
    - Scanner → text search
    - Assumption Engine → business descriptions
    - Comps → peer selection (10-K descriptions)
  ✅ Consistent across all specs

Yahoo Finance (prices) → backend price refresh timer
  → market_data table (market_cache.db)
  → Pushed via: WebSocket /ws/prices
  → Consumed by:
    - Dashboard → Market Overview, Portfolio Summary, Watchlist
    - Portfolio → live position values
    - Model Builder → ticker header bar
  ✅ Consistent across all specs
```

### Model Data Pipeline

```
Assumption Engine generates → *_assumptions tables (user_data.db)
  → User overrides via: PUT /api/v1/model-builder/model/{id}/assumptions
  → Model calculation via: POST /api/v1/model-builder/model/{id}/run
  → Results to: model_outputs table
  → Version snapshots to: model_versions table
  → Displayed in: Model Builder sub-tabs
  → Referenced by:
    - Portfolio → valuation overlay column
    - Dashboard → Recent Models widget
    - Model Overview → cross-model comparison
  ✅ Consistent across all specs
```

---

## Part 4: Naming Convention Audit

### File Naming

All specs follow: `phase{N}{letter}_{descriptive_name}.md`
✅ Consistent

### API URL Naming

All endpoints follow: `/api/v1/{module-name}/{resource}/{action}`
✅ Consistent (kebab-case for URLs)

### Database Column Naming

All columns follow: `snake_case`
✅ Consistent

### CSS Variable Naming

All follow: `--{category}-{name}` (e.g., `--text-primary`, `--bg-card`)
✅ Consistent (with the one `--color-warning` addition noted above)

### Model Type Identifiers

Used in: models table, API requests, frontend routing

```
"dcf"           — used consistently ✓
"ddm"           — used consistently ✓
"comps"         — used consistently ✓
"revenue_based" — Phase 0B uses "revbased" in table name, 
                   Phase 1D uses "revenue_based" in model_type
```

**Resolution:** Standardize to `"revbased"` everywhere (shorter, matches table name).
Update Phase 1D model_type references.

---

## Part 5: Summary of Required Amendments

### Phase 0B (Database Schema) — Amendments:

1. Add `watchlist_items` join table (replace JSON array approach)
2. Add `portfolio_lots` table
3. Add `portfolio_accounts` table
4. Add `filing_sections` table to market_cache.db
5. Add `company_events` table to market_cache.db
6. Add `price_alerts` table to user_data.db
7. Add `universe_source`, `gics_sector_code`, `gics_industry_code`,
   `fiscal_year_end` columns to companies table
8. Update backup retention from 7 to 30 days
9. Update row count estimates for R3000 universe
10. Update transaction_type documentation to include DRIP, SPINOFF, TRANSFER, ADJUSTMENT

### Phase 0C (API Layer) — Amendments:

1. Add ~30 new endpoints (itemized in Issue 3)
2. Update scanner universe enum to include "r3000"
3. Update total endpoint count to ~87

### Phase 0D (UI/UX Framework) — Amendments:

1. Add `--color-warning: #EAB308` to color system
2. Add ticker header bar navigation shortcuts specification

### Phase 1D (Revenue-Based) — Amendments:

1. Standardize model_type to `"revbased"` (not `"revenue_based"`)

### All Specs — General:

1. Cross-module navigation via ticker header bar (Model → Research → Scanner)

---

## Part 6: Verification Summary

| Area | Status | Notes |
|------|--------|-------|
| Database tables | ⚠ 6 tables missing | Amendments defined above |
| API endpoints | ⚠ ~30 missing | Amendments defined above |
| Navigation flow | ⚠ Minor gaps | Ticker header cross-links needed |
| Data flow | ✅ Consistent | All pipelines verified |
| Color system | ⚠ 1 color missing | --color-warning added |
| Typography | ✅ Consistent | Inter + JetBrains Mono throughout |
| Naming conventions | ⚠ 1 inconsistency | revbased vs revenue_based |
| Performance targets | ✅ Consistent | No conflicts across specs |
| Architecture layers | ✅ Consistent | Three-layer rule followed |
| Widget system | ✅ Consistent | All dashboard widgets defined |
| Model plugin architecture | ✅ Consistent | All 4 models fit contract |
| Assumption engine | ✅ Consistent | Data package maps to schema |
| Export system | ✅ Consistent | Excel + PDF for all models |
| Backup/restore | ⚠ Minor conflict | Resolved: 30 days retention |

**Overall: No blocking issues. All amendments are additive — no spec needs to be
rewritten, only extended. The architecture is sound and internally consistent.**

---

## Part 7: Amendment Application Log

All amendments from Parts 1-5 have been applied directly to the source specs:

| Amendment | Applied To | Status |
|-----------|-----------|--------|
| 6 new database tables | phase0b_database_schema.md | ✅ Applied |
| companies table new columns | phase0b_database_schema.md | ✅ Applied |
| watchlists table: JSON array → join table | phase0b_database_schema.md | ✅ Applied |
| Transaction types expanded | phase0b_database_schema.md | ✅ Applied |
| Row count estimate updated for R3000 | phase0b_database_schema.md | ✅ Applied |
| Backup retention 7 → 30 days | phase0b_database_schema.md | ✅ Applied |
| ER diagram updated | phase0b_database_schema.md | ✅ Applied |
| Data ownership matrix updated | phase0b_database_schema.md | ✅ Applied |
| ~30 new API endpoints | phase0c_api_layer.md | ✅ Applied |
| Scanner universe enum updated | phase0c_api_layer.md | ✅ Applied |
| Endpoint count updated to 87 | phase0c_api_layer.md | ✅ Applied |
| Ticker header cross-module nav | phase0d_ui_ux_framework.md | ✅ Applied |
| Sub-tab maps updated | phase0d_ui_ux_framework.md | ✅ Applied |
| model_type standardized to "revbased" | phase1d_revbased_model.md | ✅ Applied |
| --color-warning | Already existed in phase0d | ✅ No change needed |

---

*End of Phase 6 — Integration & Consistency Review.*
