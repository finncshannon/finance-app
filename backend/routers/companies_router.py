"""Companies router — full company CRUD, quotes, financials, metrics, filings.

All endpoints use the standard response envelope.
Services accessed via request.app.state.
"""

import time

from fastapi import APIRouter, Request
from pydantic import BaseModel

from models.response import success_response, error_response
from providers.sec_edgar import SECEdgarEmailNotConfigured

router = APIRouter(prefix="/api/v1/companies", tags=["companies"])


class LookupBody(BaseModel):
    ticker: str


# --- Search ---


@router.get("/search")
async def search_companies(request: Request, q: str = ""):
    """Search companies by ticker or name."""
    t0 = time.monotonic()
    if not q or len(q) < 1:
        return error_response("VALIDATION_ERROR", "Query parameter 'q' is required.")

    svc = request.app.state.company_service
    results = await svc.search_companies(q)
    ms = int((time.monotonic() - t0) * 1000)
    return success_response(data=results, duration_ms=ms)


# --- Company profile ---


@router.get("/{ticker}")
async def get_company(request: Request, ticker: str):
    """Get full company profile. Auto-creates on first access."""
    t0 = time.monotonic()
    svc = request.app.state.company_service
    company = await svc.get_or_create_company(ticker)
    ms = int((time.monotonic() - t0) * 1000)
    if not company:
        return error_response("TICKER_NOT_FOUND", f"No data found for {ticker.upper()}.", duration_ms=ms)
    return success_response(data=company, duration_ms=ms)


# --- Quote ---


@router.get("/{ticker}/quote")
async def get_quote(request: Request, ticker: str):
    """Get current market quote data."""
    t0 = time.monotonic()
    market_svc = request.app.state.market_data_service
    quote = await market_svc.get_quote(ticker)
    ms = int((time.monotonic() - t0) * 1000)
    if not quote:
        return error_response("NO_QUOTE", f"No quote data for {ticker.upper()}.", duration_ms=ms)
    return success_response(data=quote, duration_ms=ms)


# --- Historical prices ---


@router.get("/{ticker}/historical")
async def get_historical(request: Request, ticker: str, period: str = "1y", interval: str = "1d"):
    """Get historical OHLCV price bars."""
    t0 = time.monotonic()
    market_svc = request.app.state.market_data_service
    bars = await market_svc.get_historical(ticker, period, interval)
    ms = int((time.monotonic() - t0) * 1000)
    return success_response(
        data=[b.model_dump() for b in bars],
        duration_ms=ms,
    )


# --- Financials ---


@router.get("/{ticker}/financials")
async def get_financials(request: Request, ticker: str, years: int = 10):
    """Get historical financial statements."""
    t0 = time.monotonic()
    market_svc = request.app.state.market_data_service
    financials = await market_svc.get_financials(ticker)
    ms = int((time.monotonic() - t0) * 1000)
    # Limit to requested years
    if financials and len(financials) > years:
        financials = financials[:years]
    return success_response(data=financials, duration_ms=ms)


# --- Metrics ---


@router.get("/{ticker}/metrics")
async def get_metrics(request: Request, ticker: str):
    """Get all computed financial metrics (30+)."""
    t0 = time.monotonic()
    extraction_svc = request.app.state.data_extraction_service
    metrics = await extraction_svc.compute_all_metrics(ticker)
    ms = int((time.monotonic() - t0) * 1000)
    return success_response(data=metrics, duration_ms=ms)


# --- Filings ---


@router.get("/{ticker}/filings")
async def get_filings(request: Request, ticker: str, form_type: str = "10-K", limit: int = 10):
    """Get SEC filing index for a company."""
    try:
        t0 = time.monotonic()
        sec = request.app.state.sec_provider
        entries = await sec.get_filing_index(ticker, [form_type], limit=limit)
        ms = int((time.monotonic() - t0) * 1000)
        return success_response(
            data=[e.model_dump() for e in entries],
            duration_ms=ms,
        )
    except SECEdgarEmailNotConfigured:
        return error_response(
            "SEC_EMAIL_REQUIRED",
            "SEC EDGAR email required. Set it in Settings → Data Sources.",
        )


# --- Events ---


@router.get("/{ticker}/events")
async def get_company_events(request: Request, ticker: str):
    """Get upcoming events (earnings, dividends) for a company."""
    t0 = time.monotonic()
    events_svc = request.app.state.events_service
    events = await events_svc.get_events_for_ticker(ticker)
    ms = int((time.monotonic() - t0) * 1000)
    return success_response(data=events, duration_ms=ms)


# --- Lookup (create if new) ---


@router.post("/lookup")
async def lookup_company(request: Request, body: LookupBody):
    """Look up ticker, auto-create if new. Idempotent."""
    t0 = time.monotonic()
    svc = request.app.state.company_service
    company = await svc.get_or_create_company(body.ticker)
    ms = int((time.monotonic() - t0) * 1000)
    if not company:
        return error_response("TICKER_NOT_FOUND", f"Could not resolve {body.ticker.upper()}.", duration_ms=ms)
    return success_response(data=company, duration_ms=ms)


# --- Force refresh ---


@router.post("/{ticker}/refresh")
async def refresh_company(request: Request, ticker: str):
    """Force data refresh from all providers."""
    t0 = time.monotonic()
    company_svc = request.app.state.company_service
    market_svc = request.app.state.market_data_service

    company = await company_svc.enrich_company(ticker)
    refresh_result = await market_svc.refresh_batch([ticker])

    ms = int((time.monotonic() - t0) * 1000)
    return success_response(
        data={
            "ticker": ticker.upper(),
            "company": company,
            "refresh_result": refresh_result,
        },
        duration_ms=ms,
    )
