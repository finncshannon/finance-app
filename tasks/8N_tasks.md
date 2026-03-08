# Session 8N — Tornado + Monte Carlo + Data Tables Frontend Upgrade
## Phase 8: Model Builder

**Priority:** Normal
**Type:** Frontend Only
**Depends On:** 8L (data table range params backend), 8M (slider state in modelStore for MC toggle)
**Spec Reference:** `specs/phase8_model_builder_sensitivity.md` → Areas 2, 3, 4

---

## SCOPE SUMMARY

Upgrade the Tornado chart to Fidelity-quality detail (value labels on bar endpoints, input range annotations, spread labels, rank numbers, base price reference line, summary bar). Add a "Use slider assumptions" toggle and parameter display section to Monte Carlo panel, plus histogram polish (median line, IQR shading). Add variable selector dropdowns, zoom/range inputs, grid size control, and preset buttons to the Data Tables panel.

---

## TASKS

### Task 1: Tornado Chart Upgrade
**Description:** Upgrade the existing Recharts horizontal diverging bar chart to Fidelity-quality with value labels, annotations, and a summary bar.

**Subtasks:**
- [ ] 1.1 — In `frontend/src/pages/ModelBuilder/Sensitivity/TornadoChart.tsx`, enrich `chartData` in the existing `useMemo` with additional fields for labels and annotations:
  ```tsx
  const chartData = useMemo<TornadoChartDatum[]>(() => {
    if (!data) return [];
    return data.bars.map((bar, idx) => ({
      name: `#${idx + 1} ${bar.variable_name}`,
      lowSpread: Math.min(bar.price_at_low_input - bar.base_price, bar.price_at_high_input - bar.base_price),
      highSpread: Math.max(bar.price_at_low_input - bar.base_price, bar.price_at_high_input - bar.base_price),
      priceAtLow: bar.price_at_low_input,
      priceAtHigh: bar.price_at_high_input,
      lowInput: bar.low_input,
      highInput: bar.high_input,
      basePrice: bar.base_price,
      rank: idx + 1,
      spread: bar.spread,
      spreadFmt: `$${bar.spread.toFixed(2)}`,
      priceAtLowFmt: `$${bar.price_at_low_input.toFixed(2)}`,
      priceAtHighFmt: `$${bar.price_at_high_input.toFixed(2)}`,
      inputRange: `${formatInputValue(bar.low_input, bar.variable_key)} – ${formatInputValue(bar.high_input, bar.variable_key)}`,
    }));
  }, [data]);
  ```
  Add a helper `formatInputValue(value, key)` that formats pct params as `X.X%` and absolute params as their raw value. Use the `VARIABLE_RANGES` heuristic: if value < 1, it's likely a pct → multiply by 100 and add %. Otherwise show as-is with appropriate suffix.

- [ ] 1.2 — Upgrade the base price `<ReferenceLine>` to be more prominent with a label:
  ```tsx
  <ReferenceLine
    x={0}
    stroke="#F5F5F5"
    strokeWidth={1.5}
    strokeDasharray="4 4"
    label={{
      value: `Base: $${data.base_price.toFixed(2)}`,
      fill: '#F5F5F5',
      fontSize: 10,
      position: 'top',
    }}
  />
  ```

- [ ] 1.3 — Add spread labels on the right side of each row. This can be rendered as a custom annotation layer after the chart, or via a custom `shape` on the Bar. Simplest approach: add a positioned element overlay or use a custom YAxis tick that includes the spread:
  ```tsx
  // Option: render spread labels as absolute-positioned divs next to chart
  <div className={styles.spreadLabels}>
    {chartData.map((d, i) => (
      <div key={i} className={styles.spreadLabel}>{d.spreadFmt}</div>
    ))}
  </div>
  ```
  Or render via a custom right-side annotation using Recharts customized label.

- [ ] 1.4 — Add a summary bar below the chart:
  ```tsx
  {chartData.length > 0 && (
    <div className={styles.summaryBar}>
      Most sensitive to <strong>{data.bars[0]?.variable_name}</strong> ({chartData[0]?.spreadFmt} spread)
      {' · '}
      Least sensitive to <strong>{data.bars[data.bars.length - 1]?.variable_name}</strong> ({chartData[chartData.length - 1]?.spreadFmt} spread)
    </div>
  )}
  ```

- [ ] 1.5 — Increase chart right margin from 40 to 80 for spread labels. Increase YAxis width from 140 to 180 for rank + name.

- [ ] 1.6 — Upgrade the `<Tooltip>` with a custom content component:
  ```tsx
  const TornadoTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    if (!d) return null;
    return (
      <div className={styles.tooltip}>
        <div className={styles.tooltipTitle}>{d.name}</div>
        <div className={styles.tooltipRow}><span>Low:</span><span>${d.priceAtLow.toFixed(2)}</span></div>
        <div className={styles.tooltipRow}><span>High:</span><span>${d.priceAtHigh.toFixed(2)}</span></div>
        <div className={styles.tooltipRow}><span>Spread:</span><span>{d.spreadFmt}</span></div>
        <div className={styles.tooltipRow}><span>Range:</span><span>{d.inputRange}</span></div>
      </div>
    );
  };
  ```
  Replace existing `<Tooltip>` with `<Tooltip content={<TornadoTooltip />} />`.

- [ ] 1.7 — In `TornadoChart.module.css`, add styles for summary bar, tooltip, and spread labels:
  ```css
  .summaryBar {
    padding: var(--space-2) var(--space-3);
    background: var(--bg-tertiary);
    border: 1px solid var(--border-subtle);
    border-radius: var(--radius-md);
    font-family: var(--font-sans);
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: var(--space-2);
  }
  .summaryBar strong { color: var(--text-primary); }
  .tooltip { /* same dark theme tooltip pattern */ }
  ```

---

### Task 2: Monte Carlo Panel Enhancements
**Description:** Add a "Use slider assumptions" toggle, a collapsible parameter display section, and histogram visual polish.

**Subtasks:**
- [ ] 2.1 — In `frontend/src/pages/ModelBuilder/Sensitivity/MonteCarloPanel.tsx`, add a toggle in the header to use slider overrides:
  ```tsx
  const sliderOverrides = useModelStore((s) => s.sliderOverrides);
  const [useSliders, setUseSliders] = useState(false);
  ```
  In the header next to the iteration selector:
  ```tsx
  <label className={styles.sliderToggle}>
    <input type="checkbox" checked={useSliders} onChange={(e) => setUseSliders(e.target.checked)} />
    <span>Use slider assumptions</span>
  </label>
  ```
  Update `fetchMC` to pass overrides when toggle is on:
  ```tsx
  api.post<MonteCarloResult>(url, {
    iterations: iters,
    ...(useSliders && Object.keys(sliderOverrides).length > 0 ? { overrides: sliderOverrides } : {}),
  })
  ```

- [ ] 2.2 — Add a collapsible "Simulation Parameters" section below the header. Fetch param defs on mount:
  ```tsx
  const [showParams, setShowParams] = useState(false);
  const [paramDefs, setParamDefs] = useState<SensitivityParameterDef[]>([]);

  useEffect(() => {
    if (!ticker) return;
    api.get<SensitivityParameterDef[]>(`/api/v1/model-builder/${ticker}/sensitivity/parameters`)
      .then(setParamDefs).catch(() => {});
  }, [ticker]);
  ```
  Render a toggle + table:
  ```tsx
  <button className={styles.paramToggle} onClick={() => setShowParams(!showParams)}>
    {showParams ? '▾' : '▸'} Simulation Parameters
  </button>
  {showParams && (
    <div className={styles.paramTable}>
      <div className={styles.paramHeader}><span>Variable</span><span>Base</span><span>Range</span></div>
      {paramDefs.map((p) => (
        <div key={p.key_path} className={styles.paramRow}>
          <span>{p.name}</span>
          <span>{formatParamValue(p.current_value ?? 0, p.display_format)}</span>
          <span>{formatParamValue(p.min_val, p.display_format)} – {formatParamValue(p.max_val, p.display_format)}</span>
        </div>
      ))}
    </div>
  )}
  ```
  Import/duplicate `formatParamValue` locally (same regex-based parser as 8M's SlidersPanel).

- [ ] 2.3 — Add a median price reference line to the histogram alongside the existing current price line:
  ```tsx
  {stats && (
    <ReferenceLine
      x={histogramData.reduce((closest, d) =>
        Math.abs(d.binMid - stats.median) < Math.abs(closest.binMid - stats.median) ? d : closest,
        histogramData[0]
      ).label}
      stroke="#F59E0B"
      strokeDasharray="4 4"
      strokeWidth={1}
      label={{ value: 'Median', position: 'top', fill: '#F59E0B', fontSize: 10 }}
    />
  )}
  ```

- [ ] 2.4 — Rename stats section subtitles to match spec groupings: "Key Statistics" → "Central Tendency", "Percentiles" → "Distribution", "Probabilities" → "Risk Assessment".

- [ ] 2.5 — In `MonteCarloPanel.module.css`, add styles for slider toggle, parameter table/toggle, updated section titles.

---

### Task 3: Data Tables Panel Upgrade
**Description:** Add variable selector dropdowns, zoom/range inputs, grid size selector, and preset buttons to the Data Tables panel.

**Subtasks:**
- [ ] 3.1 — In `frontend/src/pages/ModelBuilder/Sensitivity/DataTablePanel.tsx`, add state for controls:
  ```tsx
  const [rowVar, setRowVar] = useState<string | null>(null);
  const [colVar, setColVar] = useState<string | null>(null);
  const [rowMin, setRowMin] = useState<number | null>(null);
  const [rowMax, setRowMax] = useState<number | null>(null);
  const [colMin, setColMin] = useState<number | null>(null);
  const [colMax, setColMax] = useState<number | null>(null);
  const [gridSize, setGridSize] = useState(9);
  const [paramDefs, setParamDefs] = useState<SensitivityParameterDef[]>([]);
  ```
  Fetch parameter definitions on mount:
  ```tsx
  useEffect(() => {
    if (!ticker) return;
    api.get<SensitivityParameterDef[]>(`/api/v1/model-builder/${ticker}/sensitivity/parameters`)
      .then(setParamDefs).catch(() => {});
  }, [ticker]);
  ```

- [ ] 3.2 — Add variable selector dropdowns above the table. Filter out the opposite axis's variable from each dropdown to prevent same-variable selection:
  ```tsx
  <div className={styles.controls}>
    <div className={styles.controlRow}>
      <label>Row:</label>
      <select value={rowVar ?? ''} onChange={(e) => setRowVar(e.target.value || null)}>
        <option value="">Default (WACC)</option>
        {paramDefs.filter((p) => p.key_path !== colVar).map((p) => (
          <option key={p.key_path} value={p.key_path}>{p.name}</option>
        ))}
      </select>
    </div>
    <div className={styles.controlRow}>
      <label>Col:</label>
      <select value={colVar ?? ''} onChange={(e) => setColVar(e.target.value || null)}>
        <option value="">Default (Terminal Growth)</option>
        {paramDefs.filter((p) => p.key_path !== rowVar).map((p) => (
          <option key={p.key_path} value={p.key_path}>{p.name}</option>
        ))}
      </select>
    </div>
  </div>
  ```

- [ ] 3.3 — Add range inputs per axis for zoom. Values in display units for pct params (convert to decimals before API):
  ```tsx
  <div className={styles.rangeInputs}>
    <label>Row Range:</label>
    <input type="number" className={styles.rangeInput} value={rowMin ?? ''} placeholder="Min" onChange={...} />
    <span>to</span>
    <input type="number" className={styles.rangeInput} value={rowMax ?? ''} placeholder="Max" onChange={...} />
  </div>
  ```

- [ ] 3.4 — Add grid size selector:
  ```tsx
  <select className={styles.gridSelect} value={gridSize} onChange={(e) => setGridSize(Number(e.target.value))}>
    {[5, 7, 9, 11, 13].map((n) => (
      <option key={n} value={n}>{n}×{n}</option>
    ))}
  </select>
  ```

- [ ] 3.5 — Add preset buttons:
  ```tsx
  const PRESETS = [
    { label: 'WACC × Terminal Growth', row: 'scenarios.{s}.wacc', col: 'scenarios.{s}.terminal_growth_rate' },
    { label: 'WACC × Exit Multiple', row: 'scenarios.{s}.wacc', col: 'model_assumptions.dcf.terminal_exit_multiple' },
    { label: 'Rev Growth × Op Margin', row: 'scenarios.{s}.revenue_growth_rates[0]', col: 'scenarios.{s}.operating_margins[0]' },
  ];
  ```
  Render as buttons. On click: set `rowVar`/`colVar`, clear custom ranges, trigger re-fetch.

- [ ] 3.6 — Add a "Generate Table" button that sends all params to backend:
  ```tsx
  const fetchTable = useCallback(() => {
    if (!ticker) return;
    setLoading(true);
    api.post<Table2DResult>(`/api/v1/model-builder/${ticker}/sensitivity/table-2d`, {
      grid_size: gridSize,
      ...(rowVar ? { row_variable: rowVar } : {}),
      ...(colVar ? { col_variable: colVar } : {}),
      ...(rowMin != null && rowMax != null ? { row_min: rowMin, row_max: rowMax } : {}),
      ...(colMin != null && colMax != null ? { col_min: colMin, col_max: colMax } : {}),
    }).then((result) => { setData(result); setLoading(false); })
    .catch((err) => { setError(err.message); setLoading(false); });
  }, [ticker, gridSize, rowVar, colVar, rowMin, rowMax, colMin, colMax]);
  ```

- [ ] 3.7 — Enhance the base cell styling with a glow:
  ```css
  .cellBase {
    border: 2px solid var(--accent-primary) !important;
    box-shadow: 0 0 6px rgba(59, 130, 246, 0.3);
    font-weight: 700;
  }
  ```

- [ ] 3.8 — Add hover tooltip per cell with both variable values + price + upside:
  ```tsx
  title={`${data.row_variable}: ${formatHeaderValue(rv)}, ${data.col_variable}: ${formatHeaderValue(cv)} → ${formatCellValue(price)} (${formatUpside(upside)})`}
  ```

- [ ] 3.9 — In `DataTablePanel.module.css`, add styles for controls, selectors, range inputs, preset buttons, grid select.

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: Tornado Y-axis shows rank number (`#1`, `#2`...) next to variable names.
- [ ] AC-2: Tornado has labeled base price reference line (dashed white, dollar label at top).
- [ ] AC-3: Tornado has spread labels visible for each variable row.
- [ ] AC-4: Tornado has summary bar below chart showing most/least sensitive variables.
- [ ] AC-5: Tornado tooltip shows variable name, low/high prices, spread, and input range.
- [ ] AC-6: MC panel has "Use slider assumptions" toggle that passes `sliderOverrides` as overrides.
- [ ] AC-7: MC panel has collapsible "Simulation Parameters" section showing variable, base value, range.
- [ ] AC-8: MC histogram has median price reference line (amber dashed).
- [ ] AC-9: MC stats panel groups are labeled "Central Tendency", "Distribution", "Risk Assessment".
- [ ] AC-10: Data tables have variable selector dropdowns for row and column.
- [ ] AC-11: Can't select same variable for both row and column (filtered out of opposite dropdown).
- [ ] AC-12: Data tables have range min/max inputs for zoom.
- [ ] AC-13: Data tables have grid size selector (5, 7, 9, 11, 13).
- [ ] AC-14: Data tables have preset buttons for common variable pairs.
- [ ] AC-15: "Generate Table" button sends all params to backend correctly.
- [ ] AC-16: Base cell has prominent styling (accent border + glow).
- [ ] AC-17: Cells have hover tooltip showing both variable values + price + upside.
- [ ] AC-18: Charts meet Fidelity information-density standards.
- [ ] AC-19: No regressions on existing sensitivity functionality.

---

## FILES TOUCHED

**New files:**
- None

**Modified files:**
- `frontend/src/pages/ModelBuilder/Sensitivity/TornadoChart.tsx` — enriched chartData, rank in Y-axis labels, spread labels, summary bar, enhanced tooltip, increased margins
- `frontend/src/pages/ModelBuilder/Sensitivity/TornadoChart.module.css` — summary bar, tooltip, spread label, annotation styles
- `frontend/src/pages/ModelBuilder/Sensitivity/MonteCarloPanel.tsx` — slider override toggle, parameter display section, median reference line, stats group rename
- `frontend/src/pages/ModelBuilder/Sensitivity/MonteCarloPanel.module.css` — slider toggle, parameter table, updated section titles
- `frontend/src/pages/ModelBuilder/Sensitivity/DataTablePanel.tsx` — variable selectors, range inputs, grid size selector, presets, generate button, enhanced cell tooltip
- `frontend/src/pages/ModelBuilder/Sensitivity/DataTablePanel.module.css` — controls layout, selector styles, range inputs, preset buttons, enhanced base cell

---

## BUILDER PROMPT

> **Session 8N — Tornado + Monte Carlo + Data Tables Frontend Upgrade**
>
> You are building session 8N of the Finance App v2.0 update.
>
> **What you're doing:** Three sensitivity sub-panels upgraded: (1) Tornado chart to Fidelity-quality with rank numbers, spread labels, summary bar, enhanced tooltip, (2) Monte Carlo with slider override toggle, parameter display, median line, renamed stat groups, (3) Data Tables with variable selectors, zoom/range control, grid size selector, preset buttons.
>
> **Context:** Session 8L added backend range params for data tables (`row_min`, `row_max`, `col_min`, `col_max` on `POST /sensitivity/table-2d`). Session 8M put slider state in `modelStore.sliderOverrides`. All three panels already work — you're upgrading their information density and interactivity.
>
> **Existing code:**
>
> `TornadoChart.tsx` (at `frontend/src/pages/ModelBuilder/Sensitivity/TornadoChart.tsx`):
> - Fetches from `POST /sensitivity/tornado` on mount → `TornadoResult`
> - Transforms `data.bars[]` into `TornadoChartDatum[]` with `lowSpread`/`highSpread` (deviations from base for diverging bar)
> - Renders: header (title + base price + current price + compute time) → legend (Downside red / Upside green) → Recharts `BarChart` layout="vertical"
> - Chart: `XAxis type="number"` (dollar delta formatter `+$X`), `YAxis type="category" dataKey="name" width={140}`, `ReferenceLine x={0}` (white line at zero), two stacked `<Bar>` (`lowSpread` red, `highSpread` green) with `Cell` coloring
> - Basic `Tooltip` showing `$value` for each side
> - **Missing:** rank numbers in Y-axis, spread labels, summary bar, enhanced tooltip
> - `TornadoBar` type: `variable_name`, `variable_key`, `base_value`, `low_input`, `high_input`, `price_at_low_input`, `price_at_high_input`, `spread`, `base_price`
> - Bars are pre-sorted by spread (largest first) from backend
>
> `MonteCarloPanel.tsx` (at `frontend/src/pages/ModelBuilder/Sensitivity/MonteCarloPanel.tsx`):
> - State: `iterations` (default 10000), `data` (MonteCarloResult), `loading`, `error`
> - Fetches from `POST /sensitivity/monte-carlo` with `{ iterations }` — auto-runs on mount
> - Renders: header with iteration dropdown (1k/5k/10k/25k/50k) + Run button → histogram → stats panel → footer
> - Histogram: `BarChart` with bins, cells colored green (above current price) / red (below), `ReferenceLine` at current price (white dashed)
> - Stats panel: sections with dividers: "Key Statistics" (Mean/Median/StdDev/VaR), "Percentiles" (P5–P95), "Probabilities" (Prob Upside, 15%+, Downside 15%+)
> - **Missing:** slider override toggle, parameter display, median reference line
> - `MCStatistics`: mean, median, std_dev, p5/p10/p25/p50/p75/p90/p95, prob_upside, prob_upside_15pct, prob_downside_15pct, var_5pct
>
> `DataTablePanel.tsx` (at `frontend/src/pages/ModelBuilder/Sensitivity/DataTablePanel.tsx`):
> - Fetches from `POST /sensitivity/table-2d` with `{ grid_size: 9 }` on mount → `Table2DResult`
> - Renders: header → variable labels (static Row/Col) → table grid
> - Cell coloring via `colorClass()` mapping backend names to CSS (bright_green through bright_red)
> - Base cell: `.cellBase` class
> - **Missing:** variable selector dropdowns, range inputs, grid size selector, presets, enhanced tooltips
> - Currently hardcodes `grid_size: 9`, no `row_variable`/`col_variable` in request
>
> **Cross-cutting rules:**
> - Display Name Rule: Use `displayNames.ts` for any backend keys. Tornado variable names come pre-formatted from backend.
> - Chart Quality: Fidelity/Yahoo Finance standards: value labels, proper tooltips, reference lines, compact formatting.
> - Data Format: All ratios/percentages as decimal ratios (0.15 = 15%).
> - Scenario Order: Bear / Base / Bull, Base default.
>
> **Task 1: Tornado Upgrade**
> - Enrich chartData: add rank, spread, formatted prices, input range
> - Y-axis shows `#1 WACC`, `#2 Terminal Growth`, etc.
> - Base price ReferenceLine: dashed white, labeled
> - Spread labels on right side of each row
> - Summary bar: "Most sensitive to WACC ($27.20) · Least sensitive to NWC ($3.10)"
> - Enhanced tooltip: name, low/high prices, spread, input range
> - Margins: right 40→80, YAxis 140→180
>
> **Task 2: MC Enhancements**
> - Toggle: "Use slider assumptions" — passes `modelStore.sliderOverrides` as overrides
> - Collapsible param display: Variable / Base Value / Range table from param defs
> - Median reference line (amber dashed) alongside current price line
> - Rename stat sections: "Central Tendency", "Distribution", "Risk Assessment"
>
> **Task 3: Data Tables Upgrade**
> - Fetch param defs for dropdowns
> - Row/col variable selectors (filter opposite to prevent same-variable)
> - Range min/max inputs per axis (convert display→decimal before API)
> - Grid size: 5/7/9/11/13 dropdown
> - Presets: WACC×TG, WACC×Exit, RevGrowth×OpMargin
> - "Generate Table" button sends all params
> - Base cell: accent border + glow
> - Cell tooltip: both variables + price + upside
>
> **Acceptance criteria:**
> 1. Tornado: rank numbers, spread labels, summary bar, enhanced tooltip, base line
> 2. MC: slider toggle, param display, median line, renamed groups
> 3. Data tables: selectors, range zoom, grid size, presets, generate button, base glow, tooltips
> 4. No regressions
>
> **Files to create:** None
> **Files to modify:** `TornadoChart.tsx/css`, `MonteCarloPanel.tsx/css`, `DataTablePanel.tsx/css`
>
> **Technical constraints:**
> - Recharts for charting (already loaded)
> - CSS modules for styling
> - `api.get<T>` / `api.post<T>` for fetching
> - `useModelStore` for `sliderOverrides` (Zustand)
> - `SensitivityParameterDef` from `'../../../types/models'`
> - Backend key_paths for presets: `scenarios.{s}.wacc`, `scenarios.{s}.terminal_growth_rate`, `model_assumptions.dcf.terminal_exit_multiple`, `scenarios.{s}.revenue_growth_rates[0]`, `scenarios.{s}.operating_margins[0]`
> - Range inputs: convert display units → decimal before API
> - Tornado bars sorted by spread (largest first) from backend — rank = array index + 1
