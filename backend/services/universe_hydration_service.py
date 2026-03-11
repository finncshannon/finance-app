"""Universe hydration service — background fetch of market data & financials.

Progressively fetches data for all curated universe tickers so the
scanner has real data to filter on. Runs in priority order:
DOW (30) → S&P 500 (~500) → Russell 3000 (~3000).
"""

import asyncio
import logging
import time
from datetime import datetime, timezone

from db.connection import DatabaseConnection
from services.market_data_service import MarketDataService, FINANCIAL_STALE_SECONDS
from services.universe_service import UniverseService
from providers.exceptions import RateLimitError, ProviderError

logger = logging.getLogger("finance_app")

HYDRATION_TIERS = [
    {"name": "dow", "label": "DOW 30", "priority": 1},
    {"name": "sp500", "label": "S&P 500", "priority": 2},
    {"name": "r3000", "label": "Russell 3000", "priority": 3},
]

FETCH_DELAY = 1.8  # ~2000/hr = one every 1.8s


class HydrationProgress:
    """Tracks the state of a hydration run."""

    def __init__(self):
        self.status = "idle"
        self.current_tier = None
        self.current_ticker = None
        self.tickers_total = 0
        self.tickers_done = 0
        self.tickers_skipped = 0
        self.tickers_failed = 0
        self.started_at = None
        self.elapsed_ms = 0

    def to_dict(self) -> dict:
        pct = 0.0
        if self.tickers_total > 0:
            pct = round((self.tickers_done + self.tickers_skipped + self.tickers_failed) / self.tickers_total * 100, 1)
        return {
            "status": self.status,
            "current_tier": self.current_tier,
            "current_ticker": self.current_ticker,
            "tickers_total": self.tickers_total,
            "tickers_done": self.tickers_done,
            "tickers_skipped": self.tickers_skipped,
            "tickers_failed": self.tickers_failed,
            "started_at": self.started_at,
            "elapsed_ms": self.elapsed_ms,
            "progress_pct": pct,
        }


class UniverseHydrationService:
    """Background service that fetches market data for all universe tickers."""

    def __init__(
        self,
        db: DatabaseConnection,
        market_data_svc: MarketDataService,
        universe_svc: UniverseService,
    ):
        self.db = db
        self.market_data_svc = market_data_svc
        self.universe_svc = universe_svc
        self.progress = HydrationProgress()
        self._running = False

    async def run_hydration(self):
        """Run hydration across all tiers: DOW → S&P 500 → R3000."""
        if self._running:
            logger.warning("Hydration already running, skipping.")
            return

        self._running = True
        self.progress = HydrationProgress()
        self.progress.status = "running"
        self.progress.started_at = datetime.now(timezone.utc).isoformat()
        t0 = time.monotonic()

        try:
            # Compute total unique tickers across all tiers
            all_tickers: set[str] = set()
            for tier in HYDRATION_TIERS:
                tickers = await self.universe_svc.get_universe_tickers(tier["name"])
                all_tickers.update(tickers)
            self.progress.tickers_total = len(all_tickers)

            # Track which tickers we've already processed (dedup across tiers)
            processed: set[str] = set()

            for tier in HYDRATION_TIERS:
                self.progress.current_tier = tier["label"]
                tickers = await self.universe_svc.get_universe_tickers(tier["name"])
                tier_count = 0

                for ticker in tickers:
                    if ticker in processed:
                        continue
                    processed.add(ticker)

                    self.progress.current_ticker = ticker

                    # Check rate limiter capacity
                    await self._check_rate_limiter()

                    # Check if ticker needs hydration
                    if not await self._needs_hydration(ticker):
                        self.progress.tickers_skipped += 1
                        continue

                    # Hydrate with retry on rate limit
                    try:
                        await self._hydrate_ticker(ticker)
                        self.progress.tickers_done += 1
                        tier_count += 1
                    except RateLimitError as e:
                        backoff = (e.retry_after or 60) + 5
                        logger.info(
                            "Rate limit hit during hydration, backing off %.0fs",
                            backoff,
                        )
                        await asyncio.sleep(backoff)
                        # Retry once
                        try:
                            await self._hydrate_ticker(ticker)
                            self.progress.tickers_done += 1
                            tier_count += 1
                        except Exception:
                            self.progress.tickers_failed += 1
                            logger.debug("Retry failed for %s", ticker)
                    except Exception as exc:
                        self.progress.tickers_failed += 1
                        logger.debug("Hydration failed for %s: %s", ticker, exc)

                    await asyncio.sleep(FETCH_DELAY)

                done_so_far = self.progress.tickers_done + self.progress.tickers_skipped + self.progress.tickers_failed
                logger.info(
                    "Hydrating %s: %d/%d tickers... (%d done total)",
                    tier["label"],
                    tier_count,
                    len(tickers),
                    done_so_far,
                )

            self.progress.status = "complete"

        except asyncio.CancelledError:
            self.progress.status = "cancelled"
            raise
        except Exception as exc:
            self.progress.status = "error"
            logger.error("Hydration failed: %s", exc)
        finally:
            self.progress.elapsed_ms = int((time.monotonic() - t0) * 1000)
            self.progress.current_ticker = None
            self._running = False

    async def _needs_hydration(self, ticker: str) -> bool:
        """Return True if ticker has no market_data or data is older than FINANCIAL_STALE_SECONDS."""
        md_row = await self.db.fetchone(
            "SELECT updated_at FROM cache.market_data WHERE ticker = ?", (ticker,)
        )
        if md_row and md_row.get("updated_at"):
            try:
                fetched = datetime.fromisoformat(md_row["updated_at"])
                age = (datetime.now(timezone.utc) - fetched).total_seconds()
                if age < FINANCIAL_STALE_SECONDS:
                    return False
            except (ValueError, TypeError):
                pass
        return True

    async def _hydrate_ticker(self, ticker: str):
        """Fetch market quote + financials via MarketDataService (cache-first)."""
        try:
            await self.market_data_svc.get_quote(ticker)
        except ProviderError:
            pass
        try:
            await self.market_data_svc.get_financials(ticker)
        except ProviderError:
            pass

    async def _check_rate_limiter(self):
        """Check Yahoo rate limiter capacity and pause if low."""
        try:
            from providers.yahoo_finance import _rate_limiter

            remaining = _rate_limiter.remaining
            if remaining < 50:
                logger.info(
                    "Rate limiter low (%d remaining), pausing hydration 60s",
                    remaining,
                )
                self.progress.status = "paused"
                await asyncio.sleep(60)
                self.progress.status = "running"
        except ImportError:
            pass
