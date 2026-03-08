"""Data extraction service — computes 30+ financial metrics from cached data.

Reads from MarketDataRepo (financial_data + market_data tables) and computes
profitability, growth, valuation, leverage, and efficiency metrics. All
computations use safe division — individual metrics return None on error,
never raising exceptions.
"""

import logging
from typing import Any, Callable

from db.connection import DatabaseConnection
from repositories.market_data_repo import MarketDataRepo

logger = logging.getLogger("finance_app")

# Default corporate tax rate used for ROIC calculation
_DEFAULT_TAX_RATE = 0.21


# ---------------------------------------------------------------------------
# Safe math helpers
# ---------------------------------------------------------------------------

def _safe_div(a: float | None, b: float | None) -> float | None:
    """Divide a by b, returning None if either is None or b is zero."""
    if a is None or b is None or b == 0:
        return None
    return a / b


def _cagr(begin: float | None, end: float | None, years: int) -> float | None:
    """Compound annual growth rate from begin to end over N years."""
    if begin is None or end is None or years <= 0 or begin <= 0 or end <= 0:
        return None
    return (end / begin) ** (1 / years) - 1


def _validate_ratio(value: float | None, field_name: str, max_reasonable: float = 5.0) -> float | None:
    """Validate a ratio field is in decimal format. Warn if suspiciously high."""
    if value is None:
        return None
    if abs(value) > max_reasonable:
        logger.warning(
            "Suspicious ratio for %s: %.4f (expected < %.1f). Possible format mismatch.",
            field_name, value, max_reasonable,
        )
    return value


# ---------------------------------------------------------------------------
# Metric computation registry
# ---------------------------------------------------------------------------

# Each entry: metric_name -> (callable(fin_row, market_row) -> float|None, requires_market)
# fin_row: most-recent financial_data dict (or None)
# market_row: market_data dict (or None)

def _gross_margin(f: dict, _m: dict | None) -> float | None:
    return _validate_ratio(_safe_div(f.get("gross_profit"), f.get("revenue")), "gross_margin", 1.5)


def _operating_margin(f: dict, _m: dict | None) -> float | None:
    return _validate_ratio(_safe_div(f.get("ebit"), f.get("revenue")), "operating_margin", 1.5)


def _net_margin(f: dict, _m: dict | None) -> float | None:
    return _validate_ratio(_safe_div(f.get("net_income"), f.get("revenue")), "net_margin", 1.5)


def _ebitda_margin(f: dict, _m: dict | None) -> float | None:
    return _validate_ratio(_safe_div(f.get("ebitda"), f.get("revenue")), "ebitda_margin", 1.5)


def _fcf_margin(f: dict, _m: dict | None) -> float | None:
    return _validate_ratio(_safe_div(f.get("free_cash_flow"), f.get("revenue")), "fcf_margin", 1.5)


def _roe(f: dict, _m: dict | None) -> float | None:
    return _safe_div(f.get("net_income"), f.get("stockholders_equity"))


def _roa(f: dict, _m: dict | None) -> float | None:
    return _safe_div(f.get("net_income"), f.get("total_assets"))


def _roic(f: dict, _m: dict | None) -> float | None:
    ebit = f.get("ebit")
    total_debt = f.get("total_debt")
    equity = f.get("stockholders_equity")
    cash = f.get("cash_and_equivalents")
    if any(v is None for v in (ebit, total_debt, equity, cash)):
        return None
    invested_capital = total_debt + equity - cash
    if invested_capital == 0:
        return None
    return (ebit * (1 - _DEFAULT_TAX_RATE)) / invested_capital


def _debt_to_equity(f: dict, _m: dict | None) -> float | None:
    return _safe_div(f.get("total_debt"), f.get("stockholders_equity"))


def _net_debt_to_ebitda(f: dict, _m: dict | None) -> float | None:
    total_debt = f.get("total_debt")
    cash = f.get("cash_and_equivalents")
    ebitda = f.get("ebitda")
    if total_debt is None or cash is None:
        return None
    return _safe_div(total_debt - cash, ebitda)


def _interest_coverage(f: dict, _m: dict | None) -> float | None:
    return _safe_div(f.get("ebit"), f.get("interest_expense"))


def _debt_to_assets(f: dict, _m: dict | None) -> float | None:
    return _safe_div(f.get("total_debt"), f.get("total_assets"))


def _asset_turnover(f: dict, _m: dict | None) -> float | None:
    return _safe_div(f.get("revenue"), f.get("total_assets"))


# --- Valuation (require market_data) ---

def _pe_ratio(_f: dict, m: dict | None) -> float | None:
    return m.get("pe_trailing") if m else None


def _pe_forward(_f: dict, m: dict | None) -> float | None:
    return m.get("pe_forward") if m else None


def _price_to_book(_f: dict, m: dict | None) -> float | None:
    return m.get("price_to_book") if m else None


def _price_to_sales(_f: dict, m: dict | None) -> float | None:
    return m.get("price_to_sales") if m else None


def _ev_to_ebitda(_f: dict, m: dict | None) -> float | None:
    return m.get("ev_to_ebitda") if m else None


def _ev_to_revenue(_f: dict, m: dict | None) -> float | None:
    return m.get("ev_to_revenue") if m else None


def _fcf_yield(f: dict, m: dict | None) -> float | None:
    if m is None:
        return None
    return _safe_div(f.get("free_cash_flow"), m.get("market_cap"))


def _earnings_yield(f: dict, m: dict | None) -> float | None:
    if m is None:
        return None
    return _safe_div(f.get("eps_diluted"), m.get("current_price"))


def _dividend_yield(_f: dict, m: dict | None) -> float | None:
    return m.get("dividend_yield") if m else None


# Map of single-period metric names to their computation functions
_SINGLE_METRIC_FNS: dict[str, Callable] = {
    # Profitability
    "gross_margin": _gross_margin,
    "operating_margin": _operating_margin,
    "net_margin": _net_margin,
    "ebitda_margin": _ebitda_margin,
    "fcf_margin": _fcf_margin,
    "roe": _roe,
    "roa": _roa,
    "roic": _roic,
    # Leverage
    "debt_to_equity": _debt_to_equity,
    "net_debt_to_ebitda": _net_debt_to_ebitda,
    "interest_coverage": _interest_coverage,
    "debt_to_assets": _debt_to_assets,
    # Efficiency
    "asset_turnover": _asset_turnover,
    # Valuation
    "pe_ratio": _pe_ratio,
    "pe_forward": _pe_forward,
    "price_to_book": _price_to_book,
    "price_to_sales": _price_to_sales,
    "ev_to_ebitda": _ev_to_ebitda,
    "ev_to_revenue": _ev_to_revenue,
    "fcf_yield": _fcf_yield,
    "earnings_yield": _earnings_yield,
    "dividend_yield": _dividend_yield,
}


# ---------------------------------------------------------------------------
# Growth metric helpers (require multi-year data)
# ---------------------------------------------------------------------------

def _yoy_growth(financials: list[dict], field: str) -> float | None:
    """Year-over-year growth for *field*. financials sorted newest-first."""
    if len(financials) < 2:
        return None
    curr = financials[0].get(field)
    prev = financials[1].get(field)
    if curr is None or prev is None or prev == 0:
        return None
    return _validate_ratio((curr - prev) / abs(prev), f"{field}_growth_yoy", 10.0)


def _cagr_metric(financials: list[dict], field: str, years: int) -> float | None:
    """CAGR for *field* over *years*. Index 0 = most recent, index years = N years ago."""
    if len(financials) <= years:
        return None
    return _cagr(financials[years].get(field), financials[0].get(field), years)


# Growth metric name -> (callable(financials) -> float|None)
_GROWTH_METRIC_FNS: dict[str, Callable] = {
    "revenue_growth_yoy": lambda fins: _yoy_growth(fins, "revenue"),
    "net_income_growth_yoy": lambda fins: _yoy_growth(fins, "net_income"),
    "eps_growth_yoy": lambda fins: _yoy_growth(fins, "eps_diluted"),
    "ebitda_growth_yoy": lambda fins: _yoy_growth(fins, "ebitda"),
    "fcf_growth_yoy": lambda fins: _yoy_growth(fins, "free_cash_flow"),
    "revenue_cagr_3y": lambda fins: _cagr_metric(fins, "revenue", 3),
    "revenue_cagr_5y": lambda fins: _cagr_metric(fins, "revenue", 5),
    "eps_cagr_3y": lambda fins: _cagr_metric(fins, "eps_diluted", 3),
    "eps_cagr_5y": lambda fins: _cagr_metric(fins, "eps_diluted", 5),
}

# Complete set of all metric names
ALL_METRIC_NAMES: list[str] = list(_SINGLE_METRIC_FNS.keys()) + list(_GROWTH_METRIC_FNS.keys())


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class DataExtractionService:
    """Computes financial metrics from cached market and financial data.

    Uses MarketDataRepo for data access and MarketDataService to refresh
    stale or missing data on demand.
    """

    def __init__(self, db: DatabaseConnection, market_data_service: Any):
        self.market_repo = MarketDataRepo(db)
        self.market_svc = market_data_service

    # ------------------------------------------------------------------
    # Internal data loading
    # ------------------------------------------------------------------

    async def _load_data(
        self, ticker: str
    ) -> tuple[list[dict], dict | None]:
        """Load financial and market data, refreshing from provider if needed.

        Returns:
            (financials, market_data) where financials is sorted newest-first
            and market_data is a single dict or None.
        """
        ticker = ticker.upper()

        financials = await self.market_repo.get_financials(ticker)
        market = await self.market_repo.get_market_data(ticker)

        # If either is missing, try refreshing via the market data service
        if not financials or market is None:
            if not financials:
                logger.info("No cached financials for %s — refreshing", ticker)
                try:
                    await self.market_svc.get_financials(ticker)
                except Exception as exc:
                    logger.warning("Failed to refresh financials for %s: %s", ticker, exc)

            if market is None:
                logger.info("No cached market data for %s — refreshing", ticker)
                try:
                    await self.market_svc.get_quote(ticker)
                except Exception as exc:
                    logger.warning("Failed to refresh market data for %s: %s", ticker, exc)

            # Re-read after refresh attempts
            financials = await self.market_repo.get_financials(ticker)
            market = await self.market_repo.get_market_data(ticker)

        return financials, market

    # ------------------------------------------------------------------
    # Financial data helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_period_row(
        financials: list[dict], period: str
    ) -> dict | None:
        """Select the appropriate financial row for a given period.

        Args:
            financials: list of financial_data rows sorted by fiscal_year DESC.
            period: "TTM" (most recent), "annual" (same as TTM), or a year like "2023".

        Returns:
            A single financial_data dict or None.
        """
        if not financials:
            return None

        if period.upper() in ("TTM", "ANNUAL"):
            return financials[0]

        # Specific year
        try:
            target_year = int(period)
        except ValueError:
            logger.warning("Invalid period '%s' — expected TTM, annual, or a year", period)
            return None

        for row in financials:
            if row.get("fiscal_year") == target_year:
                return row
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_metric(
        self, ticker: str, metric_name: str, period: str = "TTM"
    ) -> float | None:
        """Get a single named metric for a ticker.

        Args:
            ticker: Stock ticker symbol.
            metric_name: One of the recognised metric names (see ALL_METRIC_NAMES).
            period: "TTM" (most recent annual), "annual", or a year like "2023".

        Returns:
            The computed metric value, or None if data is unavailable.
        """
        try:
            financials, market = await self._load_data(ticker)

            # Single-period metric
            if metric_name in _SINGLE_METRIC_FNS:
                fin_row = self._get_period_row(financials, period)
                if fin_row is None:
                    logger.warning("No financial data for %s period=%s", ticker, period)
                    return None
                return _SINGLE_METRIC_FNS[metric_name](fin_row, market)

            # Growth metric (needs multi-year data)
            if metric_name in _GROWTH_METRIC_FNS:
                if not financials:
                    return None
                return _GROWTH_METRIC_FNS[metric_name](financials)

            logger.warning("Unknown metric name: %s", metric_name)
            return None

        except Exception as exc:
            logger.error("Error computing metric %s for %s: %s", metric_name, ticker, exc)
            return None

    async def compute_all_metrics(self, ticker: str) -> dict[str, float | None]:
        """Compute every recognised metric for a ticker.

        Ensures data is loaded (refreshing via market_svc if needed) then
        runs all single-period and growth metric functions.

        Returns:
            Dict mapping metric names to computed values (or None).
        """
        result: dict[str, float | None] = {}

        try:
            financials, market = await self._load_data(ticker)
            fin_row = financials[0] if financials else None

            # Single-period metrics
            for name, fn in _SINGLE_METRIC_FNS.items():
                try:
                    result[name] = fn(fin_row, market) if fin_row else None
                except Exception as exc:
                    logger.warning("Error computing %s for %s: %s", name, ticker, exc)
                    result[name] = None

            # Growth metrics
            for name, fn in _GROWTH_METRIC_FNS.items():
                try:
                    result[name] = fn(financials) if financials else None
                except Exception as exc:
                    logger.warning("Error computing %s for %s: %s", name, ticker, exc)
                    result[name] = None

        except Exception as exc:
            logger.error("Error loading data for %s: %s", ticker, exc)
            # Return dict with all keys set to None
            for name in ALL_METRIC_NAMES:
                result[name] = None

        return result

    async def get_metric_history(
        self, ticker: str, metric_name: str, years: int = 5
    ) -> list[dict]:
        """Get a metric's value across multiple fiscal years.

        Args:
            ticker: Stock ticker symbol.
            metric_name: One of the recognised metric names.
            years: Number of historical years to return (default 5).

        Returns:
            List of dicts like [{"fiscal_year": 2024, "value": 0.467}, ...]
            sorted by fiscal_year descending (newest first).
        """
        try:
            financials, market = await self._load_data(ticker)
            if not financials:
                return []

            history: list[dict] = []

            if metric_name in _SINGLE_METRIC_FNS:
                fn = _SINGLE_METRIC_FNS[metric_name]
                for row in financials[:years]:
                    fiscal_year = row.get("fiscal_year")
                    try:
                        value = fn(row, market)
                    except Exception:
                        value = None
                    history.append({"fiscal_year": fiscal_year, "value": value})

            elif metric_name in _GROWTH_METRIC_FNS:
                # Growth metrics need adjacent years, compute per-year
                # For YoY metrics, we need pairs; for CAGR, we need deeper history
                # We compute the metric at each point in the series
                if "yoy" in metric_name:
                    # YoY growth: compute for each consecutive pair
                    field_map = {
                        "revenue_growth_yoy": "revenue",
                        "net_income_growth_yoy": "net_income",
                        "eps_growth_yoy": "eps_diluted",
                        "ebitda_growth_yoy": "ebitda",
                        "fcf_growth_yoy": "free_cash_flow",
                    }
                    field = field_map.get(metric_name)
                    if field:
                        for i in range(min(years, len(financials) - 1)):
                            curr = financials[i].get(field)
                            prev = financials[i + 1].get(field)
                            if curr is not None and prev is not None and prev != 0:
                                value = (curr - prev) / abs(prev)
                            else:
                                value = None
                            history.append({
                                "fiscal_year": financials[i].get("fiscal_year"),
                                "value": value,
                            })
                elif "cagr" in metric_name:
                    # CAGR metrics: compute rolling CAGR at each point
                    field_map = {
                        "revenue_cagr_3y": ("revenue", 3),
                        "revenue_cagr_5y": ("revenue", 5),
                        "eps_cagr_3y": ("eps_diluted", 3),
                        "eps_cagr_5y": ("eps_diluted", 5),
                    }
                    field, n = field_map.get(metric_name, (None, 0))
                    if field:
                        for i in range(min(years, len(financials) - n)):
                            value = _cagr(
                                financials[i + n].get(field),
                                financials[i].get(field),
                                n,
                            )
                            history.append({
                                "fiscal_year": financials[i].get("fiscal_year"),
                                "value": value,
                            })
            else:
                logger.warning("Unknown metric name for history: %s", metric_name)

            return history

        except Exception as exc:
            logger.error(
                "Error computing metric history %s for %s: %s",
                metric_name, ticker, exc,
            )
            return []
