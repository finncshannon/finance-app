"""Universe router — manage the investable stock universe.

Endpoints for loading, querying, and refreshing the universe
(e.g. Russell 3000 tickers via SEC EDGAR CIK mapping).
"""

import asyncio
import time

from fastapi import APIRouter, Request
from pydantic import BaseModel

from models.response import success_response

router = APIRouter(prefix="/api/v1/universe", tags=["universe"])


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class LoadUniverseBody(BaseModel):
    name: str = "r3000"


class RefreshUniverseBody(BaseModel):
    universe: str = "r3000"


class LoadCuratedBody(BaseModel):
    name: str | None = None  # "dow", "sp500", "r3000", or None for all


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/stats")
async def get_universe_stats(request: Request):
    """Universe statistics: total count, financials coverage, etc."""
    t0 = time.monotonic()
    svc = request.app.state.universe_service
    stats = await svc.get_universe_stats()
    ms = int((time.monotonic() - t0) * 1000)
    return success_response(data=stats, duration_ms=ms)


@router.get("/tickers")
async def get_universe_tickers(request: Request, universe: str = "r3000"):
    """List all tickers in the given universe."""
    t0 = time.monotonic()
    svc = request.app.state.universe_service
    tickers = await svc.get_universe_tickers(universe)
    ms = int((time.monotonic() - t0) * 1000)
    return success_response(data=tickers, duration_ms=ms)


@router.post("/load")
async def load_universe(request: Request, body: LoadUniverseBody = LoadUniverseBody()):
    """Trigger initial universe load from SEC EDGAR CIK mapping."""
    t0 = time.monotonic()
    svc = request.app.state.universe_service
    count = await svc.load_universe(body.name)
    ms = int((time.monotonic() - t0) * 1000)
    return success_response(
        data={"loaded": count, "universe": body.name},
        duration_ms=ms,
    )


@router.post("/refresh")
async def refresh_universe(request: Request, body: RefreshUniverseBody = RefreshUniverseBody()):
    """Re-fetch CIK mapping and add any new tickers."""
    t0 = time.monotonic()
    svc = request.app.state.universe_service
    result = await svc.refresh_universe(body.universe)
    ms = int((time.monotonic() - t0) * 1000)
    return success_response(data=result, duration_ms=ms)


@router.post("/load-curated")
async def load_curated_universe(request: Request, body: LoadCuratedBody = LoadCuratedBody()):
    """Load curated universe from static JSON files."""
    t0 = time.monotonic()
    svc = request.app.state.universe_service
    if body.name:
        count = await svc.load_curated_universe(body.name)
        result = {body.name: count}
    else:
        result = await svc.load_all_curated()
    ms = int((time.monotonic() - t0) * 1000)
    return success_response(data=result, duration_ms=ms)


@router.get("/hydration-status")
async def get_hydration_status(request: Request):
    """Return current hydration progress."""
    svc = request.app.state.hydration_service
    return success_response(data=svc.progress.to_dict())


@router.post("/hydrate")
async def trigger_hydration(request: Request):
    """Manually trigger a hydration run."""
    svc = request.app.state.hydration_service
    if svc._running:
        return success_response(data={"message": "Hydration already running", **svc.progress.to_dict()})
    asyncio.create_task(svc.run_hydration())
    return success_response(data={"message": "Hydration started"})
