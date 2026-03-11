"""Market performance API router — index and sector performance data."""

import asyncio
import logging
from datetime import datetime, timezone

import yfinance as yf
from fastapi import APIRouter, Request

from models.response import success_response, error_response

logger = logging.getLogger("finance_app")

router = APIRouter(prefix="/api/v1/market", tags=["market"])

# --- Symbol definitions ---

INDEX_SYMBOLS = [
    ("SPY", "S&P 500"),
    ("QQQ", "NASDAQ 100"),
    ("DIA", "Dow Jones"),
    ("IWM", "Russell 2000"),
    ("MDY", "S&P MidCap 400"),
    ("^VIX", "Volatility"),
    ("^TNX", "10Y Treasury"),
]

# International country indices grouped by continent
GLOBAL_SYMBOLS: dict[str, list[tuple[str, str, str]]] = {
    # (symbol, country_name, country_code) — using native indices instead of ETFs
    "Europe": [
        ("^FTSE", "United Kingdom", "GB"),
        ("^GDAXI", "Germany", "DE"),
        ("^FCHI", "France", "FR"),
        ("FTSEMIB.MI", "Italy", "IT"),
        ("^IBEX", "Spain", "ES"),
        ("^SSMI", "Switzerland", "CH"),
        ("^OMXS30", "Sweden", "SE"),
        ("^AEX", "Netherlands", "NL"),
        ("OBX.OL", "Norway", "NO"),
        ("^OMXC25", "Denmark", "DK"),
        ("WIG20.WA", "Poland", "PL"),
        ("GD.AT", "Greece", "GR"),
        ("XU100.IS", "Turkey", "TR"),
        ("^ATX", "Austria", "AT"),
        ("^OMXH25", "Finland", "FI"),
        ("^ISEQ", "Ireland", "IE"),
        ("^BFX", "Belgium", "BE"),
        ("PSI20.LS", "Portugal", "PT"),
        ("^OMXV", "Lithuania", "LT"),
        ("^OMXR", "Latvia", "LV"),
        ("^OMXT", "Estonia", "EE"),
        ("IMOEX.ME", "Russia", "RU"),
    ],
    "Asia": [
        ("^N225", "Japan", "JP"),
        ("000001.SS", "China", "CN"),
        ("^KS11", "South Korea", "KR"),
        ("^HSI", "Hong Kong", "HK"),
        ("^TWII", "Taiwan", "TW"),
        ("^BSESN", "India", "IN"),
        ("^STI", "Singapore", "SG"),
        ("^SET.BK", "Thailand", "TH"),
        ("^JKSE", "Indonesia", "ID"),
        ("^KLSE", "Malaysia", "MY"),
        ("VNM", "Vietnam", "VN"),
        ("PSEI.PS", "Philippines", "PH"),
        ("PAK", "Pakistan", "PK"),
    ],
    "Americas": [
        ("^GSPTSE", "Canada", "CA"),
        ("^MXX", "Mexico", "MX"),
        ("^BVSP", "Brazil", "BR"),
        ("^IPSA", "Chile", "CL"),
        ("^MERV", "Argentina", "AR"),
        ("GXG", "Colombia", "CO"),
        ("EPU", "Peru", "PE"),
        ("IBC.CR", "Venezuela", "VE"),
    ],
    "Middle East & Africa": [
        ("^TA125.TA", "Israel", "IL"),
        ("^TASI.SR", "Saudi Arabia", "SA"),
        ("DFMGI.AE", "UAE", "AE"),
        ("^J203.JO", "South Africa", "ZA"),
        ("^EGX30.CA", "Egypt", "EG"),
        ("NGE", "Nigeria", "NG"),
    ],
    "Oceania": [
        ("^AXJO", "Australia", "AU"),
        ("^NZ50", "New Zealand", "NZ"),
    ],
}

SECTOR_SYMBOLS = [
    ("XLK", "Technology"),
    ("XLF", "Financials"),
    ("XLV", "Healthcare"),
    ("XLE", "Energy"),
    ("XLY", "Consumer Discretionary"),
    ("XLP", "Consumer Staples"),
    ("XLI", "Industrials"),
    ("XLB", "Materials"),
    ("XLRE", "Real Estate"),
    ("XLC", "Communications"),
    ("XLU", "Utilities"),
]

# Top 5 holdings per sector ETF (and major index ETFs).
# These change slowly — hardcoded as a reliable fallback.
ETF_TOP_HOLDINGS = {
    "XLK": [
        ("AAPL", "Apple Inc.", 20.5),
        ("MSFT", "Microsoft Corp.", 19.8),
        ("NVDA", "NVIDIA Corp.", 14.2),
        ("AVGO", "Broadcom Inc.", 5.8),
        ("CRM", "Salesforce Inc.", 3.1),
    ],
    "XLF": [
        ("BRK-B", "Berkshire Hathaway", 14.0),
        ("JPM", "JPMorgan Chase", 10.5),
        ("V", "Visa Inc.", 7.8),
        ("MA", "Mastercard Inc.", 6.5),
        ("BAC", "Bank of America", 4.2),
    ],
    "XLV": [
        ("LLY", "Eli Lilly & Co.", 11.8),
        ("UNH", "UnitedHealth Group", 9.5),
        ("JNJ", "Johnson & Johnson", 6.8),
        ("ABBV", "AbbVie Inc.", 6.2),
        ("MRK", "Merck & Co.", 5.1),
    ],
    "XLE": [
        ("XOM", "Exxon Mobil Corp.", 23.0),
        ("CVX", "Chevron Corp.", 16.5),
        ("COP", "ConocoPhillips", 7.8),
        ("EOG", "EOG Resources", 4.8),
        ("SLB", "Schlumberger Ltd.", 4.2),
    ],
    "XLY": [
        ("AMZN", "Amazon.com Inc.", 22.5),
        ("TSLA", "Tesla Inc.", 15.2),
        ("HD", "Home Depot Inc.", 8.5),
        ("MCD", "McDonald's Corp.", 4.8),
        ("LOW", "Lowe's Companies", 3.8),
    ],
    "XLP": [
        ("PG", "Procter & Gamble", 14.5),
        ("COST", "Costco Wholesale", 12.0),
        ("KO", "Coca-Cola Co.", 9.2),
        ("PEP", "PepsiCo Inc.", 8.5),
        ("WMT", "Walmart Inc.", 6.8),
    ],
    "XLI": [
        ("GE", "GE Aerospace", 8.5),
        ("CAT", "Caterpillar Inc.", 5.8),
        ("UNP", "Union Pacific", 4.5),
        ("RTX", "RTX Corp.", 4.2),
        ("HON", "Honeywell Intl.", 3.8),
    ],
    "XLB": [
        ("LIN", "Linde PLC", 17.5),
        ("SHW", "Sherwin-Williams", 8.2),
        ("FCX", "Freeport-McMoRan", 6.5),
        ("APD", "Air Products", 5.8),
        ("ECL", "Ecolab Inc.", 5.2),
    ],
    "XLRE": [
        ("PLD", "Prologis Inc.", 11.5),
        ("AMT", "American Tower", 8.8),
        ("EQIX", "Equinix Inc.", 7.5),
        ("WELL", "Welltower Inc.", 5.8),
        ("SPG", "Simon Property", 4.5),
    ],
    "XLC": [
        ("META", "Meta Platforms", 22.5),
        ("GOOGL", "Alphabet Inc.", 21.0),
        ("NFLX", "Netflix Inc.", 5.5),
        ("T", "AT&T Inc.", 4.8),
        ("CMCSA", "Comcast Corp.", 4.5),
    ],
    "XLU": [
        ("NEE", "NextEra Energy", 14.5),
        ("SO", "Southern Co.", 8.2),
        ("DUK", "Duke Energy", 7.5),
        ("CEG", "Constellation Energy", 5.8),
        ("SRE", "Sempra Energy", 4.2),
    ],
    "SPY": [
        ("AAPL", "Apple Inc.", 7.2),
        ("MSFT", "Microsoft Corp.", 6.8),
        ("NVDA", "NVIDIA Corp.", 6.2),
        ("AMZN", "Amazon.com Inc.", 3.8),
        ("META", "Meta Platforms", 2.5),
    ],
    "QQQ": [
        ("AAPL", "Apple Inc.", 8.8),
        ("MSFT", "Microsoft Corp.", 8.2),
        ("NVDA", "NVIDIA Corp.", 7.5),
        ("AMZN", "Amazon.com Inc.", 5.2),
        ("META", "Meta Platforms", 4.8),
    ],
    "DIA": [
        ("UNH", "UnitedHealth Group", 8.5),
        ("GS", "Goldman Sachs", 7.2),
        ("MSFT", "Microsoft Corp.", 6.5),
        ("HD", "Home Depot Inc.", 5.8),
        ("AMGN", "Amgen Inc.", 5.2),
    ],
    "IWM": [
        ("SMCI", "Super Micro Computer", 1.2),
        ("FTNT", "Fortinet Inc.", 0.6),
        ("DECK", "Deckers Outdoor", 0.5),
        ("FIX", "Comfort Systems USA", 0.5),
        ("EME", "EMCOR Group", 0.5),
    ],
}

# Lookback periods in trading days
LOOKBACK_TRADING_DAYS = {
    "perf_1w": 5,
    "perf_1m": 21,
    "perf_3m": 63,
    "perf_6m": 126,
    "perf_1y": 252,
}


def _market_data_svc(request: Request):
    return request.app.state.market_data_service


def _compute_performance(bars: list, current_price: float | None) -> dict:
    """Compute performance percentages from historical bars.

    bars: list of PriceBar objects sorted by date ascending.
    current_price: current price from live quote.
    Returns dict with perf_1w, perf_1m, perf_3m, perf_6m, perf_ytd, perf_1y.
    """
    result = {
        "perf_1w": None,
        "perf_1m": None,
        "perf_3m": None,
        "perf_6m": None,
        "perf_ytd": None,
        "perf_1y": None,
    }

    if not bars or current_price is None or current_price == 0:
        return result

    total_bars = len(bars)

    # Standard lookback periods
    for key, days in LOOKBACK_TRADING_DAYS.items():
        idx = total_bars - days
        if idx >= 0:
            past_close = bars[idx].close
            if past_close and past_close > 0:
                result[key] = round((current_price - past_close) / past_close * 100, 2)

    # YTD: find the first bar on or after Jan 1 of the current year
    current_year = datetime.now(timezone.utc).year
    for bar in bars:
        try:
            bar_date = datetime.fromisoformat(bar.date)
            if bar_date.year == current_year:
                ytd_close = bar.close
                if ytd_close and ytd_close > 0:
                    result["perf_ytd"] = round(
                        (current_price - ytd_close) / ytd_close * 100, 2
                    )
                break
        except (ValueError, TypeError):
            continue

    return result


async def _fetch_symbol_data(mds, symbol: str, name: str) -> dict:
    """Fetch quote and historical data for a single symbol, compute performance."""
    entry = {
        "symbol": symbol,
        "name": name,
        "current_price": None,
        "day_change": None,
        "day_change_pct": None,
        "perf_1w": None,
        "perf_1m": None,
        "perf_3m": None,
        "perf_6m": None,
        "perf_ytd": None,
        "perf_1y": None,
    }

    try:
        # Fetch quote and historical in parallel
        quote_task = mds.get_quote(symbol)
        hist_task = mds.get_historical(symbol, period="1y", interval="1d")
        quote, bars = await asyncio.gather(quote_task, hist_task)

        if quote:
            entry["current_price"] = quote.get("current_price")
            entry["day_change"] = quote.get("day_change")
            entry["day_change_pct"] = quote.get("day_change_pct")

        # Compute performance from historical bars
        perf = _compute_performance(bars, entry["current_price"])
        entry.update(perf)

    except Exception as exc:
        logger.warning("Failed to fetch data for %s: %s", symbol, exc)

    return entry


@router.get("/performance")
async def get_market_performance(request: Request):
    """Index and sector performance data with multi-period returns."""
    try:
        mds = _market_data_svc(request)

        # Build tasks for all symbols
        tasks = []
        for symbol, name in INDEX_SYMBOLS:
            tasks.append(_fetch_symbol_data(mds, symbol, name))
        for symbol, name in SECTOR_SYMBOLS:
            tasks.append(_fetch_symbol_data(mds, symbol, name))

        # Global symbols — flatten all continents
        global_flat = []
        for continent, entries in GLOBAL_SYMBOLS.items():
            for symbol, country, code in entries:
                global_flat.append((symbol, country, continent, code))
                tasks.append(_fetch_symbol_data(mds, symbol, country))

        results = await asyncio.gather(*tasks)

        # Split results back into indices, sectors, and global
        index_count = len(INDEX_SYMBOLS)
        sector_count = len(SECTOR_SYMBOLS)
        indices = list(results[:index_count])
        sectors = list(results[index_count:index_count + sector_count])

        # Build global dict grouped by continent
        global_results = list(results[index_count + sector_count:])
        global_by_continent = {}
        for i, (symbol, country, continent, code) in enumerate(global_flat):
            entry = global_results[i]
            entry["country_code"] = code
            if continent not in global_by_continent:
                global_by_continent[continent] = []
            global_by_continent[continent].append(entry)

        return success_response(data={
            "indices": indices,
            "sectors": sectors,
            "global": global_by_continent,
        })

    except Exception as exc:
        logger.error("Market performance endpoint failed: %s", exc)
        return error_response("MARKET_PERFORMANCE_ERROR", str(exc))


# --- ETF holdings helpers ---


def _fetch_yf_holdings(symbol: str) -> list[dict] | None:
    """Try to pull holdings from yfinance (synchronous).

    Returns a list of dicts with keys: ticker, name, weight_pct — or None
    if yfinance doesn't have holdings data for this symbol.
    """
    try:
        t = yf.Ticker(symbol.upper())
        # Newer yfinance versions expose funds_data.top_holdings
        funds = getattr(t, "funds_data", None)
        if funds is not None:
            top = getattr(funds, "top_holdings", None)
            if top is not None and not getattr(top, "empty", True):
                rows = []
                for idx, row in top.iterrows():
                    holding_pct = float(row.iloc[0]) * 100 if row.iloc[0] == row.iloc[0] else 0
                    rows.append({
                        "ticker": str(idx),
                        "name": str(idx),
                        "weight_pct": round(holding_pct, 2),
                    })
                if rows:
                    return rows[:10]
    except Exception:
        pass
    return None


def _fetch_holding_quote(ticker: str) -> dict:
    """Fetch a quick quote for a single holding ticker (synchronous)."""
    result = {
        "ticker": ticker,
        "name": ticker,
        "current_price": None,
        "day_change_pct": None,
    }
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        result["name"] = info.get("longName") or info.get("shortName") or ticker
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        result["current_price"] = float(price) if price is not None else None
        if price is not None and prev_close is not None and prev_close != 0:
            result["day_change_pct"] = round((float(price) - float(prev_close)) / float(prev_close) * 100, 2)
    except Exception as exc:
        logger.warning("Failed to fetch quote for holding %s: %s", ticker, exc)
    return result


@router.get("/{symbol}/holdings")
async def get_etf_holdings(symbol: str, request: Request):
    """Top holdings for an ETF with current prices and day changes."""
    symbol = symbol.upper()

    try:
        # Step 1: Try yfinance first for live holdings data
        yf_holdings = await asyncio.to_thread(_fetch_yf_holdings, symbol)

        if yf_holdings:
            holdings_list = yf_holdings
        elif symbol in ETF_TOP_HOLDINGS:
            holdings_list = [
                {"ticker": t, "name": n, "weight_pct": w}
                for t, n, w in ETF_TOP_HOLDINGS[symbol]
            ]
        else:
            return error_response(
                "HOLDINGS_NOT_FOUND",
                f"No holdings data available for {symbol}",
            )

        # Step 2: Fetch live quotes for each holding in parallel
        async def _enrich(holding: dict) -> dict:
            quote = await asyncio.to_thread(_fetch_holding_quote, holding["ticker"])
            return {
                "ticker": holding["ticker"],
                "name": quote.get("name") or holding.get("name", holding["ticker"]),
                "weight_pct": holding["weight_pct"],
                "current_price": quote.get("current_price"),
                "day_change_pct": quote.get("day_change_pct"),
            }

        enriched = await asyncio.gather(*[_enrich(h) for h in holdings_list])

        return success_response(data={
            "symbol": symbol,
            "holdings": list(enriched),
        })

    except Exception as exc:
        logger.error("ETF holdings endpoint failed for %s: %s", symbol, exc)
        return error_response("ETF_HOLDINGS_ERROR", str(exc))
