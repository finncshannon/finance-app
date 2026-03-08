"""Repository for the settings table (user_data.db).

See phase0b_database_schema.md — Table #17.
Key-value store with TEXT primary key.
"""

from datetime import datetime, timezone

from db.connection import DatabaseConnection


class SettingsRepo:

    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def get(self, key: str) -> str | None:
        row = await self.db.fetchone("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else None

    async def get_all(self) -> dict:
        rows = await self.db.fetchall("SELECT key, value FROM settings ORDER BY key")
        return {r["key"]: r["value"] for r in rows}

    async def set(self, key: str, value: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            """INSERT INTO settings (key, value, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?""",
            (key, value, now, value, now),
        )
        await self.db.commit()

    async def set_many(self, settings: dict[str, str]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        for key, value in settings.items():
            await self.db.execute(
                """INSERT INTO settings (key, value, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?""",
                (key, value, now, value, now),
            )
        await self.db.commit()

    async def delete(self, key: str) -> bool:
        cursor = await self.db.execute("DELETE FROM settings WHERE key = ?", (key,))
        await self.db.commit()
        return cursor.rowcount > 0
