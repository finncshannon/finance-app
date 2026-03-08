"""Repository for portfolio_accounts table."""

from datetime import datetime, timezone

from db.connection import DatabaseConnection


class PortfolioAccountRepo:

    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def get_account(self, account_id: int) -> dict | None:
        return await self.db.fetchone(
            "SELECT * FROM portfolio_accounts WHERE id = ?", (account_id,)
        )

    async def get_all_accounts(self) -> list[dict]:
        return await self.db.fetchall(
            "SELECT * FROM portfolio_accounts ORDER BY name"
        )

    async def create_account(self, data: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.db.execute(
            """INSERT INTO portfolio_accounts (name, account_type, is_default, created_at)
               VALUES (?, ?, ?, ?)""",
            (
                data["name"],
                data.get("account_type", "taxable"),
                1 if data.get("is_default") else 0,
                now,
            ),
        )
        await self.db.commit()
        return await self.get_account(cursor.lastrowid)

    async def update_account(self, account_id: int, data: dict) -> dict | None:
        fields = []
        values = []
        for key, val in data.items():
            if key not in ("id", "created_at"):
                if key == "is_default":
                    val = 1 if val else 0
                fields.append(f"{key} = ?")
                values.append(val)
        if not fields:
            return await self.get_account(account_id)
        values.append(account_id)
        await self.db.execute(
            f"UPDATE portfolio_accounts SET {', '.join(fields)} WHERE id = ?",
            tuple(values),
        )
        await self.db.commit()
        return await self.get_account(account_id)

    async def delete_account(self, account_id: int) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM portfolio_accounts WHERE id = ?", (account_id,)
        )
        await self.db.commit()
        return cursor.rowcount > 0
