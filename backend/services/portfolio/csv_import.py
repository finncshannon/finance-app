"""CSV import for portfolio positions and transactions — broker-specific parsers."""

from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import dataclass, field

from .models import PositionCreate, ImportPreview, ImportResult

logger = logging.getLogger("finance_app")


# =========================================================================
# Dataclasses (new broker-specific parser output)
# =========================================================================

@dataclass
class ParsedPosition:
    ticker: str
    shares: float
    cost_basis_per_share: float | None = None
    account: str | None = None
    date_acquired: str | None = None
    company_name: str | None = None


@dataclass
class ParsedTransaction:
    date: str
    type: str  # BUY, SELL, DIVIDEND
    ticker: str
    shares: float
    price: float
    fees: float = 0.0
    account: str | None = None


@dataclass
class ParseResult:
    success: bool
    positions: list[ParsedPosition] = field(default_factory=list)
    transactions: list[ParsedTransaction] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    row_count: int = 0
    skipped_count: int = 0


# =========================================================================
# Column aliases for generic auto-detection
# =========================================================================

COLUMN_ALIASES = {
    "ticker": ["symbol", "ticker", "stock symbol", "stock", "instrument"],
    "shares": ["quantity", "qty", "shares", "position", "amount"],
    "cost_basis": ["cost basis", "avg cost", "average cost basis", "price paid",
                   "avg price", "cost basis total", "cost basis per share",
                   "cost per share", "average cost", "purchase price"],
    "account": ["account", "acct", "account name", "account number", "account name/number"],
    "date": ["date", "date acquired", "purchase date", "trade date",
             "acquisition date", "buy date"],
    "name": ["description", "company name", "name", "security name"],
}

TX_ALIASES = {
    "ticker": ["symbol", "ticker", "stock symbol", "stock", "instrument"],
    "date": ["date", "run date", "trade date", "transaction date", "settlement date"],
    "type": ["action", "type", "transaction type", "trans type", "activity"],
    "shares": ["quantity", "qty", "shares", "amount"],
    "price": ["price", "price per share", "execution price", "avg price", "fill price"],
    "fees": ["fees", "commission", "fee", "commissions"],
    "account": ["account", "acct", "account name"],
}


# =========================================================================
# Utility helpers
# =========================================================================

def _clean_ticker(raw: str) -> str:
    """Strip non-alpha characters (except .) and uppercase."""
    return re.sub(r'[^A-Za-z.]', '', raw).upper()


def _parse_float(val: str | None) -> float | None:
    """Parse a float from a string, handling $, commas, parens for negatives."""
    if val is None:
        return None
    cleaned = re.sub(r'[$,]', '', val.strip())
    if cleaned.startswith('(') and cleaned.endswith(')'):
        cleaned = '-' + cleaned[1:-1]
    if not cleaned or cleaned in ('--', 'N/A', 'n/a'):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _normalize_header(h: str) -> str:
    """Normalize a CSV header for matching: lowercase, strip whitespace and unit suffixes like ($)."""
    h = h.strip().lower()
    # Strip trailing unit indicators: ($), (%), (#), etc.
    h = re.sub(r'\s*\([^)]*\)\s*$', '', h).strip()
    return h


def _match_columns(headers: list[str], aliases: dict[str, list[str]]) -> dict[str, str | None]:
    """Map logical field names to actual CSV column names via case-insensitive alias matching."""
    # Build two lookup dicts: exact stripped header and unit-suffix-stripped header
    normalized = {h.strip().lower(): h for h in headers}
    stripped = {_normalize_header(h): h for h in headers}
    result: dict[str, str | None] = {}
    for field_name, candidates in aliases.items():
        matched = None
        for candidate in candidates:
            key = candidate.lower()
            if key in normalized:
                matched = normalized[key]
                break
            if key in stripped:
                matched = stripped[key]
                break
        result[field_name] = matched
    return result


def _clean_csv_content(content: str) -> str:
    """Strip BOM, leading blank lines, and trailing disclaimer/footer text from CSV content."""
    # Strip BOM if present
    content = content.lstrip('\ufeff')
    lines = content.splitlines()

    # Skip leading blank lines to find the header
    start = 0
    for i, line in enumerate(lines):
        if line.strip():
            start = i
            break

    # Trim trailing disclaimers: look for a stretch of blank lines followed by
    # quoted text that doesn't look like CSV data.  Walk backwards from the end.
    end = len(lines)
    for i in range(len(lines) - 1, start, -1):
        stripped = lines[i].strip()
        if not stripped:
            end = i
            continue
        # Disclaimer lines typically start with a quote and have no commas
        # separating distinct CSV fields.  A valid data line has the same number
        # of commas as the header.
        if stripped.startswith('"') and stripped.count(',') <= 1:
            end = i
            continue
        break

    return "\n".join(lines[start:end])


def _infer_transaction_type(raw: str) -> str | None:
    """Map various broker action strings to BUY/SELL/DIVIDEND."""
    val = raw.strip().upper()
    if not val:
        return None
    # Buy patterns: "BUY", "BOUGHT", "YOU BOUGHT", "PURCHASE", "REINVEST"
    if "BOUGHT" in val or "BUY" in val or "PURCHASE" in val or "REINVEST" in val:
        return "BUY"
    # Sell patterns: "SELL", "SOLD", "YOU SOLD"
    if "SOLD" in val or "SELL" in val:
        return "SELL"
    # Dividend patterns
    if "DIVIDEND" in val or val == "DIV" or "DISTRIBUTION" in val:
        return "DIVIDEND"
    return None


# =========================================================================
# Fidelity parser
# =========================================================================

_FIDELITY_EXPECTED = {"account name/number", "symbol", "description", "quantity"}


def _parse_fidelity(content: str) -> ParseResult:
    """Parse Fidelity position CSV."""
    content = _clean_csv_content(content)
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        return ParseResult(success=False, errors=["Could not parse CSV headers"])

    headers_lower = {h.strip().lower() for h in reader.fieldnames}
    if not _FIDELITY_EXPECTED.issubset(headers_lower):
        found = ", ".join(reader.fieldnames)
        return ParseResult(
            success=False,
            errors=[f"Expected Fidelity format but found columns: {found}. Try 'Generic CSV'."],
        )

    col_map = _match_columns(reader.fieldnames, {
        "ticker": ["symbol"],
        "shares": ["quantity"],
        "cost_basis": ["average cost basis", "cost basis per share"],
        "account": ["account name/number"],
        "name": ["description"],
    })

    positions: list[ParsedPosition] = []
    warnings: list[str] = []
    row_count = 0
    skipped = 0

    for row in reader:
        row_count += 1
        ticker_raw = (row.get(col_map["ticker"] or "") or "").strip()

        # Skip summary/total rows and Pending Activity rows
        if not ticker_raw or ticker_raw.upper() in ("", "TOTAL", "CASH", "PENDING ACTIVITY"):
            skipped += 1
            continue
        desc = (row.get(col_map.get("name") or "") or "").strip().lower()
        if "pending" in desc:
            skipped += 1
            continue

        ticker = _clean_ticker(ticker_raw)
        if not ticker:
            skipped += 1
            continue

        shares = _parse_float(row.get(col_map["shares"] or ""))
        cost = _parse_float(row.get(col_map["cost_basis"] or ""))
        account = (row.get(col_map["account"] or "") or "").strip() or None
        name = (row.get(col_map.get("name") or "") or "").strip() or None

        if shares is None or shares <= 0:
            warnings.append(f"Row {row_count} ({ticker}): invalid shares, skipped")
            skipped += 1
            continue

        positions.append(ParsedPosition(
            ticker=ticker, shares=shares, cost_basis_per_share=cost,
            account=account, company_name=name,
        ))

    return ParseResult(success=True, positions=positions, warnings=warnings,
                       row_count=row_count, skipped_count=skipped)


# =========================================================================
# Schwab parser
# =========================================================================

_SCHWAB_EXPECTED = {"symbol", "description", "quantity"}


def _parse_schwab(content: str) -> ParseResult:
    """Parse Schwab position CSV."""
    content = _clean_csv_content(content)
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        return ParseResult(success=False, errors=["Could not parse CSV headers"])

    headers_lower = {h.strip().lower() for h in reader.fieldnames}
    if not _SCHWAB_EXPECTED.issubset(headers_lower):
        found = ", ".join(reader.fieldnames)
        return ParseResult(
            success=False,
            errors=[f"Expected Schwab format but found columns: {found}. Try 'Generic CSV'."],
        )

    col_map = _match_columns(reader.fieldnames, {
        "ticker": ["symbol"],
        "shares": ["quantity"],
        "cost_basis": ["cost basis"],
        "name": ["description"],
        "account": ["account"],
    })

    positions: list[ParsedPosition] = []
    warnings: list[str] = []
    row_count = 0
    skipped = 0

    for row in reader:
        row_count += 1
        ticker_raw = (row.get(col_map["ticker"] or "") or "").strip()
        if not ticker_raw or ticker_raw.upper() in ("TOTAL", "CASH", "ACCOUNT TOTAL"):
            skipped += 1
            continue

        ticker = _clean_ticker(ticker_raw)
        if not ticker:
            skipped += 1
            continue

        shares = _parse_float(row.get(col_map["shares"] or ""))
        total_cost = _parse_float(row.get(col_map["cost_basis"] or ""))
        account = (row.get(col_map.get("account") or "") or "").strip() or None
        name = (row.get(col_map.get("name") or "") or "").strip() or None

        if shares is None or shares <= 0:
            warnings.append(f"Row {row_count} ({ticker}): invalid shares, skipped")
            skipped += 1
            continue

        # Schwab cost_basis is total — divide by shares for per-share
        cost_per_share = None
        if total_cost is not None and shares > 0:
            cost_per_share = total_cost / shares

        positions.append(ParsedPosition(
            ticker=ticker, shares=shares, cost_basis_per_share=cost_per_share,
            account=account, company_name=name,
        ))

    return ParseResult(success=True, positions=positions, warnings=warnings,
                       row_count=row_count, skipped_count=skipped)


# =========================================================================
# IBKR parser
# =========================================================================

_IBKR_SECTION_BREAKS = frozenset([
    "trades", "cash report", "dividends", "interest",
    "fees", "deposits & withdrawals", "account information",
    "financial instrument information", "change in nav",
])


def _parse_ibkr(content: str) -> ParseResult:
    """Parse Interactive Brokers CSV (multi-section format)."""
    lines = content.strip().splitlines()
    if not lines:
        return ParseResult(success=False, errors=["Empty CSV content"])

    # IBKR CSVs have multi-section format with section headers.
    # Find the "Open Positions" or "Positions" section.
    section_lines: list[str] = []
    in_section = False

    for line in lines:
        parts = line.split(",", 1)
        first = parts[0].strip().strip('"').lower()

        if first in ("open positions", "positions", "portfolio"):
            in_section = True
            continue

        if in_section and first in _IBKR_SECTION_BREAKS:
            break

        if in_section:
            section_lines.append(line)

    if not section_lines:
        # Fallback: try parsing the whole file as a flat CSV
        section_lines = lines

    reader = csv.DictReader(io.StringIO("\n".join(section_lines)))
    if not reader.fieldnames:
        return ParseResult(success=False, errors=["Could not parse IBKR CSV headers"])

    col_map = _match_columns(reader.fieldnames, {
        "ticker": ["symbol", "financial instrument"],
        "shares": ["position", "quantity", "shares"],
        "cost_basis": ["avg price", "avg cost", "cost basis"],
        "name": ["description"],
    })

    if not col_map.get("ticker"):
        found = ", ".join(reader.fieldnames)
        return ParseResult(
            success=False,
            errors=[f"Expected IBKR format but found columns: {found}. Try 'Generic CSV'."],
        )

    positions: list[ParsedPosition] = []
    warnings: list[str] = []
    row_count = 0
    skipped = 0

    for row in reader:
        row_count += 1
        ticker_raw = (row.get(col_map["ticker"] or "") or "").strip()
        if not ticker_raw or ticker_raw.lower() in ("total", ""):
            skipped += 1
            continue

        ticker = _clean_ticker(ticker_raw)
        if not ticker:
            skipped += 1
            continue

        shares = _parse_float(row.get(col_map["shares"] or ""))
        cost = _parse_float(row.get(col_map["cost_basis"] or ""))
        name = (row.get(col_map.get("name") or "") or "").strip() or None

        if shares is None or shares == 0:
            warnings.append(f"Row {row_count} ({ticker}): zero or missing shares, skipped")
            skipped += 1
            continue

        positions.append(ParsedPosition(
            ticker=ticker, shares=abs(shares),
            cost_basis_per_share=abs(cost) if cost else None,
            company_name=name,
        ))

    return ParseResult(success=True, positions=positions, warnings=warnings,
                       row_count=row_count, skipped_count=skipped)


# =========================================================================
# Generic parser (auto-detect)
# =========================================================================

def _parse_generic(content: str) -> ParseResult:
    """Parse CSV with auto-detected column mapping."""
    content = _clean_csv_content(content)
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        return ParseResult(success=False, errors=["Could not parse CSV headers"])

    col_map = _match_columns(reader.fieldnames, COLUMN_ALIASES)

    if not col_map.get("ticker"):
        found_cols = [h for h in reader.fieldnames if h.strip()]
        matched = {k: v for k, v in col_map.items() if v}
        unmatched_fields = [k for k, v in col_map.items() if not v]
        msg_parts = [f"Could not auto-detect a ticker/symbol column."]
        msg_parts.append(f"Your CSV columns: {', '.join(found_cols)}.")
        if matched:
            matched_str = ", ".join(f'{k} -> "{v}"' for k, v in matched.items())
            msg_parts.append(f"Matched: {matched_str}.")
        msg_parts.append(f"Could not match: {', '.join(unmatched_fields)}.")
        msg_parts.append("Use the column mapping below or try a specific broker format.")
        return ParseResult(
            success=False,
            errors=[" ".join(msg_parts)],
        )

    positions: list[ParsedPosition] = []
    warnings: list[str] = []
    row_count = 0
    skipped = 0

    for row in reader:
        row_count += 1
        ticker_raw = (row.get(col_map["ticker"] or "") or "").strip()
        if not ticker_raw:
            skipped += 1
            continue

        ticker = _clean_ticker(ticker_raw)
        if not ticker or ticker in ("TOTAL", "CASH"):
            skipped += 1
            continue

        shares = _parse_float(row.get(col_map["shares"] or "")) if col_map.get("shares") else None
        cost = _parse_float(row.get(col_map["cost_basis"] or "")) if col_map.get("cost_basis") else None
        date_str = (row.get(col_map["date"] or "") or "").strip() if col_map.get("date") else None
        account = (row.get(col_map["account"] or "") or "").strip() if col_map.get("account") else None
        name = (row.get(col_map["name"] or "") or "").strip() if col_map.get("name") else None

        if shares is None or shares <= 0:
            warnings.append(f"Row {row_count} ({ticker}): invalid or missing shares, skipped")
            skipped += 1
            continue

        positions.append(ParsedPosition(
            ticker=ticker, shares=shares, cost_basis_per_share=cost,
            account=account or None, date_acquired=date_str or None,
            company_name=name or None,
        ))

    return ParseResult(success=True, positions=positions, warnings=warnings,
                       row_count=row_count, skipped_count=skipped)


# =========================================================================
# Transaction parser
# =========================================================================

def _parse_transactions(content: str, broker: str) -> ParseResult:
    """Parse a transaction CSV into ParsedTransaction records."""
    content = _clean_csv_content(content)
    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        return ParseResult(success=False, errors=["Could not parse CSV headers"])

    col_map = _match_columns(reader.fieldnames, TX_ALIASES)

    if not col_map.get("ticker"):
        found_cols = [h for h in reader.fieldnames if h.strip()]
        matched = {k: v for k, v in col_map.items() if v}
        unmatched = [k for k, v in col_map.items() if not v]
        msg_parts = [f"Could not find a ticker/symbol column for transactions."]
        msg_parts.append(f"Your CSV columns: {', '.join(found_cols)}.")
        if matched:
            matched_str = ", ".join(f'{k} -> "{v}"' for k, v in matched.items())
            msg_parts.append(f"Matched: {matched_str}.")
        msg_parts.append(f"Could not match: {', '.join(unmatched)}.")
        msg_parts.append("Use the column mapping below to assign them manually.")
        return ParseResult(
            success=False,
            errors=[" ".join(msg_parts)],
        )

    transactions: list[ParsedTransaction] = []
    warnings: list[str] = []
    row_count = 0
    skipped = 0

    for row in reader:
        row_count += 1
        ticker_raw = (row.get(col_map["ticker"] or "") or "").strip()
        if not ticker_raw:
            skipped += 1
            continue

        ticker = _clean_ticker(ticker_raw)
        if not ticker or ticker in ("TOTAL", "CASH"):
            skipped += 1
            continue

        # Type
        type_raw = (row.get(col_map.get("type") or "") or "").strip() if col_map.get("type") else ""
        tx_type = _infer_transaction_type(type_raw) if type_raw else "BUY"
        if tx_type is None:
            warnings.append(f"Row {row_count} ({ticker}): unknown transaction type '{type_raw}', skipped")
            skipped += 1
            continue

        date_str = (row.get(col_map.get("date") or "") or "").strip() if col_map.get("date") else ""
        shares = _parse_float(row.get(col_map.get("shares") or "")) if col_map.get("shares") else None
        if shares is None or shares == 0:
            warnings.append(f"Row {row_count} ({ticker}): missing shares, skipped")
            skipped += 1
            continue

        price = _parse_float(row.get(col_map.get("price") or "")) if col_map.get("price") else None
        fees = _parse_float(row.get(col_map.get("fees") or "")) if col_map.get("fees") else 0.0
        account = (row.get(col_map.get("account") or "") or "").strip() if col_map.get("account") else None

        transactions.append(ParsedTransaction(
            date=date_str, type=tx_type, ticker=ticker,
            shares=abs(shares), price=abs(price or 0),
            fees=abs(fees or 0), account=account or None,
        ))

    return ParseResult(success=True, transactions=transactions, warnings=warnings,
                       row_count=row_count, skipped_count=skipped)


# =========================================================================
# Dispatcher
# =========================================================================

def parse_csv(content: str, broker: str = "generic", import_type: str = "positions") -> ParseResult:
    """Parse CSV content using the specified broker format."""
    if import_type == "transactions":
        return _parse_transactions(content, broker)

    parsers = {
        "fidelity": _parse_fidelity,
        "schwab": _parse_schwab,
        "ibkr": _parse_ibkr,
        "generic": _parse_generic,
    }
    parser = parsers.get(broker, _parse_generic)
    return parser(content)


# =========================================================================
# Legacy CSVImporter class (backward compat for existing import endpoints)
# =========================================================================

COLUMN_MAPS: dict[str, dict[str, list[str]]] = {
    "generic": {
        "ticker": ["symbol", "ticker", "sym", "stock", "security"],
        "shares": ["quantity", "shares", "qty", "units", "shares_held"],
        "cost_basis": ["cost basis", "avg cost", "price paid", "cost_basis_per_share",
                       "average cost", "purchase price", "cost per share"],
        "date": ["date", "purchase date", "acquired", "date_acquired",
                 "acquisition date", "buy date", "trade date"],
        "account": ["account", "account name", "acct"],
    },
    "fidelity": {
        "ticker": ["symbol"],
        "shares": ["quantity"],
        "cost_basis": ["cost basis per share", "average cost basis"],
        "date": ["date acquired"],
        "account": ["account name/number"],
    },
    "schwab": {
        "ticker": ["symbol"],
        "shares": ["quantity"],
        "cost_basis": ["cost basis"],
        "date": ["date acquired"],
        "account": ["account"],
    },
    "ibkr": {
        "ticker": ["symbol"],
        "shares": ["position", "quantity"],
        "cost_basis": ["avg price", "avg cost"],
        "date": [],
        "account": [],
    },
}


class CSVImporter:
    """Parse and import broker CSV files into portfolio positions."""

    async def parse_csv(
        self, content: str, broker: str = "generic",
    ) -> ImportPreview:
        """Parse CSV content and return a preview of recognized positions."""
        warnings: list[str] = []
        positions: list[PositionCreate] = []

        reader = csv.DictReader(io.StringIO(content))
        if not reader.fieldnames:
            return ImportPreview(warnings=["Could not parse CSV headers"])

        # Map columns
        col_map = self._detect_columns(reader.fieldnames, broker)
        if not col_map.get("ticker"):
            return ImportPreview(
                warnings=["Could not find a ticker/symbol column"],
                row_count=0,
            )

        accounts_seen: set[str] = set()
        row_count = 0

        for row in reader:
            row_count += 1
            ticker = self._get_val(row, col_map.get("ticker"))
            if not ticker:
                warnings.append(f"Row {row_count}: missing ticker, skipped")
                continue

            # Clean ticker
            ticker = re.sub(r'[^A-Za-z.]', '', ticker).upper()
            if not ticker:
                continue

            shares = self._parse_float(self._get_val(row, col_map.get("shares")))
            cost = self._parse_float(self._get_val(row, col_map.get("cost_basis")))
            date_str = self._get_val(row, col_map.get("date")) or ""
            account = self._get_val(row, col_map.get("account")) or "Manual"

            if shares is None or shares <= 0:
                warnings.append(f"Row {row_count} ({ticker}): invalid shares, skipped")
                continue

            accounts_seen.add(account)
            positions.append(PositionCreate(
                ticker=ticker,
                shares=shares,
                cost_basis_per_share=cost or 0,
                date_acquired=date_str,
                account=account,
            ))

        return ImportPreview(
            positions=positions,
            account_count=len(accounts_seen),
            warnings=warnings,
            row_count=row_count,
        )

    async def import_positions(
        self, preview: ImportPreview, portfolio_service,
    ) -> ImportResult:
        """Execute import: create positions + lots + BUY transactions."""
        imported = 0
        skipped = 0
        warnings: list[str] = []

        for pos_data in preview.positions:
            try:
                await portfolio_service.add_position(pos_data)
                imported += 1
            except Exception as exc:
                skipped += 1
                warnings.append(f"{pos_data.ticker}: {exc}")

        return ImportResult(
            imported=imported,
            skipped=skipped,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _detect_columns(
        self, headers: list[str], broker: str,
    ) -> dict[str, str | None]:
        """Map logical field names to actual CSV column names."""
        mapping = COLUMN_MAPS.get(broker, COLUMN_MAPS["generic"])
        result: dict[str, str | None] = {}

        normalized = {h.strip().lower(): h for h in headers}

        for field, candidates in mapping.items():
            matched = None
            for candidate in candidates:
                if candidate.lower() in normalized:
                    matched = normalized[candidate.lower()]
                    break
            result[field] = matched

        return result

    @staticmethod
    def _get_val(row: dict, col: str | None) -> str | None:
        if col is None:
            return None
        val = row.get(col)
        if val is None:
            return None
        val = val.strip()
        return val if val else None

    @staticmethod
    def _parse_float(val: str | None) -> float | None:
        if val is None:
            return None
        # Remove currency symbols, commas, parens for negatives
        cleaned = re.sub(r'[$,]', '', val)
        cleaned = cleaned.strip()
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = '-' + cleaned[1:-1]
        try:
            return float(cleaned)
        except ValueError:
            return None
