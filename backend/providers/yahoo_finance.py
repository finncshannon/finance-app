"""Yahoo Finance data provider using the yfinance library.

All yfinance calls are synchronous — they're run via asyncio.to_thread()
to avoid blocking the FastAPI event loop.
"""

import asyncio
import logging
import time
import threading
from datetime import datetime, timezone

import yfinance as yf

from providers.base import (
    DataProvider,
    QuoteData,
    KeyStatistics,
    PriceBar,
    CompanyInfo,
    FinancialPeriod,
    FinancialStatements,
    SearchResult,
)
from providers.exceptions import (
    DataNotFoundError,
    ProviderConnectionError,
    ProviderTimeout,
    RateLimitError,
)

logger = logging.getLogger("finance_app")

# ---------------------------------------------------------------------------
# Rate limiter — token bucket (thread-safe)
# ---------------------------------------------------------------------------

class _RateLimiter:
    """Simple token bucket rate limiter. Max ~2000 req/hr ≈ 33 req/min."""

    def __init__(self, max_per_hour: int = 2000):
        self._max_per_hour = max_per_hour
        self._window_seconds = 3600
        self._timestamps: list[float] = []
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block until a request slot is available."""
        with self._lock:
            now = time.monotonic()
            cutoff = now - self._window_seconds
            self._timestamps = [t for t in self._timestamps if t > cutoff]

            if len(self._timestamps) >= self._max_per_hour:
                oldest = self._timestamps[0]
                wait = oldest + self._window_seconds - now
                logger.warning("Rate limit reached, waiting %.1fs", wait)
                raise RateLimitError("yahoo", retry_after=wait)

            self._timestamps.append(now)

    @property
    def remaining(self) -> int:
        with self._lock:
            now = time.monotonic()
            cutoff = now - self._window_seconds
            active = sum(1 for t in self._timestamps if t > cutoff)
            return max(0, self._max_per_hour - active)


_rate_limiter = _RateLimiter()

# ---------------------------------------------------------------------------
# Helper: safe get from yfinance info dict
# ---------------------------------------------------------------------------

def _safe(info: dict, key: str, default=None):
    """Get a value from yfinance .info, returning default for None/NaN/missing."""
    val = info.get(key, default)
    if val is None:
        return default
    if isinstance(val, float) and (val != val):  # NaN check
        return default
    return val


def _safe_float(info: dict, key: str) -> float | None:
    val = _safe(info, key)
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(info: dict, key: str) -> int | None:
    val = _safe(info, key)
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Yahoo Finance Provider
# ---------------------------------------------------------------------------


class YahooFinanceProvider(DataProvider):
    """Primary market data provider using yfinance library."""

    @property
    def name(self) -> str:
        return "yahoo"

    def _get_ticker(self, ticker: str) -> yf.Ticker:
        """Create a yfinance Ticker object with rate limiting."""
        _rate_limiter.acquire()
        return yf.Ticker(ticker.upper())

    async def get_quote(self, ticker: str) -> QuoteData:
        """Fetch current price data from Yahoo Finance."""
        try:
            info = await asyncio.to_thread(self._fetch_info, ticker)
        except RateLimitError:
            raise
        except Exception as e:
            raise ProviderConnectionError("yahoo", str(e)) from e

        price = _safe_float(info, "currentPrice") or _safe_float(info, "regularMarketPrice")
        prev_close = _safe_float(info, "previousClose") or _safe_float(info, "regularMarketPreviousClose")

        day_change = None
        day_change_pct = None
        if price is not None and prev_close is not None and prev_close != 0:
            day_change = price - prev_close
            day_change_pct = day_change / prev_close  # Normalized as part of 10C — decimal ratio convention (0.0085 = 0.85%)

        return QuoteData(
            ticker=ticker.upper(),
            current_price=price,
            previous_close=prev_close,
            day_open=_safe_float(info, "open") or _safe_float(info, "regularMarketOpen"),
            day_high=_safe_float(info, "dayHigh") or _safe_float(info, "regularMarketDayHigh"),
            day_low=_safe_float(info, "dayLow") or _safe_float(info, "regularMarketDayLow"),
            day_change=day_change,
            day_change_pct=day_change_pct,
            volume=_safe_int(info, "volume") or _safe_int(info, "regularMarketVolume"),
            average_volume=_safe_int(info, "averageVolume"),
            market_cap=_safe_float(info, "marketCap"),
            enterprise_value=_safe_float(info, "enterpriseValue"),
            fifty_two_week_high=_safe_float(info, "fiftyTwoWeekHigh"),
            fifty_two_week_low=_safe_float(info, "fiftyTwoWeekLow"),
        )

    async def get_key_statistics(self, ticker: str) -> KeyStatistics:
        """Fetch valuation ratios from Yahoo Finance."""
        try:
            info = await asyncio.to_thread(self._fetch_info, ticker)
        except RateLimitError:
            raise
        except Exception as e:
            raise ProviderConnectionError("yahoo", str(e)) from e

        return KeyStatistics(
            ticker=ticker.upper(),
            pe_trailing=_safe_float(info, "trailingPE"),
            pe_forward=_safe_float(info, "forwardPE"),
            price_to_book=_safe_float(info, "priceToBook"),
            price_to_sales=_safe_float(info, "priceToSalesTrailing12Months"),
            ev_to_revenue=_safe_float(info, "enterpriseToRevenue"),
            ev_to_ebitda=_safe_float(info, "enterpriseToEbitda"),
            dividend_yield=_safe_float(info, "dividendYield"),
            dividend_rate=_safe_float(info, "dividendRate"),
            beta=_safe_float(info, "beta"),
        )

    async def get_historical_prices(self, ticker: str, period: str = "1y") -> list[PriceBar]:
        """Fetch daily OHLCV bars."""

        def _fetch() -> list[PriceBar]:
            t = self._get_ticker(ticker)
            df = t.history(period=period, auto_adjust=True)
            if df.empty:
                raise DataNotFoundError("yahoo", ticker, "historical prices")

            bars: list[PriceBar] = []
            for idx, row in df.iterrows():
                bars.append(PriceBar(
                    date=idx.date(),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=int(row["Volume"]),
                ))
            return bars

        try:
            return await asyncio.to_thread(_fetch)
        except (DataNotFoundError, RateLimitError):
            raise
        except Exception as e:
            raise ProviderConnectionError("yahoo", str(e)) from e

    async def get_company_info(self, ticker: str) -> CompanyInfo:
        """Fetch company profile from Yahoo Finance."""
        try:
            info = await asyncio.to_thread(self._fetch_info, ticker)
        except RateLimitError:
            raise
        except Exception as e:
            raise ProviderConnectionError("yahoo", str(e)) from e

        name = _safe(info, "longName") or _safe(info, "shortName") or ticker.upper()
        quote_type = _safe(info, "quoteType", "EQUITY")
        is_etf = quote_type == "ETF"

        return CompanyInfo(
            ticker=ticker.upper(),
            company_name=name,
            sector="ETF" if is_etf else _safe(info, "sector", "Unknown"),
            industry=_safe(info, "category", _safe(info, "industry", "Unknown")) if is_etf else _safe(info, "industry", "Unknown"),
            quote_type=quote_type,
            cik=None,  # CIK comes from SEC EDGAR, not Yahoo
            exchange=_safe(info, "exchange"),
            currency=_safe(info, "currency", "USD"),
            description=_safe(info, "longBusinessSummary"),
            employees=_safe_int(info, "fullTimeEmployees"),
            country=_safe(info, "country"),
            website=_safe(info, "website"),
            fiscal_year_end=_safe(info, "fiscalYearEnd"),
        )

    async def get_financials(self, ticker: str) -> FinancialStatements:
        """Fetch multi-year financial statements from Yahoo Finance."""

        def _fetch() -> FinancialStatements:
            t = self._get_ticker(ticker)
            info = t.info or {}

            income = t.income_stmt
            balance = t.balance_sheet
            cashflow = t.cashflow

            if income is None or income.empty:
                raise DataNotFoundError("yahoo", ticker, "financial statements")

            periods: list[FinancialPeriod] = []
            prev_revenue: float | None = None

            # Columns are datetime objects (one per fiscal year), sorted newest first
            years = sorted(income.columns, reverse=True)

            for col in years:
                fiscal_year = col.year

                def get_is(field: str) -> float | None:
                    if field in income.index:
                        val = income.at[field, col]
                        if val is not None and val == val:  # NaN check
                            return float(val)
                    return None

                def get_bs(field: str) -> float | None:
                    if balance is not None and not balance.empty and col in balance.columns and field in balance.index:
                        val = balance.at[field, col]
                        if val is not None and val == val:
                            return float(val)
                    return None

                def get_cf(field: str) -> float | None:
                    if cashflow is not None and not cashflow.empty and col in cashflow.columns and field in cashflow.index:
                        val = cashflow.at[field, col]
                        if val is not None and val == val:
                            return float(val)
                    return None

                revenue = get_is("Total Revenue") or get_is("TotalRevenue")
                cost_rev = get_is("Cost Of Revenue") or get_is("CostOfRevenue")
                gross = get_is("Gross Profit") or get_is("GrossProfit")
                op_exp = get_is("Total Operating Expenses") or get_is("TotalExpenses") or get_is("OperatingExpense")
                rd = get_is("Research And Development") or get_is("ResearchAndDevelopment") or get_is("Research Development")
                sga = get_is("Selling General And Administration") or get_is("SellingGeneralAndAdministration")
                ebit_val = get_is("EBIT")
                interest = get_is("Interest Expense") or get_is("InterestExpense")
                tax = get_is("Tax Provision") or get_is("TaxProvision") or get_is("Income Tax Expense")
                net_inc = get_is("Net Income") or get_is("NetIncome")
                ebitda_val = get_is("EBITDA") or get_is("Normalized EBITDA")
                dep_amort = get_is("Depreciation And Amortization") or get_is("Reconciled Depreciation") or get_is("DepreciationAndAmortization")
                eps_basic = get_is("Basic EPS") or get_is("BasicEPS")
                eps_dil = get_is("Diluted EPS") or get_is("DilutedEPS")

                total_assets = get_bs("Total Assets") or get_bs("TotalAssets")
                current_assets = get_bs("Current Assets") or get_bs("CurrentAssets")
                cash = get_bs("Cash And Cash Equivalents") or get_bs("CashAndCashEquivalents") or get_bs("Cash Cash Equivalents And Short Term Investments")
                total_liab = get_bs("Total Liabilities Net Minority Interest") or get_bs("TotalLiabilitiesNetMinorityInterest") or get_bs("Total Liab")
                current_liab = get_bs("Current Liabilities") or get_bs("CurrentLiabilities")
                lt_debt = get_bs("Long Term Debt") or get_bs("LongTermDebt")
                st_debt = get_bs("Current Debt") or get_bs("CurrentDebt") or get_bs("Short Long Term Debt")
                total_debt_val = get_bs("Total Debt") or get_bs("TotalDebt")
                equity = get_bs("Stockholders Equity") or get_bs("StockholdersEquity") or get_bs("Total Stockholder Equity")
                shares = get_bs("Ordinary Shares Number") or get_bs("Share Issued")

                op_cf = get_cf("Operating Cash Flow") or get_cf("Total Cash From Operating Activities")
                capex = get_cf("Capital Expenditure") or get_cf("CapitalExpenditure")
                fcf = get_cf("Free Cash Flow") or get_cf("FreeCashFlow")
                divs_paid = get_cf("Common Stock Dividend Paid") or get_cf("Cash Dividends Paid")
                cwc = get_cf("Change In Working Capital") or get_cf("ChangeInWorkingCapital")
                inv_cf = get_cf("Investing Cash Flow") or get_cf("Cash Flow From Continuing Investing Activities")
                fin_cf = get_cf("Financing Cash Flow") or get_cf("Cash Flow From Continuing Financing Activities")

                # Derive computed metrics
                working_cap = None
                if current_assets is not None and current_liab is not None:
                    working_cap = current_assets - current_liab

                net_debt_val = None
                if total_debt_val is not None and cash is not None:
                    net_debt_val = total_debt_val - cash

                if fcf is None and op_cf is not None and capex is not None:
                    fcf = op_cf + capex  # capex is typically negative

                gross_margin = None
                if gross is not None and revenue and revenue != 0:
                    gross_margin = gross / revenue

                op_margin = None
                if ebit_val is not None and revenue and revenue != 0:
                    op_margin = ebit_val / revenue

                net_margin = None
                if net_inc is not None and revenue and revenue != 0:
                    net_margin = net_inc / revenue

                fcf_margin = None
                if fcf is not None and revenue and revenue != 0:
                    fcf_margin = fcf / revenue

                ebitda_margin = None
                if ebitda_val is not None and revenue and revenue != 0:
                    ebitda_margin = ebitda_val / revenue

                rev_growth = None
                if prev_revenue is not None and revenue is not None and prev_revenue != 0:
                    rev_growth = (revenue - prev_revenue) / abs(prev_revenue)

                roe_val = None
                if net_inc is not None and equity and equity != 0:
                    roe_val = net_inc / equity

                d_to_e = None
                if total_debt_val is not None and equity and equity != 0:
                    d_to_e = total_debt_val / equity

                payout = None
                if divs_paid is not None and net_inc and net_inc != 0:
                    payout = abs(divs_paid) / abs(net_inc)

                period = FinancialPeriod(
                    ticker=ticker.upper(),
                    fiscal_year=fiscal_year,
                    period_type="annual",
                    statement_date=col.strftime("%Y-%m-%d"),
                    revenue=revenue,
                    cost_of_revenue=cost_rev,
                    gross_profit=gross,
                    operating_expense=op_exp,
                    rd_expense=rd,
                    sga_expense=sga,
                    ebit=ebit_val,
                    interest_expense=interest,
                    tax_provision=tax,
                    net_income=net_inc,
                    ebitda=ebitda_val,
                    depreciation_amortization=dep_amort,
                    eps_basic=eps_basic,
                    eps_diluted=eps_dil,
                    total_assets=total_assets,
                    current_assets=current_assets,
                    cash_and_equivalents=cash,
                    total_liabilities=total_liab,
                    current_liabilities=current_liab,
                    long_term_debt=lt_debt,
                    short_term_debt=st_debt,
                    total_debt=total_debt_val,
                    stockholders_equity=equity,
                    working_capital=working_cap,
                    net_debt=net_debt_val,
                    operating_cash_flow=op_cf,
                    capital_expenditure=capex,
                    free_cash_flow=fcf,
                    dividends_paid=divs_paid,
                    change_in_working_capital=cwc,
                    investing_cash_flow=inv_cf,
                    financing_cash_flow=fin_cf,
                    shares_outstanding=shares,
                    market_cap_at_period=_safe_float(info, "marketCap"),
                    beta_at_period=_safe_float(info, "beta"),
                    dividend_per_share=_safe_float(info, "dividendRate"),
                    gross_margin=gross_margin,
                    operating_margin=op_margin,
                    net_margin=net_margin,
                    fcf_margin=fcf_margin,
                    revenue_growth=rev_growth,
                    ebitda_margin=ebitda_margin,
                    roe=roe_val,
                    debt_to_equity=d_to_e,
                    payout_ratio=payout,
                    data_source="yahoo_finance",
                )
                periods.append(period)
                prev_revenue = revenue

            return FinancialStatements(ticker=ticker.upper(), periods=periods)

        try:
            return await asyncio.to_thread(_fetch)
        except (DataNotFoundError, RateLimitError):
            raise
        except Exception as e:
            raise ProviderConnectionError("yahoo", str(e)) from e

    async def search_companies(self, query: str) -> list[SearchResult]:
        """Search for companies by ticker or name using yfinance."""

        def _search() -> list[SearchResult]:
            _rate_limiter.acquire()
            # yfinance doesn't have a great search API; use the search module
            try:
                results_raw = yf.Search(query)
                quotes = getattr(results_raw, "quotes", []) or []
            except Exception:
                # Fallback: try as a direct ticker
                quotes = []

            results: list[SearchResult] = []
            for q in quotes:
                if isinstance(q, dict):
                    sym = q.get("symbol", "")
                    name = q.get("longname") or q.get("shortname") or sym
                    results.append(SearchResult(
                        ticker=sym,
                        company_name=name,
                        exchange=q.get("exchange"),
                        type=q.get("quoteType"),
                    ))
            return results

        try:
            return await asyncio.to_thread(_search)
        except RateLimitError:
            raise
        except Exception as e:
            raise ProviderConnectionError("yahoo", str(e)) from e

    # --- Internal helpers ---

    def _fetch_info(self, ticker: str) -> dict:
        """Synchronous helper: get .info dict with rate limiting."""
        t = self._get_ticker(ticker)
        info = t.info
        if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
            # Check if any meaningful data came back
            if not info or len(info) < 5:
                raise DataNotFoundError("yahoo", ticker, "quote data")
        return info
