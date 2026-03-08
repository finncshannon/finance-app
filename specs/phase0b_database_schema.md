# Phase 0B — Database Schema & Data Architecture
> Designer Agent | February 23, 2026
> Status: COMPLETE — APPROVED BY FINN
> Updated March 2026 to match implemented codebase.
> Depends on: Phase 0 (Foundation), Phase 1A (DCF Model)

---

## Overview

This document defines the complete database schema for the Finance App.
All decisions here were made by Finn during the Phase 0B design session.

**Key decisions:**
- SQLite database (locked in Phase 0)
- Two database files: `user_data.db` (your work) + `market_cache.db` (regenerable)
- Wide table format for financial data (one row per company per year, metrics as columns)
- Separate assumption tables per model type (type-safe fields)
- Separate outputs table (enables cross-run comparison)
- Scenarios stored as JSON array within model outputs
- Full compressed snapshots for version history
- Ticker as primary key in companies table, integer IDs everywhere else

---

## Database Files

### user_data.db (Your Work Product)
Contains everything the user created or customized. Small file.
Backed up daily. Losing this file means losing all model work, portfolio
data, notes, and history.

**Tables (18):** companies, models, dcf_assumptions, ddm_assumptions,
revbased_assumptions, comps_assumptions, model_outputs, model_versions,
portfolio_positions, portfolio_lots, portfolio_transactions,
portfolio_accounts, watchlists, watchlist_items, scanner_presets,
research_notes, price_alerts, settings

**Indexes (11):** idx_models_ticker, idx_outputs_model, idx_outputs_run,
idx_versions_model, idx_positions_ticker, idx_transactions_ticker,
idx_transactions_date, idx_notes_ticker, idx_watchlist_items_wl,
idx_lots_position, idx_alerts_ticker

### market_cache.db (Regenerable Cache)
Contains data fetched from Yahoo Finance, SEC EDGAR, and other APIs.
Can be deleted and rebuilt without losing user work. May grow large
over time as more tickers are cached.

**Tables (5):** financial_data, market_data, filing_cache, filing_sections,
company_events

**Indexes (6):** idx_financial_ticker, idx_financial_year, idx_filing_ticker,
idx_filing_sections_filing, idx_events_date, idx_events_ticker

**Totals across both databases: 23 tables, 17 indexes.**

---

## Schema Definitions

### 1. companies
Central entity. Every other table references this via ticker.

```sql
CREATE TABLE companies (
    ticker          TEXT PRIMARY KEY,          -- "AAPL", "MSFT"
    company_name    TEXT NOT NULL,             -- "Apple Inc."
    sector          TEXT DEFAULT 'Unknown',    -- "Technology"
    industry        TEXT DEFAULT 'Unknown',    -- "Consumer Electronics"
    cik             TEXT,                      -- SEC Central Index Key
    exchange        TEXT,                      -- "NASDAQ", "NYSE"
    currency        TEXT DEFAULT 'USD',
    description     TEXT,                      -- Business summary
    employees       INTEGER,
    country         TEXT,
    website         TEXT,
    universe_source  TEXT DEFAULT 'manual',    -- "r3000", "manual", "portfolio", "watchlist"
    gics_sector_code TEXT,                     -- GICS numeric code
    gics_industry_code TEXT,                   -- GICS industry numeric code
    fiscal_year_end TEXT,                      -- "September", "December", etc.
    first_seen      TEXT NOT NULL,             -- ISO timestamp
    last_refreshed  TEXT                       -- ISO timestamp
);
```

**Notes:**
- Ticker is the natural key — used directly in foreign keys, no joins needed
- company_name, sector, industry update on each data refresh
- first_seen tracks when the user first looked up this company
- description comes from Yahoo Finance longBusinessSummary

---

### 2. financial_data (market_cache.db)
Wide table: one row per company per fiscal year. All metrics as columns.
Displayed Bloomberg-style in UI (years across top, metrics down rows).

```sql
CREATE TABLE financial_data (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,             -- FK → companies
    fiscal_year     INTEGER NOT NULL,          -- 2024, 2023, etc.
    period_type     TEXT DEFAULT 'annual',     -- "annual" or "ttm"
    statement_date  TEXT,                      -- Actual fiscal year end "2024-09-28"

    -- Income Statement
    revenue                 REAL,
    cost_of_revenue         REAL,
    gross_profit            REAL,
    operating_expense       REAL,
    rd_expense              REAL,
    sga_expense             REAL,
    ebit                    REAL,
    interest_expense        REAL,
    tax_provision           REAL,
    net_income              REAL,
    ebitda                  REAL,
    depreciation_amortization REAL,
    eps_basic               REAL,
    eps_diluted             REAL,

    -- Balance Sheet
    total_assets            REAL,
    current_assets          REAL,
    cash_and_equivalents    REAL,
    total_liabilities       REAL,
    current_liabilities     REAL,
    long_term_debt          REAL,
    short_term_debt         REAL,
    total_debt              REAL,
    stockholders_equity     REAL,
    working_capital         REAL,
    net_debt                REAL,

    -- Cash Flow Statement
    operating_cash_flow     REAL,
    capital_expenditure     REAL,
    free_cash_flow          REAL,
    dividends_paid          REAL,
    change_in_working_capital REAL,
    investing_cash_flow     REAL,
    financing_cash_flow     REAL,

    -- Per-Share & Market (at period end)
    shares_outstanding      REAL,
    market_cap_at_period    REAL,
    beta_at_period          REAL,
    dividend_per_share      REAL,

    -- Derived Metrics (computed on insert for fast queries)
    gross_margin            REAL,   -- gross_profit / revenue
    operating_margin        REAL,   -- ebit / revenue
    net_margin              REAL,   -- net_income / revenue
    fcf_margin              REAL,   -- free_cash_flow / revenue
    revenue_growth          REAL,   -- vs prior year
    ebitda_margin           REAL,
    roe                     REAL,   -- net_income / stockholders_equity
    debt_to_equity          REAL,   -- total_debt / stockholders_equity
    payout_ratio            REAL,   -- dividends_paid / net_income

    -- Metadata
    data_source     TEXT DEFAULT 'yahoo_finance',  -- "yahoo_finance" / "sec_edgar" / "combined"
    fetched_at      TEXT NOT NULL,                  -- ISO timestamp

    UNIQUE(ticker, fiscal_year, period_type)
);

CREATE INDEX idx_financial_ticker ON financial_data(ticker);
CREATE INDEX idx_financial_year ON financial_data(ticker, fiscal_year);
```

**Notes:**
- Derived metrics (margins, growth rates) are computed on insert by the backend
  so the frontend never has to calculate them — just display
- revenue_growth is calculated vs. prior year's row in the same table
- UNIQUE constraint prevents duplicate entries per ticker/year/period
- Up to 10 years of annual data + 1 TTM row per company = max ~11 rows per ticker
- Total for 3,000 companies (Russell 3000 universe): ~33,000 rows. Very manageable for SQLite.

---

### 3. market_data (market_cache.db)
Current/recent price data. Refreshes every 60 seconds during market hours.

```sql
CREATE TABLE market_data (
    ticker              TEXT PRIMARY KEY,      -- FK → companies
    current_price       REAL,
    previous_close      REAL,
    day_open            REAL,
    day_high            REAL,
    day_low             REAL,
    day_change          REAL,                  -- current_price - previous_close
    day_change_pct      REAL,                  -- day_change / previous_close
    fifty_two_week_high REAL,
    fifty_two_week_low  REAL,
    volume              INTEGER,
    average_volume      INTEGER,
    market_cap          REAL,
    enterprise_value    REAL,
    pe_trailing         REAL,
    pe_forward          REAL,
    price_to_book       REAL,
    price_to_sales      REAL,
    ev_to_revenue       REAL,
    ev_to_ebitda        REAL,
    dividend_yield      REAL,
    dividend_rate       REAL,
    beta                REAL,
    updated_at          TEXT NOT NULL           -- ISO timestamp
);
```

**Notes:**
- One row per ticker, overwritten on each refresh
- day_change and day_change_pct computed on insert
- This table drives the Dashboard, ticker header bar, and Portfolio live prices
- Stale data policy: show "as of X" timestamp when data is older than 5 minutes

---

### 4. models (user_data.db)
One record per ticker per model type. The parent record that links to
assumptions, outputs, and versions.

```sql
CREATE TABLE models (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker                  TEXT NOT NULL,              -- FK → companies
    model_type              TEXT NOT NULL,              -- "dcf" / "ddm" / "revbased" / "comps"
    auto_detection_score    INTEGER,                   -- 0-110
    auto_detection_confidence TEXT,                     -- "High" / "Medium" / "Low"
    auto_detection_confidence_pct INTEGER,              -- 90 / 75 / 60
    auto_detection_reasoning TEXT,                      -- Full reasoning string
    is_recommended          INTEGER DEFAULT 0,          -- 1 if auto-detected pick
    current_version         INTEGER DEFAULT 1,
    created_at              TEXT NOT NULL,
    last_run_at             TEXT,

    UNIQUE(ticker, model_type)
);

CREATE INDEX idx_models_ticker ON models(ticker);
```

**Notes:**
- UNIQUE(ticker, model_type) means one DCF model per company, one DDM, etc.
- auto_detection fields populated by ModelDetector when ticker is first opened
- current_version increments each time the model is saved to version history
- last_run_at updates every time the model is recalculated

---

### 5. dcf_assumptions (user_data.db)
DCF-specific assumption fields. Every value has a source tracker.

```sql
CREATE TABLE dcf_assumptions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id        INTEGER NOT NULL UNIQUE,   -- FK → models (1:1)

    -- Revenue Growth (per year, can curve)
    revenue_growth_yr1  REAL,
    revenue_growth_yr2  REAL,
    revenue_growth_yr3  REAL,
    revenue_growth_yr4  REAL,
    revenue_growth_yr5  REAL,
    revenue_growth_yr6  REAL,
    revenue_growth_yr7  REAL,
    revenue_growth_yr8  REAL,
    revenue_growth_yr9  REAL,
    revenue_growth_yr10 REAL,

    -- Cost Structure (each independent, as % of revenue)
    cogs_pct            REAL,
    sga_pct             REAL,
    rd_pct              REAL,
    da_method           TEXT DEFAULT 'linked_to_capex',  -- "linked_to_capex" / "declining" / "flat"
    da_pct_of_capex     REAL,

    -- CapEx & Working Capital
    capex_pct_revenue   REAL,
    nwc_pct_revenue     REAL,

    -- Tax
    effective_tax_rate  REAL,

    -- WACC Components (PRIMARY SCENARIO DIFFERENTIATOR)
    wacc                REAL,       -- Final computed WACC
    risk_free_rate      REAL,       -- Auto from 10-year Treasury
    beta                REAL,       -- From Yahoo, overridable
    equity_risk_premium REAL,       -- Manually set by user
    cost_of_equity      REAL,       -- Computed: RF + Beta × ERP
    cost_of_debt        REAL,       -- Interest Expense / Total Debt
    tax_shield          REAL,       -- 1 - Tax Rate
    equity_weight       REAL,       -- Market Cap / (Market Cap + Debt)
    debt_weight         REAL,       -- Total Debt / (Market Cap + Debt)

    -- Debt Schedule
    debt_starting_balance   REAL,
    debt_repayment_pct      REAL,   -- % retired per year
    new_issuance_assumption REAL DEFAULT 0,

    -- Terminal Value
    terminal_growth_rate    REAL,
    exit_ev_ebitda_multiple REAL,

    -- Tracking
    overrides_json      TEXT,       -- {"revenue_growth_yr1": true, "wacc": true, ...}
    engine_reasoning_json TEXT,     -- {"revenue_growth_yr1": "3yr CAGR 15%, decel...", ...}

    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
);
```

---

### 6. ddm_assumptions (user_data.db)

```sql
CREATE TABLE ddm_assumptions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id        INTEGER NOT NULL UNIQUE,   -- FK → models (1:1)

    -- Dividend Inputs
    current_dps         REAL,       -- Most recent DPS
    dividend_growth_stage1 REAL,    -- High-growth phase rate
    dividend_growth_stage2 REAL,    -- Transition phase rate (if 3-stage)
    terminal_dividend_growth REAL,  -- Mature phase rate
    growth_model_type   TEXT,       -- "2_stage" / "3_stage" / "h_model"
    stage1_years        INTEGER,    -- Duration of high-growth phase
    stage2_years        INTEGER,    -- Duration of transition (3-stage only)

    -- Required Return (CAPM-based or manual)
    required_return     REAL,       -- Final value used
    risk_free_rate      REAL,
    beta                REAL,
    equity_risk_premium REAL,
    use_capm            INTEGER DEFAULT 1,  -- 1 = compute from CAPM, 0 = manual

    -- Sustainability Metrics (informational, from engine)
    payout_ratio        REAL,
    fcf_coverage_ratio  REAL,
    earnings_coverage   REAL,

    -- Tracking
    overrides_json      TEXT,
    engine_reasoning_json TEXT,

    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
);
```

---

### 7. revbased_assumptions (user_data.db)

```sql
CREATE TABLE revbased_assumptions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id        INTEGER NOT NULL UNIQUE,   -- FK → models (1:1)

    -- Revenue Trajectory
    near_term_growth_yr1    REAL,
    near_term_growth_yr2    REAL,
    near_term_growth_yr3    REAL,
    mid_term_growth_rate    REAL,   -- Years 4-7
    terminal_growth_rate    REAL,   -- Years 8-10

    -- Multiple
    ev_revenue_multiple     REAL,   -- Current or target
    multiple_compression    REAL,   -- How much multiple declines over time
    target_ev_revenue       REAL,   -- Terminal year multiple

    -- Margin Trajectory (for when company transitions to profitability)
    target_gross_margin     REAL,
    target_operating_margin REAL,
    target_net_margin       REAL,
    years_to_profitability  INTEGER,

    -- Rule of 40 / Growth-Adjusted
    rule_of_40_score        REAL,

    -- WACC (same components as DCF)
    wacc                    REAL,
    risk_free_rate          REAL,
    beta                    REAL,
    equity_risk_premium     REAL,

    -- Tracking
    overrides_json          TEXT,
    engine_reasoning_json   TEXT,

    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
);
```

---

### 8. comps_assumptions (user_data.db)

```sql
CREATE TABLE comps_assumptions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id        INTEGER NOT NULL UNIQUE,   -- FK → models (1:1)

    -- Peer Selection
    peer_tickers_json   TEXT,       -- JSON array: ["MSFT", "GOOG", "META"]
    peer_selection_method TEXT,     -- "auto_sector" / "manual" / "hybrid"

    -- Multiples to Use
    use_pe              INTEGER DEFAULT 1,
    use_ev_ebitda       INTEGER DEFAULT 1,
    use_ev_revenue      INTEGER DEFAULT 1,
    use_pb              INTEGER DEFAULT 0,
    use_peg             INTEGER DEFAULT 0,

    -- Methodology
    aggregation_method  TEXT DEFAULT 'median',  -- "median" / "trimmed_mean" / "mean"
    outlier_handling    TEXT DEFAULT 'winsorize', -- "winsorize" / "trim" / "none"

    -- Quality Premium/Discount
    quality_premium     REAL DEFAULT 0,   -- % premium/discount vs peers
    quality_reasoning   TEXT,

    -- Tracking
    overrides_json      TEXT,
    engine_reasoning_json TEXT,

    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
);
```

---

### 9. model_outputs (user_data.db)
One row per model run. Enables comparison across runs over time.

```sql
CREATE TABLE model_outputs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id            INTEGER NOT NULL,          -- FK → models
    run_number          INTEGER NOT NULL,           -- Sequential per model
    run_timestamp       TEXT NOT NULL,

    -- Primary Output
    intrinsic_value_per_share REAL,
    enterprise_value    REAL,
    equity_value        REAL,

    -- Terminal Value (both methods, DCF-specific but stored generically)
    terminal_value_perpetuity   REAL,
    terminal_value_exit_multiple REAL,
    tv_pct_of_ev_perpetuity     REAL,
    tv_pct_of_ev_exit           REAL,

    -- Visualization Data
    waterfall_data_json     TEXT,   -- JSON for waterfall chart
    projection_table_json   TEXT,   -- Full 10-year projection table

    -- Scenarios (JSON array — all scenarios bundled together)
    scenarios_json          TEXT,
    -- Structure: [
    --   {
    --     "name": "Bear",
    --     "assumptions_delta": {"wacc": 0.11, "revenue_growth_yr1": 0.05},
    --     "intrinsic_value": 125.50,
    --     "enterprise_value": 2150000000000
    --   },
    --   { "name": "Base", ... },
    --   { "name": "Bull", ... },
    --   { "name": "Market-Implied", ... }
    -- ]
    uncertainty_level       TEXT,   -- "low" / "medium" / "high"
    scenario_count          INTEGER,

    -- Sensitivity Data (each tool's state saved independently)
    sensitivity_sliders_json    TEXT,
    sensitivity_tornado_json    TEXT,
    sensitivity_montecarlo_json TEXT,  -- Distribution, percentiles, probability
    sensitivity_tables_json     TEXT,

    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
);

CREATE INDEX idx_outputs_model ON model_outputs(model_id);
CREATE INDEX idx_outputs_run ON model_outputs(model_id, run_number);
```

---

### 10. model_versions (user_data.db)
Compressed full snapshots. Every save creates a new version.

```sql
CREATE TABLE model_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id        INTEGER NOT NULL,          -- FK → models
    version_number  INTEGER NOT NULL,
    snapshot_blob   BLOB NOT NULL,             -- Compressed JSON (zlib)
    -- Contains: {
    --   "assumptions": { full assumption record },
    --   "outputs": { full output record },
    --   "scenarios": [ scenario array ],
    --   "sensitivity": { all 4 tools' state },
    --   "market_data_at_time": { price, market_cap, etc. }
    -- }
    annotation      TEXT,                      -- "Updated after Q4 earnings"
    snapshot_size_bytes INTEGER,
    created_at      TEXT NOT NULL,

    UNIQUE(model_id, version_number),
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
);

CREATE INDEX idx_versions_model ON model_versions(model_id);
```

**Compression:** Python's `zlib.compress()` on JSON string. Typical model
snapshot ~5-10KB uncompressed → ~1-2KB compressed. 100 versions per ticker
= ~200KB. Negligible storage impact.

---

### 11. portfolio_positions (user_data.db)

```sql
CREATE TABLE portfolio_positions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,             -- FK → companies
    shares_held     REAL NOT NULL,
    cost_basis_per_share REAL,
    account         TEXT DEFAULT 'Manual',     -- "Fidelity" / "Manual" / broker name
    added_at        TEXT NOT NULL,
    last_synced_at  TEXT,
    notes           TEXT
);

CREATE INDEX idx_positions_ticker ON portfolio_positions(ticker);
```

---

### 12. portfolio_transactions (user_data.db)

```sql
CREATE TABLE portfolio_transactions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker              TEXT NOT NULL,         -- FK → companies
    transaction_type    TEXT NOT NULL,          -- "buy"/"sell"/"dividend"/"drip"/"split"/"spinoff"/"transfer"/"adjustment"
    shares              REAL,
    price_per_share     REAL,
    total_amount        REAL,
    transaction_date    TEXT NOT NULL,          -- ISO date
    account             TEXT,
    fees                REAL DEFAULT 0,
    notes               TEXT,
    created_at          TEXT NOT NULL
);

CREATE INDEX idx_transactions_ticker ON portfolio_transactions(ticker);
CREATE INDEX idx_transactions_date ON portfolio_transactions(transaction_date);
```

---

### 13. watchlists (user_data.db)

```sql
CREATE TABLE watchlists (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,           -- "Tech Watch", "Dividend Candidates"
    sort_order  INTEGER DEFAULT 0,              -- For tab ordering in UI
    created_at  TEXT NOT NULL,
    updated_at  TEXT
);
```

---

### 14. scanner_presets (user_data.db)

```sql
CREATE TABLE scanner_presets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    query_text      TEXT,                      -- Search keywords
    filters_json    TEXT,                      -- JSON array of filter objects
    sector_filter   TEXT DEFAULT 'All',
    universe        TEXT DEFAULT 'sp500',
    form_types_json TEXT DEFAULT '["10-K"]',
    created_at      TEXT NOT NULL,
    updated_at      TEXT
);
```

---

### 15. research_notes (user_data.db)

```sql
CREATE TABLE research_notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker      TEXT NOT NULL,                 -- FK → companies
    note_text   TEXT NOT NULL,
    note_type   TEXT DEFAULT 'general',        -- "general" / "earnings" / "thesis" / "risk"
    created_at  TEXT NOT NULL,
    updated_at  TEXT
);

CREATE INDEX idx_notes_ticker ON research_notes(ticker);
```

---

### 16. filing_cache (market_cache.db)

```sql
CREATE TABLE filing_cache (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker              TEXT NOT NULL,
    form_type           TEXT NOT NULL,          -- "10-K" / "10-Q" / "8-K"
    filing_date         TEXT,
    cik                 TEXT,
    accession_number    TEXT,
    sections_json       TEXT,                   -- ["item1", "item1a", "item7"]
    file_path           TEXT,                   -- Path to cached text on disk
    fetched_at          TEXT NOT NULL,

    UNIQUE(ticker, form_type, filing_date)
);

CREATE INDEX idx_filing_ticker ON filing_cache(ticker);
```

---

### 17. settings (user_data.db)

```sql
CREATE TABLE settings (
    key         TEXT PRIMARY KEY,               -- "window_state", "refresh_interval", etc.
    value       TEXT,                           -- JSON string or simple value
    updated_at  TEXT
);

-- Default settings inserted on first launch:
-- "window_state"       → {"width": 1400, "height": 900, "x": 100, "y": 50, "maximized": false}
-- "refresh_interval"   → "60"
-- "default_erp"        → "0.055"
-- "default_tax_rate"   → "0.21"
-- "theme"              → "dark"
-- "last_ticker"        → ""
-- "last_module"        → "dashboard"
```

---

### 18. watchlist_items (user_data.db)
Join table replacing the JSON array approach for watchlist tickers.

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

CREATE INDEX idx_watchlist_items_wl ON watchlist_items(watchlist_id);
```

---

### 19. portfolio_lots (user_data.db)
Individual tax lots within a position. Enables lot-level tracking,
holding period classification, and tax lot selection methods.

```sql
CREATE TABLE portfolio_lots (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id          INTEGER NOT NULL,       -- FK → portfolio_positions
    shares               REAL NOT NULL,
    cost_basis_per_share REAL NOT NULL,
    date_acquired        TEXT NOT NULL,           -- ISO date
    date_sold            TEXT,                    -- ISO date, null if held
    sale_price           REAL,
    realized_gain        REAL,
    lot_method           TEXT DEFAULT 'fifo',     -- "fifo", "lifo", "specific", etc.
    notes                TEXT,
    FOREIGN KEY (position_id) REFERENCES portfolio_positions(id) ON DELETE CASCADE
);

CREATE INDEX idx_lots_position ON portfolio_lots(position_id);
```

**Notes:**
- `portfolio_positions` is the aggregate per-ticker-per-account record
- `shares_held` and `cost_basis_per_share` in positions are computed from lots
- `date_sold` and `sale_price` populated when lot is closed via SELL transaction

---

### 20. portfolio_accounts (user_data.db)
User-defined brokerage accounts with tax classification.

```sql
CREATE TABLE portfolio_accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,       -- "Fidelity IRA"
    account_type    TEXT DEFAULT 'taxable',     -- "taxable", "traditional_ira", "roth_ira", "401k"
    is_default      INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL
);
```

**Notes:**
- `portfolio_positions.account` references `portfolio_accounts.id`
- A default account is auto-created on first portfolio use

---

### 21. filing_sections (market_cache.db)
Parsed sections from SEC filings, individually navigable and searchable.

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
```

**Notes:**
- Powers the Research module's section viewer and filing comparison
- Powers the Scanner's full-text filing search
- `filing_cache.sections_json` enumerates available sections; actual content lives here

---

### 22. company_events (market_cache.db)
Earnings dates, ex-dividend dates, and filing dates for calendar features.

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

**Notes:**
- Consumed by Dashboard → Upcoming Events widget
- Consumed by Portfolio → Earnings & Dividend Calendar
- Refreshed from Yahoo Finance on app launch and periodically

---

### 23. price_alerts (user_data.db)
User-configured price alerts for portfolio and watchlist tickers.

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

CREATE INDEX idx_alerts_ticker ON price_alerts(ticker);
```

---

## Entity Relationship Summary

```
companies (ticker PK)
  │
  ├──< financial_data (market_cache.db)
  ├──< market_data (market_cache.db)
  ├──< filing_cache (market_cache.db)
  │
  ├──< models
  │     ├──── dcf_assumptions (1:1)
  │     ├──── ddm_assumptions (1:1)
  │     ├──── revbased_assumptions (1:1)
  │     ├──── comps_assumptions (1:1)
  │     ├──< model_outputs (1:many, one per run)
  │     └──< model_versions (1:many, one per save)
  │
  ├──< portfolio_positions
  ├──< portfolio_transactions
  ├──< research_notes
  │
  ├──< watchlists
  │     └──< watchlist_items (ticker assignments)
  ├──< price_alerts
  └──< scanner_presets (indirect — results reference companies)

settings (standalone, no FK)
```

---

## Data Ownership Matrix

Which module WRITES to which tables:

| Table | Written By | Read By |
|-------|-----------|---------|
| companies | Data refresh service, Model Builder (on ticker entry) | All modules |
| financial_data | Data refresh service | Model Builder, Research |
| market_data | Market refresh service (60s cycle) | Dashboard, Portfolio, Model Builder |
| models | Model Builder (on first model run) | Model Builder, Overview |
| *_assumptions | Assumption engine + user overrides | Model Builder, Sensitivity |
| model_outputs | Model calculation engine | Model Builder, Sensitivity, History |
| model_versions | Version save trigger | History sub-tab |
| portfolio_positions | Portfolio module, broker sync | Portfolio, Dashboard |
| portfolio_transactions | Portfolio module | Portfolio |
| watchlists | User action (add to watchlist) | Dashboard, watchlist views |
| watchlist_items | Watchlist add/remove actions | Dashboard, watchlist views |
| portfolio_lots | Portfolio module | Portfolio |
| portfolio_accounts | Portfolio module | Portfolio, Settings |
| filing_sections | Filing parser | Research, Scanner |
| company_events | Event refresh service | Dashboard, Portfolio |
| price_alerts | Portfolio module | Portfolio, Dashboard |
| scanner_presets | Scanner module | Scanner |
| research_notes | Research module | Research |
| filing_cache | Filing fetch service | Research, Scanner |
| settings | Settings panel, window state save | App startup, all modules |

---

## Cache & Refresh Strategy

| Data Type | Cache Location | TTL | Refresh Trigger |
|-----------|---------------|-----|-----------------|
| Price data | market_data table | 60 seconds (market hours) | Auto timer |
| Price data | market_data table | Manual only (off hours) | User click |
| Financial statements | financial_data table | 24 hours | Auto on ticker open |
| Company info | companies table | 24 hours | Auto on ticker open |
| Filing text | filing_cache + disk files | Never expires | Manual re-fetch |
| Model assumptions | *_assumptions tables | Never expires | User action |
| Model outputs | model_outputs table | Never expires | Model recalculation |

---

## Backup Strategy

- **What:** `user_data.db` only (market_cache.db is regenerable)
- **When:** Daily, on app close
- **Where:** `backups/` folder alongside the database
- **Retention:** Keep last 30 daily backups, delete older
- **How:** SQLite `.backup()` API (safe even if app crashes mid-backup)
- **Size estimate:** ~5-10 MB after heavy use (thousands of model versions)

---

## Migration from Current System

| Current Source | New Location |
|---------------|-------------|
| Yahoo Finance API cache (data/yahoo_cache/cache.db) | market_cache.db financial_data + market_data |
| Screening Tool (data/filings/*) | filing_cache table + same disk structure |
| Screening Tool (data/financials/*.json) | financial_data table (imported) |
| Excel named ranges (config.py NAMED_RANGES) | Mapped to database columns |
| Excel History sheet | model_versions table |
| Excel assumptions sheets | *_assumptions tables |
| Screening Tool saved searches | scanner_presets table |
| Screening Tool settings.json | settings table |

Migration happens once on first app launch. A migration service reads
existing data files and populates the new database tables.

---

## Implementation Notes for Architect

1. **Use SQLite WAL mode** — enables concurrent reads while writing.
   `PRAGMA journal_mode=WAL;` on connection open.

2. **Foreign keys must be enabled** — SQLite has them off by default.
   `PRAGMA foreign_keys=ON;` on every connection.

3. **Timestamps are ISO 8601 strings** — "2026-02-23T14:30:00Z".
   SQLite has no native datetime type. Store as TEXT, parse in Python.

4. **JSON fields use TEXT type** — SQLite supports JSON functions
   (`json_extract()`, `json_array_length()`) for querying inside JSON columns.

5. **Compression for snapshots** — use Python `zlib.compress(json_bytes)`
   for model_versions.snapshot_blob. Store as BLOB.

6. **Connection pooling** — FastAPI should use a connection pool
   (e.g., `aiosqlite` for async) rather than opening/closing per request.

7. **Two-database access** — backend opens both database files.
   user_data.db is the primary connection. market_cache.db is attached:
   `ATTACH DATABASE 'market_cache.db' AS cache;`
   Then query as: `SELECT * FROM cache.financial_data WHERE ticker = ?`
