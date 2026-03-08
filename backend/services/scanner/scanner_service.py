"""Scanner service — filter engine, text search, composite ranking.

Builds SQL queries dynamically against:
  - cache.financial_data  (income statement, balance sheet, cash flow, margins)
  - cache.market_data     (valuation multiples, price, volume)
  - companies             (ticker, name, sector, industry)
  - cache.filing_sections (text search on SEC filings)
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from db.connection import DatabaseConnection
from repositories.scanner_repo import ScannerRepo

from .metric_defs import SCANNER_METRICS, MetricDef, get_metric, list_metrics, list_categories
from .models import (
    FilterOperator, OPERATOR_SQL,
    ScannerFilter, ScannerRequest, ScannerResult, ScannerRow,
    TextSearchRequest, TextSearchHit,
    RankRequest, RankResult, RankingWeight,
    MetricDefinition,
)
from .presets import get_built_in_presets

logger = logging.getLogger("finance_app")


class ScannerService:
    """Orchestrates financial screening, text search, and ranking."""

    def __init__(self, db: DatabaseConnection, scanner_repo: ScannerRepo):
        self.db = db
        self.repo = scanner_repo

    # ==================================================================
    # Main scan (filters + optional text search)
    # ==================================================================

    async def scan(self, request: ScannerRequest) -> ScannerResult:
        """Run a combined filter + optional text search screen."""
        t0 = time.perf_counter()

        # --- Build base query ---
        select_cols, joins, wheres, params = self._build_base_query(request)

        # --- Apply metric filters ---
        percentile_filters: list[ScannerFilter] = []
        for f in request.filters:
            metric = get_metric(f.metric)
            if metric is None:
                continue
            if f.operator in (FilterOperator.TOP_PCT, FilterOperator.BOTTOM_PCT):
                percentile_filters.append(f)
                continue
            clause, filter_params = self._filter_to_sql(f, metric)
            if clause:
                wheres.append(clause)
                params.extend(filter_params)

        # --- Count total matches (before pagination) ---
        count_sql = f"""
            SELECT COUNT(DISTINCT c.ticker) as cnt
            FROM companies c
            {' '.join(joins)}
            {'WHERE ' + ' AND '.join(wheres) if wheres else ''}
        """
        count_row = await self.db.fetchone(count_sql, tuple(params))
        total = count_row["cnt"] if count_row else 0

        # --- Universe size ---
        universe_sql = "SELECT COUNT(*) as cnt FROM companies"
        if request.universe and request.universe != "all":
            universe_sql += " WHERE (universe_source = ? OR universe_tags LIKE ?)"
            univ_row = await self.db.fetchone(universe_sql, (request.universe, f"%{request.universe}%"))
        else:
            univ_row = await self.db.fetchone(universe_sql)
        universe_size = univ_row["cnt"] if univ_row else 0

        # --- Fetch results ---
        order_clause = self._build_order_clause(request)
        main_sql = f"""
            SELECT DISTINCT c.ticker, c.company_name, c.sector, c.industry,
                   {', '.join(select_cols)}
            FROM companies c
            {' '.join(joins)}
            {'WHERE ' + ' AND '.join(wheres) if wheres else ''}
            {order_clause}
            LIMIT ? OFFSET ?
        """
        params.extend([request.limit, request.offset])
        rows = await self.db.fetchall(main_sql, tuple(params))

        # --- Percentile filters (two-pass) ---
        if percentile_filters:
            rows = await self._apply_percentile_filters(rows, percentile_filters)
            total = len(rows)

        # --- Build result rows ---
        scanner_rows = self._rows_to_scanner_rows(rows)

        # --- Optional text search ---
        text_hits: list[TextSearchHit] = []
        text_count = 0
        if request.text_query:
            tickers_in_result = [r.ticker for r in scanner_rows]
            text_result = await self.text_search(TextSearchRequest(
                query=request.text_query,
                form_types=request.form_types,
                tickers=tickers_in_result if scanner_rows else None,
                limit=50,
            ))
            text_hits = text_result
            text_count = len(text_hits)

        elapsed = int((time.perf_counter() - t0) * 1000)

        return ScannerResult(
            rows=scanner_rows,
            total_matches=total,
            text_hits=text_hits,
            text_hit_count=text_count,
            applied_filters=len(request.filters),
            universe_size=universe_size,
            computation_time_ms=elapsed,
        )

    # ==================================================================
    # Text search on filing_sections
    # ==================================================================

    async def text_search(self, request: TextSearchRequest) -> list[TextSearchHit]:
        """Search filing section content using LIKE matching."""
        if not request.query or not request.query.strip():
            return []

        query_term = f"%{request.query.strip()}%"
        params: list[Any] = [query_term]

        ticker_clause = ""
        if request.tickers:
            placeholders = ", ".join("?" for _ in request.tickers)
            ticker_clause = f"AND fc.ticker IN ({placeholders})"
            params.extend(request.tickers)

        form_clause = ""
        if request.form_types:
            placeholders = ", ".join("?" for _ in request.form_types)
            form_clause = f"AND fc.form_type IN ({placeholders})"
            params.extend(request.form_types)

        sql = f"""
            SELECT
                fc.ticker,
                c.company_name,
                fc.form_type,
                fc.filing_date,
                fs.section_title,
                fs.content_text,
                fs.word_count
            FROM cache.filing_sections fs
            JOIN cache.filing_cache fc ON fs.filing_id = fc.id
            LEFT JOIN companies c ON fc.ticker = c.ticker
            WHERE fs.content_text LIKE ?
            {ticker_clause}
            {form_clause}
            ORDER BY fc.filing_date DESC
            LIMIT ?
        """
        params.append(request.limit)

        rows = await self.db.fetchall(sql, tuple(params))

        hits: list[TextSearchHit] = []
        for row in rows:
            snippet = self._extract_snippet(
                row.get("content_text", ""), request.query, context_chars=200
            )
            hits.append(TextSearchHit(
                ticker=row["ticker"],
                company_name=row.get("company_name"),
                form_type=row.get("form_type"),
                filing_date=row.get("filing_date"),
                section_title=row.get("section_title"),
                snippet=snippet,
                word_count=row.get("word_count"),
            ))

        return hits

    # ==================================================================
    # Composite ranking
    # ==================================================================

    async def composite_rank(self, request: RankRequest) -> RankResult:
        """Rank tickers by weighted composite score across multiple metrics."""
        if not request.weights:
            return RankResult()

        # Determine ticker universe
        if request.tickers:
            tickers = request.tickers
        else:
            rows = await self.db.fetchall("SELECT ticker FROM companies ORDER BY ticker")
            tickers = [r["ticker"] for r in rows]

        if not tickers:
            return RankResult()

        # Collect metric values for each ticker
        needed_metrics = {w.metric for w in request.weights}
        ticker_data: dict[str, dict[str, float | None]] = {t: {} for t in tickers}

        for metric_key in needed_metrics:
            metric = get_metric(metric_key)
            if metric is None:
                continue
            values = await self._fetch_metric_for_tickers(tickers, metric)
            for ticker, val in values.items():
                ticker_data[ticker][metric_key] = val

        # Percentile rank each metric (0 = worst, 1 = best)
        metric_ranks: dict[str, dict[str, float]] = {t: {} for t in tickers}
        for w in request.weights:
            vals = [(t, ticker_data[t].get(w.metric)) for t in tickers]
            vals_valid = [(t, v) for t, v in vals if v is not None]
            if not vals_valid:
                continue

            # Sort ascending by value
            vals_sorted = sorted(vals_valid, key=lambda x: x[1])
            n = len(vals_sorted)
            for rank_idx, (t, _) in enumerate(vals_sorted):
                pct_rank = rank_idx / max(n - 1, 1)
                # If ascending=True (lower is better), invert
                if w.ascending:
                    pct_rank = 1.0 - pct_rank
                metric_ranks[t][w.metric] = pct_rank

        # Weighted composite score
        total_weight = sum(w.weight for w in request.weights)
        scored: list[tuple[str, float]] = []
        for t in tickers:
            score = 0.0
            has_data = False
            for w in request.weights:
                r = metric_ranks[t].get(w.metric)
                if r is not None:
                    score += r * (w.weight / total_weight)
                    has_data = True
            if has_data:
                scored.append((t, round(score, 6)))

        # Sort by composite score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        scored = scored[:request.limit]

        # Fetch company info for result rows
        result_rows: list[ScannerRow] = []
        for rank_idx, (ticker, score) in enumerate(scored, 1):
            row = await self.db.fetchone(
                "SELECT company_name, sector, industry FROM companies WHERE ticker = ?",
                (ticker,),
            )
            result_rows.append(ScannerRow(
                ticker=ticker,
                company_name=row["company_name"] if row else None,
                sector=row["sector"] if row else None,
                industry=row["industry"] if row else None,
                metrics=ticker_data.get(ticker, {}),
                rank=rank_idx,
                composite_score=score,
            ))

        return RankResult(
            rows=result_rows,
            total=len(scored),
            weights_applied=request.weights,
        )

    # ==================================================================
    # Preset helpers
    # ==================================================================

    async def get_all_presets(self) -> list[dict]:
        """Get built-in + user-saved presets."""
        built_in = get_built_in_presets()
        saved = await self.repo.get_all_presets()
        user_presets = []
        for p in saved:
            user_presets.append({
                "id": p["id"],
                "name": p["name"],
                "is_built_in": False,
                "filters": json.loads(p["filters_json"]) if p.get("filters_json") else [],
                "text_query": p.get("query_text"),
                "sector_filter": p.get("sector_filter"),
                "universe": p.get("universe", "all"),
                "form_types": json.loads(p["form_types_json"]) if p.get("form_types_json") else ["10-K"],
            })
        return built_in + user_presets

    async def save_preset(self, data: dict) -> dict:
        """Save a user preset."""
        filters_json = json.dumps(data.get("filters", []))
        form_types_json = json.dumps(data.get("form_types", ["10-K"]))
        return await self.repo.create_preset({
            "name": data["name"],
            "query_text": data.get("text_query"),
            "filters_json": filters_json,
            "sector_filter": data.get("sector_filter", "All"),
            "universe": data.get("universe", "all"),
            "form_types_json": form_types_json,
        })

    async def delete_preset(self, preset_id: int) -> bool:
        """Delete a user preset."""
        return await self.repo.delete_preset(preset_id)

    # ==================================================================
    # Metrics catalog
    # ==================================================================

    def get_metrics_catalog(self) -> dict:
        """Return the full metrics catalog for the frontend."""
        return {
            "metrics": list_metrics(),
            "categories": list_categories(),
        }

    # ==================================================================
    # Internal: SQL building
    # ==================================================================

    def _build_base_query(
        self, request: ScannerRequest,
    ) -> tuple[list[str], list[str], list[str], list[Any]]:
        """Build SELECT columns, JOINs, WHERE clauses, and params."""
        select_cols: list[str] = []
        joins: list[str] = []
        wheres: list[str] = []
        params: list[Any] = []

        # Determine which tables we need
        needs_fd = False
        needs_md = False

        for f in request.filters:
            metric = get_metric(f.metric)
            if metric is None:
                continue
            if metric.db_table == "financial_data":
                needs_fd = True
            elif metric.db_table == "market_data":
                needs_md = True

        # Also check sort_by
        if request.sort_by:
            sm = get_metric(request.sort_by)
            if sm:
                if sm.db_table == "financial_data":
                    needs_fd = True
                elif sm.db_table == "market_data":
                    needs_md = True

        # Always join both for comprehensive results
        needs_fd = True
        needs_md = True

        if needs_fd:
            # Use a subquery to get the latest fiscal year per ticker
            joins.append("""
                LEFT JOIN (
                    SELECT fd1.*
                    FROM cache.financial_data fd1
                    INNER JOIN (
                        SELECT ticker, MAX(fiscal_year) as max_fy
                        FROM cache.financial_data
                        WHERE period_type = 'annual'
                        GROUP BY ticker
                    ) fd2 ON fd1.ticker = fd2.ticker AND fd1.fiscal_year = fd2.max_fy
                    WHERE fd1.period_type = 'annual'
                ) fd ON c.ticker = fd.ticker
            """)
            # Add common financial columns
            for col in [
                "revenue", "gross_profit", "ebit", "ebitda", "net_income",
                "eps_diluted", "gross_margin", "operating_margin", "net_margin",
                "ebitda_margin", "fcf_margin", "roe", "revenue_growth",
                "free_cash_flow", "operating_cash_flow", "capital_expenditure",
                "total_assets", "total_liabilities", "stockholders_equity",
                "total_debt", "net_debt", "debt_to_equity", "cash_and_equivalents",
                "working_capital", "shares_outstanding", "dividends_paid",
                "payout_ratio", "dividend_per_share",
            ]:
                select_cols.append(f"fd.{col}")

        if needs_md:
            joins.append("LEFT JOIN cache.market_data md ON c.ticker = md.ticker")
            for col in [
                "current_price", "market_cap", "enterprise_value",
                "pe_trailing", "pe_forward", "price_to_book", "price_to_sales",
                "ev_to_revenue", "ev_to_ebitda", "dividend_yield", "beta",
                "volume", "average_volume", "day_change_pct",
                "fifty_two_week_high", "fifty_two_week_low",
            ]:
                select_cols.append(f"md.{col}")

        # Universe filter — check both universe_source and universe_tags
        if request.universe and request.universe != "all":
            wheres.append("(c.universe_source = ? OR c.universe_tags LIKE ?)")
            params.extend([request.universe, f"%{request.universe}%"])

        # Sector filter
        if request.sector_filter and request.sector_filter != "All":
            wheres.append("c.sector = ?")
            params.append(request.sector_filter)

        # Industry filter
        if request.industry_filter:
            wheres.append("c.industry = ?")
            params.append(request.industry_filter)

        return select_cols, joins, wheres, params

    def _filter_to_sql(
        self, f: ScannerFilter, metric: MetricDef,
    ) -> tuple[str, list[Any]]:
        """Convert a ScannerFilter to a SQL WHERE clause + params."""
        col = self._metric_to_column(metric)
        params: list[Any] = []

        if f.operator in OPERATOR_SQL:
            op = OPERATOR_SQL[f.operator]
            if f.value is not None:
                return f"{col} {op} ?", [f.value]
            return "", []

        if f.operator == FilterOperator.BETWEEN:
            if f.low is not None and f.high is not None:
                return f"{col} BETWEEN ? AND ?", [f.low, f.high]
            return "", []

        if f.operator == FilterOperator.IN:
            if f.values:
                placeholders = ", ".join("?" for _ in f.values)
                return f"{col} IN ({placeholders})", list(f.values)
            return "", []

        # TOP_PCT / BOTTOM_PCT handled separately via percentile pass
        return "", []

    def _metric_to_column(self, metric: MetricDef) -> str:
        """Map a metric to its fully qualified SQL column reference."""
        if metric.db_table == "financial_data":
            return f"fd.{metric.db_column}"
        elif metric.db_table == "market_data":
            return f"md.{metric.db_column}"
        elif metric.db_table == "companies":
            return f"c.{metric.db_column}"
        return metric.db_column

    def _build_order_clause(self, request: ScannerRequest) -> str:
        """Build ORDER BY clause."""
        if request.sort_by:
            metric = get_metric(request.sort_by)
            if metric:
                col = self._metric_to_column(metric)
                direction = "DESC" if request.sort_desc else "ASC"
                return f"ORDER BY {col} {direction} NULLS LAST"
        return "ORDER BY c.ticker ASC"

    # ==================================================================
    # Internal: percentile filters (two-pass)
    # ==================================================================

    async def _apply_percentile_filters(
        self, rows: list[dict], filters: list[ScannerFilter],
    ) -> list[dict]:
        """Apply TOP_PCT / BOTTOM_PCT filters via percentile calculation."""
        for f in filters:
            metric = get_metric(f.metric)
            if metric is None or f.percentile is None:
                continue

            col_key = metric.db_column
            values = [r[col_key] for r in rows if r.get(col_key) is not None]
            if not values:
                continue

            values_sorted = sorted(values)
            n = len(values_sorted)

            if f.operator == FilterOperator.TOP_PCT:
                # Top N% = values above the (100-N)th percentile
                cutoff_idx = max(0, int(n * (1 - f.percentile / 100)))
                cutoff = values_sorted[cutoff_idx]
                rows = [r for r in rows if r.get(col_key) is not None and r[col_key] >= cutoff]

            elif f.operator == FilterOperator.BOTTOM_PCT:
                # Bottom N% = values below the Nth percentile
                cutoff_idx = min(n - 1, int(n * f.percentile / 100))
                cutoff = values_sorted[cutoff_idx]
                rows = [r for r in rows if r.get(col_key) is not None and r[col_key] <= cutoff]

        return rows

    # ==================================================================
    # Internal: fetch metric values
    # ==================================================================

    async def _fetch_metric_for_tickers(
        self, tickers: list[str], metric: MetricDef,
    ) -> dict[str, float | None]:
        """Fetch a single metric's value for a list of tickers."""
        if not tickers:
            return {}

        placeholders = ", ".join("?" for _ in tickers)

        if metric.db_table == "market_data":
            sql = f"""
                SELECT ticker, {metric.db_column}
                FROM cache.market_data
                WHERE ticker IN ({placeholders})
            """
            rows = await self.db.fetchall(sql, tuple(tickers))

        elif metric.db_table == "financial_data":
            sql = f"""
                SELECT fd1.ticker, fd1.{metric.db_column}
                FROM cache.financial_data fd1
                INNER JOIN (
                    SELECT ticker, MAX(fiscal_year) as max_fy
                    FROM cache.financial_data
                    WHERE period_type = 'annual' AND ticker IN ({placeholders})
                    GROUP BY ticker
                ) fd2 ON fd1.ticker = fd2.ticker AND fd1.fiscal_year = fd2.max_fy
                WHERE fd1.period_type = 'annual'
            """
            rows = await self.db.fetchall(sql, tuple(tickers))

        else:
            return {}

        return {r["ticker"]: r.get(metric.db_column) for r in rows}

    # ==================================================================
    # Internal: helpers
    # ==================================================================

    def _rows_to_scanner_rows(self, rows: list[dict]) -> list[ScannerRow]:
        """Convert raw DB rows to ScannerRow objects."""
        result: list[ScannerRow] = []
        # Columns that aren't metrics (company info)
        skip_keys = {"ticker", "company_name", "sector", "industry"}

        for row in rows:
            metrics = {}
            for key, val in row.items():
                if key in skip_keys:
                    continue
                if val is not None:
                    metrics[key] = val

            result.append(ScannerRow(
                ticker=row["ticker"],
                company_name=row.get("company_name"),
                sector=row.get("sector"),
                industry=row.get("industry"),
                metrics=metrics,
            ))
        return result

    @staticmethod
    def _extract_snippet(text: str, query: str, context_chars: int = 200) -> str:
        """Extract a text snippet around the first occurrence of query."""
        if not text or not query:
            return ""

        lower_text = text.lower()
        lower_query = query.lower()
        pos = lower_text.find(lower_query)

        if pos == -1:
            # Return first N chars as fallback
            return text[:context_chars * 2] + ("..." if len(text) > context_chars * 2 else "")

        start = max(0, pos - context_chars)
        end = min(len(text), pos + len(query) + context_chars)

        snippet = text[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."

        return snippet
