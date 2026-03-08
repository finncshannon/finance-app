"""Repository for portfolio_transactions table."""

from datetime import datetime, timezone

from db.connection import DatabaseConnection


class PortfolioTransactionRepo:

    def __init__(self, db: DatabaseConnection):
        self.db = db

    async def get_transaction(self, tx_id: int) -> dict | None:
        return await self.db.fetchone(
            "SELECT * FROM portfolio_transactions WHERE id = ?", (tx_id,)
        )

    async def get_all_transactions(
        self,
        ticker: str | None = None,
        transaction_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        account: str | None = None,
        limit: int = 500,
    ) -> list[dict]:
        wheres = []
        params: list = []

        if ticker:
            wheres.append("ticker = ?")
            params.append(ticker.upper())
        if transaction_type:
            wheres.append("transaction_type = ?")
            params.append(transaction_type.upper())
        if start_date:
            wheres.append("transaction_date >= ?")
            params.append(start_date)
        if end_date:
            wheres.append("transaction_date <= ?")
            params.append(end_date)
        if account:
            wheres.append("account = ?")
            params.append(account)

        where_clause = f"WHERE {' AND '.join(wheres)}" if wheres else ""
        params.append(limit)
        return await self.db.fetchall(
            f"""SELECT * FROM portfolio_transactions
                {where_clause}
                ORDER BY transaction_date DESC, id DESC
                LIMIT ?""",
            tuple(params),
        )

    async def get_transactions_for_ticker(self, ticker: str) -> list[dict]:
        return await self.db.fetchall(
            """SELECT * FROM portfolio_transactions
               WHERE ticker = ?
               ORDER BY transaction_date ASC""",
            (ticker.upper(),),
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
                data["transaction_type"].upper(),
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

    async def get_dividend_income(
        self, ticker: str | None = None, start_date: str | None = None,
    ) -> list[dict]:
        wheres = ["transaction_type IN ('DIVIDEND', 'DRIP')"]
        params: list = []
        if ticker:
            wheres.append("ticker = ?")
            params.append(ticker.upper())
        if start_date:
            wheres.append("transaction_date >= ?")
            params.append(start_date)
        return await self.db.fetchall(
            f"""SELECT * FROM portfolio_transactions
                WHERE {' AND '.join(wheres)}
                ORDER BY transaction_date DESC""",
            tuple(params),
        )
