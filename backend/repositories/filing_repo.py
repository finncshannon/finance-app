"""Repository for filing_cache and filing_sections tables (market_cache.db).

See phase0b_database_schema.md — Table #16 (filing_cache), Table #21 (filing_sections).
"""

import json
from datetime import datetime, timezone

from db.connection import DatabaseConnection


class FilingRepo:

    def __init__(self, db: DatabaseConnection):
        self.db = db

    # --- filing_cache ---

    async def get_filing(
        self, ticker: str, form_type: str, filing_date: str | None = None
    ) -> dict | None:
        if filing_date:
            return await self.db.fetchone(
                """SELECT * FROM cache.filing_cache
                   WHERE ticker = ? AND form_type = ? AND filing_date = ?""",
                (ticker.upper(), form_type, filing_date),
            )
        return await self.db.fetchone(
            """SELECT * FROM cache.filing_cache
               WHERE ticker = ? AND form_type = ?
               ORDER BY filing_date DESC LIMIT 1""",
            (ticker.upper(), form_type),
        )

    async def get_filing_by_id(self, filing_id: int) -> dict | None:
        return await self.db.fetchone(
            "SELECT * FROM cache.filing_cache WHERE id = ?", (filing_id,)
        )

    async def get_filings_by_ticker(
        self, ticker: str, form_types: list[str] | None = None, limit: int = 20
    ) -> list[dict]:
        ticker = ticker.upper()
        if form_types:
            placeholders = ", ".join(["?"] * len(form_types))
            return await self.db.fetchall(
                f"""SELECT * FROM cache.filing_cache
                    WHERE ticker = ? AND form_type IN ({placeholders})
                    ORDER BY filing_date DESC LIMIT ?""",
                (ticker, *form_types, limit),
            )
        return await self.db.fetchall(
            """SELECT * FROM cache.filing_cache
               WHERE ticker = ?
               ORDER BY filing_date DESC LIMIT ?""",
            (ticker, limit),
        )

    async def upsert_filing(self, data: dict) -> int:
        """Insert or update a filing record. Returns the filing_id."""
        now = datetime.now(timezone.utc).isoformat()
        sections = data.get("sections_json")
        if isinstance(sections, list):
            sections = json.dumps(sections)

        await self.db.execute(
            """INSERT INTO cache.filing_cache
               (ticker, form_type, filing_date, cik, accession_number,
                sections_json, file_path, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(ticker, form_type, filing_date)
               DO UPDATE SET
                cik = ?, accession_number = ?,
                sections_json = ?, file_path = ?, fetched_at = ?""",
            (
                data["ticker"].upper(),
                data["form_type"],
                data.get("filing_date"),
                data.get("cik"),
                data.get("accession_number"),
                sections,
                data.get("file_path"),
                now,
                # ON CONFLICT UPDATE:
                data.get("cik"),
                data.get("accession_number"),
                sections,
                data.get("file_path"),
                now,
            ),
        )
        await self.db.commit()

        # Get the id (lastrowid works for INSERT, but for ON CONFLICT UPDATE we need a query)
        row = await self.db.fetchone(
            """SELECT id FROM cache.filing_cache
               WHERE ticker = ? AND form_type = ? AND filing_date = ?""",
            (data["ticker"].upper(), data["form_type"], data.get("filing_date")),
        )
        return row["id"] if row else 0

    async def delete_filings(self, ticker: str) -> int:
        cursor = await self.db.execute(
            "DELETE FROM cache.filing_cache WHERE ticker = ?", (ticker.upper(),)
        )
        await self.db.commit()
        return cursor.rowcount

    # --- filing_sections ---

    async def get_filing_sections(self, filing_id: int) -> list[dict]:
        return await self.db.fetchall(
            """SELECT * FROM cache.filing_sections
               WHERE filing_id = ? ORDER BY id""",
            (filing_id,),
        )

    async def get_section(self, filing_id: int, section_key: str) -> dict | None:
        return await self.db.fetchone(
            """SELECT * FROM cache.filing_sections
               WHERE filing_id = ? AND section_key = ?""",
            (filing_id, section_key),
        )

    async def upsert_sections(self, filing_id: int, sections: dict[str, dict]) -> int:
        """Insert or replace sections for a filing.

        sections: dict of {section_key: {"title": str, "content": str}}
        Returns number of sections stored.
        """
        # Delete existing sections for this filing (replace strategy)
        await self.db.execute(
            "DELETE FROM cache.filing_sections WHERE filing_id = ?", (filing_id,)
        )

        count = 0
        for key, sec_data in sections.items():
            content = sec_data.get("content", "")
            word_count = len(content.split()) if content else 0
            await self.db.execute(
                """INSERT INTO cache.filing_sections
                   (filing_id, section_key, section_title, content_text, word_count)
                   VALUES (?, ?, ?, ?, ?)""",
                (filing_id, key, sec_data.get("title", key), content, word_count),
            )
            count += 1

        await self.db.commit()
        return count
