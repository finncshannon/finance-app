"""Portfolio API router — positions, transactions, lots, accounts, alerts, analytics."""

from fastapi import APIRouter, Request, Query
from pydantic import BaseModel

from models.response import success_response, error_response
from services.portfolio.models import (
    PositionCreate, TransactionCreate,
    AccountCreate, AlertCreate,
    ImportPreview,
)

router = APIRouter(prefix="/api/v1/portfolio", tags=["portfolio"])


# =========================================================================
# Request Models
# =========================================================================

class UpdatePositionBody(BaseModel):
    shares: float | None = None
    shares_held: float | None = None
    cost_basis_per_share: float | None = None
    account: str | None = None
    date_acquired: str | None = None
    notes: str | None = None


class UpdateLotBody(BaseModel):
    shares: float | None = None
    cost_basis_per_share: float | None = None
    date_acquired: str | None = None


class ImportPreviewBody(BaseModel):
    csv_content: str
    broker: str = "generic"


class ImportExecuteBody(BaseModel):
    transactions: list[dict]


def _svc(request: Request):
    return request.app.state.portfolio_service


# =========================================================================
# Positions
# =========================================================================

@router.get("/positions")
async def get_positions(request: Request, account: str | None = None):
    """Get all positions enriched with live prices."""
    try:
        svc = _svc(request)
        positions = await svc.get_all_positions(account)
        return success_response(data={
            "positions": [p.model_dump() for p in positions],
        })
    except Exception as exc:
        return error_response("POSITION_ERROR", str(exc))


@router.post("/positions")
async def add_position(body: PositionCreate, request: Request):
    """Add a new position + initial lot + BUY transaction."""
    try:
        svc = _svc(request)
        position = await svc.add_position(body)
        return success_response(data=position.model_dump())
    except Exception as exc:
        return error_response("POSITION_CREATE_ERROR", str(exc))


@router.put("/positions/{position_id}")
async def update_position(position_id: int, body: UpdatePositionBody, request: Request):
    """Update a position (partial update)."""
    try:
        svc = _svc(request)
        updates = body.model_dump(exclude_none=True)
        if not updates:
            return error_response("VALIDATION_ERROR", "No fields to update")
        position = await svc.update_position(position_id, updates)
        if position is None:
            return error_response("NOT_FOUND", f"Position {position_id} not found")
        return success_response(data=position.model_dump())
    except ValueError as exc:
        return error_response("VALIDATION_ERROR", str(exc))
    except Exception as exc:
        return error_response("POSITION_UPDATE_ERROR", str(exc))


@router.delete("/positions/{position_id}")
async def delete_position(position_id: int, request: Request):
    """Remove a position and cascade lots."""
    try:
        svc = _svc(request)
        deleted = await svc.delete_position(position_id)
        return success_response(data={"deleted": deleted})
    except Exception as exc:
        return error_response("POSITION_DELETE_ERROR", str(exc))


@router.post("/positions/clear-all")
async def delete_all_positions(request: Request):
    """Remove all positions."""
    try:
        svc = _svc(request)
        count = await svc.delete_all_positions()
        return success_response(data={"deleted": count})
    except Exception as exc:
        return error_response("POSITION_DELETE_ERROR", str(exc))


# =========================================================================
# Lots
# =========================================================================

@router.get("/lots/{position_id}")
async def get_lots(position_id: int, request: Request):
    """Get individual lots for a position with holding period info."""
    try:
        svc = _svc(request)
        lots = await svc.get_lots(position_id)
        return success_response(data={
            "lots": [lot.model_dump() for lot in lots],
        })
    except Exception as exc:
        return error_response("LOT_ERROR", str(exc))


@router.put("/lots/{lot_id}")
async def update_lot(lot_id: int, body: UpdateLotBody, request: Request):
    """Update a single lot (partial update)."""
    try:
        svc = _svc(request)
        updates = body.model_dump(exclude_none=True)
        if not updates:
            return error_response("VALIDATION_ERROR", "No fields to update")
        result = await svc.update_lot(lot_id, updates)
        if not result:
            return error_response("NOT_FOUND", f"Lot {lot_id} not found")
        return success_response(data=result)
    except ValueError as exc:
        return error_response("VALIDATION_ERROR", str(exc))
    except Exception as exc:
        return error_response("LOT_UPDATE_ERROR", str(exc))


# =========================================================================
# Transactions
# =========================================================================

@router.get("/transactions")
async def get_transactions(
    request: Request,
    ticker: str | None = None,
    type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    account: str | None = None,
):
    """Get transaction history (filterable)."""
    try:
        svc = _svc(request)
        txs = await svc.get_transactions(
            ticker=ticker, transaction_type=type,
            start_date=start_date, end_date=end_date, account=account,
        )
        return success_response(data={
            "transactions": [tx.model_dump() for tx in txs],
        })
    except Exception as exc:
        return error_response("TRANSACTION_ERROR", str(exc))


@router.post("/transactions")
async def add_transaction(body: TransactionCreate, request: Request):
    """Record a transaction (auto-updates position + lots)."""
    try:
        svc = _svc(request)
        tx = await svc.record_transaction(body)
        return success_response(data=tx.model_dump())
    except Exception as exc:
        return error_response("TRANSACTION_CREATE_ERROR", str(exc))


# =========================================================================
# Summary
# =========================================================================

@router.get("/summary")
async def get_portfolio_summary(request: Request, account: str | None = None):
    """Get portfolio-level summary with live prices."""
    try:
        svc = _svc(request)
        summary = await svc.get_summary(account)
        return success_response(data=summary.model_dump())
    except Exception as exc:
        return error_response("SUMMARY_ERROR", str(exc))


# =========================================================================
# Performance
# =========================================================================

@router.get("/performance")
async def get_performance(
    request: Request,
    period: str = "1Y",
    account: str | None = None,
):
    """TWR, MWRR, Sharpe, Sortino, risk metrics."""
    try:
        analytics = request.app.state.portfolio_analytics
        result = await analytics.compute_performance(account, period)
        return success_response(data=result.model_dump())
    except Exception as exc:
        return error_response("PERFORMANCE_ERROR", str(exc))


# =========================================================================
# Benchmark
# =========================================================================

@router.get("/benchmark")
async def get_benchmark(
    request: Request,
    benchmark: str = "SPY",
    period: str = "1Y",
    account: str | None = None,
):
    """Compare portfolio vs benchmark returns."""
    try:
        bench_svc = request.app.state.benchmark_service
        result = await bench_svc.get_benchmark_comparison(benchmark, period, account)
        return success_response(data=result.model_dump())
    except Exception as exc:
        return error_response("BENCHMARK_ERROR", str(exc))


# =========================================================================
# Attribution
# =========================================================================

@router.get("/attribution")
async def get_attribution(
    request: Request,
    benchmark: str = "SPY",
    period: str = "1Y",
    account: str | None = None,
):
    """Brinson sector attribution analysis."""
    try:
        attr_svc = request.app.state.attribution_service
        result = await attr_svc.compute_brinson_attribution(benchmark, period, account)
        return success_response(data=result.model_dump())
    except Exception as exc:
        return error_response("ATTRIBUTION_ERROR", str(exc))


# =========================================================================
# Income
# =========================================================================

@router.get("/income")
async def get_income(request: Request, account: str | None = None):
    """Enhanced dividend income tracking + projections."""
    try:
        income_svc = getattr(request.app.state, "income_service", None)
        if income_svc:
            result = await income_svc.get_enhanced_income(account)
            return success_response(data=result)
        # Fallback to basic income
        svc = _svc(request)
        result = await svc.get_income()
        return success_response(data=result.model_dump())
    except Exception as exc:
        return error_response("INCOME_ERROR", str(exc))


@router.get("/income/upcoming-dividends")
async def get_upcoming_dividends(request: Request, account: str | None = None):
    """Get upcoming ex-dividend dates for portfolio positions."""
    try:
        portfolio_svc = _svc(request)
        positions = await portfolio_svc.repo.get_all_positions(account)
        tickers = list({p["ticker"] for p in positions})

        events_svc = getattr(request.app.state, "events_service", None)
        if not events_svc:
            return success_response(data={"upcoming": [], "message": "Events system not available"})

        # Get all upcoming events and filter to portfolio tickers + dividend types
        all_events = await events_svc.get_upcoming_events(limit=200)
        ticker_set = set(tickers)
        ticker_shares = {p["ticker"]: p.get("shares_held", 0) for p in positions}

        enriched = []
        for event in all_events:
            evt_ticker = event.get("ticker", "")
            evt_type = event.get("event_type", "")
            if evt_ticker not in ticker_set:
                continue
            if evt_type not in ("ex_dividend", "dividend"):
                continue
            shares = ticker_shares.get(evt_ticker, 0)
            amount = event.get("amount_per_share", 0)
            enriched.append({
                **event,
                "shares_held": shares,
                "expected_income": round(amount * shares, 2) if amount else None,
            })
        return success_response(data={"upcoming": enriched})
    except Exception as exc:
        import logging
        logging.getLogger("finance_app").warning("Failed to fetch upcoming dividends: %s", exc)
        return success_response(data={"upcoming": [], "message": "Could not fetch events"})


# =========================================================================
# Transaction Import
# =========================================================================

@router.post("/import/transactions/preview")
async def preview_transaction_import(body: ImportPreviewBody, request: Request):
    """Parse transaction CSV and return parsed transactions for review."""
    try:
        from services.portfolio.csv_import import parse_csv
        result = parse_csv(body.csv_content, body.broker, import_type="transactions")
        return success_response(data={
            "success": result.success,
            "transactions": [t.__dict__ for t in result.transactions],
            "errors": result.errors,
            "warnings": result.warnings,
            "row_count": result.row_count,
            "skipped_count": result.skipped_count,
        })
    except Exception as exc:
        return error_response("TX_IMPORT_PREVIEW_ERROR", str(exc))


@router.post("/import/transactions/execute")
async def execute_transaction_import(body: ImportExecuteBody, request: Request):
    """Execute transaction import via lot engine."""
    try:
        svc = _svc(request)
        results = await svc.import_transactions(body.transactions)
        return success_response(data=results)
    except Exception as exc:
        return error_response("TX_IMPORT_EXECUTE_ERROR", str(exc))


# =========================================================================
# Import (Position CSV — legacy)
# =========================================================================

@router.post("/import/preview")
async def import_preview(request: Request):
    """Preview CSV import."""
    try:
        from services.portfolio.csv_import import CSVImporter

        body = await request.json()
        content = body.get("content", "")
        broker = body.get("broker", "generic")

        importer = CSVImporter()
        preview = await importer.parse_csv(content, broker)
        return success_response(data=preview.model_dump())
    except Exception as exc:
        return error_response("IMPORT_PREVIEW_ERROR", str(exc))


@router.post("/import/execute")
async def import_execute(request: Request):
    """Execute CSV import from preview."""
    try:
        from services.portfolio.csv_import import CSVImporter
        from services.portfolio.models import ImportPreview as ImportPreviewModel

        body = await request.json()
        preview_data = body.get("preview", {})
        preview = ImportPreviewModel(**preview_data)

        svc = _svc(request)
        importer = CSVImporter()
        result = await importer.import_positions(preview, svc)
        return success_response(data=result.model_dump())
    except Exception as exc:
        return error_response("IMPORT_EXECUTE_ERROR", str(exc))


# =========================================================================
# Accounts
# =========================================================================

@router.get("/accounts")
async def get_accounts(request: Request):
    """List portfolio accounts."""
    try:
        svc = _svc(request)
        accounts = await svc.get_accounts()
        return success_response(data={
            "accounts": [a.model_dump() for a in accounts],
        })
    except Exception as exc:
        return error_response("ACCOUNT_ERROR", str(exc))


@router.post("/accounts")
async def create_account(body: AccountCreate, request: Request):
    """Create a portfolio account."""
    try:
        svc = _svc(request)
        account = await svc.create_account(body)
        return success_response(data=account.model_dump())
    except Exception as exc:
        return error_response("ACCOUNT_CREATE_ERROR", str(exc))


@router.put("/accounts/{account_id}")
async def update_account(account_id: int, body: dict, request: Request):
    """Update a portfolio account."""
    try:
        svc = _svc(request)
        account = await svc.update_account(account_id, body)
        if account is None:
            return error_response("NOT_FOUND", f"Account {account_id} not found")
        return success_response(data=account.model_dump())
    except Exception as exc:
        return error_response("ACCOUNT_UPDATE_ERROR", str(exc))


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: int, request: Request):
    """Delete a portfolio account."""
    try:
        svc = _svc(request)
        deleted = await svc.delete_account(account_id)
        return success_response(data={"deleted": deleted})
    except Exception as exc:
        return error_response("ACCOUNT_DELETE_ERROR", str(exc))


# =========================================================================
# Alerts
# =========================================================================

@router.get("/alerts")
async def get_alerts(request: Request):
    """Get price alerts."""
    try:
        svc = _svc(request)
        alerts = await svc.get_alerts()
        return success_response(data={
            "alerts": [a.model_dump() for a in alerts],
        })
    except Exception as exc:
        return error_response("ALERT_ERROR", str(exc))


@router.post("/alerts")
async def create_alert(body: AlertCreate, request: Request):
    """Create a price alert."""
    try:
        svc = _svc(request)
        alert = await svc.create_alert(body)
        return success_response(data=alert.model_dump())
    except Exception as exc:
        return error_response("ALERT_CREATE_ERROR", str(exc))


# =========================================================================
# Implied Prices (cross-module: joins models + model_outputs)
# =========================================================================

@router.get("/implied-prices")
async def get_implied_prices(request: Request):
    """Return latest intrinsic value per share for each ticker that has a model output."""
    try:
        db = request.app.state.db
        rows = await db.fetchall(
            """
            SELECT m.ticker, m.model_type, o.intrinsic_value_per_share, o.run_timestamp
            FROM models m
            JOIN model_outputs o ON o.model_id = m.id
            WHERE o.intrinsic_value_per_share IS NOT NULL
              AND o.run_number = (
                SELECT MAX(o2.run_number) FROM model_outputs o2 WHERE o2.model_id = m.id
              )
            ORDER BY m.ticker
            """
        )
        result = {}
        for row in rows:
            ticker = row[0]
            # If multiple model types exist for same ticker, keep the first (ordered by query)
            if ticker not in result:
                result[ticker] = {
                    "ticker": ticker,
                    "model_type": row[1],
                    "intrinsic_value": row[2],
                    "run_timestamp": row[3],
                }
        return success_response(data={"implied_prices": list(result.values())})
    except Exception as exc:
        return error_response("IMPLIED_PRICES_ERROR", str(exc))


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int, request: Request):
    """Delete a price alert."""
    try:
        svc = _svc(request)
        deleted = await svc.delete_alert(alert_id)
        return success_response(data={"deleted": deleted})
    except Exception as exc:
        return error_response("ALERT_DELETE_ERROR", str(exc))
