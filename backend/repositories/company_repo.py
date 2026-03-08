"""Repository for the companies table (user_data.db).

See phase0b_database_schema.md — Table #1.
Primary key: ticker (TEXT).
"""

from datetime import datetime, timezone

from db.connection import DatabaseConnection


class CompanyRepo:

    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def get_by_ticker(self, ticker: str) -> dict | None:
        return await self.db.fetchone(
            "SELECT * FROM companies WHERE ticker = ?", (ticker.upper(),)
        )

    async def create(self, data: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            """INSERT INTO companies
               (ticker, company_name, sector, industry, cik, exchange, currency,
                description, employees, country, website, universe_source,
                universe_tags, gics_sector_code, gics_industry_code,
                fiscal_year_end, first_seen, last_refreshed)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["ticker"].upper(),
                data["company_name"],
                data.get("sector", "Unknown"),
                data.get("industry", "Unknown"),
                data.get("cik"),
                data.get("exchange"),
                data.get("currency", "USD"),
                data.get("description"),
                data.get("employees"),
                data.get("country"),
                data.get("website"),
                data.get("universe_source", "manual"),
                data.get("universe_tags", ""),
                data.get("gics_sector_code"),
                data.get("gics_industry_code"),
                data.get("fiscal_year_end"),
                now,
                data.get("last_refreshed"),
            ),
        )
        await self.db.commit()
        return await self.get_by_ticker(data["ticker"])

    async def update(self, ticker: str, data: dict) -> dict | None:
        fields = []
        values = []
        for key, val in data.items():
            if key != "ticker":
                fields.append(f"{key} = ?")
                values.append(val)

        if not fields:
            return await self.get_by_ticker(ticker)

        values.append(ticker.upper())
        await self.db.execute(
            f"UPDATE companies SET {', '.join(fields)} WHERE ticker = ?",
            tuple(values),
        )
        await self.db.commit()
        return await self.get_by_ticker(ticker)

    async def upsert(self, data: dict) -> dict | None:
        """Insert or update a company record by ticker."""
        now = datetime.now(timezone.utc).isoformat()
        ticker = data["ticker"].upper()

        existing = await self.get_by_ticker(ticker)
        if existing:
            update_data = {k: v for k, v in data.items() if k != "ticker"}
            update_data["last_refreshed"] = now
            return await self.update(ticker, update_data)
        else:
            data["first_seen"] = now
            data["last_refreshed"] = now
            return await self.create(data)

    async def delete(self, ticker: str) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM companies WHERE ticker = ?", (ticker.upper(),)
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def list_all(self) -> list[dict]:
        return await self.db.fetchall("SELECT * FROM companies ORDER BY ticker")

    async def search(self, query: str) -> list[dict]:
        pattern = f"%{query}%"
        return await self.db.fetchall(
            """SELECT * FROM companies
               WHERE ticker LIKE ? OR company_name LIKE ?
               ORDER BY ticker LIMIT 50""",
            (pattern, pattern),
        )

    async def find_peers(
        self,
        ticker: str,
        sector: str,
        industry: str,
        market_cap: float | None,
        limit: int = 15,
    ) -> list[dict]:
        """Find peer companies by sector/industry with cached financial data.

        Prioritizes same industry, falls back to same sector.
        Sorted by market cap proximity to target.
        """
        target_cap = market_cap or 0
        peers: list[dict] = []

        # Step 1: Same industry
        if industry and industry != "Unknown":
            industry_peers = await self.db.fetchall(
                """SELECT c.ticker, c.company_name, c.sector, c.industry,
                          COALESCE(md.market_cap, 0) as market_cap
                   FROM companies c
                   LEFT JOIN cache.market_data md ON md.ticker = c.ticker
                   WHERE c.industry = ? AND c.ticker != ?
                     AND EXISTS (SELECT 1 FROM cache.financial_data fd WHERE fd.ticker = c.ticker)
                   ORDER BY ABS(COALESCE(md.market_cap, 0) - ?) ASC
                   LIMIT ?""",
                (industry, ticker.upper(), target_cap, limit),
            )
            peers.extend(industry_peers)

        # Step 2: Same sector (if need more)
        if len(peers) < limit and sector and sector != "Unknown":
            found_tickers = {p["ticker"] for p in peers}
            exclude_list = [ticker.upper()] + list(found_tickers)
            exclude_placeholders = ", ".join(["?"] * len(exclude_list))
            remaining = limit - len(peers)

            sector_peers = await self.db.fetchall(
                f"""SELECT c.ticker, c.company_name, c.sector, c.industry,
                           COALESCE(md.market_cap, 0) as market_cap
                    FROM companies c
                    LEFT JOIN cache.market_data md ON md.ticker = c.ticker
                    WHERE c.sector = ? AND c.ticker NOT IN ({exclude_placeholders})
                      AND EXISTS (SELECT 1 FROM cache.financial_data fd WHERE fd.ticker = c.ticker)
                    ORDER BY ABS(COALESCE(md.market_cap, 0) - ?) ASC
                    LIMIT ?""",
                (sector, *exclude_list, target_cap, remaining),
            )
            peers.extend(sector_peers)

        return peers[:limit]
