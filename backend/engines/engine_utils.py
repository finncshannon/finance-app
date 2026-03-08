"""Shared utilities for valuation engines."""

from __future__ import annotations

import statistics


def discount_factor(wacc: float, year: float) -> float:
    """Discount factor at given year. Supports fractional years (mid-year convention)."""
    if wacc <= -1:
        return 0.0
    return 1.0 / (1 + wacc) ** year


def equity_bridge(
    enterprise_value: float,
    net_debt: float,
    minority_interest: float = 0.0,
    non_operating_assets: float = 0.0,
) -> float:
    """EV → Equity Value."""
    return enterprise_value - net_debt - minority_interest + non_operating_assets


def upside_downside(implied_price: float, current_price: float) -> float | None:
    """Percentage upside/downside vs current market price."""
    if current_price is None or current_price <= 0:
        return None
    return (implied_price / current_price) - 1.0


def extend_to_10_years(
    five_year_rates: list[float],
    terminal_value: float,
    fade_years: int = 5,
) -> list[float]:
    """Extend 5-year assumptions to 10 years via linear fade to terminal.

    Returns list of 10 values.
    """
    rates = list(five_year_rates[:5])

    # Pad if fewer than 5
    while len(rates) < 5:
        rates.append(rates[-1] if rates else terminal_value)

    year_5_value = rates[4]

    for t in range(fade_years):
        frac = (t + 1) / fade_years
        faded = year_5_value + (terminal_value - year_5_value) * frac
        rates.append(faded)

    return rates


def percentile(values: list[float], pct: float) -> float:
    """Compute percentile (0-100) of sorted values."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    k = (n - 1) * (pct / 100.0)
    f = int(k)
    c = f + 1
    if c >= n:
        return sorted_vals[-1]
    d = k - f
    return sorted_vals[f] + d * (sorted_vals[c] - sorted_vals[f])


def trimmed_mean(values: list[float], trim_pct: float = 0.10) -> float:
    """Compute trimmed mean, removing trim_pct from each end."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    trim_count = max(1, int(n * trim_pct))
    if trim_count * 2 >= n:
        return statistics.mean(sorted_vals)
    trimmed = sorted_vals[trim_count:-trim_count]
    return statistics.mean(trimmed) if trimmed else statistics.mean(sorted_vals)


def clamp(value: float, floor: float, ceiling: float) -> float:
    return max(floor, min(ceiling, value))


def safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b
