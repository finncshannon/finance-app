"""Pydantic models for all 4 sensitivity analysis modes."""

from __future__ import annotations

from pydantic import BaseModel, Field


# =========================================================================
# Slider Mode
# =========================================================================

class SensitivityParameterDef(BaseModel):
    """Definition of a sensitivity slider parameter."""
    name: str
    key_path: str
    param_type: str  # "float_pct" | "float_ratio" | "float_abs"
    min_val: float
    max_val: float
    step: float
    display_format: str  # e.g. "8.5%" or "12.0x"
    current_value: float | None = None


class SliderResult(BaseModel):
    implied_price: float
    delta_from_base: float
    delta_pct: float
    enterprise_value: float
    overrides_applied: dict[str, float] = Field(default_factory=dict)
    constraints_enforced: list[str] = Field(default_factory=list)
    computation_time_ms: float = 0.0


# =========================================================================
# Tornado Mode
# =========================================================================

class TornadoBar(BaseModel):
    variable_name: str
    variable_key: str
    base_value: float
    low_input: float
    high_input: float
    price_at_low_input: float
    price_at_high_input: float
    spread: float
    base_price: float


class TornadoResult(BaseModel):
    bars: list[TornadoBar] = Field(default_factory=list)
    base_price: float = 0.0
    current_price: float = 0.0
    variable_count: int = 0
    computation_time_ms: float = 0.0


# =========================================================================
# Monte Carlo
# =========================================================================

class MCParameterConfig(BaseModel):
    name: str
    distribution: str  # "normal" | "triangular" | "lognormal"
    mean: float | None = None
    std_dev: float | None = None
    mode: float | None = None
    min_val: float | None = None
    max_val: float | None = None


class MCStatistics(BaseModel):
    mean: float = 0.0
    median: float = 0.0
    std_dev: float = 0.0
    p5: float = 0.0
    p10: float = 0.0
    p25: float = 0.0
    p50: float = 0.0
    p75: float = 0.0
    p90: float = 0.0
    p95: float = 0.0
    prob_upside: float = 0.0
    prob_upside_15pct: float = 0.0
    prob_downside_15pct: float = 0.0
    var_5pct: float = 0.0


class HistogramBin(BaseModel):
    bin_start: float
    bin_end: float
    count: int
    frequency: float


class MCHistogram(BaseModel):
    bins: list[HistogramBin] = Field(default_factory=list)
    bin_count: int = 50
    range_min: float = 0.0
    range_max: float = 0.0
    outlier_count_low: int = 0
    outlier_count_high: int = 0


class MonteCarloResult(BaseModel):
    success: bool = True
    error: str | None = None
    statistics: MCStatistics | None = None
    histogram: MCHistogram | None = None
    distributions_used: list[MCParameterConfig] | None = None
    correlation_matrix: list[list[float]] | None = None
    iteration_count: int = 0
    valid_iterations: int = 0
    skipped_iterations: int = 0
    seed: int | None = None
    computation_time_ms: float = 0.0


# =========================================================================
# 2D Tables
# =========================================================================

class Table2DResult(BaseModel):
    row_variable: str
    col_variable: str
    row_values: list[float] = Field(default_factory=list)
    col_values: list[float] = Field(default_factory=list)
    price_matrix: list[list[float]] = Field(default_factory=list)
    upside_matrix: list[list[float]] = Field(default_factory=list)
    color_matrix: list[list[str]] = Field(default_factory=list)
    base_row_index: int = 0
    base_col_index: int = 0
    base_price: float = 0.0
    current_price: float = 0.0
    grid_size: int = 9
    computation_time_ms: float = 0.0
