"""Scenario Generation — Design Section 5.

Generates bull/base/bear scenarios from revenue, margin, and WACC projections.
Pure computation, no I/O.
"""

from __future__ import annotations

import logging
import statistics

from .constants import (
    DEFAULT_WEIGHTS_HIGH_UNCERTAINTY,
    DEFAULT_WEIGHTS_LOW_UNCERTAINTY,
    DEFAULT_WEIGHTS_MED_UNCERTAINTY,
    MARGIN_OPERATING_LEVERAGE,
    MAX_SPREAD,
    MIN_SPREAD,
    TERMINAL_RATE_CEILING,
    TERMINAL_RATE_FLOOR,
    UNCERTAINTY_WEIGHTS,
    WACC_BEAR_PREMIUM,
    WACC_BULL_DISCOUNT,
    WACC_CEILING,
    WACC_FLOOR,
)
from .helpers import clamp
from .models import (
    CompanyDataPackage,
    MarginLensResult,
    RevenueProjection,
    ScenarioProjections,
    ScenarioSet,
    WACCResult,
)

logger = logging.getLogger("finance_app")


def generate_scenarios(
    data: CompanyDataPackage,
    revenue: RevenueProjection,
    margins: dict[str, MarginLensResult],
    wacc_result: WACCResult,
    capex_ratio: float,
    nwc_ratio: float,
) -> ScenarioSet:
    """Generate base, bull, and bear scenarios.

    Implements uncertainty scoring, spread determination, and consistency checks.
    """
    # Step 1 — Uncertainty Score
    uncertainty = _compute_uncertainty(data, revenue, margins, wacc_result)

    # Step 2 — Spread
    spread = _compute_spread(revenue.growth_volatility, uncertainty)
    margin_spread = spread * 0.5

    # Step 3–4 — Build scenarios
    base = _build_base_scenario(
        revenue, margins, wacc_result, capex_ratio, nwc_ratio, uncertainty,
    )
    bull = _build_bull_scenario(base, spread, margin_spread, revenue)
    bear = _build_bear_scenario(base, spread, margin_spread)

    # Step 5 — Internal Consistency Checks
    _enforce_consistency(base, bull, bear, wacc_result.wacc)

    # Step 6 — Probability Weights
    weights = _assign_weights(uncertainty)
    base.scenario_weight = weights["base"]
    bull.scenario_weight = weights["bull"]
    bear.scenario_weight = weights["bear"]

    return ScenarioSet(
        base=base,
        bull=bull,
        bear=bear,
        uncertainty_score=round(uncertainty, 4),
        spread=round(spread, 4),
    )


# ---------------------------------------------------------------------------
# Step 1 — Uncertainty Score
# ---------------------------------------------------------------------------

def _compute_uncertainty(
    data: CompanyDataPackage,
    revenue: RevenueProjection,
    margins: dict[str, MarginLensResult],
    wacc_result: WACCResult,
) -> float:
    """Compute 8-factor uncertainty score, each 0–1, weighted."""
    factors: dict[str, float] = {}

    # data_years
    yrs = data.years_available
    if yrs >= 10:
        factors["data_years"] = 0.1
    elif yrs >= 7:
        factors["data_years"] = 0.3
    elif yrs >= 5:
        factors["data_years"] = 0.5
    else:
        factors["data_years"] = 0.9

    # revenue_volatility
    vol = revenue.growth_volatility
    if vol < 0.05:
        factors["revenue_volatility"] = 0.1
    elif vol < 0.10:
        factors["revenue_volatility"] = 0.3
    elif vol < 0.20:
        factors["revenue_volatility"] = 0.5
    elif vol < 0.35:
        factors["revenue_volatility"] = 0.7
    else:
        factors["revenue_volatility"] = 0.9

    # margin_volatility (operating margin stdev)
    op_margins = margins.get("operating")
    if op_margins and op_margins.current_margin is not None:
        # Get raw operating margins from financials
        op_values = []
        for row in data.annual_financials:
            ebit = row.get("ebit")
            rev = row.get("revenue")
            if ebit is not None and rev and rev > 0:
                op_values.append(ebit / rev)
        if len(op_values) >= 3:
            op_stdev = statistics.stdev(op_values)
            factors["margin_volatility"] = clamp(op_stdev / 0.15, 0, 1)
        else:
            factors["margin_volatility"] = 0.5
    else:
        factors["margin_volatility"] = 0.5

    # growth_trend_consistency (1 - R² of revenue trend)
    op_result = margins.get("operating")
    trend_r2 = op_result.trend_r_squared if op_result else None
    if trend_r2 is not None:
        factors["growth_trend_consistency"] = 1.0 - clamp(trend_r2, 0, 1)
    else:
        factors["growth_trend_consistency"] = 0.5

    # analyst_coverage
    factors["analyst_coverage"] = 0.2 if revenue.analyst_available else 0.8

    # regime_transition
    factors["regime_transition"] = 0.8 if revenue.regime_transition else 0.2

    # leverage (D/E ratio)
    de = 0.0
    latest = data.annual_financials[-1] if data.annual_financials else {}
    debt = latest.get("total_debt") or 0
    equity = latest.get("stockholders_equity") or 1
    if equity > 0:
        de = debt / equity
    factors["leverage"] = clamp(de / 3.0, 0, 1)

    # divergence
    factors["divergence"] = 0.8 if revenue.divergence_flag else 0.2

    # Weighted sum
    score = sum(
        factors.get(k, 0.5) * w for k, w in UNCERTAINTY_WEIGHTS.items()
    )
    return clamp(score, 0, 1)


# ---------------------------------------------------------------------------
# Step 2 — Spread
# ---------------------------------------------------------------------------

def _compute_spread(growth_volatility: float, uncertainty: float) -> float:
    """Determine scenario spread from volatility and uncertainty."""
    base_spread = growth_volatility * 1.5
    spread = base_spread * (0.7 + 0.6 * uncertainty)
    return clamp(spread, MIN_SPREAD, MAX_SPREAD)


# ---------------------------------------------------------------------------
# Steps 3–4 — Build scenarios
# ---------------------------------------------------------------------------

def _build_base_scenario(
    revenue: RevenueProjection,
    margins: dict[str, MarginLensResult],
    wacc_result: WACCResult,
    capex_ratio: float,
    nwc_ratio: float,
    uncertainty: float,
) -> ScenarioProjections:
    """Build the base case scenario."""
    return ScenarioProjections(
        revenue_growth_rates=list(revenue.base_growth_rates),
        terminal_growth_rate=revenue.terminal_growth_rate,
        gross_margins=margins["gross"].projections,
        operating_margins=margins["operating"].projections,
        ebitda_margins=margins["ebitda"].projections,
        net_margins=margins["net"].projections,
        fcf_margins=margins["fcf"].projections,
        wacc=wacc_result.wacc,
        cost_of_equity=wacc_result.cost_of_equity,
        capex_to_revenue=capex_ratio,
        nwc_change_to_revenue=nwc_ratio,
        tax_rate=wacc_result.effective_tax_rate,
        scenario_weight=0.50,
    )


def _build_bull_scenario(
    base: ScenarioProjections,
    spread: float,
    margin_spread: float,
    revenue: RevenueProjection,
) -> ScenarioProjections:
    """Build bull scenario with upside adjustments."""
    # Revenue: base + spread, capped at starting_growth * 1.5
    cap = revenue.starting_growth_rate * 1.5
    bull_growth = [
        round(min(g + spread, cap), 4) for g in base.revenue_growth_rates
    ]

    # Terminal: +0.005, capped
    bull_terminal = min(
        base.terminal_growth_rate + 0.005, TERMINAL_RATE_CEILING,
    )

    # Margins: base + margin_spread * operating leverage
    ml = MARGIN_OPERATING_LEVERAGE
    bull_gross = [round(m + margin_spread * ml, 4) for m in base.gross_margins]
    bull_op = [round(m + margin_spread * ml, 4) for m in base.operating_margins]
    bull_ebitda = [round(m + margin_spread * ml, 4) for m in base.ebitda_margins]
    bull_net = [round(m + margin_spread * ml, 4) for m in base.net_margins]
    bull_fcf = [round(m + margin_spread * ml, 4) for m in base.fcf_margins]

    # WACC: base - discount
    bull_wacc = max(base.wacc - WACC_BULL_DISCOUNT, WACC_FLOOR)

    return ScenarioProjections(
        revenue_growth_rates=bull_growth,
        terminal_growth_rate=round(bull_terminal, 4),
        gross_margins=bull_gross,
        operating_margins=bull_op,
        ebitda_margins=bull_ebitda,
        net_margins=bull_net,
        fcf_margins=bull_fcf,
        wacc=round(bull_wacc, 4),
        cost_of_equity=round(base.cost_of_equity - WACC_BULL_DISCOUNT, 4),
        capex_to_revenue=base.capex_to_revenue,
        nwc_change_to_revenue=base.nwc_change_to_revenue,
        tax_rate=base.tax_rate,
        scenario_weight=0.25,
    )


def _build_bear_scenario(
    base: ScenarioProjections,
    spread: float,
    margin_spread: float,
) -> ScenarioProjections:
    """Build bear scenario with downside adjustments."""
    # Revenue: base - spread, floored at -0.15
    bear_growth = [
        round(max(g - spread, -0.15), 4) for g in base.revenue_growth_rates
    ]

    # Terminal: -0.005, floored
    bear_terminal = max(
        base.terminal_growth_rate - 0.005, TERMINAL_RATE_FLOOR,
    )

    # Margins: base - margin_spread
    bear_gross = [round(m - margin_spread, 4) for m in base.gross_margins]
    bear_op = [round(m - margin_spread, 4) for m in base.operating_margins]
    bear_ebitda = [round(m - margin_spread, 4) for m in base.ebitda_margins]
    bear_net = [round(m - margin_spread, 4) for m in base.net_margins]
    bear_fcf = [round(m - margin_spread, 4) for m in base.fcf_margins]

    # WACC: base + premium
    bear_wacc = min(base.wacc + WACC_BEAR_PREMIUM, WACC_CEILING)

    return ScenarioProjections(
        revenue_growth_rates=bear_growth,
        terminal_growth_rate=round(bear_terminal, 4),
        gross_margins=bear_gross,
        operating_margins=bear_op,
        ebitda_margins=bear_ebitda,
        net_margins=bear_net,
        fcf_margins=bear_fcf,
        wacc=round(bear_wacc, 4),
        cost_of_equity=round(base.cost_of_equity + WACC_BEAR_PREMIUM, 4),
        capex_to_revenue=base.capex_to_revenue,
        nwc_change_to_revenue=base.nwc_change_to_revenue,
        tax_rate=base.tax_rate,
        scenario_weight=0.25,
    )


# ---------------------------------------------------------------------------
# Step 5 — Consistency Checks
# ---------------------------------------------------------------------------

def _enforce_consistency(
    base: ScenarioProjections,
    bull: ScenarioProjections,
    bear: ScenarioProjections,
    base_wacc: float,
) -> None:
    """Enforce internal consistency across scenarios."""
    for i in range(5):
        # gross >= operating (each scenario)
        for scenario in (base, bull, bear):
            if scenario.gross_margins[i] < scenario.operating_margins[i]:
                scenario.operating_margins[i] = scenario.gross_margins[i]

    # terminal_growth < wacc
    for scenario in (base, bull, bear):
        if scenario.terminal_growth_rate >= scenario.wacc:
            scenario.terminal_growth_rate = round(scenario.wacc - 0.01, 4)
            logger.warning(
                "Terminal growth capped below WACC: %.4f",
                scenario.terminal_growth_rate,
            )

    # Bear revenue growth strictly <= base
    for i in range(5):
        if bear.revenue_growth_rates[i] > base.revenue_growth_rates[i]:
            bear.revenue_growth_rates[i] = base.revenue_growth_rates[i]


# ---------------------------------------------------------------------------
# Step 6 — Probability Weights
# ---------------------------------------------------------------------------

def _assign_weights(uncertainty: float) -> dict[str, float]:
    """Assign scenario probability weights from uncertainty level."""
    if uncertainty < 0.35:
        return dict(DEFAULT_WEIGHTS_LOW_UNCERTAINTY)
    elif uncertainty <= 0.65:
        return dict(DEFAULT_WEIGHTS_MED_UNCERTAINTY)
    else:
        return dict(DEFAULT_WEIGHTS_HIGH_UNCERTAINTY)
