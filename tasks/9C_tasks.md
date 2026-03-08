# Session 9C — Scanner Frontend (Universe Selector, Filter UX, Dynamic Columns, Table Polish)
## Phase 9: Scanner

**Priority:** Normal
**Type:** Frontend Only
**Depends On:** 9A (universe options for selector), 9B (hydrated data for meaningful results)
**Spec Reference:** `specs/phase9_scanner.md` → Areas 1D frontend, 2, 3, 4

---

## SCOPE SUMMARY

Add a universe selector dropdown (All / S&P 500 / DOW 30 / Russell 3000) to the filter panel. Improve filter UX: widen the metric picker, auto-format filter values with %, x, $ suffixes based on metric type, and show active filters as summary tags above results. Implement dynamic results columns that auto-add filtered metrics to the table. Polish the results table: consistent formatting, negative value highlighting, and improved scan summary.

---

## TASKS

### Task 1: Universe Selector in Filter Panel
**Description:** Add a universe dropdown in the FilterPanel so users can scope scans to DOW, S&P 500, R3000, or All.

**Subtasks:**
- [ ] 1.1 — In `frontend/src/pages/Scanner/FilterPanel/FilterPanel.tsx`, add a universe selector section at the top of the panel (before Presets):
  ```tsx
  <div className={styles.section}>
    <div className={styles.sectionLabel}>Universe</div>
    <select
      className={styles.universeSelect}
      value={universe}
      onChange={(e) => onUniverseChange(e.target.value)}
    >
      <option value="all">All Companies</option>
      <option value="dow">DOW 30</option>
      <option value="sp500">S&P 500</option>
      <option value="r3000">Russell 3000</option>
    </select>
  </div>
  ```
- [ ] 1.2 — Add `universe` and `onUniverseChange` to `FilterPanelProps`:
  ```typescript
  interface FilterPanelProps {
    // ... existing props
    universe: string;
    onUniverseChange: (universe: string) => void;
  }
  ```
- [ ] 1.3 — In `ScannerPage.tsx`, pass `universe` and `setUniverse` to `FilterPanel`:
  ```tsx
  <FilterPanel
    {...existingProps}
    universe={universe}
    onUniverseChange={setUniverse}
  />
  ```
- [ ] 1.4 — In `FilterPanel.module.css`, style the universe selector:
  ```css
  .universeSelect {
    width: 100%;
    padding: 6px 8px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    color: var(--text-primary);
    font-size: 12px;
    cursor: pointer;
  }
  ```

---

### Task 2: Wider Metric Picker with Category Labels
**Description:** Increase the MetricPicker dropdown width so metric labels aren't truncated. Ensure category headers render clearly as group labels.

**Subtasks:**
- [ ] 2.1 — In `frontend/src/pages/Scanner/FilterPanel/MetricPicker.module.css`, increase the trigger button and dropdown width:
  ```css
  .trigger {
    /* Existing styles... */
    min-width: 180px;  /* was smaller, increase for full labels */
  }
  .dropdown {
    /* Existing styles... */
    min-width: 260px;  /* wider to show full metric names + format badges */
    max-height: 360px;
  }
  ```
- [ ] 2.2 — In `MetricPicker.tsx`, ensure the category header includes the category name prominently and items show full labels. The current code already has `.categoryHeader` and `.item` — just verify they render clearly. Add a subtle count to each category header:
  ```tsx
  <div className={styles.categoryHeader}>
    {category} <span className={styles.categoryCount}>({items.length})</span>
  </div>
  ```
- [ ] 2.3 — In `MetricPicker.module.css`, add `.categoryCount`:
  ```css
  .categoryCount {
    font-weight: 400;
    color: var(--text-tertiary);
    margin-left: 4px;
  }
  ```

---

### Task 3: Auto-Formatted Filter Values
**Description:** When a metric is selected in a filter, the value input should auto-format based on the metric's `format` field: percent metrics show `%` suffix, ratio metrics show `x`, currency shows `$`. The user types display values (e.g., `15` for 15%) and the system converts to internal values (0.15) at the boundary.

**Subtasks:**
- [ ] 3.1 — In `frontend/src/pages/Scanner/FilterPanel/FilterRow.tsx`, look up the selected metric's format:
  ```tsx
  const selectedMetric = metrics.find((m) => m.key === filter.metric);
  const metricFormat = selectedMetric?.format ?? 'number';
  ```
- [ ] 3.2 — Add conversion helpers (or import from `types.ts`):
  ```typescript
  function toDisplayValue(internal: number | null, format: string): string {
    if (internal == null) return '';
    if (format === 'percent') return (internal * 100).toFixed(1);
    return String(internal);
  }

  function fromDisplayValue(display: string, format: string): number | null {
    if (display === '') return null;
    const num = parseFloat(display);
    if (isNaN(num)) return null;
    if (format === 'percent') return num / 100;
    return num;
  }
  ```
- [ ] 3.3 — Update the value inputs to use display values and convert on change:
  ```tsx
  // For standard operators (gt, lt, etc.):
  <div className={styles.valueGroup}>
    {metricFormat === 'currency' && <span className={styles.valueSuffix}>$</span>}
    <input
      className={styles.valueInput}
      type="number"
      value={toDisplayValue(filter.value, metricFormat)}
      onChange={(e) => onChange({ ...filter, value: fromDisplayValue(e.target.value, metricFormat) })}
      placeholder={metricFormat === 'percent' ? '15' : metricFormat === 'ratio' ? '12.0' : 'Value'}
    />
    {metricFormat === 'percent' && <span className={styles.valueSuffix}>%</span>}
    {metricFormat === 'ratio' && <span className={styles.valueSuffix}>x</span>}
  </div>
  ```
- [ ] 3.4 — Apply the same conversion to "between" inputs (low and high):
  ```tsx
  <input value={toDisplayValue(filter.low, metricFormat)} onChange={(e) => onChange({ ...filter, low: fromDisplayValue(e.target.value, metricFormat) })} />
  <input value={toDisplayValue(filter.high, metricFormat)} onChange={(e) => onChange({ ...filter, high: fromDisplayValue(e.target.value, metricFormat) })} />
  ```
- [ ] 3.5 — In `FilterRow.module.css`, add styles for the suffix badges:
  ```css
  .valueGroup {
    display: flex;
    align-items: center;
    gap: 2px;
  }
  .valueSuffix {
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--text-tertiary);
    min-width: 12px;
  }
  ```
- [ ] 3.6 — Add a tooltip to the value input explaining the format: `title="Enter 15 for 15%"` for percent metrics.

---

### Task 4: Filter Summary Tags
**Description:** Show active filters as compact summary tags above the results table for quick visibility.

**Subtasks:**
- [ ] 4.1 — In `frontend/src/pages/Scanner/ResultsTable/ResultsHeader.tsx`, accept a new `filters` prop and `metricsMap`:
  ```typescript
  interface ResultsHeaderProps {
    // ... existing
    activeFilters?: ScannerFilter[];
  }
  ```
- [ ] 4.2 — Render filter tags above the stats text:
  ```tsx
  {activeFilters && activeFilters.length > 0 && (
    <div className={styles.filterTags}>
      {activeFilters.map((f, i) => {
        const metric = metricsMap.get(f.metric);
        if (!metric) return null;
        const label = buildFilterLabel(metric, f);
        return (
          <span key={i} className={styles.filterTag}>{label}</span>
        );
      })}
    </div>
  )}
  ```
- [ ] 4.3 — Add `buildFilterLabel` helper that formats each tag:
  ```typescript
  function buildFilterLabel(metric: MetricDefinition, f: ScannerFilter): string {
    const name = metric.label;
    const fmtVal = (v: number | null) => formatMetricValue(v, metric.format);
    switch (f.operator) {
      case 'gt': return `${name} > ${fmtVal(f.value)}`;
      case 'gte': return `${name} ≥ ${fmtVal(f.value)}`;
      case 'lt': return `${name} < ${fmtVal(f.value)}`;
      case 'lte': return `${name} ≤ ${fmtVal(f.value)}`;
      case 'eq': return `${name} = ${fmtVal(f.value)}`;
      case 'between': return `${name}: ${fmtVal(f.low)} – ${fmtVal(f.high)}`;
      case 'top_pct': return `${name}: Top ${f.percentile}%`;
      case 'bot_pct': return `${name}: Bottom ${f.percentile}%`;
      default: return name;
    }
  }
  ```
  Import `formatMetricValue` from `../types`.
- [ ] 4.4 — In `ScannerPage.tsx`, pass filters to `ResultsHeader` (via `ResultsTable` or directly).
- [ ] 4.5 — In `ResultsTable.module.css`, add filter tag styles:
  ```css
  .filterTags {
    display: flex;
    flex-wrap: wrap;
    gap: var(--space-1);
    margin-bottom: var(--space-2);
  }
  .filterTag {
    padding: 2px 8px;
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid rgba(59, 130, 246, 0.2);
    border-radius: var(--radius-sm);
    font-family: var(--font-sans);
    font-size: 11px;
    color: var(--accent-primary);
    white-space: nowrap;
  }
  ```

---

### Task 5: Dynamic Results Columns
**Description:** When a filter is applied for a metric not in the default columns, that metric auto-appears as a column. The last 3 columns are "variable" — they fill with active filter metrics. Manual column selector overrides auto-detection.

**Subtasks:**
- [ ] 5.1 — In `frontend/src/pages/Scanner/ScannerPage.tsx`, compute `effectiveColumns` based on filters + defaults:
  ```tsx
  const [manualColumns, setManualColumns] = useState<string[] | null>(null);

  const effectiveColumns = useMemo(() => {
    // If user manually configured columns, use those (override auto-detection)
    if (manualColumns) return manualColumns;

    const FIXED = ['current_price', 'market_cap']; // always shown
    const DEFAULT_VARIABLE = ['pe_trailing', 'ev_to_ebitda', 'roe', 'revenue_growth', 'dividend_yield'];
    const MAX_VARIABLE = 5;

    // Collect unique filter metrics not in fixed columns
    const filterMetrics = filters
      .map((f) => f.metric)
      .filter((m) => m && !FIXED.includes(m));
    const uniqueFilterMetrics = [...new Set(filterMetrics)];

    // Build variable columns: filter metrics first, then defaults to fill
    const variable: string[] = [];
    for (const m of uniqueFilterMetrics) {
      if (!variable.includes(m) && variable.length < MAX_VARIABLE) variable.push(m);
    }
    for (const m of DEFAULT_VARIABLE) {
      if (!variable.includes(m) && !FIXED.includes(m) && variable.length < MAX_VARIABLE) variable.push(m);
    }

    return [...FIXED, ...variable];
  }, [filters, manualColumns]);
  ```

- [ ] 5.2 — Pass `effectiveColumns` to `ResultsTable` instead of using `DEFAULT_COLUMNS` internally:
  ```tsx
  <ResultsTable
    {...existingProps}
    columns={effectiveColumns}
    onColumnsChange={(cols) => setManualColumns(cols)}
  />
  ```

- [ ] 5.3 — In `ResultsTable.tsx`, accept `columns` and `onColumnsChange` props instead of managing `visibleColumns` with local state:
  ```typescript
  interface ResultsTableProps {
    // ... existing
    columns: string[];
    onColumnsChange: (cols: string[]) => void;
  }
  ```
  Replace `const [visibleColumns, setVisibleColumns] = useState(DEFAULT_COLUMNS)` with the props.

- [ ] 5.4 — In `ResultsHeader.tsx`, update the column selector to call `onColumnsChange` which sets `manualColumns` in ScannerPage (locking the columns to manual mode).

---

### Task 6: Results Table Polish
**Description:** Ensure consistent number formatting, add negative value highlighting, and improve the scan summary text.

**Subtasks:**
- [ ] 6.1 — In `ResultsTable.tsx`, verify all metric cells use `formatMetricValue(value, metric.format)` from `types.ts`. The current code should already do this — audit for any raw `.toFixed()` or unformatted values.

- [ ] 6.2 — Add negative value highlighting: in the cell rendering, check if value < 0 and add a CSS class:
  ```tsx
  <td className={`${styles.cell} ${val != null && val < 0 ? styles.cellNegative : ''}`}>
    {formatMetricValue(val, metricDef?.format ?? 'number')}
  </td>
  ```
  In `ResultsTable.module.css`:
  ```css
  .cellNegative {
    color: var(--color-negative);
  }
  ```

- [ ] 6.3 — In `ResultsHeader.tsx`, improve the summary text to show universe name and scan details:
  ```tsx
  <div className={styles.statsText}>
    Showing {startRow}–{endRow} of {totalMatches.toLocaleString()} matches
    {universeName && <> from {universeName}</>}
    {' '}({universeSize.toLocaleString()} scanned)
    <span className={styles.statSep}>&middot;</span>
    {appliedFilters} filter{appliedFilters !== 1 ? 's' : ''}
    <span className={styles.statSep}>&middot;</span>
    {computationTimeMs}ms
  </div>
  ```
  Accept `page` and `pageSize` props to compute startRow/endRow, and `universeName` (mapped from universe value).

- [ ] 6.4 — In `DetailPanel.tsx`, verify formatting uses `formatMetricValue` consistently for all displayed metrics.

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: Universe selector dropdown in FilterPanel with options: All, DOW 30, S&P 500, Russell 3000.
- [ ] AC-2: Selecting a universe scopes the scan (passes `universe` param to backend).
- [ ] AC-3: MetricPicker dropdown is wider (min-width 260px), shows full metric labels without truncation.
- [ ] AC-4: Category headers show category name with item count.
- [ ] AC-5: Filter value inputs for percent metrics show `%` suffix and accept display values (15 → 0.15 internally).
- [ ] AC-6: Filter value inputs for ratio metrics show `x` suffix.
- [ ] AC-7: Filter value inputs for currency metrics show `$` prefix.
- [ ] AC-8: "Between" filter inputs both use the same format conversion.
- [ ] AC-9: Active filters shown as summary tags above results: `[P/E < 20x] [Market Cap > $10B]`.
- [ ] AC-10: Filter metrics not in default columns auto-appear as dynamic columns.
- [ ] AC-11: Maximum 5 variable columns (filter metrics fill first, then defaults).
- [ ] AC-12: Manual column selector overrides auto-detection (sets `manualColumns` locking behavior).
- [ ] AC-13: When filters are cleared, variable columns revert to defaults.
- [ ] AC-14: All metric values in the table use `formatMetricValue` (%, x, $, compact currency).
- [ ] AC-15: Negative values highlighted with `var(--color-negative)` red color.
- [ ] AC-16: Results summary shows: "Showing 1–100 of 342 matches from S&P 500 (503 scanned) · 3 filters · 245ms".
- [ ] AC-17: No regressions on existing scanner functionality (presets, text search, sorting, pagination, export).

---

## FILES TOUCHED

**New files:**
- None

**Modified files:**
- `frontend/src/pages/Scanner/FilterPanel/FilterPanel.tsx` — add universe selector section, accept universe/onUniverseChange props
- `frontend/src/pages/Scanner/FilterPanel/FilterPanel.module.css` — universe selector styles
- `frontend/src/pages/Scanner/FilterPanel/FilterRow.tsx` — auto-format value inputs with suffix, toDisplayValue/fromDisplayValue conversion
- `frontend/src/pages/Scanner/FilterPanel/FilterRow.module.css` — value group + suffix styles
- `frontend/src/pages/Scanner/FilterPanel/MetricPicker.tsx` — category count annotation
- `frontend/src/pages/Scanner/FilterPanel/MetricPicker.module.css` — wider trigger + dropdown, category count
- `frontend/src/pages/Scanner/ScannerPage.tsx` — pass universe to FilterPanel, compute effectiveColumns from filters, pass to ResultsTable, manualColumns state
- `frontend/src/pages/Scanner/ResultsTable/ResultsTable.tsx` — accept columns/onColumnsChange props, negative value highlighting, formatting audit
- `frontend/src/pages/Scanner/ResultsTable/ResultsTable.module.css` — cellNegative class, filterTags styles
- `frontend/src/pages/Scanner/ResultsTable/ResultsHeader.tsx` — filter summary tags, improved stats text with universe name + page range
- `frontend/src/pages/Scanner/ResultsTable/DetailPanel.tsx` — formatting consistency audit
- `frontend/src/pages/Scanner/types.ts` — add toDisplayValue/fromDisplayValue helpers (or keep in FilterRow)

---

## BUILDER PROMPT

> **Session 9C — Scanner Frontend (Universe Selector, Filter UX, Dynamic Columns, Table Polish)**
>
> You are building session 9C of the Finance App v2.0 update.
>
> **What you're doing:** Four improvements to the Scanner frontend: (1) Universe selector dropdown, (2) Wider metric picker + auto-formatted filter values, (3) Dynamic results columns that react to active filters, (4) Table polish — consistent formatting, negative highlighting, improved summary.
>
> **Context:** Session 9A created curated universe data (DOW, S&P 500, R3000) and the backend filters by `universe_tags`. Session 9B is hydrating data in the background. The frontend needs to let users pick a universe, show properly formatted filter values, auto-show filtered metrics as table columns, and format all numbers consistently.
>
> **Existing code:**
>
> `ScannerPage.tsx` (at `frontend/src/pages/Scanner/ScannerPage.tsx`):
> - State: `filters` (ScannerFilter[]), `textQuery`, `formTypes`, `sectorFilter`, `universe` (default "all"), `sortBy`, `sortDesc`, `page`, `results`, `loading`, `scanError`, `universeStats`, `showSaveModal`, `presetName`
> - `runScan()` posts to `/api/v1/scanner/screen` with all filter state including `universe`
> - Auto-scans on filter change via debounced `useEffect` (500ms)
> - Passes `metricsMap` (Map of key → MetricDefinition) to `ResultsTable`
> - Does NOT currently compute dynamic columns — `ResultsTable` manages its own `visibleColumns` via `useState(DEFAULT_COLUMNS)`
>
> `FilterPanel.tsx` (at `frontend/src/pages/Scanner/FilterPanel/FilterPanel.tsx`):
> - Props: metrics, categories, presets, filters, textQuery, formTypes, onFiltersChange, onTextQueryChange, onFormTypesChange, onSelectPreset, onDeletePreset, onClear, onSave
> - Sections: Presets → Filters (FilterRow per filter + Add Filter button) → Filing Search → Actions (Clear All / Save Preset)
> - Does NOT currently have a universe selector
>
> `FilterRow.tsx` (at `frontend/src/pages/Scanner/FilterPanel/FilterRow.tsx`):
> - Props: filter (ScannerFilter), metrics, categories, onChange, onRemove
> - Renders: MetricPicker → operator dropdown → value input(s) → remove button
> - Value inputs are raw `<input type="number">` — no format suffix, user types raw decimals (0.15 for 15%)
> - "between" operator shows two inputs (low, high)
> - "top_pct/bot_pct" shows percentile input
>
> `MetricPicker.tsx` (at `frontend/src/pages/Scanner/FilterPanel/MetricPicker.tsx`):
> - Renders: trigger button (shows selected label) → dropdown with search + category-grouped items
> - Each item shows label + optional format badge (%, $, x via `FORMAT_BADGES`)
> - Categories come from `categories` prop: `Record<string, string[]>` (category name → metric key list)
> - Current dropdown width may be constrained — metric labels truncate
>
> `ResultsTable.tsx` (at `frontend/src/pages/Scanner/ResultsTable/ResultsTable.tsx`):
> - Props: results, loading, metricsMap, sortBy, sortDesc, onSort, page, pageSize, onPageChange
> - Local state: `visibleColumns` (useState(DEFAULT_COLUMNS)), `expandedTicker`, `contextMenu`, `textHitsOpen`
> - Uses `formatMetricValue(value, format)` from `types.ts` for cell rendering
> - `DEFAULT_COLUMNS` from `types.ts`: `['current_price', 'market_cap', 'pe_trailing', 'ev_to_ebitda', 'roe', 'revenue_growth', 'dividend_yield']`
>
> `ResultsHeader.tsx`:
> - Props: totalMatches, computationTimeMs, universeSize, appliedFilters, visibleColumns, metricsMap, onColumnsChange
> - Shows: "{N} matches · {ms}ms · Universe: {N} · {N} filters"
> - Has a column config dropdown with checkboxes per metric
>
> `types.ts` (at `frontend/src/pages/Scanner/types.ts`):
> - `MetricDefinition`: key, label, category, format, description
> - `formatMetricValue(value, format)`: handles "currency" (T/B/M/K), "percent" (×100 + %), "ratio" (+ x), "integer"
> - `DEFAULT_COLUMNS`: `['current_price', 'market_cap', 'pe_trailing', 'ev_to_ebitda', 'roe', 'revenue_growth', 'dividend_yield']`
> - `ScannerFilter`: metric, operator, value, low, high, values, percentile
>
> **Cross-cutting rules:**
> - Display Name Rule: Use `displayNames.ts` for any backend keys shown in UI.
> - Chart Quality: All charts/tables must meet Fidelity/Yahoo Finance information-density standards.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%). Frontend displays as percent.
> - Scenario Order: Bear / Base / Bull, Base default.
>
> **Task 1: Universe Selector**
> - Add to FilterPanel as first section (before Presets)
> - `<select>` with options: All, DOW 30, S&P 500, R3000
> - New props: `universe: string`, `onUniverseChange: (u: string) => void`
> - ScannerPage passes `universe` / `setUniverse`
>
> **Task 2: Wider Metric Picker**
> - MetricPicker.module.css: trigger min-width 180px, dropdown min-width 260px
> - Add category count to headers: `{category} ({items.length})`
>
> **Task 3: Auto-Format Filter Values**
> - In FilterRow, look up `selectedMetric.format`
> - Add `toDisplayValue(internal, format)` / `fromDisplayValue(display, format)`: percent → ×100/÷100
> - Show suffix badges: `%` for percent, `x` for ratio, `$` for currency
> - Apply to all value inputs including between low/high
> - Tooltip: `title="Enter 15 for 15%"` for percent metrics
>
> **Task 4: Filter Summary Tags**
> - In ResultsHeader, accept `activeFilters` prop
> - Render tags: `[P/E < 20x] [Market Cap > $10B] [Revenue Growth > 15%]`
> - `buildFilterLabel(metric, filter)` formats each tag using operator + formatted value
>
> **Task 5: Dynamic Columns**
> - In ScannerPage, compute `effectiveColumns` from filters + defaults
> - Fixed columns: current_price, market_cap (always shown)
> - Variable columns (max 5): filter metrics first, then default fill
> - Manual column selector overrides auto-detection via `manualColumns` state
> - Pass `columns` + `onColumnsChange` props to ResultsTable (replaces internal visibleColumns state)
>
> **Task 6: Table Polish**
> - Verify all cells use `formatMetricValue`
> - Negative values: `.cellNegative { color: var(--color-negative) }`
> - Summary: "Showing 1–100 of 342 matches from S&P 500 (503 scanned) · 3 filters · 245ms"
>
> **Acceptance criteria:**
> 1. Universe selector works, scopes scans
> 2. Metric picker wider, labels not truncated
> 3. Filter values auto-formatted with suffixes
> 4. Filter tags shown above results
> 5. Dynamic columns react to filters
> 6. Manual column override locks columns
> 7. Consistent formatting across table
> 8. Negative values red
> 9. Improved summary text
> 10. No regressions
>
> **Files to create:** None
> **Files to modify:** FilterPanel.tsx/css, FilterRow.tsx/css, MetricPicker.tsx/css, ScannerPage.tsx, ResultsTable.tsx/css, ResultsHeader.tsx, DetailPanel.tsx, types.ts
>
> **Technical constraints:**
> - CSS modules for all styling
> - `formatMetricValue` from `types.ts` for consistent formatting
> - `MetricDefinition.format` values: "currency", "percent", "ratio", "integer", "number"
> - Percent conversion: display `15` → internal `0.15`. Only for `format === "percent"`.
> - `api.post<ScannerResult>('/api/v1/scanner/screen', { ...filters, universe })` — universe already in the request
> - Dynamic columns: `useMemo` based on `filters` dependency. `manualColumns` state (`null` = auto, `string[]` = manual override).
> - The column selector in ResultsHeader already exists — just wire it to set `manualColumns` instead of local state.
