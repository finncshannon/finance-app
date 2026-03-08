"""Engine Configuration — defaults with settings overrides.

EngineConfig holds all tunable parameters. Loads overrides from
the Settings service if available.
"""

from __future__ import annotations

import logging
from pydantic import BaseModel

logger = logging.getLogger("finance_app")


class EngineConfig(BaseModel):
    """Configurable parameters for the Assumption Engine."""

    projection_years: int = 5
    erp: float = 0.055
    default_risk_free: float = 0.04
    terminal_growth_gdp_proxy: float = 0.025
    blume_adjustment: bool = True

    # Scenario weights (can override uncertainty-based defaults)
    base_weight: float | None = None
    bull_weight: float | None = None
    bear_weight: float | None = None

    # Monte Carlo (future use)
    monte_carlo_iterations: int = 10000

    @classmethod
    async def from_settings(cls, settings_service=None) -> "EngineConfig":
        """Load config, merging defaults with any settings overrides."""
        config = cls()

        if settings_service is None:
            return config

        try:
            overrides = await settings_service.get("assumption_engine")
            if overrides and isinstance(overrides, dict):
                for key, value in overrides.items():
                    if hasattr(config, key):
                        setattr(config, key, value)
                logger.info(
                    "Loaded %d engine config overrides from settings",
                    len(overrides),
                )
        except Exception as exc:
            logger.debug("No engine config in settings: %s", exc)

        return config
