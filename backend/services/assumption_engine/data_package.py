"""GATHER stage — pure I/O, no computation.

Queries all data sources and assembles a CompanyDataPackage.
"""

from __future__ import annotations

import logging

from .constants import (
    BROAD_MARKET_DEFAULTS,
    DEFAULT_RISK_FREE_RATE,
    SECTOR_BENCHMARKS,
)
from .models import (
    AnalystEstimates,
    CompanyDataPackage,
    CompanyProfile,
    IndustryBenchmarks,
    QuoteData,
)

logger = logging.getLogger("finance_app")


class InsufficientDataError(Exception):
    """Raised when a company has fewer than 3 years of revenue data."""


async def gather_company_data(
    ticker: str,
    *,
    company_repo,
    market_data_repo,
    market_data_svc,
) -> CompanyDataPackage:
    """Assemble a CompanyDataPackage from all available data sources.

    Raises InsufficientDataError if fewer than 3 years of revenue data.
    """
    ticker = ticker.upper()

    # 1. Company profile ------------------------------------------------
    company = await company_repo.get_by_ticker(ticker)
    if not company:
        # Try fetching via market data service
        company = await market_data_svc.get_company(ticker)

    sector = (company.get("sector") or "Unknown") if company else "Unknown"
    industry = (company.get("industry") or "Unknown") if company else "Unknown"

    profile = CompanyProfile(
        sector=sector,
        industry=industry,
        market_cap=None,  # filled from quote below
        employee_count=company.get("employees") if company else None,
        country=(company.get("country") or "US") if company else "US",
    )

    # 2. Annual financials (newest-first from repo) ---------------------
    financials_raw = await market_data_repo.get_financials(ticker)
    if not financials_raw:
        # Try refreshing
        try:
            await market_data_svc.get_financials(ticker)
            financials_raw = await market_data_repo.get_financials(ticker)
        except Exception as exc:
            logger.warning("Failed to refresh financials for %s: %s", ticker, exc)

    # Filter to annual only, reverse to oldest→newest
    annual = [
        r for r in (financials_raw or [])
        if r.get("period_type", "annual") == "annual"
    ]
    annual.sort(key=lambda r: r.get("fiscal_year", 0))  # oldest→newest

    # Count years with revenue data
    revenue_years = [r for r in annual if r.get("revenue") and r["revenue"] > 0]
    years_available = len(revenue_years)

    if years_available < 3:
        raise InsufficientDataError(
            f"{ticker}: only {years_available} years of revenue data "
            f"(minimum 3 required)"
        )

    # 3. Quote data -----------------------------------------------------
    market = await market_data_repo.get_market_data(ticker)
    if not market:
        try:
            await market_data_svc.get_quote(ticker)
            market = await market_data_repo.get_market_data(ticker)
        except Exception as exc:
            logger.warning("Failed to refresh market data for %s: %s", ticker, exc)

    quote_data = QuoteData()
    if market:
        quote_data = QuoteData(
            current_price=market.get("current_price"),
            beta=market.get("beta"),
            market_cap=market.get("market_cap"),
            forward_pe=market.get("pe_forward"),
            trailing_pe=market.get("pe_trailing"),
            price_to_book=market.get("price_to_book"),
            enterprise_value=market.get("enterprise_value"),
            ev_to_ebitda=market.get("ev_to_ebitda"),
            ev_to_revenue=market.get("ev_to_revenue"),
            dividend_yield=market.get("dividend_yield"),
            payout_ratio=_derive_payout_ratio(annual),
        )
        profile.market_cap = market.get("market_cap")

    # 4. Analyst estimates (from market data if available) ---------------
    analyst = _extract_analyst_estimates(market)

    # 5. Industry benchmarks -------------------------------------------
    benchmarks = _get_benchmarks(sector, industry)

    # 6. Risk-free rate ------------------------------------------------
    risk_free = await _fetch_risk_free_rate(market_data_svc)

    return CompanyDataPackage(
        ticker=ticker,
        company_profile=profile,
        annual_financials=annual,
        years_available=years_available,
        quote_data=quote_data,
        analyst_estimates=analyst,
        industry_benchmarks=benchmarks,
        risk_free_rate=risk_free,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _derive_payout_ratio(annual: list[dict]) -> float | None:
    """Derive payout ratio from most recent financial row."""
    if not annual:
        return None
    latest = annual[-1]
    dividends_paid = latest.get("dividends_paid")
    net_income = latest.get("net_income")
    if dividends_paid is not None and net_income and net_income > 0:
        return abs(dividends_paid) / net_income
    return None


def _extract_analyst_estimates(market: dict | None) -> AnalystEstimates:
    """Extract analyst estimate fields from market data cache.

    Yahoo Finance stores some estimate data in the info dict — these get
    passed through to market_data. For MVP we pull what's available.
    """
    if not market:
        return AnalystEstimates()

    # Yahoo Finance sometimes provides these via yfinance .info dict
    # Our market_data table doesn't store estimates directly, so for now
    # return empty. Future: add estimate fields to market_data or a
    # separate table.
    return AnalystEstimates()


def _get_benchmarks(sector: str, industry: str) -> IndustryBenchmarks:
    """Look up industry/sector benchmarks, falling back to broad market."""
    # Try sector-level first
    sector_data = SECTOR_BENCHMARKS.get(sector, {})

    # Merge with broad market defaults (sector overrides broad market)
    merged = {**BROAD_MARKET_DEFAULTS, **sector_data}

    return IndustryBenchmarks(**merged)


async def _fetch_risk_free_rate(market_data_svc) -> float:
    """Fetch 10Y Treasury yield as risk-free rate.

    Uses ^TNX (CBOE 10-Year Treasury Yield Index) / 100.
    Falls back to DEFAULT_RISK_FREE_RATE.
    """
    try:
        tnx = await market_data_svc.get_quote("^TNX")
        if tnx and tnx.get("current_price"):
            rate = tnx["current_price"] / 100.0
            if 0.001 < rate < 0.20:
                return rate
    except Exception as exc:
        logger.debug("Could not fetch ^TNX for risk-free rate: %s", exc)

    return DEFAULT_RISK_FREE_RATE
