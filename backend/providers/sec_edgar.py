"""SEC EDGAR provider for filing retrieval and XBRL data.

Does NOT extend DataProvider — separate provider type for filing/XBRL data.
All HTTP calls run via asyncio.to_thread() to avoid blocking FastAPI.
Rate limit: 5 req/sec (200ms minimum between requests).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import threading
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from pydantic import BaseModel

if TYPE_CHECKING:
    from services.settings_service import SettingsService

logger = logging.getLogger("finance_app")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

APP_VERSION = "2.1.0"
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


_SEC_BLOCK_SIGNATURES = [
    b"Request Originates from an Undeclared Automated Tool",
    b"undeclared automated tool",
    b"update your user agent to include company specific information",
]


def _is_sec_blocked(data: bytes) -> bool:
    """Detect SEC's 'undeclared automated tool' block page."""
    lowered = data[:4096].lower()
    return any(sig.lower() in lowered for sig in _SEC_BLOCK_SIGNATURES)


def _make_request(url: str, user_agent: str, accept: str = "application/json") -> bytes | None:
    """Synchronous HTTP GET with rate limiting, headers, and error handling."""
    _rate_limiter.wait()

    host = urlparse(url).hostname or ""
    req = urllib.request.Request(url)
    req.add_header("User-Agent", user_agent)
    req.add_header("Accept-Encoding", "gzip, deflate")
    req.add_header("Host", host)
    req.add_header("Accept", accept)
    logger.info("SEC request: %s (UA=%s, Host=%s)", url, user_agent, host)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            # Handle gzip
            if resp.headers.get("Content-Encoding") == "gzip":
                import gzip
                data = gzip.decompress(data)
            # Detect SEC block page masquerading as a 200 response
            if _is_sec_blocked(data):
                logger.error(
                    "SEC blocked request (undeclared automated tool). "
                    "User-Agent: %s — URL: %s",
                    user_agent, url,
                )
                return None
            logger.info("SEC response OK: %d bytes from %s", len(data), url)
            return data
    except urllib.error.HTTPError as e:
        if e.code == 429:
            logger.warning("SEC rate limited (429). Backing off 12s and retrying.")
            time.sleep(12)
            _rate_limiter.wait()
            try:
                retry_req = urllib.request.Request(url)
                retry_req.add_header("User-Agent", user_agent)
                retry_req.add_header("Accept-Encoding", "gzip, deflate")
                retry_req.add_header("Host", host)
                retry_req.add_header("Accept", accept)
                with urllib.request.urlopen(retry_req, timeout=30) as resp:
                    data = resp.read()
                    if resp.headers.get("Content-Encoding") == "gzip":
                        import gzip
                        data = gzip.decompress(data)
                    if _is_sec_blocked(data):
                        logger.error("SEC still blocking after retry — URL: %s", url)
                        return None
                    return data
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


def _fetch_json(url: str, user_agent: str) -> dict | None:
    data = _make_request(url, user_agent, "application/json")
    if data is None:
        return None
    try:
        return json.loads(data)
    except json.JSONDecodeError as e:
        logger.error("SEC JSON decode error: %s — %s", url, e)
        return None


def _fetch_text(url: str, user_agent: str) -> str | None:
    data = _make_request(url, user_agent, "text/html")
    if data is None:
        return None
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return data.decode("latin-1", errors="replace")


# ---------------------------------------------------------------------------
# SEC EDGAR Provider
# ---------------------------------------------------------------------------


class SECEdgarEmailNotConfigured(Exception):
    """Raised when SEC EDGAR email is not set in settings."""
    pass


class SECEdgarProvider:
    """SEC EDGAR filing retrieval and XBRL data access."""

    def __init__(self, settings_service: SettingsService | None = None) -> None:
        self._settings_service = settings_service
        self._cik_cache: dict[str, str] | None = None
        self._cik_cache_time: float = 0.0
        self._cik_cache_ttl = 7 * 86400  # 7 days

    @property
    def name(self) -> str:
        return "sec_edgar"

    async def _get_user_agent(self) -> str:
        """Build User-Agent from current settings. Raises if email not configured.

        SEC requires format: ``CompanyName AdminContact@domain.com``
        See https://www.sec.gov/about/developer-resources
        """
        email = ""
        if self._settings_service:
            email = (await self._settings_service.get("sec_edgar_email")) or ""
        email = email.strip()
        if not email:
            logger.warning("SEC EDGAR email not configured — blocking request")
            raise SECEdgarEmailNotConfigured(
                "SEC EDGAR email required. Set it in Settings → Data Sources."
            )
        return f"Spectre {email}"

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

        ua = await self._get_user_agent()

        def _fetch() -> dict[str, str]:
            data = _fetch_json(TICKERS_URL, ua)
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

        ua = await self._get_user_agent()

        def _fetch() -> list[FilingIndexEntry]:
            url = f"{BASE_DATA_SEC}/submissions/CIK{cik}.json"
            data = _fetch_json(url, ua)
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

        ua = await self._get_user_agent()
        return await asyncio.to_thread(_fetch_text, target.primary_doc_url, ua)

    async def download_filing_by_url(self, url: str) -> str | None:
        """Download filing directly by URL."""
        ua = await self._get_user_agent()
        logger.info("download_filing_by_url: %s (UA=%s)", url, ua)
        result = await asyncio.to_thread(_fetch_text, url, ua)
        logger.info("download_filing_by_url result: %s", "None" if result is None else f"{len(result)} chars")
        return result

    # ------------------------------------------------------------------
    # 10-K Section Parser
    # ------------------------------------------------------------------

    @staticmethod
    def parse_10k_sections(html_content: str) -> dict[str, dict[str, str]]:
        """Parse a 10-K/10-Q HTML document into standard sections.

        Returns: {section_key: {"title": str, "content": str}}
        """
        # Normalize HTML entities to plain text for pattern matching.
        # Keep a mapping from normalized positions back to original HTML.
        normalized = html_content
        normalized = re.sub(r'&#160;|&nbsp;', ' ', normalized)
        normalized = re.sub(r'&#8217;|&rsquo;', "'", normalized)
        normalized = re.sub(r'&#8220;|&#8221;|&ldquo;|&rdquo;', '"', normalized)
        normalized = re.sub(r'&#8212;|&mdash;', '—', normalized)
        normalized = re.sub(r'&#8211;|&ndash;', '–', normalized)
        normalized = re.sub(r'&amp;', '&', normalized)

        # Section patterns — match both 10-K and 10-Q item numbering
        _SEP = r'[\.\s]*(?:—|–|-|:)?\s*'
        section_patterns = [
            ("item1", "Item 1", rf"(?:Item{_SEP}1{_SEP}(?:Business|Financial\s*Statements))", "Business / Financial Statements"),
            ("item1a", "Item 1A", rf"(?:Item{_SEP}1A{_SEP}Risk\s*Factors?)", "Risk Factors"),
            ("item1b", "Item 1B", rf"(?:Item{_SEP}1B{_SEP}Unresolved\s*Staff)", "Unresolved Staff Comments"),
            ("item2", "Item 2", rf"(?:Item{_SEP}2{_SEP}(?:Properties|Management))", "Properties / MD&A"),
            ("item3", "Item 3", rf"(?:Item{_SEP}3{_SEP}(?:Legal|Quantitative))", "Legal Proceedings / Quantitative Disclosures"),
            ("item4", "Item 4", rf"(?:Item{_SEP}4{_SEP}(?:Mine|Controls))", "Controls and Procedures"),
            ("item5", "Item 5", rf"(?:Item{_SEP}5{_SEP}Market)", "Market for Registrant's Common Equity"),
            ("item6", "Item 6", rf"(?:Item{_SEP}6{_SEP}(?:Selected|Reserved))", "Selected Financial Data"),
            ("item7", "Item 7", rf"(?:Item{_SEP}7{_SEP}Management)", "MD&A"),
            ("item7a", "Item 7A", rf"(?:Item{_SEP}7A{_SEP}Quantitative)", "Quantitative and Qualitative Disclosures"),
            ("item8", "Item 8", rf"(?:Item{_SEP}8{_SEP}Financial\s*Statements)", "Financial Statements"),
        ]

        # Strip HTML tags for text extraction
        def strip_html(html: str) -> str:
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'&[a-zA-Z]+;|&#\d+;', ' ', text)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()

        sections: dict[str, dict[str, str]] = {}

        # Find all section boundaries in the normalized HTML
        boundaries: list[tuple[str, str, int]] = []
        for key, _label, pattern, title in section_patterns:
            matches = list(re.finditer(pattern, normalized, re.IGNORECASE))
            if matches:
                boundaries.append((key, title, matches[0].start()))

        # Sort by position in document
        boundaries.sort(key=lambda x: x[2])

        # Extract text between boundaries (use original HTML for content)
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

        ua = await self._get_user_agent()
        url = f"{BASE_DATA_SEC}/api/xbrl/companyfacts/CIK{cik}.json"

        def _fetch() -> dict | None:
            return _fetch_json(url, ua)

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
