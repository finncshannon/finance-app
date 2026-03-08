"""
Yahoo Finance Metrics Module for Screening Tool

Fetches financial metrics from Yahoo Finance for screening/filtering:
- Valuation: P/E, P/B, P/S, EV/EBITDA, EV/Revenue, PEG
- Profitability: gross margin, operating margin, net margin, ROE, ROA
- Growth: revenue growth, earnings growth
- Financial health: debt/equity, current ratio
- Market: market cap, dividend yield, beta

Uses the shared data_cache from the valuation engine to avoid
redundant API calls.

Version: 1.0
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import sys

import yfinance as yf

# Add python_scripts to path for data_cache access
_SCRIPTS_DIR = Path(__file__).parent.parent.parent / 'python_scripts'
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from data_cache import get_cache

logger = logging.getLogger(__name__)


# Metric definitions: (display_name, yahoo_info_key, format)
METRIC_DEFS = {
    # Valuation
    'pe_ratio':          ('P/E',           'trailingPE',                  'ratio'),
    'forward_pe':        ('Fwd P/E',       'forwardPE',                   'ratio'),
    'price_to_book':     ('P/B',           'priceToBook',                 'ratio'),
    'price_to_sales':    ('P/S',           'priceToSalesTrailing12Months', 'ratio'),
    'peg_ratio':         ('PEG',           'pegRatio',                    'ratio'),
    'ev_to_revenue':     ('EV/Rev',        'enterpriseToRevenue',         'ratio'),
    'ev_to_ebitda':      ('EV/EBITDA',     'enterpriseToEbitda',          'ratio'),

    # Profitability
    'gross_margin':      ('Gross Margin',  'grossMargins',                'pct'),
    'operating_margin':  ('Op Margin',     'operatingMargins',            'pct'),
    'net_margin':        ('Net Margin',    'profitMargins',               'pct'),
    'roe':               ('ROE',           'returnOnEquity',              'pct'),
    'roa':               ('ROA',           'returnOnAssets',              'pct'),

    # Growth
    'revenue_growth':    ('Rev Growth',    'revenueGrowth',               'pct'),
    'earnings_growth':   ('Earn Growth',   'earningsGrowth',              'pct'),

    # Financial health
    'debt_to_equity':    ('D/E',           'debtToEquity',                'ratio'),
    'current_ratio':     ('Current Ratio', 'currentRatio',                'ratio'),

    # Market
    'market_cap':        ('Market Cap',    'marketCap',                   'currency'),
    'dividend_yield':    ('Div Yield',     'dividendYield',               'pct'),
    'beta':              ('Beta',          'beta',                        'ratio'),
}


def fetch_metrics(ticker: str, force_refresh: bool = False) -> Dict[str, Any]:
    """
    Fetch all screening metrics for a single ticker.

    Uses cache when available (5 min TTL for info data).

    Args:
        ticker: Stock ticker symbol
        force_refresh: Skip cache if True

    Returns:
        dict with metric keys from METRIC_DEFS mapping to numeric values.
        Missing/unavailable metrics have value None.
    """
    ticker = ticker.upper().strip()
    cache = get_cache()

    # Check cache for info dict
    info = None
    if not force_refresh:
        info = cache.get(ticker, 'info')

    # Fetch from Yahoo if not cached
    if info is None:
        try:
            info = yf.Ticker(ticker).info or {}
            if info:
                cache.put(ticker, 'info', info)
        except Exception as e:
            logger.warning(f"Failed to fetch info for {ticker}: {e}")
            info = {}

    # Extract metrics
    metrics = {}
    for key, (display_name, yahoo_key, fmt) in METRIC_DEFS.items():
        val = info.get(yahoo_key)
        if val is not None and val != 0:
            try:
                metrics[key] = float(val)
            except (TypeError, ValueError):
                metrics[key] = None
        else:
            metrics[key] = None

    return metrics


def fetch_metrics_batch(tickers: List[str],
                        force_refresh: bool = False,
                        progress_callback=None) -> Dict[str, Dict[str, Any]]:
    """
    Fetch metrics for multiple tickers.

    Args:
        tickers: List of ticker symbols
        force_refresh: Skip cache if True
        progress_callback: Optional callable(current, total, ticker)

    Returns:
        dict mapping ticker -> metrics dict
    """
    results = {}
    total = len(tickers)

    for i, ticker in enumerate(tickers):
        if progress_callback:
            progress_callback(i + 1, total, ticker)
        results[ticker] = fetch_metrics(ticker, force_refresh=force_refresh)

    return results


def format_metric(value: Any, fmt: str) -> str:
    """
    Format a metric value for display.

    Args:
        value: Numeric value
        fmt: One of 'ratio', 'pct', 'currency'

    Returns:
        Formatted string
    """
    if value is None:
        return "N/A"

    try:
        val = float(value)
        if fmt == 'pct':
            return f"{val * 100:.1f}%"
        elif fmt == 'currency':
            abs_val = abs(val)
            sign = "-" if val < 0 else ""
            if abs_val >= 1e12:
                return f"{sign}${abs_val/1e12:.1f}T"
            elif abs_val >= 1e9:
                return f"{sign}${abs_val/1e9:.1f}B"
            elif abs_val >= 1e6:
                return f"{sign}${abs_val/1e6:.0f}M"
            return f"{sign}${abs_val:,.0f}"
        else:  # ratio
            return f"{val:.2f}"
    except (TypeError, ValueError):
        return "N/A"
