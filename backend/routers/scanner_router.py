"""Scanner API router — filter, search, presets, rank, metrics."""

import time

from fastapi import APIRouter, Request

from models.response import success_response, error_response
from services.scanner.models import (
    ScannerRequest, TextSearchRequest, RankRequest, PresetSaveRequest,
)

router = APIRouter(prefix="/api/v1/scanner", tags=["scanner"])


def _svc(request: Request):
    """Get the ScannerService from app state."""
    return request.app.state.scanner_service


# =========================================================================
# 1. POST /screen — combined filter + text search
# =========================================================================

@router.post("/screen")
async def run_screen(body: ScannerRequest, request: Request):
    """Run a combined filter + optional text search screen."""
    try:
        svc = _svc(request)
        result = await svc.scan(body)
        return success_response(
            data=result.model_dump(),
            duration_ms=result.computation_time_ms,
        )
    except Exception as exc:
        return error_response("SCAN_ERROR", str(exc))


# =========================================================================
# 2. POST /filter — metric filters only (no text search)
# =========================================================================

@router.post("/filter")
async def filter_metrics(body: ScannerRequest, request: Request):
    """Run financial metric filters only."""
    try:
        svc = _svc(request)
        body.text_query = None  # Strip text search
        result = await svc.scan(body)
        return success_response(
            data=result.model_dump(),
            duration_ms=result.computation_time_ms,
        )
    except Exception as exc:
        return error_response("FILTER_ERROR", str(exc))


# =========================================================================
# 3. POST /search — filing text search only
# =========================================================================

@router.post("/search")
async def search_filings(body: TextSearchRequest, request: Request):
    """Run keyword search on filing sections."""
    try:
        svc = _svc(request)
        t0 = time.perf_counter()
        hits = await svc.text_search(body)
        elapsed = int((time.perf_counter() - t0) * 1000)
        return success_response(
            data={
                "hits": [h.model_dump() for h in hits],
                "count": len(hits),
            },
            duration_ms=elapsed,
        )
    except Exception as exc:
        return error_response("SEARCH_ERROR", str(exc))


# =========================================================================
# 4. POST /rank — composite ranking
# =========================================================================

@router.post("/rank")
async def composite_rank(body: RankRequest, request: Request):
    """Composite ranking across multiple metrics."""
    try:
        svc = _svc(request)
        result = await svc.composite_rank(body)
        return success_response(data=result.model_dump())
    except Exception as exc:
        return error_response("RANK_ERROR", str(exc))


# =========================================================================
# 5. GET /presets — list all presets (built-in + user-saved)
# =========================================================================

@router.get("/presets")
async def get_presets(request: Request):
    """Get built-in + user-saved screening presets."""
    try:
        svc = _svc(request)
        presets = await svc.get_all_presets()
        return success_response(data={"presets": presets})
    except Exception as exc:
        return error_response("PRESET_ERROR", str(exc))


# =========================================================================
# 6. POST /presets — save a new preset
# =========================================================================

@router.post("/presets")
async def save_preset(body: PresetSaveRequest, request: Request):
    """Save a new scanner preset."""
    try:
        svc = _svc(request)
        preset = await svc.save_preset(body.model_dump())
        return success_response(data=preset)
    except Exception as exc:
        return error_response("PRESET_SAVE_ERROR", str(exc))


# =========================================================================
# 7. DELETE /presets/{preset_id}
# =========================================================================

@router.delete("/presets/{preset_id}")
async def delete_preset(preset_id: int, request: Request):
    """Delete a user-saved preset."""
    try:
        svc = _svc(request)
        deleted = await svc.delete_preset(preset_id)
        return success_response(data={"deleted": deleted})
    except Exception as exc:
        return error_response("PRESET_DELETE_ERROR", str(exc))


# =========================================================================
# 8. GET /metrics — metrics catalog for the frontend
# =========================================================================

@router.get("/metrics")
async def get_metrics_catalog(request: Request):
    """Return all scannable metrics with categories."""
    svc = _svc(request)
    return success_response(data=svc.get_metrics_catalog())


# =========================================================================
# Universe endpoints (delegate to UniverseService)
# =========================================================================

@router.get("/universe")
async def get_universe(request: Request):
    """Get current universe tickers."""
    try:
        universe_svc = request.app.state.universe_service
        tickers = await universe_svc.get_universe_tickers("all")
        return success_response(data={"tickers": tickers, "count": len(tickers)})
    except Exception as exc:
        return error_response("UNIVERSE_ERROR", str(exc))


@router.get("/universe/stats")
async def get_universe_stats(request: Request):
    """Universe size, composition."""
    try:
        universe_svc = request.app.state.universe_service
        stats = await universe_svc.get_universe_stats()
        return success_response(data=stats)
    except Exception as exc:
        return error_response("UNIVERSE_STATS_ERROR", str(exc))
