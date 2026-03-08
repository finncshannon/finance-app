"""Revenue Growth Projection — Design Section 2.

Pure computation, no I/O. Takes CompanyDataPackage, returns RevenueProjection.
"""

from __future__ import annotations

import logging
import math
import statistics

from .constants import (
    ANALYST_WEIGHT_DEFAULT,
    CAGR_WINDOWS,
    DECLINING_INDUSTRIES,
    DEFAULT_TERMINAL_RATE,
    DIVERGENCE_THRESHOLD,
    HIGH_GROWTH_INDUSTRIES,
    LAMBDA_BY_REGIME,
    MIN_YEARS_LONG_WINDOW,
    REGIME_HIGH,
    REGIME_HYPERGROWTH,
    REGIME_MODERATE,
    REGIME_STABLE,
    TERMINAL_RATE_CEILING,
    TERMINAL_RATE_FLOOR,
)
from .helpers import clamp, compute_cagr, weighted_average
from .models import CompanyDataPackage, RevenueProjection

logger = logging.getLogger("finance_app")


def project_revenue(data: CompanyDataPackage, trial_params=None) -> RevenueProjection:
    """Generate 5-year revenue growth projections.

    Implements the full 6-step algorithm from Design Section 2.
    """
    financials = data.annual_financials  # oldest→newest
    revenues = [r.get("revenue") for r in financials]

    # Step 1 — Multi-Window CAGR
    outlier_years = None
    if trial_params is not None and trial_params.outlier_mask is not None:
        outlier_years = trial_params.outlier_mask
    cagrs, yoy_rates = _compute_cagrs_and_yoy(revenues, outlier_years=outlier_years)
    growth_volatility = statistics.stdev(yoy_rates) if len(yoy_rates) >= 2 else 0.0
    growth_trend = _compute_growth_trend(yoy_rates)

    # Step 2 — Divergence Detection
    divergence_flag, divergence_type = _detect_divergence(cagrs)

    # Step 3 — Regime Classification
    cagr_3yr = cagrs.get(3)
    regime = _classify_regime(cagr_3yr)

    # Check regime transition (regime at year[-3] vs year[-1])
    regime_transition = _check_regime_transition(revenues)

    # Step 4 — Terminal Growth Rate
    terminal_rate = _compute_terminal_rate(
        data.company_profile.industry,
        data.company_profile.market_cap,
        regime,
    )

    # Step 5 — Analyst Consensus Integration
    analyst_near_term, analyst_weight = _integrate_analyst(
        data.analyst_estimates, revenues,
    )

    # Step 6 — Base Case Growth Curve
    starting_growth, base_growth_rates = _build_growth_curve(
        cagrs=cagrs,
        regime=regime,
        regime_transition=regime_transition,
        terminal_rate=terminal_rate,
        analyst_near_term=analyst_near_term,
        analyst_weight=analyst_weight,
        yoy_rates=yoy_rates,
        years_available=data.years_available,
        trial_params=trial_params,
    )

    return RevenueProjection(
        base_growth_rates=base_growth_rates,
        terminal_growth_rate=terminal_rate,
        regime=regime,
        regime_transition=regime_transition,
        starting_growth_rate=starting_growth,
        historical_cagrs=cagrs,
        growth_volatility=round(growth_volatility, 4),
        analyst_available=analyst_near_term is not None,
        divergence_flag=divergence_flag,
        divergence_type=divergence_type,
    )


# ---------------------------------------------------------------------------
# Step 1 — Multi-Window CAGR
# ---------------------------------------------------------------------------

def _compute_cagrs_and_yoy(
    revenues: list[float | None],
    outlier_years: list[int] | None = None,
) -> tuple[dict[int, float], list[float]]:
    """Compute CAGRs for each window and YoY growth rates.

    revenues: oldest→newest.
    If outlier_years is provided, exclude those fiscal year indices from YoY computation.
    """
    # Filter out outlier fiscal years if specified
    if outlier_years is not None:
        filtered_revenues = [
            r for i, r in enumerate(revenues) if i not in outlier_years
        ]
    else:
        filtered_revenues = revenues

    n = len(filtered_revenues)
    cagrs: dict[int, float] = {}

    for w in CAGR_WINDOWS:
        if n >= w + 1:
            start_val = filtered_revenues[-(w + 1)]
            end_val = filtered_revenues[-1]
            c = compute_cagr(start_val, end_val, w)
            if c is not None:
                cagrs[w] = round(c, 4)
        elif n >= 3:
            # Use max available window
            max_w = n - 1
            start_val = filtered_revenues[0]
            end_val = filtered_revenues[-1]
            c = compute_cagr(start_val, end_val, max_w)
            if c is not None:
                cagrs[max_w] = round(c, 4)
            break  # only compute once for available window

    # YoY growth rates
    yoy: list[float] = []
    for i in range(1, n):
        prev = filtered_revenues[i - 1]
        curr = filtered_revenues[i]
        if prev is not None and curr is not None and prev > 0:
            yoy.append((curr - prev) / prev)
        elif prev is not None and curr is not None and prev < 0:
            # Revenue negative — exclude from CAGR, use YoY if surrounding valid
            yoy.append((curr - prev) / abs(prev))
        # Skip if revenue is 0 or None

    return cagrs, yoy


def _compute_growth_trend(yoy_rates: list[float]) -> float:
    """Slope of linear regression on YoY growth rates."""
    if len(yoy_rates) < 3:
        return 0.0
    from .helpers import linear_regression
    x = list(range(len(yoy_rates)))
    try:
        slope, _, _ = linear_regression(x, yoy_rates)
        return slope
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# Step 2 — Divergence Detection
# ---------------------------------------------------------------------------

def _detect_divergence(
    cagrs: dict[int, float],
) -> tuple[bool, str | None]:
    """Compare shortest and longest CAGRs for divergence."""
    if len(cagrs) < 2:
        return False, None

    windows = sorted(cagrs.keys())
    shortest = cagrs[windows[0]]
    longest = cagrs[windows[-1]]

    divergence = shortest - longest
    if abs(divergence) > DIVERGENCE_THRESHOLD:
        div_type = "accelerating" if divergence > 0 else "decelerating"
        logger.info(
            "Revenue divergence detected: %s (short=%.3f, long=%.3f)",
            div_type, shortest, longest,
        )
        return True, div_type

    return False, None


# ---------------------------------------------------------------------------
# Step 3 — Regime Classification
# ---------------------------------------------------------------------------

def _classify_regime(cagr_3yr: float | None) -> str:
    """Classify growth regime from 3-year CAGR."""
    if cagr_3yr is None:
        return "stable"
    if cagr_3yr > REGIME_HYPERGROWTH:
        return "hypergrowth"
    if cagr_3yr > REGIME_HIGH:
        return "high"
    if cagr_3yr > REGIME_MODERATE:
        return "moderate"
    if cagr_3yr >= REGIME_STABLE:
        return "stable"
    return "decline"


def _check_regime_transition(revenues: list[float | None]) -> bool:
    """Check if regime changed between 3 years ago and now."""
    n = len(revenues)
    if n < 6:
        return False

    # CAGR ending at year[-3] (3yr window ending 3 positions back)
    end_old = n - 3
    if end_old < 4:
        return False

    cagr_old = compute_cagr(revenues[end_old - 3], revenues[end_old], 3)
    cagr_new = compute_cagr(revenues[-4], revenues[-1], 3)

    if cagr_old is None or cagr_new is None:
        return False

    regime_old = _classify_regime(cagr_old)
    regime_new = _classify_regime(cagr_new)

    if regime_old != regime_new:
        logger.info("Regime transition: %s → %s", regime_old, regime_new)
        return True
    return False


# ---------------------------------------------------------------------------
# Step 4 — Terminal Growth Rate
# ---------------------------------------------------------------------------

def _compute_terminal_rate(
    industry: str,
    market_cap: float | None,
    regime: str,
) -> float:
    """Compute terminal growth rate with adjustments."""
    terminal = DEFAULT_TERMINAL_RATE

    # Industry adjustment
    if industry in HIGH_GROWTH_INDUSTRIES:
        terminal += 0.01
    elif industry in DECLINING_INDUSTRIES:
        terminal -= 0.01

    # Market cap adjustment
    if market_cap is not None:
        if market_cap > 500_000_000_000:  # >$500B mega-cap
            terminal = min(terminal, 0.025)
        elif market_cap < 2_000_000_000:  # <$2B small-cap
            terminal += 0.005

    # Regime: decline → reduce
    if regime == "decline":
        terminal = max(0, terminal - 0.01)

    return round(clamp(terminal, TERMINAL_RATE_FLOOR, TERMINAL_RATE_CEILING), 4)


# ---------------------------------------------------------------------------
# Step 5 — Analyst Consensus Integration
# ---------------------------------------------------------------------------

def _integrate_analyst(
    estimates,
    revenues: list[float | None],
) -> tuple[float | None, float]:
    """Extract analyst near-term growth estimate and weight."""
    # Direct revenue growth estimate
    if estimates.revenue_growth_estimate is not None:
        return estimates.revenue_growth_estimate, ANALYST_WEIGHT_DEFAULT

    # Derive from next year estimate
    if estimates.revenue_estimate_next_year is not None and revenues:
        last_rev = revenues[-1]
        if last_rev and last_rev > 0:
            implied = (estimates.revenue_estimate_next_year - last_rev) / last_rev
            return implied, 0.30

    return None, 0.0


# ---------------------------------------------------------------------------
# Step 6 — Base Case Growth Curve (Exponential Decay)
# ---------------------------------------------------------------------------

def _build_growth_curve(
    cagrs: dict[int, float],
    regime: str,
    regime_transition: bool,
    terminal_rate: float,
    analyst_near_term: float | None,
    analyst_weight: float,
    yoy_rates: list[float],
    years_available: int,
    trial_params=None,
) -> tuple[float, list[float]]:
    """Build 5-year growth curve using exponential decay to terminal.

    Returns (starting_growth_rate, [yr1, yr2, yr3, yr4, yr5]).
    """
    # Historical anchor: weighted average of available CAGRs
    cagr_values: list[float | None] = []
    cagr_weights: list[float] = []

    # Ordered by preference: 3yr, 5yr, 10yr
    if trial_params is not None and trial_params.regression_window_weights is not None:
        weight_map = trial_params.regression_window_weights
    else:
        weight_map = {3: 0.50, 5: 0.35, 10: 0.15}
    for w in CAGR_WINDOWS:
        if w in cagrs:
            cagr_values.append(cagrs[w])
            cagr_weights.append(weight_map[w])
        else:
            # Check if there's a non-standard window
            for k in sorted(cagrs.keys()):
                if k not in [3, 5, 10] and k not in [v for v, _ in zip(cagr_values, cagr_weights)]:
                    cagr_values.append(cagrs[k])
                    cagr_weights.append(weight_map.get(w, 0.35))
                    break

    historical_anchor = weighted_average(cagr_values, cagr_weights)
    if historical_anchor is None:
        # Fallback to simple average of YoY rates
        historical_anchor = statistics.mean(yoy_rates) if yoy_rates else 0.03

    # Blend with analyst estimate
    if analyst_near_term is not None:
        # Cap wild analyst estimates
        if yoy_rates:
            p80 = sorted(yoy_rates)[int(len(yoy_rates) * 0.8)] if len(yoy_rates) >= 5 else max(yoy_rates)
            if analyst_near_term > 1.0:
                analyst_near_term = min(analyst_near_term, p80)

        starting_growth = (
            analyst_weight * analyst_near_term
            + (1 - analyst_weight) * historical_anchor
        )
    else:
        starting_growth = historical_anchor

    # Lambda (fade speed)
    lambda_ = LAMBDA_BY_REGIME.get(regime, 0.35)
    if regime_transition:
        lambda_ *= 1.20

    # Sustained hypergrowth: reduce lambda by 15%
    hypergrowth_years = sum(1 for r in yoy_rates[-5:] if r > REGIME_HYPERGROWTH)
    if hypergrowth_years >= 5:
        lambda_ *= 0.85

    # MC trial jitter: scale lambda
    if trial_params is not None:
        lambda_ *= trial_params.fade_lambda_scale

    # Build fade curve
    base_growth_rates: list[float] = []
    for t in range(1, 6):
        g_t = terminal_rate + (starting_growth - terminal_rate) * math.exp(-lambda_ * t)
        base_growth_rates.append(round(g_t, 4))

    # Analyst near-term override for years 1-2
    if analyst_near_term is not None:
        base_growth_rates[0] = round(
            0.70 * analyst_near_term + 0.30 * base_growth_rates[0], 4
        )
        # Year 2: if we have implied year 2 growth, blend
        if analyst_weight >= 0.30:
            implied_yr2 = analyst_near_term * 0.85  # dampened
            base_growth_rates[1] = round(
                0.40 * implied_yr2 + 0.60 * base_growth_rates[1], 4
            )

    # Edge case: only 3 years of data — widen scenario spread +25%
    # (handled in scenarios.py, but mark starting growth)

    # Edge case: all growth rates negative — ensure terminal is non-negative
    if all(g < 0 for g in base_growth_rates):
        terminal_rate = max(0, terminal_rate)

    return round(starting_growth, 4), base_growth_rates
