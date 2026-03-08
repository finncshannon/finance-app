"""
Universe Manager -- manages the S&P 500 (or other) ticker universe.

Fetches the current S&P 500 constituent list from Wikipedia and
cross-references with SEC CIK data for complete ticker -> CIK mapping.

Usage:
    from core.universe import UniverseManager
    from core.sec_client import SECClient

    client = SECClient(contact_email="you@email.com")
    universe = UniverseManager(client)

    companies = universe.get_sp500()
    # [{"ticker": "AAPL", "name": "Apple Inc.", "cik": "0000320193",
    #   "sector": "Information Technology", "industry": "Technology Hardware"}, ...]
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import Request, urlopen

from core.sec_client import SECClient

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "universe"

# GICS sectors for filtering
SECTORS = [
    "All",
    "Communication Services",
    "Consumer Discretionary",
    "Consumer Staples",
    "Energy",
    "Financials",
    "Health Care",
    "Industrials",
    "Information Technology",
    "Materials",
    "Real Estate",
    "Utilities",
]


class UniverseManager:
    """Manages the stock universe (S&P 500 ticker list with metadata)."""

    CACHE_FILE = DATA_DIR / "sp500.json"

    def __init__(self, client: SECClient):
        self.client = client
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def get_sp500(self, force_refresh: bool = False) -> List[Dict]:
        """
        Get the S&P 500 constituent list.

        Args:
            force_refresh: Force re-download from Wikipedia

        Returns:
            List of dicts with: ticker, name, cik, sector, industry, sub_industry
        """
        # Try cache first
        if not force_refresh:
            cached = self._load_cache()
            if cached:
                return cached

        # Fetch from Wikipedia
        print("  Fetching S&P 500 list from Wikipedia...")
        companies = self._fetch_sp500_from_wikipedia()

        if not companies:
            # Fallback to cache even if stale
            cached = self._load_cache()
            if cached:
                logger.warning("Using stale S&P 500 cache (Wikipedia fetch failed)")
                return cached
            return []

        # Enrich with CIK from SEC ticker list
        print("  Cross-referencing with SEC CIK data...")
        self._enrich_with_cik(companies)

        # Save to cache
        self._save_cache(companies)

        print(f"  S&P 500 universe: {len(companies)} companies loaded")
        return companies

    def get_sectors(self) -> List[str]:
        """Get list of available GICS sectors."""
        return list(SECTORS)

    def get_companies_by_sector(self, sector: str) -> List[Dict]:
        """Get S&P 500 companies filtered by sector."""
        companies = self.get_sp500()
        if sector == "All" or not sector:
            return companies
        return [c for c in companies if c.get("sector", "").lower() == sector.lower()]

    def get_ticker_info(self, ticker: str) -> Optional[Dict]:
        """Get info for a specific ticker from the universe."""
        companies = self.get_sp500()
        for c in companies:
            if c["ticker"].upper() == ticker.upper():
                return c
        return None

    # ----------------------------------------------------------------
    # Custom universe support
    # ----------------------------------------------------------------

    def get_custom(self, tickers: List[str]) -> List[Dict]:
        """
        Build a universe from a custom list of ticker strings.

        Enriches each ticker with CIK and company name from the SEC
        ticker database. Tickers not found in SEC are included with
        empty CIK (they'll be skipped during filing download).

        Args:
            tickers: List of ticker symbols (e.g., ["PLTR", "RKLB"])

        Returns:
            List of company dicts matching the get_sp500() structure.
        """
        if not tickers:
            return []

        sec_tickers = self.client.get_all_tickers()
        result = []
        seen = set()

        for t in tickers:
            t = t.upper().strip()
            if not t or t in seen:
                continue
            seen.add(t)

            if t in sec_tickers:
                result.append({
                    "ticker": t,
                    "name": sec_tickers[t].get("name", t),
                    "cik": sec_tickers[t].get("cik", ""),
                    "sector": "",
                    "industry": "",
                    "sub_industry": "",
                })
            else:
                # Try alternate forms (dash/dot variants)
                alt = t.replace("-", "")
                alt2 = t.replace("-", ".")
                matched = False
                for variant in [alt, alt2]:
                    if variant in sec_tickers:
                        result.append({
                            "ticker": t,
                            "name": sec_tickers[variant].get("name", t),
                            "cik": sec_tickers[variant].get("cik", ""),
                            "sector": "",
                            "industry": "",
                            "sub_industry": "",
                        })
                        matched = True
                        break
                if not matched:
                    logger.warning(f"Ticker {t} not found in SEC database")
                    result.append({
                        "ticker": t,
                        "name": t,
                        "cik": "",
                        "sector": "",
                        "industry": "",
                        "sub_industry": "",
                    })

        return result

    def get_combined(self, include_sp500: bool,
                     custom_tickers: List[str]) -> List[Dict]:
        """
        Merge S&P 500 and custom tickers, deduplicating by ticker symbol.

        Args:
            include_sp500: Whether to include S&P 500 companies
            custom_tickers: List of additional ticker strings

        Returns:
            Combined list of company dicts.
        """
        result = []
        seen = set()

        # Add S&P 500 first
        if include_sp500:
            for c in self.get_sp500():
                ticker = c["ticker"].upper()
                if ticker not in seen:
                    seen.add(ticker)
                    result.append(c)

        # Add custom tickers (skip duplicates)
        if custom_tickers:
            custom = self.get_custom(custom_tickers)
            for c in custom:
                ticker = c["ticker"].upper()
                if ticker not in seen:
                    seen.add(ticker)
                    result.append(c)

        return result

    def load_custom_from_file(self, path: Path) -> List[str]:
        """
        Read a list of tickers from a .txt or .csv file.

        Expects one ticker per line. Lines starting with # are ignored.
        Blank lines are ignored. For CSV files, takes the first column.

        Args:
            path: Path to the ticker list file

        Returns:
            List of ticker strings (uppercased, stripped).
        """
        tickers = []
        try:
            text = path.read_text(encoding="utf-8")
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # For CSV: take first column (before any comma)
                ticker = line.split(",")[0].strip().upper()
                if ticker and len(ticker) <= 10:
                    tickers.append(ticker)
        except Exception as e:
            logger.error(f"Failed to load tickers from {path}: {e}")
        return tickers

    def validate_ticker(self, ticker: str) -> Optional[Dict]:
        """
        Check if a ticker exists in the SEC database.

        Returns:
            Dict with name and cik if found, None otherwise.
        """
        ticker = ticker.upper().strip()
        sec_tickers = self.client.get_all_tickers()

        if ticker in sec_tickers:
            return {
                "ticker": ticker,
                "name": sec_tickers[ticker].get("name", ticker),
                "cik": sec_tickers[ticker].get("cik", ""),
            }

        # Try alternate forms
        for variant in [ticker.replace("-", ""), ticker.replace("-", ".")]:
            if variant in sec_tickers:
                return {
                    "ticker": ticker,
                    "name": sec_tickers[variant].get("name", ticker),
                    "cik": sec_tickers[variant].get("cik", ""),
                }

        return None

    # ----------------------------------------------------------------
    # Wikipedia scraping
    # ----------------------------------------------------------------

    def _fetch_sp500_from_wikipedia(self) -> List[Dict]:
        """
        Fetch S&P 500 list from Wikipedia.

        Parses the HTML table on the Wikipedia S&P 500 page.
        """
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {
            "User-Agent": "StockValuation-Screener/1.0 (educational)",
        }

        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=30) as response:
                html = response.read().decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to fetch S&P 500 from Wikipedia: {e}")
            return []

        return self._parse_wikipedia_table(html)

    def _parse_wikipedia_table(self, html: str) -> List[Dict]:
        """Parse the S&P 500 table from Wikipedia HTML."""
        companies = []

        # Find the first wikitable (the constituents table)
        table_match = re.search(
            r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>',
            html, re.DOTALL
        )
        if not table_match:
            logger.error("Could not find S&P 500 table on Wikipedia")
            return []

        table_html = table_match.group(1)

        # Extract rows
        rows = re.findall(r'<tr>(.*?)</tr>', table_html, re.DOTALL)

        for row in rows[1:]:  # Skip header row
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
            if len(cells) < 5:
                continue

            # Clean cell contents (strip HTML tags)
            cleaned = [re.sub(r'<[^>]+>', '', cell).strip() for cell in cells]

            ticker = cleaned[0].strip()
            name = cleaned[1].strip()
            sector = cleaned[2].strip() if len(cleaned) > 2 else ""
            sub_industry = cleaned[3].strip() if len(cleaned) > 3 else ""

            # Clean up ticker (some have notes like "BRK.B")
            ticker = ticker.replace(".", "-")  # SEC uses dashes

            if ticker and name:
                companies.append({
                    "ticker": ticker.upper(),
                    "name": name,
                    "sector": sector,
                    "industry": sub_industry,
                    "sub_industry": sub_industry,
                    "cik": "",
                })

        return companies

    # ----------------------------------------------------------------
    # CIK enrichment
    # ----------------------------------------------------------------

    def _enrich_with_cik(self, companies: List[Dict]):
        """Add CIK numbers from SEC ticker list."""
        sec_tickers = self.client.get_all_tickers()

        matched = 0
        for company in companies:
            ticker = company["ticker"]

            # Direct match
            if ticker in sec_tickers:
                company["cik"] = sec_tickers[ticker]["cik"]
                matched += 1
                continue

            # Try without dash (BRK-B -> BRKB)
            alt_ticker = ticker.replace("-", "")
            if alt_ticker in sec_tickers:
                company["cik"] = sec_tickers[alt_ticker]["cik"]
                matched += 1
                continue

            # Try with dot (BRK-B -> BRK.B)
            alt_ticker2 = ticker.replace("-", ".")
            if alt_ticker2 in sec_tickers:
                company["cik"] = sec_tickers[alt_ticker2]["cik"]
                matched += 1
                continue

            logger.debug(f"No CIK found for {ticker}")

        logger.info(f"CIK match: {matched}/{len(companies)} companies")

    # ----------------------------------------------------------------
    # Cache management
    # ----------------------------------------------------------------

    def _load_cache(self) -> Optional[List[Dict]]:
        """Load cached S&P 500 list."""
        try:
            if self.CACHE_FILE.exists():
                with open(self.CACHE_FILE, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def _save_cache(self, companies: List[Dict]):
        """Save S&P 500 list to cache."""
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(self.CACHE_FILE, "w") as f:
                json.dump(companies, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save universe cache: {e}")
