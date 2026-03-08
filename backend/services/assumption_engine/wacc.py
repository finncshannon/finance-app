"""WACC Calibration — Design Section 4.

Pure computation, no I/O.
"""

from __future__ import annotations

import logging

from .constants import (
    BLUME_WEIGHT_MARKET,
    BLUME_WEIGHT_RAW,
    DEFAULT_BETA,
    DEFAULT_ERP,
    DEFAULT_RISK_FREE_RATE,
    DEFAULT_TAX_RATE,
    SIZE_PREMIUM_LARGE,
    SIZE_PREMIUM_MEGA,
    SIZE_PREMIUM_MICRO,
    SIZE_PREMIUM_MID,
    SIZE_PREMIUM_SMALL,
    WACC_CEILING,
    WACC_FLOOR,
)
from .helpers import clamp, safe_div
from .models import CompanyDataPackage, WACCResult

logger = logging.getLogger("finance_app")


def calculate_wacc(data: CompanyDataPackage, trial_params=None) -> WACCResult:
    """Calculate weighted average cost of capital.

    Implements all 8 steps from Design Section 4.
    """
    warnings: list[str] = []
    latest = data.annual_financials[-1] if data.annual_financials else {}

    # 1. Risk-Free Rate
    rf = data.risk_free_rate
    if rf <= 0:
        rf = DEFAULT_RISK_FREE_RATE
        warnings.append("Risk-free rate unavailable; using default")

    # 2. Beta (raw → Blume adjusted)
    raw_beta = data.quote_data.beta
    if raw_beta is None or raw_beta <= 0:
        # Fallback: industry median
        raw_beta = data.industry_benchmarks.median_beta
        if raw_beta is None or raw_beta <= 0:
            raw_beta = DEFAULT_BETA
            warnings.append("Beta unavailable; using default 1.0")
        else:
            warnings.append("Using industry median beta")

    # MC trial jitter: beta
    if trial_params is not None:
        raw_beta += trial_params.beta_jitter

    # Blume adjustment
    adjusted_beta = BLUME_WEIGHT_RAW * raw_beta + BLUME_WEIGHT_MARKET * 1.0
    adjusted_beta = min(adjusted_beta, 2.5)

    # 3. Size Premium
    market_cap = data.quote_data.market_cap or data.company_profile.market_cap
    size_premium = _get_size_premium(market_cap)

    # MC trial jitter: size premium
    if trial_params is not None:
        size_premium += trial_params.size_premium_jitter

    # 4. Cost of Equity (CAPM)
    erp = DEFAULT_ERP

    # MC trial override: ERP
    if trial_params is not None and trial_params.erp_override is not None:
        erp = trial_params.erp_override
    cost_of_equity = rf + (adjusted_beta * erp) + size_premium

    # 5. Cost of Debt
    total_debt = latest.get("total_debt") or 0
    interest_expense = abs(latest.get("interest_expense") or 0)

    if total_debt > 0 and interest_expense > 0:
        cost_of_debt_pre = interest_expense / total_debt
        cost_of_debt_pre = max(cost_of_debt_pre, rf)  # floor at risk-free
        cost_of_debt_pre = min(cost_of_debt_pre, 0.15)  # cap at 15%
    elif total_debt > 0 and interest_expense == 0:
        # Interest = 0 but debt > 0
        cost_of_debt_pre = rf + 0.02
        warnings.append("No interest expense reported; using Rf + 2%")
    else:
        cost_of_debt_pre = rf + 0.02

    # 6. Effective Tax Rate
    tax_expense_raw = latest.get("tax_provision")
    net_income = latest.get("net_income") or 0

    if tax_expense_raw is not None:
        pretax_income = net_income + tax_expense_raw
        if pretax_income > 0:
            effective_tax = tax_expense_raw / pretax_income
            effective_tax = clamp(effective_tax, 0.0, 0.45)
        else:
            effective_tax = DEFAULT_TAX_RATE
            if pretax_income < 0:
                warnings.append("Negative pretax income; using default tax rate")
    else:
        effective_tax = DEFAULT_TAX_RATE
        warnings.append("No tax data; using default tax rate")

    cost_of_debt_after = cost_of_debt_pre * (1 - effective_tax)

    # 7. Capital Structure
    if market_cap and market_cap > 0:
        total_value = market_cap + total_debt
        if total_value > 0:
            weight_equity = market_cap / total_value
            weight_debt = total_debt / total_value
        else:
            weight_equity = 1.0
            weight_debt = 0.0
            warnings.append("Non-positive total value; using all-equity")
    else:
        weight_equity = 1.0
        weight_debt = 0.0
        warnings.append("No market cap; using all-equity structure")

    # Edge case: D/V > 0.7 → add distress premium
    if weight_debt > 0.7:
        cost_of_equity += 0.01
        warnings.append("High leverage (D/V > 70%); added 1% distress premium")

    # Edge case: negative equity → use market cap only
    equity_book = latest.get("stockholders_equity") or 0
    if equity_book < 0 and market_cap and market_cap > 0:
        warnings.append("Negative book equity; using market cap for equity weight")

    # 8. Final WACC
    if total_debt == 0:
        wacc = cost_of_equity
    else:
        wacc = (weight_equity * cost_of_equity) + (weight_debt * cost_of_debt_after)

    wacc = clamp(wacc, WACC_FLOOR, WACC_CEILING)

    return WACCResult(
        wacc=round(wacc, 4),
        cost_of_equity=round(cost_of_equity, 4),
        cost_of_debt_pre_tax=round(cost_of_debt_pre, 4),
        cost_of_debt_after_tax=round(cost_of_debt_after, 4),
        risk_free_rate=round(rf, 4),
        adjusted_beta=round(adjusted_beta, 4),
        raw_beta=round(raw_beta, 4),
        erp=erp,
        size_premium=size_premium,
        effective_tax_rate=round(effective_tax, 4),
        weight_equity=round(weight_equity, 4),
        weight_debt=round(weight_debt, 4),
        market_cap=market_cap,
        total_debt=total_debt if total_debt > 0 else None,
        warnings=warnings,
    )


def calculate_wacc_from_overrides(
    base_result: WACCResult,
    overrides: dict[str, float],
) -> WACCResult:
    """Recompute WACC from user-provided component overrides.

    Starts from base_result values, applies overrides, then
    recomputes all derived values (Blume beta, cost of equity,
    after-tax cost of debt, final WACC).

    Supported override keys:
        risk_free_rate, raw_beta, erp, size_premium,
        cost_of_debt_pre_tax, effective_tax_rate,
        weight_equity, weight_debt
    """
    # Start from base values
    rf = overrides.get("risk_free_rate", base_result.risk_free_rate)
    raw_beta = overrides.get("raw_beta", base_result.raw_beta)
    erp = overrides.get("erp", base_result.erp)
    sp = overrides.get("size_premium", base_result.size_premium)
    kd_pre = overrides.get("cost_of_debt_pre_tax", base_result.cost_of_debt_pre_tax)
    tax = overrides.get("effective_tax_rate", base_result.effective_tax_rate)

    # Weights (linked — one adjusts the other)
    if "weight_equity" in overrides and "weight_debt" not in overrides:
        we = overrides["weight_equity"]
        wd = 1.0 - we
    elif "weight_debt" in overrides and "weight_equity" not in overrides:
        wd = overrides["weight_debt"]
        we = 1.0 - wd
    elif "weight_equity" in overrides and "weight_debt" in overrides:
        we = overrides["weight_equity"]
        wd = overrides["weight_debt"]
    else:
        we = base_result.weight_equity
        wd = base_result.weight_debt

    # Recompute derived values
    adjusted_beta = BLUME_WEIGHT_RAW * raw_beta + BLUME_WEIGHT_MARKET * 1.0
    adjusted_beta = min(adjusted_beta, 2.5)
    cost_of_equity = rf + (adjusted_beta * erp) + sp
    kd_after = kd_pre * (1 - tax)

    if wd == 0:
        wacc = cost_of_equity
    else:
        wacc = (we * cost_of_equity) + (wd * kd_after)
    wacc = clamp(wacc, WACC_FLOOR, WACC_CEILING)

    warnings = list(base_result.warnings) + ["Computed from user overrides"]

    return WACCResult(
        wacc=round(wacc, 4),
        cost_of_equity=round(cost_of_equity, 4),
        cost_of_debt_pre_tax=round(kd_pre, 4),
        cost_of_debt_after_tax=round(kd_after, 4),
        risk_free_rate=round(rf, 4),
        adjusted_beta=round(adjusted_beta, 4),
        raw_beta=round(raw_beta, 4),
        erp=erp,
        size_premium=sp,
        effective_tax_rate=round(tax, 4),
        weight_equity=round(we, 4),
        weight_debt=round(wd, 4),
        market_cap=base_result.market_cap,
        total_debt=base_result.total_debt,
        warnings=warnings,
    )


def _get_size_premium(market_cap: float | None) -> float:
    """Determine size premium tier from market cap."""
    if market_cap is None:
        return SIZE_PREMIUM_MID  # default mid assumption

    if market_cap > 200_000_000_000:
        return SIZE_PREMIUM_MEGA
    if market_cap > 10_000_000_000:
        return SIZE_PREMIUM_LARGE
    if market_cap > 2_000_000_000:
        return SIZE_PREMIUM_MID
    if market_cap > 300_000_000:
        return SIZE_PREMIUM_SMALL
    return SIZE_PREMIUM_MICRO
