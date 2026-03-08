import os
import sys
import logging

logger = logging.getLogger("finance_app")


class SystemInfoService:
    def __init__(self, db_paths):
        self.db_paths = db_paths  # {"user_data": "path", "market_cache": "path"}

    async def get_system_info(self):
        import fastapi
        return {
            "app_version": "1.0.0",
            "python_version": sys.version.split()[0],
            "fastapi_version": fastapi.__version__,
        }

    async def get_database_stats(self):
        stats = {}
        for name, path in self.db_paths.items():
            file_size = os.path.getsize(path) if os.path.exists(path) else 0
            table_counts = {}
            try:
                import aiosqlite
                async with aiosqlite.connect(path) as conn:
                    cursor = await conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    )
                    tables = await cursor.fetchall()
                    for (table_name,) in tables:
                        count_cursor = await conn.execute(f"SELECT COUNT(*) FROM [{table_name}]")
                        (count,) = await count_cursor.fetchone()
                        table_counts[table_name] = count
            except Exception as e:
                logger.warning(f"Error reading DB stats for {name}: {e}")
            stats[name] = {"file_size_bytes": file_size, "tables": table_counts}
        return stats

    async def get_cache_size(self):
        path = self.db_paths.get("market_cache", "")
        size = os.path.getsize(path) if os.path.exists(path) else 0
        return {"cache_size_bytes": size, "path": path}

    async def clear_cache(self):
        path = self.db_paths.get("market_cache", "")
        if not os.path.exists(path):
            return {"cleared": False, "reason": "Cache file not found"}
        try:
            import aiosqlite
            async with aiosqlite.connect(path) as conn:
                cursor = await conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
                tables = await cursor.fetchall()
                for (table_name,) in tables:
                    await conn.execute(f"DELETE FROM [{table_name}]")
                await conn.execute("VACUUM")
                await conn.commit()
            return {"cleared": True}
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return {"cleared": False, "reason": str(e)}
