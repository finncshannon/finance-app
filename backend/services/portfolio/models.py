"""Pydantic models for the Portfolio service."""

from __future__ import annotations

from pydantic import BaseModel, Field


# =========================================================================
# Account
# =========================================================================

class AccountCreate(BaseModel):
    name: str
    account_type: str = "taxable"
    is_default: bool = False


class Account(BaseModel):
    id: int
    name: str
    account_type: str
    is_default: bool
    created_at: str


# =========================================================================
# Position
# =========================================================================

class PositionCreate(BaseModel):
    ticker: str
    shares: float
    cost_basis_per_share: float
    date_acquired: str = ""
    account: str = "Manual"
    notes: str | None = None


class Position(BaseModel):
    id: int
    ticker: str
    company_name: str | None = None
    shares_held: float
    cost_basis_per_share: float | None = None
    current_price: float | None = None
    market_value: float | None = None
    total_cost: float | None = None
    gain_loss: float | None = None
    gain_loss_pct: float | None = None
    day_change: float | None = None
    day_change_pct: float | None = None
    weight: float | None = None
    sector: str | None = None
    industry: str | None = None
    account: str = "Manual"
    added_at: str = ""
    lots: list[Lot] = Field(default_factory=list)


# =========================================================================
# Lot
# =========================================================================

class Lot(BaseModel):
    id: int
    position_id: int
    shares: float
    cost_basis_per_share: float
    date_acquired: str
    date_sold: str | None = None
    sale_price: float | None = None
    realized_gain: float | None = None
    holding_period_days: int | None = None
    is_long_term: bool | None = None
    lot_method: str | None = None
    notes: str | None = None


# =========================================================================
# Transaction
# =========================================================================

class TransactionCreate(BaseModel):
    ticker: str
    transaction_type: str  # BUY, SELL, DIVIDEND, DRIP, SPLIT, ADJUSTMENT
    shares: float | None = None
    price_per_share: float | None = None
    total_amount: float | None = None
    transaction_date: str
    account: str | None = None
    fees: float = 0
    notes: str | None = None
    lot_method: str = "fifo"
    specific_lot_ids: list[int] | None = None


class Transaction(BaseModel):
    id: int
    ticker: str
    transaction_type: str
    shares: float | None = None
    price_per_share: float | None = None
    total_amount: float | None = None
    transaction_date: str
    account: str | None = None
    fees: float = 0
    notes: str | None = None
    created_at: str = ""


# =========================================================================
# Price Alert
# =========================================================================

class AlertCreate(BaseModel):
    ticker: str
    alert_type: str  # price_above, price_below, pct_change, intrinsic_cross
    threshold: float


class Alert(BaseModel):
    id: int
    ticker: str
    alert_type: str
    threshold: float
    is_active: bool = True
    triggered_at: str | None = None
    created_at: str = ""
    current_price: float | None = None


# =========================================================================
# Summary & Performance
# =========================================================================

class PortfolioSummary(BaseModel):
    total_value: float = 0
    total_cost: float = 0
    total_gain_loss: float = 0
    total_gain_loss_pct: float = 0
    day_change: float = 0
    day_change_pct: float = 0
    position_count: int = 0
    account_count: int = 0
    weighted_dividend_yield: float | None = None


class DailySnapshot(BaseModel):
    date: str
    portfolio_value: float
    cash_flow: float = 0


class CashFlow(BaseModel):
    date: str
    amount: float


class PerformanceResult(BaseModel):
    twr: dict[str, float | None] = Field(default_factory=dict)
    mwrr: float | None = None
    mwrr_annualized: float | None = None
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    max_drawdown: float | None = None
    beta: float | None = None
    volatility: float | None = None
    tracking_error: float | None = None
    information_ratio: float | None = None
    daily_values: list[DailySnapshot] = Field(default_factory=list)


# =========================================================================
# Benchmark & Attribution
# =========================================================================

class BenchmarkResult(BaseModel):
    benchmark_ticker: str = "SPY"
    periods: dict[str, dict] = Field(default_factory=dict)
    portfolio_series: list[DailySnapshot] = Field(default_factory=list)
    benchmark_series: list[DailySnapshot] = Field(default_factory=list)


class SectorAttribution(BaseModel):
    sector: str
    port_weight: float
    bench_weight: float
    port_return: float
    bench_return: float
    allocation_effect: float
    selection_effect: float
    interaction_effect: float


class AttributionResult(BaseModel):
    sectors: list[SectorAttribution] = Field(default_factory=list)
    total_allocation: float = 0
    total_selection: float = 0
    total_interaction: float = 0
    total_alpha: float = 0


# =========================================================================
# CSV Import
# =========================================================================

class ImportPreview(BaseModel):
    positions: list[PositionCreate] = Field(default_factory=list)
    account_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    row_count: int = 0


class ImportResult(BaseModel):
    imported: int = 0
    skipped: int = 0
    warnings: list[str] = Field(default_factory=list)


# =========================================================================
# Income
# =========================================================================

class IncomeResult(BaseModel):
    total_annual_income: float = 0
    total_monthly_income: float = 0
    weighted_yield: float | None = None
    positions: list[dict] = Field(default_factory=list)
