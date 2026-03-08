"""Model weight calculation — confidence × applicability → normalized weights."""

from __future__ import annotations

import logging

from .models import ModelWeightResult

logger = logging.getLogger("finance_app")

# Named constants
MIN_MODEL_WEIGHT = 0.05
WEIGHT_ROUNDING = 0.05


def calculate_weights(
    detection_scores: dict[str, float],
    engine_results: dict[str, dict],
    data: dict,
) -> ModelWeightResult:
    """Compute model weights from confidence scores and applicability.

    Steps:
    1. Raw confidence scores from model detection (0-100)
    2. Applicability multipliers (0-1) based on company data
    3. adjusted_score = confidence × multiplier
    4. Normalize to 100%, enforce min 5%, round to 5%
    """
    multipliers: dict[str, float] = {}
    adjusted: dict[str, float] = {}
    excluded: list[str] = []
    latest = {}
    financials = data.get("annual_financials", [])
    if financials:
        latest = financials[-1]

    for model_name, score in detection_scores.items():
        result = engine_results.get(model_name)
        mult = _get_applicability_multiplier(model_name, result, data, latest)
        multipliers[model_name] = mult

        if mult == 0:
            excluded.append(model_name)
            continue

        adjusted[model_name] = score * mult

    # Normalize to 100%
    weights = normalize_weights(adjusted)

    return ModelWeightResult(
        weights=weights,
        raw_scores=detection_scores,
        multipliers=multipliers,
        adjusted_scores={k: round(v, 2) for k, v in adjusted.items()},
        excluded_models=excluded,
        included_model_count=len(weights),
    )


def _get_applicability_multiplier(
    model_name: str,
    result: dict | None,
    data: dict,
    latest: dict,
) -> float:
    """Determine applicability multiplier for a model (0.0-1.0)."""
    if model_name == "dcf":
        fcf = latest.get("free_cash_flow")
        ebit = latest.get("operating_income") or latest.get("ebit")
        if fcf is not None and fcf > 0:
            return 1.0
        if ebit is not None and ebit > 0:
            return 0.7
        return 0.3

    elif model_name == "ddm":
        if result and not result.get("applicable", False):
            return 0.0
        divs = latest.get("dividends_paid")
        if not divs or divs == 0:
            return 0.0
        # Check dividend history length
        financials = data.get("annual_financials", [])
        streak = sum(
            1 for row in financials
            if row.get("dividends_paid") is not None and row.get("dividends_paid") != 0
        )
        if streak >= 5:
            return 1.0
        return 0.6

    elif model_name == "comps":
        if result is None:
            return 0.3
        peer_group = result.get("peer_group", {})
        count = peer_group.get("count", 0)
        if count >= 5:
            return 1.0
        if count >= 3:
            return 0.7
        return 0.3

    elif model_name == "revenue_based":
        growth_metrics = result.get("growth_metrics", {}) if result else {}
        rule_of_40 = growth_metrics.get("rule_of_40", {})
        growth_component = rule_of_40.get("revenue_growth_component", 0) / 100  # Back to decimal

        # Check if pre-profit
        op_margin = latest.get("operating_margin")
        if op_margin is not None and op_margin < 0:
            return 1.0  # Pre-profit → highly relevant
        if growth_component > 0.20:
            return 1.0
        if growth_component > 0.10:
            return 0.5
        return 0.2

    return 0.5  # Default


def normalize_weights(adjusted_scores: dict[str, float]) -> dict[str, float]:
    """Normalize scores to 100%, enforce min 5%, round to 5%."""
    if not adjusted_scores:
        return {}

    total = sum(adjusted_scores.values())
    if total <= 0:
        # Equal weight fallback
        n = len(adjusted_scores)
        return {k: round(1.0 / n, 2) for k in adjusted_scores}

    # Raw weights
    raw = {k: v / total for k, v in adjusted_scores.items()}

    # Enforce minimum 5%
    below_min = {k: v for k, v in raw.items() if v < MIN_MODEL_WEIGHT}
    above_min = {k: v for k, v in raw.items() if v >= MIN_MODEL_WEIGHT}

    for k in below_min:
        raw[k] = MIN_MODEL_WEIGHT

    if above_min:
        excess = sum(MIN_MODEL_WEIGHT - v for v in below_min.values())
        above_total = sum(above_min.values())
        for k in above_min:
            raw[k] -= excess * (above_min[k] / above_total)

    # Round to nearest 5%
    rounded = {k: round(v / WEIGHT_ROUNDING) * WEIGHT_ROUNDING for k, v in raw.items()}

    # Fix rounding error — adjust largest weight
    total_rounded = sum(rounded.values())
    diff = 1.0 - total_rounded
    if abs(diff) > 0.001 and rounded:
        largest = max(rounded, key=rounded.get)
        rounded[largest] = round(rounded[largest] + diff, 2)

    return {k: round(v, 2) for k, v in rounded.items()}
