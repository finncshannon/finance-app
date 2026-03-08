"""Pure helper functions — no I/O, no side effects."""

from __future__ import annotations

import math
import statistics


def clamp(value: float, floor: float, ceiling: float) -> float:
    """Clamp *value* between *floor* and *ceiling*."""
    return max(floor, min(ceiling, value))


def weighted_average(
    values: list[float | None],
    weights: list[float],
) -> float | None:
    """Weighted average that skips None values and renormalizes weights.

    Returns None if no valid values remain.
    """
    pairs = [(v, w) for v, w in zip(values, weights) if v is not None]
    if not pairs:
        return None
    total_weight = sum(w for _, w in pairs)
    if total_weight == 0:
        return None
    return sum(v * w for v, w in pairs) / total_weight


def linear_regression(
    x: list[float], y: list[float],
) -> tuple[float, float, float]:
    """Ordinary least squares regression.

    Returns (slope, intercept, r_squared).
    Raises ValueError if fewer than 2 data points.
    """
    n = len(x)
    if n < 2:
        raise ValueError("Need at least 2 data points for regression")

    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)

    ss_xy = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    ss_xx = sum((xi - x_mean) ** 2 for xi in x)
    ss_yy = sum((yi - y_mean) ** 2 for yi in y)

    if ss_xx == 0:
        return 0.0, y_mean, 0.0

    slope = ss_xy / ss_xx
    intercept = y_mean - slope * x_mean

    if ss_yy == 0:
        r_squared = 1.0  # all y values identical
    else:
        r_squared = (ss_xy ** 2) / (ss_xx * ss_yy)

    return slope, intercept, clamp(r_squared, 0.0, 1.0)


def compute_cagr(
    start_value: float | None,
    end_value: float | None,
    years: int,
) -> float | None:
    """Compound annual growth rate. Returns None if start_value <= 0."""
    if start_value is None or end_value is None or years <= 0:
        return None
    if start_value <= 0 or end_value <= 0:
        return None
    return (end_value / start_value) ** (1.0 / years) - 1.0


def compute_nwc_changes(annual_financials: list[dict]) -> list[float]:
    """Compute year-over-year net working capital changes.

    NWC = current_assets - current_liabilities.
    Returns list of NWC change / revenue ratios (oldest→newest).
    financials must be sorted oldest→newest.
    """
    changes: list[float] = []
    for i in range(1, len(annual_financials)):
        prev = annual_financials[i - 1]
        curr = annual_financials[i]

        prev_nwc = _compute_nwc(prev)
        curr_nwc = _compute_nwc(curr)
        revenue = curr.get("revenue")

        if prev_nwc is not None and curr_nwc is not None and revenue and revenue > 0:
            changes.append((curr_nwc - prev_nwc) / revenue)

    return changes


def _compute_nwc(row: dict) -> float | None:
    """Compute net working capital from a financial row."""
    # Try explicit fields first
    current_assets = row.get("current_assets")
    current_liabilities = row.get("current_liabilities")

    if current_assets is not None and current_liabilities is not None:
        return current_assets - current_liabilities

    # Fallback: approximate from available fields
    # cash + receivables + inventory - payables - short_term_debt
    cash = row.get("cash_and_equivalents") or 0
    receivables = row.get("accounts_receivable") or 0
    inventory = row.get("inventory") or 0
    payables = row.get("accounts_payable") or 0
    short_debt = row.get("short_term_debt") or 0

    # Only return if we have at least cash
    if row.get("cash_and_equivalents") is not None:
        return cash + receivables + inventory - payables - short_debt

    return None


def safe_div(a: float | None, b: float | None) -> float | None:
    """Divide a by b, returning None if either is None or b is zero."""
    if a is None or b is None or b == 0:
        return None
    return a / b


def z_score_filter(
    values: list[float | None], threshold: float = 2.0,
) -> list[float | None]:
    """Replace outliers (|z| > threshold) with None. Preserves list length."""
    clean = [v for v in values if v is not None]
    if len(clean) < 3:
        return list(values)

    mean = statistics.mean(clean)
    stdev = statistics.stdev(clean)

    if stdev == 0:
        return list(values)

    result: list[float | None] = []
    for v in values:
        if v is not None and abs((v - mean) / stdev) > threshold:
            result.append(None)
        else:
            result.append(v)
    return result
