"""Repository for news_articles table (market_cache.db).

Persists RSS news articles for historical lookback beyond the live feed window.
"""

from datetime import datetime, timezone

from db.connection import DatabaseConnection


class NewsRepo:

    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def get_articles(
        self,
        days: int = 10,
        category: str | None = None,
        region: str | None = None,
        limit: int = 2000,
    ) -> list[dict]:
        """Fetch articles from the last N days, with optional filters."""
        conditions = ["published_at >= datetime('now', ?)"]
        params: list = [f"-{days} days"]

        if category:
            conditions.append("category = ?")
            params.append(category)
        if region:
            conditions.append("region = ?")
            params.append(region)

        where = " AND ".join(conditions)
        params.append(limit)

        return await self.db.fetchall(
            f"""SELECT url, title, source, published_at, snippet,
                       category, region, coverage_count
                FROM cache.news_articles
                WHERE {where}
                ORDER BY published_at DESC
                LIMIT ?""",
            tuple(params),
        )

    async def upsert_articles(self, articles: list[dict]) -> int:
        """Bulk upsert articles. Returns count of rows affected."""
        if not articles:
            return 0

        now = datetime.now(timezone.utc).isoformat()
        rows = []
        for a in articles:
            rows.append((
                a.get("link", ""),
                a.get("title", ""),
                a.get("source", ""),
                a.get("published"),
                a.get("snippet", ""),
                a.get("category", "General"),
                a.get("region", "Global"),
                a.get("coverage_count", 1),
                now,
            ))

        # Filter out articles without a URL
        rows = [r for r in rows if r[0]]

        await self.db.executemany(
            """INSERT INTO cache.news_articles
                   (url, title, source, published_at, snippet,
                    category, region, coverage_count, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(url) DO UPDATE SET
                   category = excluded.category,
                   region = excluded.region,
                   coverage_count = MAX(news_articles.coverage_count, excluded.coverage_count),
                   fetched_at = excluded.fetched_at""",
            rows,
        )
        await self.db.commit()
        return len(rows)

    async def get_article_count(self, days: int = 10) -> int:
        """Count articles in the last N days."""
        result = await self.db.fetchone(
            """SELECT COUNT(*) as cnt FROM cache.news_articles
               WHERE published_at >= datetime('now', ?)""",
            (f"-{days} days",),
        )
        return result["cnt"] if result else 0

    async def prune_old(self, keep_days: int = 30) -> int:
        """Delete articles older than keep_days. Returns deleted count."""
        cursor = await self.db.execute(
            """DELETE FROM cache.news_articles
               WHERE published_at < datetime('now', ?)""",
            (f"-{keep_days} days",),
        )
        await self.db.commit()
        return cursor.rowcount
