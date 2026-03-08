"""Universe management service for the Scanner module.

Manages the stock universe (R3000 etc.) by syncing ticker/CIK data
from SEC EDGAR into the local companies table. Also provides access
to static universe lists (S&P 500, etc.) from JSON data files.
"""

import json
import logging
from pathlib import Path

from db.connection import DatabaseConnection
from repositories.company_repo import CompanyRepo
from providers.sec_edgar import SECEdgarProvider

logger = logging.getLogger("finance_app")

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

UNIVERSE_FILES = {
    "dow": "dow_tickers.json",
    "sp500": "sp500_tickers.json",
    "r3000": "russell3000_tickers.json",
}


class UniverseService:
    """Load, query, and refresh the investable universe."""

    def __init__(self, db: DatabaseConnection, sec_provider: SECEdgarProvider):
        self.db = db
        self.sec_provider = sec_provider
        self.company_repo = CompanyRepo(db)
        self._sp500_cache: list[dict] | None = None
        self._sp500_tickers_cache: list[str] | None = None

    # ------------------------------------------------------------------
    # Load universe
    # ------------------------------------------------------------------

    async def load_universe(self, name: str = "r3000") -> int:
        """Fetch the full SEC ticker/CIK mapping and insert new companies.

        Only inserts tickers that don't already exist in the DB.
        Returns the count of companies loaded (newly inserted).
        """
        cik_mapping = await self.sec_provider._get_cik_mapping()
        if not cik_mapping:
            logger.warning("CIK mapping returned empty — nothing to load.")
            return 0

        # Batch-check which tickers already exist
        existing_rows = await self.db.fetchall(
            "SELECT ticker FROM companies"
        )
        existing_tickers = {row["ticker"] for row in existing_rows}

        new_count = 0
        for ticker, cik in cik_mapping.items():
            if ticker.upper() in existing_tickers:
                continue
            try:
                await self.company_repo.create({
                    "ticker": ticker,
                    "company_name": ticker,
                    "cik": cik,
                    "universe_source": name,
                })
                new_count += 1
            except Exception as exc:
                logger.debug("Skipping %s: %s", ticker, exc)

        logger.info(
            "Universe '%s' loaded: %d new tickers (total mapping: %d)",
            name, new_count, len(cik_mapping),
        )
        return new_count

    # ------------------------------------------------------------------
    # Load curated universes from static JSON files
    # ------------------------------------------------------------------

    async def load_curated_universe(self, name: str) -> int:
        """Load a curated universe from a static JSON file.

        Upserts each ticker into the companies table with company_name,
        sector, industry, and adds the universe name to universe_tags.
        Returns count of companies loaded.
        """
        filename = UNIVERSE_FILES.get(name)
        if not filename:
            raise ValueError(f"Unknown curated universe: {name}")

        filepath = _DATA_DIR / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Universe file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            entries = json.load(f)

        loaded = 0
        for entry in entries:
            ticker = entry["ticker"].upper()
            existing = await self.company_repo.get_by_ticker(ticker)

            if existing:
                # Update company_name, sector, industry if they were placeholder values
                updates = {}
                if existing.get("company_name") == ticker or existing.get("company_name") == "Unknown":
                    updates["company_name"] = entry.get("company_name", ticker)
                if existing.get("sector") == "Unknown":
                    updates["sector"] = entry.get("sector", "Unknown")
                if existing.get("industry") == "Unknown":
                    updates["industry"] = entry.get("industry", "Unknown")

                # Add universe tag
                current_tags = existing.get("universe_tags") or ""
                if name not in current_tags.split(","):
                    tag_list = [t for t in current_tags.split(",") if t] + [name]
                    updates["universe_tags"] = ",".join(tag_list)

                if updates:
                    await self.company_repo.update(ticker, updates)
            else:
                await self.company_repo.create({
                    "ticker": ticker,
                    "company_name": entry.get("company_name", ticker),
                    "sector": entry.get("sector", "Unknown"),
                    "industry": entry.get("industry", "Unknown"),
                    "universe_source": name,
                    "universe_tags": name,
                })
            loaded += 1

        logger.info("Curated universe '%s' loaded: %d tickers from %s", name, loaded, filename)
        return loaded

    async def load_all_curated(self) -> dict[str, int]:
        """Load all curated universes: DOW -> S&P 500 -> R3000."""
        results = {}
        for name in ["dow", "sp500", "r3000"]:
            try:
                count = await self.load_curated_universe(name)
                results[name] = count
            except Exception as exc:
                logger.error("Failed to load curated universe '%s': %s", name, exc)
                results[name] = 0
        return results

    # ------------------------------------------------------------------
    # Query tickers
    # ------------------------------------------------------------------

    async def get_universe_tickers(self, universe: str = "r3000") -> list[str]:
        """Return a list of ticker strings for the given universe.

        If universe == "all", returns every ticker regardless of source.
        Checks both universe_source and universe_tags columns.
        """
        if universe == "all":
            rows = await self.db.fetchall(
                "SELECT ticker FROM companies ORDER BY ticker"
            )
        else:
            rows = await self.db.fetchall(
                "SELECT ticker FROM companies WHERE universe_source = ? OR universe_tags LIKE ? ORDER BY ticker",
                (universe, f"%{universe}%"),
            )
        return [row["ticker"] for row in rows]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_universe_stats(self) -> dict:
        """Return aggregate universe statistics.

        Returns dict with total, with_financials, with_market_data,
        and last_refreshed.
        """
        total_row = await self.db.fetchone(
            "SELECT COUNT(*) as cnt FROM companies"
        )
        total = total_row["cnt"] if total_row else 0

        fin_row = await self.db.fetchone(
            "SELECT COUNT(DISTINCT ticker) as cnt FROM cache.financial_data"
        )
        with_financials = fin_row["cnt"] if fin_row else 0

        mkt_row = await self.db.fetchone(
            "SELECT COUNT(DISTINCT ticker) as cnt FROM cache.market_data"
        )
        with_market_data = mkt_row["cnt"] if mkt_row else 0

        refresh_row = await self.db.fetchone(
            "SELECT MAX(last_refreshed) as lr FROM companies"
        )
        last_refreshed = refresh_row["lr"] if refresh_row else None

        return {
            "total": total,
            "with_financials": with_financials,
            "with_market_data": with_market_data,
            "last_refreshed": last_refreshed,
        }

    # ------------------------------------------------------------------
    # Refresh universe
    # ------------------------------------------------------------------

    async def refresh_universe(self, universe: str = "r3000") -> dict:
        """Re-fetch the CIK mapping from SEC and add any new tickers.

        Returns dict with added and total counts.
        """
        cik_mapping = await self.sec_provider._get_cik_mapping()
        if not cik_mapping:
            logger.warning("CIK mapping returned empty — nothing to refresh.")
            return {"added": 0, "total": 0}

        existing_rows = await self.db.fetchall(
            "SELECT ticker FROM companies"
        )
        existing_tickers = {row["ticker"] for row in existing_rows}

        added = 0
        for ticker, cik in cik_mapping.items():
            if ticker.upper() in existing_tickers:
                continue
            try:
                await self.company_repo.create({
                    "ticker": ticker,
                    "company_name": ticker,
                    "cik": cik,
                    "universe_source": universe,
                })
                added += 1
            except Exception as exc:
                logger.debug("Skipping %s on refresh: %s", ticker, exc)

        total_row = await self.db.fetchone(
            "SELECT COUNT(*) as cnt FROM companies"
        )
        total = total_row["cnt"] if total_row else 0

        logger.info(
            "Universe '%s' refreshed: %d new tickers, %d total",
            universe, added, total,
        )
        return {"added": added, "total": total}

    # ------------------------------------------------------------------
    # Static universe lists (S&P 500, etc.)
    # ------------------------------------------------------------------

    def get_sp500_tickers(self) -> list[str]:
        """Return list of S&P 500 ticker strings (cached after first read)."""
        if self._sp500_tickers_cache is None:
            data = self._load_sp500_json()
            self._sp500_tickers_cache = [item["ticker"] for item in data]
        return self._sp500_tickers_cache

    def get_sp500_list(self) -> list[dict]:
        """Return full S&P 500 list with metadata (ticker, name, sector, industry)."""
        if self._sp500_cache is None:
            self._sp500_cache = self._load_sp500_json()
        return self._sp500_cache

    @staticmethod
    def _load_sp500_json() -> list[dict]:
        """Load S&P 500 tickers from the static JSON data file."""
        path = _DATA_DIR / "sp500_tickers.json"
        try:
            with open(path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("S&P 500 data file not found at %s", path)
            return []
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse S&P 500 JSON: %s", exc)
            return []
