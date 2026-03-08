"""Comps Valuation Engine — Design Section 3.

Comparable company analysis with peer selection scoring,
Modified Z-Score outlier detection, aggregate multiples,
quality premium/discount, and football field visualization.
"""

from __future__ import annotations

import logging
import statistics

from .models import (
    CompsResult, CompsTableRow, MultipleStats, ImpliedValue,
    FootballField, FootballFieldRange, QualityAssessment,
    CompsMetadata,
)
from .engine_utils import (
    upside_downside, trimmed_mean, percentile, safe_div, clamp,
)
from services.assumption_engine.models import (
    AssumptionSet, CompsAssumptions,
)
from .base_model import BaseValuationModel

logger = logging.getLogger("finance_app")

# Multiples to compute
MULTIPLE_FIELDS = ["pe", "ev_ebitda", "ev_revenue", "pb", "p_fcf"]
MULTIPLE_LABELS = {
    "pe": "P/E",
    "ev_ebitda": "EV/EBITDA",
    "ev_revenue": "EV/Revenue",
    "pb": "P/B",
    "p_fcf": "P/FCF",
}


class CompsEngine(BaseValuationModel):
    """Comparable Company Analysis engine.

    Entry point: ``CompsEngine.run(assumption_set, data, current_price, peer_data)``
    """

    model_type = "comps"
    display_name = "Comps"

    @staticmethod
    def get_required_assumptions() -> list[str]:
        return ["model_assumptions.comps"]

    @staticmethod
    def validate_assumptions(assumption_set: AssumptionSet) -> list[str]:
        errors: list[str] = []
        if assumption_set.model_assumptions.comps is None:
            errors.append("Comps assumptions not set")
        return errors

    @staticmethod
    def run(
        assumption_set: AssumptionSet,
        data: dict,
        current_price: float,
        peer_data: list[dict] | None = None,
    ) -> CompsResult:
        """Run comps valuation."""
        ticker = assumption_set.ticker

        # Early return: no peers
        if not peer_data:
            return CompsResult(
                ticker=ticker,
                current_price=current_price,
                status="no_peers",
                peer_group={"peers": [], "count": 0},
                metadata=CompsMetadata(
                    warnings=["No peer companies available. Add peers to run comparisons."],
                ),
            )

        try:
            comps = assumption_set.model_assumptions.comps
            warnings: list[str] = []

            if comps is None:
                return CompsResult(
                    ticker=ticker, current_price=current_price,
                    status="no_peers",
                    peer_group={"peers": [], "count": 0},
                    metadata=CompsMetadata(warnings=["No comps assumptions available"]),
                )

            # --- 1. Build peer rows with multiples ---
            peers = CompsEngine._build_peer_rows(peer_data, warnings)
            if not peers:
                return CompsResult(
                    ticker=ticker, current_price=current_price,
                    status="no_peers",
                    peer_group={"peers": [], "count": 0},
                    metadata=CompsMetadata(warnings=["Could not build valid peer rows"]),
                )

            # --- 2. Score peers for similarity ---
            CompsEngine._score_peers(peers, data, comps)

            # --- 3. Outlier detection (Modified Z-Score) ---
            CompsEngine._flag_outliers(peers)

            # --- 4. Aggregate multiples (excluding outliers) ---
            agg = CompsEngine._aggregate_multiples(peers)

            # --- 5. Implied values for target ---
            implied = CompsEngine._compute_implied_values(
                agg, data, comps, current_price, warnings,
            )

            # --- 6. Quality assessment ---
            quality = CompsEngine._assess_quality(data, peers)

            # --- 7. Football field ---
            ff = CompsEngine._build_football_field(implied, quality, current_price)

            peer_group = {
                "peers": [p.model_dump() for p in peers],
                "count": len(peers),
            }

            return CompsResult(
                ticker=ticker,
                current_price=current_price,
                status="ready",
                peer_group=peer_group,
                aggregate_multiples={k: v for k, v in agg.items()},
                implied_values={k: v for k, v in implied.items()},
                quality_assessment=quality,
                football_field=ff,
                metadata=CompsMetadata(warnings=warnings),
            )
        except Exception as exc:
            logger.exception("Comps engine error for %s", ticker)
            return CompsResult(
                ticker=ticker,
                current_price=current_price,
                status="error",
                peer_group={"peers": [], "count": 0},
                metadata=CompsMetadata(warnings=[f"Comps analysis failed: {exc}"]),
            )

    # ------------------------------------------------------------------
    # 1. Build peer rows
    # ------------------------------------------------------------------

    @staticmethod
    def _build_peer_rows(
        peer_data: list[dict],
        warnings: list[str],
    ) -> list[CompsTableRow]:
        """Convert raw peer dicts into CompsTableRow objects with computed multiples."""
        rows: list[CompsTableRow] = []
        for p in peer_data:
            try:
                market_cap = p.get("market_cap") or 0
                ev = p.get("enterprise_value") or 0
                revenue = p.get("revenue") or 0
                ebitda = p.get("ebitda") or 0
                net_income = p.get("net_income") or 0
                fcf = p.get("free_cash_flow") or 0
                book_value = p.get("stockholders_equity") or 0

                row = CompsTableRow(
                    ticker=p.get("ticker", "???"),
                    company_name=p.get("company_name", ""),
                    market_cap=market_cap,
                    enterprise_value=ev,
                    revenue=revenue,
                    ebitda=ebitda,
                    net_income=net_income,
                    fcf=fcf,
                    book_value=book_value,
                    pe=safe_div(market_cap, net_income) if net_income > 0 else None,
                    ev_ebitda=safe_div(ev, ebitda) if ebitda > 0 else None,
                    ev_revenue=safe_div(ev, revenue) if revenue > 0 else None,
                    pb=safe_div(market_cap, book_value) if book_value > 0 else None,
                    p_fcf=safe_div(market_cap, fcf) if fcf > 0 else None,
                    revenue_growth=p.get("revenue_growth"),
                    operating_margin=p.get("operating_margin"),
                    roe=p.get("roe"),
                )
                rows.append(row)
            except Exception as exc:
                warnings.append(f"Skipped peer {p.get('ticker', '?')}: {exc}")
        return rows

    # ------------------------------------------------------------------
    # 2. Peer similarity scoring (4-factor)
    # ------------------------------------------------------------------

    @staticmethod
    def _score_peers(
        peers: list[CompsTableRow],
        data: dict,
        comps: CompsAssumptions,
    ) -> None:
        """Score each peer 0-1 based on sector, size, growth, margin similarity."""
        criteria = comps.peer_selection_criteria
        target_sector = criteria.get("sector", "")
        target_industry = criteria.get("industry", "")
        mcap_range = criteria.get("market_cap_range", [0, 1e18])
        rev_range = criteria.get("revenue_range", [0, 1e18])

        for peer in peers:
            score = 0.0

            # Factor 1: Industry / sector match (0.4 weight)
            # We don't have peer sector in data, so score based on presence
            score += 0.4  # Assume pre-screened peers are in similar sector

            # Factor 2: Market cap proximity (0.25 weight)
            if mcap_range[0] <= peer.market_cap <= mcap_range[1]:
                score += 0.25
            elif peer.market_cap > 0:
                mid = (mcap_range[0] + mcap_range[1]) / 2
                ratio = min(peer.market_cap, mid) / max(peer.market_cap, mid)
                score += 0.25 * ratio

            # Factor 3: Revenue proximity (0.20 weight)
            if rev_range[0] <= peer.revenue <= rev_range[1]:
                score += 0.20
            elif peer.revenue > 0:
                mid = (rev_range[0] + rev_range[1]) / 2
                ratio = min(peer.revenue, mid) / max(peer.revenue, mid)
                score += 0.20 * ratio

            # Factor 4: Growth similarity (0.15 weight)
            target_growth = comps.applicable_multiples.get("growth_rate")
            if peer.revenue_growth is not None and target_growth is not None:
                diff = abs(peer.revenue_growth - target_growth)
                score += 0.15 * max(0, 1.0 - diff * 5)
            else:
                score += 0.075  # Partial credit when data missing

            peer.peer_score = round(score, 4)

    # ------------------------------------------------------------------
    # 3. Outlier detection (Modified Z-Score using MAD)
    # ------------------------------------------------------------------

    @staticmethod
    def _flag_outliers(peers: list[CompsTableRow]) -> None:
        """Flag outlier multiples using Modified Z-Score (MAD)."""
        for field in MULTIPLE_FIELDS:
            values = [
                getattr(p, field) for p in peers
                if getattr(p, field) is not None
            ]
            if len(values) < 3:
                continue

            median_val = statistics.median(values)
            deviations = [abs(v - median_val) for v in values]
            mad = statistics.median(deviations)

            if mad == 0:
                continue

            for peer in peers:
                val = getattr(peer, field)
                if val is None:
                    continue
                mod_z = 0.6745 * (val - median_val) / mad
                if abs(mod_z) > 3.5:
                    peer.outlier_flags[field] = True

    # ------------------------------------------------------------------
    # 4. Aggregate multiples
    # ------------------------------------------------------------------

    @staticmethod
    def _aggregate_multiples(
        peers: list[CompsTableRow],
    ) -> dict[str, MultipleStats | None]:
        """Compute mean, median, trimmed mean for each multiple (excluding outliers)."""
        result: dict[str, MultipleStats | None] = {}

        for field in MULTIPLE_FIELDS:
            values = [
                getattr(p, field)
                for p in peers
                if (
                    getattr(p, field) is not None
                    and not p.outlier_flags.get(field, False)
                )
            ]
            if not values:
                result[field] = None
                continue

            result[field] = MultipleStats(
                mean=round(statistics.mean(values), 2),
                median=round(statistics.median(values), 2),
                trimmed_mean=round(trimmed_mean(values), 2),
                min=round(min(values), 2),
                max=round(max(values), 2),
                count=len(values),
            )

        return result

    # ------------------------------------------------------------------
    # 5. Implied values
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_implied_values(
        agg: dict[str, MultipleStats | None],
        data: dict,
        comps: CompsAssumptions,
        current_price: float,
        warnings: list[str],
    ) -> dict[str, ImpliedValue | None]:
        """Apply peer multiples to target company metrics → implied price."""
        latest = {}
        financials = data.get("annual_financials", [])
        if financials:
            latest = financials[-1]

        quote = data.get("quote_data", {})
        shares = latest.get("shares_outstanding") or 1
        net_debt = (latest.get("total_debt") or 0) - (latest.get("cash_and_equivalents") or 0)

        result: dict[str, ImpliedValue | None] = {}

        # Target metrics
        target_metrics = {
            "pe": latest.get("net_income"),
            "ev_ebitda": latest.get("ebitda"),
            "ev_revenue": latest.get("revenue"),
            "pb": latest.get("stockholders_equity"),
            "p_fcf": latest.get("free_cash_flow"),
        }

        ev_based = {"ev_ebitda", "ev_revenue"}

        for field in MULTIPLE_FIELDS:
            stats = agg.get(field)
            metric_val = target_metrics.get(field)

            if stats is None or metric_val is None or metric_val <= 0:
                result[field] = None
                continue

            multiple = stats.median
            premium_key = MULTIPLE_LABELS.get(field, field)
            premium = comps.premium_discount.get(premium_key, 0.0)
            adjusted_multiple = multiple * (1 + premium)

            if field in ev_based:
                # EV = multiple * metric → equity = EV - net_debt
                implied_ev = adjusted_multiple * metric_val
                implied_equity = implied_ev - net_debt
                raw_price = max(0, implied_equity / shares)
            else:
                # Market cap = multiple * metric
                implied_mcap = adjusted_multiple * metric_val
                raw_price = max(0, implied_mcap / shares)

            # Quality-adjusted price (same for now, quality applied later)
            quality_price = raw_price
            ud = upside_downside(quality_price, current_price)

            result[field] = ImpliedValue(
                raw_implied_price=round(raw_price, 2),
                quality_adjusted_price=round(quality_price, 2),
                multiple_used=round(adjusted_multiple, 2),
                target_metric_used=round(metric_val, 2),
                upside_downside_pct=round(ud, 4) if ud is not None else None,
            )

        return result

    # ------------------------------------------------------------------
    # 6. Quality assessment (6-factor Z-score)
    # ------------------------------------------------------------------

    @staticmethod
    def _assess_quality(
        data: dict,
        peers: list[CompsTableRow],
    ) -> QualityAssessment:
        """Compare target vs peer group on 6 quality factors."""
        latest = {}
        financials = data.get("annual_financials", [])
        if financials:
            latest = financials[-1]

        quote = data.get("quote_data", {})

        factor_scores: dict[str, float] = {}

        # Factors to compare: revenue_growth, operating_margin, roe
        factor_defs = {
            "revenue_growth": {
                "target": quote.get("revenue_growth") if isinstance(quote, dict) else None,
                "peers": [p.revenue_growth for p in peers if p.revenue_growth is not None],
            },
            "operating_margin": {
                "target": latest.get("operating_margin"),
                "peers": [p.operating_margin for p in peers if p.operating_margin is not None],
            },
            "roe": {
                "target": safe_div(
                    latest.get("net_income"),
                    latest.get("stockholders_equity"),
                ),
                "peers": [p.roe for p in peers if p.roe is not None],
            },
        }

        for factor_name, vals in factor_defs.items():
            target = vals["target"]
            peer_vals = vals["peers"]
            if target is not None and len(peer_vals) >= 2:
                mean = statistics.mean(peer_vals)
                stdev = statistics.stdev(peer_vals) if len(peer_vals) >= 3 else 0.01
                if stdev > 0:
                    z = (target - mean) / stdev
                    factor_scores[factor_name] = round(clamp(z, -3, 3), 4)

        # Composite adjustment: average Z-score × 0.10, clamped [-0.20, +0.20]
        if factor_scores:
            avg_z = statistics.mean(factor_scores.values())
            composite = clamp(avg_z * 0.10, -0.20, 0.20)
        else:
            composite = 0.0

        return QualityAssessment(
            factor_scores=factor_scores,
            composite_adjustment=round(composite, 4),
        )

    # ------------------------------------------------------------------
    # 7. Football field
    # ------------------------------------------------------------------

    @staticmethod
    def _build_football_field(
        implied: dict[str, ImpliedValue | None],
        quality: QualityAssessment,
        current_price: float,
    ) -> FootballField:
        """Build football field ranges from implied values."""
        ranges: list[FootballFieldRange] = []

        # Collect all non-None implied prices
        all_prices: list[float] = []
        for field, iv in implied.items():
            if iv is None:
                continue
            all_prices.append(iv.raw_implied_price)

        if not all_prices:
            return FootballField(current_price=current_price)

        # Build range per multiple
        for field in MULTIPLE_FIELDS:
            iv = implied.get(field)
            if iv is None:
                continue

            mid = iv.raw_implied_price
            # P25/P75 approximation: ±15% around mid
            low = mid * 0.85
            high = mid * 1.15
            adj_mid = mid * (1 + quality.composite_adjustment)

            ranges.append(FootballFieldRange(
                method=MULTIPLE_LABELS.get(field, field),
                low=round(low, 2),
                mid=round(mid, 2),
                high=round(high, 2),
                adjusted_mid=round(adj_mid, 2),
            ))

        return FootballField(current_price=current_price, ranges=ranges)
