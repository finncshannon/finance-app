"""Market data service — business logic coordinating providers and repositories.

All module code calls this service — never providers directly.
Implements cache-first pattern with configurable staleness per refresh tier.
"""

import logging
from datetime import datetime, timezone, timedelta

from db.connection import DatabaseConnection
from providers.base import (
    CompanyInfo,
    FinancialStatements,
    KeyStatistics,
    PriceBar,
    QuoteData,
    SearchResult,
)
from providers.registry import provider_registry
from providers.exceptions import ProviderError
from repositories.company_repo import CompanyRepo
from repositories.market_data_repo import MarketDataRepo

logger = logging.getLogger("finance_app")

# Staleness thresholds
TIER1_STALE_SECONDS = 60       # Portfolio/watchlist tickers during market hours
TIER2_STALE_SECONDS = 604800   # S&P 500 — weekly (7 * 86400)
TIER3_STALE_SECONDS = 2592000  # R3000 universe — monthly (30 * 86400)
FINANCIAL_STALE_SECONDS = 86400  # Financials — 24 hours
COMPANY_STALE_SECONDS = 86400   # Company info — 24 hours

# US Eastern market hours
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 30
MARKET_CLOSE_HOUR = 16
MARKET_CLOSE_MINUTE = 0


class MarketDataService:
    """Coordinates between data providers and cache repositories.

    Cache-first pattern: always check local DB before hitting the provider.
    """

    def __init__(self, db: DatabaseConnection, provider_name: str = "yahoo"):
        self.company_repo = CompanyRepo(db)
        self.market_repo = MarketDataRepo(db)
        self._provider_name = provider_name

    @property
    def provider(self):
        return provider_registry.get(self._provider_name)

    # ------------------------------------------------------------------
    # Market hours detection
    # ------------------------------------------------------------------

    @staticmethod
    def is_market_open() -> bool:
        """Check if US stock market is currently open (9:30 AM - 4:00 PM ET, weekdays)."""
        try:
            from zoneinfo import ZoneInfo
            et = ZoneInfo("America/New_York")
        except ImportError:
            # Fallback: estimate ET as UTC-5 (ignores DST)
            et = timezone(timedelta(hours=-5))

        now_et = datetime.now(et)

        # Weekday check (Mon=0, Fri=4)
        if now_et.weekday() > 4:
            return False

        market_open = now_et.replace(
            hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0
        )
        market_close = now_et.replace(
            hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0
        )

        return market_open <= now_et <= market_close

    # ------------------------------------------------------------------
    # Staleness helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_stale(updated_at: str | None, max_age_seconds: int) -> bool:
        """Check if a cached record is stale based on its updated_at timestamp."""
        if updated_at is None:
            return True
        try:
            ts = datetime.fromisoformat(updated_at)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - ts).total_seconds()
            return age > max_age_seconds
        except (ValueError, TypeError):
            return True

    # ------------------------------------------------------------------
    # Company info (cache → provider → persist)
    # ------------------------------------------------------------------

    async def get_company(self, ticker: str) -> dict | None:
        """Get company info — serve from cache if fresh, else fetch and cache."""
        ticker = ticker.upper()

        # Check cache first
        cached = await self.company_repo.get_by_ticker(ticker)
        if cached and not self._is_stale(cached.get("last_refreshed"), COMPANY_STALE_SECONDS):
            return cached

        # Fetch from provider
        try:
            info: CompanyInfo = await self.provider.get_company_info(ticker)
            data = {
                "ticker": info.ticker,
                "company_name": info.company_name,
                "sector": info.sector,
                "industry": info.industry,
                "cik": info.cik,
                "exchange": info.exchange,
                "currency": info.currency,
                "description": info.description,
                "employees": info.employees,
                "country": info.country,
                "website": info.website,
                "fiscal_year_end": info.fiscal_year_end,
            }
            result = await self.company_repo.upsert(data)
            logger.info("Fetched and cached company info for %s", ticker)
            return result
        except ProviderError as e:
            logger.warning("Provider error fetching company %s: %s", ticker, e)
            # Return stale cache if available
            return cached

    # ------------------------------------------------------------------
    # Live quote (always fresh from provider for real-time)
    # ------------------------------------------------------------------

    async def get_live_quote(self, ticker: str) -> QuoteData | None:
        """Fetch a fresh quote from the provider (for WebSocket push / real-time)."""
        ticker = ticker.upper()
        try:
            quote = await self.provider.get_quote(ticker)
            stats = await self.provider.get_key_statistics(ticker)

            # Normalize day_change_pct — safeguard against percentage format
            dcp = quote.day_change_pct
            if dcp is not None and abs(dcp) > 1.0:
                logger.warning("day_change_pct appears to be percentage format (%.4f), normalizing to decimal", dcp)
                dcp = dcp / 100

            # dividend_yield is normalized to decimal at the provider level
            div_yield = stats.dividend_yield
            # Sanity check: cap at 100% — anything above that is data garbage
            if div_yield is not None and div_yield > 1.0:
                logger.warning("dividend_yield > 100%% (%.4f) for %s — setting to None", div_yield, ticker)
                div_yield = None

            # Persist to cache
            cache_data = {
                "ticker": ticker,
                "current_price": quote.current_price,
                "previous_close": quote.previous_close,
                "day_open": quote.day_open,
                "day_high": quote.day_high,
                "day_low": quote.day_low,
                "day_change": quote.day_change,
                "day_change_pct": dcp,
                "fifty_two_week_high": quote.fifty_two_week_high,
                "fifty_two_week_low": quote.fifty_two_week_low,
                "volume": quote.volume,
                "average_volume": quote.average_volume,
                "market_cap": quote.market_cap,
                "enterprise_value": quote.enterprise_value,
                "pe_trailing": stats.pe_trailing,
                "pe_forward": stats.pe_forward,
                "price_to_book": stats.price_to_book,
                "price_to_sales": stats.price_to_sales,
                "ev_to_revenue": stats.ev_to_revenue,
                "ev_to_ebitda": stats.ev_to_ebitda,
                "dividend_yield": div_yield,
                "dividend_rate": stats.dividend_rate,
                "beta": stats.beta,
            }
            await self.market_repo.upsert_market_data(cache_data)
            return quote
        except ProviderError as e:
            logger.warning("Provider error fetching quote for %s: %s", ticker, e)
            return None

    # ------------------------------------------------------------------
    # Cached quote (cache-first with staleness)
    # ------------------------------------------------------------------

    async def get_quote(self, ticker: str, max_age: int | None = None) -> dict | None:
        """Get quote data — cache first, refresh if stale.

        max_age: override staleness threshold in seconds (default: TIER1 during market hours).
        """
        ticker = ticker.upper()

        if max_age is None:
            max_age = TIER1_STALE_SECONDS if self.is_market_open() else TIER3_STALE_SECONDS

        cached = await self.market_repo.get_market_data(ticker)
        if cached and not self._is_stale(cached.get("updated_at"), max_age):
            return cached

        # Refresh
        quote = await self.get_live_quote(ticker)
        if quote:
            return await self.market_repo.get_market_data(ticker)
        return cached  # return stale data if provider failed

    # ------------------------------------------------------------------
    # Historical prices (pass-through, no cache in DB)
    # ------------------------------------------------------------------

    async def get_historical(self, ticker: str, period: str = "1y", interval: str = "1d") -> list[PriceBar]:
        """Get OHLCV bars from provider at the given interval."""
        ticker = ticker.upper()
        try:
            return await self.provider.get_historical_prices(ticker, period, interval)
        except ProviderError as e:
            logger.warning("Provider error fetching historical for %s: %s", ticker, e)
            return []

    # ------------------------------------------------------------------
    # Financial statements (cache-first)
    # ------------------------------------------------------------------

    async def get_financials(self, ticker: str, force_refresh: bool = False) -> list[dict]:
        """Get financial statements — cached with 24h staleness.

        Returns list of dicts (one per fiscal year) from the DB.
        """
        ticker = ticker.upper()

        if not force_refresh:
            cached = await self.market_repo.get_financials(ticker)
            if cached:
                # Check if the most recent row is still fresh
                newest = cached[0] if cached else None
                if newest and not self._is_stale(newest.get("fetched_at"), FINANCIAL_STALE_SECONDS):
                    return cached

        # Fetch from provider
        try:
            statements: FinancialStatements = await self.provider.get_financials(ticker)
            for period in statements.periods:
                data = period.model_dump()
                data["fetched_at"] = datetime.now(timezone.utc).isoformat()
                await self.market_repo.upsert_financial(data)
            logger.info("Fetched and cached %d periods of financials for %s", len(statements.periods), ticker)
        except ProviderError as e:
            logger.warning("Provider error fetching financials for %s: %s", ticker, e)

        return await self.market_repo.get_financials(ticker)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(self, query: str) -> list[SearchResult]:
        """Search for companies — check local DB first, then provider."""
        # Try local DB first
        local = await self.company_repo.search(query)
        if local:
            return [
                SearchResult(
                    ticker=r["ticker"],
                    company_name=r["company_name"],
                    exchange=r.get("exchange"),
                    type="equity",
                )
                for r in local
            ]

        # Fall through to provider search
        try:
            return await self.provider.search_companies(query)
        except ProviderError as e:
            logger.warning("Provider search error: %s", e)
            return []

    # ------------------------------------------------------------------
    # Batch refresh
    # ------------------------------------------------------------------

    async def refresh_batch(self, tickers: list[str]) -> dict[str, bool]:
        """Refresh quote + company info for multiple tickers.

        Returns dict of {ticker: success_bool}.
        """
        results: dict[str, bool] = {}
        for ticker in tickers:
            ticker = ticker.upper()
            try:
                await self.get_live_quote(ticker)
                await self.get_company(ticker)
                results[ticker] = True
                logger.info("Refreshed %s", ticker)
            except Exception as e:
                logger.warning("Failed to refresh %s: %s", ticker, e)
                results[ticker] = False
        return results
