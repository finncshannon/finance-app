# Session 7D — Events Frontend (Dashboard Widget Redesign + Portfolio Upcoming Events Tab)
## Phase 7: Dashboard

**Priority:** Normal
**Type:** Frontend Only
**Depends On:** 7C (backend endpoints for filtered events, refresh status)
**Spec Reference:** `specs/phase7_dashboard.md` → Areas 2D, 2E, 3B

---

## SCOPE SUMMARY

Fully rewrite the dashboard Upcoming Events widget with source/type filter toggles, a week-scoped view capped at 10 items, and proper loading/empty states. Create a new "Upcoming Events" sub-tab in Portfolio with paginated week-grouped event list. Add a loading skeleton to the events widget. Sync filter state between dashboard widget and portfolio tab via uiStore.

---

## TASKS

### Task 1: Add Events Filter State to uiStore
**Description:** Add shared state for event source and type filters so the dashboard widget and portfolio tab stay in sync.

**Subtasks:**
- [ ] 1.1 — In `frontend/src/stores/uiStore.ts`, add the following state properties:
  - `eventsSource: 'watchlist' | 'portfolio' | 'market'` (default: `'portfolio'`)
  - `eventsWatchlistId: number | null` (default: `null` — means "all watchlists")
  - `eventsTypes: string[]` (default: `['earnings', 'ex_dividend']`)
- [ ] 1.2 — Add setter actions:
  - `setEventsSource: (source: 'watchlist' | 'portfolio' | 'market') => void`
  - `setEventsWatchlistId: (id: number | null) => void`
  - `setEventsTypes: (types: string[]) => void`
  - `toggleEventType: (type: string) => void` — toggles a type in/out of the array, but prevents removing the last item (at least one must remain)
- [ ] 1.3 — Update `MODULE_SUB_TABS` for `portfolio` to include `'upcoming-events'` as the 7th tab.

**Implementation Notes:**
- The `MODULE_SUB_TABS` line currently is: `portfolio: ['holdings', 'performance', 'allocation', 'income', 'transactions', 'alerts']`. Add `'upcoming-events'` at the end.
- These filter values are read by both the dashboard widget and the portfolio tab to stay synchronized.

---

### Task 2: Add Navigation Helper for Events Tab
**Description:** Add a method to `navigationService` that navigates to Portfolio → Upcoming Events tab, preserving current filter state.

**Subtasks:**
- [ ] 2.1 — In `frontend/src/services/navigationService.ts`, add method:
  ```typescript
  goToUpcomingEvents() {
    const uiStore = useUIStore.getState();
    uiStore.setActiveModule('portfolio');
    uiStore.setSubTab('portfolio', 'upcoming-events');
  }
  ```
  No need to pass filter params — the filters are already synced in uiStore.

---

### Task 3: Rewrite Dashboard Upcoming Events Widget
**Description:** Replace the current flat event list with a controlled, filterable week view capped at 10 items, with source toggles, event type checkboxes, a loading skeleton, and proper empty state.

**Subtasks:**
- [ ] 3.1 — Rewrite `frontend/src/pages/Dashboard/UpcomingEvents/UpcomingEventsWidget.tsx`:
  - Remove the `events` prop — the widget now fetches its own data
  - Read `eventsSource`, `eventsWatchlistId`, `eventsTypes` from `uiStore`
  - On mount and whenever filters change, call `GET /api/v1/dashboard/events` with the filter query params:
    - `source={eventsSource}`
    - `watchlist_id={eventsWatchlistId}` (only if source is 'watchlist' and ID is not null)
    - `event_types={eventsTypes.join(',')}`
    - `date_from={monday of current week in ISO format}`
    - `date_to={sunday of current week in ISO format}`
    - `limit=10`
  - Local state: `events`, `totalCount`, `loading`, `error`
  - Render layout:
    - Header row: "Upcoming Events" title + "View All →" button (calls `navigationService.goToUpcomingEvents()`)
    - Filter row: Source toggle (3 buttons: Watchlist, Portfolio, Market — single-select, highlighted active) + Event type checkboxes (Earnings, Dividends — both on by default)
    - When source is 'watchlist': show a small dropdown to pick a specific watchlist (fetch watchlist list from `/api/v1/dashboard/watchlists`), or "All Watchlists" option
    - Week scope label: "This Week: Mar 2 – Mar 8" (computed from current date)
    - Event list: up to 10 items, each clickable → `navigationService.goToResearch(ticker)`
    - Footer: "Showing {count} of {totalCount} this week" when totalCount > 10
  - Loading state: show skeleton shimmer rows (3–4 placeholder rows with pulsing animation)
  - Empty state: "No {source} events this week" with contextual suggestion text
- [ ] 3.2 — Update `frontend/src/pages/Dashboard/UpcomingEvents/UpcomingEventsWidget.module.css`:
  - Full rewrite: source toggle buttons, event type checkboxes, week label, skeleton shimmer, filter row layout
  - Source toggle: small pill buttons, active one gets `var(--accent-primary)` background + `var(--text-on-accent)` text
  - Checkboxes: use custom styled checkboxes matching the app's design system
  - Skeleton rows: use `@keyframes shimmer` with a gradient sweep animation
  - Keep the existing event row styling (dateBadge, eventContent, etc.) or refine it

**Implementation Notes:**
- The widget currently receives events as a prop from `DashboardPage`. After this rewrite, it fetches its own data. `DashboardPage.tsx` needs to be updated to no longer pass `events` prop.
- Use `api.get<>()` from `@/services/api` for data fetching.
- For the week date range: compute Monday and Sunday of the current week from `new Date()`.
- The `UpcomingEvent` type in `types.ts` needs new fields: `source` and `is_estimated`. Update the interface.
- Source toggle is single-select (only one active at a time). Use the uiStore setter.
- Event type checkboxes: toggling should call `toggleEventType(type)`. At least one must remain checked.
- Watchlist dropdown: only shown when source is 'watchlist'. Fetch the watchlist list once and cache locally. Show "All Watchlists" as default option.

---

### Task 4: Update DashboardPage to Remove Events Prop
**Description:** Since the UpcomingEventsWidget now fetches its own data, DashboardPage no longer needs to pass events.

**Subtasks:**
- [ ] 4.1 — In `frontend/src/pages/Dashboard/DashboardPage.tsx`, remove the `events={data.events}` prop from `<UpcomingEventsWidget>`. The component now takes no required props.
- [ ] 4.2 — The `DashboardSummary` type can keep the `events` field for backward compatibility, but it's no longer used by the widget.

---

### Task 5: Update Dashboard Types
**Description:** Extend the `UpcomingEvent` type with new fields from the updated API.

**Subtasks:**
- [ ] 5.1 — In `frontend/src/pages/Dashboard/types.ts`, update the `UpcomingEvent` interface:
  ```typescript
  export interface UpcomingEvent {
    date: string;
    ticker: string;
    event_type: string;
    detail: string;
    source: 'portfolio' | 'watchlist' | 'market';
    is_estimated: boolean;
  }
  ```
- [ ] 5.2 — Add a new type for the filtered events response:
  ```typescript
  export interface FilteredEventsResponse {
    events: UpcomingEvent[];
    total_count: number;
    has_more: boolean;
  }
  ```

---

### Task 6: Create Portfolio Upcoming Events Sub-Tab
**Description:** Build a new full-page events view as the 7th Portfolio sub-tab, with week-grouped events, pagination, and the same filters as the dashboard widget.

**Subtasks:**
- [ ] 6.1 — Create `frontend/src/pages/Portfolio/UpcomingEvents/UpcomingEventsTab.tsx`:
  - Read `eventsSource`, `eventsWatchlistId`, `eventsTypes` from `uiStore` (same synced state as dashboard widget)
  - Render same filter row as dashboard widget (source toggle + event type checkboxes + optional watchlist dropdown)
  - Fetch events from `GET /api/v1/dashboard/events` with current filters:
    - `date_from` = today (or start of current week)
    - No `date_to` — fetch all upcoming
    - `limit=50`, `offset` for pagination
  - Group events by week: "This Week", "Next Week", then "Week of {date range}" headers
  - Each event row: date badge, ticker (clickable → Research), event type dot, detail text, small "→" research link
  - "Load More" button at bottom (increments offset by 50)
  - Loading state: spinner or skeleton
  - Empty state per source: "No upcoming events for your {source}. Events will appear as you add positions/tickers." etc.
- [ ] 6.2 — Create `frontend/src/pages/Portfolio/UpcomingEvents/UpcomingEventsTab.module.css`:
  - Filter bar at top (reuse patterns from dashboard widget CSS)
  - Week group headers: section divider style with week label
  - Event rows: similar to dashboard widget but full-width with research link on right
  - Load more button: centered, subtle style
  - Skeleton/loading state

**Implementation Notes:**
- Week grouping: iterate events, determine which ISO week each event falls in, group accordingly. For the header labels:
  - If week contains today → "THIS WEEK — Mar 2 – Mar 8"
  - If week is next → "NEXT WEEK — Mar 9 – Mar 15"
  - Otherwise → "WEEK OF Mar 16 – Mar 22"
- "Load More" appends new events to the existing list (offset-based pagination).
- The tab shares filter state with the dashboard widget via uiStore, so navigating from dashboard "View All" automatically shows the same filter context.

---

### Task 7: Register Upcoming Events Tab in PortfolioPage
**Description:** Add the 7th tab to the Portfolio page and render the new component.

**Subtasks:**
- [ ] 7.1 — In `frontend/src/pages/Portfolio/PortfolioPage.tsx`:
  - Add import: `import { UpcomingEventsTab } from './UpcomingEvents/UpcomingEventsTab';`
  - Add to `TABS` array: `{ id: 'upcoming-events', label: 'Upcoming Events' }`
  - Add case to `renderTab()` switch statement:
    ```typescript
    case 'upcoming-events':
      return <UpcomingEventsTab />;
    ```

---

### Task 8: Events Widget Loading Skeleton (Area 3B)
**Description:** Replace the misleading "No upcoming events" message that shows during initial load with a proper skeleton loading state.

**Subtasks:**
- [ ] 8.1 — This is now handled within Task 3's rewrite of the widget. The new widget has a `loading` local state and renders skeleton shimmer rows when loading. No separate work needed — just ensure the rewrite includes:
  - On initial mount: show skeleton (3–4 rows of pulsing placeholder bars)
  - After data loads with 0 results: show "No {source} events this week" empty state
  - Never show "No upcoming events" while data is still loading

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: `uiStore` has `eventsSource`, `eventsWatchlistId`, `eventsTypes` state with setters.
- [ ] AC-2: `MODULE_SUB_TABS` for portfolio includes `'upcoming-events'` as the 7th entry.
- [ ] AC-3: Dashboard widget fetches its own event data (no longer receives `events` prop).
- [ ] AC-4: Widget has source toggle (Watchlist, Portfolio, Market) — single-select, visually highlighted active.
- [ ] AC-5: Widget has event type checkboxes (Earnings, Dividends) — both on by default, at least one must be active.
- [ ] AC-6: When source is 'watchlist', a watchlist dropdown appears for selection.
- [ ] AC-7: Widget shows events scoped to current week with "This Week: {date range}" label.
- [ ] AC-8: Widget caps at 10 items with "Showing {n} of {total} this week" footer when overflow.
- [ ] AC-9: "View All →" navigates to Portfolio → Upcoming Events tab.
- [ ] AC-10: Widget shows skeleton shimmer during loading (not "No upcoming events").
- [ ] AC-11: Widget shows contextual empty state per source after loading completes with 0 events.
- [ ] AC-12: Each event row is clickable → navigates to Research for that ticker.
- [ ] AC-13: Portfolio has 7th tab: "Upcoming Events".
- [ ] AC-14: Portfolio Upcoming Events tab shows full event list grouped by week with headers.
- [ ] AC-15: Week group headers: "THIS WEEK", "NEXT WEEK", "WEEK OF {dates}".
- [ ] AC-16: Portfolio tab has "Load More" pagination (50 events per page).
- [ ] AC-17: Portfolio tab filters are synced with dashboard widget via uiStore.
- [ ] AC-18: Navigating from dashboard "View All" opens Portfolio tab with same active filters.
- [ ] AC-19: `UpcomingEvent` type includes `source` and `is_estimated` fields.
- [ ] AC-20: `navigationService` has `goToUpcomingEvents()` method.
- [ ] AC-21: Event type labels use `displayEventType()` from `displayNames.ts` if it exists, or fall back to titleCase transformation. (Note: `displayNames.ts` is created in 8A — if not yet available, use a local helper with the same logic.)
- [ ] AC-22: No visual regressions on dashboard grid layout or other portfolio tabs.
- [ ] AC-23: Filter changes trigger immediate re-fetch in both widget and tab.

---

## FILES TOUCHED

**New files:**
- `frontend/src/pages/Portfolio/UpcomingEvents/UpcomingEventsTab.tsx` — full Upcoming Events sub-tab
- `frontend/src/pages/Portfolio/UpcomingEvents/UpcomingEventsTab.module.css` — styles for the sub-tab

**Modified files:**
- `frontend/src/stores/uiStore.ts` — add `eventsSource`, `eventsWatchlistId`, `eventsTypes` state + setters; update `MODULE_SUB_TABS.portfolio`
- `frontend/src/services/navigationService.ts` — add `goToUpcomingEvents()` method
- `frontend/src/pages/Dashboard/UpcomingEvents/UpcomingEventsWidget.tsx` — full rewrite: self-fetching, filters, week scope, skeleton
- `frontend/src/pages/Dashboard/UpcomingEvents/UpcomingEventsWidget.module.css` — full rewrite: filter row, source toggle, checkboxes, skeleton
- `frontend/src/pages/Dashboard/DashboardPage.tsx` — remove `events` prop from `<UpcomingEventsWidget>`
- `frontend/src/pages/Dashboard/types.ts` — update `UpcomingEvent` with `source`, `is_estimated`; add `FilteredEventsResponse`
- `frontend/src/pages/Portfolio/PortfolioPage.tsx` — add 7th tab + import + render case

---

## BUILDER PROMPT

> **Session 7D — Events Frontend (Dashboard Widget Redesign + Portfolio Upcoming Events Tab)**
>
> You are building session 7D of the Finance App v2.0 update.
>
> **What you're doing:** Fully rewriting the dashboard Upcoming Events widget with source/type filters, a week-scoped capped view, and loading skeletons. Creating a new "Upcoming Events" sub-tab in Portfolio with paginated, week-grouped events. Syncing filter state between both via uiStore.
>
> **Context:** Session 7C built the backend: `GET /api/v1/dashboard/events` now accepts `source`, `watchlist_id`, `event_types`, `date_from`, `date_to`, `limit`, `offset` query params and returns `{events: [...], total_count: N, has_more: bool}`. Each event has `date`, `ticker`, `event_type`, `detail`, `source`, `is_estimated` fields. The current widget receives events as a prop from DashboardPage — you're making it self-fetching.
>
> **Existing code:**
> - `UpcomingEventsWidget.tsx` — current: receives `events: UpcomingEvent[]` prop, renders flat list, "View All" goes to Research tab. You're rewriting this entirely.
> - `UpcomingEventsWidget.module.css` — current styles for widget, header, event list, date badge, empty state. You're rewriting this.
> - `DashboardPage.tsx` — renders 5 widgets in a grid: Market, Portfolio, Watchlist, Models, Events. Currently passes `events={data.events}` to widget. You'll remove that prop.
> - `types.ts` (Dashboard) — `UpcomingEvent` type has `date, ticker, event_type, detail`. You'll add `source, is_estimated`.
> - `uiStore.ts` — Zustand store with `activeModule`, `activeSubTabs`, etc. `MODULE_SUB_TABS.portfolio` has 6 tabs. You'll add events filter state and a 7th tab.
> - `PortfolioPage.tsx` — has 6 tabs (Holdings through Alerts), `TABS` array, `renderTab()` switch. You'll add 7th tab.
> - `navigationService.ts` — has `goToResearch(ticker)`, `goToPortfolio()`. You'll add `goToUpcomingEvents()`.
> - API client: `import { api } from '../../services/api';` → `api.get<T>(path)` returns unwrapped data.
> - Tab component: `import { Tabs } from '../../components/ui/Tabs/Tabs';` → `<Tabs tabs={[{id, label}]} activeTab={id} onTabChange={fn} />`
>
> **Cross-cutting rules:**
> - Display Name Rule: All backend snake_case keys displayed in the UI must use the shared `displayNames.ts` utility. Never show raw keys. Never use inline `.replace(/_/g, ' ')`. Import from `@/utils/displayNames`. (Note: `displayNames.ts` will be created in session 8A. For now, create a local `displayEventType()` helper that maps: `earnings` → "Earnings", `ex_dividend` → "Ex-Dividend", `dividend` → "Dividend", `filing` → "Filing". When 8A ships, these will migrate to the shared utility.)
> - Chart Quality: All charts must meet Fidelity/Yahoo Finance information-density standards.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%).
> - Scenario Order: Bear / Base / Bull (left to right), Base default.
>
> **Task 1: uiStore — Events Filter State**
>
> In `frontend/src/stores/uiStore.ts`:
> - Add to state interface:
>   ```typescript
>   eventsSource: 'watchlist' | 'portfolio' | 'market';
>   eventsWatchlistId: number | null;
>   eventsTypes: string[];
>   setEventsSource: (source: 'watchlist' | 'portfolio' | 'market') => void;
>   setEventsWatchlistId: (id: number | null) => void;
>   setEventsTypes: (types: string[]) => void;
>   toggleEventType: (type: string) => void;
>   ```
> - Add default values: `eventsSource: 'portfolio'`, `eventsWatchlistId: null`, `eventsTypes: ['earnings', 'ex_dividend']`
> - Implement `toggleEventType`: toggle the type in/out of the array, but if removing would empty the array, don't remove (keep at least one).
> - Update `MODULE_SUB_TABS.portfolio` to add `'upcoming-events'`.
>
> **Task 2: Navigation Service**
>
> In `frontend/src/services/navigationService.ts`, add:
> ```typescript
> goToUpcomingEvents() {
>   const uiStore = useUIStore.getState();
>   uiStore.setActiveModule('portfolio');
>   uiStore.setSubTab('portfolio', 'upcoming-events');
> },
> ```
>
> **Task 3: Rewrite Dashboard Events Widget**
>
> Full rewrite of `frontend/src/pages/Dashboard/UpcomingEvents/UpcomingEventsWidget.tsx`:
>
> Structure:
> ```tsx
> export function UpcomingEventsWidget() {
>   // Read filters from uiStore
>   const eventsSource = useUIStore(s => s.eventsSource);
>   const eventsWatchlistId = useUIStore(s => s.eventsWatchlistId);
>   const eventsTypes = useUIStore(s => s.eventsTypes);
>   const setEventsSource = useUIStore(s => s.setEventsSource);
>   const toggleEventType = useUIStore(s => s.toggleEventType);
>
>   // Local state
>   const [events, setEvents] = useState<UpcomingEvent[]>([]);
>   const [totalCount, setTotalCount] = useState(0);
>   const [loading, setLoading] = useState(true);
>   const [watchlists, setWatchlists] = useState<WatchlistSummary[]>([]);
>
>   // Compute week range
>   const { weekStart, weekEnd, weekLabel } = useMemo(() => computeWeekRange(), []);
>
>   // Fetch events when filters change
>   useEffect(() => { fetchEvents(); }, [eventsSource, eventsWatchlistId, eventsTypes]);
>
>   // Fetch watchlist list once for the dropdown
>   useEffect(() => { fetchWatchlists(); }, []);
>
>   async function fetchEvents() {
>     setLoading(true);
>     const params = new URLSearchParams({
>       source: eventsSource,
>       event_types: eventsTypes.join(','),
>       date_from: weekStart,
>       date_to: weekEnd,
>       limit: '10',
>     });
>     if (eventsSource === 'watchlist' && eventsWatchlistId) {
>       params.set('watchlist_id', String(eventsWatchlistId));
>     }
>     try {
>       const result = await api.get<FilteredEventsResponse>(
>         `/api/v1/dashboard/events?${params}`
>       );
>       setEvents(result.events);
>       setTotalCount(result.total_count);
>     } catch { /* handle */ }
>     setLoading(false);
>   }
>
>   return (
>     <div className={styles.widget}>
>       <div className={styles.header}>
>         <span>Upcoming Events</span>
>         <button onClick={() => navigationService.goToUpcomingEvents()}>View All →</button>
>       </div>
>       <div className={styles.filterRow}>
>         {/* Source toggle: 3 buttons */}
>         {/* Event type checkboxes: Earnings, Dividends */}
>         {/* Watchlist dropdown (only when source === 'watchlist') */}
>       </div>
>       <div className={styles.weekLabel}>This Week: {weekLabel}</div>
>       <div className={styles.body}>
>         {loading ? <Skeleton /> :
>          events.length === 0 ? <EmptyState source={eventsSource} /> :
>          <EventList events={events} />}
>       </div>
>       {totalCount > 10 && (
>         <div className={styles.footer}>Showing {events.length} of {totalCount} this week</div>
>       )}
>     </div>
>   );
> }
> ```
>
> Helper function `computeWeekRange()`: returns `{ weekStart: string (ISO Monday), weekEnd: string (ISO Sunday), weekLabel: string (e.g. "Mar 2 – Mar 8") }`. Use standard JS `Date` manipulation to find Monday of current week.
>
> Skeleton component: 3–4 rows of animated placeholder bars (CSS shimmer).
>
> Empty state text per source:
> - portfolio: "No portfolio events this week. Events appear as companies in your portfolio announce earnings or dividends."
> - watchlist: "No watchlist events this week. Add tickers to your watchlist to track their events."
> - market: "No S&P 500 events this week."
>
> Event type display: For `event_type` labels, use a local helper until `displayNames.ts` exists:
> ```typescript
> function displayEventType(type: string): string {
>   const map: Record<string, string> = {
>     earnings: 'Earnings',
>     ex_dividend: 'Ex-Dividend',
>     dividend: 'Dividend',
>     filing: 'Filing',
>   };
>   return map[type] ?? type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
> }
> ```
>
> **Task 4: Update DashboardPage**
>
> In `frontend/src/pages/Dashboard/DashboardPage.tsx`:
> - Change `<UpcomingEventsWidget events={data.events} />` to `<UpcomingEventsWidget />`
> - No other changes needed.
>
> **Task 5: Update Dashboard Types**
>
> In `frontend/src/pages/Dashboard/types.ts`:
> - Update `UpcomingEvent`:
>   ```typescript
>   export interface UpcomingEvent {
>     date: string;
>     ticker: string;
>     event_type: string;
>     detail: string;
>     source: 'portfolio' | 'watchlist' | 'market';
>     is_estimated: boolean;
>   }
>   ```
> - Add:
>   ```typescript
>   export interface FilteredEventsResponse {
>     events: UpcomingEvent[];
>     total_count: number;
>     has_more: boolean;
>   }
>   ```
>
> **Task 6: Portfolio Upcoming Events Tab**
>
> Create `frontend/src/pages/Portfolio/UpcomingEvents/UpcomingEventsTab.tsx`:
>
> Structure:
> - Same filter row as dashboard widget (source toggle + event type checkboxes + optional watchlist dropdown)
> - Fetch events from `GET /api/v1/dashboard/events` with `limit=50`, `offset` state for pagination, no `date_to`
> - Group events by week using ISO week calculation
> - Week headers: "THIS WEEK — Mar 2 – Mar 8", "NEXT WEEK — Mar 9 – Mar 15", "WEEK OF Mar 16 – Mar 22"
> - Each event row: date badge (month + day), ticker (bold mono, clickable), dot colored by type, type label, detail text, small "→" icon link to Research
> - "Load More" button: when `has_more`, increments offset and appends new events to existing list
> - Empty state per source with helpful message
> - Loading state: centered spinner or skeleton rows
>
> Create `frontend/src/pages/Portfolio/UpcomingEvents/UpcomingEventsTab.module.css`:
> - Filter bar, week group headers (uppercase, small, with horizontal rule), event rows (full-width, hover effect), date badge, load more button, empty state, loading spinner.
>
> **Task 7: Register Tab in PortfolioPage**
>
> In `frontend/src/pages/Portfolio/PortfolioPage.tsx`:
> - Add import: `import { UpcomingEventsTab } from './UpcomingEvents/UpcomingEventsTab';`
> - Update `TABS`:
>   ```typescript
>   const TABS = [
>     { id: 'holdings', label: 'Holdings' },
>     { id: 'performance', label: 'Performance' },
>     { id: 'allocation', label: 'Allocation' },
>     { id: 'income', label: 'Income' },
>     { id: 'transactions', label: 'Transactions' },
>     { id: 'alerts', label: 'Alerts' },
>     { id: 'upcoming-events', label: 'Upcoming Events' },
>   ];
>   ```
> - Add case to `renderTab()`:
>   ```typescript
>   case 'upcoming-events':
>     return <UpcomingEventsTab />;
>   ```
>
> **Acceptance criteria:**
> 1. uiStore has `eventsSource`, `eventsWatchlistId`, `eventsTypes` with setters
> 2. MODULE_SUB_TABS.portfolio has 7 tabs including 'upcoming-events'
> 3. Dashboard widget is self-fetching (no props from DashboardPage)
> 4. Widget has source toggle (single-select: Watchlist / Portfolio / Market)
> 5. Widget has event type checkboxes (Earnings, Dividends) — at least one always active
> 6. Watchlist dropdown shown when source is 'watchlist'
> 7. Widget shows current week scope with "This Week: {dates}" label
> 8. Widget caps at 10 items with overflow count footer
> 9. "View All →" navigates to Portfolio → Upcoming Events tab
> 10. Widget shows skeleton during loading, contextual empty state after load
> 11. Each event row clickable → Research page for ticker
> 12. Portfolio has 7th tab: "Upcoming Events"
> 13. Portfolio tab shows week-grouped events with clear headers
> 14. "Load More" pagination works (appends 50 events per page)
> 15. Filters synced between dashboard widget and portfolio tab via uiStore
> 16. Event type labels use displayEventType helper (not raw snake_case)
> 17. No regressions on existing dashboard or portfolio functionality
>
> **Files to create:**
> - `frontend/src/pages/Portfolio/UpcomingEvents/UpcomingEventsTab.tsx`
> - `frontend/src/pages/Portfolio/UpcomingEvents/UpcomingEventsTab.module.css`
>
> **Files to modify:**
> - `frontend/src/stores/uiStore.ts`
> - `frontend/src/services/navigationService.ts`
> - `frontend/src/pages/Dashboard/UpcomingEvents/UpcomingEventsWidget.tsx` (full rewrite)
> - `frontend/src/pages/Dashboard/UpcomingEvents/UpcomingEventsWidget.module.css` (full rewrite)
> - `frontend/src/pages/Dashboard/DashboardPage.tsx`
> - `frontend/src/pages/Dashboard/types.ts`
> - `frontend/src/pages/Portfolio/PortfolioPage.tsx`
>
> **Technical constraints:**
> - CSS modules (`.module.css`) for all styling
> - CSS variables from the design system (`var(--accent-primary)`, `var(--bg-secondary)`, `var(--border-subtle)`, etc.)
> - Zustand `uiStore` for shared filter state
> - `api.get<T>(path)` for all API calls
> - No external date libraries — use native `Date` for week calculations
> - Event types are snake_case from backend: `earnings`, `ex_dividend`
> - Follow existing component patterns: functional components with hooks, no class components
> - The Tabs component interface: `<Tabs tabs={[{id, label}]} activeTab={id} onTabChange={fn} />`
