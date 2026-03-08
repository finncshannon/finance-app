"""Provider registry — name-based lookup for data providers.

Usage:
    from providers.registry import provider_registry
    provider_registry.register("yahoo", YahooFinanceProvider())
    yf = provider_registry.get("yahoo")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from providers.base import DataProvider

logger = logging.getLogger("finance_app")


class ProviderRegistry:
    """Stores registered data providers by name for service-layer lookup."""

    def __init__(self) -> None:
        self._providers: dict[str, DataProvider] = {}

    def register(self, name: str, provider: DataProvider) -> None:
        self._providers[name] = provider
        logger.info("Registered data provider: %s", name)

    def get(self, name: str) -> DataProvider:
        if name not in self._providers:
            raise KeyError(f"No provider registered with name '{name}'. Available: {list(self._providers.keys())}")
        return self._providers[name]

    def list_providers(self) -> list[str]:
        return list(self._providers.keys())

    def has(self, name: str) -> bool:
        return name in self._providers


# Module-level singleton
provider_registry = ProviderRegistry()
