"""Data readiness service — analyses cached financial data against engine
dependency map and produces a structured readiness report per engine.

Used by the ``GET /api/v1/model-builder/{ticker}/data-readiness`` endpoint.
"""

import logging

from db.connection import DatabaseConnection
from repositories.market_data_repo import MarketDataRepo
from services.engine_dependency_map import (
    ENGINE_DEPENDENCIES,
    FINANCIAL_COLUMNS,
    KNOWN_DERIVATIONS,
)

logger = logging.getLogger("finance_app")

# Metadata columns excluded from coverage stats
_META_COLUMNS = frozenset(
    {"id", "ticker", "fiscal_year", "period_type", "statement_date", "data_source", "fetched_at"}
)


class DataReadinessService:
    """Checks a ticker's cached financial data against the engine dependency
    map and returns a per-engine readiness verdict."""

    def __init__(self, db: DatabaseConnection, model_detection_svc):
        self.db = db
        self.model_detection_svc = model_detection_svc
        self.market_repo = MarketDataRepo(db)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def get_readiness(self, ticker: str) -> dict:
        """Produce a full data-readiness report for *ticker*."""
        ticker = ticker.upper()

        # 1. Fetch financial rows (newest-first from repo)
        rows = await self.market_repo.get_financials(ticker, 10)
        market_data = await self.market_repo.get_market_data(ticker)

        # 2. Coverage stats (based on most recent year)
        most_recent = rows[0] if rows else {}
        total_fields = len(FINANCIAL_COLUMNS)
        populated = sum(
            1 for col in FINANCIAL_COLUMNS
            if most_recent.get(col) is not None
        )
        coverage_pct = round(populated / total_fields, 4) if total_fields else 0
        data_years = len(rows)

        # 3. Detection scores (may fail for empty tickers)
        detection_result = None
        detection_scores: dict[str, float | None] = {}
        try:
            det = await self.model_detection_svc.detect(ticker)
            detection_result = {
                "recommended_model": det.recommended_model,
                "confidence": det.confidence,
                "confidence_percentage": det.confidence_percentage,
            }
            detection_scores = {s.model_type: float(s.score) for s in det.scores}
        except Exception:
            logger.warning("Detection failed for %s — using null scores", ticker)

        # 4. Per-engine readiness
        engines: dict[str, dict] = {}
        for engine_name, tiers in ENGINE_DEPENDENCIES.items():
            engine_entry: dict = {
                "detection_score": detection_scores.get(engine_name),
            }

            all_statuses: dict[str, list] = {"critical": [], "important": [], "helpful": []}
            for tier_name in ("critical", "important", "helpful"):
                tier_fields = tiers.get(tier_name, [])
                field_results = []
                for dep in tier_fields:
                    status, years_avail, source = self._classify_field(dep["field"], rows)
                    field_results.append({
                        "field": dep["field"],
                        "label": dep["label"],
                        "reason": dep["reason"],
                        "status": status,
                        "years_available": years_avail,
                        "source": source,
                    })
                    all_statuses[tier_name].append(status)
                engine_entry[f"{tier_name}_fields"] = field_results

            verdict, verdict_label, missing_impact = self._determine_verdict(
                engine_name, all_statuses["critical"], all_statuses["important"],
                engine_entry.get("critical_fields", []),
                engine_entry.get("important_fields", []),
            )
            engine_entry["verdict"] = verdict
            engine_entry["verdict_label"] = verdict_label
            engine_entry["missing_impact"] = missing_impact

            engines[engine_name] = engine_entry

        # 5. Flat field_metadata map
        field_metadata = self._build_field_metadata(rows)

        return {
            "ticker": ticker,
            "data_years_available": data_years,
            "total_fields": total_fields,
            "populated_fields": populated,
            "coverage_pct": coverage_pct,
            "engines": engines,
            "field_metadata": field_metadata,
            "detection_result": detection_result,
            "market_data_available": market_data is not None,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _classify_field(
        self, field_name: str, rows: list[dict],
    ) -> tuple[str, int, str | None]:
        """Classify a single field across all financial rows.

        Returns ``(status, years_available, source_description)`` where
        *status* is ``"present"`` | ``"missing"`` | ``"derived"`` and
        *source_description* is ``"direct"`` / ``"computed from ..."`` / ``None``.
        """
        if not rows:
            return ("missing", 0, None)

        most_recent = rows[0]
        years_avail = sum(1 for r in rows if r.get(field_name) is not None)

        if most_recent.get(field_name) is not None:
            return ("present", years_avail, "direct")

        # Check if derivable from other present fields
        if field_name in KNOWN_DERIVATIONS:
            formula = KNOWN_DERIVATIONS[field_name]
            # Parse source fields from formula (simple token extraction)
            source_fields = [
                tok for tok in formula.replace("+", " ").replace("-", " ")
                    .replace("*", " ").replace("/", " ").split()
                if tok.isidentifier()
            ]
            if all(most_recent.get(sf) is not None for sf in source_fields):
                return ("derived", years_avail, f"computed from {formula}")

        return ("missing", years_avail, None)

    @staticmethod
    def _determine_verdict(
        engine_name: str,
        critical_statuses: list[str],
        important_statuses: list[str],
        critical_fields: list[dict],
        important_fields: list[dict],
    ) -> tuple[str, str, str | None]:
        """Return ``(verdict, verdict_label, missing_impact)``.

        - Any critical ``missing`` → ``not_possible``
        - Any important ``missing`` → ``partial``
        - Otherwise → ``ready``
        """
        missing_critical = [
            f for f, s in zip(critical_fields, critical_statuses) if s == "missing"
        ]
        missing_important = [
            f for f, s in zip(important_fields, important_statuses) if s == "missing"
        ]

        if missing_critical:
            names = ", ".join(f["label"] for f in missing_critical)
            impact = (
                f"Cannot run {engine_name.upper()} engine — missing critical data: {names}. "
                f"These fields are required and cannot be derived from other available data."
            )
            return ("not_possible", "Not Possible", impact)

        if missing_important:
            names = ", ".join(f["label"] for f in missing_important)
            impact = (
                f"{engine_name.upper()} can run but with reduced accuracy — "
                f"missing important data: {names}. "
                f"Results may be less reliable without these fields."
            )
            return ("partial", "Partial", impact)

        return ("ready", "Ready", None)

    def _build_field_metadata(self, rows: list[dict]) -> dict:
        """Build flat lookup map: every financial field → metadata dict.

        Each entry has ``status``, ``source``, ``source_detail``,
        ``years_available``, and ``engines`` (list of engines that use it).
        """
        # Pre-compute which engines use each field
        field_to_engines: dict[str, list[dict]] = {}
        for engine_name, tiers in ENGINE_DEPENDENCIES.items():
            for tier_name in ("critical", "important", "helpful"):
                for dep in tiers.get(tier_name, []):
                    field_to_engines.setdefault(dep["field"], []).append({
                        "engine": engine_name,
                        "level": tier_name,
                        "reason": dep["reason"],
                    })

        metadata: dict[str, dict] = {}
        for col in FINANCIAL_COLUMNS:
            status, years_avail, source = self._classify_field(col, rows)
            metadata[col] = {
                "status": status,
                "source": source,
                "source_detail": KNOWN_DERIVATIONS.get(col),
                "years_available": years_avail,
                "engines": field_to_engines.get(col, []),
            }

        return metadata
