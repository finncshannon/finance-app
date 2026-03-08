# Session 9B — Universe Hydration Service (Background Fetch)
## Phase 9: Scanner

**Priority:** High
**Type:** Backend Only
**Depends On:** 9A (universe tickers must be loaded into companies table)
**Spec Reference:** `specs/phase9_scanner.md` → Area 1C

---

## SCOPE SUMMARY

Build a background hydration service that progressively fetches financials and market data for all tickers in the curated universes so the scanner has real data to scan against. Tiered priority: DOW (30 tickers, immediate) → S&P 500 (~500, background) → Russell 3000 (~3000, extended background). Respects the Yahoo Finance rate limiter. Provides a status endpoint for progress tracking.

---

## TASKS

### Task 1: Create UniverseHydrationService
**Description:** New service that fetches market quotes and financials for all universe tickers, prioritized by universe tier, respecting rate limits and staleness thresholds.

**Subtasks:**
- [ ] 1.1 — Create `backend/services/universe_hydration_service.py` with progress tracking:
  ```python
  import asyncio
  import logging
  import time
  from datetime import datetime, timezone

  from db.connection import DatabaseConnection
  from services.market_data_service import MarketDataService, FINANCIAL_STALE_SECONDS
  from services.universe_service import UniverseService
  from providers.exceptions import RateLimitError, ProviderError

  logger = logging.getLogger("finance_app")

  HYDRATION_TIERS = [
      {"name": "dow", "label": "DOW 30", "priority": 1},
      {"name": "sp500", "label": "S&P 500", "priority": 2},
      {"name": "r3000", "label": "Russell 3000", "priority": 3},
  ]

  FETCH_DELAY = 1.8  # ~2000/hr = one every 1.8s

  class HydrationProgress:
      def __init__(self):
          self.status = "idle"
          self.current_tier = None
          self.current_ticker = None
          self.tickers_total = 0
          self.tickers_done = 0
          self.tickers_skipped = 0
          self.tickers_failed = 0
          self.started_at = None
          self.elapsed_ms = 0

      def to_dict(self):
          return { ... }  # all fields + progress_pct

  class UniverseHydrationService:
      def __init__(self, db, market_data_svc, universe_svc):
          ...
          self.progress = HydrationProgress()
          self._running = False
  ```

- [ ] 1.2 — Add the main `run_hydration()` method that iterates tiers and fetches each ticker:
  - Compute total tickers (deduplicated across tiers) upfront
  - For each tier, get tickers from `universe_svc.get_universe_tickers(tier_name)`
  - For each ticker: check `_needs_hydration()` (skip if fresh), then `_hydrate_ticker()`, then `await asyncio.sleep(FETCH_DELAY)`
  - On `RateLimitError`: back off by `retry_after + 5` seconds, then retry the ticker once
  - On other errors: log, increment failed count, continue
  - Update `self.progress` throughout
  - Set status to "complete" when done, "cancelled" on CancelledError, "error" on unexpected failure

- [ ] 1.3 — Add `_needs_hydration(ticker)` helper:
  ```python
  async def _needs_hydration(self, ticker: str) -> bool:
      """Return True if ticker has no market_data or data is older than FINANCIAL_STALE_SECONDS."""
      md_row = await self.db.fetchone(
          "SELECT fetched_at FROM cache.market_data WHERE ticker = ?", (ticker,)
      )
      if md_row and md_row.get("fetched_at"):
          fetched = datetime.fromisoformat(md_row["fetched_at"])
          age = (datetime.now(timezone.utc) - fetched).total_seconds()
          if age < FINANCIAL_STALE_SECONDS:
              return False
      return True
  ```

- [ ] 1.4 — Add `_hydrate_ticker(ticker)` helper:
  ```python
  async def _hydrate_ticker(self, ticker: str):
      """Fetch market quote + financials via MarketDataService (cache-first)."""
      try:
          await self.market_data_svc.get_quote(ticker)
      except ProviderError:
          pass
      try:
          await self.market_data_svc.get_financials(ticker)
      except ProviderError:
          pass
  ```

- [ ] 1.5 — Add rate limiter awareness. Before each fetch, check the Yahoo provider's rate limiter remaining capacity. The `_RateLimiter` in `yahoo_finance.py` tracks timestamps in `self._timestamps`. The hydration service should check remaining capacity by accessing the rate limiter:
  ```python
  # In _hydrate_ticker or before the fetch:
  from providers.registry import provider_registry
  yahoo = provider_registry.get("yahoo")
  if hasattr(yahoo, '_rate_limiter'):
      limiter = yahoo._rate_limiter
      with limiter._lock:
          now = time.monotonic()
          cutoff = now - limiter._window_seconds
          active = len([t for t in limiter._timestamps if t > cutoff])
          remaining = limiter._max_per_hour - active
      if remaining < 50:  # Low on capacity, pause
          logger.info("Rate limiter low (%d remaining), pausing hydration 60s", remaining)
          await asyncio.sleep(60)
  ```

**Implementation Notes:**
- `MarketDataService.get_quote(ticker)` and `get_financials(ticker)` already implement cache-first — they check staleness before hitting Yahoo. Calling them is safe for recently-fetched tickers.
- `FETCH_DELAY = 1.8` seconds = ~2000/hour. DOW (30) finishes in ~1 min, S&P 500 in ~15 min, R3000 in ~1.5 hours.
- The `RateLimitError` is raised by `_RateLimiter.acquire()` when capacity is exhausted. It has a `retry_after` attribute with the wait time.
- Tickers appearing in multiple universes get hydrated once — `_needs_hydration` returns False after the first hydration.
- The `_rate_limiter` is an instance variable on `YahooFinanceProvider`. Access it via the provider registry.

---

### Task 2: Register in Startup + Status Endpoint
**Description:** Initialize the hydration service in `main.py`, start it as a background task after curated universes are loaded, and add a status endpoint.

**Subtasks:**
- [ ] 2.1 — In `backend/main.py`, after universe service init, add:
  ```python
  from services.universe_hydration_service import UniverseHydrationService

  hydration_svc = UniverseHydrationService(db, market_data_svc, universe_svc)
  app.state.hydration_service = hydration_svc
  logger.info("Universe hydration service initialized.")

  async def _startup_hydration():
      try:
          await universe_svc.load_all_curated()
          logger.info("Curated universes loaded, starting hydration...")
          await hydration_svc.run_hydration()
      except asyncio.CancelledError:
          raise
      except Exception as exc:
          logger.error("Startup hydration failed: %s", exc)

  hydration_task = asyncio.create_task(_startup_hydration())
  ```

- [ ] 2.2 — Add `hydration_task` to the shutdown cancellation list alongside existing tasks:
  ```python
  for task in [backup_task, refresh_task, status_task, hydration_task]:
      task.cancel()
  ```

- [ ] 2.3 — In `backend/routers/universe_router.py`, add a hydration status endpoint:
  ```python
  @router.get("/hydration-status")
  async def get_hydration_status(request: Request):
      svc = request.app.state.hydration_service
      return success_response(data=svc.progress.to_dict())
  ```

- [ ] 2.4 — Add a manual trigger endpoint for re-running hydration:
  ```python
  @router.post("/hydrate")
  async def trigger_hydration(request: Request):
      svc = request.app.state.hydration_service
      if svc._running:
          return success_response(data={"message": "Hydration already running", **svc.progress.to_dict()})
      asyncio.create_task(svc.run_hydration())
      return success_response(data={"message": "Hydration started"})
  ```

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: `UniverseHydrationService` created at `backend/services/universe_hydration_service.py`.
- [ ] AC-2: Hydration runs in priority order: DOW → S&P 500 → R3000.
- [ ] AC-3: Each ticker checked for staleness before fetching (skip if fresh within `FINANCIAL_STALE_SECONDS`).
- [ ] AC-4: Rate limiter respected — `FETCH_DELAY` of 1.8s between fetches.
- [ ] AC-5: Rate limiter remaining capacity checked before each batch — pauses if < 50 remaining.
- [ ] AC-6: `RateLimitError` caught with backoff (retry_after + 5s), ticker retried once.
- [ ] AC-7: Progress tracked in `HydrationProgress` with status, current_tier, current_ticker, done/skipped/failed counts, progress_pct.
- [ ] AC-8: Hydration starts automatically on app startup (after curated universe load).
- [ ] AC-9: `GET /universe/hydration-status` returns current progress.
- [ ] AC-10: `POST /universe/hydrate` triggers a manual re-run (rejects if already running).
- [ ] AC-11: Hydration task cancelled cleanly on app shutdown.
- [ ] AC-12: Second run of hydration is fast — skips tickers hydrated in the first run (staleness check).
- [ ] AC-13: Errors on individual tickers don't stop the entire hydration.
- [ ] AC-14: Progress logging: "Hydrating S&P 500: 142/500 tickers..."

---

## FILES TOUCHED

**New files:**
- `backend/services/universe_hydration_service.py` — HydrationProgress class, UniverseHydrationService with run_hydration(), _needs_hydration(), _hydrate_ticker()

**Modified files:**
- `backend/main.py` — initialize hydration service, start background task after curated load, add to shutdown list
- `backend/routers/universe_router.py` — add `GET /hydration-status` and `POST /hydrate` endpoints

---

## BUILDER PROMPT

> **Session 9B — Universe Hydration Service (Background Fetch)**
>
> You are building session 9B of the Finance App v2.0 update.
>
> **What you're doing:** Building a background service that progressively fetches market data and financials for all tickers in the curated universes (DOW → S&P 500 → R3000) so the scanner has real data. The service respects Yahoo Finance's rate limiter, tracks progress, and provides a status endpoint.
>
> **Context:** Session 9A loaded ~3500 tickers into the `companies` table with names, sectors, and industries. But the scanner needs `cache.market_data` and `cache.financial_data` to actually filter on — these are currently only populated when a user manually researches a ticker. The hydration service fills this gap by background-fetching data for the entire universe.
>
> **Existing code:**
>
> `MarketDataService` (at `backend/services/market_data_service.py`):
> - `get_quote(ticker)` — cache-first pattern: checks `cache.market_data` staleness, fetches from Yahoo if stale, writes to cache, returns QuoteData
> - `get_financials(ticker)` — cache-first: checks `cache.financial_data`, fetches if stale
> - `FINANCIAL_STALE_SECONDS = 86400` (24 hours)
> - These methods handle all caching internally — calling them is sufficient for hydration
>
> `YahooFinanceProvider` (at `backend/providers/yahoo_finance.py`):
> - Has `_RateLimiter` class with `acquire()` method, `_max_per_hour=2000`, `_timestamps: list[float]`, `_lock: threading.Lock`
> - `_RateLimiter.acquire()` raises `RateLimitError(retry_after=wait)` when at capacity
> - Instance: `yahoo_provider._rate_limiter` (accessible via provider registry)
>
> `RateLimitError` (from `providers/exceptions.py`):
> - `RateLimitError(provider, retry_after)` — has `retry_after: float` attribute (seconds)
>
> `UniverseService` (at `backend/services/universe_service.py`, after 9A):
> - `get_universe_tickers(universe)` — returns `list[str]` for "dow", "sp500", "r3000", "all"
> - `load_all_curated()` — loads all 3 JSON files
>
> `main.py` startup pattern:
> - Services initialized with `app.state.xxx = xxx`
> - Background tasks created with `asyncio.create_task(svc.run_xxx())`
> - Shutdown cancels tasks in a for loop: `for task in [...]: task.cancel()`
> - Existing background tasks: `refresh_task` (price refresh), `status_task` (status broadcast), `backup_task`
>
> `universe_router.py` — current endpoints: `GET /stats`, `GET /tickers`, `POST /load`, `POST /refresh`, `POST /load-curated` (from 9A)
>
> **Cross-cutting rules:**
> - Data Format: All ratios/percentages as decimal ratios (0.15 = 15%).
>
> **Task 1: Create UniverseHydrationService**
>
> New file `backend/services/universe_hydration_service.py`:
>
> `HydrationProgress` class — tracks: status (idle/running/paused/complete/error/cancelled), current_tier, current_ticker, tickers_total, tickers_done, tickers_skipped, tickers_failed, started_at, elapsed_ms. Has `to_dict()` returning all fields + computed `progress_pct`.
>
> `UniverseHydrationService.__init__(db, market_data_svc, universe_svc)` — stores refs, creates progress, `_running = False`.
>
> `run_hydration()`:
> 1. Guard: if `_running`, log warning and return
> 2. Set `_running = True`, status = "running", record start time
> 3. Compute total tickers (deduplicated set across all tiers)
> 4. For each tier in `HYDRATION_TIERS` (dow→sp500→r3000):
>    - Get tickers via `universe_svc.get_universe_tickers(tier_name)`
>    - For each ticker: update progress.current_ticker, check `_needs_hydration()`, call `_hydrate_ticker()`, sleep `FETCH_DELAY`
>    - Catch `RateLimitError`: backoff `retry_after + 5`, retry once
>    - Catch other exceptions: log, increment failed, continue
> 5. Set status = "complete" (or "cancelled"/"error")
> 6. In finally: record elapsed_ms, clear current_ticker, set `_running = False`
>
> `_needs_hydration(ticker)`: query `cache.market_data` for `fetched_at`, return True if missing or older than `FINANCIAL_STALE_SECONDS`.
>
> `_hydrate_ticker(ticker)`: call `market_data_svc.get_quote(ticker)` + `market_data_svc.get_financials(ticker)`, wrap each in try/except ProviderError (some tickers may not have data).
>
> Rate limiter check: before each hydration, access the Yahoo provider's `_rate_limiter` via `provider_registry.get("yahoo")`, check remaining capacity under the lock. If < 50 remaining, pause 60s before continuing.
>
> **Task 2: Startup + Endpoints**
>
> In `main.py`: initialize `UniverseHydrationService(db, market_data_svc, universe_svc)`, store as `app.state.hydration_service`. Create a startup coroutine that calls `universe_svc.load_all_curated()` then `hydration_svc.run_hydration()`. Launch as `asyncio.create_task()`. Add to shutdown cancellation list.
>
> In `universe_router.py`:
> - `GET /hydration-status` — returns `svc.progress.to_dict()`
> - `POST /hydrate` — starts hydration if not running, returns status if already running
>
> **Acceptance criteria:**
> 1. Hydration runs DOW → S&P 500 → R3000 in order
> 2. Stale tickers fetched, fresh ones skipped
> 3. Rate limiter respected (1.8s delay + capacity check)
> 4. RateLimitError handled with backoff
> 5. Progress tracked with all counts
> 6. Auto-starts on app startup
> 7. Status endpoint returns progress
> 8. Manual trigger works
> 9. Clean shutdown
> 10. Individual errors don't stop hydration
>
> **Files to create:** `backend/services/universe_hydration_service.py`
> **Files to modify:** `backend/main.py`, `backend/routers/universe_router.py`
>
> **Technical constraints:**
> - `asyncio.create_task()` for background work
> - `asyncio.sleep()` for delays (not `time.sleep`)
> - `RateLimitError` from `providers.exceptions` has `retry_after: float`
> - Provider registry: `provider_registry.get("yahoo")` returns the Yahoo provider instance
> - `_RateLimiter._timestamps` and `_RateLimiter._lock` are implementation details — access carefully with the lock
> - `FINANCIAL_STALE_SECONDS = 86400` from `market_data_service.py`
> - All DB queries use `await self.db.fetchone/fetchall` pattern
> - Hydration is NOT blocking — the app serves requests while hydrating in the background
