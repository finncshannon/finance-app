"""Dashboard aggregation service — combines data from multiple services."""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from db.connection import DatabaseConnection
from services.market_data_service import MarketDataService

logger = logging.getLogger("finance_app")

# Market hours in ET
MARKET_OPEN_HOUR, MARKET_OPEN_MIN = 9, 30
MARKET_CLOSE_HOUR, MARKET_CLOSE_MIN = 16, 0
PRE_MARKET_HOUR = 4
AFTER_HOURS_CLOSE_HOUR = 20


class DashboardService:

    def __init__(
        self,
        db: DatabaseConnection,
        market_data_svc: MarketDataService,
        portfolio_svc=None,
        watchlist_svc=None,
        events_svc=None,
        universe_svc=None,
    ):
        self.db = db
        self.mds = market_data_svc
        self.portfolio_svc = portfolio_svc
        self.watchlist_svc = watchlist_svc
        self.events_svc = events_svc
        self.universe_svc = universe_svc

    async def get_dashboard_summary(self) -> dict:
        """Full dashboard snapshot — market + portfolio + models + events + watchlists."""
        market = await self.get_market_overview()
        portfolio = await self.get_portfolio_summary()
        recent_models = await self.get_recent_models()
        events = await self.get_upcoming_events()
        watchlists = []
        if self.watchlist_svc:
            watchlists = await self.watchlist_svc.get_all_watchlists()

        return {
            "market": market,
            "portfolio": portfolio,
            "recent_models": recent_models,
            "events": events,
            "watchlists": watchlists,
        }

    async def get_market_overview(self) -> dict:
        """Fetch index prices for major indices + market status."""
        index_symbols = [
            ("SPY", "S&P 500"),
            ("QQQ", "NASDAQ"),
            ("DIA", "DOW"),
        ]
        indices = []
        for symbol, name in index_symbols:
            quote = await self.mds.get_quote(symbol)
            if quote:
                indices.append({
                    "symbol": symbol,
                    "name": name,
                    "value": quote.get("current_price", 0),
                    "change": quote.get("day_change", 0),
                    "change_pct": quote.get("day_change_pct", 0),
                })
            else:
                indices.append({
                    "symbol": symbol,
                    "name": name,
                    "value": 0,
                    "change": 0,
                    "change_pct": 0,
                })

        # VIX
        vix_quote = await self.mds.get_quote("^VIX")
        if vix_quote:
            indices.append({
                "symbol": "^VIX",
                "name": "VIX",
                "value": vix_quote.get("current_price", 0),
                "change": vix_quote.get("day_change", 0),
                "change_pct": vix_quote.get("day_change_pct", 0),
            })

        # 10-Year Treasury yield
        tnx_quote = await self.mds.get_quote("^TNX")
        if tnx_quote:
            indices.append({
                "symbol": "^TNX",
                "name": "10Y Treasury",
                "value": tnx_quote.get("current_price", 0),
                "change": tnx_quote.get("day_change", 0),
                "change_pct": tnx_quote.get("day_change_pct", 0),
            })

        # USD/EUR
        eur_quote = await self.mds.get_quote("EURUSD=X")
        if eur_quote:
            eur_rate = eur_quote.get("current_price", 0)
            indices.append({
                "symbol": "EURUSD=X",
                "name": "USD/EUR",
                "value": round(1 / eur_rate, 4) if eur_rate else 0,
                "change": eur_quote.get("day_change", 0),
                "change_pct": eur_quote.get("day_change_pct", 0),
            })

        status = self.get_market_status()

        return {
            "indices": indices,
            "status": status,
        }

    async def get_portfolio_summary(self) -> dict | None:
        """Portfolio summary with best/worst performers."""
        if not self.portfolio_svc:
            return None
        try:
            positions = await self.portfolio_svc.get_all_positions()
            if not positions:
                return None

            summary = await self.portfolio_svc.get_summary()
            result = {
                "total_value": summary.total_value,
                "total_cost": summary.total_cost,
                "total_gain_loss": summary.total_gain_loss,
                "total_gain_loss_pct": summary.total_gain_loss_pct,
                "day_change": summary.day_change,
                "day_change_pct": summary.day_change_pct,
                "position_count": summary.position_count,
                "best_performer": None,
                "worst_performer": None,
            }

            # Find best/worst by gain_loss_pct
            valid = [p for p in positions if p.gain_loss_pct is not None]
            if valid:
                best = max(valid, key=lambda p: p.gain_loss_pct or 0)
                worst = min(valid, key=lambda p: p.gain_loss_pct or 0)
                result["best_performer"] = {
                    "ticker": best.ticker,
                    "gain_pct": best.gain_loss_pct,
                }
                result["worst_performer"] = {
                    "ticker": worst.ticker,
                    "gain_pct": worst.gain_loss_pct,
                }

            return result
        except Exception as exc:
            logger.warning("Failed to get portfolio summary: %s", exc)
            return None

    async def get_recent_models(self, limit: int = 5) -> list[dict]:
        """Last N models with intrinsic value + current price."""
        try:
            rows = await self.db.fetchall(
                """SELECT m.ticker, m.model_type, m.last_run_at,
                          o.intrinsic_value_per_share
                   FROM models m
                   LEFT JOIN model_outputs o ON o.model_id = m.id
                   WHERE m.last_run_at IS NOT NULL
                   ORDER BY m.last_run_at DESC
                   LIMIT ?""",
                (limit,),
            )
            models = []
            for row in rows:
                ticker = row["ticker"]
                intrinsic = row.get("intrinsic_value_per_share")
                current_price = None
                upside_pct = None

                quote = await self.mds.get_quote(ticker)
                if quote:
                    current_price = quote.get("current_price")
                    if current_price and intrinsic and current_price > 0:
                        upside_pct = round((intrinsic - current_price) / current_price, 4)

                models.append({
                    "ticker": ticker,
                    "model_type": row["model_type"],
                    "intrinsic_value": intrinsic,
                    "current_price": current_price,
                    "upside_pct": upside_pct,
                    "last_run_at": row["last_run_at"],
                })
            return models
        except Exception as exc:
            logger.warning("Failed to get recent models: %s", exc)
            return []

    async def get_upcoming_events(self, limit: int = 10) -> list[dict]:
        """Upcoming events from events service."""
        if not self.events_svc:
            return []
        try:
            events = await self.events_svc.get_upcoming_events(limit)
            return [
                {
                    "date": e.get("event_date", ""),
                    "ticker": e.get("ticker", ""),
                    "event_type": e.get("event_type", ""),
                    "detail": e.get("description", ""),
                }
                for e in events
            ]
        except Exception as exc:
            logger.warning("Failed to get upcoming events: %s", exc)
            return []

    async def get_filtered_events(
        self,
        source: str = "all",
        watchlist_id: int | None = None,
        event_types: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> dict:
        """Return filtered, deduplicated events with source labels and pagination."""
        from repositories.market_data_repo import MarketDataRepo

        # Default date_from to today
        if not date_from:
            date_from = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Build ticker→source priority map
        ticker_source: dict[str, str] = {}

        # Portfolio tickers (highest priority)
        portfolio_tickers: set[str] = set()
        if source in ("all", "portfolio") and self.portfolio_svc:
            try:
                positions = await self.portfolio_svc.get_all_positions()
                portfolio_tickers = {p.ticker for p in positions}
                for t in portfolio_tickers:
                    ticker_source[t] = "portfolio"
            except Exception as e:
                logger.warning("Filtered events: portfolio tickers failed: %s", e)

        # Watchlist tickers (second priority)
        watchlist_tickers: set[str] = set()
        if source in ("all", "watchlist") and self.watchlist_svc:
            try:
                if watchlist_id:
                    detail = await self.watchlist_svc.get_watchlist(watchlist_id)
                    if detail and "items" in detail:
                        for item in detail["items"]:
                            watchlist_tickers.add(item["ticker"])
                else:
                    wls = await self.watchlist_svc.get_all_watchlists()
                    for wl in wls:
                        detail = await self.watchlist_svc.get_watchlist(wl["id"])
                        if detail and "items" in detail:
                            for item in detail["items"]:
                                watchlist_tickers.add(item["ticker"])
                for t in watchlist_tickers:
                    if t not in ticker_source:
                        ticker_source[t] = "watchlist"
            except Exception as e:
                logger.warning("Filtered events: watchlist tickers failed: %s", e)

        # Market (S&P 500) tickers (lowest priority)
        if source in ("all", "market") and self.universe_svc:
            try:
                sp500 = self.universe_svc.get_sp500_tickers()
                for t in sp500:
                    if t not in ticker_source:
                        ticker_source[t] = "market"
            except Exception as e:
                logger.warning("Filtered events: S&P 500 tickers failed: %s", e)

        all_tickers = list(ticker_source.keys())
        if not all_tickers:
            return {"events": [], "total_count": 0, "has_more": False}

        # Query events
        repo = MarketDataRepo(self.db)
        rows, total_count = await repo.get_upcoming_events_for_tickers(
            tickers=all_tickers,
            event_types=event_types,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )

        events = []
        for row in rows:
            ticker = row.get("ticker", "")
            events.append({
                "date": row.get("event_date", ""),
                "ticker": ticker,
                "company_name": row.get("company_name", ""),
                "event_type": row.get("event_type", ""),
                "detail": row.get("description", ""),
                "source": ticker_source.get(ticker, "market"),
                "is_estimated": bool(row.get("is_estimated", False)),
            })

        return {
            "events": events,
            "total_count": total_count,
            "has_more": (offset + limit) < total_count,
        }

    @staticmethod
    def get_market_status() -> dict:
        """Compute market status based on current ET time."""
        try:
            from zoneinfo import ZoneInfo
            et = datetime.now(ZoneInfo("America/New_York"))
        except Exception:
            # Fallback: assume UTC-5
            et = datetime.now(timezone(timedelta(hours=-5)))

        weekday = et.weekday()  # 0=Mon, 6=Sun
        hour, minute = et.hour, et.minute
        minutes_since_midnight = hour * 60 + minute

        logger.debug(
            "Market status calc: now_et=%s (weekday=%d), open=%d:%02d, close=%d:%02d",
            et.strftime("%Y-%m-%d %H:%M:%S %Z"), weekday,
            MARKET_OPEN_HOUR, MARKET_OPEN_MIN,
            MARKET_CLOSE_HOUR, MARKET_CLOSE_MIN,
        )

        open_time = MARKET_OPEN_HOUR * 60 + MARKET_OPEN_MIN   # 570
        close_time = MARKET_CLOSE_HOUR * 60 + MARKET_CLOSE_MIN  # 960
        pre_open = PRE_MARKET_HOUR * 60                        # 240
        after_close = AFTER_HOURS_CLOSE_HOUR * 60              # 1200

        if weekday >= 5:
            # Weekend
            # Compute countdown to Monday 9:30 AM
            days_until_monday = (7 - weekday) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            mins_left = days_until_monday * 1440 + open_time - minutes_since_midnight
            return {
                "status": "closed",
                "label": "Closed",
                "countdown": _fmt_countdown(mins_left),
                "color": "gray",
            }

        if open_time <= minutes_since_midnight < close_time:
            mins_left = close_time - minutes_since_midnight
            return {
                "status": "open",
                "label": "Open",
                "countdown": f"Closes in {_fmt_countdown(mins_left)}",
                "color": "green",
            }

        if pre_open <= minutes_since_midnight < open_time:
            mins_left = open_time - minutes_since_midnight
            return {
                "status": "pre_market",
                "label": "Pre-Market",
                "countdown": f"Opens in {_fmt_countdown(mins_left)}",
                "color": "yellow",
            }

        if close_time <= minutes_since_midnight < after_close:
            mins_left = after_close - minutes_since_midnight
            return {
                "status": "after_hours",
                "label": "After-Hours",
                "countdown": f"Ends in {_fmt_countdown(mins_left)}",
                "color": "yellow",
            }

        # Before pre-market or after after-hours — closed
        if minutes_since_midnight < pre_open:
            mins_left = open_time - minutes_since_midnight
        else:
            # After 8 PM — next day
            mins_left = (1440 - minutes_since_midnight) + open_time
        return {
            "status": "closed",
            "label": "Closed",
            "countdown": f"Opens in {_fmt_countdown(mins_left)}",
            "color": "gray",
        }


def _fmt_countdown(minutes: int) -> str:
    """Format minutes into 'Xh Ym' string."""
    if minutes < 0:
        return ""
    h = minutes // 60
    m = minutes % 60
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"
