"""Portfolio service — orchestrates positions, transactions, lots, accounts, alerts."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, date

from db.connection import DatabaseConnection
from repositories.portfolio_repo import PortfolioRepo
from repositories.portfolio_account_repo import PortfolioAccountRepo
from repositories.portfolio_transaction_repo import PortfolioTransactionRepo
from repositories.price_alert_repo import PriceAlertRepo
from services.market_data_service import MarketDataService

from .lot_engine import LotEngine
from .models import (
    Account, AccountCreate,
    Position, PositionCreate, Lot,
    Transaction, TransactionCreate,
    Alert, AlertCreate,
    PortfolioSummary, IncomeResult,
)

logger = logging.getLogger("finance_app")


class PortfolioService:
    """Coordinates position CRUD, transaction recording, lot management."""

    def __init__(
        self,
        db: DatabaseConnection,
        portfolio_repo: PortfolioRepo,
        account_repo: PortfolioAccountRepo,
        transaction_repo: PortfolioTransactionRepo,
        alert_repo: PriceAlertRepo,
        market_data_svc: MarketDataService,
    ):
        self.db = db
        self.repo = portfolio_repo
        self.account_repo = account_repo
        self.tx_repo = transaction_repo
        self.alert_repo = alert_repo
        self.mds = market_data_svc

    # ==================================================================
    # Positions
    # ==================================================================

    async def get_all_positions(self, account: str | None = None) -> list[Position]:
        """Fetch all positions enriched with live prices."""
        rows = await self.repo.get_all_positions(account)
        positions: list[Position] = []
        total_value = 0.0

        # First pass: build positions with prices
        for row in rows:
            pos = await self._enrich_position(row)
            if pos.market_value:
                total_value += pos.market_value
            positions.append(pos)

        # Second pass: compute weights
        if total_value > 0:
            for pos in positions:
                if pos.market_value:
                    pos.weight = round(pos.market_value / total_value, 4)

        return positions

    async def add_position(self, data: PositionCreate) -> Position:
        """Add position + create initial lot + record BUY transaction."""
        now = datetime.now(timezone.utc).isoformat()
        date_str = data.date_acquired or now[:10]

        # Create position
        pos_row = await self.repo.create_position({
            "ticker": data.ticker,
            "shares_held": data.shares,
            "cost_basis_per_share": data.cost_basis_per_share,
            "account": data.account,
            "added_at": now,
            "notes": data.notes,
        })

        # Create initial lot
        await self.repo.create_lot({
            "position_id": pos_row["id"],
            "shares": data.shares,
            "cost_basis_per_share": data.cost_basis_per_share,
            "date_acquired": date_str,
            "lot_method": "fifo",
        })

        # Record BUY transaction
        await self.tx_repo.create_transaction({
            "ticker": data.ticker,
            "transaction_type": "BUY",
            "shares": data.shares,
            "price_per_share": data.cost_basis_per_share,
            "total_amount": data.shares * data.cost_basis_per_share,
            "transaction_date": date_str,
            "account": data.account,
        })

        # Background fetch company profile (don't block the response)
        asyncio.create_task(self._ensure_company_profile(data.ticker))

        return await self._enrich_position(pos_row)

    async def _ensure_company_profile(self, ticker: str) -> None:
        """Fetch company profile if not already cached."""
        try:
            company = await self.mds.get_company(ticker)
            if company and company.get("company_name") == ticker:
                # Name is just the ticker — profile wasn't found, nothing more we can do
                logger.debug("Company profile for %s only has ticker as name", ticker)
        except Exception as exc:
            logger.warning("Failed to fetch profile for %s: %s", ticker, exc)

    async def update_position(self, position_id: int, data: dict) -> Position | None:
        """Update position fields with validation."""
        if "shares" in data or "shares_held" in data:
            shares_val = data.get("shares") or data.get("shares_held")
            if shares_val is not None and shares_val <= 0:
                raise ValueError("Shares must be positive")
        if "cost_basis_per_share" in data and data["cost_basis_per_share"] is not None:
            if data["cost_basis_per_share"] <= 0:
                raise ValueError("Cost basis must be positive")
        row = await self.repo.update_position(position_id, data)
        if row is None:
            return None
        return await self._enrich_position(row)

    async def delete_position(self, position_id: int) -> bool:
        """Delete position (lots cascade via FK)."""
        return await self.repo.delete_position(position_id)

    async def delete_all_positions(self) -> int:
        """Delete all positions. Returns count deleted."""
        return await self.repo.delete_all_positions()

    # ==================================================================
    # Transactions
    # ==================================================================

    async def record_transaction(self, data: TransactionCreate) -> Transaction:
        """Record a transaction and update position/lots accordingly."""
        tx_type = data.transaction_type.upper()

        if tx_type == "BUY":
            await self._handle_buy(data)
        elif tx_type == "SELL":
            await self._handle_sell(data)
        elif tx_type == "DIVIDEND":
            pass  # Just record the transaction
        elif tx_type == "DRIP":
            await self._handle_drip(data)
        elif tx_type == "SPLIT":
            await self._handle_split(data)

        # Record the transaction
        tx_row = await self.tx_repo.create_transaction({
            "ticker": data.ticker,
            "transaction_type": tx_type,
            "shares": data.shares,
            "price_per_share": data.price_per_share,
            "total_amount": data.total_amount,
            "transaction_date": data.transaction_date,
            "account": data.account,
            "fees": data.fees,
            "notes": data.notes,
        })

        return Transaction(**tx_row)

    async def get_transactions(
        self,
        ticker: str | None = None,
        transaction_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        account: str | None = None,
    ) -> list[Transaction]:
        rows = await self.tx_repo.get_all_transactions(
            ticker=ticker, transaction_type=transaction_type,
            start_date=start_date, end_date=end_date, account=account,
        )
        return [Transaction(**r) for r in rows]

    async def import_transactions(self, transactions: list[dict]) -> dict:
        """Process a batch of imported transactions through the lot engine."""
        created = 0
        failed = 0
        for tx in transactions:
            try:
                await self.record_transaction(TransactionCreate(
                    ticker=tx["ticker"],
                    transaction_type=tx["type"],
                    shares=tx.get("shares"),
                    price_per_share=tx.get("price"),
                    total_amount=(tx.get("shares") or 0) * (tx.get("price") or 0),
                    fees=tx.get("fees", 0),
                    transaction_date=tx.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
                    account=tx.get("account"),
                ))
                created += 1
            except Exception as exc:
                logger.warning("Failed to import transaction: %s — %s", tx, exc)
                failed += 1
        return {"created": created, "failed": failed, "total": len(transactions)}

    # ==================================================================
    # Lots
    # ==================================================================

    async def get_lots(self, position_id: int) -> list[Lot]:
        """Get all lots for a position with holding period info."""
        rows = await self.repo.get_lots_for_position(position_id)
        today = date.today()
        lots: list[Lot] = []
        for row in rows:
            lot = Lot(**row)
            # Compute holding period
            try:
                acquired = date.fromisoformat(lot.date_acquired)
                days = (today - acquired).days
                lot.holding_period_days = days
                lot.is_long_term = days >= 365
            except (ValueError, TypeError):
                pass
            lots.append(lot)
        return lots

    async def update_lot(self, lot_id: int, updates: dict) -> dict | None:
        """Partial update of a single lot with validation."""
        if "shares" in updates and updates["shares"] is not None:
            if updates["shares"] <= 0:
                raise ValueError("Shares must be positive")
        if "cost_basis_per_share" in updates and updates["cost_basis_per_share"] is not None:
            if updates["cost_basis_per_share"] <= 0:
                raise ValueError("Cost basis must be positive")
        return await self.repo.update_lot(lot_id, updates)

    # ==================================================================
    # Summary
    # ==================================================================

    async def get_summary(self, account: str | None = None) -> PortfolioSummary:
        """Aggregate portfolio summary with live prices."""
        positions = await self.get_all_positions(account)
        accounts = await self.account_repo.get_all_accounts()

        total_value = 0.0
        total_cost = 0.0
        day_change_total = 0.0

        for pos in positions:
            if pos.market_value:
                total_value += pos.market_value
            if pos.total_cost:
                total_cost += pos.total_cost
            if pos.day_change and pos.shares_held:
                day_change_total += pos.day_change * pos.shares_held

        gain_loss = total_value - total_cost
        gain_loss_pct = (gain_loss / total_cost) if total_cost > 0 else 0
        day_pct = (day_change_total / (total_value - day_change_total)) if total_value > day_change_total else 0

        return PortfolioSummary(
            total_value=round(total_value, 2),
            total_cost=round(total_cost, 2),
            total_gain_loss=round(gain_loss, 2),
            total_gain_loss_pct=round(gain_loss_pct, 4),
            day_change=round(day_change_total, 2),
            day_change_pct=round(day_pct, 4),
            position_count=len(positions),
            account_count=len(accounts),
        )

    # ==================================================================
    # Accounts
    # ==================================================================

    async def get_accounts(self) -> list[Account]:
        rows = await self.account_repo.get_all_accounts()
        return [Account(
            id=r["id"], name=r["name"], account_type=r["account_type"],
            is_default=bool(r["is_default"]), created_at=r["created_at"],
        ) for r in rows]

    async def create_account(self, data: AccountCreate) -> Account:
        row = await self.account_repo.create_account({
            "name": data.name,
            "account_type": data.account_type,
            "is_default": data.is_default,
        })
        return Account(
            id=row["id"], name=row["name"], account_type=row["account_type"],
            is_default=bool(row["is_default"]), created_at=row["created_at"],
        )

    async def update_account(self, account_id: int, data: dict) -> Account | None:
        row = await self.account_repo.update_account(account_id, data)
        if row is None:
            return None
        return Account(
            id=row["id"], name=row["name"], account_type=row["account_type"],
            is_default=bool(row["is_default"]), created_at=row["created_at"],
        )

    async def delete_account(self, account_id: int) -> bool:
        return await self.account_repo.delete_account(account_id)

    # ==================================================================
    # Alerts
    # ==================================================================

    async def get_alerts(self) -> list[Alert]:
        rows = await self.alert_repo.get_all_alerts()
        alerts: list[Alert] = []
        for r in rows:
            alert = Alert(
                id=r["id"], ticker=r["ticker"], alert_type=r["alert_type"],
                threshold=r["threshold"], is_active=bool(r["is_active"]),
                triggered_at=r.get("triggered_at"), created_at=r["created_at"],
            )
            # Enrich with current price
            quote = await self.mds.get_quote(r["ticker"])
            if quote:
                alert.current_price = quote.get("current_price")
            alerts.append(alert)
        return alerts

    async def create_alert(self, data: AlertCreate) -> Alert:
        row = await self.alert_repo.create_alert({
            "ticker": data.ticker,
            "alert_type": data.alert_type,
            "threshold": data.threshold,
        })
        return Alert(
            id=row["id"], ticker=row["ticker"], alert_type=row["alert_type"],
            threshold=row["threshold"], is_active=bool(row["is_active"]),
            triggered_at=row.get("triggered_at"), created_at=row["created_at"],
        )

    async def delete_alert(self, alert_id: int) -> bool:
        return await self.alert_repo.delete_alert(alert_id)

    async def check_alerts(self) -> list[Alert]:
        """Check all active alerts and trigger those that match."""
        rows = await self.alert_repo.get_all_alerts(active_only=True)
        triggered: list[Alert] = []

        for r in rows:
            quote = await self.mds.get_quote(r["ticker"])
            if not quote:
                continue
            price = quote.get("current_price", 0)
            should_trigger = False

            if r["alert_type"] == "price_above" and price >= r["threshold"]:
                should_trigger = True
            elif r["alert_type"] == "price_below" and price <= r["threshold"]:
                should_trigger = True
            elif r["alert_type"] == "pct_change":
                pct = quote.get("day_change_pct", 0) or 0
                if abs(pct) >= r["threshold"]:
                    should_trigger = True

            if should_trigger:
                updated = await self.alert_repo.trigger_alert(r["id"])
                if updated:
                    triggered.append(Alert(
                        id=updated["id"], ticker=updated["ticker"],
                        alert_type=updated["alert_type"], threshold=updated["threshold"],
                        is_active=False, triggered_at=updated.get("triggered_at"),
                        created_at=updated["created_at"], current_price=price,
                    ))

        return triggered

    # ==================================================================
    # Income
    # ==================================================================

    async def get_income(self) -> IncomeResult:
        """Compute dividend income summary."""
        positions = await self.get_all_positions()
        income_positions: list[dict] = []
        total_annual = 0.0
        total_value = sum(p.market_value or 0 for p in positions)

        for pos in positions:
            quote = await self.mds.get_quote(pos.ticker)
            div_rate = quote.get("dividend_rate", 0) if quote else 0
            div_yield = quote.get("dividend_yield", 0) if quote else 0

            if div_rate and pos.shares_held:
                annual = div_rate * pos.shares_held
                total_annual += annual
                income_positions.append({
                    "ticker": pos.ticker,
                    "shares": pos.shares_held,
                    "dividend_rate": div_rate,
                    "dividend_yield": div_yield,
                    "annual_income": round(annual, 2),
                    "monthly_income": round(annual / 12, 2),
                })

        weighted_yield = (total_annual / total_value) if total_value > 0 else None

        return IncomeResult(
            total_annual_income=round(total_annual, 2),
            total_monthly_income=round(total_annual / 12, 2),
            weighted_yield=round(weighted_yield, 4) if weighted_yield else None,
            positions=income_positions,
        )

    # ==================================================================
    # Internal helpers
    # ==================================================================

    async def _enrich_position(self, row: dict) -> Position:
        """Enrich a raw position row with live market data."""
        ticker = row["ticker"]
        shares = row["shares_held"]
        cost_basis = row.get("cost_basis_per_share")

        pos = Position(
            id=row["id"],
            ticker=ticker,
            shares_held=shares,
            cost_basis_per_share=cost_basis,
            account=row.get("account", "Manual"),
            added_at=row.get("added_at", ""),
        )

        # Company info
        company = await self.db.fetchone(
            "SELECT company_name, sector, industry FROM companies WHERE ticker = ?",
            (ticker,),
        )
        if company:
            pos.company_name = company.get("company_name")
            pos.sector = company.get("sector")
            pos.industry = company.get("industry")

        # Market data
        quote = await self.mds.get_quote(ticker)
        if quote:
            price = quote.get("current_price")
            if price:
                pos.current_price = price
                pos.market_value = round(shares * price, 2)
                if cost_basis and cost_basis > 0:
                    pos.total_cost = round(shares * cost_basis, 2)
                    pos.gain_loss = round(pos.market_value - pos.total_cost, 2)
                    pos.gain_loss_pct = round(pos.gain_loss / pos.total_cost, 4)
            pos.day_change = quote.get("day_change")
            pos.day_change_pct = quote.get("day_change_pct")

        return pos

    async def _handle_buy(self, data: TransactionCreate) -> None:
        """BUY: add shares to existing position or create new, + new lot."""
        account = data.account or "Manual"
        pos = await self.repo.get_position_by_ticker(data.ticker, account)

        if pos:
            # Update existing position (average in)
            old_shares = pos["shares_held"]
            old_cost = pos.get("cost_basis_per_share") or 0
            new_shares = old_shares + (data.shares or 0)
            if new_shares > 0 and data.price_per_share:
                new_cost = (
                    (old_shares * old_cost + (data.shares or 0) * data.price_per_share)
                    / new_shares
                )
            else:
                new_cost = old_cost
            await self.repo.update_position(pos["id"], {
                "shares_held": new_shares,
                "cost_basis_per_share": round(new_cost, 4),
            })
            position_id = pos["id"]
        else:
            # Create new position
            new_pos = await self.repo.create_position({
                "ticker": data.ticker,
                "shares_held": data.shares or 0,
                "cost_basis_per_share": data.price_per_share,
                "account": account,
            })
            position_id = new_pos["id"]

        # Create lot
        await self.repo.create_lot({
            "position_id": position_id,
            "shares": data.shares or 0,
            "cost_basis_per_share": data.price_per_share or 0,
            "date_acquired": data.transaction_date,
        })

    async def _handle_sell(self, data: TransactionCreate) -> None:
        """SELL: reduce shares, assign lots via lot_method, compute gain."""
        account = data.account or "Manual"
        pos = await self.repo.get_position_by_ticker(data.ticker, account)
        if not pos:
            logger.warning("SELL: no position found for %s in %s", data.ticker, account)
            return

        shares_to_sell = data.shares or 0
        sale_price = data.price_per_share or 0
        open_lots = await self.repo.get_open_lots(pos["id"])

        # Assign lots
        method = data.lot_method or "fifo"
        if method == "lifo":
            assignments = LotEngine.assign_lifo(open_lots, shares_to_sell)
        elif method == "avg_cost":
            assignments = LotEngine.assign_avg_cost(open_lots, shares_to_sell)
        elif method == "specific_id" and data.specific_lot_ids:
            assignments = LotEngine.assign_specific(open_lots, shares_to_sell, data.specific_lot_ids)
        else:
            assignments = LotEngine.assign_fifo(open_lots, shares_to_sell)

        # Process each lot assignment
        lots_by_id = {lot["id"]: lot for lot in open_lots}
        for lot_id, qty_sold in assignments:
            lot = lots_by_id[lot_id]
            remaining = lot["shares"] - qty_sold
            gain = round((sale_price - lot["cost_basis_per_share"]) * qty_sold, 2)

            if remaining <= 0.001:
                # Fully sold
                await self.repo.update_lot(lot_id, {
                    "shares": 0,
                    "date_sold": data.transaction_date,
                    "sale_price": sale_price,
                    "realized_gain": gain,
                })
            else:
                # Partially sold: update original, could create a sold lot record
                await self.repo.update_lot(lot_id, {"shares": remaining})

        # Update position shares
        new_shares = pos["shares_held"] - shares_to_sell
        if new_shares <= 0.001:
            await self.repo.delete_position(pos["id"])
        else:
            await self.repo.update_position(pos["id"], {"shares_held": round(new_shares, 6)})

    async def _handle_drip(self, data: TransactionCreate) -> None:
        """DRIP: dividend reinvestment — add shares as a new lot."""
        await self._handle_buy(data)

    async def _handle_split(self, data: TransactionCreate) -> None:
        """SPLIT: adjust all lots' shares and cost basis.
        data.shares = split ratio (e.g., 4.0 for a 4:1 split)
        """
        account = data.account or "Manual"
        pos = await self.repo.get_position_by_ticker(data.ticker, account)
        if not pos:
            return

        ratio = data.shares or 1.0
        if ratio <= 0:
            return

        # Adjust position
        new_shares = pos["shares_held"] * ratio
        old_cost = pos.get("cost_basis_per_share") or 0
        new_cost = old_cost / ratio if ratio > 0 else old_cost
        await self.repo.update_position(pos["id"], {
            "shares_held": round(new_shares, 6),
            "cost_basis_per_share": round(new_cost, 6),
        })

        # Adjust all lots
        lots = await self.repo.get_lots_for_position(pos["id"])
        for lot in lots:
            lot_new_shares = lot["shares"] * ratio
            lot_new_cost = lot["cost_basis_per_share"] / ratio if ratio > 0 else lot["cost_basis_per_share"]
            await self.repo.update_lot(lot["id"], {
                "shares": round(lot_new_shares, 6),
                "cost_basis_per_share": round(lot_new_cost, 6),
            })
