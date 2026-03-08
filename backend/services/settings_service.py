"""Settings service — business logic layer between router and repo.

Handles default seeding, JSON serialization for complex values,
and wraps SettingsRepo calls.
"""

import logging

from db.connection import DatabaseConnection
from repositories.settings_repo import SettingsRepo

logger = logging.getLogger("finance_app")

DEFAULT_SETTINGS: dict[str, str] = {
    "startup_module": "dashboard",
    "window_state": '{"width":1400,"height":900,"x":100,"y":50,"maximized":false}',
    "boot_animation_enabled": "true",
    "sound_enabled": "true",
    "refresh_interval_seconds": "60",
    "market_hours_only": "true",
    "sec_edgar_email": "",
    "auto_fetch_filings": "true",
    "filing_retention_years": "5",
    "backup_enabled": "true",
    "backup_retention_days": "30",
    "default_erp": "0.055",
    "size_premium_enabled": "true",
    "risk_free_rate_source": "auto",
    "risk_free_rate_manual": "",
    "default_projection_years": "10",
    "terminal_growth_source": "auto",
    "terminal_growth_manual": "",
    "scenario_weights_3": "[0.25, 0.50, 0.25]",
    "scenario_weights_5": "[0.10, 0.20, 0.40, 0.20, 0.10]",
    "monte_carlo_iterations": "10000",
    "reasoning_verbosity": "summary",
    "default_benchmark": "SPY",
    "tax_lot_method": "fifo",
    "scanner_auto_add": "true",
    "scanner_default_limit": "50",
    "scanner_default_columns": '["ticker","company_name","sector","market_cap","pe_trailing","revenue_growth","dividend_yield"]',
}


class SettingsService:

    def __init__(self, db: DatabaseConnection):
        self.repo = SettingsRepo(db)

    async def seed_defaults(self) -> int:
        """Insert default settings for any keys that don't already exist.

        Returns the number of keys seeded.
        """
        existing = await self.repo.get_all()
        to_seed = {k: v for k, v in DEFAULT_SETTINGS.items() if k not in existing}

        if to_seed:
            await self.repo.set_many(to_seed)
            logger.info("Seeded %d default settings keys.", len(to_seed))

        return len(to_seed)

    async def get_all(self) -> dict[str, str]:
        return await self.repo.get_all()

    async def get(self, key: str) -> str | None:
        return await self.repo.get(key)

    async def set(self, key: str, value: str) -> None:
        await self.repo.set(key, value)

    async def set_many(self, updates: dict[str, str]) -> None:
        await self.repo.set_many(updates)

    async def delete(self, key: str) -> bool:
        return await self.repo.delete(key)
