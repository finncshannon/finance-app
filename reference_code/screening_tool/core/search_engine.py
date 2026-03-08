"""
Search Engine -- keyword search across cached 10-K text with scoring.

Searches Items 1 (Business), 1A (Risk Factors), 7 (MD&A) for companies
matching user queries. Returns ranked results with match scores,
keyword frequencies, and text excerpts showing context.

Scoring weights:
  - Item 1 (Business): 3x weight -- most relevant for understanding what a company does
  - Item 7 (MD&A):     2x weight -- discusses strategy, growth, operations
  - Item 1A (Risks):   1x weight -- mentions competitors, market context

Supports:
  - Multi-keyword queries (each keyword scored independently)
  - Phrase matching (wrap in quotes: "thermal protection")
  - Sector filtering
  - Context excerpts with highlighted keywords

Usage:
    from core.search_engine import SearchEngine
    from core.company_store import CompanyStore

    store = CompanyStore()
    engine = SearchEngine(store)

    results = engine.search("hypersonic thermal protection scramjet")
    for r in results:
        print(f"{r.ticker}: {r.match_score:.0f}% -- {r.company_name}")
        for excerpt in r.matched_excerpts[:3]:
            print(f"  ...{excerpt}...")
"""

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from core.company_store import CompanyStore

logger = logging.getLogger(__name__)

# Path to external stopwords file
_STOPWORDS_PATH = Path(__file__).parent.parent / "config" / "stopwords.txt"


# Section weights for scoring
SECTION_WEIGHTS = {
    # 10-K
    "item1":  3.0,        # Business description -- most relevant
    "item7":  2.0,        # MD&A -- strategy and operations
    "item1a": 1.0,        # Risk factors -- market context
    # 10-Q
    "10q_item2": 2.0,     # MD&A (quarterly)
    "10q_item3": 1.0,     # Quantitative/Qualitative disclosures
    # 8-K
    "8k_body": 1.5,       # Material event body text
}

# Fallback stopwords (used if config/stopwords.txt is missing)
_FALLBACK_STOPWORDS = {
    "the", "in", "of", "and", "for", "with", "from", "that", "this",
    "are", "was", "has", "its", "our", "by", "at", "on", "an", "or",
    "as", "be", "do", "if", "we", "is", "it", "to", "no", "so", "up",
    "not", "but", "all", "can", "had", "her", "his", "how", "may",
    "new", "now", "old", "see", "way", "who", "did", "get", "let",
    "say", "she", "too", "use", "any", "each", "than", "them", "then",
    "such", "also", "been", "have", "into", "more", "most", "must",
    "over", "some", "very", "when", "what", "will", "with", "which",
    "were", "would", "could", "should", "about", "after", "other",
    "their", "there", "these", "those", "through", "under", "where",
    "company", "companies", "business", "operations", "products",
    "services", "market", "customers", "management", "financial",
    "results", "risk", "including", "united", "states", "fiscal",
    "year", "period", "certain", "related", "general", "following",
    "significant", "operating", "reported", "approximately",
    "primarily", "substantially", "respectively", "consolidated",
    "applicable", "additional", "various", "domestic", "foreign",
    "income", "total", "net", "assets", "liabilities", "equity",
    "shares", "stock", "common", "annual", "quarterly", "ended",
    "december", "january", "february", "march", "april", "june",
    "july", "august", "september", "october", "november",
}


def _load_stopwords() -> Set[str]:
    """Load stopwords from config/stopwords.txt, falling back to embedded set."""
    try:
        if _STOPWORDS_PATH.exists():
            words = set()
            for line in _STOPWORDS_PATH.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    words.add(line.lower())
            if words:
                logger.debug(f"Loaded {len(words)} stopwords from {_STOPWORDS_PATH}")
                return words
    except Exception as e:
        logger.warning(f"Failed to load stopwords file: {e}")
    return _FALLBACK_STOPWORDS


STOPWORDS = _load_stopwords()

# Excerpt context: chars before/after keyword
EXCERPT_CONTEXT = 150


@dataclass
class SearchResult:
    """A single search result for one company."""

    ticker: str
    company_name: str
    sector: str
    industry: str
    cik: str

    # Relevance
    match_score: float = 0.0                   # 0-100 relevance score
    keywords_matched: List[str] = field(default_factory=list)
    keyword_counts: Dict[str, int] = field(default_factory=dict)
    matched_excerpts: List[str] = field(default_factory=list)
    sections_matched: List[str] = field(default_factory=list)
    total_hits: int = 0

    # Financials (from cache)
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    fcf: Optional[float] = None
    operating_cash_flow: Optional[float] = None
    market_cap: Optional[float] = None

    # Filing info
    filing_date: str = ""

    def __repr__(self):
        return (f"SearchResult({self.ticker}, score={self.match_score:.0f}%, "
                f"hits={self.total_hits}, keywords={self.keywords_matched})")


class SearchEngine:
    """
    Keyword search engine for 10-K filing text.

    Searches all cached company data in the CompanyStore.
    No network calls -- entirely local and fast.
    """

    def __init__(self, store: CompanyStore):
        self.store = store

    def search(self, query: str, sector: str = None,
               universe: List[Dict] = None,
               max_results: int = 100,
               min_score: float = 5.0,
               form_types: List[str] = None) -> List[SearchResult]:
        """
        Search filing text for companies matching the query.

        Args:
            query: Search query (keywords separated by spaces).
                   Use quotes for exact phrases: "thermal protection"
            sector: Filter by GICS sector (e.g., "Industrials"). None = all.
            universe: List of company dicts with ticker/name/sector/cik.
                      If None, uses all companies in the store.
            max_results: Maximum number of results to return.
            min_score: Minimum match score (0-100) to include.
            form_types: Filing types to search (default: ["10-K"]).
                        Can include "10-K", "10-Q", "8-K".

        Returns:
            List of SearchResult, sorted by match_score descending.
        """
        if form_types is None:
            form_types = ["10-K"]

        if not query or not query.strip():
            return []

        # Parse query into keywords, phrases, and implicit phrases
        keywords, phrases, implicit_phrases = self._parse_query(query)
        all_terms = keywords + phrases + implicit_phrases

        if not all_terms:
            return []

        # Compute keyword rarity (once per search, not per company)
        rarity_weights = self._compute_keyword_rarity(keywords, form_types=form_types)

        # Identify core term: the rarest keyword (gate for multi-keyword queries)
        core_term = None
        if keywords:
            core_term = max(keywords, key=lambda kw: rarity_weights.get(kw, 0.5))

        # Determine which companies to search
        if universe:
            tickers_to_search = [
                (c["ticker"], c.get("name", ""), c.get("sector", ""),
                 c.get("industry", ""), c.get("cik", ""))
                for c in universe
                if (not sector or sector == "All" or
                    c.get("sector", "").lower() == sector.lower())
            ]
        else:
            # Search all companies in the store
            tickers_to_search = [
                (t, "", "", "", "")
                for t in self.store.list_companies()
            ]

        results = []

        for ticker, name, sec, ind, cik in tickers_to_search:
            if not self.store.has_filing_data(ticker):
                continue

            result = self._score_company(
                ticker, name, sec, ind, cik, keywords, phrases,
                rarity_weights, core_term, form_types=form_types,
                implicit_phrases=implicit_phrases
            )

            if result and result.match_score >= min_score:
                results.append(result)

        # Sort by score descending
        results.sort(key=lambda r: r.match_score, reverse=True)

        # Limit results
        return results[:max_results]

    def _parse_query(self, query: str) -> Tuple[List[str], List[str], List[str]]:
        """
        Parse query into individual keywords, quoted phrases, and implicit phrases.

        Implicit phrases are auto-generated from adjacent keywords. For example,
        "nuclear energy storage" generates implicit phrases:
          bigrams:  ["nuclear energy", "energy storage"]
          trigrams: ["nuclear energy storage"]

        This allows multi-word searches to reward documents where the words
        appear back-to-back without requiring the user to add quotes.

        Args:
            query: Raw query string

        Returns:
            (keywords, phrases, implicit_phrases) where:
              - keywords: individual words (lowercased)
              - phrases: quoted exact phrases (lowercased)
              - implicit_phrases: auto-generated adjacent-word phrases
        """
        # Extract quoted phrases
        phrases = re.findall(r'"([^"]+)"', query)
        phrases = [p.strip().lower() for p in phrases if p.strip()]

        # Remove quoted phrases from query, then split remaining into keywords
        remaining = re.sub(r'"[^"]*"', '', query)
        raw_words = [w.strip().lower() for w in remaining.split()
                     if w.strip() and len(w.strip()) >= 2]

        # Filter out stopwords for keywords
        keywords = [kw for kw in raw_words if kw not in STOPWORDS]

        # Generate implicit phrases from adjacent non-stopword keywords
        implicit_phrases = []
        phrases_lower_set = set(phrases)  # For dedup against explicit phrases

        if len(keywords) >= 2:
            # Bigrams: pairs of adjacent keywords
            for i in range(len(keywords) - 1):
                bigram = keywords[i] + " " + keywords[i + 1]
                if bigram not in phrases_lower_set:
                    implicit_phrases.append(bigram)

            # Trigrams: triples of adjacent keywords (if 3+ keywords)
            if len(keywords) >= 3:
                for i in range(len(keywords) - 2):
                    trigram = keywords[i] + " " + keywords[i + 1] + " " + keywords[i + 2]
                    if trigram not in phrases_lower_set:
                        implicit_phrases.append(trigram)

        return keywords, phrases, implicit_phrases

    def _compute_keyword_rarity(self, keywords: List[str],
                                form_types: List[str] = None) -> Dict[str, float]:
        """
        Compute rarity weight for each keyword based on how many cached
        companies mention it. Rare keywords get weight ~1.0, ubiquitous
        keywords get weight near 0.0.

        Scans all cached filings once per search (not per company).

        Returns:
            Dict mapping keyword -> rarity weight (0.0 to 1.0)
        """
        if not keywords:
            return {}

        all_tickers = self.store.list_companies()
        total = len(all_tickers)
        if total == 0:
            return {kw: 0.5 for kw in keywords}

        # Count how many companies contain each keyword (in any section)
        kw_company_counts = {kw: 0 for kw in keywords}

        for ticker in all_tickers:
            sections = self.store.get_all_section_text(ticker, form_types=form_types)
            combined = " ".join(
                text.lower() for text in sections.values() if text
            )
            for kw in keywords:
                # Stem-aware match: \w* allows plurals/variants
                if ' ' not in kw:
                    if re.search(r'\b' + re.escape(kw) + r'\w*\b', combined):
                        kw_company_counts[kw] += 1
                else:
                    if kw in combined:
                        kw_company_counts[kw] += 1

        # Compute rarity: 1.0 = appears in no other filing, 0.0 = appears in all
        rarity = {}
        for kw in keywords:
            prevalence = kw_company_counts[kw] / total
            rarity[kw] = 1.0 - prevalence

        logger.debug(
            "Keyword rarity: %s",
            {kw: f"{r:.2f}" for kw, r in rarity.items()}
        )

        return rarity

    def _score_company(self, ticker: str, name: str, sector: str,
                        industry: str, cik: str,
                        keywords: List[str],
                        phrases: List[str],
                        rarity_weights: Dict[str, float] = None,
                        core_term: str = None,
                        form_types: List[str] = None,
                        implicit_phrases: List[str] = None) -> Optional[SearchResult]:
        """
        Score a single company against the search terms.

        Returns SearchResult or None if no matches.
        """
        if implicit_phrases is None:
            implicit_phrases = []

        sections = self.store.get_all_section_text(ticker, form_types=form_types)

        # Core term gate: for multi-keyword queries, require the rarest
        # keyword (or any phrase) to be present. This prevents companies
        # matching only generic words from appearing in results.
        if core_term and len(keywords) > 1:
            combined_lower = " ".join(
                text.lower() for text in sections.values() if text
            )
            # Use \w* after the term to match plurals/variants
            # e.g. "hypersonic" also matches "hypersonics"
            core_present = bool(
                re.search(r'\b' + re.escape(core_term) + r'\w*\b', combined_lower)
            )
            phrase_present = any(p in combined_lower for p in phrases) if phrases else False
            if not core_present and not phrase_present:
                return None

        # Check each section for matches
        all_term_scores = {}  # term -> weighted score
        all_term_counts = {}  # term -> total count
        sections_hit = set()
        excerpts = []
        total_hits = 0
        implicit_phrase_hits = 0  # Track implicit phrase matches separately

        for section_id, text in sections.items():
            if not text:
                continue

            text_lower = text.lower()
            weight = SECTION_WEIGHTS.get(section_id, 1.0)

            # Score keywords
            for kw in keywords:
                count = self._count_occurrences(text_lower, kw)
                if count > 0:
                    sections_hit.add(section_id)
                    total_hits += count

                    # Weighted score: count * section_weight
                    weighted = count * weight
                    all_term_scores[kw] = all_term_scores.get(kw, 0) + weighted
                    all_term_counts[kw] = all_term_counts.get(kw, 0) + count

                    # Extract excerpts (up to 2 per section per keyword)
                    section_excerpts = self._extract_excerpts(
                        text, kw, max_excerpts=2
                    )
                    excerpts.extend(section_excerpts)

            # Score explicit phrases (higher weight -- exact matches are more precise)
            for phrase in phrases:
                count = self._count_occurrences(text_lower, phrase)
                if count > 0:
                    sections_hit.add(section_id)
                    total_hits += count

                    # Explicit phrases get 5x multiplier for precision
                    weighted = count * weight * 5.0
                    all_term_scores[phrase] = all_term_scores.get(phrase, 0) + weighted
                    all_term_counts[phrase] = all_term_counts.get(phrase, 0) + count

                    section_excerpts = self._extract_excerpts(
                        text, phrase, max_excerpts=2
                    )
                    excerpts.extend(section_excerpts)

            # Score implicit phrases (moderate weight -- rewards adjacency)
            for imp_phrase in implicit_phrases:
                count = self._count_occurrences(text_lower, imp_phrase)
                if count > 0:
                    sections_hit.add(section_id)
                    implicit_phrase_hits += count

                    # Implicit phrases get 2.5x multiplier (less than explicit 5x)
                    weighted = count * weight * 2.5
                    all_term_scores[imp_phrase] = all_term_scores.get(imp_phrase, 0) + weighted
                    all_term_counts[imp_phrase] = all_term_counts.get(imp_phrase, 0) + count

                    section_excerpts = self._extract_excerpts(
                        text, imp_phrase, max_excerpts=1
                    )
                    excerpts.extend(section_excerpts)

        if total_hits == 0 and implicit_phrase_hits == 0:
            return None

        # Compute final score (0-100)
        score = self._compute_final_score(
            all_term_scores, all_term_counts,
            keywords, phrases, sections_hit,
            rarity_weights or {},
            implicit_phrases=implicit_phrases
        )

        # Get financial data from cache
        financials = self.store.get_financials(ticker) or {}
        filing_date = self.store.get_filing_date(ticker)

        # Get company name from store metadata if not provided
        if not name:
            meta = self.store.get_filing_metadata(ticker)
            name = meta.get("company_name", ticker) if meta else ticker

        result = SearchResult(
            ticker=ticker,
            company_name=name,
            sector=sector,
            industry=industry,
            cik=cik,
            match_score=min(score, 100.0),
            keywords_matched=list(all_term_counts.keys()),
            keyword_counts=all_term_counts,
            matched_excerpts=excerpts[:10],  # Limit to 10 excerpts
            sections_matched=list(sections_hit),
            total_hits=total_hits,
            revenue=financials.get("revenue"),
            net_income=financials.get("net_income"),
            fcf=financials.get("fcf"),
            operating_cash_flow=financials.get("operating_cash_flow"),
            filing_date=filing_date,
        )

        return result

    def _count_occurrences(self, text: str, term: str) -> int:
        """Count non-overlapping occurrences of a term in text.
        Uses stem-aware matching: 'hypersonic' matches 'hypersonics' too."""
        # Use word-boundary aware counting for single keywords
        if ' ' not in term:
            # Single word: \w* allows plurals/variants (e.g. hypersonic -> hypersonics)
            pattern = r'\b' + re.escape(term) + r'\w*\b'
            return len(re.findall(pattern, text, re.IGNORECASE))
        else:
            # Phrase: simple substring count
            return text.lower().count(term.lower())

    def _extract_excerpts(self, text: str, term: str,
                           max_excerpts: int = 2) -> List[str]:
        """
        Extract text excerpts showing the keyword in context.

        Returns up to max_excerpts strings with the keyword surrounded
        by context characters.
        """
        excerpts = []
        term_lower = term.lower()
        text_lower = text.lower()

        start_pos = 0
        while len(excerpts) < max_excerpts:
            idx = text_lower.find(term_lower, start_pos)
            if idx == -1:
                break

            # Extract context around the match
            ctx_start = max(0, idx - EXCERPT_CONTEXT)
            ctx_end = min(len(text), idx + len(term) + EXCERPT_CONTEXT)

            excerpt = text[ctx_start:ctx_end].strip()
            # Clean up whitespace
            excerpt = re.sub(r'\s+', ' ', excerpt)

            # Add ellipsis if truncated
            if ctx_start > 0:
                excerpt = "..." + excerpt
            if ctx_end < len(text):
                excerpt = excerpt + "..."

            excerpts.append(excerpt)
            start_pos = idx + len(term)

        return excerpts

    def _compute_final_score(self, term_scores: Dict[str, float],
                              term_counts: Dict[str, int],
                              keywords: List[str],
                              phrases: List[str],
                              sections_hit: set,
                              rarity_weights: Dict[str, float] = None,
                              implicit_phrases: List[str] = None) -> float:
        """
        Compute the final match score (0-100).

        Scoring factors:
          1. Rarity-weighted hit score (logarithmic scale)
          2. Breadth bonus for non-trivial keywords (rarity > 0.3)
          3. Section breadth bonus (found in multiple sections)
          4. Phrase precision bonus (explicit phrases: +10, implicit: +5)
        """
        if not term_scores:
            return 0.0
        if rarity_weights is None:
            rarity_weights = {}
        if implicit_phrases is None:
            implicit_phrases = []

        # 1. Base score from rarity-weighted hits (logarithmic)
        import math
        total_weighted = 0.0
        for term, raw_score in term_scores.items():
            rarity = rarity_weights.get(term, 0.5)
            # Ensure a minimum weight of 0.1 so no keyword is completely zeroed
            effective_weight = max(rarity, 0.1)
            total_weighted += raw_score * effective_weight

        base_score = min(55.0, math.log2(1 + total_weighted) * 8)

        # 2. Breadth bonus: only count non-trivial keywords (rarity > 0.3)
        non_trivial_matched = 0
        for term in term_counts.keys():
            rarity = rarity_weights.get(term, 0.5)
            if rarity > 0.3:
                non_trivial_matched += 1
        # Also count matched phrases as non-trivial
        for phrase in phrases:
            if phrase in term_counts:
                non_trivial_matched += 1

        breadth_bonus = max(0, (non_trivial_matched - 1)) * 8  # Up to ~16 points
        breadth_bonus = min(breadth_bonus, 20.0)

        # 3. Section breadth bonus: found in multiple sections
        section_bonus = min(len(sections_hit) * 5, 15)  # Up to 15 points

        # 4. Phrase bonus: explicit phrases found (+10 each)
        phrase_bonus = 0
        for phrase in phrases:
            if phrase in term_counts:
                phrase_bonus += 10  # 10 points per explicit phrase matched

        # 5. Implicit phrase bonus: auto-detected adjacency (+5 each)
        implicit_bonus = 0
        for imp_phrase in implicit_phrases:
            if imp_phrase in term_counts:
                implicit_bonus += 5  # 5 points per implicit phrase matched

        score = base_score + breadth_bonus + section_bonus + phrase_bonus + implicit_bonus

        return min(score, 100.0)
