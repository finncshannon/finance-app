# Finance App — Model Builder: Model Sub-Tab Update Plan
## Phase 8: Model Builder — Model

**Prepared by:** Planner (March 5, 2026)
**Recipient:** PM Agent
**Scope:** Model Builder → Model sub-tab (DCF, DDM, Comps, Revenue-Based views)

---

## PLAN SUMMARY

Seven workstreams:

1. **Comps Crash Fix + Peer Selection** — Fix the crash, build auto-peer-discovery backend, add manual peer selection UI
2. **Error Boundary Scoping** — Move ErrorBoundary to wrap only the tab content, not the entire page, so model type pills remain accessible during errors; error messages made human-readable
3. **Underscore Syntax Cleanup** — Fix raw `xxx_xxx` labels in DDM and across all views
4. **Scenario Pill Reorder** — Bear / Base / Bull across all views (consistent with Assumptions tab)
5. **DDM & Revenue-Based Detail Upgrade** — Bring both views closer to DCF's level of detail
6. **DCF Key Outputs & Chart Upgrade** — Better formatting for key outputs panel, Fidelity-detail upgrade on the waterfall chart
7. **Export Button on Model Tab** — Add per-model export (Excel/PDF) directly on the Model sub-tab results view

---

## AREA 1: COMPS CRASH FIX + PEER SELECTION

### Root Cause
The frontend `ModelTab.tsx` POSTs to `/run/comps` with no `peer_tickers`. The backend returns a `CompsResult` with empty `peer_group`. `CompsView.tsx` accesses `result.peer_group.peers` directly — if the response shape is off or `peer_group` is undefined, it crashes with "cannot read properties of undefined (reading 'peers')."

### Fix — Three Parts

#### 1A. Backend — Auto Peer Discovery
**Goal:** When `peer_tickers` is not provided, the backend should automatically find 8–15 peer companies based on the target's sector, industry, and market cap range.

**Logic:**
1. Get the target company's profile (sector, industry, market_cap) from the DB
2. Query the `companies` table for tickers in the same sector (preferring same industry)
3. Filter to companies with cached financial data (they need financials for multiples)
4. Sort by market cap proximity to the target
5. Return top 8–15 peers
6. If fewer than 3 peers found, return a response with `peer_group.count = 0` and a clear warning instead of crashing

**New service method:** `CompanyService.find_peers(ticker, limit=15) -> list[str]`

**Files touched:**
- `backend/services/company_service.py` — add `find_peers()` method
- `backend/routers/models_router.py` — in `run_comps`, call `find_peers()` when `peer_tickers` is None
- `backend/repositories/company_repo.py` — add query for companies by sector/industry with financial data

#### 1B. Backend — Comps Response Null Safety
**Goal:** Ensure `CompsResult` always has a well-formed `peer_group` even when there are no peers.

**Changes:**
- `CompsEngine.run()` should always return `peer_group = {"peers": [], "count": 0}` (never `None`)
- Add a `status` field to `CompsResult`: `"ready"` (has peers + results), `"no_peers"` (no peers found, needs manual selection), `"error"` (engine failure)
- Frontend can use `status` to decide which UI to show

**Files touched:**
- `backend/engines/comps_engine.py` — ensure peer_group always populated, add status field
- `backend/engines/models.py` — add `status` to `CompsResult`

#### 1C. Frontend — Peer Selection Panel
**Goal:** A peer selection UI at the top of the Comps view that lets the user search for and manage peer companies.

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│ PEER GROUP                                    [▾ Collapse]      │
│─────────────────────────────────────────────────────────────────│
│ Search: [Enter ticker...  ] [Add]                                │
│                                                                   │
│ AAPL  Apple Inc.         $3.2T   ✕                               │
│ MSFT  Microsoft Corp.    $2.8T   ✕                               │
│ GOOGL Alphabet Inc.      $1.9T   ✕                               │
│ META  Meta Platforms     $1.2T   ✕                               │
│ ... (8-15 peers)                                                  │
│                                                                   │
│ [Run Comps Analysis]    Auto-discovered: 12 peers from Technology │
└─────────────────────────────────────────────────────────────────┘
```

**Behavior:**
- On initial load: if backend auto-discovered peers, they appear pre-populated in the list and the analysis runs automatically
- If no peers found: shows "No peers found for {ticker}. Add peer companies below to run comparisons." with the search bar prominent
- Search bar: same autocomplete pattern as the main ticker search (`/api/v1/companies/search`)
- Add: clicking Add or pressing Enter adds the ticker to the peer list
- Remove: ✕ button removes a peer
- "Run Comps Analysis" button: sends the current peer list to the backend and reruns
- Collapsible: after initial run, the peer panel collapses to a single line showing "12 peers" with an expand toggle
- Peer list persists in component state for the session

**Two UI states:**
1. **Setup state** (no peers / no results yet): Peer selection panel prominent, no results below
2. **Results state** (peers loaded, analysis complete): Peer panel collapsed at top, full results below (existing CompsView content)

**Files touched:**
- `frontend/src/pages/ModelBuilder/Models/CompsView.tsx` — add peer selection panel, two-state rendering, null-safe access throughout
- `frontend/src/pages/ModelBuilder/Models/CompsView.module.css` — peer panel styles
- `frontend/src/pages/ModelBuilder/Models/ModelTab.tsx` — pass peer_tickers to the run endpoint

---

## AREA 2: ERROR BOUNDARY SCOPING

### Current Problem
`App.tsx` wraps the entire active page in an `ErrorBoundary`:
```tsx
<ErrorBoundary key={activeModule} moduleName={activeModule}>
  <ActivePage />
</ErrorBoundary>
```
When Comps crashes inside `ModelTab` → `CompsView`, the ErrorBoundary catches it at the page level. The error screen covers everything: ticker search, model type pills, sub-tabs. Clicking "Reload Module" re-renders the same crashed component → infinite loop.

### Fix

**Move ErrorBoundary to wrap only the tab content**, keeping the page chrome accessible:

```tsx
// ModelBuilderPage.tsx — around tab content only
<div className={styles.tabContent}>
  <ErrorBoundary key={`${activeTicker}-${activeSubTab}-${activeModelType}`} moduleName={activeSubTab}>
    {activeTicker ? tabContent() : emptyState}
  </ErrorBoundary>
</div>
```

The `key` includes `activeModelType` so switching from Comps to DCF resets the error boundary automatically.

**Human-readable error messages:**
- Replace raw error messages (like "cannot read properties of undefined") with user-facing text
- Error screen shows: "This model encountered an issue" + a simplified explanation
- Add a "Switch Model" suggestion: "Try switching to DCF or DDM using the model selector above"
- The model type pills and sub-tabs remain fully functional above the error

**Files touched:**
- `frontend/src/pages/ModelBuilder/ModelBuilderPage.tsx` — move ErrorBoundary to wrap tab content only, update key
- `frontend/src/components/ui/ErrorBoundary/ErrorBoundary.tsx` — improve error message formatting, add suggestion text
- `frontend/src/components/ui/ErrorBoundary/ErrorBoundary.module.css` — minor style updates

---

## AREA 3: UNDERSCORE SYNTAX CLEANUP

### Known Issues
- DDM View: `row.stage` displays raw `high_growth`, `transition`, `terminal` — the `stageClass()` function handles CSS but the badge text shows `{row.stage.replace(/_/g, ' ')}` which produces "high growth" (lowercase). Should be "High Growth"
- DDM View: sustainability metric names may contain underscores
- CompsView: `key.replace(/_/g, '/').toUpperCase()` in implied values table produces `EV/EBITDA` which is correct, but `P/FCF` etc. — verify all are clean
- RevBasedView: `statusLabel()` does title case but `statusBadgeClass()` relies on raw strings — verify consistency
- All views: scenario labels use `SCENARIO_LABELS` map which is clean

### Fix
- Use the shared `displayModelName()` utility from the Overview plan (session 8A) where applicable
- Add a `displayStageName()` utility: `high_growth` → "High Growth", `transition` → "Transition", `terminal` → "Terminal"
- Audit all `.replace(/_/g, ' ')` calls and replace with proper title-casing
- DDM sustainability metric names: apply the same label cleanup

**Files touched:**
- `frontend/src/pages/ModelBuilder/Models/DDMView.tsx` — fix stage badge text, metric names
- `frontend/src/pages/ModelBuilder/Models/CompsView.tsx` — verify implied value labels
- `frontend/src/pages/ModelBuilder/Models/RevBasedView.tsx` — verify status labels
- `frontend/src/utils/format.ts` (or wherever shared utility lives from 8A) — add stage/label utilities

---

## AREA 4: SCENARIO PILL REORDER

### Change
All views that have scenario tabs (DCF, DDM, Revenue-Based) currently show `Base / Bull / Bear`. Change to `Bear / Base / Bull` with Base remaining the default.

**Files touched:**
- `frontend/src/pages/ModelBuilder/Models/DCFView.tsx` — reorder `availableScenarios` filter
- `frontend/src/pages/ModelBuilder/Models/DDMView.tsx` — same
- `frontend/src/pages/ModelBuilder/Models/RevBasedView.tsx` — same (already has `bear, base, bull` order in `allScenarios` but not in the tabs)

---

## AREA 5: DDM & REVENUE-BASED DETAIL UPGRADE

### Current State
- **DCF:** Full 10-year projection table (19 rows), key outputs panel, waterfall chart, scenario tabs — comprehensive
- **DDM:** Dividend schedule table, value decomposition (4 numbers), sustainability panel — functional but sparse
- **Revenue-Based:** Growth metrics panel, revenue projection table, scenario comparison bars — sparse

### Goal
Bring DDM and Revenue-Based closer to DCF's level of detail. This means more data visualization, richer output panels, and better storytelling of the valuation logic.

#### 5A. DDM Detail Upgrade

**Add:**
1. **Dividend Growth Trajectory Chart** — A line chart (Recharts) showing projected DPS over the multi-stage horizon. X-axis: years, Y-axis: DPS ($). Color-coded by stage (high growth = blue, transition = yellow, terminal = green). Shows how dividends evolve over time. This is the DDM equivalent of the DCF projection table.

2. **Value Waterfall** — Similar to DCF's EV bridge but for DDM: PV Stage 1 → PV Stage 2 → PV Terminal → Total Intrinsic Value. Bar chart with labeled steps.

3. **Key Outputs Panel** — Matching DCF's layout: Intrinsic Value, Current Dividend Yield, Implied Dividend Yield at Intrinsic, Payout Ratio, Cost of Equity, Total PV, TV % of Total. Formatted as a proper panel, not just decomposition numbers.

4. **Sustainability Detail** — Expand the sustainability section: show each metric with a mini progress bar (0-1 scale), plus a tooltip explaining what each metric means and why it matters for dividend safety.

**Data availability:** All data already exists in `DDMResult` — `dividend_schedule` has per-year data, `sustainability.metrics` has the 6 metrics. No backend changes needed.

**Files touched:**
- `frontend/src/pages/ModelBuilder/Models/DDMView.tsx` — add chart, waterfall, key outputs, expand sustainability
- `frontend/src/pages/ModelBuilder/Models/DDMView.module.css` — new section styles

#### 5B. Revenue-Based Detail Upgrade

**Add:**
1. **Revenue Growth Trajectory Chart** — Line chart showing projected revenue over the projection horizon. X-axis: years, Y-axis: revenue ($). Bear/Base/Bull as three lines overlaid.

2. **Multiple Compression/Expansion Chart** — Line chart showing how the EV/Revenue multiple evolves by year (multiples_by_year from scenario data). Helps visualize whether the model assumes multiple compression or expansion.

3. **Key Outputs Panel** — Matching DCF's layout: Weighted Implied Price, Current Price, Upside, Rule of 40 Score, EV/ARR, Magic Number, PSG Ratio. Proper panel formatting.

4. **Scenario Comparison Upgrade** — The existing scenario comparison bars are too basic. Replace with a proper table showing Bear/Base/Bull side by side: Implied Price, Upside %, Weight, Primary Revenue Multiple, Exit Revenue. Plus a mini football field chart below (horizontal bars like the Overview football field).

**Data availability:** All data exists in `RevBasedResult`. Scenario data has `projected_revenue`, `revenue_growth_rates`, `multiples_by_year`, `primary_implied_price`, `upside_downside_pct`. No backend changes needed.

**Files touched:**
- `frontend/src/pages/ModelBuilder/Models/RevBasedView.tsx` — add charts, key outputs, upgrade scenario comparison
- `frontend/src/pages/ModelBuilder/Models/RevBasedView.module.css` — new section styles

---

## AREA 6: DCF KEY OUTPUTS & CHART UPGRADE

### 6A. Key Outputs Panel Redesign
**Current:** A flat grid of 6 label/value pairs. Feels like "a bar of numbers."
**Goal:** Make it feel like the culmination of the model — the "so what."

**New layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│ KEY OUTPUTS                                                      │
│                                                                   │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│ │  Enterprise  │  │   Equity    │  │  Implied    │              │
│ │    Value     │  │   Value     │  │   Price     │              │
│ │   $2.85T    │  │   $2.79T    │  │  $178.45    │              │
│ └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                   │
│  PV of FCFs .............. $1.12T    (39.3% of EV)               │
│  PV of Terminal Value .... $1.73T    (60.7% of EV)               │
│  Less: Net Debt .......... -$62.5B                                │
│  ─────────────────────────────                                    │
│  Equity Value ............ $2.79T                                 │
│  ÷ Shares Outstanding .... 15.6B                                  │
│  = Implied Price ......... $178.45   (+12.3% upside)             │
│                                                                   │
│  WACC: 10.2%  │  Terminal Growth: 2.5%  │  TV % of EV: 60.7%    │
└─────────────────────────────────────────────────────────────────┘
```

**Key changes:**
- Top 3 numbers (EV, Equity Value, Implied Price) get prominence as large cards
- Below: a step-down calculation showing how you get from EV to implied price (mirrors the waterfall logic in text form)
- Bottom bar: key assumptions (WACC, terminal growth, TV %) as reference
- The panel tells a story: "Here's the enterprise value, here's how we get to equity, here's your price"

**Files touched:**
- `frontend/src/pages/ModelBuilder/Models/DCFView.tsx` — redesign key outputs section
- `frontend/src/pages/ModelBuilder/Models/DCFView.module.css` — new card/step-down styles

#### 6B. Waterfall Chart Detail Upgrade
**Current:** Basic Recharts BarChart with colored bars. Minimal labels.
**Goal:** Fidelity-level detail.

**Changes:**
- Add value labels directly on each bar (not just in tooltip)
- Add connecting lines between steps showing the running total
- Add percentage annotations (e.g., "61% of EV" next to terminal value bar)
- Improve axis formatting — Y-axis should use compact dollar format ($1.7T not $1,700,000,000,000)
- Add a subtle reference line for current market cap for context
- Tooltip on hover should show the step detail plus running total

**Files touched:**
- `frontend/src/pages/ModelBuilder/Models/DCFView.tsx` — enhance waterfall chart with labels, annotations
- `frontend/src/pages/ModelBuilder/Models/DCFView.module.css` — chart annotation styles

---

## AREA 7: EXPORT BUTTON ON MODEL TAB

### Current State
The main Model Builder page header has an ExportDropdown that appears when `activeModelId` exists. But when you're on the Model sub-tab viewing results, there's no export option directly on the view itself. You have to scroll up to the page header or know it's there.

### Change
Add an ExportDropdown directly on each model view (DCFView, DDMView, CompsView, RevBasedView) so you can export the current model results right from where you're looking at them.

**UI:** A small export button in the top-right of each model view's ResultsCard or header area:
```
┌─────────────────────────────────────────────────────────────┐
│  Implied Price: $178.45    +12.3%    Current: $158.65       │
│  WACC: 10.2%  │  Terminal: 2.5%  │  TV%: 60.7%  [Export ▾] │
└─────────────────────────────────────────────────────────────┘
```

**Export options per model type:**
- **Excel (.xlsx):** Uses existing `/api/v1/export/model/{modelId}/excel` endpoint — requires `activeModelId` (which will exist after 8O auto-creates model records on run)
- **PDF Report:** Uses existing `/api/v1/export/model/{modelId}/pdf` endpoint
- If `activeModelId` is not set (model hasn't been saved yet), show a tooltip: "Save model first to enable export" and disable the button

**Files touched:**
- `frontend/src/pages/ModelBuilder/Models/DCFView.tsx` — add ExportDropdown
- `frontend/src/pages/ModelBuilder/Models/DDMView.tsx` — add ExportDropdown
- `frontend/src/pages/ModelBuilder/Models/CompsView.tsx` — add ExportDropdown
- `frontend/src/pages/ModelBuilder/Models/RevBasedView.tsx` — add ExportDropdown
- `frontend/src/pages/ModelBuilder/Models/ResultsCard.tsx` — optionally add export slot to ResultsCard for consistent placement

---

## SESSION ORGANIZATION (Recommended for PM)

### Session 8H — Comps Fix + Peer Discovery Backend (Backend Only)
**Scope:** Areas 1A, 1B
**Files:**
- `backend/services/company_service.py` — add find_peers()
- `backend/repositories/company_repo.py` — sector/industry peer query
- `backend/routers/models_router.py` — auto-discover peers in run_comps
- `backend/engines/comps_engine.py` — null safety, status field
- `backend/engines/models.py` — add status to CompsResult
**Complexity:** Medium
**Estimated acceptance criteria:** 10–12

### Session 8I — Comps Frontend + Error Boundary + Underscore Fix + Export (Frontend Only)
**Scope:** Areas 1C, 2, 3, 4, 7
**Files:**
- `CompsView.tsx` — peer selection panel, two-state rendering, null safety
- `CompsView.module.css` — peer panel styles
- `ModelTab.tsx` — pass peer_tickers
- `ModelBuilderPage.tsx` — move ErrorBoundary
- `ErrorBoundary.tsx` — human-readable errors
- `DDMView.tsx` — underscore fix
- `RevBasedView.tsx` — underscore fix
- `DCFView.tsx`, `DDMView.tsx`, `RevBasedView.tsx` — scenario reorder + export button
- `ResultsCard.tsx` — export slot
- `CompsView.tsx` — export button
- `utils/format.ts` — shared label utilities
**Complexity:** Medium-High (peer selection panel is new component, ErrorBoundary restructure)
**Estimated acceptance criteria:** 20–25
**Depends on:** Session 8H (backend peer discovery must exist)

### Session 8J — DDM & Revenue-Based Detail Upgrade (Frontend Only)
**Scope:** Area 5
**Files:**
- `DDMView.tsx` — dividend trajectory chart, value waterfall, key outputs, sustainability expansion
- `DDMView.module.css` — new section styles
- `RevBasedView.tsx` — revenue trajectory chart, multiple chart, key outputs, scenario comparison upgrade
- `RevBasedView.module.css` — new section styles
**Complexity:** Medium-High (two new Recharts charts per view, panel redesigns)
**Estimated acceptance criteria:** 20–25

### Session 8K — DCF Key Outputs & Chart Upgrade (Frontend Only)
**Scope:** Area 6
**Files:**
- `DCFView.tsx` — key outputs panel redesign, waterfall chart detail upgrade
- `DCFView.module.css` — new card/step-down styles, chart annotation styles
**Complexity:** Medium (redesign within existing component, chart enhancements)
**Estimated acceptance criteria:** 12–15

---

## DEPENDENCIES & RISKS

| Risk | Mitigation |
|------|------------|
| Auto peer discovery finds irrelevant peers | Use sector + industry + market cap range filtering; user can always override via manual selection |
| Few companies in DB with cached financials for peer matching | Peer discovery gracefully returns fewer peers with a warning; manual selection always available |
| Recharts charts in DDM/RevBased views add bundle size | Recharts is already loaded (DCF uses it); no additional dependency |
| ErrorBoundary key change causes unnecessary re-renders | Key only includes ticker + subtab + modelType — these don't change during normal interaction |
| Peer selection state lost on tab switch | Store peer list in modelStore so it persists during the session |

---

## DECISIONS MADE

1. Comps auto-discovers peers from DB by sector/industry/market cap — no manual selection required for most cases
2. Manual peer selection panel always available (collapsible) for user customization
3. Comps has two UI states: setup (no peers) and results (peers loaded) — no crash
4. ErrorBoundary moves to tab content level only — page chrome stays accessible
5. Error messages become human-readable with actionable suggestions
6. Scenario order: Bear / Base / Bull across all model views (consistent with Assumptions)
7. DDM gets: dividend trajectory chart, value waterfall, expanded key outputs, richer sustainability
8. Revenue-Based gets: revenue trajectory chart, multiple evolution chart, expanded key outputs, upgraded scenario comparison
9. DCF key outputs becomes a storytelling panel (EV → Equity → Price step-down)
10. DCF waterfall gets bar labels, connecting lines, percentage annotations, market cap reference line
11. All underscore syntax cleaned up via shared utility functions
12. Export button (Excel/PDF) added to each model view's ResultsCard area
13. Export requires activeModelId (auto-created via 8O); disabled with tooltip if not yet saved

---

*End of Model Builder — Model Sub-Tab Update Plan*
*Phase 8H–8K · Prepared March 5, 2026*
