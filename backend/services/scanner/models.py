"""Pydantic models for the Scanner service."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# =========================================================================
# Filter Operators
# =========================================================================

class FilterOperator(str, Enum):
    GT = "gt"              # >
    GTE = "gte"            # >=
    LT = "lt"              # <
    LTE = "lte"            # <=
    EQ = "eq"              # ==
    NEQ = "neq"            # !=
    BETWEEN = "between"    # BETWEEN low AND high
    IN = "in_list"         # IN (...)
    TOP_PCT = "top_pct"    # Top N% (percentile)
    BOTTOM_PCT = "bot_pct" # Bottom N% (percentile)


OPERATOR_SQL = {
    FilterOperator.GT: ">",
    FilterOperator.GTE: ">=",
    FilterOperator.LT: "<",
    FilterOperator.LTE: "<=",
    FilterOperator.EQ: "=",
    FilterOperator.NEQ: "!=",
}


# =========================================================================
# Request / Response Models
# =========================================================================

class ScannerFilter(BaseModel):
    """A single metric filter rule."""
    metric: str                          # key from SCANNER_METRICS
    operator: FilterOperator
    value: float | None = None           # for gt/gte/lt/lte/eq/neq
    low: float | None = None             # for between
    high: float | None = None            # for between
    values: list[str] | None = None      # for in_list
    percentile: float | None = None      # for top_pct / bot_pct (0-100)


class RankingWeight(BaseModel):
    """Weight for composite ranking."""
    metric: str
    weight: float = 1.0
    ascending: bool = False  # False = higher is better


class ScannerRequest(BaseModel):
    """Combined screen request: filters + optional text search."""
    filters: list[ScannerFilter] = Field(default_factory=list)
    text_query: str | None = None
    form_types: list[str] = Field(default_factory=lambda: ["10-K"])
    sector_filter: str | None = None     # GICS sector or "All"
    industry_filter: str | None = None
    universe: str = "all"                # "all", "r3000", "sp500", etc.
    sort_by: str | None = None           # metric key
    sort_desc: bool = True
    limit: int = 100
    offset: int = 0


class RankRequest(BaseModel):
    """Composite ranking request."""
    tickers: list[str] | None = None     # None = use full universe
    weights: list[RankingWeight]
    limit: int = 50


class TextSearchRequest(BaseModel):
    """Filing text search request."""
    query: str
    form_types: list[str] = Field(default_factory=lambda: ["10-K"])
    tickers: list[str] | None = None
    limit: int = 50


class PresetSaveRequest(BaseModel):
    """Save a scanner preset."""
    name: str
    filters: list[ScannerFilter] = Field(default_factory=list)
    text_query: str | None = None
    sector_filter: str | None = None
    universe: str = "all"
    form_types: list[str] = Field(default_factory=lambda: ["10-K"])


# =========================================================================
# Result Models
# =========================================================================

class ScannerRow(BaseModel):
    """A single row in scanner results."""
    ticker: str
    company_name: str | None = None
    sector: str | None = None
    industry: str | None = None
    metrics: dict[str, float | None] = Field(default_factory=dict)
    rank: int | None = None
    composite_score: float | None = None


class TextSearchHit(BaseModel):
    """A single filing text search match."""
    ticker: str
    company_name: str | None = None
    form_type: str | None = None
    filing_date: str | None = None
    section_title: str | None = None
    snippet: str = ""
    word_count: int | None = None


class ScannerResult(BaseModel):
    """Full scanner response."""
    rows: list[ScannerRow] = Field(default_factory=list)
    total_matches: int = 0
    text_hits: list[TextSearchHit] = Field(default_factory=list)
    text_hit_count: int = 0
    applied_filters: int = 0
    universe_size: int = 0
    computation_time_ms: int = 0


class RankResult(BaseModel):
    """Composite ranking response."""
    rows: list[ScannerRow] = Field(default_factory=list)
    total: int = 0
    weights_applied: list[RankingWeight] = Field(default_factory=list)


class MetricDefinition(BaseModel):
    """Describes a single scannable metric."""
    key: str
    label: str
    category: str
    db_table: str
    db_column: str
    format: str = "number"       # number, percent, currency, ratio
    description: str = ""
