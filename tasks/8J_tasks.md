# Session 8J — DDM & Revenue-Based Detail Upgrade
## Phase 8: Model Builder

**Priority:** Normal
**Type:** Frontend Only
**Depends On:** 8A (displayNames.ts), 8I (scenario reorder + underscore fixes already applied)
**Spec Reference:** `specs/phase8_model_builder_model.md` → Area 5

---

## SCOPE SUMMARY

Bring DDM and Revenue-Based model views closer to DCF's level of detail. For DDM: add a dividend growth trajectory chart (Recharts), a value waterfall bar chart, an expanded key outputs panel, and richer sustainability metrics with progress bars and tooltips. For Revenue-Based: add a revenue growth trajectory chart, a multiple compression/expansion chart, an expanded key outputs panel, and an upgraded scenario comparison with a table + mini football field.

---

## TASKS

### Task 1: DDM — Dividend Growth Trajectory Chart
**Description:** Add a Recharts line chart showing projected DPS over the multi-stage horizon, color-coded by stage.

**Subtasks:**
- [ ] 1.1 — In `frontend/src/pages/ModelBuilder/Models/DDMView.tsx`, add a new section after the ResultsCard:
  - Chart type: `LineChart` from Recharts with `XAxis` (years), `YAxis` (DPS in $)
  - Data: map `scenario.dividend_schedule` to `{year, dps, stage}`
  - Color-code by stage: high_growth = `#3B82F6` (blue), transition = `#F59E0B` (yellow), terminal = `#22C55E` (green)
  - Implementation: since Recharts can't easily color-code segments of a single line, use multiple `<Line>` components or `<Area>` with different fills per stage. Simplest approach: use a single Line with custom dot colors based on stage.
  - Alternative: render 3 separate Lines (one per stage), each with only their stage's data points + connecting gaps
- [ ] 1.2 — Add proper chart formatting:
  - Y-axis: `$X.XX` format
  - X-axis: year numbers
  - Tooltip: shows Year, DPS ($), Growth Rate (%), Stage name (using `displayStageName()`)
  - Legend: Stage colors with labels (High Growth, Transition, Terminal)
  - Grid lines: subtle
  - Chart title: "Dividend Growth Trajectory"
- [ ] 1.3 — Chart should be responsive and match the dark theme (dark background, light text, subtle grid)

**Implementation Notes:**
- Recharts is already imported and used by DCFView for the waterfall chart.
- The `dividend_schedule` array has: `{year, stage, dps, growth_rate, discount_factor, pv}` per row.
- Use `displayStageName()` from `@/utils/displayNames` for legend and tooltip labels.
- Chart height: ~250px. Full width.

---

### Task 2: DDM — Value Waterfall Chart
**Description:** Add a stepped bar chart showing the DDM value decomposition: PV Stage 1 → PV Stage 2 → PV Terminal → Total Intrinsic Value.

**Subtasks:**
- [ ] 2.1 — Add a Recharts `BarChart` (waterfall-style) below the trajectory chart:
  - Bars: PV Stage 1, PV Stage 2 (if exists), PV Terminal
  - Final bar: Total (sum) as a different color
  - Each bar labeled with dollar value
  - Percentage annotation: show each component's % of total (e.g., "38%" on PV Terminal)
- [ ] 2.2 — Waterfall implementation: use stacked bars where each step builds on the previous total. The "invisible" base bar creates the waterfall effect.
  - Step 1: PV Stage 1 (base=0, height=PV1)
  - Step 2: PV Stage 2 (base=PV1, height=PV2) — if exists
  - Step 3: PV Terminal (base=PV1+PV2, height=PVT)
  - Step 4: Total (base=0, height=total) — full bar as summary
- [ ] 2.3 — Colors: Stage 1 blue, Stage 2 yellow, Terminal green, Total accent-primary. Match the trajectory chart colors for consistency.
- [ ] 2.4 — Tooltip: show component name, dollar value, % of total.
- [ ] 2.5 — Chart height: ~200px. Full width. Dark theme styling.

**Implementation Notes:**
- Data from `scenario.pv_stage1`, `scenario.pv_stage2`, `scenario.pv_terminal`.
- Total = `scenario.pv_stage1 + (scenario.pv_stage2 ?? 0) + scenario.pv_terminal`.
- Waterfall pattern with Recharts: use a stacked BarChart with an invisible base series. This is a well-documented Recharts pattern.

---

### Task 3: DDM — Expanded Key Outputs Panel
**Description:** Replace the sparse 4-number Value Decomposition grid with a proper key outputs panel matching DCF's format.

**Subtasks:**
- [ ] 3.1 — Replace the current `.decomposition` section with a new key outputs panel:
  - Top row: 3 large-format cards:
    - **Intrinsic Value**: `$XX.XX` (the scenario's `intrinsic_value_per_share`)
    - **Current Dividend Yield**: computed from `scenario.dividend_schedule[0].dps / result.current_price`
    - **Implied Dividend Yield**: computed from `scenario.dividend_schedule[0].dps / scenario.intrinsic_value_per_share`
  - Step-down section below:
    - PV Stage 1 .............. $XX.XX (XX% of total)
    - PV Stage 2 .............. $XX.XX (XX% of total) — if applicable
    - PV Terminal .............. $XX.XX (XX% of total)
    - ────────────────────
    - Total Intrinsic Value .... $XX.XX
    - Cost of Equity .......... XX.X%
    - Terminal Growth ......... XX.X%
    - TV % of Total ........... XX.X%
    - Payout Ratio ............ XX.X% — if available from metadata or scenario
- [ ] 3.2 — Style the panel to match DCF's key outputs design (from session 8K spec, but implement a clean version now).

---

### Task 4: DDM — Sustainability Detail Expansion
**Description:** Expand the sustainability section with mini progress bars per metric and tooltips explaining each metric.

**Subtasks:**
- [ ] 4.1 — For each sustainability metric, render:
  - Metric name (left)
  - Mini progress bar (middle): fill based on `metric.value` mapped to 0–1 scale (or normalize based on reasonable ranges). Color: green if status=green/healthy, yellow if caution, red if at_risk.
  - Value (right): formatted number
  - Status dot: colored circle matching the status
  - Tooltip (on hover over metric name): show `metric.description` — this field already exists in `SustainabilityMetric`.
- [ ] 4.2 — Add CSS for mini progress bars: 60px wide, 4px tall, rounded, with fill color based on status.
- [ ] 4.3 — Use `displayLabel()` from `@/utils/displayNames` for any metric names that might contain underscores.

**Implementation Notes:**
- `SustainabilityMetric` has: `name`, `value` (float | null), `status` ("green"/"yellow"/"red"), `description` (string).
- Progress bar scale: most sustainability metrics are ratios (0–1 range). If `value > 1`, clamp bar to 100%. If `value` is null, show empty bar.
- The `description` field provides the tooltip text — hover over the metric name to see it.

---

### Task 5: Revenue-Based — Revenue Growth Trajectory Chart
**Description:** Add a Recharts line chart showing projected revenue with Bear/Base/Bull overlaid as three lines.

**Subtasks:**
- [ ] 5.1 — In `frontend/src/pages/ModelBuilder/Models/RevBasedView.tsx`, add a new section after the ResultsCard:
  - Chart type: `LineChart` with 3 `<Line>` components (Bear, Base, Bull)
  - Data: for each scenario, map `projected_revenue` array to `{year: i+1, revenue: val}`
  - Merge into a single data array: `[{year: 1, bear: X, base: Y, bull: Z}, ...]`
  - Colors: Bear = `#60A5FA` (light blue), Base = `var(--accent-primary)`, Bull = `#22C55E` (green)
- [ ] 5.2 — Chart formatting:
  - Y-axis: compact dollar format ($XXB, $XXM)
  - X-axis: Year 1, Year 2, ...
  - Tooltip: shows year, all 3 scenario revenues
  - Legend: Bear / Base / Bull with colored lines
  - Chart title: "Revenue Growth Trajectory"
- [ ] 5.3 — Dark theme, responsive, ~250px height.

**Implementation Notes:**
- Data from `result.scenarios.bear.projected_revenue`, `result.scenarios.base.projected_revenue`, `result.scenarios.bull.projected_revenue`.
- Some scenarios may not exist — only include available ones.

---

### Task 6: Revenue-Based — Multiple Compression/Expansion Chart
**Description:** Add a line chart showing how the EV/Revenue multiple evolves by year per scenario.

**Subtasks:**
- [ ] 6.1 — Add a second chart below the revenue trajectory:
  - Chart type: `LineChart` with lines per available scenario
  - Data: `scenario.multiples_by_year` array per scenario
  - Same Bear/Base/Bull color scheme
  - Chart title: "Multiple Evolution (EV/Revenue)"
- [ ] 6.2 — Formatting:
  - Y-axis: multiple format (Xx)
  - Tooltip: year, multiple value per scenario
  - Add a horizontal reference line at current EV/Revenue multiple if available from `result.growth_metrics` or result metadata
  - Chart height: ~200px

---

### Task 7: Revenue-Based — Expanded Key Outputs Panel
**Description:** Replace or augment the Growth Metrics panel with a proper key outputs section matching DCF's format.

**Subtasks:**
- [ ] 7.1 — Add a key outputs section at the top (after ResultsCard, before charts):
  - Top row: 3 large cards:
    - **Weighted Implied Price**: `$XX.XX`
    - **Current Price**: `$XX.XX`
    - **Upside/Downside**: `+XX.X%` (color coded)
  - Secondary row:
    - Rule of 40 Score: XX.X (with pass/fail badge)
    - EV/ARR: XXx
    - Magic Number: X.XX (with status badge)
    - PSG Ratio: X.Xx
  - These metrics already exist in the Growth Metrics panel — this reorganizes them into a more prominent layout alongside the key valuation result
- [ ] 7.2 — Keep the existing Growth Metrics panel but make it more compact (it can coexist as a "detail" section below the key outputs).

---

### Task 8: Revenue-Based — Scenario Comparison Table Upgrade
**Description:** Replace the basic horizontal bar comparison with a proper table + mini football field.

**Subtasks:**
- [ ] 8.1 — Replace or augment the current scenario comparison bars with a table:
  ```
  | Scenario | Implied Price | Upside | Weight | Primary Multiple | Exit Revenue |
  |----------|--------------|--------|--------|-----------------|-------------|
  | Bear     | $142.30      | -10.2% | 25%    | 5.8x            | $45.2B      |
  | Base     | $178.45      | +12.3% | 50%    | 7.2x            | $52.1B      |
  | Bull     | $215.80      | +36.0% | 25%    | 9.1x            | $61.8B      |
  ```
- [ ] 8.2 — Below the table, add a mini football field visualization:
  - Horizontal bars (like the Overview football field but simpler): one bar per scenario showing implied price range
  - Current price as a dashed vertical line
  - Bear/Base/Bull labeled at their positions
  - Reuse the FootballField gradient pattern from 8A but simplified (single bar for range)
- [ ] 8.3 — The football field data: Bear price (left), Base price (marker), Bull price (right), Current price (dashed line). All from `result.scenarios[key].primary_implied_price`.

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: DDM has a dividend growth trajectory line chart (Recharts) with stage-based color coding.
- [ ] AC-2: DDM trajectory chart tooltip shows Year, DPS, Growth Rate, Stage name (via displayStageName).
- [ ] AC-3: DDM has a value waterfall bar chart showing PV Stage 1 → PV Stage 2 → PV Terminal → Total.
- [ ] AC-4: DDM waterfall bars have dollar value labels and percentage annotations.
- [ ] AC-5: DDM key outputs panel shows: Intrinsic Value, Current Dividend Yield, Implied Dividend Yield as large cards, plus step-down decomposition.
- [ ] AC-6: DDM sustainability metrics have mini progress bars with status-based colors and hover tooltips showing descriptions.
- [ ] AC-7: Revenue-Based has a revenue trajectory chart with Bear/Base/Bull as overlaid lines.
- [ ] AC-8: Revenue-Based has a multiple evolution chart showing EV/Revenue multiple by year.
- [ ] AC-9: Revenue-Based key outputs section shows Weighted Implied Price, Current Price, Upside prominently.
- [ ] AC-10: Revenue-Based scenario comparison has a proper table (implied price, upside, weight, multiple, exit revenue).
- [ ] AC-11: Revenue-Based has a mini football field below the scenario table.
- [ ] AC-12: All charts use dark theme styling (dark background, light text, subtle grid).
- [ ] AC-13: All charts are responsive and render correctly at 1024px, 1280px, 1600px.
- [ ] AC-14: Charts use Recharts (already in the bundle — no new dependencies).
- [ ] AC-15: Stage names in DDM charts use `displayStageName()` from `@/utils/displayNames`.
- [ ] AC-16: All new sections integrate smoothly with the existing view layout (no visual regressions).
- [ ] AC-17: Charts meet information-density standards: proper labels, hover tooltips, value annotations, compact axis labels.

---

## FILES TOUCHED

**New files:**
- None (all changes within existing view files)

**Modified files:**
- `frontend/src/pages/ModelBuilder/Models/DDMView.tsx` — trajectory chart, waterfall chart, expanded key outputs, sustainability progress bars
- `frontend/src/pages/ModelBuilder/Models/DDMView.module.css` — chart containers, key outputs panel, progress bar styles, waterfall styles
- `frontend/src/pages/ModelBuilder/Models/RevBasedView.tsx` — revenue trajectory chart, multiple evolution chart, key outputs, scenario table upgrade, mini football field
- `frontend/src/pages/ModelBuilder/Models/RevBasedView.module.css` — chart containers, key outputs panel, scenario table, football field styles

---

## BUILDER PROMPT

> **Session 8J — DDM & Revenue-Based Detail Upgrade**
>
> You are building session 8J of the Finance App v2.0 update.
>
> **What you're doing:** Upgrading DDM and Revenue-Based model views to be closer to DCF's level of detail. Adding Recharts charts, expanded key outputs panels, and richer visualization to both views.
>
> **Context:** The DCF view has a full 10-year projection table, key outputs panel, and waterfall chart. DDM currently has a dividend schedule table, 4-number decomposition, and a sustainability panel. Revenue-Based has a growth metrics panel, revenue projection table, and basic scenario comparison bars. Both need more visualization and richer output formatting.
>
> **Existing code:**
>
> `DDMView.tsx`:
> - Renders: ResultsCard → Scenario Tabs → Dividend Schedule Table → Value Decomposition (4 numbers: PV Stage 1, PV Stage 2, PV Terminal, TV%) → Sustainability Panel
> - `DDMResult` has: `scenarios` (dict of `DDMScenarioResult`), `sustainability` (`DividendSustainability`), `metadata` (cost_of_equity, ddm_variant, warnings), `weighted_intrinsic_value`, `current_price`
> - `DDMScenarioResult` has: `pv_stage1`, `pv_stage2` (nullable), `pv_terminal`, `tv_pct_of_total`, `dividend_schedule[]` (year, stage, dps, growth_rate, discount_factor, pv), `intrinsic_value_per_share`
> - `SustainabilityMetric` has: `name`, `value` (float|null), `status` ("green"/"yellow"/"red"), `description`
>
> `RevBasedView.tsx`:
> - Renders: ResultsCard → Growth Metrics Panel (Rule of 40, EV/ARR, Magic Number, PSG Ratio) → Scenario Tabs → Revenue Projection Table → Scenario Comparison (horizontal bars)
> - `RevBasedResult` has: `scenarios` (dict of `RevBasedScenarioResult`), `growth_metrics`, `current_price`, `weighted_implied_price`
> - `RevBasedScenarioResult` has: `projected_revenue[]`, `revenue_growth_rates[]`, `multiples_by_year[]`, `primary_implied_price`, `upside_downside_pct`, `scenario_weight`, `terminal_ev_revenue`
>
> Recharts is already used by DCFView — available imports: `import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, Cell } from 'recharts'`
>
> `displayNames.ts` at `@/utils/displayNames` has `displayStageName()`, `displayLabel()`.
>
> **Cross-cutting rules:**
> - Display Name Rule: Use `displayStageName()` for DDM stage labels. Import from `@/utils/displayNames`.
> - Chart Quality: All charts must meet Fidelity/Yahoo Finance information-density standards: proper labels, hover tooltips with full detail, value annotations, responsive formatting, compact axis labels. No decorative or minimal charts.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%).
> - Scenario Order: Bear / Base / Bull (left to right), Base default.
>
> **Task 1: DDM Dividend Growth Trajectory Chart**
>
> Add a Recharts LineChart after ResultsCard:
> - Data: `scenario.dividend_schedule.map(row => ({year: row.year, dps: row.dps, stage: row.stage}))`
> - Color-code dots/line segments by stage: high_growth=#3B82F6, transition=#F59E0B, terminal=#22C55E
> - Simple approach: single `<Line>` with custom `<Dot>` component that colors based on stage
> - Tooltip: Year, DPS ($ formatted), Growth Rate (%), Stage (via `displayStageName`)
> - Legend: three colored entries for stages
> - Y-axis: `$X.XX`, X-axis: year numbers
> - ResponsiveContainer height={250}
> - Dark theme: `stroke: var(--text-tertiary)` for grid, `fill: var(--text-secondary)` for axis text
>
> **Task 2: DDM Value Waterfall Chart**
>
> Add a Recharts waterfall-style BarChart:
> - Data: `[{name: "PV Stage 1", value: scenario.pv_stage1, base: 0}, {name: "PV Stage 2", value: scenario.pv_stage2, base: scenario.pv_stage1}, ...]`
> - Waterfall: stacked bars with invisible base + visible value
> - Colors: blue/yellow/green/accent matching trajectory
> - Labels on bars: dollar value + % of total
> - ResponsiveContainer height={200}
>
> **Task 3: DDM Key Outputs Panel**
>
> Replace `.decomposition` grid with:
> - 3 large cards: Intrinsic Value, Current Div Yield, Implied Div Yield
> - Step-down: PV components with % of total, total, Cost of Equity, Terminal Growth, TV%, Payout Ratio
>
> **Task 4: DDM Sustainability Expansion**
>
> Add to each metric row:
> - Mini progress bar (60px × 4px, status-colored fill)
> - Tooltip on name hover showing `metric.description`
> - Use `displayLabel()` for metric names with underscores
>
> **Task 5: RevBased Revenue Trajectory Chart**
>
> Recharts LineChart with 3 lines (Bear/Base/Bull):
> - Data: merge scenarios into `[{year: 1, bear: X, base: Y, bull: Z}, ...]`
> - Colors: Bear=#60A5FA, Base=accent, Bull=#22C55E
> - Y-axis: compact dollar ($XXB)
> - Tooltip: year, all 3 revenues
> - ResponsiveContainer height={250}
>
> **Task 6: RevBased Multiple Evolution Chart**
>
> Recharts LineChart below revenue chart:
> - Data: `scenario.multiples_by_year` per scenario
> - Same color scheme. Y-axis: Xx format. Height={200}
> - Optional ReferenceLine at current EV/Revenue
>
> **Task 7: RevBased Key Outputs**
>
> Add key outputs section (after ResultsCard, before charts):
> - 3 large cards: Weighted Implied Price, Current Price, Upside (color-coded)
> - Secondary row: Rule of 40, EV/ARR, Magic Number, PSG Ratio — reorganized from existing metrics panel
>
> **Task 8: RevBased Scenario Comparison Upgrade**
>
> Replace horizontal bars with:
> - Table: Scenario, Implied Price, Upside, Weight, Primary Multiple, Exit Revenue
> - Mini football field below: horizontal bar showing bear→base→bull range, current price line
> - Reuse gradient pattern from FootballField (lighter version)
>
> **Acceptance criteria:**
> 1. DDM: dividend trajectory chart with stage colors, proper tooltip
> 2. DDM: value waterfall with dollar + % labels
> 3. DDM: expanded key outputs (3 large cards + step-down)
> 4. DDM: sustainability progress bars with tooltips
> 5. RevBased: revenue trajectory chart with 3 scenario lines
> 6. RevBased: multiple evolution chart
> 7. RevBased: key outputs section (3 large cards + metric row)
> 8. RevBased: scenario table + mini football field
> 9. All charts: dark theme, responsive, Fidelity-quality detail
> 10. Stage names via displayStageName()
> 11. No regressions on existing functionality
>
> **Files to create:** None
>
> **Files to modify:**
> - `frontend/src/pages/ModelBuilder/Models/DDMView.tsx`
> - `frontend/src/pages/ModelBuilder/Models/DDMView.module.css`
> - `frontend/src/pages/ModelBuilder/Models/RevBasedView.tsx`
> - `frontend/src/pages/ModelBuilder/Models/RevBasedView.module.css`
>
> **Technical constraints:**
> - Recharts library (already bundled): `LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, Cell`
> - CSS modules for all styling
> - CSS variables from design system for dark theme
> - `displayStageName()` from `@/utils/displayNames`
> - Data format: percentages as decimals (multiply by 100 for display)
> - Compact dollar formatting for axes: `$XXB`, `$XXM`
> - No new dependencies — Recharts is already available
> - Waterfall pattern: stacked bars with invisible base (Recharts documented pattern)
> - All charts in `<ResponsiveContainer width="100%" height={N}>` wrapper
