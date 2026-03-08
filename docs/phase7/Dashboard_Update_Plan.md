# Finance App — Dashboard Update Plan
## Phase 7: Dashboard Tab

**Prepared by:** Planner (March 4, 2026)
**Recipient:** PM Agent
**Scope:** Dashboard page, Boot Sequence, and new Portfolio "Upcoming Events" sub-tab

---

## PLAN SUMMARY

Three workstreams for the Dashboard update:

1. **Boot Sequence Enhancement** — Longer animation, more boot lines, staggered dashboard widget entry animations, sound infrastructure
2. **Upcoming Events Overhaul** — Complete redesign of events system: dashboard widget with source/type toggles + week view, new Portfolio sub-tab for full calendar, backend event fetcher with S&P 500 support
3. **Minor Polish** — Refresh button spinner, events loading state, silent error handling cleanup

---

## AREA 1: BOOT SEQUENCE ENHANCEMENT

### Current State
- Total boot duration: ~2 seconds (200ms black → 600ms terminal → 700ms shift → 500ms fadeout)
- 5 boot lines: Database connected, Market data service, Model engine loaded, Portfolio sync, UI components ready
- After fadeout, dashboard renders instantly with all widgets appearing at once
- No sound

### What Changes

#### 1A. Longer Boot Animation
**Goal:** Stretch boot to ~4–5 seconds with a more immersive terminal feel.

**Changes to `BootSequence.tsx` and `BootPhase.tsx`:**
- Increase phase timings: black 300ms → terminal 1500ms → shift 800ms → fadeout 600ms
- Add more boot lines (8–10 total). Suggested additions:
  - `├── Scanning universe`
  - `├── Syncing portfolio`
  - `├── Loading watchlists`
  - `├── Connecting market feeds`
  - Keep existing 5, reorder for logical flow
- Slow stagger between lines from 70ms to 100–120ms
- Slow checkmark stagger from 60ms to 80–100ms
- Add a brief "All systems online" status line after all checkmarks complete, before shift phase begins
- Add a subtle pulsing cursor/caret on the status line while boot lines are appearing

**Files touched:**
- `frontend/src/components/BootSequence/BootSequence.tsx` — phase timing constants
- `frontend/src/components/BootSequence/BootPhase.tsx` — boot lines array, stagger timing, new completion line
- `frontend/src/components/BootSequence/BootSequence.module.css` — cursor animation, timing adjustments

#### 1B. Dashboard Widget Entry Animations
**Goal:** After boot overlay fades, dashboard widgets animate in with a staggered cascade rather than appearing all at once. Creates the "loading up" feel.

**Behavior:**
- Boot overlay fades out (existing behavior)
- Dashboard page renders but widgets start invisible/below
- Staggered reveal order (150–200ms between each):
  1. Market Overview (top-left) — fade-up + subtle scale
  2. Portfolio Summary (top-right) — fade-up + subtle scale
  3. Watchlist (full-width middle) — fade-up + subtle scale
  4. Recent Models (bottom-left) — fade-up + subtle scale
  5. Upcoming Events (bottom-right) — fade-up + subtle scale
- Each widget animates over ~300ms (opacity 0→1, translateY 12px→0, scale 0.98→1)
- Total cascade: ~1.2 seconds from first widget to last widget fully visible
- This animation only plays on initial app boot, NOT on tab switching back to Dashboard

**Implementation approach:**
- Add a `booted` flag from App.tsx passed to DashboardPage (or via uiStore)
- DashboardPage tracks `animationPhase` state, incrementing on timers after mount when `booted` transitions
- Each grid cell gets a CSS class toggled by animation phase
- CSS handles the transitions via opacity/transform with `transition` property
- On subsequent visits to Dashboard tab (not first boot), all widgets render immediately

**Files touched:**
- `frontend/src/pages/Dashboard/DashboardPage.tsx` — animation phase logic, conditional classes
- `frontend/src/pages/Dashboard/DashboardPage.module.css` — widget entry animation classes
- `frontend/src/App.tsx` — pass `justBooted` prop or set uiStore flag after boot completes
- `frontend/src/stores/uiStore.ts` — add `justBooted` flag (set true on boot complete, never reset during session)

#### 1C. Sound Infrastructure
**Goal:** Build the plumbing for startup sounds without committing to specific audio files. Finn will test and approve sounds before they ship.

**Implementation:**
- Create `frontend/src/services/soundManager.ts`:
  - Uses Web Audio API (`AudioContext`)
  - Exposes `playBootTick()`, `playBootComplete()`, `playStartupTone()` methods
  - Reads a `sound_enabled` setting from settingsStore (default: true)
  - Methods are no-ops when sound is disabled
  - Audio files loaded from `frontend/public/sounds/` (or Electron resources)
- Add hook points in BootPhase:
  - `playBootTick()` on each boot line appearance
  - `playBootComplete()` when all checkmarks finish
  - `playStartupTone()` at phase transition to shift (the "all systems go" moment)
- Add sound toggle in Settings → General section
- Ship with placeholder silent files or very minimal procedural beeps via Web Audio API oscillator (can be replaced with real audio files later)

**Sound direction (for future audio file selection):**
- Futuristic / holographic feel (Star Wars, Iron Man aesthetic)
- Boot ticks: short, clean, high-pitched digital clicks
- Completion: ascending tone or chord that resolves
- Startup tone: brief ambient swell

**Files touched:**
- `frontend/src/services/soundManager.ts` — new file
- `frontend/src/components/BootSequence/BootPhase.tsx` — call sound hooks
- `frontend/src/components/BootSequence/BootSequence.tsx` — call startup tone on shift phase
- `frontend/src/pages/Settings/sections/GeneralSection.tsx` — add sound toggle
- `frontend/public/sounds/` — new directory for audio assets (initially empty or with procedural fallbacks)
- `backend/services/settings_service.py` — add `sound_enabled` to default settings

---

## AREA 2: UPCOMING EVENTS OVERHAUL

### Current State
- Events come from `CompanyEventsService` which uses yfinance to fetch earnings dates and ex-dividend dates per ticker
- Events are only fetched on-demand (when a user researches or models a ticker) — no proactive fetching
- Dashboard widget shows a flat list of whatever is in the cache, no filtering, no source control
- "View All" button navigates to Research tab (not useful)
- No S&P 500 or general market events
- No way to control which tickers' events appear

### What Changes

#### 2A. Backend — S&P 500 Ticker List & Storage
**Goal:** Ship a static S&P 500 component list. Fetch and cache events for all 500 tickers with smart staleness management.

**S&P 500 List:**
- Store as `backend/data/sp500_tickers.json` — a JSON array of ~503 ticker strings
- Source: Wikipedia S&P 500 list or a one-time yfinance pull
- Add a Settings option to manually refresh (re-download) the list
- The app reads this file on startup to know which tickers constitute "Market" events

**Files touched:**
- `backend/data/sp500_tickers.json` — new file (static ticker list)
- `backend/services/universe_service.py` — add `get_sp500_tickers()` method that reads the JSON

#### 2B. Backend — Background Event Fetcher
**Goal:** On app startup, proactively fetch events for portfolio, watchlist, and S&P 500 tickers so the dashboard has data immediately.

**Behavior:**
- New `EventRefreshService` (or extend `CompanyEventsService`) with a `run_startup_fetch()` method
- Called as an `asyncio.create_task()` in `main.py` lifespan, after all services are initialized
- Fetch priority order:
  1. Portfolio tickers (small list, fetch all, ~5–30 tickers)
  2. Watchlist tickers across all watchlists (small list, fetch all)
  3. S&P 500 tickers (large list, only fetch stale ones)
- Staleness logic: skip any ticker where `company_events.fetched_at` is less than 7 days old
- For S&P 500: batch sequentially with a small delay (100ms between tickers) to avoid rate limiting from Yahoo Finance
- Log progress: "Refreshing events: 23/500 S&P 500 tickers (47 stale)"
- Cold start (empty cache): first run fetches all 500, takes ~8–10 minutes in background. Subsequent startups only refresh stale entries (~20–50 tickers, ~30 seconds)
- This runs in the background — dashboard renders immediately with whatever is in cache, then updates as new events arrive

**New endpoint:**
- `GET /api/v1/dashboard/events/refresh-status` — returns progress of background fetch (for optional UI indicator)

**Files touched:**
- `backend/services/company_events_service.py` — add `run_startup_fetch()`, staleness check, batch logic
- `backend/main.py` — add startup task for event refresh
- `backend/routers/dashboard_router.py` — add refresh-status endpoint

#### 2C. Backend — Filtered Events Endpoint
**Goal:** Allow the frontend to request events filtered by source (watchlist, portfolio, market) and event type (earnings, dividends).

**New/modified endpoint:**
- `GET /api/v1/dashboard/events` updated with query parameters:
  - `source`: `watchlist` | `portfolio` | `market` | `all` (default: `all`)
  - `watchlist_id`: optional, filters to specific watchlist when source=watchlist
  - `event_types`: comma-separated, e.g. `earnings,ex_dividend` (default: all types)
  - `date_from`: ISO date string (default: today)
  - `date_to`: ISO date string (default: none, meaning all future)
  - `limit`: integer (default: 10 for dashboard, higher for full view)
  - `offset`: integer for pagination in full view

**Source resolution logic (backend):**
- `watchlist` → get all tickers from specified watchlist (or all watchlists if no ID) → filter events to those tickers
- `portfolio` → get all tickers from portfolio positions → filter events to those tickers
- `market` → get all tickers from sp500_tickers.json → filter events to those tickers
- Deduplication: if a ticker appears in multiple sources, show it once (prioritize portfolio > watchlist > market)

**Response format:**
```json
{
  "events": [
    {
      "date": "2026-03-10",
      "ticker": "AAPL",
      "event_type": "earnings",
      "detail": "Earnings (est. EPS 2.35)",
      "source": "portfolio",
      "is_estimated": true
    }
  ],
  "total_count": 47,
  "has_more": true
}
```

**Files touched:**
- `backend/routers/dashboard_router.py` — update events endpoint with new params
- `backend/services/dashboard_service.py` — new `get_filtered_events()` method with source resolution
- `backend/services/company_events_service.py` — add `get_events_for_tickers()` batch query method
- `backend/repositories/market_data_repo.py` — add `get_upcoming_events_for_tickers()` with ticker list filter

#### 2D. Frontend — Dashboard Events Widget Redesign
**Goal:** Replace the current flat list with a controlled, filterable week view capped at 10 items.

**Layout:**
```
┌─────────────────────────────────────────────────┐
│ Upcoming Events                     [View All →]│
│─────────────────────────────────────────────────│
│ Source: [Watchlist ▾] [Portfolio] [Market]       │
│ Show:   [✓ Earnings] [✓ Dividends]              │
│─────────────────────────────────────────────────│
│ ┌─────┐                                        │
│ │ Mar │ AAPL · Earnings · est. EPS 2.35        │
│ │ 10  │                                        │
│ ├─────┤                                        │
│ │ Mar │ MSFT · Ex-Dividend · $0.75/share       │
│ │ 11  │                                        │
│ └─────┘                                        │
│         ... (up to 10 items) ...                │
│                                                 │
│ Showing 10 of 23 this week                      │
└─────────────────────────────────────────────────┘
```

**Behavior:**
- Source toggle: three buttons (Watchlist, Portfolio, Market). Active source is highlighted. Single-select.
  - When "Watchlist" is selected: if user has multiple watchlists, show a dropdown to pick which one (or "All Watchlists")
- Event type toggles: checkboxes for Earnings and Dividends. Both on by default. At least one must be on.
- Week scope: shows events from Monday of current week through Sunday. Display "This Week: Mar 2 – Mar 8" label.
- Cap at 10 items. If more exist, show "Showing 10 of {total} this week" with the View All link.
- "View All →" button: navigates to Portfolio → Upcoming Events sub-tab, passing the current source filter and event type toggles so the full view opens in the same context.
- Each event row: clickable, navigates to Research page for that ticker (existing behavior, keep it).
- Loading state: show spinner/skeleton while events are being fetched (replaces the misleading "No upcoming events" on first load).
- Empty state: "No {source} events this week" with suggestion text based on source (e.g., "Add tickers to your watchlist to see their events here").

**State management:**
- Source selection and event type toggles stored in `uiStore` so they persist during the session and carry over to the Portfolio Upcoming Events tab.
- Add to uiStore:
  - `eventsSource: 'watchlist' | 'portfolio' | 'market'` (default: 'portfolio')
  - `eventsWatchlistId: number | null` (default: null = all watchlists)
  - `eventsTypes: string[]` (default: ['earnings', 'ex_dividend'])

**Files touched:**
- `frontend/src/pages/Dashboard/UpcomingEvents/UpcomingEventsWidget.tsx` — full rewrite
- `frontend/src/pages/Dashboard/UpcomingEvents/UpcomingEventsWidget.module.css` — full rewrite
- `frontend/src/pages/Dashboard/types.ts` — update UpcomingEvent type with `source` and `is_estimated` fields, add filter types
- `frontend/src/pages/Dashboard/DashboardPage.tsx` — update to pass new props, remove direct events prop (widget fetches its own data now)
- `frontend/src/stores/uiStore.ts` — add events filter state
- `frontend/src/services/navigationService.ts` — add `goToUpcomingEvents(filters)` method

#### 2E. Frontend — Portfolio "Upcoming Events" Sub-Tab (New)
**Goal:** Full calendar experience for events, accessible from Dashboard "View All" or directly from Portfolio tab bar.

**Tab addition:**
- Add 7th tab to Portfolio: `{ id: 'upcoming-events', label: 'Upcoming Events' }`
- New component: `frontend/src/pages/Portfolio/UpcomingEvents/UpcomingEventsTab.tsx`

**Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│ Filters:                                                     │
│ Source: [Watchlist ▾] [Portfolio] [Market]                    │
│ Show:   [✓ Earnings] [✓ Dividends]                           │
│─────────────────────────────────────────────────────────────│
│                                                               │
│ THIS WEEK — Mar 2 – Mar 8                                    │
│ ┌─────┐                                                      │
│ │ Mar │ AAPL · Earnings · est. EPS 2.35          [→ Research]│
│ │ 10  │                                                      │
│ │ Mar │ MSFT · Ex-Dividend · $0.75/share         [→ Research]│
│ │ 11  │                                                      │
│ │ Mar │ GOOGL · Earnings · est. EPS 1.89         [→ Research]│
│ │ 12  │                                                      │
│ └─────┘                                                      │
│                                                               │
│ NEXT WEEK — Mar 9 – Mar 15                                   │
│ ┌─────┐                                                      │
│ │ Mar │ JPM · Earnings                           [→ Research]│
│ │ 14  │                                                      │
│ │ Mar │ NVDA · Ex-Dividend · $0.04/share         [→ Research]│
│ │ 15  │                                                      │
│ └─────┘                                                      │
│                                                               │
│ WEEK OF Mar 16 – Mar 22                                      │
│ ...                                                           │
│                                                               │
│ [Load More]                                                   │
└─────────────────────────────────────────────────────────────┘
```

**Behavior:**
- Same source and event type filters as dashboard widget, synced via uiStore
- Events grouped by week with clear week headers ("This Week", "Next Week", then "Week of {date range}")
- Scrollable list, paginated with "Load More" button (fetches next 50 events)
- Each event row shows: date badge, ticker, event type, detail text, and a small "→ Research" link
- Ticker click → navigates to Research page for that ticker
- When opened from Dashboard "View All", inherits the dashboard's current filter state
- When opened directly from Portfolio tab bar, uses last-used filter state from uiStore
- Initial load: fetch first 50 events matching current filters
- Empty state per source: helpful message (e.g., "No upcoming events for your portfolio. Events will appear as you add positions.")

**Files touched:**
- `frontend/src/pages/Portfolio/UpcomingEvents/UpcomingEventsTab.tsx` — new file
- `frontend/src/pages/Portfolio/UpcomingEvents/UpcomingEventsTab.module.css` — new file
- `frontend/src/pages/Portfolio/PortfolioPage.tsx` — add 7th tab, import new component
- `frontend/src/pages/Portfolio/types.ts` — add any needed types (or reuse from Dashboard types)

---

## AREA 3: MINOR POLISH

#### 3A. Refresh Button Spinner
**Current:** Button text changes to "Refreshing..." and button disables.
**Change:** Add a small animated spinner icon (CSS-only rotating circle) next to the text when loading. Keep the disable behavior.

**Files touched:**
- `frontend/src/pages/Dashboard/DashboardPage.tsx` — add spinner element conditional on loading
- `frontend/src/pages/Dashboard/DashboardPage.module.css` — spinner animation keyframes

#### 3B. Events Widget Loading State
**Current:** Shows "No upcoming events" immediately while data is loading, which is misleading.
**Change:** Show a skeleton/shimmer loading state while the dashboard summary is being fetched. Only show "No upcoming events" after data has loaded and there truly are none.

**Files touched:**
- `frontend/src/pages/Dashboard/UpcomingEvents/UpcomingEventsWidget.tsx` — add loading prop and skeleton state
- `frontend/src/pages/Dashboard/UpcomingEvents/UpcomingEventsWidget.module.css` — skeleton animation

#### 3C. Silent Error Handling Cleanup (Low Priority)
**Current:** Multiple `catch { /* swallow */ }` blocks across dashboard widgets, watchlist operations, and WatchlistPicker modal. Errors are invisible.
**Change:** Replace with proper error handling:
- Watchlist operations: show inline error message ("Failed to add ticker" / "Failed to create watchlist") that auto-clears after 3 seconds
- Dashboard widget fetches: show small error indicator within the widget rather than blank/misleading state
- WatchlistPicker modal: show error message in the modal

**Files touched:**
- `frontend/src/pages/Dashboard/Watchlist/WatchlistWidget.tsx` — add error states to handlers
- `frontend/src/components/ui/WatchlistPicker/WatchlistPicker.tsx` — add error handling
- Consider creating a lightweight toast/notification utility if one doesn't exist

---

## SESSION ORGANIZATION (Recommended for PM)

### Session 7A — Boot Sequence & Dashboard Animations (Frontend Only)
**Scope:** Areas 1A, 1B, 3A
**Files:** BootSequence.tsx, BootPhase.tsx, BootSequence.module.css, DashboardPage.tsx, DashboardPage.module.css, App.tsx, uiStore.ts
**Complexity:** Medium (animation timing, state coordination)
**Estimated acceptance criteria:** 12–15

### Session 7B — Sound Infrastructure (Frontend Only)
**Scope:** Area 1C
**Files:** soundManager.ts (new), BootPhase.tsx, BootSequence.tsx, GeneralSection.tsx, settings_service.py
**Complexity:** Low-Medium (Web Audio API, settings integration)
**Estimated acceptance criteria:** 8–10
**Note:** Can be deferred or done as part of 7A if scope allows

### Session 7C — Events Backend (Backend Only)
**Scope:** Areas 2A, 2B, 2C
**Files:** sp500_tickers.json (new), company_events_service.py, dashboard_service.py, dashboard_router.py, market_data_repo.py, universe_service.py, main.py
**Complexity:** Medium-High (background tasks, staleness logic, filtered queries)
**Estimated acceptance criteria:** 15–20

### Session 7D — Events Frontend (Frontend Only)
**Scope:** Areas 2D, 2E, 3B
**Files:** UpcomingEventsWidget.tsx (rewrite), UpcomingEventsTab.tsx (new), PortfolioPage.tsx, DashboardPage.tsx, uiStore.ts, navigationService.ts, types.ts, all associated CSS
**Complexity:** Medium-High (two new/rewritten components, state sync, navigation)
**Estimated acceptance criteria:** 18–22
**Depends on:** Session 7C (backend endpoints must exist)

### Session 7E — Error Handling Polish (Frontend Only)
**Scope:** Area 3C
**Files:** WatchlistWidget.tsx, WatchlistPicker.tsx, potentially new toast utility
**Complexity:** Low
**Estimated acceptance criteria:** 6–8
**Note:** Can be batched with other polish work from future tabs

---

## DEPENDENCIES & RISKS

| Risk | Mitigation |
|------|------------|
| Yahoo Finance rate limiting on 500-ticker batch fetch | Sequential fetching with 100ms delay, staleness cache to minimize refetches, background task so it doesn't block UI |
| S&P 500 list goes stale (quarterly rebalances) | Ship static JSON, add manual refresh in Settings, low urgency since composition changes are ~20 tickers per quarter |
| Boot animation feels too slow after first few uses | Sound toggle and potential "skip boot" setting in General settings for power users |
| Events background fetch not complete when user opens dashboard | Dashboard reads from cache immediately, shows whatever exists, updates reactively as fetch completes |
| Widget entry animation conflicts with Electron window restore | Only trigger on `justBooted` flag, not on window focus/restore events |

---

## DECISIONS MADE

1. Boot duration: ~4–5 seconds (up from ~2 seconds)
2. Dashboard widget cascade: 5 widgets, ~150–200ms stagger, ~1.2 seconds total
3. Sound: build infrastructure now, placeholder audio, Finn tests before final files ship
4. Events dashboard widget: week view, single-select source toggle, event type checkboxes, cap at 10
5. "View All" navigates to Portfolio → Upcoming Events (new 7th sub-tab), preserving active filters
6. S&P 500 stored as static JSON, background fetch on startup with 7-day staleness
7. Fetch priority: portfolio → watchlist → S&P 500
8. Deduplication: ticker in multiple sources shown once (portfolio > watchlist > market priority)
9. Watchlist bug removed from scope (confirmed working)
10. Silent error swallowing kept as low-priority polish item

---

*End of Dashboard Update Plan*
*Phase 7A–7E · Prepared March 4, 2026*
