"""Agreement analysis — model consensus evaluation and reasoning."""

from __future__ import annotations

import logging
import statistics

from .models import (
    AgreementAnalysis, DivergenceMatrix, DivergencePair,
    FootballFieldRow,
)

logger = logging.getLogger("finance_app")

# Named constants
AGREEMENT_STRONG = 0.15
AGREEMENT_MODERATE = 0.30
AGREEMENT_WEAK = 0.50


def calculate_agreement(
    model_rows: dict[str, FootballFieldRow],
    engine_results: dict[str, dict],
    current_price: float,
) -> AgreementAnalysis:
    """Classify model agreement level and generate reasoning."""
    base_prices = {
        name: row.base_price
        for name, row in model_rows.items()
        if row.base_price > 0
    }

    if len(base_prices) <= 1:
        return AgreementAnalysis(
            level="N/A",
            reasoning="Single model — run additional models for cross-model comparison.",
        )

    # Compute spread
    prices = list(base_prices.values())
    mean_price = statistics.mean(prices)
    max_price = max(prices)
    min_price = min(prices)
    spread = (max_price - min_price) / mean_price if mean_price > 0 else 0

    # Identify highest / lowest
    highest_model = max(base_prices, key=base_prices.get)
    lowest_model = min(base_prices, key=base_prices.get)

    # Classify level
    if spread < AGREEMENT_STRONG:
        level = "STRONG"
    elif spread < AGREEMENT_MODERATE:
        level = "MODERATE"
    elif spread < AGREEMENT_WEAK:
        level = "WEAK"
    else:
        level = "SIGNIFICANT_DISAGREEMENT"

    # Divergence matrix
    div_matrix = _build_divergence_matrix(base_prices)

    # Generate reasoning
    reasoning = _generate_reasoning(
        level, spread, base_prices,
        highest_model, max_price,
        lowest_model, min_price,
        engine_results,
    )

    return AgreementAnalysis(
        level=level,
        max_spread=round(max_price - min_price, 2),
        max_spread_pct=round(spread, 4),
        highest_model=highest_model,
        highest_price=round(max_price, 2),
        lowest_model=lowest_model,
        lowest_price=round(min_price, 2),
        reasoning=reasoning,
        divergence_matrix=div_matrix,
    )


def _build_divergence_matrix(
    base_prices: dict[str, float],
) -> DivergenceMatrix:
    """Compute pairwise divergence between all models."""
    models = list(base_prices.keys())
    pairs: list[DivergencePair] = []

    for i in range(len(models)):
        for j in range(i + 1, len(models)):
            a, b = models[i], models[j]
            pa, pb = base_prices[a], base_prices[b]
            mean_ab = (pa + pb) / 2
            div = abs(pa - pb) / mean_ab if mean_ab > 0 else 0
            pairs.append(DivergencePair(
                model_a=a, model_b=b,
                divergence_pct=round(div, 4),
            ))

    closest = min(pairs, key=lambda p: p.divergence_pct) if pairs else None
    most_div = max(pairs, key=lambda p: p.divergence_pct) if pairs else None

    return DivergenceMatrix(
        pairs=pairs,
        closest_pair=closest,
        most_divergent_pair=most_div,
    )


def _generate_reasoning(
    level: str,
    spread: float,
    base_prices: dict[str, float],
    highest_model: str,
    highest_price: float,
    lowest_model: str,
    lowest_price: float,
    engine_results: dict[str, dict],
) -> str:
    """Generate template-based reasoning text."""
    n = len(base_prices)
    spread_pct = f"{spread * 100:.0f}%"
    models_str = ", ".join(_display_name(m) for m in base_prices)

    if level == "STRONG":
        return (
            f"All {n} models converge within {spread_pct}, "
            f"suggesting ${lowest_price:.0f}-${highest_price:.0f} range. "
            f"High confidence in composite valuation."
        )

    # Identify outlier for explanation
    explanation = _get_divergence_explanation(
        highest_model, lowest_model, engine_results,
    )

    if level == "MODERATE":
        return (
            f"{n} models show moderate agreement ({spread_pct} spread). "
            f"{_display_name(highest_model)} highest (${highest_price:.0f}), "
            f"{_display_name(lowest_model)} lowest (${lowest_price:.0f}). "
            f"{explanation}"
        )

    if level == "WEAK":
        return (
            f"Notable divergence across {n} models. "
            f"{_display_name(highest_model)} at ${highest_price:.0f} vs "
            f"{_display_name(lowest_model)} at ${lowest_price:.0f} "
            f"({spread_pct} spread). {explanation}"
        )

    # SIGNIFICANT_DISAGREEMENT
    return (
        f"Significant disagreement ({spread_pct} spread), "
        f"${lowest_price:.0f} to ${highest_price:.0f}. "
        f"{explanation} "
        f"Composite should be interpreted cautiously."
    )


def _get_divergence_explanation(
    highest_model: str,
    lowest_model: str,
    engine_results: dict[str, dict],
) -> str:
    """Select the appropriate divergence explanation sub-template."""
    # Determine which model is the outlier
    if highest_model == "comps":
        return (
            "Market-based valuation exceeds intrinsic models, "
            "suggesting market prices in growth optionality."
        )
    if lowest_model == "comps":
        return (
            "Intrinsic models value above peer multiples, "
            "suggesting underappreciated fundamentals."
        )
    if lowest_model == "ddm":
        return (
            "Dividend model lower because payout ratio only distributes "
            "a fraction of earnings."
        )
    if highest_model == "ddm":
        return "DDM higher, reflecting sustainable above-market dividend growth."

    if highest_model == "revenue_based":
        return (
            "Revenue model higher, reflecting aggressive multiples "
            "typical for high-growth companies."
        )
    if lowest_model == "revenue_based":
        return (
            "Revenue multiples undervalue vs earnings-based models "
            "due to strong margins."
        )

    if highest_model == "dcf":
        dcf = engine_results.get("dcf", {})
        base_sc = dcf.get("scenarios", {}).get("base", {})
        tv_pct = base_sc.get("tv_pct_of_ev", 0) * 100
        return f"DCF higher, driven by terminal value ({tv_pct:.0f}% of EV)."

    if lowest_model == "dcf":
        dcf = engine_results.get("dcf", {})
        base_sc = dcf.get("scenarios", {}).get("base", {})
        wacc = base_sc.get("wacc", 0) * 100
        tg = base_sc.get("terminal_growth_rate", 0) * 100
        return f"DCF conservative due to high WACC ({wacc:.1f}%) or low terminal growth ({tg:.1f}%)."

    return ""


def _display_name(model_key: str) -> str:
    """Convert internal key to display name."""
    names = {
        "dcf": "DCF",
        "ddm": "DDM",
        "comps": "Comps",
        "revenue_based": "Revenue-Based",
    }
    return names.get(model_key, model_key)
