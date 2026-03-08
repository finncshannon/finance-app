"""Abstract base class for valuation engines — plugin architecture contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from services.assumption_engine.models import AssumptionSet


class BaseValuationModel(ABC):
    """Abstract interface that all valuation engines must implement.

    To add a new valuation model:
    1. Subclass BaseValuationModel
    2. Implement all abstract methods
    3. Register via engine_registry.register(YourEngine)
    """

    model_type: str  # e.g. "dcf", "ddm", "comps", "revenue_based"
    display_name: str  # e.g. "DCF", "DDM", "Comps", "Revenue-Based"

    @staticmethod
    @abstractmethod
    def run(assumption_set: AssumptionSet, data: dict, current_price: float, **kwargs) -> Any:
        """Run the valuation calculation.

        Args:
            assumption_set: Full assumption set from the Assumption Engine.
            data: Dict with 'annual_financials' (list of dicts) and 'quote_data'.
            current_price: Current market price per share.

        Returns:
            A Pydantic model (e.g. DCFResult, DDMResult) with full valuation output.
        """
        ...

    @staticmethod
    @abstractmethod
    def get_required_assumptions() -> list[str]:
        """Return list of assumption keys this engine requires.

        Example: ["model_assumptions.dcf.wacc", "scenarios.base.revenue_growth_rates"]
        """
        ...

    @staticmethod
    @abstractmethod
    def validate_assumptions(assumption_set: AssumptionSet) -> list[str]:
        """Validate that the assumption set has all required data for this engine.

        Returns:
            List of error messages. Empty list means assumptions are valid.
        """
        ...
