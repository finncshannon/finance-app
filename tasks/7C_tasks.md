# Session 7C — Events Backend (S&P 500 List, Background Fetcher, Filtered Endpoint)
## Phase 7: Dashboard

**Priority:** Normal
**Type:** Backend Only
**Depends On:** None (but note MASTER_INDEX recommends 9A runs first to create `sp500_tickers.json`; if 9A is not yet built, this session creates a minimal version of the S&P 500 list sufficient for Phase 7)
**Spec Reference:** `specs/phase7_dashboard.md` → Areas 2A, 2B, 2C

---

## SCOPE SUMMARY

Create a static S&P 500 ticker list as a JSON file, build a background event-fetching service that proactively fetches events for portfolio, watchlist, and S&P 500 tickers on startup, and upgrade the `/api/v1/dashboard/events` endpoint to accept source/type/date filters with deduplication.

---

## TASKS

### Task 1: Create S&P 500 Ticker List
**Description:** Ship a static JSON file containing ~503 S&P 500 ticker symbols with metadata. Add a service method to read it.

**Subtasks:**
- [ ] 1.1 — Create directory `backend/data/`
- [ ] 1.2 — Create `backend/data/sp500_tickers.json` — a JSON array of objects: `[{"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics"}, ...]` for all ~503 S&P 500 constituents. Source data from the current Wikipedia S&P 500 list.
- [ ] 1.3 — In `backend/services/universe_service.py`, add method `get_sp500_tickers() -> list[str]` that reads `sp500_tickers.json` from the `data/` directory and returns a list of ticker strings. Cache the result in memory after first read using a module-level variable.
- [ ] 1.4 — Add method `get_sp500_list() -> list[dict]` that returns the full list with metadata (ticker, name, sector, industry).

**Implementation Notes:**
- The `data/` directory is at `backend/data/` — it does not exist yet and needs to be created.
- `universe_service.py` currently uses `CompanyRepo` and `SECEdgarProvider`. The new methods should be standalone — they just read a JSON file, no DB or provider needed. Use `pathlib.Path(__file__).parent.parent / "data" / "sp500_tickers.json"` for the file path.
- The MASTER_INDEX notes that 9A will also create this file with DOW and Russell 3000 lists. If 9A runs after 7C, it should merge/overwrite — but for now, 7C creates the S&P 500 file and 9A will expand the data directory.

---

### Task 2: Background Event Fetcher
**Description:** On app startup, proactively fetch events for portfolio, watchlist, and S&P 500 tickers in the background.

**Subtasks:**
- [ ] 2.1 — In `backend/services/company_events_service.py`, add method `run_startup_fetch(portfolio_svc, watchlist_svc, universe_svc)`:
  - Fetch priority order: (1) portfolio tickers, (2) watchlist tickers, (3) S&P 500 tickers
  - For each ticker, check staleness: skip if the ticker has events in `company_events` table where `fetched_at` is within the last 7 days
  - For S&P 500 tickers: fetch sequentially with `asyncio.sleep(0.1)` (100ms) between each to avoid rate limiting
  - Log progress: `"Event refresh: {done}/{total} S&P 500 tickers ({stale} stale)"`
  - Wrap entire method in try/except so failures don't crash the app
- [ ] 2.2 — Add staleness check method `_is_stale(ticker: str, max_age_days: int = 7) -> bool` to `CompanyEventsService`:
  - Query `cache.company_events` for the most recent `fetched_at` for the ticker
  - Return True if no events exist or if `fetched_at` is older than `max_age_days` days
- [ ] 2.3 — Add method `get_tickers_needing_refresh(tickers: list[str], max_age_days: int = 7) -> list[str]` that batch-checks staleness for a list of tickers and returns only the stale ones.
- [ ] 2.4 — In `backend/main.py`, in the `lifespan` function, after all services are initialized but before `yield`, add:
  ```python
  asyncio.create_task(
      events_svc.run_startup_fetch(portfolio_svc, watchlist_svc, universe_svc)
  )
  ```
  This runs in the background — it does not block app startup.
- [ ] 2.5 — Add instance variable `self._refresh_progress: dict` to `CompanyEventsService` to track background fetch progress: `{"phase": "portfolio"|"watchlist"|"sp500"|"idle", "done": int, "total": int, "stale_count": int}`. Initialize to `{"phase": "idle", "done": 0, "total": 0, "stale_count": 0}`.

**Implementation Notes:**
- Portfolio tickers: get from `portfolio_svc.get_all_positions()` → extract unique tickers.
- Watchlist tickers: get from `watchlist_svc.get_all_watchlists()` → for each, get items → extract tickers. Or add a `get_all_tickers()` convenience method.
- S&P 500 tickers: get from `universe_svc.get_sp500_tickers()`.
- Deduplication: combine all three lists into a single set to avoid fetching the same ticker twice. Process in priority order: portfolio first, then watchlist-only tickers, then sp500-only tickers.
- Cold start (empty cache): first run fetches all ~503 S&P 500 tickers — at 100ms delay = ~50 seconds. Subsequent runs only refresh stale entries.
- The `company_events_service.py` already has `fetch_events(ticker)` and `fetch_events_batch(tickers)`. The new `run_startup_fetch` should reuse `fetch_events()` per ticker with the delay.

---

### Task 3: Refresh Status Endpoint
**Description:** Expose the background fetch progress to the frontend via a new endpoint.

**Subtasks:**
- [ ] 3.1 — In `backend/routers/dashboard_router.py`, add endpoint `GET /api/v1/dashboard/events/refresh-status` that returns the `_refresh_progress` dict from `CompanyEventsService`.

**Implementation Notes:**
- Access the events service via `request.app.state.company_events_service`.
- Response format: `{"phase": "sp500", "done": 47, "total": 503, "stale_count": 312}`
- When idle: `{"phase": "idle", "done": 0, "total": 0, "stale_count": 0}`

---

### Task 4: Filtered Events Endpoint
**Description:** Upgrade the existing `/api/v1/dashboard/events` endpoint to support source, type, date, and pagination filters.

**Subtasks:**
- [ ] 4.1 — In `backend/routers/dashboard_router.py`, update the `GET /api/v1/dashboard/events` endpoint to accept query parameters:
  - `source`: `watchlist` | `portfolio` | `market` | `all` (default: `all`)
  - `watchlist_id`: optional int, filters to specific watchlist (only when source=watchlist)
  - `event_types`: optional comma-separated string, e.g. `earnings,ex_dividend` (default: all)
  - `date_from`: optional ISO date string (default: today)
  - `date_to`: optional ISO date string (default: none)
  - `limit`: int (default: 10)
  - `offset`: int (default: 0)
- [ ] 4.2 — In `backend/services/dashboard_service.py`, add method `get_filtered_events(source, watchlist_id, event_types, date_from, date_to, limit, offset)`:
  - Resolve source to ticker list:
    - `portfolio` → get tickers from portfolio positions
    - `watchlist` → get tickers from specified watchlist (or all watchlists if no ID)
    - `market` → get tickers from `sp500_tickers.json`
    - `all` → union of all three
  - Query `cache.company_events` filtering by ticker list, event types, date range
  - Deduplicate: if a ticker appears in multiple sources, assign priority: portfolio > watchlist > market
  - Return events with a `source` field indicating where the ticker comes from
  - Return `total_count` for pagination and `has_more` boolean
- [ ] 4.3 — In `backend/repositories/market_data_repo.py`, add method `get_upcoming_events_for_tickers(tickers: list[str], event_types: list[str] | None, date_from: str, date_to: str | None, limit: int, offset: int) -> tuple[list[dict], int]`:
  - Build dynamic SQL with ticker IN clause, optional event_type filter, date range
  - Return (events_list, total_count)
  - Sort by event_date ASC

**Implementation Notes:**
- The existing `get_upcoming_events(limit)` in `dashboard_service.py` should remain for backward compatibility but the new method is the primary path.
- Source resolution requires access to `portfolio_svc`, `watchlist_svc`, and `universe_svc`. These are already available on `DashboardService` (portfolio_svc and watchlist_svc are injected; universe_svc will need to be added to the constructor or accessed via app.state).
- Response format per event:
  ```json
  {
    "date": "2026-03-10",
    "ticker": "AAPL",
    "event_type": "earnings",
    "detail": "Earnings (est. EPS 2.35)",
    "source": "portfolio",
    "is_estimated": true
  }
  ```
- Deduplication priority: when building the ticker→source map, process portfolio tickers first, then watchlist (only those not in portfolio), then market (only those not in portfolio or watchlist).

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: `backend/data/sp500_tickers.json` exists and contains ~503 S&P 500 tickers with name, sector, industry metadata.
- [ ] AC-2: `universe_service.get_sp500_tickers()` returns a list of ~503 ticker strings.
- [ ] AC-3: `universe_service.get_sp500_list()` returns full metadata objects.
- [ ] AC-4: S&P 500 list is cached in memory after first read (not re-read from disk on every call).
- [ ] AC-5: On app startup, `run_startup_fetch()` is called as a background task (does not block health endpoint).
- [ ] AC-6: Background fetch processes portfolio tickers first, then watchlist, then S&P 500.
- [ ] AC-7: Staleness check skips tickers with events fetched within 7 days.
- [ ] AC-8: S&P 500 fetch includes 100ms delay between each ticker to avoid rate limiting.
- [ ] AC-9: Background fetch logs progress including ticker count and stale count.
- [ ] AC-10: Background fetch failures don't crash the app — all errors are caught and logged.
- [ ] AC-11: `GET /api/v1/dashboard/events/refresh-status` returns current progress of background fetch.
- [ ] AC-12: `GET /api/v1/dashboard/events` accepts `source`, `watchlist_id`, `event_types`, `date_from`, `date_to`, `limit`, `offset` query params.
- [ ] AC-13: Source filter correctly resolves tickers: `portfolio` = portfolio positions, `watchlist` = watchlist items, `market` = S&P 500 list.
- [ ] AC-14: Events are deduplicated: a ticker in multiple sources appears once with highest-priority source label (portfolio > watchlist > market).
- [ ] AC-15: Response includes `total_count` and `has_more` for frontend pagination.
- [ ] AC-16: Each event includes a `source` field (`portfolio`, `watchlist`, or `market`).
- [ ] AC-17: Each event includes an `is_estimated` field (boolean).
- [ ] AC-18: Default `date_from` is today when not specified.
- [ ] AC-19: Existing `/api/v1/dashboard/summary` endpoint continues to work (backward compatible).
- [ ] AC-20: `backend/data/` directory is created.

---

## FILES TOUCHED

**New files:**
- `backend/data/sp500_tickers.json` — static S&P 500 ticker list with metadata (~503 entries)

**Modified files:**
- `backend/services/universe_service.py` — add `get_sp500_tickers()`, `get_sp500_list()` with in-memory cache
- `backend/services/company_events_service.py` — add `run_startup_fetch()`, `_is_stale()`, `get_tickers_needing_refresh()`, `_refresh_progress` tracking
- `backend/services/dashboard_service.py` — add `get_filtered_events()` with source resolution, deduplication, pagination; accept `universe_svc` in constructor
- `backend/repositories/market_data_repo.py` — add `get_upcoming_events_for_tickers()` with dynamic SQL filtering
- `backend/routers/dashboard_router.py` — upgrade `GET /events` with query params, add `GET /events/refresh-status`
- `backend/main.py` — add `asyncio.create_task()` for startup event fetch, pass `universe_svc` to `DashboardService`

---

## BUILDER PROMPT

> **Session 7C — Events Backend (S&P 500 List, Background Fetcher, Filtered Endpoint)**
>
> You are building session 7C of the Finance App v2.0 update.
>
> **What you're doing:** Creating a static S&P 500 ticker list, building a background event-fetching service for proactive startup data loading, and upgrading the events API endpoint to support source/type/date filtering with pagination.
>
> **Context:** The app currently fetches company events (earnings dates, ex-dividend dates) from Yahoo Finance via `CompanyEventsService` only on-demand when a user researches a ticker. The dashboard shows a flat unfiltered list from cache. You're building proactive background fetching and filtered queries so the dashboard has rich, filterable event data immediately.
>
> **Existing code you need to know:**
> - `backend/services/company_events_service.py` — has `fetch_events(ticker)`, `fetch_events_batch(tickers)`, `get_upcoming_events(limit)`, `get_events_for_ticker(ticker)`. Uses `MarketDataRepo.upsert_event()` and `MarketDataRepo.get_upcoming_events()`.
> - `backend/services/dashboard_service.py` — `DashboardService` class with `get_dashboard_summary()`, `get_upcoming_events(limit=10)`. Constructor takes `db, market_data_svc, portfolio_svc=None, watchlist_svc=None, events_svc=None`.
> - `backend/services/universe_service.py` — `UniverseService` class with `load_universe()`, `get_universe_tickers()`. Uses `CompanyRepo` and `SECEdgarProvider`. You're adding S&P 500 JSON reading methods here.
> - `backend/repositories/market_data_repo.py` — has `get_upcoming_events(limit)`, `upsert_event(data)`, `get_events(ticker)`. Events table: `cache.company_events` with columns `ticker, event_type, event_date, event_time, description, amount, is_estimated, source, fetched_at`. Unique constraint on `(ticker, event_type, event_date)`.
> - `backend/routers/dashboard_router.py` — has `GET /api/v1/dashboard/events` (currently just takes `limit` param), and various watchlist endpoints.
> - `backend/main.py` — lifespan function initializes all services and stores on `app.state`. Current services on app.state: `settings_service`, `market_data_service`, `company_events_service`, `dashboard_service`, `watchlist_service`, `universe_service`, `portfolio_service`, etc.
> - The `backend/data/` directory does NOT exist yet — you need to create it.
>
> **Cross-cutting rules:**
> - Display Name Rule: All backend snake_case keys displayed in the UI must use the shared `displayNames.ts` utility. Never show raw keys. Never use inline `.replace(/_/g, ' ')`. Import from `@/utils/displayNames`. (Backend-only session, but ensure `event_type` values are consistent snake_case: `earnings`, `ex_dividend`.)
> - Chart Quality: All charts must meet Fidelity/Yahoo Finance information-density standards.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%).
> - Scenario Order: Bear / Base / Bull (left to right), Base default.
>
> **Task 1: Create S&P 500 Ticker List**
>
> Create `backend/data/` directory.
> Create `backend/data/sp500_tickers.json` with all ~503 S&P 500 constituents:
> ```json
> [
>   {"ticker": "AAPL", "name": "Apple Inc.", "sector": "Technology", "industry": "Consumer Electronics"},
>   {"ticker": "MSFT", "name": "Microsoft Corp.", "sector": "Technology", "industry": "Software"},
>   ...
> ]
> ```
> Use the current S&P 500 composition. Include all ~503 tickers (some companies have multiple share classes).
>
> In `backend/services/universe_service.py`, add:
> ```python
> import json
> from pathlib import Path
>
> _sp500_cache: list[dict] | None = None
> _sp500_tickers_cache: list[str] | None = None
>
> # Add these as standalone module-level functions OR as static/class methods on UniverseService:
>
> def get_sp500_tickers() -> list[str]:
>     global _sp500_tickers_cache
>     if _sp500_tickers_cache is None:
>         data = _load_sp500_json()
>         _sp500_tickers_cache = [item["ticker"] for item in data]
>     return _sp500_tickers_cache
>
> def get_sp500_list() -> list[dict]:
>     global _sp500_cache
>     if _sp500_cache is None:
>         _sp500_cache = _load_sp500_json()
>     return _sp500_cache
>
> def _load_sp500_json() -> list[dict]:
>     path = Path(__file__).parent.parent / "data" / "sp500_tickers.json"
>     with open(path, "r") as f:
>         return json.load(f)
> ```
> Prefer adding these as methods on `UniverseService` with instance-level caching rather than module globals, since the class is already instantiated as a singleton.
>
> **Task 2: Background Event Fetcher**
>
> In `backend/services/company_events_service.py`, add to `CompanyEventsService`:
>
> ```python
> def __init__(self, db, market_data_svc):
>     # ... existing init ...
>     self._refresh_progress = {"phase": "idle", "done": 0, "total": 0, "stale_count": 0}
>
> async def _is_stale(self, ticker: str, max_age_days: int = 7) -> bool:
>     """Check if events for ticker need refreshing."""
>     row = await self.market_repo.db.fetchone(
>         """SELECT MAX(fetched_at) as last_fetch
>            FROM cache.company_events WHERE ticker = ?""",
>         (ticker.upper(),),
>     )
>     if not row or not row["last_fetch"]:
>         return True
>     from datetime import datetime, timezone, timedelta
>     last = datetime.fromisoformat(row["last_fetch"])
>     return (datetime.now(timezone.utc) - last) > timedelta(days=max_age_days)
>
> async def get_tickers_needing_refresh(self, tickers: list[str], max_age_days: int = 7) -> list[str]:
>     """Return subset of tickers whose events are stale."""
>     stale = []
>     for t in tickers:
>         if await self._is_stale(t, max_age_days):
>             stale.append(t)
>     return stale
>
> async def run_startup_fetch(self, portfolio_svc, watchlist_svc, universe_svc):
>     """Background task: proactively fetch events for portfolio, watchlist, S&P 500."""
>     try:
>         # 1. Gather all tickers by source
>         portfolio_tickers = set()
>         watchlist_tickers = set()
>         sp500_tickers = set()
>
>         try:
>             positions = await portfolio_svc.get_all_positions()
>             portfolio_tickers = {p.ticker for p in positions}
>         except Exception as e:
>             logger.warning("Startup fetch: failed to get portfolio tickers: %s", e)
>
>         try:
>             wls = await watchlist_svc.get_all_watchlists()
>             for wl in wls:
>                 detail = await watchlist_svc.get_watchlist(wl["id"])
>                 if detail and "items" in detail:
>                     for item in detail["items"]:
>                         watchlist_tickers.add(item["ticker"])
>         except Exception as e:
>             logger.warning("Startup fetch: failed to get watchlist tickers: %s", e)
>
>         try:
>             sp500_tickers = set(universe_svc.get_sp500_tickers())
>         except Exception as e:
>             logger.warning("Startup fetch: failed to get S&P 500 tickers: %s", e)
>
>         # 2. Deduplicate: process in priority order
>         # Phase 1: Portfolio
>         await self._fetch_phase("portfolio", list(portfolio_tickers))
>
>         # Phase 2: Watchlist (exclude portfolio tickers)
>         wl_only = watchlist_tickers - portfolio_tickers
>         await self._fetch_phase("watchlist", list(wl_only))
>
>         # Phase 3: S&P 500 (exclude portfolio + watchlist)
>         sp_only = sp500_tickers - portfolio_tickers - watchlist_tickers
>         await self._fetch_phase("sp500", list(sp_only), delay_ms=100)
>
>         self._refresh_progress = {"phase": "idle", "done": 0, "total": 0, "stale_count": 0}
>         logger.info("Startup event fetch complete.")
>
>     except Exception as exc:
>         logger.error("Startup event fetch failed: %s", exc)
>         self._refresh_progress["phase"] = "idle"
>
> async def _fetch_phase(self, phase_name: str, tickers: list[str], delay_ms: int = 0):
>     """Fetch events for a list of tickers, updating progress."""
>     stale = await self.get_tickers_needing_refresh(tickers)
>     self._refresh_progress = {
>         "phase": phase_name,
>         "done": 0,
>         "total": len(stale),
>         "stale_count": len(stale),
>     }
>     logger.info("Event refresh [%s]: %d/%d tickers stale", phase_name, len(stale), len(tickers))
>
>     for i, ticker in enumerate(stale):
>         try:
>             await self.fetch_events(ticker)
>         except Exception as e:
>             logger.debug("Event fetch failed for %s: %s", ticker, e)
>         self._refresh_progress["done"] = i + 1
>         if delay_ms > 0:
>             await asyncio.sleep(delay_ms / 1000)
> ```
>
> In `backend/main.py`, in the lifespan function, after all services are initialized and before `yield`:
> ```python
> # Background event fetch (non-blocking)
> asyncio.create_task(
>     events_svc.run_startup_fetch(portfolio_svc, watchlist_svc, universe_svc)
> )
> logger.info("Background event fetch task started.")
> ```
> Note: `events_svc` is the `company_events_service`, `portfolio_svc` is `portfolio_service`, `watchlist_svc` is `watchlist_service`, `universe_svc` is `universe_service`. All are already on `app.state`.
>
> **Task 3: Refresh Status Endpoint**
>
> In `backend/routers/dashboard_router.py`, add:
> ```python
> @router.get("/events/refresh-status")
> async def get_events_refresh_status(request: Request):
>     try:
>         svc = request.app.state.company_events_service
>         return success_response(data=svc._refresh_progress)
>     except Exception as exc:
>         return error_response("REFRESH_STATUS_ERROR", str(exc))
> ```
> IMPORTANT: Place this route BEFORE the existing `/events` route to avoid path conflicts.
>
> **Task 4: Filtered Events Endpoint**
>
> Update the `GET /api/v1/dashboard/events` endpoint in `dashboard_router.py`:
> ```python
> @router.get("/events")
> async def get_events(
>     request: Request,
>     source: str = "all",
>     watchlist_id: int | None = None,
>     event_types: str | None = None,
>     date_from: str | None = None,
>     date_to: str | None = None,
>     limit: int = 10,
>     offset: int = 0,
> ):
>     try:
>         svc = _dashboard(request)
>         types_list = event_types.split(",") if event_types else None
>         result = await svc.get_filtered_events(
>             source=source,
>             watchlist_id=watchlist_id,
>             event_types=types_list,
>             date_from=date_from,
>             date_to=date_to,
>             limit=limit,
>             offset=offset,
>         )
>         return success_response(data=result)
>     except Exception as exc:
>         return error_response("EVENTS_ERROR", str(exc))
> ```
>
> In `backend/services/dashboard_service.py`:
> - Add `universe_svc` to the constructor (alongside existing portfolio_svc, watchlist_svc, events_svc)
> - Add `get_filtered_events(source, watchlist_id, event_types, date_from, date_to, limit, offset)`:
>   1. Resolve source to ticker list + build ticker→source priority map
>   2. Call `market_data_repo.get_upcoming_events_for_tickers(...)` with the resolved tickers
>   3. Attach `source` field to each event based on the priority map
>   4. Return `{"events": [...], "total_count": N, "has_more": bool}`
>
> In `backend/repositories/market_data_repo.py`, add:
> ```python
> async def get_upcoming_events_for_tickers(
>     self, tickers: list[str], event_types: list[str] | None,
>     date_from: str, date_to: str | None,
>     limit: int, offset: int,
> ) -> tuple[list[dict], int]:
>     """Query events for specific tickers with filters. Returns (events, total_count)."""
>     if not tickers:
>         return [], 0
>
>     placeholders = ", ".join(["?"] * len(tickers))
>     params: list = [t.upper() for t in tickers]
>
>     where_clauses = [f"ticker IN ({placeholders})"]
>
>     where_clauses.append("event_date >= ?")
>     params.append(date_from)
>
>     if date_to:
>         where_clauses.append("event_date <= ?")
>         params.append(date_to)
>
>     if event_types:
>         type_ph = ", ".join(["?"] * len(event_types))
>         where_clauses.append(f"event_type IN ({type_ph})")
>         params.extend(event_types)
>
>     where_sql = " AND ".join(where_clauses)
>
>     # Count total
>     count_row = await self.db.fetchone(
>         f"SELECT COUNT(*) as cnt FROM cache.company_events WHERE {where_sql}",
>         tuple(params),
>     )
>     total = count_row["cnt"] if count_row else 0
>
>     # Fetch page
>     fetch_params = list(params) + [limit, offset]
>     rows = await self.db.fetchall(
>         f"""SELECT * FROM cache.company_events
>             WHERE {where_sql}
>             ORDER BY event_date ASC
>             LIMIT ? OFFSET ?""",
>         tuple(fetch_params),
>     )
>     return rows, total
> ```
>
> Update `main.py` to pass `universe_svc` to `DashboardService`:
> ```python
> dashboard_svc = DashboardService(
>     db=db,
>     market_data_svc=market_data_svc,
>     portfolio_svc=portfolio_svc,
>     watchlist_svc=watchlist_svc,
>     events_svc=events_svc,
>     universe_svc=universe_svc,  # NEW
> )
> ```
>
> **Acceptance criteria:**
> 1. `backend/data/sp500_tickers.json` exists with ~503 S&P 500 tickers and metadata
> 2. `get_sp500_tickers()` returns ticker list, cached after first read
> 3. Background fetch runs on startup without blocking health endpoint
> 4. Fetch priority: portfolio → watchlist → S&P 500, with deduplication
> 5. Staleness check skips tickers with events fetched within 7 days
> 6. S&P 500 fetch has 100ms delay between tickers
> 7. Progress logged; errors caught (no crash)
> 8. `GET /events/refresh-status` returns current progress
> 9. `GET /events` accepts source, watchlist_id, event_types, date_from, date_to, limit, offset
> 10. Source filter resolves to correct ticker lists
> 11. Events deduplicated with source priority (portfolio > watchlist > market)
> 12. Response includes total_count, has_more, and source field on each event
> 13. Default date_from is today
> 14. Backward compatible: `/dashboard/summary` still works
>
> **Files to create:**
> - `backend/data/sp500_tickers.json`
>
> **Files to modify:**
> - `backend/services/universe_service.py`
> - `backend/services/company_events_service.py`
> - `backend/services/dashboard_service.py`
> - `backend/repositories/market_data_repo.py`
> - `backend/routers/dashboard_router.py`
> - `backend/main.py`
>
> **Technical constraints:**
> - Python 3.12, FastAPI, asyncio
> - SQLite via `DatabaseConnection` (async wrapper)
> - All DB queries use parameterized `?` placeholders
> - Yahoo Finance rate limiting: 100ms delay for S&P 500 batch
> - Background tasks via `asyncio.create_task()` — do not use threading
> - Event types are snake_case: `earnings`, `ex_dividend`
> - All services are singletons on `app.state`
