"""Dashboard API router — summary, market, watchlists, models, events."""

from fastapi import APIRouter, Request

from models.response import success_response, error_response

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _dashboard(request: Request):
    return request.app.state.dashboard_service


def _watchlist(request: Request):
    return request.app.state.watchlist_service


# =========================================================================
# Dashboard Summary
# =========================================================================

@router.get("/summary")
async def get_summary(request: Request):
    """Full dashboard data in one call."""
    try:
        svc = _dashboard(request)
        data = await svc.get_dashboard_summary()
        return success_response(data=data)
    except Exception as exc:
        return error_response("DASHBOARD_ERROR", str(exc))


@router.get("/market")
async def get_market(request: Request):
    """Market overview only."""
    try:
        svc = _dashboard(request)
        data = await svc.get_market_overview()
        return success_response(data=data)
    except Exception as exc:
        return error_response("MARKET_ERROR", str(exc))


@router.get("/models/recent")
async def get_recent_models(request: Request, limit: int = 5):
    """Recent valuation models."""
    try:
        svc = _dashboard(request)
        models = await svc.get_recent_models(limit)
        return success_response(data={"models": models})
    except Exception as exc:
        return error_response("MODELS_ERROR", str(exc))


# =========================================================================
# Events
# =========================================================================

@router.get("/events/refresh-status")
async def get_events_refresh_status(request: Request):
    """Current progress of background event fetch."""
    try:
        svc = request.app.state.events_service
        return success_response(data=svc._refresh_progress)
    except Exception as exc:
        return error_response("REFRESH_STATUS_ERROR", str(exc))


@router.get("/events")
async def get_events(
    request: Request,
    source: str = "all",
    watchlist_id: int | None = None,
    event_types: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 10,
    offset: int = 0,
):
    """Upcoming events with source, type, date, and pagination filters."""
    try:
        svc = _dashboard(request)
        types_list = event_types.split(",") if event_types else None
        result = await svc.get_filtered_events(
            source=source,
            watchlist_id=watchlist_id,
            event_types=types_list,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
        return success_response(data=result)
    except Exception as exc:
        return error_response("EVENTS_ERROR", str(exc))


# =========================================================================
# Watchlists
# =========================================================================

@router.get("/watchlists")
async def get_watchlists(request: Request):
    """Get all watchlists with item counts."""
    try:
        svc = _watchlist(request)
        watchlists = await svc.get_all_watchlists()
        return success_response(data={"watchlists": watchlists})
    except Exception as exc:
        return error_response("WATCHLIST_ERROR", str(exc))


@router.get("/watchlists/{watchlist_id}")
async def get_watchlist(watchlist_id: int, request: Request):
    """Get single watchlist with enriched items."""
    try:
        svc = _watchlist(request)
        wl = await svc.get_watchlist(watchlist_id)
        if wl is None:
            return error_response("NOT_FOUND", f"Watchlist {watchlist_id} not found")
        return success_response(data=wl)
    except Exception as exc:
        return error_response("WATCHLIST_ERROR", str(exc))


@router.post("/watchlists")
async def create_watchlist(request: Request):
    """Create a watchlist."""
    try:
        body = await request.json()
        name = body.get("name", "")
        svc = _watchlist(request)
        wl = await svc.create_watchlist(name)
        return success_response(data=wl)
    except ValueError as exc:
        return error_response("VALIDATION_ERROR", str(exc))
    except Exception as exc:
        return error_response("WATCHLIST_CREATE_ERROR", str(exc))


@router.put("/watchlists/{watchlist_id}")
async def update_watchlist(watchlist_id: int, request: Request):
    """Update watchlist name or sort_order."""
    try:
        body = await request.json()
        svc = _watchlist(request)
        wl = await svc.update_watchlist(watchlist_id, body)
        if wl is None:
            return error_response("NOT_FOUND", f"Watchlist {watchlist_id} not found")
        return success_response(data=wl)
    except Exception as exc:
        return error_response("WATCHLIST_UPDATE_ERROR", str(exc))


@router.delete("/watchlists/{watchlist_id}")
async def delete_watchlist(watchlist_id: int, request: Request):
    """Delete watchlist and cascade items."""
    try:
        svc = _watchlist(request)
        deleted = await svc.delete_watchlist(watchlist_id)
        return success_response(data={"deleted": deleted})
    except Exception as exc:
        return error_response("WATCHLIST_DELETE_ERROR", str(exc))


@router.post("/watchlists/{watchlist_id}/items")
async def add_watchlist_item(watchlist_id: int, request: Request):
    """Add ticker to watchlist."""
    try:
        body = await request.json()
        ticker = body.get("ticker", "")
        svc = _watchlist(request)
        item = await svc.add_item(watchlist_id, ticker)
        return success_response(data=item)
    except ValueError as exc:
        return error_response("VALIDATION_ERROR", str(exc))
    except Exception as exc:
        return error_response("WATCHLIST_ITEM_ERROR", str(exc))


@router.delete("/watchlists/{watchlist_id}/items/{ticker}")
async def remove_watchlist_item(watchlist_id: int, ticker: str, request: Request):
    """Remove ticker from watchlist."""
    try:
        svc = _watchlist(request)
        deleted = await svc.remove_item(watchlist_id, ticker)
        return success_response(data={"deleted": deleted})
    except Exception as exc:
        return error_response("WATCHLIST_ITEM_ERROR", str(exc))


@router.put("/watchlists/{watchlist_id}/items/reorder")
async def reorder_watchlist_items(watchlist_id: int, request: Request):
    """Reorder watchlist items."""
    try:
        body = await request.json()
        tickers = body.get("tickers", [])
        svc = _watchlist(request)
        await svc.reorder_items(watchlist_id, tickers)
        return success_response(data={"reordered": True})
    except Exception as exc:
        return error_response("WATCHLIST_REORDER_ERROR", str(exc))
