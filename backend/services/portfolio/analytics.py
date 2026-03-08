"""Portfolio performance analytics — TWR, MWRR, risk metrics."""

from __future__ import annotations

import logging
import math
from datetime import date, timedelta

from db.connection import DatabaseConnection
from services.market_data_service import MarketDataService

from .models import DailySnapshot, CashFlow, PerformanceResult

logger = logging.getLogger("finance_app")

# Period definitions (approximate trading days)
PERIOD_DAYS = {
    "1M": 30, "3M": 90, "6M": 180, "YTD": None,
    "1Y": 365, "3Y": 1095, "5Y": 1825, "ALL": None,
}


class PortfolioAnalytics:
    """Compute TWR, MWRR, Sharpe, Sortino, drawdown, beta, volatility."""

    def __init__(self, db: DatabaseConnection, market_data_svc: MarketDataService):
        self.db = db
        self.mds = market_data_svc

    async def compute_performance(
        self, account: str | None = None, period: str = "1Y",
    ) -> PerformanceResult:
        """Compute full performance metrics for a given period."""
        today = date.today()
        start = self._period_start(today, period)

        # Build daily valuation series
        daily = await self.build_daily_valuation_series(
            start.isoformat(), today.isoformat(), account,
        )

        if len(daily) < 2:
            return PerformanceResult(daily_values=daily)

        values = [d.portfolio_value for d in daily]
        returns = self._daily_returns(values)

        # TWR across multiple periods
        twr_dict: dict[str, float | None] = {}
        for p in ["1M", "3M", "6M", "YTD", "1Y", "3Y", "ALL"]:
            p_start = self._period_start(today, p)
            p_daily = [d for d in daily if d.date >= p_start.isoformat()]
            if len(p_daily) >= 2:
                p_values = [d.portfolio_value for d in p_daily]
                twr_dict[p] = round(self.compute_twr(p_values), 4)
            else:
                twr_dict[p] = None

        # Cash flows for MWRR
        cash_flows = [CashFlow(date=d.date, amount=d.cash_flow) for d in daily if d.cash_flow != 0]
        ending_value = values[-1] if values else 0
        mwrr = self.compute_mwrr(cash_flows, ending_value, values[0] if values else 0)

        # Annualize MWRR
        days = (today - start).days
        mwrr_ann = ((1 + mwrr) ** (365 / max(days, 1)) - 1) if mwrr is not None else None

        # Benchmark returns for beta/tracking error
        bench_bars = await self.mds.get_historical("SPY", self._period_string(period))
        bench_returns = []
        if bench_bars and len(bench_bars) >= 2:
            bench_prices = [b.close for b in bench_bars]
            bench_returns = self._daily_returns(bench_prices)

        # Risk metrics
        rf_daily = 0.05 / 252  # Approximate 5% annual risk-free rate

        result = PerformanceResult(
            twr=twr_dict,
            mwrr=round(mwrr, 4) if mwrr is not None else None,
            mwrr_annualized=round(mwrr_ann, 4) if mwrr_ann is not None else None,
            sharpe_ratio=self._safe_round(self.compute_sharpe(returns, rf_daily)),
            sortino_ratio=self._safe_round(self.compute_sortino(returns, rf_daily)),
            max_drawdown=self._safe_round(self.compute_max_drawdown(values)),
            volatility=self._safe_round(self.compute_volatility(returns)),
            daily_values=daily,
        )

        if bench_returns and len(bench_returns) == len(returns):
            result.beta = self._safe_round(self.compute_beta(returns, bench_returns))
            result.tracking_error = self._safe_round(self.compute_tracking_error(returns, bench_returns))
            result.information_ratio = self._safe_round(self.compute_information_ratio(returns, bench_returns))

        return result

    # ==================================================================
    # Daily valuation series
    # ==================================================================

    async def build_daily_valuation_series(
        self, start_date: str, end_date: str, account: str | None = None,
    ) -> list[DailySnapshot]:
        """Build daily portfolio value from positions + historical prices.

        Simplified approach: uses current position snapshot × historical prices.
        """
        # Get current positions
        where = "WHERE account = ?" if account else ""
        params = (account,) if account else ()
        positions = await self.db.fetchall(
            f"SELECT ticker, shares_held FROM portfolio_positions {where} ORDER BY ticker",
            params,
        )

        if not positions:
            return []

        # Get historical prices for each ticker
        ticker_histories: dict[str, dict[str, float]] = {}
        for pos in positions:
            ticker = pos["ticker"]
            bars = await self.mds.get_historical(ticker, "5y")
            if bars:
                ticker_histories[ticker] = {
                    bar.date.isoformat(): bar.close for bar in bars
                }

        # Build date range
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        snapshots: list[DailySnapshot] = []
        current = start

        while current <= end:
            date_str = current.isoformat()
            total = 0.0
            has_data = False

            for pos in positions:
                ticker = pos["ticker"]
                shares = pos["shares_held"]
                history = ticker_histories.get(ticker, {})

                # Find the closest price on or before this date
                price = history.get(date_str)
                if price is None:
                    # Look back up to 5 days for weekends/holidays
                    for offset in range(1, 6):
                        check = (current - timedelta(days=offset)).isoformat()
                        price = history.get(check)
                        if price:
                            break

                if price:
                    total += shares * price
                    has_data = True

            if has_data:
                snapshots.append(DailySnapshot(
                    date=date_str,
                    portfolio_value=round(total, 2),
                ))

            current += timedelta(days=1)

        return snapshots

    # ==================================================================
    # Return calculations
    # ==================================================================

    @staticmethod
    def compute_twr(values: list[float]) -> float:
        """Time-Weighted Return: product of (1 + daily_return) - 1."""
        if len(values) < 2:
            return 0.0
        cumulative = 1.0
        for i in range(1, len(values)):
            if values[i - 1] > 0:
                daily_return = (values[i] - values[i - 1]) / values[i - 1]
                cumulative *= (1 + daily_return)
        return cumulative - 1

    @staticmethod
    def compute_mwrr(
        cash_flows: list[CashFlow], ending_value: float, starting_value: float,
    ) -> float | None:
        """Money-Weighted Return via bisection method IRR solver."""
        if starting_value <= 0:
            return None

        # Build flow list: negative = outflow (investment), positive = inflow
        flows = [(-starting_value, 0)]  # Initial investment at t=0

        if cash_flows:
            first_date = date.fromisoformat(cash_flows[0].date) if cash_flows else date.today()
            for cf in cash_flows:
                d = date.fromisoformat(cf.date)
                t = (d - first_date).days / 365.0
                flows.append((-cf.amount, t))

        # Ending value as final inflow
        last_t = flows[-1][1] if flows else 0
        flows.append((ending_value, last_t + 1.0 / 365))

        # Bisection IRR
        def npv(rate: float) -> float:
            return sum(amount / (1 + rate) ** t for amount, t in flows)

        low, high = -0.99, 10.0
        for _ in range(100):
            mid = (low + high) / 2
            val = npv(mid)
            if abs(val) < 0.01:
                return mid
            if val > 0:
                low = mid
            else:
                high = mid

        return (low + high) / 2

    # ==================================================================
    # Risk metrics
    # ==================================================================

    @staticmethod
    def compute_sharpe(returns: list[float], risk_free_rate: float) -> float | None:
        """(Mean Return - Rf) / StdDev(Returns), annualized."""
        if len(returns) < 2:
            return None
        mean_r = sum(returns) / len(returns)
        excess = [r - risk_free_rate for r in returns]
        std = math.sqrt(sum(x ** 2 for x in excess) / (len(excess) - 1))
        if std == 0:
            return None
        return ((mean_r - risk_free_rate) / std) * math.sqrt(252)

    @staticmethod
    def compute_sortino(returns: list[float], risk_free_rate: float) -> float | None:
        """(Mean Return - Rf) / Downside StdDev, annualized."""
        if len(returns) < 2:
            return None
        mean_r = sum(returns) / len(returns)
        downside = [min(0, r - risk_free_rate) ** 2 for r in returns]
        downside_dev = math.sqrt(sum(downside) / len(downside))
        if downside_dev == 0:
            return None
        return ((mean_r - risk_free_rate) / downside_dev) * math.sqrt(252)

    @staticmethod
    def compute_max_drawdown(values: list[float]) -> float | None:
        """Largest peak-to-trough decline as a fraction."""
        if len(values) < 2:
            return None
        peak = values[0]
        max_dd = 0.0
        for v in values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        return max_dd

    @staticmethod
    def compute_beta(
        portfolio_returns: list[float], benchmark_returns: list[float],
    ) -> float | None:
        """Cov(P, B) / Var(B)."""
        n = min(len(portfolio_returns), len(benchmark_returns))
        if n < 2:
            return None

        p = portfolio_returns[:n]
        b = benchmark_returns[:n]
        mean_p = sum(p) / n
        mean_b = sum(b) / n

        cov = sum((p[i] - mean_p) * (b[i] - mean_b) for i in range(n)) / (n - 1)
        var_b = sum((b[i] - mean_b) ** 2 for i in range(n)) / (n - 1)

        if var_b == 0:
            return None
        return cov / var_b

    @staticmethod
    def compute_volatility(returns: list[float]) -> float | None:
        """Annualized StdDev of daily returns."""
        if len(returns) < 2:
            return None
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        return math.sqrt(variance) * math.sqrt(252)

    @staticmethod
    def compute_tracking_error(
        port_returns: list[float], bench_returns: list[float],
    ) -> float | None:
        """StdDev(P - B), annualized."""
        n = min(len(port_returns), len(bench_returns))
        if n < 2:
            return None
        diffs = [port_returns[i] - bench_returns[i] for i in range(n)]
        mean_diff = sum(diffs) / n
        variance = sum((d - mean_diff) ** 2 for d in diffs) / (n - 1)
        return math.sqrt(variance) * math.sqrt(252)

    @staticmethod
    def compute_information_ratio(
        port_returns: list[float], bench_returns: list[float],
    ) -> float | None:
        """(Mean(P - B)) / TrackingError."""
        n = min(len(port_returns), len(bench_returns))
        if n < 2:
            return None
        diffs = [port_returns[i] - bench_returns[i] for i in range(n)]
        mean_diff = sum(diffs) / n
        variance = sum((d - mean_diff) ** 2 for d in diffs) / (n - 1)
        te = math.sqrt(variance) * math.sqrt(252)
        if te == 0:
            return None
        return (mean_diff * 252) / te

    # ==================================================================
    # Helpers
    # ==================================================================

    @staticmethod
    def _daily_returns(values: list[float]) -> list[float]:
        """Compute daily returns from a price series."""
        returns = []
        for i in range(1, len(values)):
            if values[i - 1] > 0:
                returns.append((values[i] - values[i - 1]) / values[i - 1])
        return returns

    @staticmethod
    def _period_start(today: date, period: str) -> date:
        days = PERIOD_DAYS.get(period)
        if period == "YTD":
            return date(today.year, 1, 1)
        if period == "ALL" or days is None:
            return today - timedelta(days=3650)  # ~10 years
        return today - timedelta(days=days)

    @staticmethod
    def _period_string(period: str) -> str:
        """Convert period to yfinance-compatible string."""
        mapping = {
            "1M": "1mo", "3M": "3mo", "6M": "6mo",
            "YTD": "ytd", "1Y": "1y", "3Y": "3y", "5Y": "5y", "ALL": "max",
        }
        return mapping.get(period, "1y")

    @staticmethod
    def _safe_round(val: float | None, decimals: int = 4) -> float | None:
        if val is None:
            return None
        return round(val, decimals)
