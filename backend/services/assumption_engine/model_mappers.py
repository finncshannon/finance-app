"""Model-Specific Assumption Mappings — Design Section 6.

Maps synthesized projections into model-specific assumption structures.
Pure computation, no I/O.
"""

from __future__ import annotations

import logging
import statistics

from .constants import BROAD_MARKET_DEFAULTS
from .helpers import clamp, compute_cagr, safe_div
from .models import (
    CompanyDataPackage,
    CompsAssumptions,
    DCFAssumptions,
    DDMAssumptions,
    ModelAssumptions,
    RevenueBasedAssumptions,
    RevenueProjection,
    ScenarioProjections,
    WACCResult,
)

logger = logging.getLogger("finance_app")


def map_all_models(
    data: CompanyDataPackage,
    base_scenario: ScenarioProjections,
    revenue: RevenueProjection,
    wacc_result: WACCResult,
) -> ModelAssumptions:
    """Map base scenario to all 4 model-specific assumption sets."""
    return ModelAssumptions(
        dcf=map_dcf(data, base_scenario, wacc_result),
        ddm=map_ddm(data, base_scenario, revenue, wacc_result),
        comps=map_comps(data, revenue),
        revenue_based=map_revenue_based(data, base_scenario, revenue, wacc_result),
    )


# ---------------------------------------------------------------------------
# DCF
# ---------------------------------------------------------------------------

def map_dcf(
    data: CompanyDataPackage,
    base: ScenarioProjections,
    wacc_result: WACCResult,
) -> DCFAssumptions:
    """Map to DCF model assumptions."""
    latest = data.annual_financials[-1] if data.annual_financials else {}

    # CapEx to revenue: average of last 3 years (try both field names)
    capex_ratio = _avg_ratio_multi(
        data.annual_financials, ["capex", "capital_expenditure"], "revenue", 3, default=0.05,
    )
    # Depreciation to revenue
    depr_ratio = _avg_ratio(data.annual_financials, "depreciation", "revenue", 3,
                            default=capex_ratio * 0.8)

    # NWC change to revenue
    nwc_ratio = base.nwc_change_to_revenue

    # Terminal exit multiple
    ev_ebitda = data.quote_data.ev_to_ebitda
    if ev_ebitda is None or ev_ebitda <= 0:
        bm = data.industry_benchmarks.median_ev_ebitda
        ev_ebitda = bm if bm and bm > 0 else 12.0

    # Net debt
    total_debt = latest.get("total_debt") or 0
    cash = latest.get("cash_and_equivalents") or 0
    net_debt = total_debt - cash

    return DCFAssumptions(
        projection_years=5,
        revenue_growth_rates=base.revenue_growth_rates,
        operating_margins=base.operating_margins,
        tax_rate=base.tax_rate,
        wacc=base.wacc,
        terminal_growth_rate=base.terminal_growth_rate,
        capex_to_revenue=round(capex_ratio, 4),
        depreciation_to_revenue=round(depr_ratio, 4),
        nwc_change_to_revenue=round(nwc_ratio, 4),
        terminal_method="perpetuity_growth",
        terminal_exit_multiple=round(ev_ebitda, 2),
        shares_outstanding=latest.get("shares_outstanding"),
        net_debt=round(net_debt, 2) if net_debt else None,
        base_revenue=latest.get("revenue"),
    )


# ---------------------------------------------------------------------------
# DDM
# ---------------------------------------------------------------------------

def map_ddm(
    data: CompanyDataPackage,
    base: ScenarioProjections,
    revenue: RevenueProjection,
    wacc_result: WACCResult,
) -> DDMAssumptions | None:
    """Map to DDM assumptions. Returns None if not a dividend payer."""
    latest = data.annual_financials[-1] if data.annual_financials else {}

    dividends_paid = latest.get("dividends_paid")
    shares = latest.get("shares_outstanding")

    if not dividends_paid or not shares or shares <= 0:
        return None
    if abs(dividends_paid) == 0:
        return None

    current_dps = abs(dividends_paid) / shares

    # Dividend CAGR (from financials)
    div_cagr = _compute_dividend_cagr(data.annual_financials)

    # Near-term dividend growth: min of div CAGR and base revenue growth
    near_term = min(
        div_cagr if div_cagr is not None else base.revenue_growth_rates[0],
        base.revenue_growth_rates[0],
    )

    # Terminal dividend growth: min of terminal rate and 4%
    terminal_div = min(revenue.terminal_growth_rate, 0.04)

    # Payout ratio
    net_income = latest.get("net_income")
    payout_current = safe_div(abs(dividends_paid), net_income) if net_income and net_income > 0 else None

    # Model type
    diff = abs(near_term - terminal_div)
    model_type = "gordon" if diff < 0.02 else "two_stage"

    return DDMAssumptions(
        current_annual_dividend_per_share=round(current_dps, 4),
        dividend_growth_rate_near_term=round(near_term, 4),
        dividend_growth_rate_terminal=round(terminal_div, 4),
        cost_of_equity=wacc_result.cost_of_equity,
        payout_ratio_current=round(payout_current, 4) if payout_current else None,
        payout_ratio_projected=round(payout_current * 0.95, 4) if payout_current else None,
        model_type=model_type,
        shares_outstanding=shares,
    )


# ---------------------------------------------------------------------------
# Comps
# ---------------------------------------------------------------------------

def map_comps(
    data: CompanyDataPackage,
    revenue: RevenueProjection,
) -> CompsAssumptions:
    """Map to comparable company analysis assumptions."""
    latest = data.annual_financials[-1] if data.annual_financials else {}
    quote = data.quote_data

    # Applicable multiples (only positive values)
    multiples: dict[str, float] = {}
    if quote.trailing_pe and quote.trailing_pe > 0:
        multiples["PE"] = round(quote.trailing_pe, 2)
    if quote.ev_to_ebitda and quote.ev_to_ebitda > 0:
        multiples["EV/EBITDA"] = round(quote.ev_to_ebitda, 2)
    if quote.ev_to_revenue and quote.ev_to_revenue > 0:
        multiples["P/S"] = round(quote.ev_to_revenue, 2)
    if quote.price_to_book and quote.price_to_book > 0:
        multiples["P/B"] = round(quote.price_to_book, 2)

    # Peer selection criteria
    market_cap = quote.market_cap or data.company_profile.market_cap or 0
    base_revenue = latest.get("revenue") or 0
    criteria = {
        "sector": data.company_profile.sector,
        "industry": data.company_profile.industry,
        "market_cap_range": [round(market_cap * 0.33, 0), round(market_cap * 3, 0)],
        "revenue_range": [round(base_revenue * 0.25, 0), round(base_revenue * 4, 0)],
    }

    # Premium/discount per multiple based on growth differential
    growth_rate = revenue.base_growth_rates[0] if revenue.base_growth_rates else 0
    industry_growth = data.industry_benchmarks.median_revenue_growth or 0.05
    growth_diff = growth_rate - industry_growth

    premium: dict[str, float] = {}
    multipliers = {"PE": 5.0, "EV/EBITDA": 3.0, "P/S": 4.0, "P/B": 1.0}
    for mult_name in multiples:
        if mult_name in multipliers:
            raw = growth_diff * multipliers[mult_name]
            premium[mult_name] = round(clamp(raw, -0.30, 0.50), 4)

    return CompsAssumptions(
        applicable_multiples=multiples,
        peer_selection_criteria=criteria,
        premium_discount=premium,
    )


# ---------------------------------------------------------------------------
# Revenue-Based
# ---------------------------------------------------------------------------

def map_revenue_based(
    data: CompanyDataPackage,
    base: ScenarioProjections,
    revenue: RevenueProjection,
    wacc_result: WACCResult,
) -> RevenueBasedAssumptions:
    """Map to revenue-based valuation assumptions."""
    latest = data.annual_financials[-1] if data.annual_financials else {}
    quote = data.quote_data

    base_revenue = latest.get("revenue")
    current_ev_revenue = quote.ev_to_revenue

    # If current EV/Revenue not available, compute
    if current_ev_revenue is None or current_ev_revenue <= 0:
        ev = quote.enterprise_value
        if ev and base_revenue and base_revenue > 0:
            current_ev_revenue = ev / base_revenue
        else:
            current_ev_revenue = data.industry_benchmarks.median_ps or 2.0

    # Terminal EV/Revenue: blend current and industry
    industry_ps = data.industry_benchmarks.median_ps or 2.0
    terminal_ev_revenue = 0.3 * current_ev_revenue + 0.7 * industry_ps

    # Growth-adjusted multiple
    growth_rate = revenue.base_growth_rates[0] if revenue.base_growth_rates else 0
    growth_adjusted = None
    if growth_rate > 0.01:
        growth_adjusted = round(current_ev_revenue / (growth_rate * 100), 4)

    # Net debt
    total_debt = latest.get("total_debt") or 0
    cash = latest.get("cash_and_equivalents") or 0
    net_debt = total_debt - cash

    return RevenueBasedAssumptions(
        base_revenue=base_revenue,
        revenue_growth_rates=base.revenue_growth_rates,
        current_ev_revenue=round(current_ev_revenue, 4) if current_ev_revenue else None,
        terminal_ev_revenue=round(terminal_ev_revenue, 4),
        growth_adjusted_multiple=growth_adjusted,
        enterprise_value=quote.enterprise_value,
        net_debt=round(net_debt, 2) if net_debt else None,
        shares_outstanding=latest.get("shares_outstanding"),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _avg_ratio(
    financials: list[dict],
    numerator_field: str,
    denominator_field: str,
    years: int,
    default: float,
) -> float:
    """Average of numerator/denominator over last N years."""
    ratios: list[float] = []
    for row in financials[-years:]:
        num = row.get(numerator_field)
        den = row.get(denominator_field)
        if num is not None and den and den > 0:
            ratios.append(abs(num) / den)

    return statistics.mean(ratios) if ratios else default


def _avg_ratio_multi(
    financials: list[dict],
    numerator_fields: list[str],
    denominator_field: str,
    years: int,
    default: float,
) -> float:
    """Average of numerator/denominator, trying multiple numerator field names."""
    ratios: list[float] = []
    for row in financials[-years:]:
        num = None
        for field in numerator_fields:
            num = row.get(field)
            if num is not None:
                break
        den = row.get(denominator_field)
        if num is not None and den and den > 0:
            ratios.append(abs(num) / den)

    return statistics.mean(ratios) if ratios else default


def _compute_dividend_cagr(financials: list[dict]) -> float | None:
    """Compute CAGR of dividends paid over available history."""
    divs = []
    for row in financials:
        d = row.get("dividends_paid")
        if d is not None and d != 0:
            divs.append(abs(d))

    if len(divs) < 2:
        return None

    return compute_cagr(divs[0], divs[-1], len(divs) - 1)
