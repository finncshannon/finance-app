"""Repository for market data tables (market_cache.db).

See phase0b_database_schema.md:
  - financial_data (Table #2, cache.financial_data)
  - market_data (Table #3, cache.market_data)
  - company_events (Table #22, cache.company_events)
"""

from datetime import datetime, timezone

from db.connection import DatabaseConnection


class MarketDataRepo:

    def __init__(self, db: DatabaseConnection):
        self.db = db

    # --- financial_data (cache.financial_data) ---

    async def get_financials(self, ticker: str, years: int = 10) -> list[dict]:
        return await self.db.fetchall(
            """SELECT * FROM cache.financial_data
               WHERE ticker = ?
               ORDER BY fiscal_year DESC
               LIMIT ?""",
            (ticker.upper(), years + 1),  # +1 for potential TTM row
        )

    async def upsert_financial(self, data: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        cols = [k for k in data if k != "id"]
        if "fetched_at" not in cols:
            cols.append("fetched_at")
            data["fetched_at"] = now

        placeholders = ", ".join(["?"] * len(cols))
        updates = ", ".join(f"{c} = ?" for c in cols if c not in ("ticker", "fiscal_year", "period_type"))
        update_vals = [data[c] for c in cols if c not in ("ticker", "fiscal_year", "period_type")]

        await self.db.execute(
            f"""INSERT INTO cache.financial_data ({', '.join(cols)})
                VALUES ({placeholders})
                ON CONFLICT(ticker, fiscal_year, period_type)
                DO UPDATE SET {updates}""",
            tuple([data[c] for c in cols] + update_vals),
        )
        await self.db.commit()

    async def delete_financials(self, ticker: str) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM cache.financial_data WHERE ticker = ?", (ticker.upper(),)
        )
        await self.db.commit()
        return cursor.rowcount > 0

    # --- market_data (cache.market_data) ---

    async def get_market_data(self, ticker: str) -> dict | None:
        return await self.db.fetchone(
            "SELECT * FROM cache.market_data WHERE ticker = ?", (ticker.upper(),)
        )

    async def get_market_data_bulk(self, tickers: list[str]) -> list[dict]:
        if not tickers:
            return []
        placeholders = ", ".join(["?"] * len(tickers))
        return await self.db.fetchall(
            f"SELECT * FROM cache.market_data WHERE ticker IN ({placeholders})",
            tuple(t.upper() for t in tickers),
        )

    async def upsert_market_data(self, data: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            """INSERT INTO cache.market_data
               (ticker, current_price, previous_close, day_open, day_high, day_low,
                day_change, day_change_pct, fifty_two_week_high, fifty_two_week_low,
                volume, average_volume, market_cap, enterprise_value,
                pe_trailing, pe_forward, price_to_book, price_to_sales,
                ev_to_revenue, ev_to_ebitda, dividend_yield, dividend_rate,
                beta, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(ticker)
               DO UPDATE SET
                current_price=?, previous_close=?, day_open=?, day_high=?, day_low=?,
                day_change=?, day_change_pct=?, fifty_two_week_high=?, fifty_two_week_low=?,
                volume=?, average_volume=?, market_cap=?, enterprise_value=?,
                pe_trailing=?, pe_forward=?, price_to_book=?, price_to_sales=?,
                ev_to_revenue=?, ev_to_ebitda=?, dividend_yield=?, dividend_rate=?,
                beta=?, updated_at=?""",
            (
                data["ticker"].upper(),
                data.get("current_price"), data.get("previous_close"),
                data.get("day_open"), data.get("day_high"), data.get("day_low"),
                data.get("day_change"), data.get("day_change_pct"),
                data.get("fifty_two_week_high"), data.get("fifty_two_week_low"),
                data.get("volume"), data.get("average_volume"),
                data.get("market_cap"), data.get("enterprise_value"),
                data.get("pe_trailing"), data.get("pe_forward"),
                data.get("price_to_book"), data.get("price_to_sales"),
                data.get("ev_to_revenue"), data.get("ev_to_ebitda"),
                data.get("dividend_yield"), data.get("dividend_rate"),
                data.get("beta"), now,
                # ON CONFLICT UPDATE values:
                data.get("current_price"), data.get("previous_close"),
                data.get("day_open"), data.get("day_high"), data.get("day_low"),
                data.get("day_change"), data.get("day_change_pct"),
                data.get("fifty_two_week_high"), data.get("fifty_two_week_low"),
                data.get("volume"), data.get("average_volume"),
                data.get("market_cap"), data.get("enterprise_value"),
                data.get("pe_trailing"), data.get("pe_forward"),
                data.get("price_to_book"), data.get("price_to_sales"),
                data.get("ev_to_revenue"), data.get("ev_to_ebitda"),
                data.get("dividend_yield"), data.get("dividend_rate"),
                data.get("beta"), now,
            ),
        )
        await self.db.commit()

    # --- company_events (cache.company_events) ---

    async def get_events(self, ticker: str) -> list[dict]:
        return await self.db.fetchall(
            "SELECT * FROM cache.company_events WHERE ticker = ? ORDER BY event_date",
            (ticker.upper(),),
        )

    async def get_upcoming_events(self, limit: int = 20) -> list[dict]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return await self.db.fetchall(
            """SELECT * FROM cache.company_events
               WHERE event_date >= ?
               ORDER BY event_date
               LIMIT ?""",
            (today, limit),
        )

    async def upsert_event(self, data: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            """INSERT INTO cache.company_events
               (ticker, event_type, event_date, event_time, description,
                amount, is_estimated, source, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(ticker, event_type, event_date)
               DO UPDATE SET event_time=?, description=?, amount=?,
                is_estimated=?, source=?, fetched_at=?""",
            (
                data["ticker"].upper(), data["event_type"], data["event_date"],
                data.get("event_time"), data.get("description"),
                data.get("amount"), data.get("is_estimated", 0),
                data.get("source", "yahoo"), now,
                # ON CONFLICT UPDATE:
                data.get("event_time"), data.get("description"),
                data.get("amount"), data.get("is_estimated", 0),
                data.get("source", "yahoo"), now,
            ),
        )
        await self.db.commit()

    async def get_upcoming_events_for_tickers(
        self,
        tickers: list[str],
        event_types: list[str] | None,
        date_from: str,
        date_to: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        """Query events for specific tickers with filters.

        Returns (events_list, total_count).
        """
        if not tickers:
            return [], 0

        placeholders = ", ".join(["?"] * len(tickers))
        params: list = [t.upper() for t in tickers]

        where_clauses = [f"ticker IN ({placeholders})"]

        where_clauses.append("event_date >= ?")
        params.append(date_from)

        if date_to:
            where_clauses.append("event_date <= ?")
            params.append(date_to)

        if event_types:
            type_ph = ", ".join(["?"] * len(event_types))
            where_clauses.append(f"event_type IN ({type_ph})")
            params.extend(event_types)

        where_sql = " AND ".join(where_clauses)

        # Count total
        count_row = await self.db.fetchone(
            f"SELECT COUNT(*) as cnt FROM cache.company_events WHERE {where_sql}",
            tuple(params),
        )
        total = count_row["cnt"] if count_row else 0

        # Fetch page (join companies for company_name)
        fetch_params = list(params) + [limit, offset]
        rows = await self.db.fetchall(
            f"""SELECT e.*, c.company_name
                FROM cache.company_events e
                LEFT JOIN companies c ON e.ticker = c.ticker
                WHERE {where_sql.replace('ticker', 'e.ticker').replace('event_date', 'e.event_date').replace('event_type', 'e.event_type')}
                ORDER BY e.event_date ASC
                LIMIT ? OFFSET ?""",
            tuple(fetch_params),
        )
        return rows, total

    async def delete_events(self, ticker: str) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM cache.company_events WHERE ticker = ?", (ticker.upper(),)
        )
        await self.db.commit()
        return cursor.rowcount > 0
