"""Brinson sector attribution analysis."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from db.connection import DatabaseConnection
from services.market_data_service import MarketDataService

from .models import SectorAttribution, AttributionResult

logger = logging.getLogger("finance_app")

# Approximate SPY sector weights (updated periodically)
DEFAULT_BENCH_SECTOR_WEIGHTS = {
    "Technology": 0.30,
    "Healthcare": 0.13,
    "Financial Services": 0.13,
    "Consumer Cyclical": 0.10,
    "Communication Services": 0.09,
    "Industrials": 0.08,
    "Consumer Defensive": 0.06,
    "Energy": 0.04,
    "Utilities": 0.03,
    "Real Estate": 0.02,
    "Basic Materials": 0.02,
}


class AttributionService:
    """Brinson sector attribution: allocation + selection + interaction."""

    def __init__(self, db: DatabaseConnection, market_data_svc: MarketDataService):
        self.db = db
        self.mds = market_data_svc

    async def compute_brinson_attribution(
        self, benchmark: str = "SPY", period: str = "1Y",
        account: str | None = None,
    ) -> AttributionResult:
        """Compute Brinson attribution by sector.

        allocation_effect = (w_p - w_b) * (R_b_sector - R_b_total)
        selection_effect  = w_b * (R_p_sector - R_b_sector)
        interaction_effect = (w_p - w_b) * (R_p_sector - R_b_sector)
        """
        # Get portfolio positions with sector info
        where = "WHERE p.account = ?" if account else ""
        params: tuple = (account,) if account else ()
        positions = await self.db.fetchall(
            f"""SELECT p.ticker, p.shares_held, c.sector
                FROM portfolio_positions p
                LEFT JOIN companies c ON p.ticker = c.ticker
                {where}""",
            params,
        )

        if not positions:
            return AttributionResult()

        # Compute portfolio sector weights and returns
        total_value = 0.0
        sector_data: dict[str, dict] = {}

        for pos in positions:
            ticker = pos["ticker"]
            sector = pos.get("sector") or "Unknown"
            shares = pos["shares_held"]

            quote = await self.mds.get_quote(ticker)
            price = quote.get("current_price", 0) if quote else 0
            value = shares * price
            total_value += value

            if sector not in sector_data:
                sector_data[sector] = {"value": 0, "tickers": []}
            sector_data[sector]["value"] += value
            sector_data[sector]["tickers"].append(ticker)

        if total_value <= 0:
            return AttributionResult()

        # Compute portfolio sector weights
        for s in sector_data:
            sector_data[s]["weight"] = sector_data[s]["value"] / total_value

        # Compute portfolio sector returns (simple: average day_change_pct)
        for s, sd in sector_data.items():
            returns = []
            for ticker in sd["tickers"]:
                q = await self.mds.get_quote(ticker)
                if q and q.get("day_change_pct") is not None:
                    returns.append(q["day_change_pct"] / 100 if abs(q["day_change_pct"]) > 1 else q["day_change_pct"])
            sd["return"] = sum(returns) / len(returns) if returns else 0

        # Benchmark sector weights & returns (using defaults)
        bench_weights = dict(DEFAULT_BENCH_SECTOR_WEIGHTS)
        bench_total_return = sum(
            w * sector_data.get(s, {}).get("return", 0)
            for s, w in bench_weights.items()
        )

        # All sectors (union of portfolio + benchmark)
        all_sectors = set(sector_data.keys()) | set(bench_weights.keys())

        sectors: list[SectorAttribution] = []
        total_alloc = 0.0
        total_select = 0.0
        total_interact = 0.0

        for sector in sorted(all_sectors):
            w_p = sector_data.get(sector, {}).get("weight", 0)
            w_b = bench_weights.get(sector, 0)
            r_p = sector_data.get(sector, {}).get("return", 0)
            r_b = r_p  # Simplified: use portfolio sector return as proxy

            alloc = (w_p - w_b) * (r_b - bench_total_return)
            select = w_b * (r_p - r_b)
            interact = (w_p - w_b) * (r_p - r_b)

            total_alloc += alloc
            total_select += select
            total_interact += interact

            sectors.append(SectorAttribution(
                sector=sector,
                port_weight=round(w_p, 4),
                bench_weight=round(w_b, 4),
                port_return=round(r_p, 4),
                bench_return=round(r_b, 4),
                allocation_effect=round(alloc, 6),
                selection_effect=round(select, 6),
                interaction_effect=round(interact, 6),
            ))

        return AttributionResult(
            sectors=sectors,
            total_allocation=round(total_alloc, 6),
            total_selection=round(total_select, 6),
            total_interaction=round(total_interact, 6),
            total_alpha=round(total_alloc + total_select + total_interact, 6),
        )
