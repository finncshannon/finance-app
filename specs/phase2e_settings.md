# Phase 2E — Settings & Configuration Module
> Designer Agent | February 26, 2026
> Status: COMPLETE — APPROVED BY FINN
> Depends on: Phase 0A-0E (foundation), all module specs

---

## Overview

The Settings module is the central configuration hub for the entire app.
It consolidates every user-configurable option referenced across all
other specs into a single, organized interface.

Settings are stored in the `settings` table (key-value pairs) and
`portfolio_accounts` table. Changes take effect immediately — no
"Save" button needed (auto-persist on change).

---

## Part 1: Settings Sub-Tab Structure

```
Settings Sub-Tabs:
  General │ Data Sources │ Model Defaults │ Portfolio │ Scanner │ About
```

---

## Part 2: General Settings

```
GENERAL SETTINGS
────────────────────────────────────────────────────────────────────────

  Application
  ──────────────────────────────────────────────
  Startup Module:         [Dashboard ▼]
    Options: Dashboard, Model Builder, Scanner, Portfolio, Research
    Which module opens after the boot sequence.

  Window Behavior:        [● Remember last position]
    ○ Remember last position and size
    ○ Always start maximized
    ○ Always start at default size (1400×900)

  Boot Animation:         [● Enabled]
    Toggle on/off. When off, app opens directly to startup module.

  Notifications
  ──────────────────────────────────────────────
  Price Alerts:           [● In-app toast]
    Notification method for triggered alerts.

  Stale Data Warning:     [● Enabled]
    Show warning indicators when data is older than expected.

  Keyboard Shortcuts
  ──────────────────────────────────────────────
  Ctrl+1 through Ctrl+5:  Switch between module tabs
  Ctrl+R:                  Refresh current data
  Ctrl+S:                  Save version (in Model Builder)
  Ctrl+F:                  Search within current view
  Ctrl+E:                  Export current view
  Ctrl+N:                  New model / New position / New watchlist (context-dependent)
  Esc:                     Close modal / Cancel action

  (Display only — not configurable in v1, but documented here for reference)
────────────────────────────────────────────────────────────────────────
```

---

## Part 3: Data Sources Settings

```
DATA SOURCES
────────────────────────────────────────────────────────────────────────

  Yahoo Finance
  ──────────────────────────────────────────────
  Status:                 ● Connected (last fetch: 2 min ago)
  Refresh Interval:       [60 seconds ▼]
    Options: 30s, 60s (default), 120s, 300s, Manual only
    Controls how often live prices update during market hours.

  Market Hours Behavior:  [● Auto-refresh during market hours only]
    ○ Auto-refresh during market hours only (9:30 AM - 4:00 PM ET)
    ○ Auto-refresh always (includes pre/post market)
    ○ Manual refresh only

  SEC EDGAR
  ──────────────────────────────────────────────
  Status:                 ● Connected
  User Agent Email:       [finn@example.com        ]
    Required by SEC EDGAR fair access policy.
    Used in API request headers.

  Auto-Fetch Filings:    [● On ticker open]
    ○ On ticker open (fetch if not cached)
    ○ Manual only (never auto-fetch)

  Filing Retention:       [5 years ▼]
    Options: 1 year, 3 years, 5 years (default), 10 years
    How many years of 10-K/10-Q filings to cache per company.

  Data Management
  ──────────────────────────────────────────────
  Market Cache Size:      142 MB (market_cache.db)
  User Data Size:         8.2 MB (user_data.db)

  [Clear Market Cache]    Deletes market_cache.db. Data re-fetched on demand.
  [Refresh All Data]      Force-refreshes all universe data (background task).

  Backup
  ──────────────────────────────────────────────
  Auto-Backup:            [● Enabled (daily)]
  Backup Location:        /backups/ (alongside database)
  Retention:              [30 days ▼]
    Options: 7 days, 14 days, 30 days (default), 90 days
  Last Backup:            Feb 26, 2026 at 11:45 PM
  Backup Count:           12 backups (total: 45 MB)

  [Backup Now]            Trigger immediate backup
  [Restore from Backup]   Select a backup to restore (confirmation required)
  [Open Backup Folder]    Opens backup directory in file explorer
────────────────────────────────────────────────────────────────────────
```

---

## Part 4: Model Defaults

These are the global defaults used by the Assumption Engine when generating
assumptions for any new model. Per-model overrides always take precedence.

```
MODEL DEFAULTS
────────────────────────────────────────────────────────────────────────

  WACC / Required Return
  ──────────────────────────────────────────────
  Equity Risk Premium:    [5.5%    ] (range: 3.0% - 10.0%)
    The market-wide ERP applied in all CAPM calculations.
    Reference: Damodaran's current estimate ~5.5%

  Size Premium:           [● Enabled]
    Auto-applied based on market cap tier.
    Mega/Large: 0%, Mid: 0.5%, Small: 1.5%, Micro: 2.5%

  Risk-Free Rate Source:  [● Auto (10Y Treasury)]
    ○ Auto — fetched daily from Yahoo Finance
    ○ Manual — [    %] user enters fixed rate

  Projections
  ──────────────────────────────────────────────
  Default Projection Period:  [10 years ▼]
    Options: 5, 7, 10 (default), 15 years
    How many years forward the DCF and Revenue-Based models project.

  Terminal Growth Rate:   [● Auto (engine-determined)]
    ○ Auto — engine determines based on company and sector
    ○ Fixed — [    %] applied to all models

  Scenarios
  ──────────────────────────────────────────────
  Default Scenario Weights (3-scenario):
    Bear: [25%]  Base: [50%]  Bull: [25%]
    Must sum to 100%. Sliders linked.

  Default Scenario Weights (5-scenario):
    Deep Bear: [10%]  Bear: [20%]  Base: [40%]  Bull: [20%]  Deep Bull: [10%]
    Must sum to 100%.

  Monte Carlo
  ──────────────────────────────────────────────
  Default Iterations:     [10,000 ▼]
    Options: 1,000 / 5,000 / 10,000 (default) / 50,000 / 100,000
    Higher = more accurate distribution, longer calculation time.

  Display
  ──────────────────────────────────────────────
  Reasoning Verbosity:    [● Summary]
    ○ Summary — one-line reasoning per assumption (default)
    ○ Detailed — full multi-paragraph reasoning expanded by default

  Currency Display:       [● USD ($)]
    For future multi-currency support. Locked to USD for v1.

  Number Format:          [● US (1,234.56)]
    For future internationalization. Locked to US format for v1.
────────────────────────────────────────────────────────────────────────
```

---

## Part 5: Portfolio Settings

```
PORTFOLIO SETTINGS
────────────────────────────────────────────────────────────────────────

  Accounts
  ──────────────────────────────────────────────
  ┌──────────────────────────────────────────────────────────────┐
  │ Account           Type              Default    Actions       │
  │ Fidelity IRA      Traditional IRA   ●          [Edit] [×]   │
  │ Fidelity Taxable  Taxable           ○          [Edit] [×]   │
  │ Schwab Roth       Roth IRA          ○          [Edit] [×]   │
  └──────────────────────────────────────────────────────────────┘

  [+ Add Account]

  Account types: Taxable, Traditional IRA, Roth IRA, 401(k), Other
  Default account: used when adding positions without specifying account.
  Deleting an account requires reassigning its positions first.

  Performance
  ──────────────────────────────────────────────
  Default Benchmark:      [S&P 500 (SPY) ▼]
    Options: S&P 500, Russell 3000, NASDAQ, DJIA, Custom ETF ticker
    Custom: [         ] (enter any ETF ticker)

  Tax Lot Method:         [FIFO ▼]
    Options: FIFO (default), LIFO, Highest Cost, Lowest Cost, Specific Lot
    Used when calculating realized gains from SELL transactions.

  Broker Integration (Future)
  ──────────────────────────────────────────────
  Connected Accounts:     None
  [Connect Broker...]     (Coming soon — architecture ready)
────────────────────────────────────────────────────────────────────────
```

---

## Part 6: Scanner Settings

```
SCANNER SETTINGS
────────────────────────────────────────────────────────────────────────

  Universe
  ──────────────────────────────────────────────
  Base Universe:          Russell 3000 (2,987 companies)
  Additional Tickers:     43 (manually added)
  Total Universe:         3,030 companies

  Auto-Add Behavior:      [● Add tickers when searched in Model Builder]
    When you look up a ticker in Model Builder, it's automatically
    added to the scanner universe.

  [Manage Universe →]     Opens Scanner → Universe tab

  Defaults
  ──────────────────────────────────────────────
  Default Result Limit:   [50 ▼]
    Options: 25, 50 (default), 100, 200, All
    Max results shown per screen run.

  Default Columns:        [Customize...]
    Opens column picker for the default results table columns.
    Changes apply to new screens. Existing presets keep their columns.
────────────────────────────────────────────────────────────────────────
```

---

## Part 7: About

```
ABOUT
────────────────────────────────────────────────────────────────────────

  Finance App                         v1.0.0
  Built with Electron + React + FastAPI

  Database
  ──────────────────────────────────────────────
  User Data:    user_data.db     (8.2 MB)
  Market Cache: market_cache.db  (142 MB)
  Companies:    3,030
  Models:       47
  Versions:     312

  System
  ──────────────────────────────────────────────
  Backend Status:   ● Running (uptime: 4h 23m)
  Python Version:   3.11.7
  Node Version:     20.x
  Platform:         macOS 15.2 (Apple M4 Pro)
  Memory Usage:     287 MB

  [Open Data Folder]      Opens directory containing database files
  [Open Logs]             Opens application log file
  [Check for Updates]     (Future — manual check)
────────────────────────────────────────────────────────────────────────
```

---

## Part 8: Settings Data Model

All settings stored as key-value pairs in the `settings` table:

```
KEY                          DEFAULT VALUE         TYPE
─────────────────────────────────────────────────────────────
startup_module               "dashboard"           string
window_state                 {...}                 JSON
boot_animation_enabled       true                  boolean
refresh_interval_seconds     60                    integer
market_hours_only            true                  boolean
sec_edgar_email              ""                    string
auto_fetch_filings           true                  boolean
filing_retention_years       5                     integer
backup_enabled               true                  boolean
backup_retention_days        30                    integer
default_erp                  0.055                 float
size_premium_enabled         true                  boolean
risk_free_rate_source        "auto"                string
risk_free_rate_manual        null                  float|null
default_projection_years     10                    integer
terminal_growth_source       "auto"                string
terminal_growth_manual       null                  float|null
scenario_weights_3           [0.25, 0.50, 0.25]   JSON
scenario_weights_5           [0.10, 0.20, ...]     JSON
monte_carlo_iterations       10000                 integer
reasoning_verbosity          "summary"             string
default_benchmark            "SPY"                 string
tax_lot_method               "fifo"                string
scanner_auto_add             true                  boolean
scanner_default_limit        50                    integer
scanner_default_columns      [...]                 JSON
```

---

## Part 9: Performance

```
Settings page load:         < 200ms (reads from settings table)
Setting change persist:     < 100ms (single key-value write)
Backup trigger:             < 5s (SQLite .backup() API)
Cache clear:                < 2s (delete + vacuum)
```

---

*End of Phase 2E specification.*
