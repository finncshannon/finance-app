"""
Filing Parser -- extracts key sections from SEC filing HTML.

Supports:
  - 10-K: Items 1 (Business), 1A (Risk Factors), 7 (MD&A)
  - 10-Q: Items 1 (Financials), 2 (MD&A), 3 (Market Risk), 4 (Controls)
  - 8-K: Item text extraction (material events)

Challenge: Every company formats their filings differently. Modern iXBRL
filings split section headers across multiple HTML elements, making
regex on raw HTML unreliable.

Strategy:
  1. Convert entire HTML to plain text (preserving rough position mapping)
  2. Find section boundaries in the plain text
  3. Extract text between section markers
  4. Clean up extracted text

Usage:
    from core.filing_parser import FilingParser

    parser = FilingParser()

    # 10-K
    sections = parser.extract_sections(html_content)
    print(sections["item1"][:500])    # Business description

    # 10-Q
    sections = parser.extract_sections(html_content, form_type="10-Q")
    print(sections["10q_item2"][:500])  # MD&A

    # 8-K
    sections = parser.extract_sections(html_content, form_type="8-K")
    print(sections["8k_body"][:500])    # Full 8-K text
"""

import re
import html as htmlmod
import logging
from typing import Dict, Optional, List, Tuple
from html.parser import HTMLParser

logger = logging.getLogger(__name__)


class _TextExtractor(HTMLParser):
    """
    HTML parser that extracts visible text, stripping tags.

    Preserves paragraph structure but removes:
      - All HTML tags
      - Script/style blocks
      - Comments
      - Excessive whitespace
    """

    SKIP_TAGS = {"script", "style", "head", "title", "meta", "link", "noscript"}

    def __init__(self):
        super().__init__()
        self.result = []
        self._skip_stack = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_stack += 1
        elif tag in ("p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6",
                      "li", "tr"):
            if self.result and self.result[-1] != "\n":
                self.result.append("\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_stack = max(0, self._skip_stack - 1)
        elif tag in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr"):
            if self.result and self.result[-1] != "\n":
                self.result.append("\n")

    def handle_data(self, data):
        if self._skip_stack > 0:
            return
        text = data.strip()
        if text:
            self.result.append(text)
            self.result.append(" ")

    def handle_entityref(self, name):
        char = htmlmod.unescape(f"&{name};")
        if char and self._skip_stack == 0:
            self.result.append(char)

    def handle_charref(self, name):
        char = htmlmod.unescape(f"&#{name};")
        if char and self._skip_stack == 0:
            self.result.append(char)

    def get_text(self) -> str:
        return "".join(self.result)


class FilingParser:
    """
    Extracts and cleans 10-K filing sections from raw HTML.

    Supports multiple header formats across different companies.
    Works by converting to plain text first, then finding sections.
    """

    # ================================================================
    # 10-K section header patterns
    # ================================================================
    # These match against cleaned text (HTML already stripped).
    # Order: most specific to least specific. First match wins.
    # Note: iXBRL can insert spaces within words (e.g., "B USINESS", "RIS K"),
    # so patterns use \s* within keywords to handle this.
    SECTION_PATTERNS = {
        "item1": [
            r'ITEM\s+1[\.\s]+B\s*U\s*S\s*I\s*N\s*E\s*S\s*S\b',
            r'Item\s+1[\.\s]+B\s*u\s*s\s*i\s*n\s*e\s*s\s*s\b',
        ],
        "item1a": [
            r'ITEM\s+1A[\.\s]+R\s*I\s*S\s*K\s+F\s*A\s*C\s*T\s*O\s*R\s*S',
            r'Item\s+1A[\.\s]+R\s*i\s*s\s*k\s+F\s*a\s*c\s*t\s*o\s*r\s*s',
        ],
        "item1b": [
            r'ITEM\s+1B[\.\s]+',
            r'Item\s+1B[\.\s]+',
        ],
        "item1c": [
            r'ITEM\s+1C[\.\s]+',
            r'Item\s+1C[\.\s]+',
        ],
        "item2": [
            r'ITEM\s+2[\.\s]+P\s*R\s*O\s*P\s*E\s*R\s*T\s*I\s*E\s*S',
            r'Item\s+2[\.\s]+P\s*r\s*o\s*p\s*e\s*r\s*t\s*i\s*e\s*s',
        ],
        "item7": [
            r"ITEM\s+7[\.\s]+M\s*A\s*N\s*A\s*G\s*E\s*M\s*E\s*N\s*T",
            r"Item\s+7[\.\s]+M\s*a\s*n\s*a\s*g\s*e\s*m\s*e\s*n\s*t",
            r"ITEM\s+7[\.\s]+MD\s*&\s*A",
        ],
        "item7a": [
            r'ITEM\s+7A[\.\s]+',
            r'Item\s+7A[\.\s]+',
        ],
        "item8": [
            r'ITEM\s+8[\.\s]+F\s*I\s*N\s*A\s*N\s*C\s*I\s*A\s*L',
            r'Item\s+8[\.\s]+F\s*i\s*n\s*a\s*n\s*c\s*i\s*a\s*l',
        ],
    }

    # ================================================================
    # 10-Q section header patterns (Part I, Items 1-4)
    # ================================================================
    SECTION_PATTERNS_10Q = {
        "10q_item1": [
            r'ITEM\s+1[\.\s]+F\s*I\s*N\s*A\s*N\s*C\s*I\s*A\s*L\s+S\s*T\s*A\s*T\s*E\s*M\s*E\s*N\s*T\s*S',
            r'Item\s+1[\.\s]+F\s*i\s*n\s*a\s*n\s*c\s*i\s*a\s*l\s+S\s*t\s*a\s*t\s*e\s*m\s*e\s*n\s*t\s*s',
        ],
        "10q_item2": [
            r"ITEM\s+2[\.\s]+M\s*A\s*N\s*A\s*G\s*E\s*M\s*E\s*N\s*T",
            r"Item\s+2[\.\s]+M\s*a\s*n\s*a\s*g\s*e\s*m\s*e\s*n\s*t",
            r"ITEM\s+2[\.\s]+MD\s*&\s*A",
        ],
        "10q_item3": [
            r'ITEM\s+3[\.\s]+Q\s*U\s*A\s*N\s*T\s*I\s*T\s*A\s*T\s*I\s*V\s*E',
            r'Item\s+3[\.\s]+Q\s*u\s*a\s*n\s*t\s*i\s*t\s*a\s*t\s*i\s*v\s*e',
        ],
        "10q_item4": [
            r'ITEM\s+4[\.\s]+C\s*O\s*N\s*T\s*R\s*O\s*L\s*S',
            r'Item\s+4[\.\s]+C\s*o\s*n\s*t\s*r\s*o\s*l\s*s',
        ],
        # Part II markers (used as end boundaries)
        "10q_part2": [
            r'PART\s+II',
            r'Part\s+II',
        ],
    }

    # ================================================================
    # 8-K: no standard section headers — extract full body
    # ================================================================
    SECTION_PATTERNS_8K = {
        "8k_item": [
            r'ITEM\s+\d+\.\d+',
            r'Item\s+\d+\.\d+',
        ],
        "8k_signature": [
            r'SIGNATURE',
            r'Signature',
        ],
    }

    # Boilerplate patterns to remove from extracted text
    BOILERPLATE_PATTERNS = [
        r'Table\s+of\s+Contents',
        r'(?:Page|F-)\s*\d+',
    ]

    def __init__(self, max_section_chars: int = 500000):
        """
        Args:
            max_section_chars: Maximum characters per section (safety limit).
        """
        self.max_section_chars = max_section_chars

    def extract_sections(self, html_content: str, form_type: str = "10-K") -> Dict[str, str]:
        """
        Extract key sections from a filing HTML.

        Args:
            html_content: Raw HTML string of the filing
            form_type: "10-K", "10-Q", or "8-K"

        Returns:
            Dict with section IDs as keys, cleaned plain text as values.
            - 10-K: "item1", "item1a", "item7"
            - 10-Q: "10q_item2" (MD&A), "10q_item3" (Market Risk)
            - 8-K: "8k_body" (full item text)
            Missing sections have empty string.
        """
        if form_type == "10-Q":
            return self._extract_10q_sections(html_content)
        elif form_type == "8-K":
            return self._extract_8k_sections(html_content)
        else:
            return self._extract_10k_sections(html_content)

    def _extract_10k_sections(self, html_content: str) -> Dict[str, str]:
        """Extract Items 1, 1A, 7 from a 10-K."""
        result = {
            "item1": "",
            "item1a": "",
            "item7": "",
        }

        if not html_content:
            return result

        full_text = self._html_to_text(html_content)

        if not full_text or len(full_text) < 1000:
            logger.warning("HTML produced very little text after extraction")
            return result

        boundaries = self._find_section_boundaries(full_text)

        if not boundaries:
            logger.warning("Could not find any section boundaries")
            return result

        for section_id in ["item1", "item1a", "item7"]:
            text = self._extract_section_text(full_text, boundaries, section_id)
            if text:
                text = self._clean_section_text(text)
                if len(text) > self.max_section_chars:
                    text = text[:self.max_section_chars] + "\n[TRUNCATED]"
                result[section_id] = text

        return result

    def _extract_10q_sections(self, html_content: str) -> Dict[str, str]:
        """Extract Items 2 (MD&A) and 3 (Market Risk) from a 10-Q."""
        result = {
            "10q_item2": "",   # MD&A (most valuable for screening)
            "10q_item3": "",   # Quantitative & Qualitative Disclosures
        }

        if not html_content:
            return result

        full_text = self._html_to_text(html_content)

        if not full_text or len(full_text) < 500:
            logger.warning("10-Q HTML produced very little text")
            return result

        # Find boundaries using 10-Q patterns
        boundaries = self._find_section_boundaries(full_text, self.SECTION_PATTERNS_10Q)

        if not boundaries:
            logger.warning("Could not find any 10-Q section boundaries")
            return result

        # Define end sections for 10-Q items
        end_sections_10q = {
            "10q_item2": ["10q_item3", "10q_item4", "10q_part2"],
            "10q_item3": ["10q_item4", "10q_part2"],
        }

        for section_id in ["10q_item2", "10q_item3"]:
            text = self._extract_section_text(
                full_text, boundaries, section_id,
                end_sections_override=end_sections_10q
            )
            if text:
                text = self._clean_section_text(text)
                if len(text) > self.max_section_chars:
                    text = text[:self.max_section_chars] + "\n[TRUNCATED]"
                result[section_id] = text

        return result

    def _extract_8k_sections(self, html_content: str) -> Dict[str, str]:
        """
        Extract body text from an 8-K filing.

        8-K filings are short and don't have standardized section structure
        like 10-K/10-Q. We extract everything between the first Item and
        the Signatures block.
        """
        result = {
            "8k_body": "",
        }

        if not html_content:
            return result

        full_text = self._html_to_text(html_content)

        if not full_text or len(full_text) < 100:
            logger.warning("8-K HTML produced very little text")
            return result

        # Find Item markers and Signature boundary
        boundaries = self._find_section_boundaries(full_text, self.SECTION_PATTERNS_8K)

        if not boundaries:
            # Fallback: use the full text (8-K filings are short)
            text = self._clean_section_text(full_text)
            if len(text) > self.max_section_chars:
                text = text[:self.max_section_chars] + "\n[TRUNCATED]"
            result["8k_body"] = text
            return result

        # Extract from first Item to Signature (or end)
        item_positions = [pos for sid, pos in boundaries if sid == "8k_item"]
        sig_positions = [pos for sid, pos in boundaries if sid == "8k_signature"]

        if item_positions:
            start = min(item_positions)
            end = min(sig_positions) if sig_positions else len(full_text)
            text = full_text[start:end]
        else:
            text = full_text

        text = self._clean_section_text(text)
        if len(text) > self.max_section_chars:
            text = text[:self.max_section_chars] + "\n[TRUNCATED]"
        result["8k_body"] = text

        return result

    # Map section IDs to filenames for saving
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

    def save_sections(self, sections: Dict[str, str], company_dir):
        """
        Save extracted sections to disk as .txt files.

        Args:
            sections: Dict from extract_sections()
            company_dir: Path to the company's data directory
        """
        from pathlib import Path
        company_dir = Path(company_dir)
        company_dir.mkdir(parents=True, exist_ok=True)

        for section_id, text in sections.items():
            if not text:
                continue
            filename = self.SECTION_FILE_MAP.get(section_id)
            if not filename:
                continue
            path = company_dir / filename
            try:
                path.write_text(text, encoding="utf-8")
            except Exception as e:
                logger.error(f"Failed to save {path}: {e}")

    # ----------------------------------------------------------------
    # Step 1: HTML to plain text
    # ----------------------------------------------------------------

    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to plain text, preserving paragraph structure."""
        # Strip iXBRL/XBRL wrapper tags first
        html_str = self._strip_xbrl_tags(html_content)

        # Remove HTML comments
        html_str = re.sub(r'<!--.*?-->', '', html_str, flags=re.DOTALL)

        # Remove large tables (financial data is noise for text search)
        html_str = self._strip_large_tables(html_str)

        # Parse HTML to extract text
        try:
            extractor = _TextExtractor()
            extractor.feed(html_str)
            text = extractor.get_text()
        except Exception:
            # Fallback: regex-based tag stripping
            text = re.sub(r'<[^>]+>', ' ', html_str)
            text = htmlmod.unescape(text)

        return text

    def _strip_xbrl_tags(self, html_content: str) -> str:
        """Remove iXBRL/XBRL wrapper tags while preserving content."""
        text = re.sub(r'</?ix:[^>]*>', '', html_content)
        text = re.sub(r'<\?xbrl[^?]*\?>', '', text)
        text = re.sub(r'</?xbrli?:[^>]*>', '', text)
        return text

    def _strip_large_tables(self, html_str: str) -> str:
        """
        Remove large HTML tables (financial data noise).
        Keep small tables (often used for layout in older filings).
        """
        table_pattern = re.compile(r'<table[^>]*>.*?</table>', re.DOTALL | re.IGNORECASE)

        def should_remove(match):
            table_html = match.group(0)
            text_only = re.sub(r'<[^>]+>', '', table_html)
            return len(text_only.strip()) > 500

        return table_pattern.sub(
            lambda m: '' if should_remove(m) else m.group(0),
            html_str
        )

    # ----------------------------------------------------------------
    # Step 2: Find section boundaries in plain text
    # ----------------------------------------------------------------

    def _find_section_boundaries(self, text: str,
                                  patterns_dict: Dict = None) -> List[Tuple[str, int]]:
        """
        Find all section start positions in the plain text.

        Args:
            text: Plain text of the filing
            patterns_dict: Section patterns to use (defaults to SECTION_PATTERNS for 10-K)

        Returns sorted list of (section_id, char_position).

        Strategy: Find ALL matches for each section, then pick the one
        that's most likely the actual section start (not a ToC reference).
        """
        if patterns_dict is None:
            patterns_dict = self.SECTION_PATTERNS

        boundaries = []

        for section_id, patterns in patterns_dict.items():
            pos = self._find_best_match(text, patterns, section_id)
            if pos is not None:
                boundaries.append((section_id, pos))

        boundaries.sort(key=lambda x: x[1])
        return boundaries

    def _find_best_match(self, text: str, patterns: List[str],
                          section_id: str) -> Optional[int]:
        """
        Find the best match for a section header in plain text.

        When multiple matches exist (ToC + actual section), prefer the
        one that's NOT in the table of contents (first ~5% of document).
        """
        all_matches = []

        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                pos = match.start()
                all_matches.append(pos)

        if not all_matches:
            return None

        if len(all_matches) == 1:
            return all_matches[0]

        # Multiple matches: distinguish ToC from actual section.
        # Heuristic: actual section headers are followed by substantial text
        # (paragraphs), while ToC entries are followed by page numbers or
        # other section entries.
        doc_len = len(text)
        toc_threshold = doc_len * 0.05  # First 5% is usually ToC/cover

        # Strategy: Find the SECOND occurrence — first is ToC, second is actual
        # But also check: the second one should have substantial text after it
        all_matches.sort()

        # Filter out matches that are just ToC entries
        # ToC entry: followed by a page number within 50 chars
        actual_matches = []
        for pos in all_matches:
            # Look at what follows this match
            after = text[pos:pos + 200]
            # If it's a ToC entry, it'll have "... 15" or similar page number nearby
            # and then immediately another "ITEM" entry
            lines_after = after.split('\n')
            first_line = lines_after[0] if lines_after else ""

            # Check if followed by page number pattern (e.g., "Business 3" or "Business    15")
            is_toc = bool(re.search(r'\d+\s*$', first_line.strip()))

            if not is_toc or pos > toc_threshold:
                actual_matches.append(pos)

        if actual_matches:
            # Prefer matches after the ToC region
            non_toc = [p for p in actual_matches if p > toc_threshold]
            if non_toc:
                return min(non_toc)
            return actual_matches[-1]  # Last match as fallback

        # Fallback: use the last occurrence
        return max(all_matches)

    # ----------------------------------------------------------------
    # Step 3: Extract section text using boundaries
    # ----------------------------------------------------------------

    def _extract_section_text(self, full_text: str,
                                boundaries: List[Tuple[str, int]],
                                target_section: str,
                                end_sections_override: Dict = None) -> str:
        """
        Extract text for a specific section using boundary positions.

        Section ranges:
            Item 1:  from "item1" to next section (item1a, item1b, item1c, item2)
            Item 1A: from "item1a" to next section (item1b, item1c, item2)
            Item 7:  from "item7" to next section (item7a, item8)
        """
        # Define what sections can end each target section
        end_sections = {
            "item1":  ["item1a", "item1b", "item1c", "item2"],
            "item1a": ["item1b", "item1c", "item2"],
            "item7":  ["item7a", "item8"],
        }
        if end_sections_override:
            end_sections.update(end_sections_override)

        boundary_dict = {sid: pos for sid, pos in boundaries}

        if target_section not in boundary_dict:
            return ""

        start = boundary_dict[target_section]

        # Find the end: first following section
        end = None
        for end_section in end_sections.get(target_section, []):
            if end_section in boundary_dict:
                pos = boundary_dict[end_section]
                if pos > start:
                    if end is None or pos < end:
                        end = pos
                    break  # Take the first valid end section

        if end:
            return full_text[start:end]
        else:
            # No clear end: take a reasonable chunk
            max_chars = {"item1": 200000, "item1a": 300000, "item7": 400000}
            limit = max_chars.get(target_section, 200000)
            return full_text[start:start + limit]

    # ----------------------------------------------------------------
    # Step 4: Clean extracted text
    # ----------------------------------------------------------------

    def _clean_section_text(self, text: str) -> str:
        """Clean extracted section text for search use."""
        # Decode HTML entities
        text = htmlmod.unescape(text)

        # Fix common encoding artifacts
        text = text.replace('\xa0', ' ')
        text = text.replace('\u200b', '')
        text = text.replace('\u2019', "'")
        text = text.replace('\u2018', "'")
        text = text.replace('\u201c', '"')
        text = text.replace('\u201d', '"')
        text = text.replace('\u2014', '--')
        text = text.replace('\u2013', '-')

        # Remove boilerplate
        for pattern in self.BOILERPLATE_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Normalize whitespace within lines
        text = re.sub(r'[ \t]+', ' ', text)

        # Remove standalone page numbers
        text = re.sub(r'^\s*\d{1,3}\s*$', '', text, flags=re.MULTILINE)

        # Collapse multiple blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove leading/trailing whitespace per line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)

        return text.strip()

    # ----------------------------------------------------------------
    # Utilities
    # ----------------------------------------------------------------

    def get_section_stats(self, sections: Dict[str, str]) -> Dict[str, Dict]:
        """Get statistics about extracted sections."""
        stats = {}
        for section_id, text in sections.items():
            if text:
                words = len(text.split())
                paragraphs = len([p for p in text.split('\n\n') if p.strip()])
                stats[section_id] = {
                    "chars": len(text),
                    "words": words,
                    "paragraphs": paragraphs,
                }
            else:
                stats[section_id] = {"chars": 0, "words": 0, "paragraphs": 0}
        return stats
