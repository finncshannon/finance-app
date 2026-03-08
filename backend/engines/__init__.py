"""Valuation Engines — DCF, DDM, Comps, Revenue-Based.

Each engine consumes an AssumptionSet and produces a valuation result.
"""

from .dcf_engine import DCFEngine
from .ddm_engine import DDMEngine
from .comps_engine import CompsEngine
from .revbased_engine import RevBasedEngine
from .base_model import BaseValuationModel
from .registry import engine_registry

# Register all built-in engines
engine_registry.register(DCFEngine)
engine_registry.register(DDMEngine)
engine_registry.register(CompsEngine)
engine_registry.register(RevBasedEngine)

__all__ = [
    "DCFEngine", "DDMEngine", "CompsEngine", "RevBasedEngine",
    "BaseValuationModel", "engine_registry",
]
