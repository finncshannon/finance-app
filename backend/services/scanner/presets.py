"""Built-in scanner presets.

Six predefined screening strategies that can be loaded as starting points.
"""

from __future__ import annotations

from .models import ScannerFilter, FilterOperator


# =========================================================================
# Built-in presets
# =========================================================================

BUILT_IN_PRESETS: list[dict] = [
    {
        "name": "Value Stocks",
        "description": "Classic value: low P/E, low P/B, positive earnings",
        "filters": [
            ScannerFilter(metric="pe_trailing", operator=FilterOperator.LTE, value=15.0),
            ScannerFilter(metric="price_to_book", operator=FilterOperator.LTE, value=2.0),
            ScannerFilter(metric="net_income", operator=FilterOperator.GT, value=0),
            ScannerFilter(metric="debt_to_equity", operator=FilterOperator.LTE, value=1.5),
        ],
        "sector_filter": None,
        "universe": "all",
    },
    {
        "name": "Growth Stocks",
        "description": "High revenue growth, expanding margins",
        "filters": [
            ScannerFilter(metric="revenue_growth", operator=FilterOperator.GTE, value=0.15),
            ScannerFilter(metric="gross_margin", operator=FilterOperator.GTE, value=0.40),
            ScannerFilter(metric="revenue", operator=FilterOperator.GTE, value=500_000_000),
        ],
        "sector_filter": None,
        "universe": "all",
    },
    {
        "name": "Dividend Champions",
        "description": "High-yield, sustainable payout, consistent dividends",
        "filters": [
            ScannerFilter(metric="dividend_yield", operator=FilterOperator.GTE, value=0.025),
            ScannerFilter(metric="payout_ratio", operator=FilterOperator.LTE, value=0.80),
            ScannerFilter(metric="payout_ratio", operator=FilterOperator.GT, value=0),
            ScannerFilter(metric="free_cash_flow", operator=FilterOperator.GT, value=0),
        ],
        "sector_filter": None,
        "universe": "all",
    },
    {
        "name": "Quality Growth",
        "description": "GARP: reasonable valuation with strong fundamentals",
        "filters": [
            ScannerFilter(metric="pe_trailing", operator=FilterOperator.LTE, value=25.0),
            ScannerFilter(metric="revenue_growth", operator=FilterOperator.GTE, value=0.08),
            ScannerFilter(metric="roe", operator=FilterOperator.GTE, value=0.12),
            ScannerFilter(metric="debt_to_equity", operator=FilterOperator.LTE, value=1.0),
        ],
        "sector_filter": None,
        "universe": "all",
    },
    {
        "name": "Turnaround Candidates",
        "description": "Beaten-down stocks with improving cash flow",
        "filters": [
            ScannerFilter(metric="price_to_book", operator=FilterOperator.LTE, value=1.0),
            ScannerFilter(metric="operating_cash_flow", operator=FilterOperator.GT, value=0),
            ScannerFilter(metric="net_margin", operator=FilterOperator.LT, value=0.05),
        ],
        "sector_filter": None,
        "universe": "all",
    },
    {
        "name": "Small-Cap Value",
        "description": "Small caps trading below intrinsic value signals",
        "filters": [
            ScannerFilter(metric="market_cap", operator=FilterOperator.BETWEEN, low=300_000_000, high=2_000_000_000),
            ScannerFilter(metric="pe_trailing", operator=FilterOperator.LTE, value=18.0),
            ScannerFilter(metric="price_to_book", operator=FilterOperator.LTE, value=2.5),
            ScannerFilter(metric="free_cash_flow", operator=FilterOperator.GT, value=0),
        ],
        "sector_filter": None,
        "universe": "all",
    },
]


def get_built_in_presets() -> list[dict]:
    """Return built-in presets as serializable dicts."""
    result = []
    for preset in BUILT_IN_PRESETS:
        result.append({
            "id": None,
            "name": preset["name"],
            "description": preset.get("description", ""),
            "is_built_in": True,
            "filters": [f.model_dump() for f in preset["filters"]],
            "sector_filter": preset.get("sector_filter"),
            "universe": preset.get("universe", "all"),
            "form_types": ["10-K"],
        })
    return result
