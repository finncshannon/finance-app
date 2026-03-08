"""Repository for price_alerts table."""

from datetime import datetime, timezone

from db.connection import DatabaseConnection


class PriceAlertRepo:

    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def get_alert(self, alert_id: int) -> dict | None:
        return await self.db.fetchone(
            "SELECT * FROM price_alerts WHERE id = ?", (alert_id,)
        )

    async def get_all_alerts(self, active_only: bool = False) -> list[dict]:
        if active_only:
            return await self.db.fetchall(
                "SELECT * FROM price_alerts WHERE is_active = 1 ORDER BY ticker"
            )
        return await self.db.fetchall(
            "SELECT * FROM price_alerts ORDER BY ticker"
        )

    async def create_alert(self, data: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.db.execute(
            """INSERT INTO price_alerts (ticker, alert_type, threshold, is_active, created_at)
               VALUES (?, ?, ?, 1, ?)""",
            (
                data["ticker"].upper(),
                data["alert_type"],
                data["threshold"],
                now,
            ),
        )
        await self.db.commit()
        return await self.get_alert(cursor.lastrowid)

    async def trigger_alert(self, alert_id: int) -> dict | None:
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            "UPDATE price_alerts SET is_active = 0, triggered_at = ? WHERE id = ?",
            (now, alert_id),
        )
        await self.db.commit()
        return await self.get_alert(alert_id)

    async def delete_alert(self, alert_id: int) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM price_alerts WHERE id = ?", (alert_id,)
        )
        await self.db.commit()
        return cursor.rowcount > 0
