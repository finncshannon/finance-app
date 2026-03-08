"""2D sensitivity tables — grid of implied prices for variable pairs."""

from __future__ import annotations

import logging
import time

from engines import DCFEngine
from services.assumption_engine.models import AssumptionSet

from .models import Table2DResult
from .sliders import _deep_clone_assumptions, _apply_override

logger = logging.getLogger("finance_app")

# Named constants
TABLE_DEFAULT_STEPS = 9
TABLE_MIN_STEPS = 5
TABLE_MAX_STEPS = 13

# Default variable pairs
DEFAULT_PAIRS = [
    ("scenarios.{s}.wacc", "scenarios.{s}.terminal_growth_rate"),
    ("scenarios.{s}.wacc", "model_assumptions.dcf.terminal_exit_multiple"),
    ("scenarios.{s}.revenue_growth_rates[0]", "scenarios.{s}.operating_margins[0]"),
]

# Range limits per variable key
VARIABLE_RANGES: dict[str, tuple[float, float]] = {
    "scenarios.{s}.wacc": (0.04, 0.20),
    "scenarios.{s}.terminal_growth_rate": (0.00, 0.05),
    "scenarios.{s}.revenue_growth_rates[0]": (-0.10, 0.60),
    "scenarios.{s}.operating_margins[0]": (-0.20, 0.60),
    "model_assumptions.dcf.capex_to_revenue": (0.01, 0.25),
    "model_assumptions.dcf.tax_rate": (0.00, 0.40),
    "model_assumptions.dcf.terminal_exit_multiple": (4.0, 30.0),
    "model_assumptions.dcf.nwc_change_to_revenue": (-0.05, 0.10),
}

# Variable display names
VARIABLE_NAMES: dict[str, str] = {
    "scenarios.{s}.wacc": "WACC",
    "scenarios.{s}.terminal_growth_rate": "Terminal Growth",
    "scenarios.{s}.revenue_growth_rates[0]": "Revenue Growth Y1",
    "scenarios.{s}.operating_margins[0]": "Operating Margin Y1",
    "model_assumptions.dcf.capex_to_revenue": "CapEx / Revenue",
    "model_assumptions.dcf.tax_rate": "Tax Rate",
    "model_assumptions.dcf.terminal_exit_multiple": "Exit Multiple",
    "model_assumptions.dcf.nwc_change_to_revenue": "NWC / Revenue",
}

# Color thresholds
COLOR_TIERS = [
    (0.20, "bright_green"),
    (0.10, "green"),
    (0.00, "light_green"),
    (-0.10, "light_red"),
    (-0.20, "red"),
]
COLOR_WORST = "bright_red"


def build_2d_table(
    assumption_set: AssumptionSet,
    data: dict,
    current_price: float,
    row_key: str | None = None,
    col_key: str | None = None,
    n_steps: int = TABLE_DEFAULT_STEPS,
    row_min: float | None = None,
    row_max: float | None = None,
    col_min: float | None = None,
    col_max: float | None = None,
) -> Table2DResult:
    """Build a 2D sensitivity grid of implied prices."""
    t0 = time.perf_counter()

    # Default to WACC × Terminal Growth
    if row_key is None:
        row_key = DEFAULT_PAIRS[0][0]
    if col_key is None:
        col_key = DEFAULT_PAIRS[0][1]

    n_steps = max(TABLE_MIN_STEPS, min(n_steps, TABLE_MAX_STEPS))

    # Get base values
    from .tornado import _get_base_value
    row_base = _get_base_value(assumption_set, row_key)
    col_base = _get_base_value(assumption_set, col_key)

    if row_base is None or col_base is None:
        return Table2DResult(
            row_variable=VARIABLE_NAMES.get(row_key, row_key),
            col_variable=VARIABLE_NAMES.get(col_key, col_key),
            current_price=current_price,
        )

    # Build step arrays
    row_range = VARIABLE_RANGES.get(row_key, (row_base * 0.5, row_base * 1.5))
    col_range = VARIABLE_RANGES.get(col_key, (col_base * 0.5, col_base * 1.5))

    # Override with custom ranges if provided
    if row_min is not None and row_max is not None:
        if row_min >= row_max:
            raise ValueError(f"row_min ({row_min}) must be less than row_max ({row_max})")
        row_range = (row_min, row_max)
    if col_min is not None and col_max is not None:
        if col_min >= col_max:
            raise ValueError(f"col_min ({col_min}) must be less than col_max ({col_max})")
        col_range = (col_min, col_max)

    row_values = build_centered_steps(row_base, row_range[0], row_range[1], n_steps)
    col_values = build_centered_steps(col_base, col_range[0], col_range[1], n_steps)

    # Find base indices (closest to base value)
    base_row_idx = _find_closest(row_values, row_base)
    base_col_idx = _find_closest(col_values, col_base)

    # Get base price
    base_result = DCFEngine.run(assumption_set, data, current_price)
    base_sc = base_result.scenarios.get("base")
    base_price = base_sc.implied_price if base_sc else 0.0

    # Fill grid (N×N engine runs)
    price_matrix: list[list[float]] = []
    upside_matrix: list[list[float]] = []
    color_matrix: list[list[str]] = []

    for r_val in row_values:
        price_row: list[float] = []
        upside_row: list[float] = []
        color_row: list[str] = []

        for c_val in col_values:
            modified = _deep_clone_assumptions(assumption_set)
            _apply_override(modified, row_key, r_val)
            _apply_override(modified, col_key, c_val)

            # Enforce terminal growth < wacc
            if modified.scenarios:
                for sc in [modified.scenarios.base, modified.scenarios.bull, modified.scenarios.bear]:
                    if sc.terminal_growth_rate >= sc.wacc:
                        sc.terminal_growth_rate = sc.wacc - 0.01

            result = DCFEngine.run(modified, data, current_price)
            sc = result.scenarios.get("base")
            price = sc.implied_price if sc else 0.0

            upside = (price / current_price - 1) if current_price > 0 else 0
            color = _cell_color(upside)

            price_row.append(round(price, 2))
            upside_row.append(round(upside, 4))
            color_row.append(color)

        price_matrix.append(price_row)
        upside_matrix.append(upside_row)
        color_matrix.append(color_row)

    elapsed = (time.perf_counter() - t0) * 1000

    return Table2DResult(
        row_variable=VARIABLE_NAMES.get(row_key, row_key),
        col_variable=VARIABLE_NAMES.get(col_key, col_key),
        row_values=[round(v, 6) for v in row_values],
        col_values=[round(v, 6) for v in col_values],
        price_matrix=price_matrix,
        upside_matrix=upside_matrix,
        color_matrix=color_matrix,
        base_row_index=base_row_idx,
        base_col_index=base_col_idx,
        base_price=round(base_price, 2),
        current_price=current_price,
        grid_size=n_steps,
        computation_time_ms=round(elapsed, 1),
    )


def build_centered_steps(
    base: float,
    range_min: float,
    range_max: float,
    n_steps: int,
) -> list[float]:
    """Build N evenly-spaced steps centered on base value within range."""
    step_size = (range_max - range_min) / (n_steps - 1)
    half = n_steps // 2
    start = max(base - half * step_size, range_min)
    end = start + (n_steps - 1) * step_size
    if end > range_max:
        end = range_max
        start = end - (n_steps - 1) * step_size
    return [round(start + i * step_size, 6) for i in range(n_steps)]


def _cell_color(upside_pct: float) -> str:
    """Map upside percentage to 7-tier color."""
    for threshold, color in COLOR_TIERS:
        if upside_pct >= threshold:
            return color
    return COLOR_WORST


def _find_closest(values: list[float], target: float) -> int:
    """Find index of closest value to target."""
    return min(range(len(values)), key=lambda i: abs(values[i] - target))
