"""Reasoning Generation — template-based explanation strings.

Produces human-readable reasoning for each assumption category.
Pure computation, no I/O.
"""

from __future__ import annotations

from .models import (
    CompanyDataPackage,
    MarginLensResult,
    RevenueProjection,
    ScenarioSet,
    WACCResult,
)


def generate_reasoning(
    data: CompanyDataPackage,
    revenue: RevenueProjection,
    margins: dict[str, MarginLensResult],
    wacc_result: WACCResult,
    scenarios: ScenarioSet,
) -> dict[str, str]:
    """Generate reasoning strings keyed by assumption category."""
    ticker = data.ticker
    reasoning: dict[str, str] = {}

    # Revenue
    reasoning["revenue_growth"] = _revenue_reasoning(ticker, revenue, data)

    # Margins
    for mtype, result in margins.items():
        reasoning[f"{mtype}_margin"] = _margin_reasoning(ticker, result)

    # WACC
    reasoning["wacc"] = _wacc_reasoning(ticker, wacc_result)

    # Terminal growth
    reasoning["terminal_growth"] = _terminal_reasoning(ticker, revenue, data)

    # Scenarios
    reasoning["scenarios"] = _scenario_reasoning(ticker, scenarios)

    return reasoning


# ---------------------------------------------------------------------------
# Template builders
# ---------------------------------------------------------------------------

def _revenue_reasoning(
    ticker: str,
    revenue: RevenueProjection,
    data: CompanyDataPackage,
) -> str:
    """Build revenue growth reasoning."""
    parts: list[str] = []

    # Regime
    regime_labels = {
        "hypergrowth": "hypergrowth (>30% CAGR)",
        "high": "high growth (15–30% CAGR)",
        "moderate": "moderate growth (5–15% CAGR)",
        "stable": "stable growth (0–5% CAGR)",
        "decline": "declining revenue",
    }
    parts.append(
        f"{ticker} is classified as {regime_labels.get(revenue.regime, revenue.regime)}"
    )

    # CAGRs
    if revenue.historical_cagrs:
        cagr_strs = [f"{w}Y: {c:.1%}" for w, c in sorted(revenue.historical_cagrs.items())]
        parts.append(f"Historical CAGRs: {', '.join(cagr_strs)}")

    # Divergence
    if revenue.divergence_flag:
        parts.append(
            f"Growth is {revenue.divergence_type} — "
            f"recent trends diverge from long-term history"
        )

    # Analyst
    if revenue.analyst_available:
        parts.append("Analyst consensus is blended into near-term projections")

    # Starting → terminal
    parts.append(
        f"Growth fades from {revenue.starting_growth_rate:.1%} "
        f"to terminal rate of {revenue.terminal_growth_rate:.1%} "
        f"using exponential decay"
    )

    return ". ".join(parts) + "."


def _margin_reasoning(ticker: str, result: MarginLensResult) -> str:
    """Build margin reasoning for a single margin type."""
    parts: list[str] = []

    label = result.margin_type.replace("_", " ").title()

    if result.current_margin is not None:
        parts.append(f"Current {label.lower()} margin: {result.current_margin:.1%}")

    if result.historical_mean is not None:
        parts.append(f"historical average: {result.historical_mean:.1%}")

    if result.industry_median is not None:
        parts.append(f"industry median: {result.industry_median:.1%}")

    # Weights used
    dominant = max(result.weights_used, key=result.weights_used.get) if result.weights_used else "trend"
    parts.append(f"Projection weighted primarily toward {dominant.replace('_', ' ')}")

    if result.outlier_years:
        parts.append(
            f"{len(result.outlier_years)} outlier year(s) excluded from analysis"
        )

    proj_start = result.projections[0] if result.projections else 0
    proj_end = result.projections[-1] if result.projections else 0
    parts.append(f"Projects from {proj_start:.1%} to {proj_end:.1%} over 5 years")

    return ". ".join(parts) + "."


def _wacc_reasoning(ticker: str, wacc: WACCResult) -> str:
    """Build WACC reasoning."""
    parts: list[str] = []

    parts.append(
        f"WACC of {wacc.wacc:.1%} derived from CAPM "
        f"(Rf={wacc.risk_free_rate:.1%}, β={wacc.adjusted_beta:.2f}, "
        f"ERP={wacc.erp:.1%}, size premium={wacc.size_premium:.1%})"
    )

    parts.append(
        f"Cost of equity: {wacc.cost_of_equity:.1%}"
    )

    if wacc.weight_debt > 0:
        parts.append(
            f"Capital structure: {wacc.weight_equity:.0%} equity / "
            f"{wacc.weight_debt:.0%} debt"
        )
        parts.append(
            f"After-tax cost of debt: {wacc.cost_of_debt_after_tax:.1%}"
        )
    else:
        parts.append("All-equity capital structure assumed")

    if wacc.warnings:
        parts.append(f"Notes: {'; '.join(wacc.warnings)}")

    return ". ".join(parts) + "."


def _terminal_reasoning(
    ticker: str,
    revenue: RevenueProjection,
    data: CompanyDataPackage,
) -> str:
    """Build terminal growth rate reasoning."""
    rate = revenue.terminal_growth_rate

    parts = [f"Terminal growth rate set at {rate:.1%}"]

    if rate == 0.025:
        parts.append("based on long-term GDP growth proxy")
    elif rate > 0.025:
        parts.append("adjusted upward for growth industry or small-cap premium")
    elif rate < 0.025:
        parts.append("adjusted downward for declining industry or mega-cap constraint")

    if data.company_profile.market_cap and data.company_profile.market_cap > 500e9:
        parts.append("capped at 2.5% for mega-cap")

    return ". ".join(parts) + "."


def _scenario_reasoning(ticker: str, scenarios: ScenarioSet) -> str:
    """Build scenario spread reasoning."""
    u = scenarios.uncertainty_score
    s = scenarios.spread

    level = "low" if u < 0.35 else ("moderate" if u <= 0.65 else "high")

    return (
        f"Uncertainty score of {u:.2f} ({level}) produces a scenario spread "
        f"of {s:.1%}. Base case weighted at {scenarios.base.scenario_weight:.0%}, "
        f"bull at {scenarios.bull.scenario_weight:.0%}, "
        f"bear at {scenarios.bear.scenario_weight:.0%}."
    )
