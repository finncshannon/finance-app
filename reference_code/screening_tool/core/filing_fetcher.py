"""
Filing Fetcher — downloads SEC filing documents from EDGAR.

Supports:
  - 10-K (annual reports)
  - 10-Q (quarterly reports)
  - 8-K (current reports / material events)

Handles:
  - Finding the correct filing document (not the index page)
  - Downloading the full HTML
  - Managing per-company filing metadata
  - Staleness detection (only re-download when a newer filing exists)

Usage:
    from core.sec_client import SECClient
    from core.filing_fetcher import FilingFetcher

    client = SECClient(contact_email="you@email.com")
    fetcher = FilingFetcher(client)

    # Download latest 10-K for a company
    result = fetcher.fetch_latest_10k("AAPL", cik="0000320193")

    # Download latest 10-Q
    result = fetcher.fetch_filing("AAPL", cik="0000320193", form_type="10-Q")
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, List

from core.sec_client import SECClient

logger = logging.getLogger(__name__)

# Default data directory
DATA_DIR = Path(__file__).parent.parent / "data" / "filings"


class FilingFetcher:
    """
    Downloads SEC filings (10-K, 10-Q, 8-K) from EDGAR.

    Manages per-company metadata to avoid re-downloading filings
    that haven't changed since the last fetch.
    """

    # Map form types to filename stems for local storage
    FORM_FILE_STEMS = {
        "10-K": "10k",
        "10-Q": "10q",
        "8-K": "8k",
    }

    def __init__(self, client: SECClient, data_dir: Optional[Path] = None):
        """
        Args:
            client: SEC EDGAR API client
            data_dir: Directory for storing fetched filings. Default: data/filings/
        """
        self.client = client
        self.data_dir = data_dir or DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def fetch_latest_10k(self, ticker: str, cik: str,
                          force: bool = False) -> Optional[Dict]:
        """
        Fetch the latest 10-K filing for a company.

        Args:
            ticker: Stock ticker (e.g., "AAPL")
            cik: SEC CIK number (10-digit, zero-padded)
            force: Force re-download even if cached

        Returns:
            Dict with keys:
                - ticker: str
                - cik: str
                - filing_date: str (YYYY-MM-DD)
                - report_date: str (YYYY-MM-DD)
                - accession_number: str
                - primary_document: str
                - html: str (full 10-K HTML content)
            Or None if filing not found or download failed.
        """
        cik = cik.zfill(10)
        company_dir = self.data_dir / ticker.upper()

        # Check if we already have this filing cached (on disk, not SEC cache)
        if not force:
            cached = self._load_cached_filing(ticker)
            if cached is not None:
                # Check staleness — is there a newer 10-K on SEC?
                latest_date = self.client.get_latest_filing_date(cik, "10-K")
                if latest_date and cached.get("filing_date") == latest_date:
                    logger.debug(f"{ticker}: Using cached 10-K from {latest_date}")
                    return cached

        # Find the latest 10-K filing metadata
        filing_info = self.client.find_latest_10k(cik)
        if not filing_info:
            logger.warning(f"{ticker}: No 10-K filing found")
            return None

        accession = filing_info.get("accessionNumber")
        primary_doc = filing_info.get("primaryDocument")
        filing_date = filing_info.get("filingDate", "")
        report_date = filing_info.get("reportDate", "")

        if not accession or not primary_doc:
            logger.warning(f"{ticker}: 10-K filing missing accession or primary document")
            return None

        # Download the actual 10-K document
        print(f"  Downloading 10-K for {ticker} (filed {filing_date})...")
        html = self.client.download_filing_document(cik, accession, primary_doc)

        if not html:
            # Try alternate: sometimes the primary doc is wrong, check the index
            html = self._try_alternate_document(cik, accession, ticker)

        if not html:
            logger.warning(f"{ticker}: Failed to download 10-K document")
            return None

        result = {
            "ticker": ticker.upper(),
            "cik": cik,
            "filing_date": filing_date,
            "report_date": report_date,
            "accession_number": accession,
            "primary_document": primary_doc,
            "html": html,
        }

        # Save to disk for local caching
        self._save_filing(ticker, result)

        return result

    def fetch_filing(self, ticker: str, cik: str, form_type: str = "10-K",
                     force: bool = False) -> Optional[Dict]:
        """
        Fetch the latest filing of any supported type.

        Args:
            ticker: Stock ticker (e.g., "AAPL")
            cik: SEC CIK number (10-digit, zero-padded)
            form_type: SEC form type: "10-K", "10-Q", or "8-K"
            force: Force re-download even if cached

        Returns:
            Dict with keys:
                - ticker, cik, form_type, filing_date, report_date
                - accession_number, primary_document
                - html: str (full filing HTML content)
            Or None if filing not found or download failed.
        """
        if form_type == "10-K":
            return self.fetch_latest_10k(ticker, cik, force=force)

        cik = cik.zfill(10)
        file_stem = self.FORM_FILE_STEMS.get(form_type, form_type.lower().replace("-", ""))

        # Check disk cache
        if not force:
            cached = self._load_cached_filing(ticker, form_type=form_type)
            if cached is not None:
                latest_date = self.client.get_latest_filing_date(cik, form_type)
                if latest_date and cached.get("filing_date") == latest_date:
                    logger.debug(f"{ticker}: Using cached {form_type} from {latest_date}")
                    return cached

        # Find the latest filing metadata
        filing_info = self.client.find_latest_filing(cik, form_type)
        if not filing_info:
            logger.warning(f"{ticker}: No {form_type} filing found")
            return None

        accession = filing_info.get("accessionNumber")
        primary_doc = filing_info.get("primaryDocument")
        filing_date = filing_info.get("filingDate", "")
        report_date = filing_info.get("reportDate", "")

        if not accession or not primary_doc:
            logger.warning(f"{ticker}: {form_type} filing missing accession or primary document")
            return None

        # Download the actual document
        print(f"  Downloading {form_type} for {ticker} (filed {filing_date})...")
        html = self.client.download_filing_document(cik, accession, primary_doc)

        if not html:
            html = self._try_alternate_document(cik, accession, ticker)

        if not html:
            logger.warning(f"{ticker}: Failed to download {form_type} document")
            return None

        result = {
            "ticker": ticker.upper(),
            "cik": cik,
            "form_type": form_type,
            "filing_date": filing_date,
            "report_date": report_date,
            "accession_number": accession,
            "primary_document": primary_doc,
            "html": html,
        }

        # Save to disk
        self._save_filing(ticker, result, form_type=form_type)
        return result

    def needs_refresh(self, ticker: str, cik: str) -> bool:
        """
        Check if a company's cached filing is stale.

        Args:
            ticker: Stock ticker
            cik: SEC CIK number

        Returns:
            True if we need to re-download (no cache, or newer filing exists).
        """
        cached = self._load_cached_filing(ticker)
        if cached is None:
            return True

        cik = cik.zfill(10)
        latest_date = self.client.get_latest_filing_date(cik, "10-K")
        if latest_date is None:
            return False  # Can't check, assume current

        return latest_date > cached.get("filing_date", "")

    def get_cached_filing(self, ticker: str) -> Optional[Dict]:
        """
        Get a cached filing without contacting SEC.

        Returns:
            Cached filing dict, or None if not cached.
        """
        return self._load_cached_filing(ticker)

    def list_cached_tickers(self) -> List[str]:
        """List all tickers that have cached filings (any type)."""
        tickers = []
        if self.data_dir.exists():
            for d in self.data_dir.iterdir():
                if d.is_dir():
                    # Check for any metadata file (legacy or new naming)
                    has_meta = ((d / "metadata.json").exists() or
                                any(d.glob("metadata_*.json")))
                    if has_meta:
                        tickers.append(d.name)
        return sorted(tickers)

    def get_cached_filing_types(self, ticker: str) -> List[str]:
        """List form types that are cached for a given ticker."""
        company_dir = self.data_dir / ticker.upper()
        if not company_dir.exists():
            return []

        types = []
        for form_type, stem in self.FORM_FILE_STEMS.items():
            meta_path = company_dir / f"metadata_{stem}.json"
            html_path = company_dir / f"{stem}_raw.html"
            # Legacy check for 10-K
            if form_type == "10-K":
                if (meta_path.exists() or (company_dir / "metadata.json").exists()):
                    if (html_path.exists() or (company_dir / "10k_raw.html").exists()):
                        types.append(form_type)
                        continue
            if meta_path.exists() and html_path.exists():
                types.append(form_type)
        return types

    # ----------------------------------------------------------------
    # Internal: filing storage
    # ----------------------------------------------------------------

    def _company_dir(self, ticker: str) -> Path:
        """Get the directory for a company's filing data."""
        d = self.data_dir / ticker.upper()
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _save_filing(self, ticker: str, result: Dict, form_type: str = "10-K"):
        """Save a fetched filing to disk."""
        company_dir = self._company_dir(ticker)
        file_stem = self.FORM_FILE_STEMS.get(form_type, form_type.lower().replace("-", ""))

        # Save HTML
        html_path = company_dir / f"{file_stem}_raw.html"
        try:
            html_path.write_text(result["html"], encoding="utf-8")
        except Exception as e:
            logger.error(f"{ticker}: Failed to save {form_type} HTML: {e}")

        # Save metadata (everything except the HTML)
        metadata = {k: v for k, v in result.items() if k != "html"}
        meta_path = company_dir / f"metadata_{file_stem}.json"
        try:
            with open(meta_path, "w") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            logger.error(f"{ticker}: Failed to save {form_type} metadata: {e}")

        # Backwards compatibility: also write to legacy paths for 10-K
        if form_type == "10-K":
            legacy_html = company_dir / "10k_raw.html"
            legacy_meta = company_dir / "metadata.json"
            if html_path != legacy_html:
                try:
                    legacy_html.write_text(result["html"], encoding="utf-8")
                except Exception:
                    pass
            if meta_path != legacy_meta:
                try:
                    with open(legacy_meta, "w") as f:
                        json.dump(metadata, f, indent=2)
                except Exception:
                    pass

    def _load_cached_filing(self, ticker: str, form_type: str = "10-K") -> Optional[Dict]:
        """Load a cached filing from disk."""
        company_dir = self.data_dir / ticker.upper()
        file_stem = self.FORM_FILE_STEMS.get(form_type, form_type.lower().replace("-", ""))

        meta_path = company_dir / f"metadata_{file_stem}.json"
        html_path = company_dir / f"{file_stem}_raw.html"

        # Backwards compatibility: fall back to legacy paths for 10-K
        if form_type == "10-K":
            if not meta_path.exists():
                meta_path = company_dir / "metadata.json"
            if not html_path.exists():
                html_path = company_dir / "10k_raw.html"

        if not meta_path.exists() or not html_path.exists():
            return None

        try:
            with open(meta_path, "r") as f:
                metadata = json.load(f)

            html = html_path.read_text(encoding="utf-8")
            metadata["html"] = html
            metadata.setdefault("form_type", form_type)
            return metadata

        except Exception as e:
            logger.debug(f"{ticker}: Failed to load {form_type} cache: {e}")
            return None

    def _try_alternate_document(self, cik: str, accession: str,
                                 ticker: str) -> Optional[str]:
        """
        Try to find the 10-K document from the filing index.

        Some companies use non-standard primary document names.
        We look at the filing index and try common patterns.
        """
        index = self.client.get_filing_index(cik, accession)
        if not index:
            return None

        # Look for the main document in the filing index
        items = index.get("directory", {}).get("item", [])
        if not items:
            return None

        # Prioritize .htm files that look like 10-K documents
        candidates = []
        for item in items:
            name = item.get("name", "")
            if not name:
                continue
            name_lower = name.lower()

            # Skip non-HTML files
            if not (name_lower.endswith(".htm") or name_lower.endswith(".html")):
                continue

            # Skip exhibits, graphics, etc.
            if any(skip in name_lower for skip in ["ex-", "ex1", "ex2", "ex3",
                                                     "exhibit", "graphic",
                                                     "image", "logo", "r9999"]):
                continue

            # Prefer files with the ticker name or "10-k" in them
            size = item.get("size", "0")
            try:
                size_int = int(size.replace(",", ""))
            except (ValueError, AttributeError):
                size_int = 0

            # Score the candidate
            score = size_int  # Larger files are more likely to be the main document
            if ticker.lower() in name_lower:
                score += 10000000
            if "10-k" in name_lower or "10k" in name_lower:
                score += 5000000

            candidates.append((name, score))

        if not candidates:
            return None

        # Sort by score, try the best candidate
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_name = candidates[0][0]

        logger.info(f"{ticker}: Trying alternate document: {best_name}")
        return self.client.download_filing_document(cik, accession, best_name)
