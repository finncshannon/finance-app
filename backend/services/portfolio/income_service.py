"""Enhanced income service — yield-on-cost, projections, dividend growth."""

import asyncio
import logging

from db.connection import DatabaseConnection
from repositories.portfolio_repo import PortfolioRepo
from services.market_data_service import MarketDataService

logger = logging.getLogger("finance_app")


class IncomeService:
    """Computes dividend income metrics for portfolio positions."""

    def __init__(
        self,
        db: DatabaseConnection,
        market_data_svc: MarketDataService,
        portfolio_repo: PortfolioRepo,
    ):
        self.db = db
        self.mds = market_data_svc
        self.repo = portfolio_repo

    async def get_enhanced_income(self, account: str | None = None) -> dict:
        """Enhanced income with yield-on-cost, projections, and growth."""
        positions = await self.repo.get_all_positions(account)

        income_positions: list[dict] = []
        total_annual_income = 0.0
        total_cost_basis = 0.0
        total_market_value = 0.0

        for pos in positions:
            ticker = pos["ticker"]
            shares = pos.get("shares_held", 0)
            cost_per_share = pos.get("cost_basis_per_share", 0)

            # Get dividend data from market_data cache
            md = await self.db.fetchone(
                "SELECT dividend_rate, dividend_yield, current_price FROM cache.market_data WHERE ticker = ?",
                (ticker,),
            )
            if not md or not md.get("dividend_rate"):
                continue  # Non-dividend position

            div_rate = md["dividend_rate"]  # Annual dividend per share
            current_price = md.get("current_price", 0)
            annual_income = div_rate * shares

            # Yield on cost
            yoc = div_rate / cost_per_share if cost_per_share > 0 else None

            # Market yield (for reference)
            market_yield = md.get("dividend_yield")  # Already decimal from Yahoo

            income_positions.append({
                "ticker": ticker,
                "shares": shares,
                "dividend_rate": round(div_rate, 4),
                "annual_income": round(annual_income, 2),
                "monthly_income": round(annual_income / 12, 2),
                "cost_basis_per_share": cost_per_share,
                "yield_on_cost": round(yoc, 6) if yoc is not None else None,
                "market_yield": market_yield,
                "current_price": current_price,
            })

            total_annual_income += annual_income
            total_cost_basis += cost_per_share * shares
            total_market_value += current_price * shares

        # Portfolio-level metrics
        portfolio_yoc = total_annual_income / total_cost_basis if total_cost_basis > 0 else None
        portfolio_yield = total_annual_income / total_market_value if total_market_value > 0 else None

        return {
            "positions": income_positions,
            "summary": {
                "total_annual_income": round(total_annual_income, 2),
                "total_monthly_income": round(total_annual_income / 12, 2),
                "projected_annual_income": round(total_annual_income, 2),
                "yield_on_cost": round(portfolio_yoc, 6) if portfolio_yoc else None,
                "yield_on_market": round(portfolio_yield, 6) if portfolio_yield else None,
                "dividend_position_count": len(income_positions),
                "total_position_count": len(positions),
            },
        }

    async def get_dividend_growth(self, ticker: str) -> float | None:
        """Calculate 5-year dividend CAGR for a ticker using historical dividend data."""
        try:
            import yfinance as yf

            def _fetch():
                t = yf.Ticker(ticker)
                divs = t.dividends
                if divs is None or len(divs) < 2:
                    return None
                # Get annual totals for last 5 years
                annual = divs.resample("YE").sum()
                if len(annual) < 2:
                    return None
                recent = annual.iloc[-1]
                oldest = annual.iloc[-min(5, len(annual))]
                years = min(5, len(annual) - 1)
                if oldest <= 0 or years <= 0:
                    return None
                cagr = (recent / oldest) ** (1 / years) - 1
                return float(cagr)

            return await asyncio.to_thread(_fetch)
        except Exception:
            return None
