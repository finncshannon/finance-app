# Phase 0C — API Layer & Frontend-Backend Communication
> Designer Agent | February 23, 2026
> Status: COMPLETE — APPROVED BY FINN
> Updated March 2026 to match implemented codebase.
> Depends on: Phase 0A (Foundation), Phase 0B (Database Schema)

---

## Overview

This document defines how the React/TypeScript frontend communicates with
the Python FastAPI backend. Every UI action maps to an API call defined here.

**Key decisions:**
- REST + WebSocket hybrid (REST for actions/queries, WebSocket for live price streaming)
- Module-grouped URL structure mirroring UI tabs
- Consistent JSON response envelope on all endpoints
- Strict API contract with documented request/response types
- Full loading screen with progress bar for model calculations
- API versioned at /api/v1/

---

## Communication Architecture

```
┌─────────────────────────────────────────────┐
│              Electron App (Renderer)         │
│                                              │
│  React Frontend (TypeScript)                 │
│  ├── REST calls (fetch/axios) ──────────────────┐
│  └── WebSocket connection ──────────────────────┐│
│                                              │  ││
└─────────────────────────────────────────────┘  ││
                                                  ││
┌─────────────────────────────────────────────┐  ││
│              Electron App (Main Process)     │  ││
│                                              │  ││
│  Spawns & manages FastAPI backend            │  ││
│  localhost:8000 (never exposed externally)   │  ││
│                                              │  ││
└─────────────────────────────────────────────┘  ││
                                                  ││
┌─────────────────────────────────────────────┐  ││
│              FastAPI Backend (Python)        │◄─┘│
│                                              │◄──┘
│  /api/v1/*  (REST endpoints)                 │
│  /ws/prices (WebSocket - live prices)        │
│  /ws/status (WebSocket - system health)      │
│                                              │
│  ├── SQLite: user_data.db                    │
│  ├── SQLite: market_cache.db                 │
│  ├── Yahoo Finance API                       │
│  └── SEC EDGAR API                           │
└─────────────────────────────────────────────┘
```

**Why hybrid REST + WebSocket:**
- REST handles 95% of operations (CRUD, calculations, searches)
- WebSocket handles the one thing REST can't: server-initiated push
- Live prices need to push to the UI every 60 seconds without polling
- Both are independently editable — if WebSocket causes issues,
  fall back to REST polling without changing any other code

---

## Response Envelope

Every REST endpoint returns this structure. No exceptions.

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": {
    "timestamp": "2026-02-23T14:30:00Z",
    "duration_ms": 45,
    "version": "1.0.0"
  }
}
```

### Error Response
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "TICKER_NOT_FOUND",
    "message": "No company found for ticker 'XYZZ'",
    "details": {}
  },
  "meta": {
    "timestamp": "2026-02-23T14:30:00Z",
    "duration_ms": 12,
    "version": "1.0.0"
  }
}
```

### TypeScript Type (Frontend)
```typescript
interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: ApiError | null;
  meta: {
    timestamp: string;
    duration_ms: number;
    version: string;
  };
}

interface ApiError {
  code: string;
  message: string;
  details: Record<string, any>;
}
```

### Python Model (Backend)
```python
class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[ApiError] = None
    meta: ResponseMeta

class ApiError(BaseModel):
    code: str
    message: str
    details: dict = {}

class ResponseMeta(BaseModel):
    timestamp: datetime
    duration_ms: int
    version: str = "1.0.0"
```

---

## Error Codes

Standardized error codes used across all endpoints:

| Code | HTTP Status | Meaning |
|------|------------|---------|
| TICKER_NOT_FOUND | 404 | Company ticker doesn't exist |
| MODEL_NOT_FOUND | 404 | No model exists for this ticker/type |
| VALIDATION_ERROR | 422 | Request body failed validation |
| CALCULATION_ERROR | 500 | Model calculation failed |
| DATA_FETCH_ERROR | 502 | Yahoo Finance or SEC API failed |
| RATE_LIMITED | 429 | Too many API requests to external service |
| DATABASE_ERROR | 500 | SQLite operation failed |
| STALE_DATA | 200 | Data returned but older than expected (in meta) |
| NOT_ENOUGH_DATA | 422 | Insufficient historical data for this model |

---

## Endpoint Catalog

### Companies — /api/v1/companies

| Method | Path | Purpose |
|--------|------|---------|
| GET | /search?q= | Search companies |
| GET | /{ticker} | Company info |
| GET | /{ticker}/quote | Live quote |
| GET | /{ticker}/historical | Historical prices |
| GET | /{ticker}/financials | Financial data |
| GET | /{ticker}/metrics | Key metrics |
| GET | /{ticker}/filings | SEC filings list |
| GET | /{ticker}/events | Upcoming events |
| POST | /lookup | Batch lookup |
| POST | /{ticker}/refresh | Refresh data |

---

### Model Builder — /api/v1/model-builder

| Method | Path | Purpose |
|--------|------|---------|
| GET | /{ticker}/detect | Auto-detect best model type |
| POST | /{ticker}/generate | Generate assumptions |
| GET | /{ticker}/assumptions | Get current assumptions |
| PUT | /{ticker}/assumptions | Update assumptions |
| POST | /{ticker}/assumptions/reset | Reset to generated defaults |
| POST | /{ticker}/run/dcf | Run DCF engine |
| POST | /{ticker}/run/ddm | Run DDM engine |
| POST | /{ticker}/run/comps | Run Comps engine |
| POST | /{ticker}/run/revbased | Run Revenue-Based engine |
| POST | /{ticker}/run/all | Run all engines |
| GET | /{ticker}/models | List models for ticker |
| GET | /model/{model_id} | Get model by ID |
| POST | /model/{model_id}/run | Run model by ID |
| PUT | /model/{model_id}/assumptions | Update model assumptions |
| POST | /model/{model_id}/save-version | Save version snapshot |
| GET | /model/{model_id}/versions | List versions |
| GET | /model/{model_id}/version/{version_id} | Get specific version |
| GET | /model/{model_id}/outputs | List outputs |
| GET | /model/{model_id}/output/{output_id} | Get specific output |
| POST | /{ticker}/sensitivity/slider | Slider sensitivity |
| POST | /{ticker}/sensitivity/tornado | Tornado chart data |
| POST | /{ticker}/sensitivity/monte-carlo | Monte Carlo simulation |
| POST | /{ticker}/sensitivity/table-2d | 2D data table |
| GET | /{ticker}/sensitivity/parameters | Get sensitivity params |
| POST | /{ticker}/overview | Model overview + football field |

---

### Scanner — /api/v1/scanner

| Method | Path | Purpose |
|--------|------|---------|
| POST | /screen | Run screen with filters |
| POST | /filter | Filter existing results |
| POST | /search | Text search companies |
| POST | /rank | Rank/sort results |
| GET | /presets | List saved presets |
| POST | /presets | Save preset |
| DELETE | /presets/{preset_id} | Delete preset |
| GET | /metrics | Available filter metrics |
| GET | /universe | Get universe tickers |
| GET | /universe/stats | Universe statistics |

---

### Portfolio — /api/v1/portfolio

| Method | Path | Purpose |
|--------|------|---------|
| GET | /positions | List positions |
| POST | /positions | Add position |
| PUT | /positions/{position_id} | Update position |
| DELETE | /positions/{position_id} | Delete position |
| GET | /lots/{position_id} | Get tax lots |
| GET | /transactions | List transactions |
| POST | /transactions | Record transaction |
| GET | /summary | Portfolio summary |
| GET | /performance | Performance metrics |
| GET | /benchmark | Benchmark comparison |
| GET | /attribution | Performance attribution |
| GET | /income | Dividend income |
| POST | /import/preview | Preview CSV import |
| POST | /import/execute | Execute CSV import |
| GET | /accounts | List accounts |
| POST | /accounts | Create account |
| PUT | /accounts/{account_id} | Update account |
| DELETE | /accounts/{account_id} | Delete account |
| GET | /alerts | List price alerts |
| POST | /alerts | Create alert |
| DELETE | /alerts/{alert_id} | Delete alert |
| GET | /implied-prices | Implied prices from models |

---

### Research — /api/v1/research

| Method | Path | Purpose |
|--------|------|---------|
| GET | /{ticker}/profile | Company profile |
| GET | /{ticker}/filings | Filing list |
| GET | /{ticker}/filing/{filing_id} | Filing detail + sections |
| GET | /{ticker}/financials | Financial statements |
| GET | /{ticker}/ratios | Financial ratios |
| GET | /{ticker}/ratios/history | Ratio trend history |
| GET | /{ticker}/peers | Peer companies |
| POST | /{ticker}/compare-filings | Compare filing sections |
| GET | /{ticker}/notes | Research notes |
| POST | /{ticker}/notes | Add note |
| PUT | /notes/{note_id} | Update note |
| DELETE | /notes/{note_id} | Delete note |

---

### Dashboard — /api/v1/dashboard

| Method | Path | Purpose |
|--------|------|---------|
| GET | /summary | Full dashboard payload |
| GET | /market | Market overview |
| GET | /models/recent | Recent models |
| GET | /events | Upcoming events |
| GET | /watchlists | All watchlists |
| GET | /watchlists/{watchlist_id} | Single watchlist |
| POST | /watchlists | Create watchlist |
| PUT | /watchlists/{watchlist_id} | Update watchlist |
| DELETE | /watchlists/{watchlist_id} | Delete watchlist |
| POST | /watchlists/{watchlist_id}/items | Add ticker to watchlist |
| DELETE | /watchlists/{watchlist_id}/items/{ticker} | Remove ticker |
| PUT | /watchlists/{watchlist_id}/items/reorder | Reorder items |

---

### Settings — /api/v1/settings

| Method | Path | Purpose |
|--------|------|---------|
| GET | / | All settings |
| GET | /system-info | System information |
| GET | /database-stats | Database statistics |
| GET | /cache-size | Cache size |
| POST | /clear-cache | Clear cache |
| GET | /{key} | Get single setting |
| PUT | / | Bulk update settings |
| PUT | /{key} | Update single setting |

---

### Export — /api/v1/export

| Method | Path | Purpose |
|--------|------|---------|
| POST | /model/{model_id}/excel | Export model to Excel |
| POST | /model/{model_id}/pdf | Export model to PDF |
| POST | /scanner/excel | Export scanner to Excel |
| POST | /scanner/csv | Export scanner to CSV |
| POST | /portfolio/excel | Export portfolio to Excel |
| POST | /portfolio/pdf | Export portfolio to PDF |
| POST | /research/{ticker}/excel | Export research to Excel |

---

### System — /api/v1/system

| Method | Path | Purpose |
|--------|------|---------|
| GET | /health | Health check |
| GET | /status | System status |
| POST | /clear-cache | Clear caches |
| POST | /backup | Create DB backup |
| GET | /backups | List backups |
| POST | /restore | Restore from backup |

---

### Universe — /api/v1/universe

| Method | Path | Purpose |
|--------|------|---------|
| GET | /stats | Universe statistics |
| GET | /tickers | List tickers |
| POST | /load | Load universe |
| POST | /refresh | Refresh universe |

---

## WebSocket Channels

### ws://localhost:8000/ws/prices
Live price updates pushed to frontend during market hours.

**Connection:** Frontend opens on app launch, maintains throughout session.

**Server → Client message format:**
```json
{
  "type": "price_update",
  "data": {
    "AAPL": {
      "current_price": 182.52,
      "day_change": 1.23,
      "day_change_pct": 0.68,
      "volume": 52340000,
      "updated_at": "2026-02-23T14:30:00Z"
    },
    "MSFT": { ... },
    "GOOG": { ... }
  }
}
```

**Behavior:**
- During market hours: pushes updates every 60 seconds
- Off-hours: pushes once on connection, then silent
- Only sends data for tickers the user has in portfolio + watchlists + open models
- Frontend subscribes by sending:
  ```json
  { "type": "subscribe", "tickers": ["AAPL", "MSFT", "GOOG"] }
  ```
- Frontend can update subscription:
  ```json
  { "type": "subscribe", "tickers": ["AAPL", "MSFT", "GOOG", "AMZN"] }
  ```

### ws://localhost:8000/ws/status
System health updates.

**Server → Client message format:**
```json
{
  "type": "system_status",
  "data": {
    "market_open": true,
    "last_price_refresh": "2026-02-23T14:30:00Z",
    "active_refresh_tickers": 15,
    "api_calls_remaining": 1850,
    "backend_uptime_seconds": 3600
  }
}
```

---

## Loading States

Every API call from the frontend needs a defined loading behavior.

### Instant (< 200ms expected)
No visible loading state. Data appears immediately.
- GET /api/v1/settings
- GET /api/v1/dashboard/watchlists
- PUT /api/v1/model-builder/model/{id}/assumptions (saves only, no calc)
- POST /api/v1/research/{ticker}/notes

### Quick Loader (200ms - 2s expected)
Subtle inline loading indicator. Content area shows skeleton or spinner.
- GET /api/v1/companies/{ticker}
- GET /api/v1/companies/{ticker}/financials
- GET /api/v1/companies/{ticker}/market
- GET /api/v1/portfolio/positions
- GET /api/v1/dashboard/summary
- POST /api/v1/model-builder/detect

### Full Loading Screen (2s+ expected)
Full screen overlay with progress bar. Blocks all interaction.
User pressed a deliberate action button ("Run Model", "Screen", "Export").
- POST /api/v1/model-builder/model/{id}/run
- POST /api/v1/scanner/screen
- POST /api/v1/export/* (file generation)
- POST /api/v1/companies/{ticker}/refresh (full data re-fetch)

### Loading Screen Design
```
┌─────────────────────────────────────────┐
│                                         │
│                                         │
│          Running DCF Model...           │
│          AAPL — Apple Inc.              │
│                                         │
│     ████████████░░░░░░░░  62%           │
│                                         │
│     Building projections...             │
│                                         │
│                                         │
└─────────────────────────────────────────┘
```

Progress stages reported by the model calculation:
1. "Loading financial data..." (0-10%)
2. "Generating assumptions..." (10-30%)
3. "Building projections..." (30-50%)
4. "Calculating terminal value..." (50-60%)
5. "Running scenarios..." (60-75%)
6. "Running sensitivity analysis..." (75-90%)
7. "Preparing visualizations..." (90-100%)

For Monte Carlo specifically:
- "Running Monte Carlo simulation (2,847 / 10,000 iterations)..."
- Progress bar tracks actual iteration count

---

## Request Flow Examples

### Example 1: User opens Model Builder and types "AAPL"

```
1. POST /api/v1/companies/lookup { ticker: "AAPL" }
   → Returns company profile, is_new: false, data_available: true

2. POST /api/v1/model-builder/detect { ticker: "AAPL" }
   → Returns detection results: DCF recommended (score 95),
     DDM applicable (score 80), Comps applicable (score 70)
   → Frontend shows detection reasoning panel

3. GET /api/v1/companies/AAPL/financials
   → Returns 10 years of financial data
   → Frontend renders Bloomberg-style historical data view

4. GET /api/v1/companies/AAPL/market
   → Returns current price, multiples, etc.
   → Frontend renders ticker header bar

5. GET /api/v1/model-builder/AAPL/models
   → Returns existing models (if any) for AAPL
   → If DCF model exists: load it with saved assumptions
   → If no DCF model exists: create new one with engine defaults
```

### Example 2: User adjusts assumptions and runs model

```
1. PUT /api/v1/model-builder/model/42/assumptions
   { updates: { revenue_growth_yr1: 0.12, wacc: 0.095 } }
   → Saves overrides, marks as user-modified
   → No calculation yet

2. User clicks "Run Model"

3. POST /api/v1/model-builder/model/42/run
   → Frontend shows full loading screen with progress bar
   → Backend calculates: projections → terminal value → scenarios → sensitivity
   → Returns complete ModelRunResult
   → Frontend hides loading screen, renders all results

4. User reviews results, clicks "Save Version"

5. POST /api/v1/model-builder/model/42/save-version
   { annotation: "Adjusted revenue growth after Q4 beat" }
   → Compresses and saves full snapshot
```

### Example 3: User runs a screen in Scanner

```
1. POST /api/v1/scanner/screen
   {
     keywords: ["artificial intelligence", "machine learning"],
     filters: [
       { metric: "revenue_growth", operator: "gt", value: 0.15 },
       { metric: "market_cap", operator: "gt", value: 10000000000 }
     ],
     universe: "sp500",
     form_types: ["10-K"],
     limit: 25
   }
   → Frontend shows full loading screen
   → Backend searches filings + applies filters
   → Returns ranked results with excerpts

2. User right-clicks a result → "Run Model"
   → Smooth tab switch to Model Builder
   → Triggers the same flow as Example 1
```

### Example 4: App launch sequence

```
1. GET /api/v1/system/health
   → Verify backend is running

2. GET /api/v1/settings
   → Load user preferences, window state, last ticker

3. Open WebSocket: ws://localhost:8000/ws/prices
   → Subscribe to portfolio + watchlist tickers

4. GET /api/v1/dashboard/summary
   → Load dashboard data (portfolio summary, watchlists, recent models)

5. Open WebSocket: ws://localhost:8000/ws/status
   → Receive market status updates

Total expected startup time: < 2 seconds
```

---

## Backend Startup Sequence

When Electron launches, the main process starts FastAPI:

1. **Spawn Python process** — `python -m uvicorn main:app --port 8000`
2. **Wait for health check** — poll GET /api/v1/system/health until 200
3. **Initialize databases** — run migrations if needed, create tables
4. **Start price refresh timer** — begins 60-second cycle for subscribed tickers
5. **Signal ready to renderer** — Electron main → renderer IPC message
6. **Renderer begins API calls** — dashboard load sequence starts

If the backend fails to start within 10 seconds, Electron shows an
error dialog with the Python stderr output for debugging.

---

## CORS & Security

Since frontend and backend are in the same Electron app:
- No CORS needed (both on localhost)
- No authentication needed (single-user local app)
- No HTTPS needed (localhost only, never exposed)
- No rate limiting on internal endpoints
- Rate limiting only on external API calls (Yahoo Finance, SEC EDGAR)

---

## Endpoint Count Summary

| Module | Endpoints |
|--------|-----------|
| Companies | 10 |
| Model Builder | 25 |
| Scanner | 10 |
| Portfolio | 22 |
| Research | 12 |
| Dashboard | 12 |
| Settings | 8 |
| Export | 7 |
| System | 6 |
| Universe | 4 |
| WebSocket | 2 |
| **Total** | **~118** |

---

## Implementation Notes for Architect

1. **FastAPI router structure** — one router file per module:
   `routers/companies.py`, `routers/model_builder.py`, etc.
   Mirrors the URL grouping exactly.

2. **Pydantic models for every endpoint** — strict request/response
   validation. TypeScript types generated from Pydantic models
   to keep frontend and backend in sync.

3. **WebSocket manager class** — handles connection lifecycle,
   subscription management, and broadcast to connected clients.
   Only one client expected (the Electron renderer), but design
   for potential future multi-window support.

4. **Background price refresh** — use FastAPI's `BackgroundTasks` or
   `asyncio` timer. Fetches prices for all subscribed tickers,
   writes to market_data table, broadcasts via WebSocket.

5. **Model calculation is synchronous** — the /run endpoint blocks
   until complete. No need for task queues or job systems.
   The frontend loading screen handles the wait.

6. **Export endpoints return file paths** — Electron's main process
   then opens a Save dialog and copies the file to the user's
   chosen location.

7. **Database access pattern** — each endpoint opens its own
   connection from a pool. Use `aiosqlite` for async SQLite access.
   user_data.db attached as main, market_cache.db via ATTACH.
