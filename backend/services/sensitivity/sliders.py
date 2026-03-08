"""Slider mode — real-time sensitivity recalculation."""

from __future__ import annotations

import copy
import logging
import time

from engines import DCFEngine
from engines.engine_utils import clamp
from services.assumption_engine.models import AssumptionSet

from .models import SliderResult

logger = logging.getLogger("finance_app")


def slider_recalculate(
    base_assumption_set: AssumptionSet,
    overrides: dict[str, float],
    data: dict,
    current_price: float,
) -> SliderResult:
    """Apply overrides to a cloned assumption set and run base-scenario DCF.

    All overrides are applied independently to the same clone (not sequential).
    Returns the base-scenario implied price and delta from unmodified base.
    """
    t0 = time.perf_counter()
    constraints: list[str] = []

    # --- Clone assumptions ---
    modified = _deep_clone_assumptions(base_assumption_set)

    # --- Compute unmodified base price ---
    base_result = DCFEngine.run(base_assumption_set, data, current_price)
    base_price = base_result.scenarios.get("base")
    unmodified_price = base_price.implied_price if base_price else 0.0

    # --- Apply all overrides ---
    for key, value in overrides.items():
        _apply_override(modified, key, value)

    # --- Enforce constraints ---
    if modified.scenarios:
        for scenario in [modified.scenarios.base, modified.scenarios.bull, modified.scenarios.bear]:
            if scenario.terminal_growth_rate >= scenario.wacc:
                old = scenario.terminal_growth_rate
                scenario.terminal_growth_rate = scenario.wacc - 0.01
                constraints.append(
                    f"terminal_growth capped: {old:.4f} → {scenario.terminal_growth_rate:.4f}"
                )

    # --- Run DCF (full result but we only use base scenario) ---
    result = DCFEngine.run(modified, data, current_price)
    base_sc = result.scenarios.get("base")
    implied_price = base_sc.implied_price if base_sc else 0.0
    ev = base_sc.enterprise_value if base_sc else 0.0

    delta = implied_price - unmodified_price
    delta_pct = delta / unmodified_price if unmodified_price else 0.0

    elapsed = (time.perf_counter() - t0) * 1000

    return SliderResult(
        implied_price=round(implied_price, 2),
        delta_from_base=round(delta, 2),
        delta_pct=round(delta_pct, 4),
        enterprise_value=round(ev, 2),
        overrides_applied=overrides,
        constraints_enforced=constraints,
        computation_time_ms=round(elapsed, 1),
    )


# ---------------------------------------------------------------------------
# Override application
# ---------------------------------------------------------------------------

def _apply_override(assumption_set: AssumptionSet, key: str, value: float) -> None:
    """Apply a single override identified by key path."""
    scenarios = assumption_set.scenarios
    if scenarios is None:
        return

    # Scenario-level overrides (applied to all scenarios)
    if key.startswith("scenarios.{s}."):
        field = key.replace("scenarios.{s}.", "")
        for scenario in [scenarios.base, scenarios.bull, scenarios.bear]:
            _set_scenario_field(scenario, field, value)

    # Model-assumption level overrides
    elif key.startswith("model_assumptions.dcf."):
        field = key.replace("model_assumptions.dcf.", "")
        dcf = assumption_set.model_assumptions.dcf
        if dcf and hasattr(dcf, field):
            setattr(dcf, field, value)


def _set_scenario_field(scenario, field: str, value: float) -> None:
    """Set a field on a ScenarioProjections, handling indexed arrays."""
    # Handle array[index] syntax: e.g. "revenue_growth_rates[0]"
    if "[" in field:
        attr_name, idx_str = field.split("[")
        idx = int(idx_str.rstrip("]"))
        arr = getattr(scenario, attr_name, None)
        if arr is not None and isinstance(arr, list) and idx < len(arr):
            # Curve shifting: apply delta to all elements
            if attr_name in ("revenue_growth_rates", "operating_margins"):
                original = arr[:]
                delta = value - original[idx]
                for i in range(len(arr)):
                    arr[i] = clamp(original[i] + delta, -0.10, 0.60)
            else:
                arr[idx] = value
    elif hasattr(scenario, field):
        setattr(scenario, field, value)


def _deep_clone_assumptions(a: AssumptionSet) -> AssumptionSet:
    """Deep copy an AssumptionSet to avoid mutating the original."""
    return AssumptionSet.model_validate(copy.deepcopy(a.model_dump(mode="python")))
