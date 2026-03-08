"""Tornado mode — one-at-a-time sensitivity analysis."""

from __future__ import annotations

import logging
import time

from engines import DCFEngine
from services.assumption_engine.models import AssumptionSet

from .models import TornadoBar, TornadoResult
from .sliders import _deep_clone_assumptions, _apply_override

logger = logging.getLogger("finance_app")

# Named constants
TORNADO_DEFAULT_PERTURBATION_PCT = 0.10

# Variable definitions: (name, key, perturbation_method)
# perturbation_method: "bull_bear" uses scenario spread, "pct" uses percentage of base
TORNADO_VARIABLES = [
    ("WACC", "scenarios.{s}.wacc", "bull_bear_reverse"),
    ("Terminal Growth", "scenarios.{s}.terminal_growth_rate", "pct_50"),
    ("Revenue Growth Y1", "scenarios.{s}.revenue_growth_rates[0]", "bull_bear"),
    ("Operating Margin Y1", "scenarios.{s}.operating_margins[0]", "bull_bear"),
    ("Tax Rate", "model_assumptions.dcf.tax_rate", "pct_25"),
    ("CapEx / Revenue", "model_assumptions.dcf.capex_to_revenue", "pct_30"),
    ("Exit Multiple", "model_assumptions.dcf.terminal_exit_multiple", "pct_25"),
    ("NWC / Revenue", "model_assumptions.dcf.nwc_change_to_revenue", "pct_50"),
]


def calculate_tornado(
    assumption_set: AssumptionSet,
    data: dict,
    current_price: float,
) -> TornadoResult:
    """Calculate tornado chart bars for all variables.

    For each variable: run engine at low and high perturbation,
    record prices, compute spread. Sort by spread descending.
    """
    t0 = time.perf_counter()
    scenarios = assumption_set.scenarios
    if scenarios is None:
        return TornadoResult(current_price=current_price)

    # Get base price
    base_result = DCFEngine.run(assumption_set, data, current_price)
    base_sc = base_result.scenarios.get("base")
    base_price = base_sc.implied_price if base_sc else 0.0

    bars: list[TornadoBar] = []

    for var_name, var_key, method in TORNADO_VARIABLES:
        base_value = _get_base_value(assumption_set, var_key)
        if base_value is None:
            continue

        low, high = _compute_perturbation(
            base_value, method, assumption_set, var_key,
        )

        # Run at low
        price_low = _run_at_value(assumption_set, var_key, low, data, current_price)
        # Run at high
        price_high = _run_at_value(assumption_set, var_key, high, data, current_price)

        spread = abs(price_high - price_low)

        bars.append(TornadoBar(
            variable_name=var_name,
            variable_key=var_key,
            base_value=round(base_value, 6),
            low_input=round(low, 6),
            high_input=round(high, 6),
            price_at_low_input=round(price_low, 2),
            price_at_high_input=round(price_high, 2),
            spread=round(spread, 2),
            base_price=round(base_price, 2),
        ))

    # Sort by spread descending
    bars.sort(key=lambda b: b.spread, reverse=True)

    elapsed = (time.perf_counter() - t0) * 1000
    return TornadoResult(
        bars=bars,
        base_price=round(base_price, 2),
        current_price=current_price,
        variable_count=len(bars),
        computation_time_ms=round(elapsed, 1),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_base_value(a: AssumptionSet, key: str) -> float | None:
    """Extract the base-scenario value for a given key path."""
    if key.startswith("scenarios.{s}."):
        field = key.replace("scenarios.{s}.", "")
        scenario = a.scenarios.base if a.scenarios else None
        if scenario is None:
            return None
        return _get_field(scenario, field)
    elif key.startswith("model_assumptions.dcf."):
        field = key.replace("model_assumptions.dcf.", "")
        dcf = a.model_assumptions.dcf
        if dcf is None:
            return None
        return getattr(dcf, field, None)
    return None


def _get_field(obj, field: str):
    """Get field value, handling array[index] syntax."""
    if "[" in field:
        attr_name, idx_str = field.split("[")
        idx = int(idx_str.rstrip("]"))
        arr = getattr(obj, attr_name, None)
        if arr and isinstance(arr, list) and idx < len(arr):
            return arr[idx]
        return None
    return getattr(obj, field, None)


def _compute_perturbation(
    base_value: float,
    method: str,
    a: AssumptionSet,
    key: str,
) -> tuple[float, float]:
    """Compute (low, high) perturbation range for a variable."""
    scenarios = a.scenarios

    if method == "bull_bear" and scenarios:
        bull_val = _get_scenario_value(scenarios.bull, key)
        bear_val = _get_scenario_value(scenarios.bear, key)
        if bull_val is not None and bear_val is not None and abs(bull_val - bear_val) > 1e-9:
            return (min(bear_val, bull_val), max(bear_val, bull_val))

    if method == "bull_bear_reverse" and scenarios:
        # For WACC: bear has higher WACC, bull has lower
        bull_val = _get_scenario_value(scenarios.bull, key)
        bear_val = _get_scenario_value(scenarios.bear, key)
        if bull_val is not None and bear_val is not None and abs(bull_val - bear_val) > 1e-9:
            return (min(bull_val, bear_val), max(bull_val, bear_val))

    # Percentage-based perturbation
    pct = TORNADO_DEFAULT_PERTURBATION_PCT
    if method == "pct_25":
        pct = 0.25
    elif method == "pct_30":
        pct = 0.30
    elif method == "pct_50":
        pct = 0.50

    if abs(base_value) < 1e-9:
        return (-0.01, 0.01)

    low = base_value * (1 - pct)
    high = base_value * (1 + pct)

    # For terminal growth, cap high at wacc - 0.01
    if "terminal_growth" in key and scenarios:
        wacc = scenarios.base.wacc
        high = min(high, wacc - 0.01)

    return (low, high)


def _get_scenario_value(scenario, key: str) -> float | None:
    """Extract value from a specific scenario using key path."""
    field = key.replace("scenarios.{s}.", "")
    return _get_field(scenario, field)


def _run_at_value(
    assumption_set: AssumptionSet,
    key: str,
    value: float,
    data: dict,
    current_price: float,
) -> float:
    """Clone assumptions, apply single override, run DCF, return base price."""
    modified = _deep_clone_assumptions(assumption_set)
    _apply_override(modified, key, value)

    # Enforce terminal growth < wacc
    if modified.scenarios:
        for sc in [modified.scenarios.base, modified.scenarios.bull, modified.scenarios.bear]:
            if sc.terminal_growth_rate >= sc.wacc:
                sc.terminal_growth_rate = sc.wacc - 0.01

    result = DCFEngine.run(modified, data, current_price)
    base_sc = result.scenarios.get("base")
    return base_sc.implied_price if base_sc else 0.0
