"""
SEC EDGAR API Client — rate-limited, cached, production-grade.

Handles all communication with SEC EDGAR:
  - Company tickers lookup (CIK mapping)
  - Company submissions (filing history)
  - 10-K document download
  - XBRL company facts (structured financials)

SEC EDGAR API rules:
  - Max 10 requests/second
  - User-Agent header REQUIRED with company/contact info
  - No API key needed (free public data)
  - All data is JSON or HTML

Reference: https://www.sec.gov/edgar/sec-api-documentation
"""

import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)


class SECClient:
    """
    Rate-limited SEC EDGAR API client with local caching.

    Usage:
        client = SECClient(contact_email="your@email.com")
        tickers = client.get_all_tickers()
        submissions = client.get_company_submissions(cik="0000320193")
        facts = client.get_company_facts(cik="0000320193")
    """

    # SEC EDGAR API endpoints
    BASE_URL = "https://data.sec.gov"
    EDGAR_URL = "https://www.sec.gov"
    EFTS_URL = "https://efts.sec.gov"

    # Rate limiting: SEC allows max 10 req/sec, we use 5 to be safe
    MIN_REQUEST_INTERVAL = 0.2  # 200ms between requests (5/sec)

    # Cache TTL (seconds)
    TICKER_CACHE_TTL = 86400 * 7     # 7 days for ticker list
    SUBMISSION_CACHE_TTL = 86400 * 1  # 1 day for submission history
    FACTS_CACHE_TTL = 86400 * 30     # 30 days for XBRL facts

    def __init__(self, contact_email: str = "", cache_dir: Optional[Path] = None):
        """
        Initialize SEC client.

        Args:
            contact_email: Email for SEC User-Agent header (required by SEC)
            cache_dir: Directory for HTTP response cache. Defaults to data/_cache/
        """
        self.contact_email = contact_email
        self.user_agent = f"StockValuation-Screener/1.0 ({contact_email})"

        # Cache directory
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent / "data" / "_cache"
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Rate limiting state
        self._last_request_time = 0.0
        self._request_count = 0

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    def get_all_tickers(self) -> Dict[str, Dict]:
        """
        Get all SEC-registered company tickers with CIK mapping.

        Returns:
            Dict mapping ticker -> {"cik": str, "name": str, "ticker": str}

        Example:
            {"AAPL": {"cik": "0000320193", "name": "Apple Inc.", "ticker": "AAPL"}, ...}
        """
        url = f"{self.EDGAR_URL}/files/company_tickers.json"
        data = self._get_json(url, cache_key="company_tickers", ttl=self.TICKER_CACHE_TTL)

        # SEC returns: {"0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."}, ...}
        result = {}
        if data:
            for entry in data.values():
                ticker = entry.get("ticker", "").upper()
                cik = str(entry.get("cik_str", "")).zfill(10)
                name = entry.get("title", "")
                if ticker:
                    result[ticker] = {
                        "cik": cik,
                        "name": name,
                        "ticker": ticker,
                    }
        return result

    def get_company_submissions(self, cik: str) -> Optional[Dict]:
        """
        Get a company's filing history from SEC EDGAR.

        Args:
            cik: 10-digit CIK number (zero-padded)

        Returns:
            Full submissions JSON including recent filings, or None on error.

        The returned dict contains:
            - name, cik, sic, sicDescription, category, entityType
            - filings.recent.form, filings.recent.filingDate, etc.
        """
        cik = cik.zfill(10)
        url = f"{self.BASE_URL}/submissions/CIK{cik}.json"
        cache_key = f"submissions_{cik}"
        return self._get_json(url, cache_key=cache_key, ttl=self.SUBMISSION_CACHE_TTL)

    def get_company_facts(self, cik: str) -> Optional[Dict]:
        """
        Get XBRL company facts (structured financial data).

        Args:
            cik: 10-digit CIK number (zero-padded)

        Returns:
            Company facts JSON with all reported XBRL concepts, or None on error.

        Structure:
            facts.us-gaap.{concept}.units.{unit}[{val, end, fy, fp, form, ...}]
        """
        cik = cik.zfill(10)
        url = f"{self.BASE_URL}/api/xbrl/companyfacts/CIK{cik}.json"
        cache_key = f"facts_{cik}"
        return self._get_json(url, cache_key=cache_key, ttl=self.FACTS_CACHE_TTL)

    def download_filing_document(self, cik: str, accession_number: str,
                                  primary_document: str) -> Optional[str]:
        """
        Download a specific filing document (e.g., the 10-K HTML).

        Args:
            cik: 10-digit CIK (zero-padded)
            accession_number: Filing accession number (e.g., "0000320193-23-000106")
            primary_document: Filename of the primary doc (e.g., "aapl-20230930.htm")

        Returns:
            Document content as string, or None on error.
        """
        cik = cik.zfill(10)
        # CIK in Archives URLs is NOT zero-padded
        cik_stripped = str(int(cik))
        # Accession number in URL has no dashes
        accession_clean = accession_number.replace("-", "")
        url = f"{self.EDGAR_URL}/Archives/edgar/data/{cik_stripped}/{accession_clean}/{primary_document}"

        # Cache using a hash of the URL (filing docs can be large)
        cache_key = f"doc_{cik}_{accession_clean}_{primary_document}"
        cached = self._get_cached(cache_key, ttl=86400 * 365)  # Cache for 1 year (filings don't change)
        if cached is not None:
            return cached

        content = self._get_text(url)
        if content:
            self._save_cache(cache_key, content)
        return content

    def get_filing_index(self, cik: str, accession_number: str) -> Optional[Dict]:
        """
        Get the filing index (list of documents in a filing).

        Args:
            cik: 10-digit CIK
            accession_number: Filing accession number

        Returns:
            Filing index JSON, or None on error.
        """
        cik = cik.zfill(10)
        cik_stripped = str(int(cik))
        accession_clean = accession_number.replace("-", "")
        url = f"{self.EDGAR_URL}/Archives/edgar/data/{cik_stripped}/{accession_clean}/index.json"
        cache_key = f"index_{cik}_{accession_clean}"
        return self._get_json(url, cache_key=cache_key, ttl=86400 * 365)

    def find_latest_10k(self, cik: str) -> Optional[Dict]:
        """
        Find the latest 10-K filing for a company.

        Args:
            cik: 10-digit CIK (zero-padded)

        Returns:
            Dict with: accessionNumber, filingDate, primaryDocument, reportDate
            Or None if no 10-K found.
        """
        return self.find_latest_filing(cik, "10-K")

    def find_latest_filing(self, cik: str, form_type: str = "10-K") -> Optional[Dict]:
        """
        Find the latest filing of a given type for a company.

        Args:
            cik: 10-digit CIK (zero-padded)
            form_type: SEC form type (e.g., "10-K", "10-Q", "8-K")

        Returns:
            Dict with: accessionNumber, filingDate, primaryDocument, reportDate, formType
            Or None if not found.
        """
        submissions = self.get_company_submissions(cik)
        if not submissions:
            return None

        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        report_dates = recent.get("reportDate", [])

        # Find the most recent filing of the requested type (not amendments like 10-K/A)
        for i, form in enumerate(forms):
            if form == form_type:
                return {
                    "accessionNumber": accessions[i] if i < len(accessions) else None,
                    "filingDate": dates[i] if i < len(dates) else None,
                    "primaryDocument": primary_docs[i] if i < len(primary_docs) else None,
                    "reportDate": report_dates[i] if i < len(report_dates) else None,
                    "formType": form_type,
                }

        return None

    def find_recent_filings(self, cik: str, form_types: List[str] = None,
                            max_per_type: int = 1) -> List[Dict]:
        """
        Find recent filings of multiple types.

        Args:
            cik: 10-digit CIK (zero-padded)
            form_types: List of form types to search for (default: ["10-K"])
            max_per_type: Max filings to return per form type

        Returns:
            List of filing info dicts, sorted by filing date (newest first).
        """
        if form_types is None:
            form_types = ["10-K"]

        submissions = self.get_company_submissions(cik)
        if not submissions:
            return []

        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        report_dates = recent.get("reportDate", [])

        results = []
        type_counts = {ft: 0 for ft in form_types}

        for i, form in enumerate(forms):
            if form in type_counts and type_counts[form] < max_per_type:
                results.append({
                    "accessionNumber": accessions[i] if i < len(accessions) else None,
                    "filingDate": dates[i] if i < len(dates) else None,
                    "primaryDocument": primary_docs[i] if i < len(primary_docs) else None,
                    "reportDate": report_dates[i] if i < len(report_dates) else None,
                    "formType": form,
                })
                type_counts[form] += 1

                # Stop early if we have enough of everything
                if all(c >= max_per_type for c in type_counts.values()):
                    break

        # Sort by filing date (newest first)
        results.sort(key=lambda x: x.get("filingDate", ""), reverse=True)
        return results

    def get_latest_filing_date(self, cik: str, form_type: str = "10-K") -> Optional[str]:
        """
        Get the filing date of the most recent filing of a given type.

        Args:
            cik: 10-digit CIK
            form_type: SEC form type (default "10-K")

        Returns:
            Filing date string "YYYY-MM-DD" or None if not found.
        """
        submissions = self.get_company_submissions(cik)
        if not submissions:
            return None

        recent = submissions.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])

        for i, form in enumerate(forms):
            if form == form_type and i < len(dates):
                return dates[i]

        return None

    # ----------------------------------------------------------------
    # HTTP layer (rate-limited)
    # ----------------------------------------------------------------

    def _rate_limit(self):
        """Enforce SEC rate limiting: max 5 requests/second."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            sleep_time = self.MIN_REQUEST_INTERVAL - elapsed
            time.sleep(sleep_time)
        self._last_request_time = time.time()
        self._request_count += 1

    def _make_request(self, url: str, accept: str = "application/json") -> Optional[bytes]:
        """
        Make an HTTP GET request to SEC EDGAR with rate limiting.

        Args:
            url: Full URL to fetch
            accept: Accept header value

        Returns:
            Response body as bytes, or None on error.
        """
        self._rate_limit()

        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Accept": accept,
        }

        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=30) as response:
                data = response.read()

                # Handle gzip encoding
                if response.headers.get("Content-Encoding") == "gzip":
                    import gzip
                    data = gzip.decompress(data)

                return data

        except HTTPError as e:
            if e.code == 404:
                logger.debug(f"SEC 404: {url}")
            elif e.code == 429:
                logger.warning(f"SEC rate limited (429). Backing off...")
                time.sleep(10)  # Back off for 10 seconds
                return self._make_request(url, accept)  # Retry once
            else:
                logger.error(f"SEC HTTP error {e.code}: {url}")
            return None

        except URLError as e:
            logger.error(f"SEC URL error: {e.reason} — {url}")
            return None

        except Exception as e:
            logger.error(f"SEC request failed: {e} — {url}")
            return None

    def _get_json(self, url: str, cache_key: str = None,
                   ttl: int = 86400) -> Optional[Dict]:
        """
        Fetch JSON from SEC EDGAR with caching.

        Args:
            url: URL to fetch
            cache_key: Cache key name (auto-generated from URL if None)
            ttl: Cache time-to-live in seconds

        Returns:
            Parsed JSON dict, or None on error.
        """
        # Check cache first
        if cache_key:
            cached = self._get_cached(cache_key, ttl)
            if cached is not None:
                try:
                    return json.loads(cached)
                except json.JSONDecodeError:
                    pass  # Cache is corrupted, re-fetch

        # Fetch from SEC
        raw = self._make_request(url, accept="application/json")
        if raw is None:
            return None

        try:
            text = raw.decode("utf-8")
            data = json.loads(text)

            # Save to cache
            if cache_key:
                self._save_cache(cache_key, text)

            return data

        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error(f"Failed to parse JSON from {url}: {e}")
            return None

    def _get_text(self, url: str) -> Optional[str]:
        """
        Fetch text/HTML content from SEC EDGAR (no caching by default).

        Args:
            url: URL to fetch

        Returns:
            Response body as string, or None on error.
        """
        raw = self._make_request(url, accept="text/html")
        if raw is None:
            return None

        # Try UTF-8 first, fall back to latin-1
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return raw.decode("latin-1")
            except Exception:
                return raw.decode("utf-8", errors="replace")

    # ----------------------------------------------------------------
    # Cache layer
    # ----------------------------------------------------------------

    def _cache_path(self, key: str) -> Path:
        """Get the file path for a cache key."""
        # Hash long keys to avoid filesystem path length issues
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.json"

    def _get_cached(self, key: str, ttl: int) -> Optional[str]:
        """
        Get cached response if it exists and is not expired.

        Args:
            key: Cache key
            ttl: Max age in seconds

        Returns:
            Cached content as string, or None if cache miss/expired.
        """
        path = self._cache_path(key)
        if not path.exists():
            return None

        # Check age
        age = time.time() - path.stat().st_mtime
        if age > ttl:
            return None  # Expired

        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            return None

    def _save_cache(self, key: str, content: str):
        """Save content to cache."""
        path = self._cache_path(key)
        try:
            path.write_text(content, encoding="utf-8")
        except Exception as e:
            logger.debug(f"Failed to cache {key}: {e}")

    def clear_cache(self, pattern: str = None):
        """
        Clear cached responses.

        Args:
            pattern: If None, clears all cache. Otherwise only matching keys.
        """
        if pattern:
            # Can't reverse the hash, so clear all (rare operation anyway)
            logger.info("Clearing all SEC cache (pattern-based clear not supported with hashed keys)")

        for f in self.cache_dir.glob("*.json"):
            try:
                f.unlink()
            except Exception:
                pass

    @property
    def request_count(self) -> int:
        """Number of HTTP requests made this session."""
        return self._request_count

    def __repr__(self):
        return f"SECClient(email='{self.contact_email}', requests={self._request_count})"
