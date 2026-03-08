"""SEC EDGAR provider for filing retrieval and XBRL data.

Does NOT extend DataProvider — separate provider type for filing/XBRL data.
All HTTP calls run via asyncio.to_thread() to avoid blocking FastAPI.
Rate limit: 5 req/sec (200ms minimum between requests).
"""

import asyncio
import json
import logging
import re
import time
import threading
import urllib.request
import urllib.error
from datetime import datetime, timezone

from pydantic import BaseModel

logger = logging.getLogger("finance_app")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

USER_AGENT = "FinanceApp/1.0 (finncshannon@gmail.com)"
MIN_REQUEST_INTERVAL = 0.2  # 200ms → 5 req/sec

BASE_DATA_SEC = "https://data.sec.gov"
BASE_WWW_SEC = "https://www.sec.gov"
TICKERS_URL = f"{BASE_WWW_SEC}/files/company_tickers.json"

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class FilingIndexEntry(BaseModel):
    """One filing from the SEC EDGAR submissions index."""
    ticker: str
    cik: str
    accession_number: str
    form_type: str
    filing_date: str
    primary_doc_url: str
    description: str = ""


# ---------------------------------------------------------------------------
# Rate limiter (thread-safe, timestamp-based)
# ---------------------------------------------------------------------------


class _SECRateLimiter:
    def __init__(self, min_interval: float = MIN_REQUEST_INTERVAL):
        self._min_interval = min_interval
        self._last_request_time = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._min_interval:
                sleep_time = self._min_interval - elapsed
                time.sleep(sleep_time)
            self._last_request_time = time.monotonic()


_rate_limiter = _SECRateLimiter()

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _make_request(url: str, accept: str = "application/json") -> bytes | None:
    """Synchronous HTTP GET with rate limiting, headers, and error handling."""
    _rate_limiter.wait()

    req = urllib.request.Request(url)
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Accept-Encoding", "gzip, deflate")
    req.add_header("Accept", accept)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            # Handle gzip
            if resp.headers.get("Content-Encoding") == "gzip":
                import gzip
                data = gzip.decompress(data)
            return data
    except urllib.error.HTTPError as e:
        if e.code == 429:
            logger.warning("SEC rate limited (429). Backing off 10s and retrying.")
            time.sleep(10)
            _rate_limiter.wait()
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return resp.read()
            except Exception:
                logger.error("SEC retry failed for %s", url)
                return None
        elif e.code == 404:
            logger.debug("SEC 404: %s", url)
            return None
        else:
            logger.error("SEC HTTP %d: %s", e.code, url)
            return None
    except urllib.error.URLError as e:
        logger.error("SEC connection error: %s — %s", url, e.reason)
        return None
    except Exception as e:
        logger.error("SEC request error: %s — %s", url, e)
        return None


def _fetch_json(url: str) -> dict | None:
    data = _make_request(url, "application/json")
    if data is None:
        return None
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        logger.error("SEC JSON decode error: %s — %s", url, e)
        return None


def _fetch_text(url: str) -> str | None:
    data = _make_request(url, "text/html")
    if data is None:
        return None
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return data.decode("latin-1", errors="replace")


# ---------------------------------------------------------------------------
# SEC EDGAR Provider
# ---------------------------------------------------------------------------


class SECEdgarProvider:
    """SEC EDGAR filing retrieval and XBRL data access."""

    def __init__(self) -> None:
        self._cik_cache: dict[str, str] | None = None
        self._cik_cache_time: float = 0.0
        self._cik_cache_ttl = 7 * 86400  # 7 days

    @property
    def name(self) -> str:
        return "sec_edgar"

    # ------------------------------------------------------------------
    # CIK Lookup
    # ------------------------------------------------------------------

    async def get_cik(self, ticker: str) -> str | None:
        """Get 10-digit zero-padded CIK for a ticker."""
        ticker = ticker.upper()
        mapping = await self._get_cik_mapping()
        return mapping.get(ticker)

    async def _get_cik_mapping(self) -> dict[str, str]:
        """Fetch and cache the full ticker→CIK mapping."""
        now = time.monotonic()
        if self._cik_cache and (now - self._cik_cache_time) < self._cik_cache_ttl:
            return self._cik_cache

        def _fetch() -> dict[str, str]:
            data = _fetch_json(TICKERS_URL)
            if not data:
                return {}
            mapping: dict[str, str] = {}
            for entry in data.values():
                if isinstance(entry, dict):
                    t = entry.get("ticker", "").upper()
                    cik = str(entry.get("cik_str", "")).zfill(10)
                    if t:
                        mapping[t] = cik
            return mapping

        self._cik_cache = await asyncio.to_thread(_fetch)
        self._cik_cache_time = time.monotonic()
        logger.info("Loaded %d CIK mappings from SEC", len(self._cik_cache))
        return self._cik_cache

    # ------------------------------------------------------------------
    # Filing Index
    # ------------------------------------------------------------------

    async def get_filing_index(
        self,
        ticker: str,
        form_types: list[str] | None = None,
        limit: int = 10,
    ) -> list[FilingIndexEntry]:
        """Get list of filings from SEC EDGAR submissions index."""
        if form_types is None:
            form_types = ["10-K"]

        cik = await self.get_cik(ticker)
        if not cik:
            logger.warning("No CIK found for %s", ticker)
            return []

        def _fetch() -> list[FilingIndexEntry]:
            url = f"{BASE_DATA_SEC}/submissions/CIK{cik}.json"
            data = _fetch_json(url)
            if not data:
                return []

            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accessions = recent.get("accessionNumber", [])
            primary_docs = recent.get("primaryDocument", [])
            descriptions = recent.get("primaryDocDescription", [])

            cik_stripped = str(int(cik))
            entries: list[FilingIndexEntry] = []

            for i in range(len(forms)):
                if forms[i] not in form_types:
                    continue
                if len(entries) >= limit:
                    break

                acc = accessions[i]
                acc_clean = acc.replace("-", "")
                doc = primary_docs[i] if i < len(primary_docs) else ""
                doc_url = f"{BASE_WWW_SEC}/Archives/edgar/data/{cik_stripped}/{acc_clean}/{doc}"

                entries.append(FilingIndexEntry(
                    ticker=ticker.upper(),
                    cik=cik,
                    accession_number=acc,
                    form_type=forms[i],
                    filing_date=dates[i] if i < len(dates) else "",
                    primary_doc_url=doc_url,
                    description=descriptions[i] if i < len(descriptions) else "",
                ))

            return entries

        return await asyncio.to_thread(_fetch)

    # ------------------------------------------------------------------
    # Filing Download
    # ------------------------------------------------------------------

    async def download_filing(self, ticker: str, accession_number: str) -> str | None:
        """Download the full HTML text of a filing document."""
        cik = await self.get_cik(ticker)
        if not cik:
            return None

        # First get the filing index to find the primary document URL
        entries = await self.get_filing_index(
            ticker, form_types=["10-K", "10-Q", "8-K", "DEF 14A"], limit=50
        )
        target = None
        for entry in entries:
            if entry.accession_number == accession_number:
                target = entry
                break

        if not target:
            logger.warning("Filing %s not found for %s", accession_number, ticker)
            return None

        return await asyncio.to_thread(_fetch_text, target.primary_doc_url)

    async def download_filing_by_url(self, url: str) -> str | None:
        """Download filing directly by URL."""
        return await asyncio.to_thread(_fetch_text, url)

    # ------------------------------------------------------------------
    # 10-K Section Parser
    # ------------------------------------------------------------------

    @staticmethod
    def parse_10k_sections(html_content: str) -> dict[str, dict[str, str]]:
        """Parse a 10-K HTML document into standard sections.

        Returns: {section_key: {"title": str, "content": str}}
        """
        # Section patterns for 10-K
        section_patterns = [
            ("item1", "Item 1", r"(?:Item\s*1[\.\s]*(?:—|–|-|:)?\s*Business)", "Business"),
            ("item1a", "Item 1A", r"(?:Item\s*1A[\.\s]*(?:—|–|-|:)?\s*Risk\s*Factors)", "Risk Factors"),
            ("item1b", "Item 1B", r"(?:Item\s*1B[\.\s]*(?:—|–|-|:)?\s*Unresolved\s*Staff)", "Unresolved Staff Comments"),
            ("item2", "Item 2", r"(?:Item\s*2[\.\s]*(?:—|–|-|:)?\s*Properties)", "Properties"),
            ("item3", "Item 3", r"(?:Item\s*3[\.\s]*(?:—|–|-|:)?\s*Legal)", "Legal Proceedings"),
            ("item5", "Item 5", r"(?:Item\s*5[\.\s]*(?:—|–|-|:)?\s*Market)", "Market for Registrant's Common Equity"),
            ("item6", "Item 6", r"(?:Item\s*6[\.\s]*(?:—|–|-|:)?\s*(?:Selected|Reserved))", "Selected Financial Data"),
            ("item7", "Item 7", r"(?:Item\s*7[\.\s]*(?:—|–|-|:)?\s*Management)", "MD&A"),
            ("item7a", "Item 7A", r"(?:Item\s*7A[\.\s]*(?:—|–|-|:)?\s*Quantitative)", "Quantitative and Qualitative Disclosures"),
            ("item8", "Item 8", r"(?:Item\s*8[\.\s]*(?:—|–|-|:)?\s*Financial\s*Statements)", "Financial Statements"),
        ]

        # Strip HTML tags for text extraction
        def strip_html(html: str) -> str:
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()

        sections: dict[str, dict[str, str]] = {}

        # Find all section boundaries
        boundaries: list[tuple[str, str, int]] = []
        for key, _label, pattern, title in section_patterns:
            matches = list(re.finditer(pattern, html_content, re.IGNORECASE))
            if matches:
                boundaries.append((key, title, matches[0].start()))

        # Sort by position in document
        boundaries.sort(key=lambda x: x[2])

        # Extract text between boundaries
        for i, (key, title, start) in enumerate(boundaries):
            end = boundaries[i + 1][2] if i + 1 < len(boundaries) else len(html_content)
            raw_html = html_content[start:end]
            content = strip_html(raw_html)

            # Truncate very long sections (>200KB of text)
            if len(content) > 200_000:
                content = content[:200_000] + "\n[Section truncated]"

            sections[key] = {"title": title, "content": content}

        return sections

    # ------------------------------------------------------------------
    # XBRL Company Facts
    # ------------------------------------------------------------------

    async def get_company_facts(self, ticker: str) -> dict | None:
        """Fetch XBRL company facts from SEC (structured financial data)."""
        cik = await self.get_cik(ticker)
        if not cik:
            return None

        url = f"{BASE_DATA_SEC}/api/xbrl/companyfacts/CIK{cik}.json"

        def _fetch() -> dict | None:
            return _fetch_json(url)

        return await asyncio.to_thread(_fetch)

    # ------------------------------------------------------------------
    # Helper: find latest filing
    # ------------------------------------------------------------------

    async def find_latest_filing(
        self, ticker: str, form_type: str = "10-K"
    ) -> FilingIndexEntry | None:
        """Convenience: get the most recent filing of a given type."""
        entries = await self.get_filing_index(ticker, [form_type], limit=1)
        return entries[0] if entries else None
