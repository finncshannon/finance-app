"""Margin Projection — Design Section 3.

4-lens approach: trend, mean reversion, sector gravity, management guidance.
Pure computation, no I/O.
"""

from __future__ import annotations

import logging
import statistics

from .constants import (
    BROAD_MARKET_MEDIAN,
    MARGIN_CEILINGS,
    MARGIN_FLOOR,
    MEAN_REVERSION_YEARS,
    MIN_YEARS_FOR_REGRESSION,
    OUTLIER_Z_THRESHOLD,
    SECTOR_CONVERGENCE_YEARS,
    WEIGHT_PROFILE_GROWTH,
    WEIGHT_PROFILE_LIMITED_DATA,
    WEIGHT_PROFILE_STABLE,
    WEIGHT_PROFILE_TURNAROUND,
)
from .helpers import clamp, linear_regression, z_score_filter
from .models import CompanyDataPackage, MarginLensResult

logger = logging.getLogger("finance_app")

# Mapping from margin type to the financial fields used
_MARGIN_FIELDS = {
    "gross": ("gross_profit", "revenue"),
    "operating": ("ebit", "revenue"),
    "ebitda": ("ebitda", "revenue"),
    "net": ("net_income", "revenue"),
    "fcf": ("free_cash_flow", "revenue"),
}

# Mapping from margin type to industry benchmark field
_BENCHMARK_FIELDS = {
    "gross": "median_gross_margin",
    "operating": "median_operating_margin",
    "ebitda": "median_ebitda_margin",
    "net": "median_net_margin",
    "fcf": "median_fcf_margin",
}


def project_margins(
    data: CompanyDataPackage,
    regime: str,
    trial_params=None,
) -> dict[str, MarginLensResult]:
    """Project 5 margin types using the 4-lens approach.

    Returns dict keyed by margin type ("gross", "operating", etc.).
    """
    results: dict[str, MarginLensResult] = {}

    for margin_type in _MARGIN_FIELDS:
        results[margin_type] = _project_single_margin(
            data=data,
            margin_type=margin_type,
            regime=regime,
            trial_params=trial_params,
        )

    return results


def _project_single_margin(
    data: CompanyDataPackage,
    margin_type: str,
    regime: str,
    trial_params=None,
) -> MarginLensResult:
    """Project a single margin type through 4 lenses and synthesize."""
    numerator_field, denominator_field = _MARGIN_FIELDS[margin_type]
    ceiling = MARGIN_CEILINGS[margin_type]

    # Extract historical margin values (oldest→newest)
    raw_margins: list[float | None] = []
    fiscal_years: list[int] = []
    for row in data.annual_financials:
        num = row.get(numerator_field)
        den = row.get(denominator_field)
        if num is not None and den is not None and den != 0:
            raw_margins.append(num / den)
        else:
            raw_margins.append(None)
        fiscal_years.append(row.get("fiscal_year", 0))

    # Industry median
    benchmark_field = _BENCHMARK_FIELDS[margin_type]
    industry_median = getattr(data.industry_benchmarks, benchmark_field, None)
    if industry_median is None:
        industry_median = BROAD_MARKET_MEDIAN.get(margin_type)

    # Edge case: all None → flat projection at industry median
    clean_values = [v for v in raw_margins if v is not None]
    if not clean_values:
        flat = industry_median if industry_median is not None else BROAD_MARKET_MEDIAN[margin_type]
        return MarginLensResult(
            margin_type=margin_type,
            projections=[round(flat, 4)] * 5,
            weights_used={"trend": 0, "mean_reversion": 0, "sector": 1.0, "guidance": 0},
            industry_median=industry_median,
        )

    n_points = len(clean_values)
    current_margin = clean_values[-1]
    historical_mean = statistics.mean(clean_values)

    # Step 1 — Outlier Detection
    filtered = z_score_filter(raw_margins, OUTLIER_Z_THRESHOLD)
    outlier_years = [
        fiscal_years[i] for i in range(len(raw_margins))
        if raw_margins[i] is not None and filtered[i] is None
    ]

    # Step 2 — Lens 1: Historical Trend
    trend_projections, trend_r2 = _lens_trend(
        filtered, ceiling, n_points,
    )

    # Step 3 — Lens 2: Mean Reversion
    mr_convergence = MEAN_REVERSION_YEARS
    sc_convergence = SECTOR_CONVERGENCE_YEARS
    if trial_params is not None and trial_params.margin_convergence_years is not None:
        mr_convergence = trial_params.margin_convergence_years
        sc_convergence = trial_params.margin_convergence_years

    mean_rev_projections = _lens_mean_reversion(
        current_margin, historical_mean, ceiling,
        convergence_years=mr_convergence,
    )

    # Step 4 — Lens 3: Sector/Industry Gravity
    sector_projections = _lens_sector_gravity(
        current_margin, industry_median, ceiling,
        convergence_years=sc_convergence,
    )

    # Step 5 — Lens 4: Management Guidance (stub)
    guidance_projections: list[float] = []

    # Step 6 — Weight Profile Selection
    weights = _select_weight_profile(
        n_points=n_points,
        regime=regime,
        current_margin=current_margin,
        industry_median=industry_median,
        trend_r2=trend_r2,
        trial_params=trial_params,
    )

    # Step 7 — Weighted Synthesis
    projections: list[float] = []
    for t in range(5):
        trend_val = trend_projections[t] if t < len(trend_projections) else current_margin
        mr_val = mean_rev_projections[t] if t < len(mean_rev_projections) else current_margin
        sector_val = sector_projections[t] if t < len(sector_projections) else current_margin

        blended = (
            trend_val * weights["trend"]
            + mr_val * weights["mean_reversion"]
            + sector_val * weights["sector"]
        )
        blended = clamp(blended, MARGIN_FLOOR, ceiling)
        projections.append(round(blended, 4))

    return MarginLensResult(
        margin_type=margin_type,
        projections=projections,
        lens_outputs={
            "trend": [round(v, 4) for v in trend_projections],
            "mean_reversion": [round(v, 4) for v in mean_rev_projections],
            "sector": [round(v, 4) for v in sector_projections],
        },
        weights_used=weights,
        trend_r_squared=trend_r2,
        outlier_years=outlier_years,
        current_margin=round(current_margin, 4),
        historical_mean=round(historical_mean, 4),
        industry_median=round(industry_median, 4) if industry_median is not None else None,
    )


# ---------------------------------------------------------------------------
# Lens implementations
# ---------------------------------------------------------------------------

def _lens_trend(
    filtered_margins: list[float | None],
    ceiling: float,
    n_points: int,
) -> tuple[list[float], float | None]:
    """Lens 1: OLS trend extrapolation."""
    # Build x, y arrays from non-None values
    x_vals: list[float] = []
    y_vals: list[float] = []
    for i, v in enumerate(filtered_margins):
        if v is not None:
            x_vals.append(float(i))
            y_vals.append(v)

    if len(x_vals) < 2:
        # Not enough data for regression — flat at last value
        last = y_vals[-1] if y_vals else 0.0
        return [clamp(last, MARGIN_FLOOR, ceiling)] * 5, None

    if n_points >= MIN_YEARS_FOR_REGRESSION:
        slope, intercept, r2 = linear_regression(x_vals, y_vals)
        n = len(filtered_margins)
        projections = []
        for t in range(1, 6):
            projected = intercept + slope * (n - 1 + t)
            projections.append(clamp(projected, MARGIN_FLOOR, ceiling))
        return projections, r2
    else:
        # Flat projection at last-3-year average
        recent = [v for v in filtered_margins[-3:] if v is not None]
        avg = statistics.mean(recent) if recent else 0.0
        return [clamp(avg, MARGIN_FLOOR, ceiling)] * 5, None


def _lens_mean_reversion(
    current: float,
    historical_mean: float,
    ceiling: float,
    convergence_years: int | None = None,
) -> list[float]:
    """Lens 2: Linear convergence to historical mean over convergence_years."""
    years = convergence_years if convergence_years is not None else MEAN_REVERSION_YEARS
    projections: list[float] = []
    for t in range(1, 6):
        factor = min(t / years, 1.0)
        projected = current + (historical_mean - current) * factor
        projections.append(clamp(projected, MARGIN_FLOOR, ceiling))
    return projections


def _lens_sector_gravity(
    current: float,
    industry_median: float | None,
    ceiling: float,
    convergence_years: int | None = None,
) -> list[float]:
    """Lens 3: Convergence toward industry median over convergence_years."""
    if industry_median is None:
        return [clamp(current, MARGIN_FLOOR, ceiling)] * 5

    years = convergence_years if convergence_years is not None else SECTOR_CONVERGENCE_YEARS
    projections: list[float] = []
    for t in range(1, 6):
        factor = min(t / years, 1.0)
        projected = current + (industry_median - current) * factor
        projections.append(clamp(projected, MARGIN_FLOOR, ceiling))
    return projections


# ---------------------------------------------------------------------------
# Weight profile selection
# ---------------------------------------------------------------------------

def _select_weight_profile(
    n_points: int,
    regime: str,
    current_margin: float,
    industry_median: float | None,
    trend_r2: float | None,
    trial_params=None,
) -> dict[str, float]:
    """Select and adjust weight profile based on data characteristics."""
    if n_points < MIN_YEARS_FOR_REGRESSION:
        weights = dict(WEIGHT_PROFILE_LIMITED_DATA)
    elif regime in ("hypergrowth", "high"):
        weights = dict(WEIGHT_PROFILE_GROWTH)
    elif (
        industry_median is not None
        and current_margin < industry_median
        and current_margin < 0
    ):
        # Declining margin below industry median → turnaround
        weights = dict(WEIGHT_PROFILE_TURNAROUND)
    else:
        weights = dict(WEIGHT_PROFILE_STABLE)

    # MC trial override: set sector weight from trial_params
    if trial_params is not None and trial_params.industry_weight is not None:
        weights["sector"] = trial_params.industry_weight

    # Low trend confidence: shift weight from trend to sector
    if trend_r2 is not None and trend_r2 < 0.3:
        shift = weights["trend"] / 2
        weights["trend"] -= shift
        weights["sector"] += shift

    # Renormalize (guidance always 0 for MVP)
    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}

    return {k: round(v, 4) for k, v in weights.items()}
