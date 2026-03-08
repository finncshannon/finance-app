"""WebSocket connection manager and background price refresh scheduler.

Manages real-time price streaming to connected frontend clients via WebSocket.
Two independent loops: price refresh (60s, market hours only) and status broadcast (30s, always).
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta

from fastapi import WebSocket

from services.market_data_service import MarketDataService
from repositories.market_data_repo import MarketDataRepo

logger = logging.getLogger("finance_app")

_STARTUP_MONOTONIC = time.monotonic()

PRICE_REFRESH_INTERVAL = 60    # seconds between price refreshes (market hours)
AFTER_HOURS_INTERVAL = 900     # 15 minutes (weekday after-hours)
WEEKEND_INTERVAL = 3600        # 1 hour (weekends)
STATUS_BROADCAST_INTERVAL = 30  # seconds between status broadcasts


# ======================================================================
# ConnectionManager — tracks WebSocket clients and ticker subscriptions
# ======================================================================

class ConnectionManager:
    """Manages WebSocket connections and per-client ticker subscriptions."""

    def __init__(self):
        # client_id -> WebSocket
        self._connections: dict[str, WebSocket] = {}
        # client_id -> set of subscribed tickers
        self._subscriptions: dict[str, set[str]] = {}

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Register a new WebSocket client."""
        await websocket.accept()
        self._connections[client_id] = websocket
        self._subscriptions[client_id] = set()
        logger.info("WebSocket client connected: %s", client_id)

    def disconnect(self, client_id: str) -> None:
        """Remove a client and its subscriptions."""
        self._connections.pop(client_id, None)
        self._subscriptions.pop(client_id, None)
        logger.info("WebSocket client disconnected: %s", client_id)

    def subscribe(self, client_id: str, tickers: list[str]) -> None:
        """Set the subscription list for a client (replaces previous)."""
        if client_id in self._subscriptions:
            self._subscriptions[client_id] = {t.upper() for t in tickers}
            logger.debug(
                "Client %s subscribed to %d tickers", client_id, len(tickers)
            )

    def get_all_subscribed_tickers(self) -> set[str]:
        """Return the union of all clients' subscribed tickers."""
        all_tickers: set[str] = set()
        for tickers in self._subscriptions.values():
            all_tickers.update(tickers)
        return all_tickers

    async def broadcast_prices(self, price_data: dict) -> None:
        """Send price_update to clients whose subscribed tickers overlap with the data."""
        if not price_data:
            return

        available_tickers = set(price_data.keys())
        disconnected: list[str] = []

        for client_id, ws in self._connections.items():
            client_tickers = self._subscriptions.get(client_id, set())
            relevant = client_tickers & available_tickers
            if not relevant:
                continue

            # Build per-client payload with only their subscribed tickers
            client_payload = {t: price_data[t] for t in relevant}
            message = {"type": "price_update", "data": client_payload}

            try:
                await ws.send_json(message)
            except Exception:
                logger.warning(
                    "Failed to send price_update to client %s — removing",
                    client_id,
                )
                disconnected.append(client_id)

        for cid in disconnected:
            self.disconnect(cid)

    async def broadcast_status(self, status_data: dict) -> None:
        """Send system_status to ALL connected clients."""
        message = {"type": "system_status", "data": status_data}
        disconnected: list[str] = []

        for client_id, ws in self._connections.items():
            try:
                await ws.send_json(message)
            except Exception:
                logger.warning(
                    "Failed to send system_status to client %s — removing",
                    client_id,
                )
                disconnected.append(client_id)

        for cid in disconnected:
            self.disconnect(cid)


# ======================================================================
# PriceRefreshService — background scheduler
# ======================================================================

class PriceRefreshService:
    """Background loops for refreshing prices and broadcasting status."""

    def __init__(
        self,
        market_data_svc: MarketDataService,
        connection_manager: ConnectionManager,
        status_manager: ConnectionManager,
    ):
        self.market_data_svc = market_data_svc
        self.connection_manager = connection_manager
        self.status_manager = status_manager

        self.last_refresh_time: datetime | None = None
        self.active_ticker_count: int = 0

    # ------------------------------------------------------------------
    # Price refresh loop — every 60s during market hours
    # ------------------------------------------------------------------

    async def run_refresh_loop(self) -> None:
        """Continuously refresh prices for all subscribed tickers.

        Tiered intervals: 60s market hours, 15min after-hours, 1hr weekends.
        """
        logger.info("Price refresh loop started")
        while True:
            # Determine interval based on market state
            if MarketDataService.is_market_open():
                interval = PRICE_REFRESH_INTERVAL
            elif self._is_weekend():
                interval = WEEKEND_INTERVAL
            else:
                interval = AFTER_HOURS_INTERVAL

            try:
                tickers = self.connection_manager.get_all_subscribed_tickers()
                if tickers:
                    ticker_list = sorted(tickers)
                    logger.info(
                        "Refreshing %d tickers (interval=%ds): %s",
                        len(ticker_list),
                        interval,
                        ", ".join(ticker_list),
                    )

                    await self.market_data_svc.refresh_batch(ticker_list)

                    # Build price_data from freshly cached values
                    price_data = await self._build_price_data(ticker_list)
                    await self.connection_manager.broadcast_prices(price_data)

                    self.last_refresh_time = datetime.now(timezone.utc)
                    self.active_ticker_count = len(ticker_list)
                else:
                    logger.debug("No subscribed tickers — skipping refresh")
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in price refresh loop")

            await asyncio.sleep(interval)

    @staticmethod
    def _is_weekend() -> bool:
        """Check if it's currently a weekend in US Eastern time."""
        try:
            from zoneinfo import ZoneInfo
            et = ZoneInfo("America/New_York")
        except ImportError:
            et = timezone(timedelta(hours=-5))
        now_et = datetime.now(et)
        return now_et.weekday() > 4

    # ------------------------------------------------------------------
    # Status broadcast loop — every 30s, always active
    # ------------------------------------------------------------------

    async def run_status_loop(self) -> None:
        """Continuously broadcast system status to all status-channel clients."""
        logger.info("Status broadcast loop started")
        while True:
            try:
                status = {
                    "market_open": MarketDataService.is_market_open(),
                    "last_price_refresh": (
                        self.last_refresh_time.isoformat()
                        if self.last_refresh_time
                        else None
                    ),
                    "active_refresh_tickers": self.active_ticker_count,
                    "api_calls_remaining": None,  # reserved for future rate-limit tracking
                    "backend_uptime_seconds": round(
                        time.monotonic() - _STARTUP_MONOTONIC, 1
                    ),
                }
                await self.status_manager.broadcast_status(status)
            except Exception:
                logger.exception("Error in status broadcast loop")

            await asyncio.sleep(STATUS_BROADCAST_INTERVAL)

    # ------------------------------------------------------------------
    # Initial snapshot — for new WS connections
    # ------------------------------------------------------------------

    async def get_initial_snapshot(self, tickers: list[str]) -> dict:
        """Fetch current cached prices for an initial WebSocket response."""
        return await self._build_price_data([t.upper() for t in tickers])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _build_price_data(self, tickers: list[str]) -> dict:
        """Read cached market data and return the frontend-expected dict format."""
        repo: MarketDataRepo = self.market_data_svc.market_repo
        rows = await repo.get_market_data_bulk(tickers)

        price_data: dict[str, dict] = {}
        for row in rows:
            ticker = row["ticker"]
            price_data[ticker] = {
                "current_price": row.get("current_price"),
                "day_change": row.get("day_change"),
                "day_change_pct": row.get("day_change_pct"),
                "volume": row.get("volume"),
                "updated_at": row.get("updated_at"),
            }
        return price_data


# ======================================================================
# Module-level singletons
# ======================================================================

price_ws_manager = ConnectionManager()   # for /ws/prices clients
status_ws_manager = ConnectionManager()  # for /ws/status clients (no ticker subscriptions needed)
