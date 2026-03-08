"""Research API router — profile, filings, financials, ratios, peers, notes."""

import logging

from fastapi import APIRouter, Query, Request

from models.response import success_response, error_response

logger = logging.getLogger("finance_app")

router = APIRouter(prefix="/api/v1/research", tags=["research"])


def _svc(request: Request):
    return request.app.state.research_service


# =========================================================================
# Profile
# =========================================================================

@router.get("/{ticker}/profile")
async def get_profile(ticker: str, request: Request):
    try:
        data = await _svc(request).get_profile(ticker)
        return success_response(data=data)
    except Exception as exc:
        return error_response("PROFILE_ERROR", str(exc))


# =========================================================================
# Filings
# =========================================================================

@router.get("/{ticker}/filings")
async def get_filings(
    ticker: str,
    request: Request,
    form_type: list[str] = Query(default=[]),
    limit: int = Query(default=50, ge=1, le=200),
):
    try:
        form_types = form_type if form_type else None
        filings = await _svc(request).get_filings(ticker, form_types, limit)
        return success_response(data={"filings": filings})
    except Exception as exc:
        return error_response("FILINGS_ERROR", str(exc))


@router.post("/{ticker}/filings/fetch")
async def fetch_filings(ticker: str, request: Request):
    """Trigger a fresh filing fetch from SEC EDGAR."""
    try:
        svc = _svc(request)
        result = await svc.fetch_filings(ticker)
        return success_response(data=result)
    except Exception as exc:
        logger.exception("Filing fetch failed for %s", ticker)
        return error_response("FETCH_ERROR", str(exc))


@router.get("/{ticker}/filing/{filing_id}")
async def get_filing_sections(ticker: str, filing_id: int, request: Request):
    try:
        sections = await _svc(request).get_filing_sections(filing_id)
        return success_response(data={"sections": sections})
    except Exception as exc:
        return error_response("FILING_ERROR", str(exc))


# =========================================================================
# Financials
# =========================================================================

@router.get("/{ticker}/financials")
async def get_financials(
    ticker: str,
    request: Request,
    period_type: str = Query(default="annual"),
    limit: int = Query(default=10, ge=1, le=30),
):
    try:
        rows = await _svc(request).get_financials(ticker, period_type, limit)
        return success_response(data={"financials": rows})
    except Exception as exc:
        return error_response("FINANCIALS_ERROR", str(exc))


# =========================================================================
# Ratios
# =========================================================================

@router.get("/{ticker}/ratios")
async def get_ratios(ticker: str, request: Request):
    try:
        data = await _svc(request).get_ratios(ticker)
        return success_response(data=data)
    except Exception as exc:
        return error_response("RATIOS_ERROR", str(exc))


@router.get("/{ticker}/ratios/history")
async def get_ratio_history(
    ticker: str,
    request: Request,
    metric: list[str] = Query(default=[]),
    years: int = Query(default=10, ge=1, le=20),
):
    try:
        data = await _svc(request).get_ratio_history(ticker, metric, years)
        return success_response(data=data)
    except Exception as exc:
        return error_response("RATIO_HISTORY_ERROR", str(exc))


# =========================================================================
# Peers
# =========================================================================

@router.get("/{ticker}/peers")
async def get_peers(ticker: str, request: Request):
    try:
        peers = await _svc(request).get_peers(ticker)
        return success_response(data={"peers": peers})
    except Exception as exc:
        return error_response("PEERS_ERROR", str(exc))


# =========================================================================
# Compare Filings
# =========================================================================

@router.post("/{ticker}/compare-filings")
async def compare_filings(ticker: str, request: Request):
    try:
        body = await request.json()
        left_id = body.get("left_filing_id")
        right_id = body.get("right_filing_id")
        section_key = body.get("section_key", "")
        if not left_id or not right_id:
            return error_response("VALIDATION_ERROR", "left_filing_id and right_filing_id required")
        data = await _svc(request).compare_filings(left_id, right_id, section_key)
        return success_response(data=data)
    except ValueError as exc:
        return error_response("VALIDATION_ERROR", str(exc))
    except Exception as exc:
        return error_response("COMPARE_ERROR", str(exc))


# =========================================================================
# Notes
# =========================================================================

@router.get("/{ticker}/notes")
async def get_notes(ticker: str, request: Request):
    try:
        notes = await _svc(request).get_notes(ticker)
        return success_response(data={"notes": notes})
    except Exception as exc:
        return error_response("NOTES_ERROR", str(exc))


@router.post("/{ticker}/notes")
async def create_note(ticker: str, request: Request):
    try:
        body = await request.json()
        note_text = body.get("note_text", "")
        note_type = body.get("note_type", "general")
        if not note_text.strip():
            return error_response("VALIDATION_ERROR", "note_text cannot be empty")
        note = await _svc(request).create_note(ticker, note_text, note_type)
        return success_response(data=note)
    except Exception as exc:
        return error_response("NOTE_CREATE_ERROR", str(exc))


@router.put("/notes/{note_id}")
async def update_note(note_id: int, request: Request):
    try:
        body = await request.json()
        updated = await _svc(request).update_note(note_id, body)
        if updated is None:
            return error_response("NOT_FOUND", f"Note {note_id} not found")
        return success_response(data=updated)
    except Exception as exc:
        return error_response("NOTE_UPDATE_ERROR", str(exc))


@router.delete("/notes/{note_id}")
async def delete_note(note_id: int, request: Request):
    try:
        deleted = await _svc(request).delete_note(note_id)
        return success_response(data={"deleted": deleted})
    except Exception as exc:
        return error_response("NOTE_DELETE_ERROR", str(exc))
