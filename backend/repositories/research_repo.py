"""Repository for research and filing tables.

See phase0b_database_schema.md:
  - filing_cache (Table #16, market_cache.db — accessed via cache. prefix)
  - filing_sections (Table #21, market_cache.db — accessed via cache. prefix)
  - research_notes (Table #15, user_data.db)
"""

from datetime import datetime, timezone

from db.connection import DatabaseConnection


class ResearchRepo:

    def __init__(self, db: DatabaseConnection):
        self.db = db

    # --- research_notes (user_data.db) ---

    async def get_note(self, note_id: int) -> dict | None:
        return await self.db.fetchone("SELECT * FROM research_notes WHERE id = ?", (note_id,))

    async def get_notes_for_ticker(self, ticker: str) -> list[dict]:
        return await self.db.fetchall(
            "SELECT * FROM research_notes WHERE ticker = ? ORDER BY created_at DESC",
            (ticker.upper(),),
        )

    async def create_note(self, data: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.db.execute(
            """INSERT INTO research_notes (ticker, note_text, note_type, created_at)
               VALUES (?, ?, ?, ?)""",
            (data["ticker"].upper(), data["note_text"], data.get("note_type", "general"), now),
        )
        await self.db.commit()
        return await self.get_note(cursor.lastrowid)

    async def update_note(self, note_id: int, data: dict) -> dict | None:
        now = datetime.now(timezone.utc).isoformat()
        fields = ["updated_at = ?"]
        values = [now]
        for key, val in data.items():
            if key not in ("id", "created_at"):
                fields.append(f"{key} = ?")
                values.append(val)
        values.append(note_id)
        await self.db.execute(
            f"UPDATE research_notes SET {', '.join(fields)} WHERE id = ?",
            tuple(values),
        )
        await self.db.commit()
        return await self.get_note(note_id)

    async def delete_note(self, note_id: int) -> bool:
        cursor = await self.db.execute("DELETE FROM research_notes WHERE id = ?", (note_id,))
        await self.db.commit()
        return cursor.rowcount > 0

    # --- filing_cache (cache.filing_cache) ---

    async def get_filing(self, filing_id: int) -> dict | None:
        return await self.db.fetchone(
            "SELECT * FROM cache.filing_cache WHERE id = ?", (filing_id,)
        )

    async def get_filings_for_ticker(self, ticker: str) -> list[dict]:
        return await self.db.fetchall(
            "SELECT * FROM cache.filing_cache WHERE ticker = ? ORDER BY filing_date DESC",
            (ticker.upper(),),
        )

    async def create_filing(self, data: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.db.execute(
            """INSERT INTO cache.filing_cache
               (ticker, form_type, filing_date, cik, accession_number,
                sections_json, file_path, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["ticker"].upper(),
                data["form_type"],
                data.get("filing_date"),
                data.get("cik"),
                data.get("accession_number"),
                data.get("sections_json"),
                data.get("file_path"),
                now,
            ),
        )
        await self.db.commit()
        return await self.get_filing(cursor.lastrowid)

    # --- filing_sections (cache.filing_sections) ---

    async def get_sections_for_filing(self, filing_id: int) -> list[dict]:
        return await self.db.fetchall(
            "SELECT * FROM cache.filing_sections WHERE filing_id = ? ORDER BY id",
            (filing_id,),
        )

    async def create_section(self, data: dict) -> dict:
        cursor = await self.db.execute(
            """INSERT INTO cache.filing_sections
               (filing_id, section_key, section_title, content_text, word_count)
               VALUES (?, ?, ?, ?, ?)""",
            (
                data["filing_id"],
                data["section_key"],
                data["section_title"],
                data["content_text"],
                data.get("word_count"),
            ),
        )
        await self.db.commit()
        return await self.db.fetchone(
            "SELECT * FROM cache.filing_sections WHERE id = ?", (cursor.lastrowid,)
        )
