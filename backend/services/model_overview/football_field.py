"""Football field data assembly — extract bear/base/bull per engine."""

from __future__ import annotations

import logging
import statistics

from .models import FootballFieldRow, FootballFieldResult

logger = logging.getLogger("finance_app")


def extract_model_prices(
    engine_results: dict[str, dict],
    current_price: float,
) -> dict[str, FootballFieldRow]:
    """Extract bear/base/bull prices from each engine result.

    Args:
        engine_results: Dict of model_name → engine result dict.
        current_price: Current market price.

    Returns:
        Dict of model_name → FootballFieldRow.
    """
    rows: dict[str, FootballFieldRow] = {}

    for model_name, result in engine_results.items():
        if result is None:
            continue

        if model_name == "dcf":
            row = _extract_dcf(result)
        elif model_name == "ddm":
            row = _extract_ddm(result)
        elif model_name == "comps":
            row = _extract_comps(result)
        elif model_name == "revenue_based":
            row = _extract_revbased(result)
        else:
            continue

        if row is not None:
            rows[model_name] = row

    return rows


def build_football_field(
    rows: dict[str, FootballFieldRow],
    current_price: float,
) -> FootballFieldResult:
    """Assemble football field result with chart bounds."""
    model_rows = list(rows.values())

    if not model_rows:
        return FootballFieldResult(current_price=current_price)

    # Chart bounds: min/max across all rows with padding
    all_prices = []
    for r in model_rows:
        all_prices.extend([r.bear_price, r.base_price, r.bull_price])
    all_prices.append(current_price)
    all_prices = [p for p in all_prices if p > 0]

    chart_min = min(all_prices) * 0.85 if all_prices else 0
    chart_max = max(all_prices) * 1.15 if all_prices else current_price * 2

    return FootballFieldResult(
        models=model_rows,
        current_price=current_price,
        chart_min=round(chart_min, 2),
        chart_max=round(chart_max, 2),
    )


# ---------------------------------------------------------------------------
# Per-engine extractors
# ---------------------------------------------------------------------------

def _extract_dcf(result: dict) -> FootballFieldRow | None:
    """DCF: scenarios.bear/base/bull.implied_price."""
    scenarios = result.get("scenarios", {})
    bear = scenarios.get("bear", {}).get("implied_price", 0)
    base = scenarios.get("base", {}).get("implied_price", 0)
    bull = scenarios.get("bull", {}).get("implied_price", 0)

    return FootballFieldRow(
        model_name="DCF",
        bear_price=round(bear, 2),
        base_price=round(base, 2),
        bull_price=round(bull, 2),
    )


def _extract_ddm(result: dict) -> FootballFieldRow | None:
    """DDM: scenarios.bear/base/bull.intrinsic_value_per_share. Skip if not applicable."""
    if not result.get("applicable", False):
        return None

    scenarios = result.get("scenarios", {})
    bear = scenarios.get("bear", {}).get("intrinsic_value_per_share", 0)
    base = scenarios.get("base", {}).get("intrinsic_value_per_share", 0)
    bull = scenarios.get("bull", {}).get("intrinsic_value_per_share", 0)

    return FootballFieldRow(
        model_name="DDM",
        bear_price=round(bear, 2),
        base_price=round(base, 2),
        bull_price=round(bull, 2),
    )


def _extract_comps(result: dict) -> FootballFieldRow | None:
    """Comps: use football_field ranges — min(low), avg(adjusted_mid), max(high)."""
    ff = result.get("football_field", {})
    ranges = ff.get("ranges", [])

    if not ranges:
        return None

    lows = [r["low"] for r in ranges if r.get("low", 0) > 0]
    mids = [r["adjusted_mid"] for r in ranges if r.get("adjusted_mid", 0) > 0]
    highs = [r["high"] for r in ranges if r.get("high", 0) > 0]

    if not lows or not mids or not highs:
        return None

    return FootballFieldRow(
        model_name="Comps",
        bear_price=round(min(lows), 2),
        base_price=round(statistics.mean(mids), 2),
        bull_price=round(max(highs), 2),
    )


def _extract_revbased(result: dict) -> FootballFieldRow | None:
    """Revenue-Based: scenarios.bear/base/bull.primary_implied_price."""
    scenarios = result.get("scenarios", {})
    bear = scenarios.get("bear", {}).get("primary_implied_price", 0)
    base = scenarios.get("base", {}).get("primary_implied_price", 0)
    bull = scenarios.get("bull", {}).get("primary_implied_price", 0)

    return FootballFieldRow(
        model_name="Revenue-Based",
        bear_price=round(bear, 2),
        base_price=round(base, 2),
        bull_price=round(bull, 2),
    )
