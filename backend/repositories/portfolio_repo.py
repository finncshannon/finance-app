"""Repository for portfolio tables (user_data.db).

See phase0b_database_schema.md — Tables #11, #12, #19, #20:
  portfolio_positions, portfolio_transactions, portfolio_lots, portfolio_accounts
"""

from datetime import datetime, timezone

from db.connection import DatabaseConnection


class PortfolioRepo:

    def __init__(self, db: DatabaseConnection):
        self.db = db

    # --- portfolio_positions ---

    async def get_position(self, position_id: int) -> dict | None:
        return await self.db.fetchone(
            "SELECT * FROM portfolio_positions WHERE id = ?", (position_id,)
        )

    async def get_all_positions(self, account: str | None = None) -> list[dict]:
        if account:
            return await self.db.fetchall(
                "SELECT * FROM portfolio_positions WHERE account = ? ORDER BY ticker",
                (account,),
            )
        return await self.db.fetchall(
            "SELECT * FROM portfolio_positions ORDER BY ticker"
        )

    async def get_positions_by_ticker(self, ticker: str) -> list[dict]:
        return await self.db.fetchall(
            "SELECT * FROM portfolio_positions WHERE ticker = ?", (ticker.upper(),)
        )

    async def create_position(self, data: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.db.execute(
            """INSERT INTO portfolio_positions
               (ticker, shares_held, cost_basis_per_share, account, added_at, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                data["ticker"].upper(),
                data["shares_held"],
                data.get("cost_basis_per_share"),
                data.get("account", "Manual"),
                now,
                data.get("notes"),
            ),
        )
        await self.db.commit()
        return await self.get_position(cursor.lastrowid)

    async def update_position(self, position_id: int, data: dict) -> dict | None:
        fields = []
        values = []
        for key, val in data.items():
            if key != "id":
                fields.append(f"{key} = ?")
                values.append(val)
        if not fields:
            return await self.get_position(position_id)
        values.append(position_id)
        await self.db.execute(
            f"UPDATE portfolio_positions SET {', '.join(fields)} WHERE id = ?",
            tuple(values),
        )
        await self.db.commit()
        return await self.get_position(position_id)

    async def delete_position(self, position_id: int) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM portfolio_positions WHERE id = ?", (position_id,)
        )
        await self.db.commit()
        return cursor.rowcount > 0

    # --- portfolio_transactions ---

    async def get_transaction(self, transaction_id: int) -> dict | None:
        return await self.db.fetchone(
            "SELECT * FROM portfolio_transactions WHERE id = ?", (transaction_id,)
        )

    async def get_transactions(self, ticker: str | None = None) -> list[dict]:
        if ticker:
            return await self.db.fetchall(
                "SELECT * FROM portfolio_transactions WHERE ticker = ? ORDER BY transaction_date DESC",
                (ticker.upper(),),
            )
        return await self.db.fetchall(
            "SELECT * FROM portfolio_transactions ORDER BY transaction_date DESC"
        )

    async def create_transaction(self, data: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.db.execute(
            """INSERT INTO portfolio_transactions
               (ticker, transaction_type, shares, price_per_share, total_amount,
                transaction_date, account, fees, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["ticker"].upper(),
                data["transaction_type"],
                data.get("shares"),
                data.get("price_per_share"),
                data.get("total_amount"),
                data["transaction_date"],
                data.get("account"),
                data.get("fees", 0),
                data.get("notes"),
                now,
            ),
        )
        await self.db.commit()
        return await self.get_transaction(cursor.lastrowid)

    # --- portfolio_lots ---

    async def get_position_by_ticker(self, ticker: str, account: str = "Manual") -> dict | None:
        return await self.db.fetchone(
            "SELECT * FROM portfolio_positions WHERE ticker = ? AND account = ?",
            (ticker.upper(), account),
        )

    async def get_lot(self, lot_id: int) -> dict | None:
        return await self.db.fetchone(
            "SELECT * FROM portfolio_lots WHERE id = ?", (lot_id,)
        )

    async def get_lots_for_position(self, position_id: int) -> list[dict]:
        return await self.db.fetchall(
            "SELECT * FROM portfolio_lots WHERE position_id = ? ORDER BY date_acquired",
            (position_id,),
        )

    async def get_open_lots(self, position_id: int) -> list[dict]:
        """Get lots with unsold shares."""
        return await self.db.fetchall(
            """SELECT * FROM portfolio_lots
               WHERE position_id = ? AND date_sold IS NULL AND shares > 0
               ORDER BY date_acquired ASC""",
            (position_id,),
        )

    async def create_lot(self, data: dict) -> dict:
        cursor = await self.db.execute(
            """INSERT INTO portfolio_lots
               (position_id, shares, cost_basis_per_share, date_acquired,
                date_sold, sale_price, realized_gain, lot_method, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["position_id"],
                data["shares"],
                data["cost_basis_per_share"],
                data["date_acquired"],
                data.get("date_sold"),
                data.get("sale_price"),
                data.get("realized_gain"),
                data.get("lot_method", "fifo"),
                data.get("notes"),
            ),
        )
        await self.db.commit()
        return await self.db.fetchone(
            "SELECT * FROM portfolio_lots WHERE id = ?", (cursor.lastrowid,)
        )

    async def update_lot(self, lot_id: int, data: dict) -> dict | None:
        fields = []
        values = []
        for key, val in data.items():
            if key != "id":
                fields.append(f"{key} = ?")
                values.append(val)
        if not fields:
            return await self.db.fetchone("SELECT * FROM portfolio_lots WHERE id = ?", (lot_id,))
        values.append(lot_id)
        await self.db.execute(
            f"UPDATE portfolio_lots SET {', '.join(fields)} WHERE id = ?",
            tuple(values),
        )
        await self.db.commit()
        return await self.db.fetchone("SELECT * FROM portfolio_lots WHERE id = ?", (lot_id,))

    # --- portfolio_accounts ---

    async def get_accounts(self) -> list[dict]:
        return await self.db.fetchall("SELECT * FROM portfolio_accounts ORDER BY name")

    async def create_account(self, data: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.db.execute(
            """INSERT INTO portfolio_accounts (name, account_type, is_default, created_at)
               VALUES (?, ?, ?, ?)""",
            (
                data["name"],
                data.get("account_type", "taxable"),
                data.get("is_default", 0),
                now,
            ),
        )
        await self.db.commit()
        return await self.db.fetchone(
            "SELECT * FROM portfolio_accounts WHERE id = ?", (cursor.lastrowid,)
        )

    async def update_account(self, account_id: int, data: dict) -> dict | None:
        fields = []
        values = []
        for key, val in data.items():
            if key != "id":
                fields.append(f"{key} = ?")
                values.append(val)
        if not fields:
            return await self.db.fetchone("SELECT * FROM portfolio_accounts WHERE id = ?", (account_id,))
        values.append(account_id)
        await self.db.execute(
            f"UPDATE portfolio_accounts SET {', '.join(fields)} WHERE id = ?",
            tuple(values),
        )
        await self.db.commit()
        return await self.db.fetchone("SELECT * FROM portfolio_accounts WHERE id = ?", (account_id,))

    async def delete_account(self, account_id: int) -> bool:
        cursor = await self.db.execute(
            "DELETE FROM portfolio_accounts WHERE id = ?", (account_id,)
        )
        await self.db.commit()
        return cursor.rowcount > 0
