"""Repository for watchlist tables (user_data.db).

See phase0b_database_schema.md — Tables #13, #18:
  watchlists, watchlist_items
"""

from datetime import datetime, timezone

from db.connection import DatabaseConnection


class WatchlistRepo:

    def __init__(self, db: DatabaseConnection):
        self.db = db

    # --- watchlists ---

    async def get_watchlist(self, watchlist_id: int) -> dict | None:
        return await self.db.fetchone("SELECT * FROM watchlists WHERE id = ?", (watchlist_id,))

    async def get_all_watchlists(self) -> list[dict]:
        return await self.db.fetchall("SELECT * FROM watchlists ORDER BY sort_order, name")

    async def create_watchlist(self, name: str) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.db.execute(
            "INSERT INTO watchlists (name, created_at) VALUES (?, ?)", (name, now)
        )
        await self.db.commit()
        return await self.get_watchlist(cursor.lastrowid)

    async def update_watchlist(self, watchlist_id: int, data: dict) -> dict | None:
        now = datetime.now(timezone.utc).isoformat()
        fields = ["updated_at = ?"]
        values = [now]
        for key, val in data.items():
            if key not in ("id", "created_at"):
                fields.append(f"{key} = ?")
                values.append(val)
        values.append(watchlist_id)
        await self.db.execute(
            f"UPDATE watchlists SET {', '.join(fields)} WHERE id = ?",
            tuple(values),
        )
        await self.db.commit()
        return await self.get_watchlist(watchlist_id)

    async def delete_watchlist(self, watchlist_id: int) -> bool:
        cursor = await self.db.execute("DELETE FROM watchlists WHERE id = ?", (watchlist_id,))
        await self.db.commit()
        return cursor.rowcount > 0

    # --- watchlist_items ---

    async def get_items(self, watchlist_id: int) -> list[dict]:
        return await self.db.fetchall(
            "SELECT * FROM watchlist_items WHERE watchlist_id = ? ORDER BY sort_order",
            (watchlist_id,),
        )

    async def add_item(self, watchlist_id: int, ticker: str) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.db.execute(
            """INSERT INTO watchlist_items (watchlist_id, ticker, added_at)
               VALUES (?, ?, ?)""",
            (watchlist_id, ticker.upper(), now),
        )
        await self.db.commit()
        return await self.db.fetchone(
            "SELECT * FROM watchlist_items WHERE id = ?", (cursor.lastrowid,)
        )

    async def remove_item(self, watchlist_id: int, ticker: str) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM watchlist_items WHERE watchlist_id = ? AND ticker = ?",
            (watchlist_id, ticker.upper()),
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def get_watchlist_with_items(self, watchlist_id: int) -> dict | None:
        watchlist = await self.get_watchlist(watchlist_id)
        if not watchlist:
            return None
        items = await self.get_items(watchlist_id)
        watchlist["items"] = items
        return watchlist
