# Session 8I — Comps Frontend + Error Boundary + Underscore Fix + Export Button
## Phase 8: Model Builder

**Priority:** High (Tier 2 — completes the Comps crash fix)
**Type:** Frontend Only
**Depends On:** 8H (Comps backend peer discovery + null safety), 8A (displayNames.ts)
**Spec Reference:** `specs/phase8_model_builder_model.md` → Areas 1C, 2, 3, 4, 7

---

## SCOPE SUMMARY

Complete the Comps crash fix on the frontend with a peer selection panel and null-safe rendering. Move the ErrorBoundary to wrap only tab content (not the entire page). Fix underscore display issues in DDM, Comps, and RevBased views using `displayNames.ts`. Reorder scenario pills to Bear/Base/Bull across all model views. Add an export button (Excel/PDF) to each model view's results area.

---

## TASKS

### Task 1: Comps Frontend — Peer Selection Panel + Null Safety
**Description:** Add a peer selection UI at the top of CompsView with two states: setup (no peers) and results (analysis complete). Make all property access null-safe.

**Subtasks:**
- [ ] 1.1 — In `frontend/src/pages/ModelBuilder/Models/CompsView.tsx`, add the two-state rendering:
  - **Check `result.status`**: if `"no_peers"` → show setup state (peer selection prominent, no results). If `"ready"` → show results state (peer panel collapsed, full results below). If `"error"` → show error message from `result.metadata.warnings`.
  - If `status` field doesn't exist (backward compat), check `result.peer_group?.peers?.length > 0`
- [ ] 1.2 — Add peer selection panel component at the top of CompsView:
  ```
  PEER GROUP                                    [▾ Collapse]
  ──────────────────────────────────────────────────────────
  Search: [Enter ticker...  ] [Add]
  
  AAPL  Apple Inc.         $3.2T   ✕
  MSFT  Microsoft Corp.    $2.8T   ✕
  ...
  
  [Run Comps Analysis]    Auto-discovered: 12 peers from Technology
  ```
  - Local state: `peerTickers: string[]` (initialized from `result.peer_group.peers` ticker list if available), `peerSearch: string`, `searchResults`, `panelCollapsed: boolean`
  - Search: use existing autocomplete pattern — debounced call to `/api/v1/companies/search?q={query}`
  - Add button: adds ticker to `peerTickers` list
  - Remove (✕): removes ticker from list
  - "Run Comps Analysis" button: calls `onRunWithPeers(peerTickers)` callback
- [ ] 1.3 — Accept new prop on CompsView or handle internally:
  - Option A: CompsView accepts `onRerun: (peerTickers: string[]) => void` prop, ModelTab passes it
  - Option B: CompsView makes the API call directly using `api.post`
  - Prefer Option A for consistency with ModelTab's run pattern
- [ ] 1.4 — Null-safe all property access in CompsView:
  - `result.peer_group?.peers ?? []` instead of `result.peer_group.peers`
  - `result.aggregate_multiples ?? {}` instead of `result.aggregate_multiples`
  - `result.implied_values ?? {}` instead of `result.implied_values`
  - `result.quality_assessment?.factor_scores ?? {}` instead of `result.quality_assessment?.factor_scores`
  - Guard all `.map()` calls with optional chaining or fallback to empty array
- [ ] 1.5 — In `ModelTab.tsx`, update to pass peer_tickers:
  - Accept `peerTickers` from CompsView rerun callback
  - When rerunning, pass peer_tickers in the request body:
    ```typescript
    await api.post(`/api/v1/model-builder/${ticker}/run/comps`, { peer_tickers: peerTickers })
    ```
- [ ] 1.6 — In `CompsView.module.css`, add peer panel styles:
  - `.peerPanel` — dark card, subtle border, collapsible
  - `.peerSearch` — inline search input + Add button
  - `.peerList` — compact rows: ticker (mono bold), company name, market cap, ✕ remove button
  - `.peerPanelCollapsed` — single-line summary: "12 peers" + expand toggle
  - `.runBtn` — accent button for "Run Comps Analysis"
  - `.setupState` — centered layout when no results yet

---

### Task 2: Move ErrorBoundary to Tab Content Level
**Description:** Move the ErrorBoundary from App.tsx (page level) to ModelBuilderPage.tsx (tab content level only), so page chrome (search, model pills, sub-tabs) remains accessible during crashes.

**Subtasks:**
- [ ] 2.1 — In `frontend/src/pages/ModelBuilderPage.tsx`, wrap only the `tabContent()` call in an ErrorBoundary:
  ```tsx
  <div className={styles.tabContent}>
    <ErrorBoundary
      key={`${activeTicker}-${activeSubTab}-${activeModelType}`}
      moduleName={activeSubTab}
    >
      {activeTicker ? tabContent() : emptyState}
    </ErrorBoundary>
  </div>
  ```
  - The `key` includes `activeTicker`, `activeSubTab`, and `activeModelType` so switching any of these resets the error boundary automatically
  - Import `ErrorBoundary` from `@/components/ui/ErrorBoundary/ErrorBoundary`
- [ ] 2.2 — The existing `ErrorBoundary` in `App.tsx` wraps the entire active page. Keep it as a global catch-all, but the Model Builder's inner ErrorBoundary will catch model-specific errors first.
- [ ] 2.3 — In `ErrorBoundary.tsx`, improve the error display:
  - Replace raw error messages with user-friendly text. Map common errors:
    - "cannot read properties of undefined" → "This model encountered a data issue. The required data may not be available."
    - "is not a function" → "This model encountered an internal error."
    - Generic fallback: "This model encountered an unexpected issue."
  - Add suggestion text: "Try switching to a different model type using the selector above, or select a different ticker."
  - Keep the "Reload Module" button but rename to "Try Again"
  - Show the raw error in a collapsible "Technical Details" section for debugging

---

### Task 3: Underscore Syntax Cleanup Across Model Views
**Description:** Fix raw snake_case keys displayed in DDM, Comps, and RevBased views using the shared `displayNames.ts` utility.

**Subtasks:**
- [ ] 3.1 — In `DDMView.tsx`:
  - Stage badges: currently `{row.stage.replace(/_/g, ' ')}` produces "high growth" (lowercase). Replace with `displayStageName(row.stage)` from `@/utils/displayNames` → "High Growth".
  - Sustainability metric names: if any use raw keys, replace with `displayLabel()`.
  - Import `displayStageName, displayLabel` from `@/utils/displayNames`.
- [ ] 3.2 — In `CompsView.tsx`:
  - Implied values table: `{key.replace(/_/g, '/').toUpperCase()}` produces things like `EV/EBITDA`, `P/FCF`. This is actually correct for multiple names — but verify all keys. Create a local map if needed:
    ```typescript
    const IMPLIED_VALUE_LABELS: Record<string, string> = {
      pe: 'P/E', ev_ebitda: 'EV/EBITDA', ev_revenue: 'EV/Revenue',
      pb: 'P/B', p_fcf: 'P/FCF',
    };
    ```
    Replace the `.replace(/_/g, '/').toUpperCase()` with the map lookup.
  - Quality assessment factor names: `{name.replace(/_/g, ' ').replace(/\b\w/g, ...)}` — replace with `displayLabel(name)`.
  - Import `displayLabel` from `@/utils/displayNames`.
- [ ] 3.3 — In `RevBasedView.tsx`:
  - Verify `statusLabel()` and `statusBadgeClass()` produce clean output.
  - Any metric names using raw keys → use `displayLabel()`.
  - Import from `@/utils/displayNames` if needed.
- [ ] 3.4 — In `ModelBuilderPage.tsx`:
  - The `MODEL_TYPE_LABELS` map is already clean. Verify `MODEL_TAB_LABELS` is too. Consider importing `displayModelName` for the detection bar where model names appear.

---

### Task 4: Scenario Pill Reorder Across Model Views
**Description:** Change scenario tabs from Base/Bull/Bear to Bear/Base/Bull across all model views.

**Subtasks:**
- [ ] 4.1 — In `DDMView.tsx`:
  - Find the scenario tabs/pills rendering. If using a `SCENARIO_LABELS` record or array, reorder to Bear/Base/Bull.
  - The `availableScenarios` may be derived from `result.scenarios` keys — ensure they're rendered in Bear/Base/Bull order regardless of object key order.
  - Default `activeScenario` stays `'base'`.
- [ ] 4.2 — In `RevBasedView.tsx`: same treatment.
- [ ] 4.3 — In `DCFView.tsx`: verify scenario order. If it already uses the correct order, no change needed.
- [ ] 4.4 — Ensure the order is: Bear (left) → Base (center) → Bull (right), matching the Assumptions tab (session 8D).

---

### Task 5: Export Button on Each Model View
**Description:** Add an ExportDropdown to each model view so users can export results directly from the results area.

**Subtasks:**
- [ ] 5.1 — In `ResultsCard.tsx`, add an optional `exportSlot` prop:
  ```typescript
  interface ResultsCardProps {
    // ...existing
    exportSlot?: React.ReactNode;
  }
  ```
  Render the slot in the top-right area of the card.
- [ ] 5.2 — In each model view (`DCFView.tsx`, `DDMView.tsx`, `CompsView.tsx`, `RevBasedView.tsx`), pass an `ExportDropdown` component into the ResultsCard's export slot:
  ```tsx
  <ResultsCard
    {...props}
    exportSlot={
      <ExportDropdown
        options={[
          {
            label: 'Excel (.xlsx)',
            format: 'excel',
            onClick: async () => {
              const modelId = useModelStore.getState().activeModelId;
              if (!modelId) return;
              const date = new Date().toISOString().slice(0, 10);
              await downloadExport(
                `/api/v1/export/model/${modelId}/excel`,
                `${result.ticker}_${result.model_type}_${date}.xlsx`,
              );
            },
          },
          {
            label: 'PDF Report',
            format: 'pdf',
            onClick: async () => {
              const modelId = useModelStore.getState().activeModelId;
              if (!modelId) return;
              const date = new Date().toISOString().slice(0, 10);
              await downloadExport(
                `/api/v1/export/model/${modelId}/pdf`,
                `${result.ticker}_${result.model_type}_${date}.pdf`,
              );
            },
          },
        ]}
      />
    }
  />
  ```
- [ ] 5.3 — If `activeModelId` is null (model not yet saved/auto-saved — auto-save is built in 8O), show a disabled export button with tooltip: "Run and save model first to enable export".
- [ ] 5.4 — Import `ExportDropdown` from `@/components/ui/ExportButton/ExportDropdown` and `downloadExport` from `@/services/exportService` in each view. Import `useModelStore` for `activeModelId`.

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: CompsView renders without crashing when `peer_group` is empty or undefined.
- [ ] AC-2: CompsView shows setup state when `status === "no_peers"`: peer search prominent, no results table.
- [ ] AC-3: CompsView shows results state when `status === "ready"`: peer panel collapsed, full results below.
- [ ] AC-4: Peer selection panel: search bar with autocomplete, Add button, peer list with ✕ remove.
- [ ] AC-5: "Run Comps Analysis" button sends peer_tickers to the backend and re-renders with results.
- [ ] AC-6: All property access in CompsView is null-safe (no `cannot read properties of undefined` crashes).
- [ ] AC-7: ErrorBoundary wraps only tab content in ModelBuilderPage (search bar, model pills, sub-tabs remain accessible).
- [ ] AC-8: ErrorBoundary key includes ticker + subTab + modelType (switching any resets the boundary).
- [ ] AC-9: Error messages are user-friendly, not raw JS errors. "Try switching to a different model" suggestion shown.
- [ ] AC-10: Raw error available in collapsible "Technical Details" section.
- [ ] AC-11: DDM stage badges display "High Growth" not "high growth" or "high_growth".
- [ ] AC-12: Comps implied value method labels use a proper map (not `replace(/_/g, '/').toUpperCase()`).
- [ ] AC-13: Comps quality factor names use `displayLabel()` (not inline replace).
- [ ] AC-14: Scenario order is Bear/Base/Bull in DDMView, RevBasedView, and DCFView.
- [ ] AC-15: Base remains the default active scenario.
- [ ] AC-16: Each model view (DCF, DDM, Comps, RevBased) has an Export button in the ResultsCard area.
- [ ] AC-17: Export button offers Excel and PDF options.
- [ ] AC-18: Export disabled with tooltip when `activeModelId` is null.
- [ ] AC-19: No `.replace(/_/g, ' ')` inline calls remain in model view components.
- [ ] AC-20: No visual regressions on existing model view layouts, charts, or tables.

---

## FILES TOUCHED

**New files:**
- None

**Modified files:**
- `frontend/src/pages/ModelBuilder/Models/CompsView.tsx` — peer selection panel, two-state rendering, null safety, implied value label map, quality factor displayLabel, export button
- `frontend/src/pages/ModelBuilder/Models/CompsView.module.css` — peer panel styles, setup/results state
- `frontend/src/pages/ModelBuilder/Models/ModelTab.tsx` — pass peer_tickers, accept rerun callback
- `frontend/src/pages/ModelBuilderPage.tsx` — wrap tabContent in ErrorBoundary with composite key
- `frontend/src/components/ui/ErrorBoundary/ErrorBoundary.tsx` — user-friendly messages, suggestion text, collapsible technical details
- `frontend/src/components/ui/ErrorBoundary/ErrorBoundary.module.css` — updated styles for suggestion, collapsible
- `frontend/src/pages/ModelBuilder/Models/DDMView.tsx` — displayStageName for stage badges, scenario reorder, export button
- `frontend/src/pages/ModelBuilder/Models/RevBasedView.tsx` — underscore fix, scenario reorder, export button
- `frontend/src/pages/ModelBuilder/Models/DCFView.tsx` — scenario reorder verification, export button
- `frontend/src/pages/ModelBuilder/Models/ResultsCard.tsx` — add `exportSlot` prop

---

## BUILDER PROMPT

> **Session 8I — Comps Frontend + Error Boundary + Underscore Fix + Export Button**
>
> You are building session 8I of the Finance App v2.0 update.
>
> **What you're doing:** Five things in one session: (1) Complete the Comps crash fix with a peer selection panel and null-safe rendering, (2) Move ErrorBoundary to tab content level, (3) Fix underscore display issues across model views, (4) Reorder scenario pills to Bear/Base/Bull, (5) Add export buttons to each model view.
>
> **Context:** Session 8H built the backend: auto-peer-discovery, CompsResult `status` field ("ready"/"no_peers"/"error"), null-safe peer_group default. Session 8A created `displayNames.ts` with `displayModelName`, `displayStageName`, `displayLabel`, etc. The current CompsView crashes when `peer_group` is undefined — you're fixing that and adding a peer management UI.
>
> **Existing code:**
>
> `CompsView.tsx` — renders: ResultsCard, Peer Comparison Table, Implied Values Panel, Quality Assessment. Currently accesses `result.peer_group.peers` directly (crash source). Has `key.replace(/_/g, '/').toUpperCase()` for implied value labels and `name.replace(/_/g, ' ').replace(...)` for quality factors.
>
> `ModelTab.tsx` — routes to DCFView/DDMView/CompsView/RevBasedView based on `modelType`. Calls `api.post('/run/{endpoint}', {})` with empty body (no peer_tickers).
>
> `ModelBuilderPage.tsx` — full page with search bar, model type pills, detection bar, sub-tabs, tab content. Currently NO ErrorBoundary around tab content — the global one in App.tsx catches everything.
>
> `ErrorBoundary.tsx` — class component with `getDerivedStateFromError`, shows raw error message, "Reload Module" button.
>
> `DDMView.tsx` — has `stageClass()` function and renders `{row.stage.replace(/_/g, ' ')}` for stage badges. `SCENARIO_LABELS` already maps base→"Base" etc.
>
> `ResultsCard.tsx` — simple card with impliedPrice, currentPrice, upsidePct. No export slot.
>
> `displayNames.ts` — at `frontend/src/utils/displayNames.ts` with `displayModelName`, `displayStageName`, `displayEventType`, `displayAgreementLevel`, `displayLabel`, etc.
>
> **Cross-cutting rules:**
> - Display Name Rule: All backend snake_case keys displayed in the UI must use the shared `displayNames.ts` utility. Never show raw keys. Never use inline `.replace(/_/g, ' ')`. Import from `@/utils/displayNames`.
> - Chart Quality: All charts must meet Fidelity/Yahoo Finance information-density standards.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%).
> - Scenario Order: Bear / Base / Bull (left to right), Base default.
>
> **Task 1: Comps Peer Selection + Null Safety**
>
> Rewrite CompsView to have two states:
> - Setup state (`status === "no_peers"` or no peers in peer_group): show prominent peer search panel, no results
> - Results state (`status === "ready"` with peers): collapsed peer panel at top, full results below
>
> Peer selection panel:
> - Debounced search via `/api/v1/companies/search?q={query}`
> - Peer list with ticker, name, market cap, ✕ remove button
> - "Run Comps Analysis" button that triggers rerun with selected peers
> - Auto-populated from backend auto-discovered peers when available
> - Collapsible after initial run
>
> Null safety: guard ALL property access with `?.` and `?? []` / `?? {}` fallbacks:
> - `result.peer_group?.peers ?? []`
> - `result.aggregate_multiples ?? {}`
> - `result.implied_values ?? {}`
> - `result.quality_assessment?.factor_scores ?? {}`
>
> Update ModelTab to support rerunning with peer_tickers.
>
> **Task 2: ErrorBoundary Scope**
>
> In ModelBuilderPage.tsx, wrap `tabContent()` call:
> ```tsx
> <ErrorBoundary key={`${activeTicker}-${activeSubTab}-${activeModelType}`} moduleName={activeSubTab}>
>   {activeTicker ? tabContent() : emptyState}
> </ErrorBoundary>
> ```
>
> In ErrorBoundary.tsx: map common JS errors to friendly messages, add "Try switching model" suggestion, collapsible raw error details.
>
> **Task 3: Underscore Fix**
>
> - DDMView: `displayStageName(row.stage)` instead of `row.stage.replace(/_/g, ' ')`
> - CompsView implied values: use local `IMPLIED_VALUE_LABELS` map or `displayLabel`
> - CompsView quality factors: `displayLabel(name)` instead of inline replace
> - RevBasedView: verify clean, fix if needed
> - Import from `@/utils/displayNames`
>
> **Task 4: Scenario Reorder**
>
> In DDMView, RevBasedView (and DCFView if needed): render scenario tabs as Bear/Base/Bull. If using a `SCENARIO_LABELS` record, ensure rendering order is `['bear', 'base', 'bull']`. Default stays `'base'`.
>
> **Task 5: Export Button**
>
> Add `exportSlot?: React.ReactNode` to ResultsCard props, render in top-right.
> Pass `<ExportDropdown>` with Excel/PDF options into each view's ResultsCard.
> Disable if `activeModelId` is null (tooltip: "Run and save model first").
>
> **Acceptance criteria:**
> 1. CompsView doesn't crash on empty/undefined peer_group
> 2. Setup state shown when no peers; results state when peers exist
> 3. Peer selection panel with search, add, remove, run
> 4. All CompsView property access null-safe
> 5. ErrorBoundary wraps tab content only (search/pills/tabs accessible during error)
> 6. Error messages user-friendly with switching suggestion
> 7. DDM stages: "High Growth" not "high_growth"
> 8. No inline `.replace(/_/g, ...)` in model views
> 9. Scenario order: Bear/Base/Bull across all views
> 10. Export button on all 4 model views
> 11. Export disabled with tooltip when no activeModelId
> 12. No regressions
>
> **Files to create:** None
>
> **Files to modify:**
> - `frontend/src/pages/ModelBuilder/Models/CompsView.tsx`
> - `frontend/src/pages/ModelBuilder/Models/CompsView.module.css`
> - `frontend/src/pages/ModelBuilder/Models/ModelTab.tsx`
> - `frontend/src/pages/ModelBuilderPage.tsx`
> - `frontend/src/components/ui/ErrorBoundary/ErrorBoundary.tsx`
> - `frontend/src/components/ui/ErrorBoundary/ErrorBoundary.module.css`
> - `frontend/src/pages/ModelBuilder/Models/DDMView.tsx`
> - `frontend/src/pages/ModelBuilder/Models/RevBasedView.tsx`
> - `frontend/src/pages/ModelBuilder/Models/DCFView.tsx`
> - `frontend/src/pages/ModelBuilder/Models/ResultsCard.tsx`
>
> **Technical constraints:**
> - CSS modules for all styling
> - Import `displayStageName`, `displayLabel` from `@/utils/displayNames`
> - `api.get<T>` / `api.post<T>` for data fetching
> - Debounced search: 200ms timeout for peer ticker search
> - Peer list stored in local component state (not in store)
> - ExportDropdown already exists at `@/components/ui/ExportButton/ExportDropdown`
> - `downloadExport` from `@/services/exportService`
> - `useModelStore` for `activeModelId`
> - ErrorBoundary is a class component (React requirement for error boundaries)
