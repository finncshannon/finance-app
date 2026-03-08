"""Business logic for watchlist management.

Uses WatchlistRepo for CRUD. Enforces limits and enriches items with live prices.
"""

from __future__ import annotations

import logging

from db.connection import DatabaseConnection
from repositories.watchlist_repo import WatchlistRepo
from services.market_data_service import MarketDataService

logger = logging.getLogger("finance_app")

MAX_WATCHLISTS = 20
MAX_ITEMS_PER_WATCHLIST = 100


class WatchlistService:

    def __init__(
        self,
        db: DatabaseConnection,
        repo: WatchlistRepo,
        market_data_svc: MarketDataService,
    ):
        self.db = db
        self.repo = repo
        self.mds = market_data_svc

    async def get_all_watchlists(self) -> list[dict]:
        """Return watchlists with item_count."""
        watchlists = await self.repo.get_all_watchlists()
        result = []
        for wl in watchlists:
            items = await self.repo.get_items(wl["id"])
            result.append({
                "id": wl["id"],
                "name": wl["name"],
                "sort_order": wl.get("sort_order", 0),
                "item_count": len(items),
            })
        return result

    async def get_watchlist(self, watchlist_id: int) -> dict | None:
        """Return watchlist with enriched items."""
        wl = await self.repo.get_watchlist(watchlist_id)
        if not wl:
            return None
        items = await self.repo.get_items(watchlist_id)
        enriched = []
        for item in items:
            enriched.append(await self._enrich_item(item))
        return {
            "id": wl["id"],
            "name": wl["name"],
            "items": enriched,
        }

    async def create_watchlist(self, name: str) -> dict:
        """Create watchlist, enforcing 20-list max."""
        if not name or not name.strip():
            raise ValueError("Watchlist name cannot be empty")
        existing = await self.repo.get_all_watchlists()
        if len(existing) >= MAX_WATCHLISTS:
            raise ValueError(f"Maximum {MAX_WATCHLISTS} watchlists allowed")
        wl = await self.repo.create_watchlist(name.strip())
        return {
            "id": wl["id"],
            "name": wl["name"],
            "sort_order": wl.get("sort_order", 0),
            "item_count": 0,
        }

    async def update_watchlist(self, watchlist_id: int, data: dict) -> dict | None:
        """Update name or sort_order."""
        updated = await self.repo.update_watchlist(watchlist_id, data)
        if not updated:
            return None
        items = await self.repo.get_items(watchlist_id)
        return {
            "id": updated["id"],
            "name": updated["name"],
            "sort_order": updated.get("sort_order", 0),
            "item_count": len(items),
        }

    async def delete_watchlist(self, watchlist_id: int) -> bool:
        return await self.repo.delete_watchlist(watchlist_id)

    async def add_item(self, watchlist_id: int, ticker: str) -> dict:
        """Add ticker to watchlist, enforcing 100-item max."""
        ticker = ticker.upper().strip()
        if not ticker:
            raise ValueError("Ticker cannot be empty")
        items = await self.repo.get_items(watchlist_id)
        if len(items) >= MAX_ITEMS_PER_WATCHLIST:
            raise ValueError(f"Maximum {MAX_ITEMS_PER_WATCHLIST} items per watchlist")
        item = await self.repo.add_item(watchlist_id, ticker)
        return await self._enrich_item(item)

    async def remove_item(self, watchlist_id: int, ticker: str) -> bool:
        return await self.repo.remove_item(watchlist_id, ticker.upper().strip())

    async def reorder_items(
        self, watchlist_id: int, ticker_order: list[str],
    ) -> bool:
        """Update sort_order for all items based on provided ticker list."""
        for idx, ticker in enumerate(ticker_order):
            await self.db.execute(
                "UPDATE watchlist_items SET sort_order = ? WHERE watchlist_id = ? AND ticker = ?",
                (idx, watchlist_id, ticker.upper()),
            )
        await self.db.commit()
        return True

    async def _enrich_item(self, item: dict) -> dict:
        """Enrich a watchlist item row with live market data."""
        ticker = item["ticker"]
        result: dict = {
            "ticker": ticker,
            "company_name": None,
            "current_price": None,
            "day_change": None,
            "day_change_pct": None,
            "pe_ratio": None,
            "market_cap": None,
            "volume": None,
            "added_at": item.get("added_at", ""),
        }

        company = await self.db.fetchone(
            "SELECT company_name FROM companies WHERE ticker = ?", (ticker,),
        )
        if company:
            result["company_name"] = company.get("company_name")

        quote = await self.mds.get_quote(ticker)
        if quote:
            result["current_price"] = quote.get("current_price")
            result["day_change"] = quote.get("day_change")
            result["day_change_pct"] = quote.get("day_change_pct")
            result["pe_ratio"] = quote.get("pe_trailing")
            result["market_cap"] = quote.get("market_cap")
            result["volume"] = quote.get("volume")

        return result
