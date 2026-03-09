"""Initialize market_cache.db with all 6 tables.

Tables (from phase0b_database_schema.md):
  financial_data, market_data, filing_cache, filing_sections, company_events

Note: research_notes is in user_data.db per phase0b despite being listed
under market_cache in the task spec. The schema follows phase0b exactly.

Cache tables are accessed via the 'cache' schema prefix:
    SELECT * FROM cache.financial_data WHERE ticker = ?
"""

from db.connection import DatabaseConnection

_CACHE_DB_SCHEMA = """
-- 2. financial_data
CREATE TABLE IF NOT EXISTS financial_data (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    fiscal_year     INTEGER NOT NULL,
    period_type     TEXT DEFAULT 'annual',
    statement_date  TEXT,
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
    operating_cash_flow     REAL,
    capital_expenditure     REAL,
    free_cash_flow          REAL,
    dividends_paid          REAL,
    change_in_working_capital REAL,
    investing_cash_flow     REAL,
    financing_cash_flow     REAL,
    shares_outstanding      REAL,
    market_cap_at_period    REAL,
    beta_at_period          REAL,
    dividend_per_share      REAL,
    gross_margin            REAL,
    operating_margin        REAL,
    net_margin              REAL,
    fcf_margin              REAL,
    revenue_growth          REAL,
    ebitda_margin           REAL,
    roe                     REAL,
    debt_to_equity          REAL,
    payout_ratio            REAL,
    data_source     TEXT DEFAULT 'yahoo_finance',
    fetched_at      TEXT NOT NULL,
    UNIQUE(ticker, fiscal_year, period_type)
);

CREATE INDEX IF NOT EXISTS idx_financial_ticker ON financial_data(ticker);
CREATE INDEX IF NOT EXISTS idx_financial_year ON financial_data(ticker, fiscal_year);

-- 3. market_data
CREATE TABLE IF NOT EXISTS market_data (
    ticker              TEXT PRIMARY KEY,
    current_price       REAL,
    previous_close      REAL,
    day_open            REAL,
    day_high            REAL,
    day_low             REAL,
    day_change          REAL,
    day_change_pct      REAL,
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
    updated_at          TEXT NOT NULL
);

-- 16. filing_cache
CREATE TABLE IF NOT EXISTS filing_cache (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker              TEXT NOT NULL,
    form_type           TEXT NOT NULL,
    filing_date         TEXT,
    cik                 TEXT,
    accession_number    TEXT,
    sections_json       TEXT,
    file_path           TEXT,
    fetched_at          TEXT NOT NULL,
    UNIQUE(ticker, form_type, filing_date)
);

CREATE INDEX IF NOT EXISTS idx_filing_ticker ON filing_cache(ticker);

-- 21. filing_sections
CREATE TABLE IF NOT EXISTS filing_sections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    filing_id       INTEGER NOT NULL,
    section_key     TEXT NOT NULL,
    section_title   TEXT NOT NULL,
    content_text    TEXT NOT NULL,
    word_count      INTEGER,
    FOREIGN KEY (filing_id) REFERENCES filing_cache(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_filing_sections_filing ON filing_sections(filing_id);

-- 22. company_events
CREATE TABLE IF NOT EXISTS company_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    event_date      TEXT NOT NULL,
    event_time      TEXT,
    description     TEXT,
    amount          REAL,
    is_estimated    INTEGER DEFAULT 0,
    source          TEXT DEFAULT 'yahoo',
    fetched_at      TEXT NOT NULL,
    UNIQUE(ticker, event_type, event_date)
);

CREATE INDEX IF NOT EXISTS idx_events_date ON company_events(event_date);
CREATE INDEX IF NOT EXISTS idx_events_ticker ON company_events(ticker);

-- 23. news_articles — persisted news feed for historical lookback
CREATE TABLE IF NOT EXISTS news_articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    url             TEXT NOT NULL UNIQUE,
    title           TEXT NOT NULL,
    source          TEXT NOT NULL,
    published_at    TEXT,
    snippet         TEXT,
    category        TEXT DEFAULT 'General',
    region          TEXT DEFAULT 'Global',
    coverage_count  INTEGER DEFAULT 1,
    fetched_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_news_published ON news_articles(published_at);
CREATE INDEX IF NOT EXISTS idx_news_category ON news_articles(category);
CREATE INDEX IF NOT EXISTS idx_news_cat_pub ON news_articles(category, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_reg_pub ON news_articles(region, published_at DESC);
"""


async def init_cache_db(db: DatabaseConnection) -> None:
    """Create all cache tables in the ATTACHed cache database.

    Since cache db is ATTACHed as 'cache', we need to run the DDL
    directly on the cache db file before attaching, or use the
    cache. prefix. We run it via executescript on a temporary
    direct connection to the cache db file.
    """
    import aiosqlite

    # Initialize cache db schema via direct connection
    async with aiosqlite.connect(str(db.cache_db_path)) as cache_conn:
        await cache_conn.execute("PRAGMA journal_mode=WAL;")
        await cache_conn.executescript(_CACHE_DB_SCHEMA)
        await cache_conn.commit()
