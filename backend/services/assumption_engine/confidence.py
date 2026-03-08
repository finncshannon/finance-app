"""Confidence Scoring — scores 0–100 per assumption category.

Evaluates data quality, consistency, peer alignment, and method agreement.
Pure computation, no I/O.
"""

from __future__ import annotations

import logging
import statistics

from .helpers import clamp
from .models import (
    AssumptionConfidence,
    CompanyDataPackage,
    ConfidenceDetail,
    MarginLensResult,
    RevenueProjection,
    WACCResult,
)

logger = logging.getLogger("finance_app")

# Category weights for overall confidence
_CATEGORY_WEIGHTS = {
    "data_quality": 0.25,
    "revenue_projection": 0.25,
    "margin_projection": 0.20,
    "wacc": 0.15,
    "peer_alignment": 0.15,
}


def score_confidence(
    data: CompanyDataPackage,
    revenue: RevenueProjection,
    margins: dict[str, MarginLensResult],
    wacc_result: WACCResult,
) -> AssumptionConfidence:
    """Score confidence across 5 categories, returning overall + details."""
    details: list[ConfidenceDetail] = []

    # 1. Data Quality
    dq_score, dq_reason = _score_data_quality(data)
    details.append(ConfidenceDetail(
        category="data_quality", score=dq_score, reasoning=dq_reason,
    ))

    # 2. Revenue Projection
    rev_score, rev_reason = _score_revenue_confidence(revenue, data)
    details.append(ConfidenceDetail(
        category="revenue_projection", score=rev_score, reasoning=rev_reason,
    ))

    # 3. Margin Projection
    mar_score, mar_reason = _score_margin_confidence(margins)
    details.append(ConfidenceDetail(
        category="margin_projection", score=mar_score, reasoning=mar_reason,
    ))

    # 4. WACC
    wacc_score, wacc_reason = _score_wacc_confidence(wacc_result)
    details.append(ConfidenceDetail(
        category="wacc", score=wacc_score, reasoning=wacc_reason,
    ))

    # 5. Peer Alignment
    peer_score, peer_reason = _score_peer_alignment(data, margins)
    details.append(ConfidenceDetail(
        category="peer_alignment", score=peer_score, reasoning=peer_reason,
    ))

    # Overall: weighted average
    overall = sum(
        d.score * _CATEGORY_WEIGHTS.get(d.category, 0.20)
        for d in details
    )

    return AssumptionConfidence(
        overall_score=round(clamp(overall, 0, 100), 1),
        details=details,
    )


# ---------------------------------------------------------------------------
# Category scorers
# ---------------------------------------------------------------------------

def _score_data_quality(data: CompanyDataPackage) -> tuple[float, str]:
    """Score based on years of data, completeness, and freshness."""
    score = 50.0
    reasons: list[str] = []

    # Years of data: +5 per year above 3, cap contribution at +35
    years_bonus = min((data.years_available - 3) * 5, 35)
    score += years_bonus
    reasons.append(f"{data.years_available} years of data")

    # Financial completeness (check key fields in latest year)
    if data.annual_financials:
        latest = data.annual_financials[-1]
        key_fields = [
            "revenue", "gross_profit", "ebit", "net_income",
            "total_assets", "total_debt", "free_cash_flow",
        ]
        present = sum(1 for f in key_fields if latest.get(f) is not None)
        completeness = present / len(key_fields)
        score += completeness * 15
        if completeness < 0.7:
            reasons.append("some financial fields missing")

    # Quote data available
    if data.quote_data.current_price is not None:
        score += 5
    else:
        score -= 10
        reasons.append("no market data")

    # Analyst coverage
    if data.analyst_estimates.revenue_growth_estimate is not None:
        score += 5
        reasons.append("analyst estimates available")

    return round(clamp(score, 0, 100), 1), "; ".join(reasons) if reasons else "Adequate data"


def _score_revenue_confidence(
    revenue: RevenueProjection,
    data: CompanyDataPackage,
) -> tuple[float, str]:
    """Score based on CAGR consistency, volatility, and analyst agreement."""
    score = 60.0
    reasons: list[str] = []

    # Low volatility → higher confidence
    if revenue.growth_volatility < 0.05:
        score += 20
        reasons.append("very stable growth")
    elif revenue.growth_volatility < 0.10:
        score += 10
        reasons.append("relatively stable growth")
    elif revenue.growth_volatility > 0.25:
        score -= 15
        reasons.append("high growth volatility")

    # Divergence flag reduces confidence
    if revenue.divergence_flag:
        score -= 10
        reasons.append(f"growth {revenue.divergence_type}")

    # Regime transition reduces confidence
    if revenue.regime_transition:
        score -= 10
        reasons.append("regime transition detected")

    # Multiple CAGR windows → more reliable
    n_cagrs = len(revenue.historical_cagrs)
    if n_cagrs >= 3:
        score += 10
    elif n_cagrs == 1:
        score -= 10
        reasons.append("limited CAGR windows")

    # Analyst available boosts slightly
    if revenue.analyst_available:
        score += 5

    return round(clamp(score, 0, 100), 1), "; ".join(reasons) if reasons else "Adequate basis"


def _score_margin_confidence(
    margins: dict[str, MarginLensResult],
) -> tuple[float, str]:
    """Score based on trend quality and lens agreement."""
    score = 60.0
    reasons: list[str] = []

    r2_values: list[float] = []
    for mtype, result in margins.items():
        if result.trend_r_squared is not None:
            r2_values.append(result.trend_r_squared)

    # Average R² of trends
    if r2_values:
        avg_r2 = statistics.mean(r2_values)
        if avg_r2 > 0.7:
            score += 20
            reasons.append("strong trend fit")
        elif avg_r2 > 0.4:
            score += 10
        elif avg_r2 < 0.2:
            score -= 10
            reasons.append("weak trend fit")

    # Check for outliers detected
    total_outliers = sum(len(r.outlier_years) for r in margins.values())
    if total_outliers > 5:
        score -= 10
        reasons.append(f"{total_outliers} margin outliers detected")

    # Check industry median coverage
    has_industry = sum(
        1 for r in margins.values() if r.industry_median is not None
    )
    if has_industry >= 4:
        score += 5
    elif has_industry <= 1:
        score -= 10
        reasons.append("limited industry benchmarks")

    return round(clamp(score, 0, 100), 1), "; ".join(reasons) if reasons else "Adequate basis"


def _score_wacc_confidence(wacc_result: WACCResult) -> tuple[float, str]:
    """Score based on input quality and reasonableness."""
    score = 70.0
    reasons: list[str] = []

    # Warnings reduce confidence
    n_warnings = len(wacc_result.warnings)
    score -= n_warnings * 5
    if n_warnings > 0:
        reasons.append(f"{n_warnings} calculation warnings")

    # Beta from market data (not default) → higher confidence
    if wacc_result.raw_beta != 1.0:
        score += 10
    else:
        reasons.append("using default beta")

    # WACC in typical range (7-14%) → reasonable
    if 0.07 <= wacc_result.wacc <= 0.14:
        score += 10
        reasons.append("WACC in typical range")
    elif wacc_result.wacc > 0.20:
        score -= 10
        reasons.append("unusually high WACC")

    return round(clamp(score, 0, 100), 1), "; ".join(reasons) if reasons else "Adequate basis"


def _score_peer_alignment(
    data: CompanyDataPackage,
    margins: dict[str, MarginLensResult],
) -> tuple[float, str]:
    """Score based on proximity to industry benchmarks."""
    score = 60.0
    reasons: list[str] = []

    deviations: list[float] = []
    for mtype, result in margins.items():
        if result.current_margin is not None and result.industry_median is not None:
            dev = abs(result.current_margin - result.industry_median)
            deviations.append(dev)

    if deviations:
        avg_dev = statistics.mean(deviations)
        if avg_dev < 0.05:
            score += 25
            reasons.append("closely aligned with industry")
        elif avg_dev < 0.10:
            score += 15
            reasons.append("reasonably aligned with industry")
        elif avg_dev > 0.20:
            score -= 10
            reasons.append("significant deviation from industry")
    else:
        score -= 15
        reasons.append("no industry comparison available")

    return round(clamp(score, 0, 100), 1), "; ".join(reasons) if reasons else "Adequate basis"
