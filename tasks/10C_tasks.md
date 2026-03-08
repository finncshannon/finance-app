# Session 10C — Live Data Fix (Startup Refresh, After-Hours, day_change_pct, Profiles)
## Phase 10: Portfolio

**Priority:** CRITICAL
**Type:** Backend Only
**Depends On:** None (but should coordinate with 11A — see below)
**Spec Reference:** `specs/phase10_portfolio_performance.md` → Areas 5A–5D, Area 4

---

## ⚠️ CRITICAL COORDINATION NOTE

**This session modifies the same files as 11A (Data Accuracy Normalization).** They address the same root cause: data format mismatches in the pipeline.

**Recommended order:** Run 11A first for the full pipeline audit, then 10C adds the live refresh / startup / profile features on top.

**Read `specs/10C_11A_COORDINATION.md` before building this session.** That document details the overlapping files, the `day_change_pct` root cause, and how to handle sequencing.

If 11A has already run, the `day_change_pct` fix below may already be applied — check the code before duplicating the fix.

---

## SCOPE SUMMARY

Fix critical data issues: add one-time price refresh on app startup (so data is fresh regardless of market hours), add after-hours refresh interval (15 min instead of never), fix the `day_change_pct` format bug (SPY showing 85%), fix market status timezone handling, auto-fetch company profiles on position create, and add a profile backfill startup task for existing positions.

---

## TASKS

### Task 1: Fix day_change_pct Format Bug
**Description:** The Yahoo provider computes `day_change_pct = (day_change / prev_close) * 100`, storing a percentage value (0.85 for 0.85%). But the app convention is decimal ratios (0.0085 for 0.85%). The frontend's `fmtPct()` multiplies by 100, so `0.85 * 100 = 85%` — the SPY bug.

**Subtasks:**
- [ ] 1.1 — **INVESTIGATE FIRST.** Before making the fix, add temporary logging to trace the value through the pipeline. In `yahoo_finance.py` `get_quote()`:
  ```python
  logger.debug("TRACE day_change_pct for %s: raw=%.6f", ticker, day_change_pct)
  ```
  In `market_data_service.py` `get_live_quote()`:
  ```python
  logger.debug("TRACE day_change_pct cache write for %s: %.6f", ticker, quote.day_change_pct)
  ```
  Run with a known ticker (e.g., AAPL) and verify the value at each layer. This confirms the root cause before fixing.

- [ ] 1.2 — In `backend/providers/yahoo_finance.py`, method `get_quote()`, fix the calculation:
  ```python
  # BEFORE (bug):
  # day_change_pct = (day_change / prev_close) * 100
  
  # AFTER (fix — decimal ratio convention):
  day_change_pct = day_change / prev_close  # 0.0085 for 0.85%
  ```

- [ ] 1.3 — Verify `dividend_yield` from `get_key_statistics()`. Yahoo's `dividendYield` key already returns a decimal (e.g., 0.005 for 0.5%). Confirm this with a known dividend stock. If it's already a decimal, no change needed.

- [ ] 1.4 — Search the entire codebase for any other place that reads `day_change_pct` from cache and applies its own formatting — ensure they all expect a decimal ratio. Check:
  - `frontend/src/pages/Dashboard/MarketOverview/MarketOverviewWidget.tsx`
  - `frontend/src/pages/Portfolio/Holdings/HoldingsTable.tsx`
  - Any component displaying daily change

- [ ] 1.5 — Remove the temporary logging after confirming the fix works.

---

### Task 2: Startup Price Refresh
**Description:** Add a one-time price refresh on app startup for all portfolio + watchlist tickers, regardless of market hours. Currently, if you open the app after hours, you see stale cached data from the last market-hours refresh.

**Subtasks:**
- [ ] 2.1 — In `backend/main.py`, add a startup refresh task after all services are initialized:
  ```python
  async def _startup_price_refresh():
      """One-time refresh of portfolio + watchlist tickers on app launch."""
      try:
          # Get portfolio tickers
          portfolio_svc = app.state.portfolio_service
          positions = await portfolio_svc.repo.get_all_positions()
          portfolio_tickers = list({p["ticker"] for p in positions})

          # Get watchlist tickers
          watchlist_svc = app.state.watchlist_service
          watchlists = await watchlist_svc.get_all_watchlists()
          watchlist_tickers = []
          for wl in watchlists:
              items = await watchlist_svc.get_watchlist_items(wl["id"])
              watchlist_tickers.extend([item["ticker"] for item in items])

          all_tickers = list(set(portfolio_tickers + watchlist_tickers))
          if all_tickers:
              logger.info("Startup refresh: %d tickers", len(all_tickers))
              await market_data_svc.refresh_batch(all_tickers)
              logger.info("Startup refresh complete")
      except Exception as exc:
          logger.error("Startup refresh failed: %s", exc)

  startup_refresh_task = asyncio.create_task(_startup_price_refresh())
  ```

- [ ] 2.2 — Add `startup_refresh_task` to shutdown cancellation list.

---

### Task 3: After-Hours Refresh Interval
**Description:** Modify `PriceRefreshService.run_refresh_loop()` to refresh outside market hours at a reduced frequency (every 15 minutes) instead of doing nothing.

**Subtasks:**
- [ ] 3.1 — In `backend/services/price_refresh_service.py`, update `run_refresh_loop()`:
  ```python
  AFTER_HOURS_INTERVAL = 900   # 15 minutes
  WEEKEND_INTERVAL = 3600      # 1 hour

  async def run_refresh_loop(self):
      """Background loop: refresh prices for subscribed tickers."""
      while True:
          try:
              if MarketDataService.is_market_open():
                  interval = PRICE_REFRESH_INTERVAL  # 60s
              elif self._is_weekend():
                  interval = WEEKEND_INTERVAL  # 1 hour
              else:
                  interval = AFTER_HOURS_INTERVAL  # 15 min

              # Get all subscribed tickers
              tickers = self._get_all_subscribed_tickers()
              if tickers:
                  await self._refresh_tickers(tickers)

              await asyncio.sleep(interval)
          except asyncio.CancelledError:
              break
          except Exception as exc:
              logger.exception("Refresh loop error: %s", exc)
              await asyncio.sleep(interval)
  ```

- [ ] 3.2 — Add `_is_weekend()` helper:
  ```python
  @staticmethod
  def _is_weekend() -> bool:
      from datetime import datetime, timezone, timedelta
      try:
          from zoneinfo import ZoneInfo
          et = ZoneInfo("America/New_York")
      except ImportError:
          et = timezone(timedelta(hours=-5))
      now_et = datetime.now(et)
      return now_et.weekday() > 4
  ```

- [ ] 3.3 — Verify the existing `run_refresh_loop` has the `if MarketDataService.is_market_open()` guard. Replace it with the tiered interval logic above. The refresh logic itself (fetching and broadcasting) remains unchanged — only the interval and the "skip if not market hours" guard changes.

---

### Task 4: Market Status Fix
**Description:** Audit and fix `DashboardService.get_market_status()` for timezone/DST handling.

**Subtasks:**
- [ ] 4.1 — In `backend/services/dashboard_service.py`, audit `get_market_status()`:
  - Verify it uses `ZoneInfo("America/New_York")` with proper fallback
  - Verify DST transitions are handled (America/New_York automatically handles DST via ZoneInfo)
  - Add logging: `logger.debug("Market status calc: now_et=%s, open=%s, close=%s", now_et, market_open, market_close)`
  - Verify the "After hours ending in X hours" calculation is correct — it should compare current time to the next market open, not to the current day's close

- [ ] 4.2 — Verify the status WebSocket broadcasts the market status correctly and the frontend consumes it. Check:
  - `price_refresh_service.py` `run_status_loop()` — does it call `dashboard_svc.get_market_status()`?
  - Frontend: does the Dashboard subscribe to `ws/status` and update the market status indicator?

---

### Task 5: Auto-Fetch Company Profile on Position Create
**Description:** When a position is added (manual, CSV import, or transaction), auto-fetch the company profile in the background so company names and sectors populate in the holdings table and allocation views.

**Subtasks:**
- [ ] 5.1 — In `backend/services/portfolio/portfolio_service.py`, after creating a position, trigger a background profile fetch:
  ```python
  async def add_position(self, data: PositionCreate) -> Position:
      """Create a position and auto-fetch company profile."""
      position = await self._create_position(data)
      
      # Background fetch company profile (don't block the response)
      asyncio.create_task(self._ensure_company_profile(data.ticker))
      
      return position

  async def _ensure_company_profile(self, ticker: str):
      """Fetch company profile if not already cached."""
      try:
          company = await self.mds.get_company(ticker)
          if company and company.get("company_name") == ticker:
              # Name is just the ticker — needs a real fetch
              await self.mds.get_company(ticker)
      except Exception as exc:
          logger.warning("Failed to fetch profile for %s: %s", ticker, exc)
  ```

- [ ] 5.2 — Add `import asyncio` to portfolio_service.py if not already imported.

---

### Task 6: Profile Backfill Startup Task
**Description:** On app startup, scan all portfolio positions for tickers missing company profiles and fetch them in the background.

**Subtasks:**
- [ ] 6.1 — In `backend/main.py`, add a backfill task:
  ```python
  async def _backfill_profiles():
      """Fetch missing company profiles for portfolio positions."""
      try:
          portfolio_svc = app.state.portfolio_service
          positions = await portfolio_svc.repo.get_all_positions()
          tickers = list({p["ticker"] for p in positions})
          
          company_repo = CompanyRepo(db)
          for ticker in tickers:
              company = await company_repo.get_by_ticker(ticker)
              if not company or company.get("company_name") == ticker or company.get("sector") == "Unknown":
                  try:
                      await market_data_svc.get_company(ticker)
                      await asyncio.sleep(2)  # Rate limit friendly
                  except Exception:
                      pass
          logger.info("Profile backfill complete for %d tickers", len(tickers))
      except Exception as exc:
          logger.error("Profile backfill failed: %s", exc)

  backfill_task = asyncio.create_task(_backfill_profiles())
  ```

- [ ] 6.2 — Add to shutdown cancellation list.

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: `day_change_pct` stored as decimal ratio (0.0085 for 0.85% change) — not percentage (0.85).
- [ ] AC-2: SPY and other tickers show correct daily change percentage in the UI (e.g., `+0.85%` not `+85%`).
- [ ] AC-3: Investigation logging confirms the fix at each pipeline layer before removing logs.
- [ ] AC-4: App startup triggers a one-time price refresh for all portfolio + watchlist tickers.
- [ ] AC-5: Startup refresh works regardless of market hours.
- [ ] AC-6: After market close, prices refresh every 15 minutes (not never).
- [ ] AC-7: On weekends, prices refresh every 1 hour.
- [ ] AC-8: During market hours, prices still refresh every 60 seconds (no regression).
- [ ] AC-9: Market status ("Open", "After Hours", "Closed") displays correctly across timezone transitions.
- [ ] AC-10: Market status accounts for DST via `ZoneInfo("America/New_York")`.
- [ ] AC-11: Adding a new position auto-fetches company profile in the background.
- [ ] AC-12: Company name and sector populate in holdings table after profile fetch.
- [ ] AC-13: Startup profile backfill fetches missing profiles for existing positions.
- [ ] AC-14: Profile backfill is rate-limit friendly (2s delay between fetches).
- [ ] AC-15: `dividend_yield` confirmed as decimal ratio (no double-multiplication).
- [ ] AC-16: All background tasks cancel cleanly on app shutdown.
- [ ] AC-17: No regressions on existing price refresh, market status, or portfolio functionality.

---

## FILES TOUCHED

**New files:**
- None

**Modified files:**
- `backend/providers/yahoo_finance.py` — fix `day_change_pct` calculation (remove `* 100`), add temporary trace logging
- `backend/services/market_data_service.py` — add trace logging for investigation (temporary)
- `backend/services/price_refresh_service.py` — add after-hours refresh interval (15 min), weekend interval (1 hr), replace market-hours-only guard with tiered logic
- `backend/services/dashboard_service.py` — audit market status timezone handling, add debug logging
- `backend/services/portfolio/portfolio_service.py` — add `_ensure_company_profile()`, call from `add_position()`
- `backend/main.py` — add startup refresh task, add profile backfill task, add to shutdown list

---

## BUILDER PROMPT

> **Session 10C — Live Data Fix (Startup Refresh, After-Hours, day_change_pct, Profiles)**
>
> You are building session 10C of the Finance App v2.0 update. This is a **CRITICAL** session.
>
> ⚠️ **Read `specs/10C_11A_COORDINATION.md` first.** This session overlaps with 11A (Data Accuracy Normalization). If 11A has already run, the `day_change_pct` fix may already be applied — check before duplicating.
>
> **What you're doing:** Fixing critical data issues: (1) Fix `day_change_pct` format bug causing SPY to show 85%, (2) Add startup price refresh, (3) Add after-hours refresh interval, (4) Fix market status timezone handling, (5) Auto-fetch company profiles on position create, (6) Profile backfill on startup.
>
> **Context:** Currently: no refresh outside market hours (stale data), `day_change_pct` multiplied by 100 at provider level AND by frontend `fmtPct` (double multiplication), market status shows wrong times due to DST issues, most portfolio positions show no company name/sector because profiles aren't auto-fetched.
>
> **Existing code:**
>
> `yahoo_finance.py` (at `backend/providers/yahoo_finance.py`):
> - `get_quote()` computes: `day_change_pct = (day_change / prev_close) * 100`
> - **BUG:** This stores `0.85` for a 0.85% change. Frontend `fmtPct(0.85)` → `85%`.
> - **FIX:** Remove `* 100`: `day_change_pct = day_change / prev_close` → stores `0.0085`
> - `get_key_statistics()` reads `dividendYield` from Yahoo — yfinance returns this as a decimal (0.005 for 0.5%). Verify but likely correct.
> - `_RateLimiter` with `acquire()` and `remaining` property
>
> `market_data_service.py` (at `backend/services/market_data_service.py`):
> - `get_live_quote(ticker)` — fetches from provider, writes to `cache.market_data` via `market_repo.upsert_market_data(cache_data)`. Passes `day_change_pct` through as-is from provider.
> - `refresh_batch(tickers)` — calls `get_live_quote` + `get_company` per ticker. Returns `{ticker: success}`.
> - `is_market_open()` — uses `ZoneInfo("America/New_York")` with fallback to UTC-5. Checks weekday + 9:30-16:00 ET.
> - Staleness constants: `TIER1_STALE_SECONDS = 60`, `FINANCIAL_STALE_SECONDS = 86400`
>
> `price_refresh_service.py` (at `backend/services/price_refresh_service.py`):
> - `PRICE_REFRESH_INTERVAL = 60` seconds
> - `run_refresh_loop()` — while True loop. **Currently only refreshes if `is_market_open()`** — does nothing outside market hours.
> - `run_status_loop()` — broadcasts system status every 30 seconds
> - `ConnectionManager` tracks WebSocket subscriptions per client
>
> `dashboard_service.py` (at `backend/services/dashboard_service.py`):
> - `get_market_status()` — computes "Open", "Pre-Market", "After Hours", "Closed" based on ET time
> - May have DST issues with the fallback `timezone(timedelta(hours=-5))`
>
> `portfolio_service.py` (at `backend/services/portfolio/portfolio_service.py`):
> - `add_position(PositionCreate)` — creates position record. Does NOT fetch company profile.
> - Has access to `self.mds` (MarketDataService) for `get_company(ticker)`
>
> `main.py` startup pattern:
> - Services initialized, stored as `app.state.xxx`
> - Background tasks via `asyncio.create_task()`, cancelled on shutdown
> - Existing tasks: `refresh_task`, `status_task`, `backup_task`, `hydration_task` (from 9B)
>
> **Cross-cutting rules:**
> - Data Format: **All ratios/percentages stored as decimal ratios (0.15 = 15%).** This is the rule `day_change_pct` violates.
> - Display Name Rule: Use `displayNames.ts` for UI labels.
>
> **Task 1: Fix day_change_pct**
> - INVESTIGATE FIRST: add temp logging at provider and cache write layers, run with known ticker, verify values
> - Fix: `day_change_pct = day_change / prev_close` (remove `* 100`)
> - Verify `dividend_yield` is already a decimal ratio from Yahoo
> - Search codebase for other consumers of `day_change_pct` to ensure they expect decimal
> - Remove temp logging after confirming
>
> **Task 2: Startup Refresh**
> - In `main.py`, after services init: get portfolio tickers + watchlist tickers, call `market_data_svc.refresh_batch(all_tickers)`
> - Background task, non-blocking
>
> **Task 3: After-Hours Refresh**
> - In `price_refresh_service.py`, replace market-hours-only guard with tiered intervals:
>   - Market hours: 60s (existing)
>   - After hours (weekday): 15 min
>   - Weekend: 1 hour
> - Add `_is_weekend()` helper
>
> **Task 4: Market Status Fix**
> - Audit `dashboard_service.py` `get_market_status()` for timezone/DST
> - Ensure `ZoneInfo("America/New_York")` is used (handles DST automatically)
> - Add debug logging for the status calculation
> - Verify "After hours ending in X hours" math
>
> **Task 5: Auto-Fetch Profile on Position Create**
> - In `portfolio_service.py` `add_position()`, after creating position: `asyncio.create_task(self._ensure_company_profile(ticker))`
> - `_ensure_company_profile()`: calls `self.mds.get_company(ticker)` which fetches from Yahoo and caches
>
> **Task 6: Profile Backfill**
> - Startup task in `main.py`: iterate all portfolio tickers, fetch profile for any with `company_name == ticker` or `sector == "Unknown"`
> - 2s delay between fetches for rate limiting
>
> **Acceptance criteria:**
> 1. day_change_pct is decimal ratio (0.0085 not 0.85)
> 2. SPY shows correct % in UI
> 3. Startup refresh runs for portfolio + watchlist tickers
> 4. After-hours: 15 min refresh interval
> 5. Weekend: 1 hour refresh
> 6. Market hours: 60s (no regression)
> 7. Market status correct across DST
> 8. New positions auto-fetch company profile
> 9. Startup backfill fills missing profiles
> 10. Clean shutdown
> 11. No regressions
>
> **Files to create:** None
> **Files to modify:** `yahoo_finance.py`, `market_data_service.py`, `price_refresh_service.py`, `dashboard_service.py`, `portfolio_service.py`, `main.py`
>
> **Technical constraints:**
> - `asyncio.create_task()` for background work — don't block the app startup
> - `ZoneInfo("America/New_York")` for timezone — handles DST automatically
> - `refresh_batch(tickers)` already exists on MarketDataService — use it for startup refresh
> - Rate limiter: startup refresh + backfill both hit Yahoo. They run sequentially within `refresh_batch` which calls `get_live_quote` per ticker. The rate limiter in Yahoo provider will block if capacity is exhausted.
> - `CompanyRepo.get_by_ticker()` and `MarketDataService.get_company()` already exist
> - The investigation logging (Task 1.1) should be added, verified, then removed in the same session
