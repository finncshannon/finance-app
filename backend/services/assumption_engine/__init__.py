"""Assumption Engine — generates valuation assumptions from financial data.

Pipeline: GATHER → ANALYZE → SYNTHESIZE → OUTPUT
"""

from .pipeline import AssumptionEngine
from .monte_carlo import generate_assumptions_monte_carlo

__all__ = ["AssumptionEngine", "generate_assumptions_monte_carlo"]
