# Code Review Report — Phase 1 (Foundation + Data Layer)

**Date:** 2026-03-02
**Reviewer:** Claude Code Review Bot (4-Agent Pipeline)
**Scope:** backend/models, backend/routers, backend/services, backend/providers, backend/db, frontend core

---

## Executive Summary

| Metric                          | Count |
|---------------------------------|-------|
| Files reviewed                  | 65    |
| Backend Python issues           | 26    |
| Frontend TypeScript issues      | 27    |
| Consistency/spec violations     | 15    |
| **Auto-fixed**                  | **8** |
| Needs manual attention          | 12    |
| Flagged for design review       | 10    |

**Critical runtime bugs found and fixed:** 3 field-name mismatches that caused silent data corruption (WACC tax rate, peer book value, engine config loading). These were producing incorrect valuation results for every company without any error messages.

**Critical unfixed bugs (under active dev):** 2 more field-name mismatches in `engines/` directory (restricted from modification) — `comps_engine.py` uses `book_value` instead of `stockholders_equity`, and `revbased_engine.py` uses `operating_expenses` instead of `operating_expense`.

**Critical frontend bug fixed:** Settings store `setMany()` was calling a nonexistent `PUT /api/v1/settings/` endpoint — bulk settings updates were silently failing.

---

## Repairs Applied

### Fix 1: `config.py:41` — `get_setting()` → `get()`
- **File:** `backend/services/assumption_engine/config.py`
- **Before:** `await settings_service.get_setting("assumption_engine")`
- **After:** `await settings_service.get("assumption_engine")`
- **Impact:** Engine config overrides from Settings were *never* loading because `get_setting()` doesn't exist on `SettingsService`. The `except Exception` clause silently swallowed the `AttributeError`, so the feature appeared to work but config overrides were ignored.
- **Verified:** Yes — compiles clean

### Fix 2: `wacc.py:84` — `tax_expense` → `tax_provision`
- **File:** `backend/services/assumption_engine/wacc.py`
- **Before:** `latest.get("tax_expense")`
- **After:** `latest.get("tax_provision")`
- **Impact:** WACC calculation always used the default 21% tax rate instead of the company's actual effective tax rate. The DB schema and `FinancialPeriod` model both use `tax_provision`, not `tax_expense`. This means **every WACC calculation was incorrect** for companies with non-21% effective tax rates.
- **Verified:** Yes — compiles clean

### Fix 3: `models_router.py:309` — `book_value` → `stockholders_equity`
- **File:** `backend/routers/models_router.py`
- **Before:** `latest.get("book_value") or 0`
- **After:** `latest.get("stockholders_equity") or 0`
- **Impact:** All peer companies in Comps analysis had `book_value=0`, making P/B multiple computation return `None` for every peer. The DB schema uses `stockholders_equity`, not `book_value`.
- **Verified:** Yes — compiles clean

### Fix 4: `base.py:147` — `datetime.utcnow` → `datetime.now(timezone.utc)`
- **File:** `backend/providers/base.py`
- **Before:** `fetched_at: datetime = Field(default_factory=datetime.utcnow)`
- **After:** `fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))`
- **Also added:** `timezone` to the `datetime` import
- **Impact:** `datetime.utcnow()` is deprecated in Python 3.12 and returns naive datetime (no timezone). Other files like `backup_service.py` use `datetime.now(timezone.utc)` (timezone-aware). Mixing naive and aware datetimes causes comparison errors.
- **Verified:** Yes — compiles clean

### Fix 5: `data_extraction_service.py:156,209` — `callable` → `Callable`
- **File:** `backend/services/data_extraction_service.py`
- **Before:** `dict[str, callable]` (lowercase — the builtin function, not a type)
- **After:** `dict[str, Callable]` (from `typing`)
- **Also added:** `Callable` to the `typing` import
- **Impact:** Type annotation didn't express the intended constraint. `callable` is the builtin function (returns `bool`), not a type constructor. Static type checkers would flag this.
- **Verified:** Yes — compiles clean

### Fix 6: `backup_service.py:66` — `asyncio.get_event_loop()` → `asyncio.get_running_loop()`
- **File:** `backend/services/backup_service.py`
- **Before:** `loop = asyncio.get_event_loop()`
- **After:** `loop = asyncio.get_running_loop()`
- **Impact:** `get_event_loop()` is deprecated in Python 3.10+ when called from within an async function. `get_running_loop()` is the correct replacement.
- **Verified:** Yes — compiles clean

### Fix 7: `settings_router.py` — Added bulk `PUT /` endpoint
- **File:** `backend/routers/settings_router.py`
- **Added:** `PUT /api/v1/settings/` endpoint that accepts a JSON body of key-value pairs and calls `svc.set_many()`
- **Impact:** The frontend `settingsStore.ts:51` `setMany()` function sends `PUT /api/v1/settings/` with a JSON body, but no such handler existed. Bulk settings updates were silently failing (optimistic UI update succeeded, but persistence didn't). Settings would revert on next app load.
- **Verified:** Yes — compiles clean

### Fix 8: `uiStore.ts:16-21` — Added `api_calls_remaining` to `SystemStatus`
- **File:** `frontend/src/stores/uiStore.ts`
- **Added:** `api_calls_remaining: number | null;` to the `SystemStatus` interface
- **Impact:** The WebSocket `SystemStatusMessage` type (`types/api.ts:67`) includes `api_calls_remaining`, but the store's `SystemStatus` interface omitted it. The field was silently dropped when `updateSystemStatus(msg.data)` was called.
- **Verified:** Yes — TypeScript type alignment restored

---

## Outstanding Items (Sorted by Priority)

### PRIORITY 1: Runtime Bugs in Restricted Files (needs dev attention)

1. **`backend/engines/comps_engine.py:301,376` — `book_value` should be `stockholders_equity`**
   - Same bug as Fix 3 but inside the Comps engine (restricted directory)
   - `latest.get("book_value")` always returns `None` — P/B implied value never computed
   - `_assess_quality()` at line 376 also uses `book_value` — ROE quality factor broken
   - **Action:** Change `book_value` → `stockholders_equity` in both locations

2. **`backend/engines/revbased_engine.py:254` — `operating_expenses` should be `operating_expense`**
   - DB schema uses singular `operating_expense` (confirmed in `init_cache_db.py:26`)
   - `opex = latest.get("operating_expenses")` always returns `None`
   - Magic number metric computation is completely skipped for every company
   - **Action:** Change `operating_expenses` → `operating_expense`

### PRIORITY 2: Frontend Architecture Issues

3. **Hardcoded `localhost:8000` URLs in 4 locations**
   - `frontend/src/services/api.ts:8` — `BASE_URL = 'http://localhost:8000'`
   - `frontend/src/services/websocket.ts:9` — `WS_BASE = 'ws://localhost:8000'`
   - `frontend/src/App.tsx:31` — health check URL
   - `frontend/src/stores/settingsStore.ts:19,36,51` — raw fetch calls
   - `vite-env.d.ts` defines `ElectronAPI.getBackendUrl()` but it's never used
   - **Recommendation:** Create a shared `getBaseUrl()` utility; use it in api.ts, websocket.ts, and settingsStore.ts

4. **`settingsStore.ts` bypasses the `api` service layer entirely**
   - Uses raw `fetch()` with manual response parsing instead of the `api` wrapper
   - Inconsistent error handling and response envelope unwrapping
   - **Recommendation:** Refactor to use `api.get()`, `api.put()` from `services/api.ts`

### PRIORITY 3: Spec-Code Divergences (design decisions needed)

5. **Model type naming: `"revenue_based"` vs `"revbased"`**
   - URL uses `revbased` (`/run/revbased`), DB table uses `revbased` (`revbased_assumptions`)
   - Code uses `"revenue_based"` everywhere (`model_detection_service.py`, `engines/models.py`, `modelStore.ts`)
   - Spec phase0b says `"revbased"`, spec phase6 says standardize to `"revbased"`
   - **Decision needed:** Pick one and standardize everywhere

6. **5 different names for "implied share price" across engines**
   - DCF: `implied_price`, `weighted_implied_price`
   - DDM: `intrinsic_value_per_share`, `weighted_intrinsic_value`
   - Comps: `raw_implied_price`
   - RevBased: `implied_price`, `primary_implied_price`
   - DB: `intrinsic_value_per_share`
   - **Decision needed:** Standardize to one name (suggest `implied_price` since DCF and RevBased already use it)

7. **API architecture diverged from spec (ticker-based vs model_id-based)**
   - Spec: `POST /model/{model_id}/run` (model_id-centric)
   - Code: `POST /{ticker}/run/dcf|ddm|comps|revbased` (ticker-centric, per-engine)
   - This is intentional/better for the use case but spec should be updated
   - **Action:** Update `specs/phase0c_api_layer.md` to match actual implementation

8. **Detect endpoint: spec says POST, code uses GET**
   - Spec: `POST /api/v1/model-builder/detect` with body `{ ticker: string }`
   - Code: `GET /api/v1/model-builder/{ticker}/detect` with ticker as path param
   - Frontend matches the code (uses GET)
   - **Action:** Update spec to match code (GET with path param is more RESTful for reads)

9. **Market data endpoint: spec says `/market`, code uses `/quote`**
   - Spec: `GET /api/v1/companies/{ticker}/market`
   - Code: `GET /api/v1/companies/{ticker}/quote`
   - **Action:** Update spec or rename endpoint

10. **Error codes don't match spec table**
    - Code uses `ENGINE_ERROR` — spec has `CALCULATION_ERROR`
    - Code uses `NO_QUOTE` — not in spec
    - **Action:** Either update spec's error code table or update the code error codes

### PRIORITY 4: Code Quality Warnings

11. **SQL injection risk in `model_repo.py:57-68,81`**
    - `model_type` parameter used in f-string to build table name: `f"{model_type}_assumptions"`
    - Column names from user dicts interpolated directly in SQL
    - Currently mitigated by limited inputs, but should validate `model_type` against allowed values

12. **SQL injection risk in `db/connection.py:62`**
    - ATTACH DATABASE uses f-string: `f"ATTACH DATABASE '{str(self.cache_db_path)}' AS cache;"`
    - Should escape or validate the path

13. **`system_router.py:22` — accesses private `db._conn`**
    - Should use public API or try/except pattern

14. **WebSocket `msg.data` is unvalidated `any` in `websocket.ts`**
    - `JSON.parse(event.data)` returns `any` — malformed messages could crash

15. **`modelStore.ts:81` — unsafe cast `result.recommended_model as ModelType`**
    - If backend returns unexpected model type string, downstream UI will malfunction

### PRIORITY 5: Info / Nice-to-Have

16. **Universe endpoints duplicated** — `scanner_router.py` has `/universe/*` AND `universe_router.py` has separate `/api/v1/universe/*`
17. **`frontend/src/types/api.ts:42` — `is_stale` field never computed by backend**
18. **Frontend `PAGE_MAP` typed as `Record<string, ComponentType>` instead of `Record<ModuleId, ...>`**
19. **`scannerStore.ts` `reset()` doesn't reset `universe` field**
20. **API version `"1.0.0"` hardcoded in 3 places in `response.py`**
21. **`Tooltip.tsx` — `onFocus`/`onBlur` on non-focusable `<span>`**
22. **`SettingsPage.tsx` uses local `useState` instead of `uiStore` sub-tab tracking**

---

## Consistency Summary

### Tables: Spec vs Code
- All 23 spec'd tables are implemented in `init_user_db.py` and `init_cache_db.py`
- Column names and types match the spec (with the noted field name mismatches in application code)
- Foreign keys and indexes are present as specified

### Endpoints: Spec vs Code
- ~60% of spec'd endpoints are implemented (rest are stubs)
- Multiple extra endpoints exist in code but not spec (assumption engine, sensitivity, overview, extra company endpoints)
- HTTP methods and URL patterns diverge in several places (documented above)

### Frontend ↔ Backend
- All active frontend API calls target real backend endpoints (after Fix 7)
- Many backend endpoints have no frontend consumer yet (stubs awaiting UI implementation)
- Data shapes generally align between frontend types and backend responses

---

*Report generated by Claude Code Review Bot — Phase 1 Pipeline*
*Next: Run "Review Phase 2" for Scanner and Portfolio modules*
