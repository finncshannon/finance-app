"""Company service — coordinates company CRUD, enrichment, and aggregation.

Every module that needs company data goes through this service.
Coordinates between CompanyRepo, MarketDataService, DataExtractionService,
and SECEdgarProvider.
"""

import logging
from datetime import datetime, timezone

from db.connection import DatabaseConnection
from repositories.company_repo import CompanyRepo
from services.market_data_service import MarketDataService
from services.data_extraction_service import DataExtractionService
from providers.sec_edgar import SECEdgarProvider

logger = logging.getLogger("finance_app")


class CompanyService:
    """Shared company data layer — used by all modules."""

    def __init__(
        self,
        db: DatabaseConnection,
        market_data_svc: MarketDataService,
        data_extraction_svc: DataExtractionService,
        sec_provider: SECEdgarProvider,
    ):
        self.company_repo = CompanyRepo(db)
        self.market_svc = market_data_svc
        self.extraction_svc = data_extraction_svc
        self.sec = sec_provider

    # ------------------------------------------------------------------
    # Core: get or create
    # ------------------------------------------------------------------

    async def get_or_create_company(self, ticker: str) -> dict | None:
        """Get company from DB, or fetch + cache from provider if missing."""
        ticker = ticker.upper()

        cached = await self.company_repo.get_by_ticker(ticker)
        if cached:
            return cached

        # Fetch from provider and cache
        company = await self.market_svc.get_company(ticker)
        if company:
            logger.info("Created company record for %s", ticker)
        return company

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search_companies(self, query: str) -> list[dict]:
        """Search local DB first, then fall through to provider."""
        local = await self.company_repo.search(query)
        if local:
            return local

        # Fall through to provider search
        results = await self.market_svc.search(query)
        return [
            {
                "ticker": r.ticker,
                "company_name": r.company_name,
                "exchange": r.exchange,
                "type": r.type,
            }
            for r in results
        ]

    # ------------------------------------------------------------------
    # Enrich (force-refresh)
    # ------------------------------------------------------------------

    async def enrich_company(self, ticker: str) -> dict | None:
        """Force-refresh company info from provider and SEC CIK."""
        ticker = ticker.upper()

        # Force-refresh from Yahoo
        company = await self.market_svc.get_company(ticker)

        # Also fetch CIK from SEC and update
        try:
            cik = await self.sec.get_cik(ticker)
            if cik and company:
                await self.company_repo.update(ticker, {"cik": cik})
                company = await self.company_repo.get_by_ticker(ticker)
        except Exception as exc:
            logger.warning("Failed to fetch CIK for %s: %s", ticker, exc)

        return company

    # ------------------------------------------------------------------
    # Peer discovery
    # ------------------------------------------------------------------

    async def find_peers(self, ticker: str, limit: int = 15) -> list[str]:
        """Auto-discover peer companies for Comps analysis.

        Returns list of peer ticker strings, sorted by relevance.
        Returns empty list if no peers found.
        """
        ticker = ticker.upper()
        company = await self.company_repo.get_by_ticker(ticker)
        if not company:
            logger.warning("Cannot find peers: company %s not found", ticker)
            return []

        sector = company.get("sector", "Unknown")
        industry = company.get("industry", "Unknown")
        if sector == "Unknown" and industry == "Unknown":
            logger.warning("Cannot find peers for %s: no sector/industry data", ticker)
            return []

        # Get market cap for proximity sorting
        from repositories.market_data_repo import MarketDataRepo
        market_repo = MarketDataRepo(self.company_repo.db)
        md = await market_repo.get_market_data(ticker)
        market_cap = md.get("market_cap") if md else None

        peers = await self.company_repo.find_peers(
            ticker, sector, industry, market_cap, limit,
        )
        return [p["ticker"] for p in peers]

    # ------------------------------------------------------------------
    # Aggregated company + metrics
    # ------------------------------------------------------------------

    async def get_company_with_metrics(self, ticker: str) -> dict:
        """Get company profile + quote + key metrics in one call.

        Returns a merged dict suitable for the ticker header bar.
        """
        ticker = ticker.upper()

        company = await self.get_or_create_company(ticker)
        quote = await self.market_svc.get_quote(ticker)
        metrics = await self.extraction_svc.compute_all_metrics(ticker)

        # Supplement metrics with enterprise_value and shares_outstanding
        if metrics is None:
            metrics = {}
        if quote:
            if "enterprise_value" not in metrics or metrics["enterprise_value"] is None:
                metrics["enterprise_value"] = quote.get("enterprise_value")
        financials = await self.market_svc.market_repo.get_financials(ticker)
        if financials:
            latest = financials[0]
            if "shares_outstanding" not in metrics or metrics["shares_outstanding"] is None:
                metrics["shares_outstanding"] = latest.get("shares_outstanding")

        result = {}
        if company:
            result.update(company)
        if quote:
            result["quote"] = quote
        if metrics:
            result["metrics"] = metrics

        return result
