"""Benchmark comparison service — portfolio vs benchmark TWR."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from db.connection import DatabaseConnection
from services.market_data_service import MarketDataService

from .models import BenchmarkResult, DailySnapshot
from .analytics import PortfolioAnalytics

logger = logging.getLogger("finance_app")


class BenchmarkService:
    """Compare portfolio returns against a benchmark (default: SPY)."""

    def __init__(self, db: DatabaseConnection, market_data_svc: MarketDataService):
        self.db = db
        self.mds = market_data_svc
        self.analytics = PortfolioAnalytics(db, market_data_svc)

    async def get_benchmark_comparison(
        self, benchmark: str = "SPY", period: str = "1Y",
        account: str | None = None,
    ) -> BenchmarkResult:
        """Compare portfolio TWR vs benchmark TWR over multiple periods."""
        today = date.today()
        periods_to_compute = ["1M", "3M", "6M", "YTD", "1Y"]

        # Get portfolio daily series for longest period
        start = self.analytics._period_start(today, "1Y")
        port_daily = await self.analytics.build_daily_valuation_series(
            start.isoformat(), today.isoformat(), account,
        )

        # Get benchmark daily series
        bench_daily = await self.get_benchmark_daily_series(
            benchmark, start.isoformat(), today.isoformat(),
        )

        # Compute TWR for each period
        period_results: dict[str, dict] = {}
        for p in periods_to_compute:
            p_start = self.analytics._period_start(today, p).isoformat()

            # Portfolio TWR for this period
            p_port = [d for d in port_daily if d.date >= p_start]
            p_port_vals = [d.portfolio_value for d in p_port]
            port_twr = self.analytics.compute_twr(p_port_vals) if len(p_port_vals) >= 2 else None

            # Benchmark TWR for this period
            p_bench = [d for d in bench_daily if d.date >= p_start]
            p_bench_vals = [d.portfolio_value for d in p_bench]
            bench_twr = self.analytics.compute_twr(p_bench_vals) if len(p_bench_vals) >= 2 else None

            alpha = None
            if port_twr is not None and bench_twr is not None:
                alpha = round(port_twr - bench_twr, 4)

            period_results[p] = {
                "portfolio": round(port_twr, 4) if port_twr is not None else None,
                "benchmark": round(bench_twr, 4) if bench_twr is not None else None,
                "alpha": alpha,
            }

        return BenchmarkResult(
            benchmark_ticker=benchmark,
            periods=period_results,
            portfolio_series=port_daily,
            benchmark_series=bench_daily,
        )

    async def get_benchmark_daily_series(
        self, ticker: str, start_date: str, end_date: str,
    ) -> list[DailySnapshot]:
        """Fetch benchmark price history, normalized to $100 base."""
        bars = await self.mds.get_historical(ticker, "5y")
        if not bars:
            return []

        # Filter to date range
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        filtered = [b for b in bars if start <= b.date <= end]

        if not filtered:
            return []

        # Normalize to base $100 for comparison
        base_price = filtered[0].close
        if base_price <= 0:
            return []

        return [
            DailySnapshot(
                date=bar.date.isoformat(),
                portfolio_value=round(100 * bar.close / base_price, 2),
            )
            for bar in filtered
        ]
