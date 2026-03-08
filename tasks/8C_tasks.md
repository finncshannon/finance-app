# Session 8C — Data Readiness Frontend + Diagnostic Overlay + Historical Polish
## Phase 8: Model Builder

**Priority:** Normal
**Type:** Frontend Only
**Depends On:** 8B (data readiness endpoint must exist)
**Spec Reference:** `specs/phase8_model_builder_historical.md` → Areas 1C, 2A–2D, 3A, 3B

---

## SCOPE SUMMARY

Build a new "Data Readiness" 4th sub-tab inside the Historical Data tab that renders per-engine readiness reports (Ready/Partial/Not Possible) with collapsible engine cards and a coverage progress bar. Add a diagnostic overlay toggle ("Inspect") to the financial statement tables that adds glass-bubble indicators on populated cells and warning markers on missing-but-critical cells, with hover popovers showing source, engine usage, and derivation info. Add hover tooltips on blank "—" cells and a data freshness indicator with refresh button.

---

## TASKS

### Task 1: Add TypeScript Interfaces for Data Readiness
**Description:** Define the response types for the `/data-readiness` endpoint.

**Subtasks:**
- [ ] 1.1 — In `frontend/src/types/models.ts`, add:
  ```typescript
  export interface FieldReadiness {
    field: string;
    label: string;
    status: 'present' | 'missing' | 'derived';
    years_available: number;
    source: string | null;
    reason: string;
  }

  export interface EngineReadiness {
    verdict: 'ready' | 'partial' | 'not_possible';
    verdict_label: string;
    detection_score: number | null;
    critical_fields: FieldReadiness[];
    important_fields: FieldReadiness[];
    helpful_fields: FieldReadiness[];
    missing_impact: string | null;
    notes: string[];
  }

  export interface FieldMetadataEntry {
    status: 'present' | 'missing' | 'derived';
    source: string | null;
    source_detail: string | null;
    years_available: number;
    engines: { engine: string; level: string; reason: string }[];
  }

  export interface DetectionSummary {
    recommended_model: string;
    confidence: string;
    confidence_percentage: number;
  }

  export interface DataReadinessResult {
    ticker: string;
    data_years_available: number;
    total_fields: number;
    populated_fields: number;
    coverage_pct: number;
    engines: Record<string, EngineReadiness>;
    field_metadata: Record<string, FieldMetadataEntry>;
    detection_result: DetectionSummary | null;
  }
  ```

---

### Task 2: Create Data Readiness Sub-Tab Component
**Description:** Build the 4th sub-tab that shows coverage stats and per-engine readiness cards.

**Subtasks:**
- [ ] 2.1 — Create `frontend/src/pages/ModelBuilder/Historical/DataReadinessTab.tsx`:
  - Fetch from `GET /api/v1/model-builder/{ticker}/data-readiness` using `api.get<DataReadinessResult>(...)`
  - Read `activeTicker` from `modelStore`
  - Re-fetch when ticker changes
  - Render: coverage progress bar + 4 engine readiness cards
- [ ] 2.2 — Coverage section:
  - Label: "DATA COVERAGE"
  - Stats: "{N} years available · {populated}/{total} fields populated ({pct}%)"
  - Progress bar: filled portion = `coverage_pct`, color gradient from red (<50%) → yellow (50-80%) → green (>80%)
- [ ] 2.3 — Engine cards (one per engine: DCF, DDM, Comps, Revenue-Based):
  - Card header: engine name (using `displayModelName()`) + verdict badge (green "Ready", yellow "Partial", red "Not Possible")
  - Detection score: "{score}/100"
  - Collapsible body (expanded by default for non-"ready" engines, collapsed for "ready"):
    - Critical fields section: "{present}/{total} present" header, then list each field with icon (✓/✗/~), label, years, source
    - Important fields section: same
    - Helpful fields section: same (collapsed by default within the card)
  - Missing fields with critical/important status: show indented note explaining impact (from `missing_impact` and `notes`)
- [ ] 2.4 — Loading state: spinner. Error state: error message + retry. No ticker: "Select a ticker..."
- [ ] 2.5 — Create `frontend/src/pages/ModelBuilder/Historical/DataReadinessTab.module.css`:
  - Coverage bar, engine cards, verdict badges (color-coded), field rows with status icons, collapse/expand toggle, indented impact notes

**Implementation Notes:**
- Use `displayModelName()` from `@/utils/displayNames` for engine names in card headers.
- Verdict badge colors: `ready` → `var(--color-positive)`, `partial` → `var(--color-warning)`, `not_possible` → `var(--color-negative)`.
- Collapsible sections: use local state `expandedEngines: Set<string>`. Default: expand engines where verdict !== 'ready'.
- Status icons: ✓ (green, present), ~ (yellow, derived), ✗ (red, missing).
- Source text for derived fields: e.g. "computed from operating_cash_flow + capital_expenditure". For direct: "Yahoo Finance". For missing: "MISSING".

---

### Task 3: Add Data Readiness as 4th Sub-Tab
**Description:** Register the new sub-tab in the Historical Data tab.

**Subtasks:**
- [ ] 3.1 — In `frontend/src/pages/ModelBuilder/Historical/HistoricalDataTab.tsx`:
  - Add import: `import { DataReadinessTab } from './DataReadinessTab';`
  - Update the `SubTab` type: `type SubTab = 'income' | 'balance' | 'cashflow' | 'readiness';`
  - Add to `SUB_TAB_LABELS` array: `{ key: 'readiness', label: 'Data Readiness' }`
  - When `subTab === 'readiness'`, render `<DataReadinessTab />` instead of the financial table
  - The financial table rendering (tableWrapper, etc.) should only show when subTab is income/balance/cashflow

---

### Task 4: Diagnostic Overlay Toggle
**Description:** Add an "Inspect" toggle to the financial table sub-tabs that activates a diagnostic overlay layer.

**Subtasks:**
- [ ] 4.1 — In `HistoricalDataTab.tsx`, add state: `const [inspectMode, setInspectMode] = useState(false)`
- [ ] 4.2 — Add state for readiness data: `const [readinessData, setReadinessData] = useState<DataReadinessResult | null>(null)`. When `inspectMode` is toggled on, fetch from the data readiness endpoint (if not already cached). Cache the result for the session.
- [ ] 4.3 — Render a toggle switch in the sub-tab bar area, right-aligned:
  ```tsx
  <div className={styles.inspectToggle}>
    <label className={styles.toggleLabel}>
      <input
        type="checkbox"
        checked={inspectMode}
        onChange={(e) => setInspectMode(e.target.checked)}
        className={styles.toggleInput}
      />
      <span className={styles.toggleSlider} />
      <span className={styles.toggleText}>Inspect</span>
    </label>
  </div>
  ```
  - Only show the toggle when subTab is income/balance/cashflow (not readiness)
- [ ] 4.4 — In CSS, style the toggle as a sleek Apple-style slider: small pill shape (36px × 20px), smooth transition, `var(--accent-primary)` when on.

---

### Task 5: Glass Bubble Cell Indicators (Populated Cells)
**Description:** When inspect mode is on, populated cells get a glass-bubble visual treatment with hover popovers.

**Subtasks:**
- [ ] 5.1 — In `HistoricalDataTab.tsx`, when `inspectMode && readinessData`:
  - For each data cell, look up the field key in `readinessData.field_metadata`
  - If metadata exists and status is `present` or `derived`, add a glass-bubble CSS class to the `<td>`
- [ ] 5.2 — Glass bubble CSS (in `HistoricalDataTab.module.css`):
  ```css
  .glassBubble {
    position: relative;
    background: rgba(59, 130, 246, 0.04) !important;
    border: 1px solid rgba(59, 130, 246, 0.08);
    cursor: pointer;
    transition: background 150ms ease;
  }
  .glassBubble:hover {
    background: rgba(59, 130, 246, 0.08) !important;
    border-color: rgba(59, 130, 246, 0.15);
  }
  ```
- [ ] 5.3 — Add hover popover state: `const [popover, setPopover] = useState<{ fieldKey: string; year: number; rect: DOMRect } | null>(null)`.
- [ ] 5.4 — On cell hover (when inspect mode on), set the popover state. On mouse leave, clear it.
- [ ] 5.5 — Render a popover component positioned near the cell:
  ```
  Revenue · FY 2024
  $394.3B
  ──────────────────
  Source: Yahoo Finance (direct)
  Years available: 8
  ──────────────────
  Used by:
   • DCF — critical (projection)
   • Comps — critical (EV/Rev)
   • Revenue — critical (core)
   • DDM — helpful (context)
  ```
  - Use `displayModelName()` for engine names
  - Position: to the right of the cell (or left if near right edge)
- [ ] 5.6 — Popover CSS: dark bg, border, rounded, `z-index: 20`, mono font for values, sans for labels, max-width 280px. Subtle shadow.

**Implementation Notes:**
- The field_metadata map uses DB column names (e.g. `revenue`, `operating_cash_flow`). The `LineItem.key` in the table uses the FinancialRecord key names (e.g. `revenue`, `operating_cash_flow`). These may not match exactly — some mapping may be needed between the frontend `FinancialRecord` keys and the backend `financial_data` column names. The Builder should check and create a mapping if needed.
- Popover positioning: use `getBoundingClientRect()` on the cell element, then position the popover absolutely relative to the table wrapper.
- Only one popover visible at a time.

---

### Task 6: Missing-but-Critical Cell Indicators
**Description:** When inspect mode is on, missing cells ("—") that are critical or important for engines get a colored dot indicator.

**Subtasks:**
- [ ] 6.1 — In `HistoricalDataTab.tsx`, when `inspectMode && readinessData`:
  - For each missing cell, check if the field appears in any engine's critical or important tiers (via `field_metadata.engines[]`)
  - If critical for any engine: add `styles.missingCritical` class (red dot)
  - If important (but not critical) for any engine: add `styles.missingImportant` class (amber dot)
  - Otherwise: no indicator (plain "—")
- [ ] 6.2 — CSS for missing indicators:
  ```css
  .missingCritical::after {
    content: '';
    position: absolute;
    top: 4px;
    right: 4px;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--color-negative);
  }
  .missingImportant::after {
    content: '';
    position: absolute;
    top: 4px;
    right: 4px;
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--color-warning);
  }
  ```
  - Cells with these classes need `position: relative` (add via a shared class)
- [ ] 6.3 — Hovering missing-but-critical/important cells shows an impact popover:
  ```
  Dividends Paid · FY 2024
  NOT REPORTED
  ──────────────────
  Impact:
   • DDM — CRITICAL (missing)
     DDM not possible without dividend history
   • DCF — not needed
  ```

---

### Task 7: Blank Cell Hover Tooltip (Area 3A)
**Description:** In normal mode (not inspect), hovering a "—" cell shows a small tooltip: "Not reported by {ticker}".

**Subtasks:**
- [ ] 7.1 — In `HistoricalDataTab.tsx`, for missing cells (where `raw == null`), add a `title` attribute: `title={`Not reported by ${activeTicker}`}`. This uses the browser's native tooltip.
- [ ] 7.2 — Alternatively, for a nicer look, add a custom CSS tooltip using `::after` pseudo-element on hover. The tooltip says "Not reported by {ticker}" or "Not available from Yahoo Finance."

**Implementation Notes:**
- The simplest approach is `title` attribute for native tooltip. If a custom tooltip is desired, use CSS only — no JavaScript state needed.
- This only applies when inspect mode is OFF (or always, since the inspect popover would override).

---

### Task 8: Data Freshness Indicator (Area 3B)
**Description:** Show when data was last fetched and provide a manual refresh button.

**Subtasks:**
- [ ] 8.1 — In `HistoricalDataTab.tsx`, after the sub-tab bar, show a small text line:
  ```
  Data as of {date} · {N} fiscal years     [↻ Refresh]
  ```
  - Date comes from the most recent record's `period_end_date` or from a `fetched_at` timestamp
  - Fiscal years count from data length
  - Refresh button calls the existing financials endpoint with a `force_refresh=true` parameter (if supported), or just re-fetches
- [ ] 8.2 — Style: 11px font, `var(--text-tertiary)`, right-aligned or below the sub-tab bar. Refresh button is a subtle link-style button.

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: TypeScript interfaces for `DataReadinessResult`, `EngineReadiness`, `FieldReadiness`, `FieldMetadataEntry` exist in `types/models.ts`.
- [ ] AC-2: "Data Readiness" appears as the 4th sub-tab in Historical Data.
- [ ] AC-3: Data Readiness tab shows coverage progress bar with years available, fields populated, and percentage.
- [ ] AC-4: 4 engine cards (DCF, DDM, Comps, Revenue-Based) with verdict badges (Ready/Partial/Not Possible).
- [ ] AC-5: Engine cards use `displayModelName()` for headers.
- [ ] AC-6: Verdict badge color: green (ready), yellow (partial), red (not_possible).
- [ ] AC-7: Non-ready engines expanded by default; ready engines collapsed.
- [ ] AC-8: Each field shows status icon (✓/~/✗), label, years, source.
- [ ] AC-9: Missing critical/important fields show indented impact notes.
- [ ] AC-10: "Inspect" toggle appears in sub-tab bar area (only on income/balance/cashflow tabs).
- [ ] AC-11: Toggle is a sleek Apple-style slider.
- [ ] AC-12: Inspect mode OFF: table looks exactly as before (no visual changes).
- [ ] AC-13: Inspect mode ON: populated cells get subtle glass-bubble background.
- [ ] AC-14: Hovering a glass-bubble cell shows popover with field label, value, source, engine usage.
- [ ] AC-15: Popover uses `displayModelName()` for engine names.
- [ ] AC-16: Missing-but-critical cells show red dot indicator (inspect mode ON).
- [ ] AC-17: Missing-but-important cells show amber dot indicator (inspect mode ON).
- [ ] AC-18: Hovering missing-indicator cells shows impact popover.
- [ ] AC-19: Normal "—" cells have hover tooltip "Not reported by {ticker}".
- [ ] AC-20: Data freshness indicator shows date and fiscal years count below sub-tab bar.
- [ ] AC-21: Refresh button re-fetches financial data.
- [ ] AC-22: Only one popover visible at a time.
- [ ] AC-23: No regressions: existing financial table rendering, formatting, scrolling all preserved.

---

## FILES TOUCHED

**New files:**
- `frontend/src/pages/ModelBuilder/Historical/DataReadinessTab.tsx` — Data Readiness sub-tab
- `frontend/src/pages/ModelBuilder/Historical/DataReadinessTab.module.css` — coverage bar, engine cards, field rows, verdict badges

**Modified files:**
- `frontend/src/types/models.ts` — add DataReadinessResult and related interfaces
- `frontend/src/pages/ModelBuilder/Historical/HistoricalDataTab.tsx` — add 4th sub-tab, inspect toggle, glass-bubble rendering, popover, missing indicators, freshness indicator
- `frontend/src/pages/ModelBuilder/Historical/HistoricalDataTab.module.css` — inspect toggle, glass-bubble, popover, missing indicator dots, freshness text

---

## BUILDER PROMPT

> **Session 8C — Data Readiness Frontend + Diagnostic Overlay + Historical Polish**
>
> You are building session 8C of the Finance App v2.0 update.
>
> **What you're doing:** Building a "Data Readiness" sub-tab in Historical Data that shows per-engine readiness reports. Adding a diagnostic "Inspect" toggle overlay to financial tables with glass-bubble cell indicators and hover popovers. Adding blank cell tooltips and a data freshness indicator.
>
> **Context:** Session 8B built the backend `GET /api/v1/model-builder/{ticker}/data-readiness` endpoint that returns per-engine readiness analysis (verdict, field statuses, detection scores) and a `field_metadata` flat map for cell-level annotations. You're building the frontend that consumes this.
>
> **Existing code:**
> - `HistoricalDataTab.tsx` — located at `frontend/src/pages/ModelBuilder/Historical/HistoricalDataTab.tsx`. Has 3 sub-tabs (income/balance/cashflow) via `SUB_TAB_LABELS` array and `SubTab` union type. Fetches from `/api/v1/companies/{ticker}/financials?years=10`. Renders a transposed table with `LineItem[]` definitions for each sub-tab. Each `LineItem` has `label`, `key` (keyof FinancialRecord), `format`, and optional `separator`. Cells format values with `formatValue()` and apply `.missing` or `.negative` CSS classes.
> - `HistoricalDataTab.module.css` — sub-tab bar (pill style), table wrapper with sticky first column, alternating row colors, section separators, loading/error/empty states.
> - `types/models.ts` — has FootballFieldRow, ModelOverviewResult, SensitivityParameterDef, etc. You're adding DataReadinessResult interfaces here.
> - `displayNames.ts` — created in 8A at `frontend/src/utils/displayNames.ts`. Import `displayModelName` from `@/utils/displayNames`.
> - `api.ts` — `api.get<T>(path)` returns unwrapped data.
> - `modelStore` — `activeTicker` for current ticker.
>
> **Cross-cutting rules:**
> - Display Name Rule: All backend snake_case keys displayed in the UI must use the shared `displayNames.ts` utility. Never show raw keys. Never use inline `.replace(/_/g, ' ')`. Import from `@/utils/displayNames`.
> - Chart Quality: All charts must meet Fidelity/Yahoo Finance information-density standards.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%).
> - Scenario Order: Bear / Base / Bull (left to right), Base default.
>
> **Task 1: TypeScript Interfaces**
>
> In `frontend/src/types/models.ts`, add the following interfaces:
> ```typescript
> export interface FieldReadiness {
>   field: string;
>   label: string;
>   status: 'present' | 'missing' | 'derived';
>   years_available: number;
>   source: string | null;
>   reason: string;
> }
>
> export interface EngineReadiness {
>   verdict: 'ready' | 'partial' | 'not_possible';
>   verdict_label: string;
>   detection_score: number | null;
>   critical_fields: FieldReadiness[];
>   important_fields: FieldReadiness[];
>   helpful_fields: FieldReadiness[];
>   missing_impact: string | null;
>   notes: string[];
> }
>
> export interface FieldMetadataEntry {
>   status: 'present' | 'missing' | 'derived';
>   source: string | null;
>   source_detail: string | null;
>   years_available: number;
>   engines: { engine: string; level: string; reason: string }[];
> }
>
> export interface DetectionSummary {
>   recommended_model: string;
>   confidence: string;
>   confidence_percentage: number;
> }
>
> export interface DataReadinessResult {
>   ticker: string;
>   data_years_available: number;
>   total_fields: number;
>   populated_fields: number;
>   coverage_pct: number;
>   engines: Record<string, EngineReadiness>;
>   field_metadata: Record<string, FieldMetadataEntry>;
>   detection_result: DetectionSummary | null;
> }
> ```
>
> **Task 2: DataReadinessTab Component**
>
> Create `frontend/src/pages/ModelBuilder/Historical/DataReadinessTab.tsx`:
>
> Structure:
> - Fetch `api.get<DataReadinessResult>(`/api/v1/model-builder/${ticker}/data-readiness`)` when ticker changes
> - Coverage section: progress bar + stats text
> - Engine cards: iterate `Object.entries(result.engines)` → render card per engine with:
>   - Header: `displayModelName(engineKey)` + verdict badge
>   - Detection score
>   - Collapsible sections for critical/important/helpful fields
>   - Each field row: status icon (✓ green for present, ~ yellow for derived, ✗ red for missing), label, "{N} years", source text
>   - Missing impact note (indented, italic)
> - Collapse state: `useState<Set<string>>` — default: expand engines where verdict !== 'ready'
> - Loading: spinner. Error: message + retry. No ticker: placeholder.
>
> Create `DataReadinessTab.module.css`:
> - Coverage bar: 4px height, rounded, gradient fill
> - Engine cards: dark bg, subtle border, rounded, with header row (engine name left, badge right)
> - Verdict badges: `.badgeReady { background: rgba(34,197,94,0.15); color: var(--color-positive); }`, `.badgePartial { background: rgba(234,179,8,0.15); color: var(--color-warning); }`, `.badgeNotPossible { background: rgba(239,68,68,0.15); color: var(--color-negative); }`
> - Field rows: flex layout, icon + label + dots + years + source
> - Collapse toggle: small chevron icon that rotates
>
> **Task 3: Register 4th Sub-Tab**
>
> In `HistoricalDataTab.tsx`:
> - Add `'readiness'` to `SubTab` type
> - Add `{ key: 'readiness', label: 'Data Readiness' }` to `SUB_TAB_LABELS`
> - Render `<DataReadinessTab />` when `subTab === 'readiness'`
> - Wrap the existing table rendering in a condition: only show when subTab is income/balance/cashflow
>
> **Task 4: Inspect Toggle**
>
> In `HistoricalDataTab.tsx`:
> - Add `inspectMode` state (default false)
> - Add `readinessData` state (cached after first fetch)
> - When inspectMode toggles on and readinessData is null, fetch from data readiness endpoint
> - Render toggle in the sub-tab bar area (right-aligned), only when subTab !== 'readiness':
>   - Apple-style slider: 36×20px pill, smooth transition, accent color when on
>   - Label: "Inspect"
>
> **Task 5: Glass Bubble Cells (Inspect ON)**
>
> When `inspectMode && readinessData`:
> - For each data cell, check `readinessData.field_metadata[fieldKey]`
> - If status is 'present' or 'derived': add `styles.glassBubble` class
> - Glass bubble: subtle blue-tinted background, faint border, cursor pointer
> - On hover: show popover with field metadata (label, value, source, engine usage list)
> - Only one popover at a time; dismiss on mouse leave
> - Popover positioned near the cell using `getBoundingClientRect()`
>
> Note on field key mapping: the `LineItem.key` values (e.g. `operating_cash_flow`, `capital_expenditures`) may differ slightly from the `field_metadata` keys (which use `cache.financial_data` column names). Create a mapping object if needed: `const FIELD_KEY_MAP: Record<string, string> = { capital_expenditures: 'capital_expenditure', ... }`.
>
> **Task 6: Missing Cell Indicators (Inspect ON)**
>
> For missing cells when inspect mode is on:
> - Check if field appears in any engine's critical or important tier via `field_metadata.engines[]`
> - Critical: red dot (top-right corner of cell)
> - Important: amber dot
> - No engine dependency: no indicator
> - Hover shows impact popover (which engines are affected)
>
> **Task 7: Blank Cell Tooltip (Normal Mode)**
>
> For missing cells (value is null, displayed as "—"):
> - Add `title="Not reported by {ticker}"` attribute for native browser tooltip
> - This works in both inspect mode and normal mode
>
> **Task 8: Data Freshness Indicator**
>
> Below the sub-tab bar (when showing financial tables):
> - Text: "Data as of {most recent period_end_date} · {N} fiscal years"
> - Small refresh button (↻ icon or "Refresh" text) that re-fetches financials
> - Style: 11px, tertiary color, subtle
>
> **Acceptance criteria:**
> 1. DataReadinessResult TypeScript interfaces exist
> 2. "Data Readiness" is the 4th sub-tab in Historical Data
> 3. Coverage progress bar shows years + fields + percentage
> 4. 4 engine cards with color-coded verdict badges
> 5. Engine names use displayModelName()
> 6. Non-ready engines expanded, ready engines collapsed by default
> 7. Field rows show status icon, label, years, source
> 8. "Inspect" toggle in sub-tab bar, Apple-style slider
> 9. Inspect OFF: table unchanged
> 10. Inspect ON: populated cells get glass-bubble treatment
> 11. Glass-bubble hover shows popover with source + engine usage
> 12. Missing critical cells: red dot (inspect ON)
> 13. Missing important cells: amber dot (inspect ON)
> 14. Blank "—" cells have tooltip "Not reported by {ticker}"
> 15. Data freshness indicator with refresh button
> 16. Only one popover visible at a time
> 17. No regressions on existing table rendering
>
> **Files to create:**
> - `frontend/src/pages/ModelBuilder/Historical/DataReadinessTab.tsx`
> - `frontend/src/pages/ModelBuilder/Historical/DataReadinessTab.module.css`
>
> **Files to modify:**
> - `frontend/src/types/models.ts`
> - `frontend/src/pages/ModelBuilder/Historical/HistoricalDataTab.tsx`
> - `frontend/src/pages/ModelBuilder/Historical/HistoricalDataTab.module.css`
>
> **Technical constraints:**
> - CSS modules for all styling
> - CSS variables from design system
> - Import `displayModelName` from `@/utils/displayNames`
> - `api.get<T>(path)` for data fetching
> - `modelStore.activeTicker` for current ticker
> - Popover positioning: use `getBoundingClientRect()` + absolute positioning
> - No external tooltip libraries — custom implementation
> - Cache readiness data after first fetch (don't re-fetch on every toggle)
> - Glass bubble must not disrupt number readability (very subtle treatment)
> - The `FinancialRecord` type keys may differ slightly from `field_metadata` keys — build a mapping if needed
