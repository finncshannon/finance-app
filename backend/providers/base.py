"""Abstract DataProvider interface and Pydantic data models.

All provider implementations (Yahoo Finance, Polygon, Finnhub, etc.)
extend DataProvider and return these standard models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime, timezone

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Data models — map cleanly to phase0b database table schemas
# ---------------------------------------------------------------------------


class QuoteData(BaseModel):
    """Current price and key market data. Maps to market_data table."""

    ticker: str
    current_price: float | None = None
    previous_close: float | None = None
    day_open: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    day_change: float | None = None
    day_change_pct: float | None = None
    volume: int | None = None
    average_volume: int | None = None
    market_cap: float | None = None
    enterprise_value: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None


class KeyStatistics(BaseModel):
    """Valuation ratios and statistics. Stored alongside quote in market_data."""

    ticker: str
    pe_trailing: float | None = None
    pe_forward: float | None = None
    price_to_book: float | None = None
    price_to_sales: float | None = None
    ev_to_revenue: float | None = None
    ev_to_ebitda: float | None = None
    dividend_yield: float | None = None
    dividend_rate: float | None = None
    beta: float | None = None


class PriceBar(BaseModel):
    """Single OHLCV price bar (daily or intraday)."""

    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class CompanyInfo(BaseModel):
    """Company profile data. Maps to companies table."""

    ticker: str
    company_name: str
    sector: str = "Unknown"
    industry: str = "Unknown"
    cik: str | None = None
    exchange: str | None = None
    currency: str = "USD"
    description: str | None = None
    employees: int | None = None
    country: str | None = None
    website: str | None = None
    fiscal_year_end: str | None = None
    quote_type: str = "EQUITY"  # EQUITY, ETF, MUTUALFUND, etc.


class FinancialPeriod(BaseModel):
    """One fiscal period (annual or quarterly) of financial data.
    Maps to a single row in financial_data table."""

    ticker: str
    fiscal_year: int
    period_type: str = "annual"
    statement_date: str | None = None

    # Income Statement
    revenue: float | None = None
    cost_of_revenue: float | None = None
    gross_profit: float | None = None
    operating_expense: float | None = None
    rd_expense: float | None = None
    sga_expense: float | None = None
    ebit: float | None = None
    interest_expense: float | None = None
    tax_provision: float | None = None
    net_income: float | None = None
    ebitda: float | None = None
    depreciation_amortization: float | None = None
    eps_basic: float | None = None
    eps_diluted: float | None = None

    # Balance Sheet
    total_assets: float | None = None
    current_assets: float | None = None
    cash_and_equivalents: float | None = None
    total_liabilities: float | None = None
    current_liabilities: float | None = None
    long_term_debt: float | None = None
    short_term_debt: float | None = None
    total_debt: float | None = None
    stockholders_equity: float | None = None
    working_capital: float | None = None
    net_debt: float | None = None

    # Cash Flow
    operating_cash_flow: float | None = None
    capital_expenditure: float | None = None
    free_cash_flow: float | None = None
    dividends_paid: float | None = None
    change_in_working_capital: float | None = None
    investing_cash_flow: float | None = None
    financing_cash_flow: float | None = None

    # Per-Share & Market
    shares_outstanding: float | None = None
    market_cap_at_period: float | None = None
    beta_at_period: float | None = None
    dividend_per_share: float | None = None

    # Derived Metrics (computed on insert)
    gross_margin: float | None = None
    operating_margin: float | None = None
    net_margin: float | None = None
    fcf_margin: float | None = None
    revenue_growth: float | None = None
    ebitda_margin: float | None = None
    roe: float | None = None
    debt_to_equity: float | None = None
    payout_ratio: float | None = None

    data_source: str = "yahoo_finance"
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FinancialStatements(BaseModel):
    """Multi-year financial statements for a company."""

    ticker: str
    periods: list[FinancialPeriod] = []


class SearchResult(BaseModel):
    """Lightweight search result for ticker/company name search."""

    ticker: str
    company_name: str
    exchange: str | None = None
    type: str | None = None  # "equity", "etf", etc.


# ---------------------------------------------------------------------------
# Abstract provider interface
# ---------------------------------------------------------------------------


class DataProvider(ABC):
    """Abstract base class for all market data providers.

    Implementing a new provider requires:
    1. Subclass DataProvider
    2. Implement all abstract methods
    3. Register with provider_registry
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider name (e.g., 'yahoo', 'polygon')."""
        ...

    @abstractmethod
    async def get_quote(self, ticker: str) -> QuoteData:
        """Get current price, volume, market cap, and day changes."""
        ...

    @abstractmethod
    async def get_historical_prices(self, ticker: str, period: str = "1y") -> list[PriceBar]:
        """Get daily OHLCV bars for the given period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)."""
        ...

    @abstractmethod
    async def get_financials(self, ticker: str) -> FinancialStatements:
        """Get multi-year income statement, balance sheet, and cash flow data."""
        ...

    @abstractmethod
    async def get_company_info(self, ticker: str) -> CompanyInfo:
        """Get company profile: name, sector, industry, description, etc."""
        ...

    @abstractmethod
    async def search_companies(self, query: str) -> list[SearchResult]:
        """Search for companies by ticker or name."""
        ...

    @abstractmethod
    async def get_key_statistics(self, ticker: str) -> KeyStatistics:
        """Get valuation ratios: PE, PB, dividend yield, beta, etc."""
        ...
