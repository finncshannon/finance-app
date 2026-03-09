"""News API router — top news and company-specific news from RSS feeds."""

import logging

from fastapi import APIRouter, Query, Request

from models.response import success_response, error_response
from repositories.company_repo import CompanyRepo

logger = logging.getLogger("finance_app")

router = APIRouter(prefix="/api/v1/news", tags=["news"])


def _svc(request: Request):
    return request.app.state.news_service


@router.get("/top")
async def get_top_news(
    request: Request,
    limit: int = Query(default=2000, ge=1, le=5000),
    days: int = Query(default=10, ge=1, le=30),
):
    """Return news stories from the last N days."""
    try:
        articles = await _svc(request).get_top_news(limit=limit, days=days)
        return success_response(data={"articles": articles})
    except Exception as exc:
        logger.exception("Failed to fetch top news")
        return error_response("NEWS_ERROR", str(exc))


@router.get("/company/{ticker}")
async def get_company_news(
    request: Request,
    ticker: str,
    limit: int = Query(default=200, ge=1, le=500),
):
    """Return news for a specific company."""
    try:
        # Look up company name for broader search
        company_repo = CompanyRepo(request.app.state.db)
        company = await company_repo.get_by_ticker(ticker.upper())
        company_name = company.get("company_name") if company else None

        articles = await _svc(request).get_company_news(
            ticker=ticker.upper(),
            company_name=company_name,
            limit=limit,
        )
        return success_response(data={"articles": articles, "ticker": ticker.upper()})
    except Exception as exc:
        logger.exception("Failed to fetch company news for %s", ticker)
        return error_response("NEWS_ERROR", str(exc))
