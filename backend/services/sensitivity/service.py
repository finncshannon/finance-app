"""SensitivityService — orchestrates all 4 sensitivity analysis modes."""

from __future__ import annotations

import logging

from services.assumption_engine.models import AssumptionSet

from .models import SliderResult, TornadoResult, MonteCarloResult, Table2DResult
from .parameter_defs import get_dcf_parameter_defs
from .sliders import slider_recalculate
from .tornado import calculate_tornado
from .monte_carlo import run_monte_carlo
from .tables_2d import build_2d_table

logger = logging.getLogger("finance_app")


class SensitivityService:
    """Orchestrates slider, tornado, Monte Carlo, and 2D table analyses."""

    def __init__(self, settings_service=None):
        self._settings = settings_service

    async def run_slider(
        self,
        assumption_set: AssumptionSet,
        overrides: dict[str, float],
        data: dict,
        current_price: float,
    ) -> SliderResult:
        """Recalculate DCF with slider overrides."""
        return slider_recalculate(assumption_set, overrides, data, current_price)

    async def run_tornado(
        self,
        assumption_set: AssumptionSet,
        data: dict,
        current_price: float,
    ) -> TornadoResult:
        """Generate tornado chart data."""
        return calculate_tornado(assumption_set, data, current_price)

    async def run_monte_carlo(
        self,
        assumption_set: AssumptionSet,
        data: dict,
        current_price: float,
        iterations: int | None = None,
        seed: int | None = None,
    ) -> MonteCarloResult:
        """Run Monte Carlo simulation."""
        if iterations is None:
            iterations = 10_000
            if self._settings:
                try:
                    val = await self._settings.get_setting("monte_carlo_iterations")
                    if val is not None:
                        iterations = int(val)
                except Exception:
                    pass
        return run_monte_carlo(assumption_set, data, current_price, iterations, seed)

    async def run_table_2d(
        self,
        assumption_set: AssumptionSet,
        data: dict,
        current_price: float,
        row_variable: str | None = None,
        col_variable: str | None = None,
        grid_size: int = 9,
        row_min: float | None = None,
        row_max: float | None = None,
        col_min: float | None = None,
        col_max: float | None = None,
    ) -> Table2DResult:
        """Generate 2D sensitivity table."""
        return build_2d_table(
            assumption_set, data, current_price,
            row_key=row_variable,
            col_key=col_variable,
            n_steps=grid_size,
            row_min=row_min,
            row_max=row_max,
            col_min=col_min,
            col_max=col_max,
        )

    def get_parameter_definitions(self):
        """Return parameter definitions for the frontend."""
        return get_dcf_parameter_defs()
