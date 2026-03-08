"""Initialize user_data.db with all 17 tables.

Tables (from phase0b_database_schema.md):
  companies, models, dcf_assumptions, ddm_assumptions, revbased_assumptions,
  comps_assumptions, model_outputs, model_versions, portfolio_positions,
  portfolio_lots, portfolio_transactions, portfolio_accounts, watchlists,
  watchlist_items, scanner_presets, price_alerts, settings
"""

from datetime import datetime, timezone

from db.connection import DatabaseConnection

# All CREATE TABLE / INDEX statements copied verbatim from phase0b
_USER_DB_SCHEMA = """
-- 1. companies
CREATE TABLE IF NOT EXISTS companies (
    ticker          TEXT PRIMARY KEY,
    company_name    TEXT NOT NULL,
    sector          TEXT DEFAULT 'Unknown',
    industry        TEXT DEFAULT 'Unknown',
    cik             TEXT,
    exchange        TEXT,
    currency        TEXT DEFAULT 'USD',
    description     TEXT,
    employees       INTEGER,
    country         TEXT,
    website         TEXT,
    universe_source  TEXT DEFAULT 'manual',
    universe_tags    TEXT DEFAULT '',
    gics_sector_code TEXT,
    gics_industry_code TEXT,
    fiscal_year_end TEXT,
    first_seen      TEXT NOT NULL,
    last_refreshed  TEXT
);

-- 4. models
CREATE TABLE IF NOT EXISTS models (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker                  TEXT NOT NULL,
    model_type              TEXT NOT NULL,
    auto_detection_score    INTEGER,
    auto_detection_confidence TEXT,
    auto_detection_confidence_pct INTEGER,
    auto_detection_reasoning TEXT,
    is_recommended          INTEGER DEFAULT 0,
    current_version         INTEGER DEFAULT 1,
    created_at              TEXT NOT NULL,
    last_run_at             TEXT,
    UNIQUE(ticker, model_type)
);

CREATE INDEX IF NOT EXISTS idx_models_ticker ON models(ticker);

-- 5. dcf_assumptions
CREATE TABLE IF NOT EXISTS dcf_assumptions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id        INTEGER NOT NULL UNIQUE,
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
    cogs_pct            REAL,
    sga_pct             REAL,
    rd_pct              REAL,
    da_method           TEXT DEFAULT 'linked_to_capex',
    da_pct_of_capex     REAL,
    capex_pct_revenue   REAL,
    nwc_pct_revenue     REAL,
    effective_tax_rate  REAL,
    wacc                REAL,
    risk_free_rate      REAL,
    beta                REAL,
    equity_risk_premium REAL,
    cost_of_equity      REAL,
    cost_of_debt        REAL,
    tax_shield          REAL,
    equity_weight       REAL,
    debt_weight         REAL,
    debt_starting_balance   REAL,
    debt_repayment_pct      REAL,
    new_issuance_assumption REAL DEFAULT 0,
    terminal_growth_rate    REAL,
    exit_ev_ebitda_multiple REAL,
    overrides_json      TEXT,
    engine_reasoning_json TEXT,
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
);

-- 6. ddm_assumptions
CREATE TABLE IF NOT EXISTS ddm_assumptions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id        INTEGER NOT NULL UNIQUE,
    current_dps         REAL,
    dividend_growth_stage1 REAL,
    dividend_growth_stage2 REAL,
    terminal_dividend_growth REAL,
    growth_model_type   TEXT,
    stage1_years        INTEGER,
    stage2_years        INTEGER,
    required_return     REAL,
    risk_free_rate      REAL,
    beta                REAL,
    equity_risk_premium REAL,
    use_capm            INTEGER DEFAULT 1,
    payout_ratio        REAL,
    fcf_coverage_ratio  REAL,
    earnings_coverage   REAL,
    overrides_json      TEXT,
    engine_reasoning_json TEXT,
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
);

-- 7. revbased_assumptions
CREATE TABLE IF NOT EXISTS revbased_assumptions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id        INTEGER NOT NULL UNIQUE,
    near_term_growth_yr1    REAL,
    near_term_growth_yr2    REAL,
    near_term_growth_yr3    REAL,
    mid_term_growth_rate    REAL,
    terminal_growth_rate    REAL,
    ev_revenue_multiple     REAL,
    multiple_compression    REAL,
    target_ev_revenue       REAL,
    target_gross_margin     REAL,
    target_operating_margin REAL,
    target_net_margin       REAL,
    years_to_profitability  INTEGER,
    rule_of_40_score        REAL,
    wacc                    REAL,
    risk_free_rate          REAL,
    beta                    REAL,
    equity_risk_premium     REAL,
    overrides_json          TEXT,
    engine_reasoning_json   TEXT,
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
);

-- 8. comps_assumptions
CREATE TABLE IF NOT EXISTS comps_assumptions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id        INTEGER NOT NULL UNIQUE,
    peer_tickers_json   TEXT,
    peer_selection_method TEXT,
    use_pe              INTEGER DEFAULT 1,
    use_ev_ebitda       INTEGER DEFAULT 1,
    use_ev_revenue      INTEGER DEFAULT 1,
    use_pb              INTEGER DEFAULT 0,
    use_peg             INTEGER DEFAULT 0,
    aggregation_method  TEXT DEFAULT 'median',
    outlier_handling    TEXT DEFAULT 'winsorize',
    quality_premium     REAL DEFAULT 0,
    quality_reasoning   TEXT,
    overrides_json      TEXT,
    engine_reasoning_json TEXT,
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
);

-- 9. model_outputs
CREATE TABLE IF NOT EXISTS model_outputs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id            INTEGER NOT NULL,
    run_number          INTEGER NOT NULL,
    run_timestamp       TEXT NOT NULL,
    intrinsic_value_per_share REAL,
    enterprise_value    REAL,
    equity_value        REAL,
    terminal_value_perpetuity   REAL,
    terminal_value_exit_multiple REAL,
    tv_pct_of_ev_perpetuity     REAL,
    tv_pct_of_ev_exit           REAL,
    waterfall_data_json     TEXT,
    projection_table_json   TEXT,
    scenarios_json          TEXT,
    uncertainty_level       TEXT,
    scenario_count          INTEGER,
    sensitivity_sliders_json    TEXT,
    sensitivity_tornado_json    TEXT,
    sensitivity_montecarlo_json TEXT,
    sensitivity_tables_json     TEXT,
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_outputs_model ON model_outputs(model_id);
CREATE INDEX IF NOT EXISTS idx_outputs_run ON model_outputs(model_id, run_number);

-- 10. model_versions
CREATE TABLE IF NOT EXISTS model_versions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id        INTEGER NOT NULL,
    version_number  INTEGER NOT NULL,
    snapshot_blob   BLOB NOT NULL,
    annotation      TEXT,
    snapshot_size_bytes INTEGER,
    created_at      TEXT NOT NULL,
    UNIQUE(model_id, version_number),
    FOREIGN KEY (model_id) REFERENCES models(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_versions_model ON model_versions(model_id);

-- 11. portfolio_positions
CREATE TABLE IF NOT EXISTS portfolio_positions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    shares_held     REAL NOT NULL,
    cost_basis_per_share REAL,
    account         TEXT DEFAULT 'Manual',
    added_at        TEXT NOT NULL,
    last_synced_at  TEXT,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_positions_ticker ON portfolio_positions(ticker);

-- 12. portfolio_transactions
CREATE TABLE IF NOT EXISTS portfolio_transactions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker              TEXT NOT NULL,
    transaction_type    TEXT NOT NULL,
    shares              REAL,
    price_per_share     REAL,
    total_amount        REAL,
    transaction_date    TEXT NOT NULL,
    account             TEXT,
    fees                REAL DEFAULT 0,
    notes               TEXT,
    created_at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_transactions_ticker ON portfolio_transactions(ticker);
CREATE INDEX IF NOT EXISTS idx_transactions_date ON portfolio_transactions(transaction_date);

-- 13. watchlists
CREATE TABLE IF NOT EXISTS watchlists (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    sort_order  INTEGER DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT
);

-- 14. scanner_presets
CREATE TABLE IF NOT EXISTS scanner_presets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    query_text      TEXT,
    filters_json    TEXT,
    sector_filter   TEXT DEFAULT 'All',
    universe        TEXT DEFAULT 'sp500',
    form_types_json TEXT DEFAULT '["10-K"]',
    created_at      TEXT NOT NULL,
    updated_at      TEXT
);

-- 15. research_notes (in user_data.db per phase0b)
CREATE TABLE IF NOT EXISTS research_notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker      TEXT NOT NULL,
    note_text   TEXT NOT NULL,
    note_type   TEXT DEFAULT 'general',
    created_at  TEXT NOT NULL,
    updated_at  TEXT
);

CREATE INDEX IF NOT EXISTS idx_notes_ticker ON research_notes(ticker);

-- 17. settings
CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT,
    updated_at  TEXT
);

-- 18. watchlist_items
CREATE TABLE IF NOT EXISTS watchlist_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    watchlist_id    INTEGER NOT NULL,
    ticker          TEXT NOT NULL,
    sort_order      INTEGER DEFAULT 0,
    added_at        TEXT NOT NULL,
    UNIQUE(watchlist_id, ticker),
    FOREIGN KEY (watchlist_id) REFERENCES watchlists(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_watchlist_items_wl ON watchlist_items(watchlist_id);

-- 19. portfolio_lots
CREATE TABLE IF NOT EXISTS portfolio_lots (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id          INTEGER NOT NULL,
    shares               REAL NOT NULL,
    cost_basis_per_share REAL NOT NULL,
    date_acquired        TEXT NOT NULL,
    date_sold            TEXT,
    sale_price           REAL,
    realized_gain        REAL,
    lot_method           TEXT DEFAULT 'fifo',
    notes                TEXT,
    FOREIGN KEY (position_id) REFERENCES portfolio_positions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_lots_position ON portfolio_lots(position_id);

-- 20. portfolio_accounts
CREATE TABLE IF NOT EXISTS portfolio_accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    account_type    TEXT DEFAULT 'taxable',
    is_default      INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL
);

-- 23. price_alerts
CREATE TABLE IF NOT EXISTS price_alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    alert_type      TEXT NOT NULL,
    threshold       REAL NOT NULL,
    is_active       INTEGER DEFAULT 1,
    triggered_at    TEXT,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_alerts_ticker ON price_alerts(ticker);
"""

# Default settings from phase0b
_DEFAULT_SETTINGS = [
    ("window_state", '{"width": 1400, "height": 900, "x": 100, "y": 50, "maximized": false}'),
    ("refresh_interval", "60"),
    ("default_erp", "0.055"),
    ("default_tax_rate", "0.21"),
    ("theme", "dark"),
    ("last_ticker", ""),
    ("last_module", "dashboard"),
]


async def init_user_db(db: DatabaseConnection) -> None:
    """Create all 17 user_data.db tables and insert default settings."""
    # Execute schema (CREATE TABLE IF NOT EXISTS is idempotent)
    await db.conn.executescript(_USER_DB_SCHEMA)
    await db.commit()

    # Migration: add universe_tags column if missing (for existing databases)
    try:
        await db.execute("ALTER TABLE companies ADD COLUMN universe_tags TEXT DEFAULT ''")
        await db.commit()
    except Exception:
        pass  # Column already exists

    # Insert default settings only if table is empty (first launch)
    row = await db.fetchone("SELECT COUNT(*) as cnt FROM settings")
    if row and row["cnt"] == 0:
        now = datetime.now(timezone.utc).isoformat()
        await db.executemany(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
            [(k, v, now) for k, v in _DEFAULT_SETTINGS],
        )
        await db.commit()
