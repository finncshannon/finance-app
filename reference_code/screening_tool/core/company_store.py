"""
Company Store -- local cache of all parsed company data.

Manages the per-company data directory structure:
    data/filings/{TICKER}/
        metadata.json          - 10-K filing metadata (legacy)
        metadata_10k.json      - 10-K filing metadata
        metadata_10q.json      - 10-Q filing metadata
        metadata_8k.json       - 8-K filing metadata
        10k_raw.html          - Raw 10-K HTML
        10q_raw.html          - Raw 10-Q HTML
        8k_raw.html           - Raw 8-K HTML
        item1_business.txt    - Extracted 10-K Item 1 text
        item1a_risks.txt      - Extracted 10-K Item 1A text
        item7_mda.txt         - Extracted 10-K Item 7 text
        10q_item2_mda.txt     - Extracted 10-Q Item 2 (MD&A) text
        10q_item3_market_risk.txt - Extracted 10-Q Item 3 text
        8k_body.txt           - Extracted 8-K body text
    data/financials/{TICKER}.json  - XBRL financial data

Provides a unified interface for the search engine to access
cached filing text and financial data without touching the network.

Usage:
    from core.company_store import CompanyStore

    store = CompanyStore()

    # Check what's available
    tickers = store.list_companies()
    has_data = store.has_filing_data("AAPL")

    # Get data for search
    text = store.get_section_text("AAPL", "item1")
    text = store.get_section_text("AAPL", "10q_item2")
    financials = store.get_financials("AAPL")
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Default data directories
SCREENER_ROOT = Path(__file__).parent.parent
FILINGS_DIR = SCREENER_ROOT / "data" / "filings"
FINANCIALS_DIR = SCREENER_ROOT / "data" / "financials"


class CompanyStore:
    """
    Local cache manager for company filing text and financial data.

    Thread-safe for reads (file system provides isolation).
    Not thread-safe for writes (caller should serialize).
    """

    def __init__(self, filings_dir: Optional[Path] = None,
                 financials_dir: Optional[Path] = None):
        self.filings_dir = filings_dir or FILINGS_DIR
        self.financials_dir = financials_dir or FINANCIALS_DIR
        self.filings_dir.mkdir(parents=True, exist_ok=True)
        self.financials_dir.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------------
    # Company listing
    # ----------------------------------------------------------------

    def list_companies(self) -> List[str]:
        """List all tickers that have any cached data."""
        tickers = set()

        # From filings
        if self.filings_dir.exists():
            for d in self.filings_dir.iterdir():
                if d.is_dir() and (d / "metadata.json").exists():
                    tickers.add(d.name)

        # From financials
        if self.financials_dir.exists():
            for f in self.financials_dir.glob("*.json"):
                tickers.add(f.stem)

        return sorted(tickers)

    def company_count(self) -> int:
        """Get the number of companies with cached data."""
        return len(self.list_companies())

    # ----------------------------------------------------------------
    # Filing data (10-K text sections)
    # ----------------------------------------------------------------

    # Map section IDs to filenames (must stay in sync with FilingParser.SECTION_FILE_MAP)
    SECTION_FILE_MAP = {
        # 10-K
        "item1": "item1_business.txt",
        "item1a": "item1a_risks.txt",
        "item7": "item7_mda.txt",
        # 10-Q
        "10q_item2": "10q_item2_mda.txt",
        "10q_item3": "10q_item3_market_risk.txt",
        # 8-K
        "8k_body": "8k_body.txt",
    }

    # Sections per form type
    FORM_SECTIONS = {
        "10-K": ["item1", "item1a", "item7"],
        "10-Q": ["10q_item2", "10q_item3"],
        "8-K": ["8k_body"],
    }

    def has_filing_data(self, ticker: str, form_type: str = None) -> bool:
        """
        Check if a company has cached filing text.

        Args:
            ticker: Stock ticker
            form_type: If given, check only that form type. Otherwise check any.
        """
        company_dir = self.filings_dir / ticker.upper()

        if form_type:
            sections = self.FORM_SECTIONS.get(form_type, [])
            return any(
                (company_dir / self.SECTION_FILE_MAP[s]).exists()
                for s in sections if s in self.SECTION_FILE_MAP
            )

        # Check any form type
        return any(
            (company_dir / fname).exists()
            for fname in self.SECTION_FILE_MAP.values()
        )

    def get_section_text(self, ticker: str, section: str) -> str:
        """
        Get cached section text for a company.

        Args:
            ticker: Stock ticker (e.g., "AAPL")
            section: Section ID (e.g., "item1", "item1a", "item7",
                     "10q_item2", "10q_item3", "8k_body")

        Returns:
            Section text as string, or empty string if not found.
        """
        filename = self.SECTION_FILE_MAP.get(section)
        if not filename:
            return ""

        path = self.filings_dir / ticker.upper() / filename
        try:
            if path.exists():
                return path.read_text(encoding="utf-8")
        except Exception as e:
            logger.debug(f"Failed to read {path}: {e}")
        return ""

    def get_all_section_text(self, ticker: str, form_types: List[str] = None) -> Dict[str, str]:
        """
        Get all cached section texts for a company.

        Args:
            ticker: Stock ticker
            form_types: List of form types to include (default: ["10-K"])

        Returns:
            Dict mapping section_id -> text for all requested form types.
        """
        if form_types is None:
            form_types = ["10-K"]

        result = {}
        for ft in form_types:
            for section_id in self.FORM_SECTIONS.get(ft, []):
                result[section_id] = self.get_section_text(ticker, section_id)
        return result

    def get_filing_metadata(self, ticker: str, form_type: str = "10-K") -> Optional[Dict]:
        """Get filing metadata (date, CIK, accession number, etc.)."""
        company_dir = self.filings_dir / ticker.upper()

        # Try form-specific metadata first
        stem_map = {"10-K": "10k", "10-Q": "10q", "8-K": "8k"}
        stem = stem_map.get(form_type, form_type.lower().replace("-", ""))
        path = company_dir / f"metadata_{stem}.json"

        # Legacy fallback for 10-K
        if not path.exists() and form_type == "10-K":
            path = company_dir / "metadata.json"

        try:
            if path.exists():
                with open(path, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def get_filing_date(self, ticker: str, form_type: str = "10-K") -> str:
        """Get the filing date for a company's cached filing."""
        meta = self.get_filing_metadata(ticker, form_type)
        if meta:
            return meta.get("filing_date", "")
        return ""

    def get_available_form_types(self, ticker: str) -> List[str]:
        """List form types that have cached section text for a ticker."""
        available = []
        for ft in self.FORM_SECTIONS:
            if self.has_filing_data(ticker, ft):
                available.append(ft)
        return available

    # ----------------------------------------------------------------
    # Financial data (XBRL)
    # ----------------------------------------------------------------

    def has_financials(self, ticker: str) -> bool:
        """Check if a company has cached financial data."""
        path = self.financials_dir / f"{ticker.upper()}.json"
        return path.exists()

    def save_financials(self, ticker: str, financials: Dict):
        """
        Save financial data to the cache.

        Args:
            ticker: Stock ticker
            financials: Dict from XBRLParser.get_financials()
        """
        path = self.financials_dir / f"{ticker.upper()}.json"
        try:
            # Remove _raw before saving (too verbose for cache)
            save_data = {k: v for k, v in financials.items() if k != "_raw"}
            with open(path, "w") as f:
                json.dump(save_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save financials for {ticker}: {e}")

    def get_financials(self, ticker: str) -> Optional[Dict]:
        """
        Get cached financial data for a company.

        Returns:
            Financial data dict, or None if not cached.
        """
        path = self.financials_dir / f"{ticker.upper()}.json"
        try:
            if path.exists():
                with open(path, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    # ----------------------------------------------------------------
    # Combined data access (for search engine)
    # ----------------------------------------------------------------

    def get_company_data(self, ticker: str,
                         form_types: List[str] = None) -> Optional[Dict]:
        """
        Get all cached data for a company (sections + financials).

        Args:
            ticker: Stock ticker
            form_types: Form types to include (default: ["10-K"])

        Returns:
            Dict with keys:
                - ticker, filing_date, cik
                - sections: {"item1": "...", "item1a": "...", ...}
                - financials: {...} or None
                - form_types: list of available form types
            Or None if no data at all.
        """
        if form_types is None:
            form_types = ["10-K"]

        if not self.has_filing_data(ticker):
            return None

        meta = self.get_filing_metadata(ticker) or {}
        sections = self.get_all_section_text(ticker, form_types=form_types)
        financials = self.get_financials(ticker)
        available = self.get_available_form_types(ticker)

        return {
            "ticker": ticker.upper(),
            "filing_date": meta.get("filing_date", ""),
            "cik": meta.get("cik", ""),
            "sections": sections,
            "financials": financials,
            "form_types": available,
        }

    def get_companies_with_data(self) -> List[str]:
        """
        List tickers that have BOTH filing text AND financial data.
        These are the companies ready for searching.
        """
        ready = []
        for ticker in self.list_companies():
            if self.has_filing_data(ticker) and self.has_financials(ticker):
                ready.append(ticker)
        return ready

    # ----------------------------------------------------------------
    # Data management
    # ----------------------------------------------------------------

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the local cache."""
        all_tickers = self.list_companies()
        with_filings = sum(1 for t in all_tickers if self.has_filing_data(t))
        with_financials = sum(1 for t in all_tickers if self.has_financials(t))
        with_both = sum(1 for t in all_tickers
                        if self.has_filing_data(t) and self.has_financials(t))

        # Estimate disk usage
        total_size = 0
        for d in [self.filings_dir, self.financials_dir]:
            if d.exists():
                for f in d.rglob("*"):
                    if f.is_file():
                        total_size += f.stat().st_size

        return {
            "total_companies": len(all_tickers),
            "with_filings": with_filings,
            "with_financials": with_financials,
            "search_ready": with_both,
            "disk_usage_mb": round(total_size / (1024 * 1024), 1),
        }

    def clear_company(self, ticker: str):
        """Remove all cached data for a company."""
        import shutil

        # Remove filing directory
        company_dir = self.filings_dir / ticker.upper()
        if company_dir.exists():
            shutil.rmtree(company_dir, ignore_errors=True)

        # Remove financials file
        fin_path = self.financials_dir / f"{ticker.upper()}.json"
        if fin_path.exists():
            try:
                fin_path.unlink()
            except Exception:
                pass

    def clear_all(self):
        """Remove all cached data. Use with caution."""
        import shutil
        for d in [self.filings_dir, self.financials_dir]:
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
                d.mkdir(parents=True, exist_ok=True)
