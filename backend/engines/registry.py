"""Engine registry — central lookup for all valuation engine classes."""

from __future__ import annotations

import logging

logger = logging.getLogger("finance_app")


class EngineRegistry:
    """Singleton registry mapping model_type → engine class."""

    _engines: dict[str, type] = {}

    @classmethod
    def register(cls, engine_class: type) -> None:
        model_type = getattr(engine_class, "model_type", None)
        if not model_type:
            raise ValueError(f"{engine_class.__name__} missing 'model_type' class attribute")
        cls._engines[model_type] = engine_class
        logger.debug("Registered engine: %s → %s", model_type, engine_class.__name__)

    @classmethod
    def get(cls, model_type: str) -> type | None:
        return cls._engines.get(model_type)

    @classmethod
    def all(cls) -> dict[str, type]:
        return dict(cls._engines)

    @classmethod
    def list_types(cls) -> list[str]:
        return list(cls._engines.keys())


engine_registry = EngineRegistry()
