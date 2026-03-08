"""
Yahoo Finance Data Extractor

Extracts comprehensive financial data for stock valuation:
- Company information (name, sector, industry, market cap)
- Income statements (5 years historical)
- Balance sheets (5 years historical)
- Cash flow statements (5 years historical)
- Key metrics (price, PE, beta, margins, etc.)
- Dividend history
- Analyst estimates

Uses yfinance library to pull data from Yahoo Finance API.
Version 2.6: Added parallel API fetching for improved performance.

IMPORTANT: Class name is YahooFinanceExtractor (NOT YahooDataExtractor)
"""

import yfinance as yf
import pandas as pd
from typing import Dict, Any, Optional
import logging
import concurrent.futures
import time

import utils  # Import for logging and safe operations
import config
from data_cache import get_cache

logger = logging.getLogger('StockValuation')

# Configuration for parallel fetching
PARALLEL_FETCH_ENABLED = True
PARALLEL_FETCH_TIMEOUT = 15  # seconds per API call


class YahooFinanceExtractor:
    """
    Extract financial data from Yahoo Finance.
    
    CRITICAL: This is the correct class name - YahooFinanceExtractor
    (NOT YahooDataExtractor which was causing import errors)
    """
    
    def __init__(self, ticker: str):
        """
        Initialize extractor for a specific ticker.
        
        Args:
            ticker (str): Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        """
        self.ticker = ticker.upper().strip()
        if not self.ticker:
            raise ValueError(f"ticker must be a non-empty string, got: {ticker!r}")
        self.yf_ticker = None
        self.data = {}

        logger.debug(f"Initializing extractor for {self.ticker}")
    
    
    def extract_all_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Extract all available data for the ticker.

        Uses SQLite cache to avoid redundant API calls. Cached data is returned
        if it hasn't expired (5 min for price data, 24 hrs for financials).

        Args:
            force_refresh: If True, skip cache and always fetch fresh data

        Returns:
            dict: {
                'ticker': str,
                'company_info': dict,
                'key_metrics': dict,
                'income_statement': DataFrame,
                'balance_sheet': DataFrame,
                'cash_flow': DataFrame,
                'dividends': dict,
                'data_availability': dict,
                'error': str (if error occurred)
            }
        """
        try:
            start_time = time.time()

            cache_enabled = getattr(config, 'CACHE_ENABLED', True) and not force_refresh
            cache = get_cache() if cache_enabled else None

            logger.info(f"Connecting to Yahoo Finance for {self.ticker}")

            # Create yfinance Ticker object
            self.yf_ticker = yf.Ticker(self.ticker)

            # Initialize data dictionary
            self.data = {
                'ticker': self.ticker,
                'company_info': {},
                'key_metrics': {},
                'income_statement': pd.DataFrame(),
                'balance_sheet': pd.DataFrame(),
                'cash_flow': pd.DataFrame(),
                'dividends': {},
                'data_availability': {}
            }

            # Parallel fetch: Get all API data concurrently
            logger.info(f"Fetching data (parallel mode) for {self.ticker}")
            self._extract_all_parallel(cache)

            logger.debug(f"Checking data availability for {self.ticker}")
            self._check_data_availability()

            elapsed = time.time() - start_time
            logger.info(f"Data extraction complete for {self.ticker} ({elapsed:.2f}s)")

            return self.data

        except Exception as e:
            error_msg = f"Failed to extract data for {self.ticker}: {str(e)}"
            logger.error(error_msg)

            return {
                'ticker': self.ticker,
                'error': str(e),
                'company_info': {},
                'key_metrics': {},
                'income_statement': pd.DataFrame(),
                'balance_sheet': pd.DataFrame(),
                'cash_flow': pd.DataFrame(),
                'dividends': {},
                'data_availability': {}
            }

    def _extract_all_parallel(self, cache=None):
        """
        Fetch all API data in parallel using ThreadPoolExecutor.
        Uses cache to skip API calls for data types that are already cached.

        Args:
            cache: DataCache instance, or None to skip caching
        """
        # Check cache for each data type
        cached_info = cache.get(self.ticker, 'info') if cache else None
        cached_financials = cache.get(self.ticker, 'financials') if cache else None
        cached_balance = cache.get(self.ticker, 'balance_sheet') if cache else None
        cached_cashflow = cache.get(self.ticker, 'cashflow') if cache else None
        cached_dividends = cache.get(self.ticker, 'dividends') if cache else None

        cache_hits = sum(1 for x in [cached_info, cached_financials, cached_balance,
                                      cached_cashflow, cached_dividends] if x is not None)
        if cache_hits > 0:
            logger.info(f"{cache_hits}/5 data types served from cache for {self.ticker}")

        # Define fetch functions (only for non-cached data)
        def fetch_info():
            return self.yf_ticker.info

        def fetch_financials():
            return self.yf_ticker.financials

        def fetch_balance_sheet():
            return self.yf_ticker.balance_sheet

        def fetch_cashflow():
            return self.yf_ticker.cashflow

        def fetch_dividends():
            return self.yf_ticker.dividends

        # Submit only missing fetches in parallel
        futures = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            if cached_info is None:
                futures['info'] = executor.submit(fetch_info)
            if cached_financials is None:
                futures['financials'] = executor.submit(fetch_financials)
            if cached_balance is None:
                futures['balance_sheet'] = executor.submit(fetch_balance_sheet)
            if cached_cashflow is None:
                futures['cashflow'] = executor.submit(fetch_cashflow)
            if cached_dividends is None:
                futures['dividends'] = executor.submit(fetch_dividends)

            # Collect results
            info = cached_info if cached_info is not None else \
                self._safe_future_result(futures.get('info'), {}, "info") if 'info' in futures else {}
            financials = cached_financials if cached_financials is not None else \
                self._safe_future_result(futures.get('financials'), pd.DataFrame(), "financials") if 'financials' in futures else pd.DataFrame()
            balance_sheet = cached_balance if cached_balance is not None else \
                self._safe_future_result(futures.get('balance_sheet'), pd.DataFrame(), "balance_sheet") if 'balance_sheet' in futures else pd.DataFrame()
            cash_flow = cached_cashflow if cached_cashflow is not None else \
                self._safe_future_result(futures.get('cashflow'), pd.DataFrame(), "cashflow") if 'cashflow' in futures else pd.DataFrame()
            dividends_series = cached_dividends if cached_dividends is not None else \
                self._safe_future_result(futures.get('dividends'), pd.Series(), "dividends") if 'dividends' in futures else pd.Series()

        # Store fresh API results in cache
        if cache:
            if cached_info is None and info:
                cache.put(self.ticker, 'info', info)
            if cached_financials is None and financials is not None and not financials.empty:
                cache.put(self.ticker, 'financials', financials)
            if cached_balance is None and balance_sheet is not None and not balance_sheet.empty:
                cache.put(self.ticker, 'balance_sheet', balance_sheet)
            if cached_cashflow is None and cash_flow is not None and not cash_flow.empty:
                cache.put(self.ticker, 'cashflow', cash_flow)
            if cached_dividends is None and dividends_series is not None and not dividends_series.empty:
                cache.put(self.ticker, 'dividends', dividends_series)

        # Process info into company_info and key_metrics
        if info:
            self._process_info(info)

        # Store financial statements
        if financials is not None and not financials.empty:
            self.data['income_statement'] = financials
            logger.info(f"Income statement: {len(financials.columns)} years")
        else:
            logger.warning(f"No income statement data for {self.ticker}")

        if balance_sheet is not None and not balance_sheet.empty:
            self.data['balance_sheet'] = balance_sheet
            logger.info(f"Balance sheet: {len(balance_sheet.columns)} years")
        else:
            logger.warning(f"No balance sheet data for {self.ticker}")

        if cash_flow is not None and not cash_flow.empty:
            self.data['cash_flow'] = cash_flow
            logger.info(f"Cash flow: {len(cash_flow.columns)} years")
        else:
            logger.warning(f"No cash flow data for {self.ticker}")

        # Process dividends
        self._process_dividends(dividends_series)

    def _safe_future_result(self, future, default, name: str):
        """Safely get result from a future with timeout handling."""
        try:
            return future.result(timeout=PARALLEL_FETCH_TIMEOUT)
        except concurrent.futures.TimeoutError:
            logger.warning(f"Timeout fetching {name} for {self.ticker}")
            return default
        except Exception as e:
            logger.warning(f"Error fetching {name} for {self.ticker}: {e}")
            return default

    def _process_info(self, info: dict):
        """Process info dict into company_info and key_metrics."""
        # Company info
        self.data['company_info'] = {
            'longName': info.get('longName', ''),
            'shortName': info.get('shortName', ''),
            'name': info.get('longName') or info.get('shortName', self.ticker),
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown'),
            'website': info.get('website', ''),
            'description': info.get('longBusinessSummary', ''),
            'country': info.get('country', ''),
            'city': info.get('city', ''),
            'state': info.get('state', ''),
            'employees': info.get('fullTimeEmployees', 0),
            'market_cap': info.get('marketCap', 0),
            'shares_outstanding': info.get('sharesOutstanding', 0),
            'beta': info.get('beta', 1.0),
            'currency': info.get('currency', 'USD'),
        }

        company_name = self.data['company_info']['name']
        sector = self.data['company_info']['sector']
        logger.info(f"Company: {company_name}")
        logger.info(f"Sector: {sector}")

        # Key metrics
        self.data['key_metrics'] = {
            'currentPrice': info.get('currentPrice', 0),
            'regularMarketPrice': info.get('regularMarketPrice', 0),
            'previousClose': info.get('previousClose', 0),
            'open': info.get('open', 0),
            'dayHigh': info.get('dayHigh', 0),
            'dayLow': info.get('dayLow', 0),
            'fiftyTwoWeekHigh': info.get('fiftyTwoWeekHigh', 0),
            'fiftyTwoWeekLow': info.get('fiftyTwoWeekLow', 0),
            'volume': info.get('volume', 0),
            'averageVolume': info.get('averageVolume', 0),
            'marketCap': info.get('marketCap', 0),
            'enterpriseValue': info.get('enterpriseValue', 0),
            'sharesOutstanding': info.get('sharesOutstanding', 0),
            'floatShares': info.get('floatShares', 0),
            'trailingPE': info.get('trailingPE', 0),
            'forwardPE': info.get('forwardPE', 0),
            'priceToBook': info.get('priceToBook', 0),
            'priceToSales': info.get('priceToSalesTrailing12Months', 0),
            'pegRatio': info.get('pegRatio', 0),
            'enterpriseToRevenue': info.get('enterpriseToRevenue', 0),
            'enterpriseToEbitda': info.get('enterpriseToEbitda', 0),
            'profitMargins': info.get('profitMargins', 0),
            'grossMargins': info.get('grossMargins', 0),
            'ebitdaMargins': info.get('ebitdaMargins', 0),
            'operatingMargins': info.get('operatingMargins', 0),
            'returnOnAssets': info.get('returnOnAssets', 0),
            'returnOnEquity': info.get('returnOnEquity', 0),
            'revenueGrowth': info.get('revenueGrowth', 0),
            'earningsGrowth': info.get('earningsGrowth', 0),
            'earningsQuarterlyGrowth': info.get('earningsQuarterlyGrowth', 0),
            'dividendRate': info.get('dividendRate', 0),
            'dividendYield': info.get('dividendYield', 0),
            'payoutRatio': info.get('payoutRatio', 0),
            'totalCash': info.get('totalCash', 0),
            'totalDebt': info.get('totalDebt', 0),
            'debtToEquity': info.get('debtToEquity', 0),
            'currentRatio': info.get('currentRatio', 0),
            'quickRatio': info.get('quickRatio', 0),
            'beta': info.get('beta', 1.0),
            'totalRevenue': info.get('totalRevenue', 0),
            'operatingCashflow': info.get('operatingCashflow', 0),
            'freeCashflow': info.get('freeCashflow', 0),
            'ebitda': info.get('ebitda', 0),
        }

        current_price = self.data['key_metrics'].get('currentPrice', 0)
        market_cap = self.data['key_metrics'].get('marketCap', 0)

        if current_price:
            logger.info(f"Current Price: ${current_price:.2f}")
        if market_cap:
            logger.info(f"Market Cap: ${market_cap/1e9:.2f}B")

    def _process_dividends(self, dividends):
        """Process dividend series into structured data."""
        try:
            if dividends is not None and not dividends.empty:
                annual_divs = {}

                # Get timezone from dividends index (if any) for proper comparison
                div_tz = dividends.index.tz
                now = pd.Timestamp.now(tz=div_tz) if div_tz else pd.Timestamp.now()

                for year in range(5):
                    year_start = now - pd.DateOffset(years=year+1)
                    year_end = now - pd.DateOffset(years=year)
                    year_divs = dividends[(dividends.index >= year_start) & (dividends.index < year_end)]
                    annual_divs[f'year_{year}'] = year_divs.sum() if not year_divs.empty else 0

                self.data['dividends'] = {
                    'history': dividends,
                    'annual': annual_divs,
                    'most_recent': dividends.iloc[-1] if len(dividends) > 0 else 0
                }
                total_years = sum(1 for v in annual_divs.values() if v > 0)
                logger.info(f"Dividend data: {total_years} years with payments")
            else:
                logger.warning(f"No dividend history for {self.ticker}")
                self.data['dividends'] = {'history': pd.Series(), 'annual': {}, 'most_recent': 0}
        except Exception as e:
            logger.warning(f"Error processing dividends for {self.ticker}: {e}")
            self.data['dividends'] = {'history': pd.Series(), 'annual': {}, 'most_recent': 0}
    
    
    def _check_data_availability(self):
        """Check what data is available and create availability flags."""
        availability = {
            'revenue': False,
            'fcf': False,
            'dividends': False,
            'balance_sheet': False,
            'estimates': False,
            'income_statement': False,
            'cash_flow': False
        }
        
        # Check income statement
        if not self.data['income_statement'].empty:
            availability['income_statement'] = True
            
            # Check for revenue
            if 'Total Revenue' in self.data['income_statement'].index or \
               'Operating Revenue' in self.data['income_statement'].index:
                availability['revenue'] = True
        
        # Check balance sheet
        if not self.data['balance_sheet'].empty:
            availability['balance_sheet'] = True
        
        # Check cash flow
        if not self.data['cash_flow'].empty:
            availability['cash_flow'] = True
            
            # Check for FCF
            if 'Free Cash Flow' in self.data['cash_flow'].index or \
               'Operating Cash Flow' in self.data['cash_flow'].index:
                availability['fcf'] = True
        
        # Check dividends
        if self.data['dividends'].get('most_recent', 0) > 0:
            availability['dividends'] = True
        
        # Estimates - would need separate API call (placeholder)
        availability['estimates'] = False
        
        self.data['data_availability'] = availability
        
        # Log summary
        available_items = [k for k, v in availability.items() if v]
        logger.info(f"Data availability for {self.ticker}: {len(available_items)}/7 categories — {available_items}")
    
    
    def get_current_price(self) -> float:
        """
        Get current stock price.
        
        Returns:
            float: Current price or 0 if not available
        """
        try:
            if self.yf_ticker is None:
                self.yf_ticker = yf.Ticker(self.ticker)

            info = self.yf_ticker.info
            return info.get('currentPrice', 0) or info.get('regularMarketPrice', 0)
            
        except Exception as e:
            logger.error(f"Error getting current price for {self.ticker}: {e}")
            return 0
    
    
    def get_company_name(self) -> str:
        """
        Get company name.
        
        Returns:
            str: Company name or ticker if not available
        """
        try:
            if self.yf_ticker is None:
                self.yf_ticker = yf.Ticker(self.ticker)

            info = self.yf_ticker.info
            return info.get('longName') or info.get('shortName', self.ticker)
            
        except Exception as e:
            logger.error(f"Error getting company name for {self.ticker}: {e}")
            return self.ticker


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def quick_price_check(ticker: str) -> Optional[float]:
    """
    Quick check to get current price without full data extraction.
    
    Args:
        ticker (str): Stock ticker symbol
        
    Returns:
        float: Current price or None if error
    """
    try:
        extractor = YahooFinanceExtractor(ticker)
        return extractor.get_current_price()
    except Exception as e:
        logger.error(f"Quick price check failed for {ticker}: {e}")
        return None


def validate_ticker(ticker: str) -> bool:
    """
    Validate that a ticker exists and has data.
    
    Args:
        ticker (str): Stock ticker symbol
        
    Returns:
        bool: True if valid ticker with data, False otherwise
    """
    try:
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info
        
        # Check if we got valid data
        if not info or len(info) < 10:
            return False
        
        # Check for basic required fields
        has_name = 'longName' in info or 'shortName' in info
        has_price = 'currentPrice' in info or 'regularMarketPrice' in info
        
        return has_name and has_price
        
    except Exception as e:
        logger.error(f"Ticker validation failed for {ticker}: {e}")
        return False


# ============================================================================
# MODULE METADATA
# ============================================================================

__version__ = '2.6'  # Added parallel API fetching, fixed Unicode encoding, fixed dividend timestamps
__all__ = [
    'YahooFinanceExtractor',  # CRITICAL: This is the correct class name
    'quick_price_check',
    'validate_ticker'
]