"""Scanner metric definitions — maps metric keys to DB columns.

Each metric maps to a table (financial_data via cache, market_data via cache,
or companies from user_data) and a column name.

Tables are accessed via the 'cache' schema prefix for cache DB tables:
    cache.financial_data, cache.market_data
And directly for user_data tables:
    companies
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricDef:
    key: str
    label: str
    category: str
    db_table: str       # "financial_data", "market_data", "companies"
    db_column: str
    format: str = "number"  # number, percent, currency, ratio, integer
    description: str = ""
    fiscal_year: str = "latest"  # "latest" = most recent fiscal year


# =========================================================================
# All metric definitions grouped by category
# =========================================================================

_METRIC_LIST: list[MetricDef] = [
    # =====================================================================
    # 1. VALUATION
    # =====================================================================
    MetricDef("pe_trailing", "P/E (Trailing)", "Valuation",
             "market_data", "pe_trailing", "ratio", "Trailing 12-month P/E"),
    MetricDef("pe_forward", "P/E (Forward)", "Valuation",
             "market_data", "pe_forward", "ratio", "Forward P/E estimate"),
    MetricDef("price_to_book", "P/B", "Valuation",
             "market_data", "price_to_book", "ratio", "Price to book value"),
    MetricDef("price_to_sales", "P/S", "Valuation",
             "market_data", "price_to_sales", "ratio", "Price to sales"),
    MetricDef("ev_to_revenue", "EV/Revenue", "Valuation",
             "market_data", "ev_to_revenue", "ratio", "Enterprise value to revenue"),
    MetricDef("ev_to_ebitda", "EV/EBITDA", "Valuation",
             "market_data", "ev_to_ebitda", "ratio", "Enterprise value to EBITDA"),
    MetricDef("dividend_yield", "Dividend Yield", "Valuation",
             "market_data", "dividend_yield", "percent", "Annual dividend yield"),

    # =====================================================================
    # 2. SIZE & MARKET
    # =====================================================================
    MetricDef("market_cap", "Market Cap", "Size",
             "market_data", "market_cap", "currency", "Market capitalization"),
    MetricDef("enterprise_value", "Enterprise Value", "Size",
             "market_data", "enterprise_value", "currency", "Enterprise value"),
    MetricDef("current_price", "Current Price", "Size",
             "market_data", "current_price", "currency", "Latest stock price"),
    MetricDef("volume", "Volume", "Size",
             "market_data", "volume", "integer", "Daily trading volume"),
    MetricDef("average_volume", "Avg Volume", "Size",
             "market_data", "average_volume", "integer", "Average daily volume"),
    MetricDef("beta", "Beta", "Size",
             "market_data", "beta", "ratio", "Beta coefficient"),

    # =====================================================================
    # 3. PRICE PERFORMANCE
    # =====================================================================
    MetricDef("day_change_pct", "Day Change %", "Price",
             "market_data", "day_change_pct", "percent", "Daily price change %"),
    MetricDef("fifty_two_week_high", "52W High", "Price",
             "market_data", "fifty_two_week_high", "currency", "52-week high price"),
    MetricDef("fifty_two_week_low", "52W Low", "Price",
             "market_data", "fifty_two_week_low", "currency", "52-week low price"),

    # =====================================================================
    # 4. INCOME STATEMENT
    # =====================================================================
    MetricDef("revenue", "Revenue", "Income Statement",
             "financial_data", "revenue", "currency", "Total revenue"),
    MetricDef("gross_profit", "Gross Profit", "Income Statement",
             "financial_data", "gross_profit", "currency"),
    MetricDef("ebit", "EBIT", "Income Statement",
             "financial_data", "ebit", "currency", "Earnings before interest & taxes"),
    MetricDef("ebitda", "EBITDA", "Income Statement",
             "financial_data", "ebitda", "currency"),
    MetricDef("net_income", "Net Income", "Income Statement",
             "financial_data", "net_income", "currency"),
    MetricDef("eps_diluted", "EPS (Diluted)", "Income Statement",
             "financial_data", "eps_diluted", "currency"),
    MetricDef("eps_basic", "EPS (Basic)", "Income Statement",
             "financial_data", "eps_basic", "currency"),
    MetricDef("rd_expense", "R&D Expense", "Income Statement",
             "financial_data", "rd_expense", "currency"),
    MetricDef("sga_expense", "SG&A Expense", "Income Statement",
             "financial_data", "sga_expense", "currency"),

    # =====================================================================
    # 5. MARGINS & PROFITABILITY
    # =====================================================================
    MetricDef("gross_margin", "Gross Margin", "Profitability",
             "financial_data", "gross_margin", "percent", "Gross profit / revenue"),
    MetricDef("operating_margin", "Operating Margin", "Profitability",
             "financial_data", "operating_margin", "percent", "EBIT / revenue"),
    MetricDef("net_margin", "Net Margin", "Profitability",
             "financial_data", "net_margin", "percent", "Net income / revenue"),
    MetricDef("ebitda_margin", "EBITDA Margin", "Profitability",
             "financial_data", "ebitda_margin", "percent"),
    MetricDef("fcf_margin", "FCF Margin", "Profitability",
             "financial_data", "fcf_margin", "percent", "Free cash flow / revenue"),
    MetricDef("roe", "ROE", "Profitability",
             "financial_data", "roe", "percent", "Return on equity"),

    # =====================================================================
    # 6. GROWTH
    # =====================================================================
    MetricDef("revenue_growth", "Revenue Growth", "Growth",
             "financial_data", "revenue_growth", "percent", "Year-over-year revenue growth"),

    # =====================================================================
    # 7. BALANCE SHEET
    # =====================================================================
    MetricDef("total_assets", "Total Assets", "Balance Sheet",
             "financial_data", "total_assets", "currency"),
    MetricDef("total_liabilities", "Total Liabilities", "Balance Sheet",
             "financial_data", "total_liabilities", "currency"),
    MetricDef("stockholders_equity", "Stockholders Equity", "Balance Sheet",
             "financial_data", "stockholders_equity", "currency"),
    MetricDef("current_assets", "Current Assets", "Balance Sheet",
             "financial_data", "current_assets", "currency"),
    MetricDef("current_liabilities", "Current Liabilities", "Balance Sheet",
             "financial_data", "current_liabilities", "currency"),
    MetricDef("long_term_debt", "Long-Term Debt", "Balance Sheet",
             "financial_data", "long_term_debt", "currency"),
    MetricDef("total_debt", "Total Debt", "Balance Sheet",
             "financial_data", "total_debt", "currency"),
    MetricDef("cash_and_equivalents", "Cash & Equivalents", "Balance Sheet",
             "financial_data", "cash_and_equivalents", "currency"),
    MetricDef("net_debt", "Net Debt", "Balance Sheet",
             "financial_data", "net_debt", "currency"),
    MetricDef("working_capital", "Working Capital", "Balance Sheet",
             "financial_data", "working_capital", "currency"),
    MetricDef("debt_to_equity", "Debt/Equity", "Balance Sheet",
             "financial_data", "debt_to_equity", "ratio"),
    MetricDef("shares_outstanding", "Shares Outstanding", "Balance Sheet",
             "financial_data", "shares_outstanding", "integer"),

    # =====================================================================
    # 8. CASH FLOW
    # =====================================================================
    MetricDef("operating_cash_flow", "Operating Cash Flow", "Cash Flow",
             "financial_data", "operating_cash_flow", "currency"),
    MetricDef("free_cash_flow", "Free Cash Flow", "Cash Flow",
             "financial_data", "free_cash_flow", "currency"),
    MetricDef("capital_expenditure", "CapEx", "Cash Flow",
             "financial_data", "capital_expenditure", "currency"),
    MetricDef("dividends_paid", "Dividends Paid", "Cash Flow",
             "financial_data", "dividends_paid", "currency"),
    MetricDef("payout_ratio", "Payout Ratio", "Cash Flow",
             "financial_data", "payout_ratio", "percent"),
    MetricDef("investing_cash_flow", "Investing Cash Flow", "Cash Flow",
             "financial_data", "investing_cash_flow", "currency"),
    MetricDef("financing_cash_flow", "Financing Cash Flow", "Cash Flow",
             "financial_data", "financing_cash_flow", "currency"),
    MetricDef("dividend_per_share", "Dividend Per Share", "Cash Flow",
             "financial_data", "dividend_per_share", "currency"),
]

# =========================================================================
# Lookup dict: metric_key → MetricDef
# =========================================================================

SCANNER_METRICS: dict[str, MetricDef] = {m.key: m for m in _METRIC_LIST}

# Category grouping for the frontend metrics picker
METRIC_CATEGORIES: dict[str, list[str]] = {}
for _m in _METRIC_LIST:
    METRIC_CATEGORIES.setdefault(_m.category, []).append(_m.key)


def get_metric(key: str) -> MetricDef | None:
    """Look up a metric definition by key."""
    return SCANNER_METRICS.get(key)


def list_metrics() -> list[dict]:
    """Return all metrics as serializable dicts for the API."""
    return [
        {
            "key": m.key,
            "label": m.label,
            "category": m.category,
            "format": m.format,
            "description": m.description,
        }
        for m in _METRIC_LIST
    ]


def list_categories() -> dict[str, list[str]]:
    """Return category → metric keys mapping."""
    return dict(METRIC_CATEGORIES)
