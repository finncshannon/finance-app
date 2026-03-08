"""Company events service — fetches earnings dates, ex-dividend dates,
and other corporate events from Yahoo Finance and caches them locally.

Uses yfinance Ticker objects to pull calendar and info data, then
persists via MarketDataRepo.upsert_event().
"""

import asyncio
import logging
from datetime import datetime, timezone

from db.connection import DatabaseConnection
from repositories.market_data_repo import MarketDataRepo

logger = logging.getLogger("finance_app")


class CompanyEventsService:
    """Fetches and caches corporate events (earnings, dividends) for tickers."""

    def __init__(self, db: DatabaseConnection, market_data_svc):
        """Initialise with database connection and MarketDataService.

        Args:
            db: Active DatabaseConnection instance.
            market_data_svc: MarketDataService (used for provider reference).
        """
        self.db = db
        self.market_repo = MarketDataRepo(db)
        self.market_svc = market_data_svc
        self._refresh_progress: dict = {
            "phase": "idle", "done": 0, "total": 0, "stale_count": 0,
        }

    # ------------------------------------------------------------------
    # Core: fetch events for a single ticker
    # ------------------------------------------------------------------

    async def fetch_events(self, ticker: str) -> list[dict]:
        """Fetch earnings and dividend events from Yahoo Finance for *ticker*.

        Returns list of event dicts that were stored (may be empty).
        """
        ticker = ticker.upper()
        events: list[dict] = []

        try:
            import yfinance  # noqa: local import to avoid hard dependency

            t = await asyncio.to_thread(yfinance.Ticker, ticker)
            calendar = await asyncio.to_thread(lambda: t.calendar)
            info = await asyncio.to_thread(lambda: t.info)

            # --- Earnings events ---
            events.extend(self._parse_earnings(ticker, calendar, info))

            # --- Ex-dividend event ---
            events.extend(self._parse_dividend(ticker, info))

            # Persist all events
            for ev in events:
                await self.market_repo.upsert_event(ev)

            logger.info(
                "Fetched %d event(s) for %s", len(events), ticker
            )
        except Exception as exc:
            logger.warning("Error fetching events for %s: %s", ticker, exc)
            return []

        return events

    # ------------------------------------------------------------------
    # Batch fetch
    # ------------------------------------------------------------------

    async def fetch_events_batch(self, tickers: list[str]) -> int:
        """Fetch events for multiple tickers sequentially.

        Returns total count of events stored across all tickers.
        """
        total = 0
        for ticker in tickers:
            result = await self.fetch_events(ticker)
            total += len(result)
        return total

    # ------------------------------------------------------------------
    # Read helpers (delegate to repo)
    # ------------------------------------------------------------------

    async def get_upcoming_events(self, limit: int = 20) -> list[dict]:
        """Return upcoming events across all tickers."""
        return await self.market_repo.get_upcoming_events(limit)

    async def get_events_for_ticker(self, ticker: str) -> list[dict]:
        """Return all cached events for a single ticker."""
        return await self.market_repo.get_events(ticker)

    # ------------------------------------------------------------------
    # Background startup fetch
    # ------------------------------------------------------------------

    async def _is_stale(self, ticker: str, max_age_days: int = 7) -> bool:
        """Check if events for ticker need refreshing."""
        from datetime import timedelta

        row = await self.db.fetchone(
            """SELECT MAX(fetched_at) as last_fetch
               FROM cache.company_events WHERE ticker = ?""",
            (ticker.upper(),),
        )
        if not row or not row["last_fetch"]:
            return True
        try:
            last = datetime.fromisoformat(row["last_fetch"])
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - last) > timedelta(days=max_age_days)
        except (ValueError, TypeError):
            return True

    async def get_tickers_needing_refresh(
        self, tickers: list[str], max_age_days: int = 7,
    ) -> list[str]:
        """Return subset of tickers whose events are stale."""
        stale = []
        for t in tickers:
            if await self._is_stale(t, max_age_days):
                stale.append(t)
        return stale

    async def run_startup_fetch(self, portfolio_svc, watchlist_svc, universe_svc):
        """Background task: proactively fetch events for portfolio, watchlist, S&P 500."""
        try:
            # 1. Gather tickers by source
            portfolio_tickers: set[str] = set()
            watchlist_tickers: set[str] = set()
            sp500_tickers: set[str] = set()

            try:
                positions = await portfolio_svc.get_all_positions()
                portfolio_tickers = {p.ticker for p in positions}
            except Exception as e:
                logger.warning("Startup fetch: failed to get portfolio tickers: %s", e)

            try:
                wls = await watchlist_svc.get_all_watchlists()
                for wl in wls:
                    detail = await watchlist_svc.get_watchlist(wl["id"])
                    if detail and "items" in detail:
                        for item in detail["items"]:
                            watchlist_tickers.add(item["ticker"])
            except Exception as e:
                logger.warning("Startup fetch: failed to get watchlist tickers: %s", e)

            try:
                sp500_tickers = set(universe_svc.get_sp500_tickers())
            except Exception as e:
                logger.warning("Startup fetch: failed to get S&P 500 tickers: %s", e)

            # 2. Deduplicate and process in priority order
            await self._fetch_phase("portfolio", list(portfolio_tickers))

            wl_only = watchlist_tickers - portfolio_tickers
            await self._fetch_phase("watchlist", list(wl_only))

            sp_only = sp500_tickers - portfolio_tickers - watchlist_tickers
            await self._fetch_phase("sp500", list(sp_only), delay_ms=100)

            self._refresh_progress = {
                "phase": "idle", "done": 0, "total": 0, "stale_count": 0,
            }
            logger.info("Startup event fetch complete.")

        except Exception as exc:
            logger.error("Startup event fetch failed: %s", exc)
            self._refresh_progress["phase"] = "idle"

    async def _fetch_phase(
        self, phase_name: str, tickers: list[str], delay_ms: int = 0,
    ):
        """Fetch events for a list of tickers, updating progress."""
        if not tickers:
            return

        stale = await self.get_tickers_needing_refresh(tickers)
        self._refresh_progress = {
            "phase": phase_name,
            "done": 0,
            "total": len(stale),
            "stale_count": len(stale),
        }
        logger.info(
            "Event refresh [%s]: %d/%d tickers stale",
            phase_name, len(stale), len(tickers),
        )

        for i, ticker in enumerate(stale):
            try:
                await self.fetch_events(ticker)
            except Exception as e:
                logger.debug("Event fetch failed for %s: %s", ticker, e)
            self._refresh_progress["done"] = i + 1
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)

    # ------------------------------------------------------------------
    # Internal parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_earnings(ticker: str, calendar, info: dict) -> list[dict]:
        """Extract earnings event(s) from yfinance calendar and info."""
        events: list[dict] = []

        # calendar may be a pandas DataFrame, a dict, or None
        if calendar is not None:
            try:
                import pandas as pd

                if isinstance(calendar, pd.DataFrame):
                    # DataFrame: columns are dates, index are labels
                    # Try to extract 'Earnings Date' row
                    if "Earnings Date" in calendar.index:
                        dates_row = calendar.loc["Earnings Date"]
                        for val in dates_row:
                            date_str = _timestamp_to_iso(val)
                            if date_str:
                                events.append(
                                    _build_event(
                                        ticker, "earnings", date_str,
                                        description="Earnings",
                                        is_estimated=1,
                                    )
                                )
                    # Also check for columns that look like dates
                    if not events:
                        for col in calendar.columns:
                            date_str = _timestamp_to_iso(col)
                            if date_str:
                                events.append(
                                    _build_event(
                                        ticker, "earnings", date_str,
                                        description="Earnings",
                                        is_estimated=1,
                                    )
                                )
                elif isinstance(calendar, dict):
                    # Dict: look for 'Earnings Date' key (list of Timestamps)
                    earnings_dates = calendar.get("Earnings Date", [])
                    if not isinstance(earnings_dates, list):
                        earnings_dates = [earnings_dates]
                    for val in earnings_dates:
                        date_str = _timestamp_to_iso(val)
                        if date_str:
                            events.append(
                                _build_event(
                                    ticker, "earnings", date_str,
                                    description="Earnings",
                                    is_estimated=1,
                                )
                            )

                    # Check for Earnings High/Low as confirmation signal
                    earnings_avg = calendar.get("Earnings Average")
                    if earnings_avg is not None and events:
                        events[0]["description"] = (
                            f"Earnings (est. EPS {earnings_avg})"
                        )
            except ImportError:
                # pandas not available — try dict-style parsing only
                if isinstance(calendar, dict):
                    earnings_dates = calendar.get("Earnings Date", [])
                    if not isinstance(earnings_dates, list):
                        earnings_dates = [earnings_dates]
                    for val in earnings_dates:
                        date_str = _timestamp_to_iso(val)
                        if date_str:
                            events.append(
                                _build_event(
                                    ticker, "earnings", date_str,
                                    description="Earnings",
                                    is_estimated=1,
                                )
                            )

        # Fallback: earningsTimestamp in info
        if not events:
            earnings_ts = info.get("earningsTimestamp")
            if isinstance(earnings_ts, (int, float)) and earnings_ts > 0:
                date_str = datetime.fromtimestamp(
                    earnings_ts, tz=timezone.utc
                ).strftime("%Y-%m-%d")
                events.append(
                    _build_event(
                        ticker, "earnings", date_str,
                        description="Earnings",
                        is_estimated=0,
                    )
                )

        return events

    @staticmethod
    def _parse_dividend(ticker: str, info: dict) -> list[dict]:
        """Extract ex-dividend event from yfinance info dict."""
        events: list[dict] = []

        ex_div_ts = info.get("exDividendDate")
        if isinstance(ex_div_ts, (int, float)) and ex_div_ts > 0:
            date_str = datetime.fromtimestamp(
                ex_div_ts, tz=timezone.utc
            ).strftime("%Y-%m-%d")
            div_rate = info.get("dividendRate")
            description = "Ex-Dividend"
            if div_rate is not None:
                description = f"Ex-Dividend (${div_rate:.4g}/share)"
            events.append(
                _build_event(
                    ticker, "ex_dividend", date_str,
                    description=description,
                    amount=div_rate,
                    is_estimated=0,
                )
            )

        return events


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _build_event(
    ticker: str,
    event_type: str,
    event_date: str,
    *,
    event_time: str | None = None,
    description: str | None = None,
    amount=None,
    is_estimated: int = 1,
    source: str = "yahoo",
) -> dict:
    """Build a normalised event dict ready for upsert."""
    return {
        "ticker": ticker.upper(),
        "event_type": event_type,
        "event_date": event_date,
        "event_time": event_time,
        "description": description,
        "amount": amount,
        "is_estimated": is_estimated,
        "source": source,
    }


def _timestamp_to_iso(val) -> str | None:
    """Convert a pandas Timestamp, datetime, or string to ISO date string.

    Returns None if conversion fails.
    """
    try:
        # pandas Timestamp
        if hasattr(val, "strftime"):
            return val.strftime("%Y-%m-%d")
        # Might be a string already
        if isinstance(val, str):
            # Quick sanity check for ISO-ish date
            datetime.fromisoformat(val[:10])
            return val[:10]
    except (ValueError, TypeError, AttributeError):
        pass
    return None
