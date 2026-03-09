"""Benchmark comparison service — portfolio vs benchmark TWR."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from db.connection import DatabaseConnection
from services.market_data_service import MarketDataService

from .models import BenchmarkResult, DailySnapshot
from .analytics import PortfolioAnalytics, SHORT_PERIODS, PERIOD_DAYS

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
        start = self.analytics._period_start(today, period)
        is_short = period in SHORT_PERIODS

        # Build series — hourly for short periods, daily otherwise
        if is_short:
            port_daily = await self.analytics.build_hourly_valuation_series(period, account)
            bench_daily = await self.get_benchmark_hourly_series(benchmark, period)
        else:
            port_daily = await self.analytics.build_daily_valuation_series(
                start.isoformat(), today.isoformat(), account,
            )
            bench_daily = await self.get_benchmark_daily_series(
                benchmark, start.isoformat(), today.isoformat(),
            )

        # Compute TWR for each standard period
        periods_to_compute = ["1M", "3M", "6M", "YTD", "1Y"]
        period_results: dict[str, dict] = {}
        for p in periods_to_compute:
            p_start = self.analytics._period_start(today, p).isoformat()

            p_port = [d for d in port_daily if d.date[:10] >= p_start]
            p_port_vals = [d.portfolio_value for d in p_port]
            port_twr = self.analytics.compute_twr(p_port_vals) if len(p_port_vals) >= 2 else None

            p_bench = [d for d in bench_daily if d.date[:10] >= p_start]
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

        # Filter to date range (compare as strings — both ISO format)
        filtered = [b for b in bars if start_date <= b.date <= end_date]

        if not filtered:
            return []

        # Normalize to base $100 for comparison
        base_price = filtered[0].close
        if base_price <= 0:
            return []

        return [
            DailySnapshot(
                date=bar.date,
                portfolio_value=round(100 * bar.close / base_price, 2),
            )
            for bar in filtered
        ]

    async def get_benchmark_hourly_series(
        self, ticker: str, period: str,
    ) -> list[DailySnapshot]:
        """Fetch benchmark hourly price history, normalized to $100 base."""
        bars = await self.mds.get_historical(ticker, "5d", "1h")
        if not bars:
            return []

        # Filter to requested period
        today = date.today()
        period_days = PERIOD_DAYS.get(period, 5)
        start_str = (today - timedelta(days=period_days)).isoformat()
        filtered = [b for b in bars if b.date[:10] >= start_str]

        if not filtered:
            return []

        base_price = filtered[0].close
        if base_price <= 0:
            return []

        return [
            DailySnapshot(
                date=bar.date,
                portfolio_value=round(100 * bar.close / base_price, 2),
            )
            for bar in filtered
        ]
