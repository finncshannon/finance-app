"""Async SQLite connection manager for both database files.

Architecture:
- user_data.db is the primary connection (17 tables)
- market_cache.db is ATTACHed as 'cache' (6 tables)
- WAL mode and foreign keys enabled on every connection
- Singleton pattern: one connection shared across the app lifecycle

Usage from phase0b_database_schema.md:
    SELECT * FROM cache.financial_data WHERE ticker = ?
    SELECT * FROM companies WHERE ticker = ?
"""

import os
from pathlib import Path

import aiosqlite


def _default_data_dir() -> Path:
    """Return OS-appropriate app data directory for database files."""
    app_data = os.environ.get("FINANCE_APP_DATA_DIR")
    if app_data:
        return Path(app_data)

    # Windows: %LOCALAPPDATA%/FinanceApp
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "FinanceApp"

    # Fallback: user home
    return Path.home() / ".finance-app"


class DatabaseConnection:
    """Async SQLite connection manager.

    Manages a single persistent connection to user_data.db with
    market_cache.db ATTACHed as 'cache'.
    """

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or _default_data_dir()
        self.user_db_path = self.data_dir / "user_data.db"
        self.cache_db_path = self.data_dir / "market_cache.db"
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Open connections and configure SQLite pragmas."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._conn = await aiosqlite.connect(str(self.user_db_path))
        self._conn.row_factory = aiosqlite.Row

        # Enable WAL mode for concurrent read/write
        await self._conn.execute("PRAGMA journal_mode=WAL;")
        # Enable foreign key enforcement
        await self._conn.execute("PRAGMA foreign_keys=ON;")

        # Attach market cache database
        await self._conn.execute(
            f"ATTACH DATABASE '{str(self.cache_db_path)}' AS cache;"
        )
        # WAL mode for cache db too
        await self._conn.execute("PRAGMA cache.journal_mode=WAL;")

        await self._conn.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        """Get the active connection. Raises if not connected."""
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._conn

    async def execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        """Execute a single SQL statement with parameters."""
        return await self.conn.execute(sql, params)

    async def executemany(self, sql: str, params_seq: list[tuple]) -> aiosqlite.Cursor:
        """Execute a SQL statement for each set of parameters."""
        return await self.conn.executemany(sql, params_seq)

    async def fetchone(self, sql: str, params: tuple = ()) -> dict | None:
        """Execute and fetch one row as a dict."""
        cursor = await self.conn.execute(sql, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        """Execute and fetch all rows as list of dicts."""
        cursor = await self.conn.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.conn.commit()


# Module-level singleton
db = DatabaseConnection()
