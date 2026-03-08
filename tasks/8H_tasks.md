# Session 8H — Comps Backend (Auto Peer Discovery, Null Safety)
## Phase 8: Model Builder

**Priority:** High (Tier 2 — the app literally crashes on Comps)
**Type:** Backend Only
**Depends On:** None
**Spec Reference:** `specs/phase8_model_builder_model.md` → Areas 1A, 1B

---

## SCOPE SUMMARY

Fix the Comps crash by: (1) building auto-peer-discovery that finds 8–15 peer companies by sector, industry, and market cap proximity when no peers are provided, (2) ensuring CompsResult always has a well-formed `peer_group` with a `status` field so the frontend can render appropriate UI states without crashing on undefined access.

---

## TASKS

### Task 1: Add Peer Discovery Query to CompanyRepo
**Description:** Add a query method to find companies in the same sector/industry with cached financial data, sorted by market cap proximity.

**Subtasks:**
- [ ] 1.1 — In `backend/repositories/company_repo.py`, add method:
  ```python
  async def find_peers(
      self,
      ticker: str,
      sector: str,
      industry: str,
      market_cap: float | None,
      limit: int = 15,
  ) -> list[dict]:
      """Find peer companies by sector/industry with financial data.
      
      Prioritizes:
      1. Same industry with cached financials
      2. Same sector with cached financials
      3. Sorted by market cap proximity to target
      """
  ```
- [ ] 1.2 — Implementation:
  1. Query companies in the same industry (excluding the target ticker) that have at least one row in `cache.financial_data`:
     ```sql
     SELECT c.ticker, c.company_name, c.sector, c.industry,
            md.market_cap
     FROM companies c
     LEFT JOIN cache.market_data md ON md.ticker = c.ticker
     INNER JOIN cache.financial_data fd ON fd.ticker = c.ticker
     WHERE c.industry = ? AND c.ticker != ?
     GROUP BY c.ticker
     HAVING COUNT(fd.id) >= 1
     ORDER BY ABS(COALESCE(md.market_cap, 0) - ?) ASC
     LIMIT ?
     ```
  2. If fewer than `limit` results from same industry, expand to same sector:
     ```sql
     WHERE c.sector = ? AND c.ticker != ? AND c.ticker NOT IN (already_found)
     ```
  3. Combine and return up to `limit` peers.
- [ ] 1.3 — Return format: list of dicts with `ticker`, `company_name`, `sector`, `industry`, `market_cap`.

**Implementation Notes:**
- The `INNER JOIN cache.financial_data` ensures we only return peers with actual data (otherwise Comps has nothing to compute multiples from).
- Market cap proximity: `ABS(COALESCE(md.market_cap, 0) - target_market_cap)` — peers closest in size rank higher.
- If `market_cap` is None for the target, use 0 (all peers sorted by absolute market cap ascending).

---

### Task 2: Add find_peers Method to CompanyService
**Description:** Add a service-level method that coordinates peer discovery.

**Subtasks:**
- [ ] 2.1 — In `backend/services/company_service.py`, add method:
  ```python
  async def find_peers(self, ticker: str, limit: int = 15) -> list[str]:
      """Auto-discover peer companies for Comps analysis.
      
      Returns list of peer ticker strings, sorted by relevance.
      Returns empty list if no peers found.
      """
  ```
- [ ] 2.2 — Implementation:
  1. Get the target company's profile (sector, industry, market_cap) from `company_repo.get_by_ticker(ticker)`
  2. If company not found, return `[]`
  3. Get market data for market_cap: `market_data_repo.get_market_data(ticker)` → `market_cap`
  4. Call `company_repo.find_peers(ticker, sector, industry, market_cap, limit)`
  5. Return list of ticker strings: `[peer["ticker"] for peer in peers]`
- [ ] 2.3 — Add fallback: if company has no sector/industry set (both "Unknown"), log a warning and return `[]`.

---

### Task 3: Add Status Field to CompsResult
**Description:** Ensure CompsResult always has a well-formed response with a status field for the frontend.

**Subtasks:**
- [ ] 3.1 — In `backend/engines/models.py`, add `status` field to `CompsResult`:
  ```python
  class CompsResult(BaseModel):
      ticker: str
      current_price: float = 0.0
      model_type: str = "comps"
      status: str = "ready"  # "ready" | "no_peers" | "error"
      peer_group: dict = Field(default_factory=lambda: {"peers": [], "count": 0})
      # ... rest unchanged
  ```
- [ ] 3.2 — Ensure the `default_factory` for `peer_group` always produces `{"peers": [], "count": 0}` (not `None`, not `{}`).

---

### Task 4: Add Null Safety to CompsEngine
**Description:** Ensure CompsEngine.run() never crashes on missing peer data and always returns a well-formed result.

**Subtasks:**
- [ ] 4.1 — In `backend/engines/comps_engine.py`, in the `run()` method:
  - If `peer_data` is None or empty: return a `CompsResult` with `status="no_peers"`, `peer_group={"peers": [], "count": 0}`, and a warning message: "No peer companies available. Add peers to run comparisons."
  - Do NOT attempt to compute multiples or implied values with no peers
- [ ] 4.2 — Wrap the entire run() method body in try/except. On any exception, return a `CompsResult` with `status="error"` and the error message in `metadata.warnings`.
- [ ] 4.3 — In the peer_group construction (the part that builds the peers list), add null checks:
  - Skip peers where required data is missing (no financials, no market_data)
  - If after filtering, `len(valid_peers) < 1`, set `status="no_peers"`

---

### Task 5: Auto-Discover Peers in Router
**Description:** When the `run_comps` endpoint receives no `peer_tickers`, automatically discover peers.

**Subtasks:**
- [ ] 5.1 — In `backend/routers/models_router.py`, update the `run_comps` endpoint:
  ```python
  @router.post("/{ticker}/run/comps")
  async def run_comps(ticker: str, body: RunRequest, request: Request):
      try:
          engine = request.app.state.assumption_engine
          assumptions = await engine.generate_assumptions(
              ticker, model_type="comps", overrides=body.overrides,
          )
          data, price = await _gather_engine_data(ticker, request)

          # Auto-discover peers if not provided
          peer_tickers = body.peer_tickers
          if not peer_tickers:
              company_svc = request.app.state.company_service
              peer_tickers = await company_svc.find_peers(ticker)
              logger.info("Auto-discovered %d peers for %s", len(peer_tickers), ticker)

          # Gather peer data
          peer_data = None
          if peer_tickers:
              peer_data = await _gather_peer_data(peer_tickers, request)

          result = CompsEngine.run(assumptions, data, price, peer_data)
          return success_response(data=result.model_dump(mode="json"))
      except Exception as exc:
          logger.exception("Comps run failed for %s", ticker)
          return error_response("ENGINE_ERROR", str(exc))
  ```
- [ ] 5.2 — Also update `run_all_models` endpoint to auto-discover peers when `peer_tickers` not provided.
- [ ] 5.3 — Also update the `generate_overview` endpoint to auto-discover peers for the Comps component of the overview.

---

### Task 6: Ensure CompanyService is on app.state
**Description:** Verify CompanyService is initialized and registered on app.state during startup.

**Subtasks:**
- [ ] 6.1 — Check `backend/main.py` for `company_service` initialization. If it doesn't exist, add:
  ```python
  from services.company_service import CompanyService
  company_svc = CompanyService(
      db=db,
      market_data_svc=market_data_svc,
      data_extraction_svc=data_extraction_svc,
      sec_provider=sec_provider,
  )
  app.state.company_service = company_svc
  logger.info("Company service initialized.")
  ```
- [ ] 6.2 — If `CompanyService` is already on `app.state`, just verify it has the `find_peers` method after the update.

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: `company_repo.find_peers()` returns companies in same industry/sector with cached financial data, sorted by market cap proximity.
- [ ] AC-2: Peer discovery prioritizes same industry, falls back to same sector.
- [ ] AC-3: Only peers with at least 1 row in `cache.financial_data` are returned (can actually compute multiples).
- [ ] AC-4: `company_service.find_peers(ticker)` returns up to 15 peer ticker strings.
- [ ] AC-5: If company has no sector/industry, returns empty list (no crash).
- [ ] AC-6: `CompsResult` has `status: str` field with values `"ready"`, `"no_peers"`, or `"error"`.
- [ ] AC-7: `CompsResult.peer_group` default is `{"peers": [], "count": 0}` (never None).
- [ ] AC-8: `CompsEngine.run()` with no peers returns `status="no_peers"` with warning (no crash).
- [ ] AC-9: `CompsEngine.run()` with any exception returns `status="error"` (no crash).
- [ ] AC-10: `POST /{ticker}/run/comps` auto-discovers peers when `peer_tickers` is not provided.
- [ ] AC-11: Auto-discovered peers logged: "Auto-discovered N peers for TICKER".
- [ ] AC-12: `run_all_models` also auto-discovers peers for the Comps component.
- [ ] AC-13: `generate_overview` also auto-discovers peers for Comps.
- [ ] AC-14: `CompanyService` is registered on `app.state.company_service`.
- [ ] AC-15: Existing Comps functionality with manually-provided peers still works (backward compatible).

---

## FILES TOUCHED

**New files:**
- None

**Modified files:**
- `backend/repositories/company_repo.py` — add `find_peers()` query method
- `backend/services/company_service.py` — add `find_peers()` service method
- `backend/engines/models.py` — add `status` field to `CompsResult`, fix `peer_group` default
- `backend/engines/comps_engine.py` — null safety in `run()`, early return for no peers, try/except wrapper
- `backend/routers/models_router.py` — auto-discover peers in `run_comps`, `run_all_models`, `generate_overview`
- `backend/main.py` — ensure `company_service` is on `app.state` (may already exist)

---

## BUILDER PROMPT

> **Session 8H — Comps Backend (Auto Peer Discovery, Null Safety)**
>
> You are building session 8H of the Finance App v2.0 update.
>
> **What you're doing:** Fixing the Comps crash by building auto-peer-discovery (finds 8–15 similar companies by sector/industry/market cap) and adding null safety so CompsResult always returns a well-formed response with a status field.
>
> **Context:** The Comps model crashes the frontend because: (1) no peers are provided by default — the run_comps endpoint receives `peer_tickers: null`, (2) CompsEngine.run() produces an incomplete `peer_group`, (3) CompsView.tsx accesses `result.peer_group.peers` which crashes on undefined. You're fixing the backend so it auto-discovers peers and never returns a malformed response.
>
> **Existing code:**
>
> `company_repo.py`:
> - `CompanyRepo` with `get_by_ticker(ticker)`, `create(data)`, `update(ticker, data)`. Uses `companies` table.
> - `companies` table has: `ticker (PK), company_name, sector, industry, cik, exchange, market_cap` etc.
>
> `company_service.py`:
> - `CompanyService(db, market_data_svc, data_extraction_svc, sec_provider)` with `get_or_create_company(ticker)`, `search(query)`. No `find_peers` yet.
>
> `engines/comps_engine.py`:
> - `CompsEngine.run(assumption_set, data, current_price, peer_data)` — static method. `peer_data` is `list[dict] | None`. When `peer_data` is None, the engine proceeds but produces incomplete output that crashes the frontend.
>
> `engines/models.py`:
> - `CompsResult(BaseModel)`: has `peer_group: dict = Field(default_factory=dict)` — defaults to `{}` not `{"peers": [], "count": 0}`. No `status` field.
>
> `routers/models_router.py`:
> - `POST /{ticker}/run/comps` — calls `CompsEngine.run(assumptions, data, price, peer_data)`. Only gathers `peer_data` if `body.peer_tickers` is provided. No auto-discovery.
> - `_gather_peer_data(peer_tickers, request)` — fetches financials + quote for each peer ticker.
>
> Database schema:
> - `companies` table in `user_data.db` — has `sector`, `industry` columns
> - `cache.financial_data` — has financials per ticker (need INNER JOIN to find peers with data)
> - `cache.market_data` — has `market_cap` per ticker
>
> **Cross-cutting rules:**
> - Display Name Rule: All backend snake_case keys displayed in the UI must use the shared `displayNames.ts` utility.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%).
> - Scenario Order: Bear / Base / Bull (left to right), Base default.
>
> **Task 1: Peer Discovery Query in CompanyRepo**
>
> In `backend/repositories/company_repo.py`, add:
> ```python
> async def find_peers(
>     self, ticker: str, sector: str, industry: str,
>     market_cap: float | None, limit: int = 15,
> ) -> list[dict]:
>     """Find peer companies by sector/industry with cached financial data."""
>     target_cap = market_cap or 0
>     peers = []
>     
>     # Step 1: Same industry
>     if industry and industry != "Unknown":
>         industry_peers = await self.db.fetchall(
>             """SELECT c.ticker, c.company_name, c.sector, c.industry,
>                       COALESCE(md.market_cap, 0) as market_cap
>                FROM companies c
>                LEFT JOIN cache.market_data md ON md.ticker = c.ticker
>                WHERE c.industry = ? AND c.ticker != ?
>                  AND EXISTS (SELECT 1 FROM cache.financial_data fd WHERE fd.ticker = c.ticker)
>                ORDER BY ABS(COALESCE(md.market_cap, 0) - ?) ASC
>                LIMIT ?""",
>             (industry, ticker.upper(), target_cap, limit),
>         )
>         peers.extend(industry_peers)
>     
>     # Step 2: Same sector (if need more)
>     if len(peers) < limit and sector and sector != "Unknown":
>         found_tickers = {p["ticker"] for p in peers}
>         exclude_placeholders = ", ".join(["?"] * (len(found_tickers) + 1))
>         exclude_list = [ticker.upper()] + list(found_tickers)
>         remaining = limit - len(peers)
>         
>         sector_peers = await self.db.fetchall(
>             f"""SELECT c.ticker, c.company_name, c.sector, c.industry,
>                        COALESCE(md.market_cap, 0) as market_cap
>                 FROM companies c
>                 LEFT JOIN cache.market_data md ON md.ticker = c.ticker
>                 WHERE c.sector = ? AND c.ticker NOT IN ({exclude_placeholders})
>                   AND EXISTS (SELECT 1 FROM cache.financial_data fd WHERE fd.ticker = c.ticker)
>                 ORDER BY ABS(COALESCE(md.market_cap, 0) - ?) ASC
>                 LIMIT ?""",
>             (sector, *exclude_list, target_cap, remaining),
>         )
>         peers.extend(sector_peers)
>     
>     return peers[:limit]
> ```
>
> **Task 2: CompanyService.find_peers()**
>
> In `company_service.py`, add:
> ```python
> async def find_peers(self, ticker: str, limit: int = 15) -> list[str]:
>     ticker = ticker.upper()
>     company = await self.company_repo.get_by_ticker(ticker)
>     if not company:
>         logger.warning("Cannot find peers: company %s not found", ticker)
>         return []
>     
>     sector = company.get("sector", "Unknown")
>     industry = company.get("industry", "Unknown")
>     if sector == "Unknown" and industry == "Unknown":
>         logger.warning("Cannot find peers for %s: no sector/industry data", ticker)
>         return []
>     
>     # Get market cap for proximity sorting
>     from repositories.market_data_repo import MarketDataRepo
>     market_repo = MarketDataRepo(self.company_repo.db)
>     md = await market_repo.get_market_data(ticker)
>     market_cap = md.get("market_cap") if md else None
>     
>     peers = await self.company_repo.find_peers(ticker, sector, industry, market_cap, limit)
>     return [p["ticker"] for p in peers]
> ```
>
> **Task 3: CompsResult Status + Null Safety**
>
> In `engines/models.py`:
> - Add `status: str = "ready"` to CompsResult
> - Change peer_group default: `peer_group: dict = Field(default_factory=lambda: {"peers": [], "count": 0})`
>
> In `engines/comps_engine.py`:
> - At the start of `run()`: if `peer_data` is None or empty, return:
>   ```python
>   return CompsResult(
>       ticker=assumption_set.ticker,
>       current_price=current_price,
>       status="no_peers",
>       peer_group={"peers": [], "count": 0},
>       metadata=CompsMetadata(warnings=["No peer companies available. Add peers to run comparisons."]),
>   )
>   ```
> - Wrap the rest of `run()` in try/except:
>   ```python
>   except Exception as exc:
>       logger.exception("Comps engine error for %s", assumption_set.ticker)
>       return CompsResult(
>           ticker=assumption_set.ticker,
>           current_price=current_price,
>           status="error",
>           metadata=CompsMetadata(warnings=[f"Comps analysis failed: {exc}"]),
>       )
>   ```
>
> **Task 4: Auto-Discover Peers in Router**
>
> In `models_router.py`, in `run_comps`:
> - If `body.peer_tickers` is None or empty, call `company_svc.find_peers(ticker)` 
> - Access via `request.app.state.company_service`
> - Same for `run_all_models` and `generate_overview`
>
> **Task 5: Ensure CompanyService on app.state**
>
> Check `main.py`. If `company_service` isn't initialized, add it after the existing service initialization block.
>
> **Acceptance criteria:**
> 1. find_peers returns companies in same industry/sector with cached financial data
> 2. Prioritizes same industry, falls back to same sector
> 3. Sorted by market cap proximity
> 4. Only includes companies with financial_data (can compute multiples)
> 5. CompsResult has `status` field: "ready", "no_peers", or "error"
> 6. CompsResult.peer_group defaults to `{"peers": [], "count": 0}` (never None/empty dict)
> 7. CompsEngine.run() with no peers returns status="no_peers" (no crash)
> 8. CompsEngine.run() wraps in try/except → status="error" on failure
> 9. run_comps auto-discovers peers when peer_tickers not provided
> 10. run_all_models and generate_overview also auto-discover
> 11. company_service on app.state
> 12. Existing manual peer functionality still works
>
> **Files to create:** None
>
> **Files to modify:**
> - `backend/repositories/company_repo.py`
> - `backend/services/company_service.py`
> - `backend/engines/models.py`
> - `backend/engines/comps_engine.py`
> - `backend/routers/models_router.py`
> - `backend/main.py` (if company_service not already registered)
>
> **Technical constraints:**
> - Python 3.12, FastAPI, Pydantic v2
> - SQLite: uses attached `cache` schema for market_cache.db tables
> - Parameterized queries with `?` placeholders
> - `companies` table is in `user_data.db` (default schema), `financial_data` and `market_data` are in `cache` schema
> - Cross-database JOIN syntax: `cache.financial_data`, `cache.market_data` (SQLite attached databases)
> - Cap peer discovery at 20 peers max to avoid slow queries
> - Log auto-discovery results for debugging
