# Session 8K — DCF Key Outputs & Waterfall Chart Upgrade
## Phase 8: Model Builder

**Priority:** Normal
**Type:** Frontend Only
**Depends On:** None (existing DCFView works, this is an upgrade)
**Spec Reference:** `specs/phase8_model_builder_model.md` → Area 6

---

## SCOPE SUMMARY

Redesign the DCF key outputs panel from a flat 6-value grid into a storytelling layout (3 large headline cards for EV, Equity Value, Implied Price + a step-down calculation showing EV → net debt → equity → shares → price). Upgrade the waterfall chart to Fidelity-quality detail: value labels on bars, percentage annotations, compact dollar Y-axis, market cap reference line, and richer hover tooltips with running totals.

---

## TASKS

### Task 1: Key Outputs Panel Redesign
**Description:** Replace the flat `.keyOutputsGrid` (6 `keyOutputItem` divs) with a storytelling panel: 3 large headline cards at top (Enterprise Value, Equity Value, Implied Price), a step-down calculation section in the middle, and a reference bar at the bottom showing WACC, Terminal Growth, TV% of EV, and Exit Multiple.

**Subtasks:**
- [ ] 1.1 — In `frontend/src/pages/ModelBuilder/Models/DCFView.tsx`, replace the current key outputs section (the `<div className={styles.keyOutputsPanel}>` block containing `keyOutputsGrid` with 6 `keyOutputItem` divs) with the new layout:
  - **Headline cards row:** 3 cards — Enterprise Value, Equity Value, Implied Price. Each card shows a label (10px uppercase) and a large monospaced value (22px bold). The Implied Price card gets an accent border and upside/downside tag.
  ```tsx
  <div className={styles.headlineCards}>
    <div className={styles.headlineCard}>
      <span className={styles.headlineLabel}>Enterprise Value</span>
      <span className={styles.headlineValue}>{fmtDollar(scenario.enterprise_value)}</span>
    </div>
    <div className={styles.headlineCard}>
      <span className={styles.headlineLabel}>Equity Value</span>
      <span className={styles.headlineValue}>{fmtDollar(scenario.equity_value)}</span>
    </div>
    <div className={`${styles.headlineCard} ${styles.headlineCardAccent}`}>
      <span className={styles.headlineLabel}>Implied Price</span>
      <span className={styles.headlineValue}>{fmtPrice(scenario.implied_price)}</span>
      {scenario.upside_downside_pct != null && (
        <span className={scenario.upside_downside_pct >= 0 ? styles.upsideTag : styles.downsideTag}>
          {scenario.upside_downside_pct >= 0 ? '+' : ''}{fmtPct(scenario.upside_downside_pct)} upside
        </span>
      )}
    </div>
  </div>
  ```
  - **Step-down section:** Shows the derivation from EV to implied price. Each row has a label, a right-aligned value, and an optional annotation (% of EV). Subtotal rows have a top border; the final row has a bold 2px border.
  ```tsx
  <div className={styles.stepDown}>
    <div className={styles.stepRow}>
      <span className={styles.stepLabel}>PV of FCFs</span>
      <span className={styles.stepValue}>{fmtDollar(scenario.pv_fcf_total)}</span>
      <span className={styles.stepAnnotation}>
        {fmtPct(scenario.pv_fcf_total / scenario.enterprise_value)} of EV
      </span>
    </div>
    <div className={styles.stepRow}>
      <span className={styles.stepLabel}>PV of Terminal Value</span>
      <span className={styles.stepValue}>{fmtDollar(scenario.pv_terminal_value)}</span>
      <span className={styles.stepAnnotation}>{fmtPct(scenario.tv_pct_of_ev)} of EV</span>
    </div>
    <div className={styles.stepRowSubtotal}>
      <span className={styles.stepLabel}>= Enterprise Value</span>
      <span className={styles.stepValue}>{fmtDollar(scenario.enterprise_value)}</span>
    </div>
    {netDebt != null && (
      <div className={styles.stepRow}>
        <span className={styles.stepLabel}>Less: Net Debt</span>
        <span className={styles.stepValue}>{fmtDollar(-netDebt)}</span>
      </div>
    )}
    <div className={styles.stepRowSubtotal}>
      <span className={styles.stepLabel}>= Equity Value</span>
      <span className={styles.stepValue}>{fmtDollar(scenario.equity_value)}</span>
    </div>
    {sharesOutstanding != null && (
      <div className={styles.stepRow}>
        <span className={styles.stepLabel}>÷ Shares Outstanding</span>
        <span className={styles.stepValue}>{fmtNumber(sharesOutstanding / 1e9, 2)}B</span>
      </div>
    )}
    <div className={styles.stepRowFinal}>
      <span className={styles.stepLabel}>= Implied Price</span>
      <span className={styles.stepValue}>{fmtPrice(scenario.implied_price)}</span>
    </div>
  </div>
  ```
  - **Reference bar:** Compact row at the bottom showing key assumptions.
  ```tsx
  <div className={styles.refBar}>
    <div className={styles.refItem}>
      <span className={styles.refLabel}>WACC</span>
      <span className={styles.refValue}>{fmtPct(scenario.wacc)}</span>
    </div>
    <div className={styles.refItem}>
      <span className={styles.refLabel}>Terminal Growth</span>
      <span className={styles.refValue}>{fmtPct(scenario.terminal_growth_rate)}</span>
    </div>
    <div className={styles.refItem}>
      <span className={styles.refLabel}>TV % of EV</span>
      <span className={styles.refValue}>{fmtPct(scenario.tv_pct_of_ev)}</span>
    </div>
    {scenario.terminal_exit_multiple != null && (
      <div className={styles.refItem}>
        <span className={styles.refLabel}>Exit Multiple</span>
        <span className={styles.refValue}>{fmtMultiple(scenario.terminal_exit_multiple)}</span>
      </div>
    )}
  </div>
  ```

- [ ] 1.2 — Add derived values for net debt and shares outstanding. These are NOT on `DCFScenarioResult` directly — derive them mathematically. Add as `useMemo` hooks:
  ```tsx
  const netDebt = useMemo(() => {
    if (scenario) return scenario.enterprise_value - scenario.equity_value;
    return null;
  }, [scenario]);

  const sharesOutstanding = useMemo(() => {
    if (scenario && scenario.implied_price > 0) {
      return scenario.equity_value / scenario.implied_price;
    }
    return null;
  }, [scenario]);
  ```

- [ ] 1.3 — Import `fmtMultiple` and `fmtNumber` from `./formatters` (both already exist in `formatters.ts` but are not currently imported by DCFView):
  ```tsx
  import { fmtDollar, fmtPct, fmtFactor, fmtPrice, fmtMultiple, fmtNumber } from './formatters';
  ```

**Implementation Notes:**
- `DCFScenarioResult` has: `enterprise_value`, `pv_fcf_total`, `pv_terminal_value`, `tv_pct_of_ev`, `equity_value`, `implied_price`, `upside_downside_pct`, `wacc`, `terminal_growth_rate`, `terminal_exit_multiple` (number | null).
- `DCFAssumptions` (in `types/models.ts`) has `shares_outstanding` and `net_debt` fields, but these are NOT in the run response — derive them: `net_debt = enterprise_value - equity_value`, `shares = equity_value / implied_price`.
- Guard the step-down rows for net debt and shares with null checks so they gracefully omit if the derivation fails.

---

### Task 2: Waterfall Chart Detail Upgrade
**Description:** Upgrade the existing Recharts BarChart waterfall from basic colored bars to Fidelity-quality: dollar value labels on each bar (via LabelList), percentage-of-EV annotations on addition/subtraction bars, a reference line for current market cap, compact Y-axis formatting, and richer hover tooltips showing step name + value + running total.

**Subtasks:**
- [ ] 2.1 — Add `LabelList` and `ReferenceLine` to the recharts import:
  ```tsx
  import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, Cell, LabelList, ReferenceLine,
  } from 'recharts';
  ```

- [ ] 2.2 — Enrich `waterfallData` in the existing `useMemo` to compute running totals, percentages, and pre-formatted display values:
  ```tsx
  const waterfallData = useMemo(() => {
    let runningTotal = 0;
    const ev = result.waterfall?.steps?.[0]?.value ?? 1;
    return (result.waterfall?.steps ?? []).map((step) => {
      if (step.step_type === 'start' || step.step_type === 'subtotal' || step.step_type === 'end') {
        runningTotal = step.value;
      } else {
        runningTotal += step.value;
      }
      return {
        label: step.label,
        value: step.value,
        stepType: step.step_type,
        runningTotal,
        pctOfEV: ev > 0 ? step.value / ev : 0,
        displayValue: fmtDollar(step.value),
      };
    });
  }, [result.waterfall]);
  ```

- [ ] 2.3 — Add `<LabelList>` inside `<Bar>` for dollar value labels on each bar:
  ```tsx
  <Bar dataKey="value" barSize={36}>
    {waterfallData.map((entry, index) => (
      <Cell key={index} fill={STEP_COLORS[entry.stepType] ?? '#3B82F6'} />
    ))}
    <LabelList
      dataKey="displayValue"
      position="top"
      fill="#E5E5E5"
      fontSize={10}
      fontFamily="var(--font-mono)"
    />
  </Bar>
  ```

- [ ] 2.4 — Add a custom label renderer for percentage annotations on addition/subtraction bars (skip start/end/subtotal):
  ```tsx
  const PctLabel = (props: any) => {
    const { x, y, width, index } = props;
    const entry = waterfallData[index];
    if (!entry || entry.stepType === 'start' || entry.stepType === 'end' || entry.stepType === 'subtotal') return null;
    return (
      <text
        x={x + width / 2}
        y={y - 16}
        fill="#A3A3A3"
        fontSize={9}
        textAnchor="middle"
        fontFamily="var(--font-mono)"
      >
        {fmtPct(Math.abs(entry.pctOfEV))} of EV
      </text>
    );
  };
  ```
  Add as a second `<LabelList content={<PctLabel />} />` (or `content={PctLabel}`) inside `<Bar>`.

- [ ] 2.5 — Add a `<ReferenceLine>` for current market cap. Compute from shares outstanding × current price:
  ```tsx
  const marketCap = useMemo(() => {
    if (sharesOutstanding != null && result.current_price > 0) {
      return result.current_price * sharesOutstanding;
    }
    return null;
  }, [sharesOutstanding, result.current_price]);
  ```
  Add inside `<BarChart>`:
  ```tsx
  {marketCap != null && (
    <ReferenceLine
      y={marketCap}
      stroke="#F59E0B"
      strokeDasharray="5 5"
      strokeWidth={1}
      label={{
        value: `Market Cap: ${fmtDollar(marketCap)}`,
        fill: '#F59E0B',
        fontSize: 10,
        position: 'right',
      }}
    />
  )}
  ```

- [ ] 2.6 — Replace the existing inline `<Tooltip>` with a custom content component:
  ```tsx
  const WaterfallTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    const data = payload[0]?.payload;
    if (!data) return null;
    return (
      <div className={styles.waterfallTooltip}>
        <div className={styles.tooltipLabel}>{label}</div>
        <div className={styles.tooltipRow}>
          <span>Value:</span><span>{fmtDollar(data.value)}</span>
        </div>
        <div className={styles.tooltipRow}>
          <span>Running Total:</span><span>{fmtDollar(data.runningTotal)}</span>
        </div>
        {data.pctOfEV !== 0 && data.stepType !== 'start' && (
          <div className={styles.tooltipRow}>
            <span>% of EV:</span><span>{fmtPct(Math.abs(data.pctOfEV))}</span>
          </div>
        )}
      </div>
    );
  };
  ```
  Use: `<Tooltip content={<WaterfallTooltip />} />`

- [ ] 2.7 — Increase chart height from 250 to 320 and YAxis width to 70:
  ```tsx
  <ResponsiveContainer width="100%" height={320}>
  ```
  ```tsx
  <YAxis ... width={70} />
  ```

---

### Task 3: CSS Updates
**Description:** Add new CSS classes for headline cards, step-down section, reference bar, and waterfall tooltip. Remove old grid classes.

**Subtasks:**
- [ ] 3.1 — In `DCFView.module.css`, add `.headlineCards` (3-column grid), `.headlineCard` (dark card with centered content), `.headlineCardAccent` (accent border + subtle blue bg), `.headlineLabel` (10px uppercase), `.headlineValue` (22px mono bold), `.upsideTag` / `.downsideTag` (11px colored tags)
- [ ] 3.2 — Add `.stepDown` (flex column), `.stepRow` (flex row: label flex-1, value right-aligned mono 13px, annotation tertiary 11px), `.stepRowSubtotal` (extends stepRow with 1px top border), `.stepRowFinal` (extends stepRow with 2px bold top border, 14px bold text)
- [ ] 3.3 — Add `.refBar` (flex row, bg-tertiary, top border), `.refItem` / `.refLabel` / `.refValue` (compact inline pairs)
- [ ] 3.4 — Add `.waterfallTooltip` (dark card bg-tertiary, border-medium, radius-md), `.tooltipLabel` (bold 12px), `.tooltipRow` (flex space-between, 11px, mono values)
- [ ] 3.5 — Remove old `.keyOutputsGrid`, `.keyOutputItem`, `.keyOutputLabel`, `.keyOutputValue` classes (fully replaced)
- [ ] 3.6 — Add responsive breakpoint: `@media (max-width: 768px)` — `.headlineCards` becomes single column, `.refBar` wraps with `flex-wrap: wrap`

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: 3 large headline cards (Enterprise Value, Equity Value, Implied Price) prominently displayed with monospaced large-font values.
- [ ] AC-2: Implied Price card has accent border and shows upside/downside percentage tag.
- [ ] AC-3: Step-down calculation showing PV FCFs → PV Terminal → = EV → Less: Net Debt → = Equity Value → ÷ Shares → = Implied Price.
- [ ] AC-4: Each step-down row for PV FCFs and PV Terminal shows its percentage of EV.
- [ ] AC-5: Subtotal rows (EV, Equity Value) have visible top border separators.
- [ ] AC-6: Final row (Implied Price) has bold 2px separator with larger font.
- [ ] AC-7: Reference bar at bottom showing WACC, Terminal Growth, TV%, and Exit Multiple (if applicable).
- [ ] AC-8: Waterfall bars have dollar value labels directly on them (via LabelList).
- [ ] AC-9: Addition/subtraction bars show "X.X% of EV" annotation above the dollar label.
- [ ] AC-10: Y-axis uses compact dollar format ($1.7T, $500B) — handled by existing `fmtDollar`.
- [ ] AC-11: Current market cap reference line on waterfall (dashed amber line with label). Omitted gracefully if shares not derivable.
- [ ] AC-12: Enhanced hover tooltips showing step name, value, running total, and % of EV.
- [ ] AC-13: Chart height increased to 320px to accommodate labels without overlap.
- [ ] AC-14: Old flat `.keyOutputsGrid` layout fully replaced — no remnant of the 6-item grid.
- [ ] AC-15: Charts meet Fidelity information-density standards: labeled axes, value annotations, reference lines, detailed tooltips.
- [ ] AC-16: Responsive at 1024/1280/1600px. Headline cards stack on narrow viewports.
- [ ] AC-17: No regressions on existing DCF functionality (projection table, scenario tabs, ResultsCard all unchanged).

---

## FILES TOUCHED

**New files:**
- None

**Modified files:**
- `frontend/src/pages/ModelBuilder/Models/DCFView.tsx` — key outputs panel redesign (headline cards + step-down + reference bar), waterfall chart enhancements (LabelList, ReferenceLine, custom tooltip, percentage annotations, enriched waterfallData), new imports (`LabelList`, `ReferenceLine`, `fmtMultiple`, `fmtNumber`), new derived memos (`netDebt`, `sharesOutstanding`, `marketCap`)
- `frontend/src/pages/ModelBuilder/Models/DCFView.module.css` — new classes for headline cards, step-down, reference bar, waterfall tooltip; removal of old `keyOutputsGrid`/`keyOutputItem`/`keyOutputLabel`/`keyOutputValue` classes; responsive breakpoint

---

## BUILDER PROMPT

> **Session 8K — DCF Key Outputs & Waterfall Chart Upgrade**
>
> You are building session 8K of the Finance App v2.0 update.
>
> **What you're doing:** Redesigning DCF key outputs into a storytelling panel (3 headline cards + step-down calculation + reference bar) and upgrading the waterfall chart to Fidelity-quality detail with value labels, percentage annotations, market cap reference line, and richer tooltips.
>
> **Context:** The DCF view already has a functional key outputs grid (6 flat label/value pairs in a CSS grid) and a Recharts waterfall bar chart. You're replacing the flat grid with a narrative layout that tells the story: "Here's the enterprise value, here's how we get to equity, here's your price." The waterfall gets detailed annotations so users can read precise values without hovering.
>
> **Existing code:**
>
> `DCFView.tsx` (at `frontend/src/pages/ModelBuilder/Models/DCFView.tsx`):
> - Props: `{ result: DCFResult }`
> - State: `activeScenario` (ScenarioKey = 'base' | 'bull' | 'bear')
> - Computed: `availableScenarios` (filters `['base', 'bull', 'bear']` by presence in `result.scenarios`), `scenario` (`result.scenarios[activeScenario]`), `projectionTable` (`scenario?.projection_table ?? []`), `waterfallData` (mapped from `result.waterfall.steps` to `{label, value, stepType}`), `secondaryValues` (WACC, Terminal Growth, Terminal Method, TV% for ResultsCard)
> - Renders in order: ResultsCard → Scenario Tabs → Projection Table → **Key Outputs Panel** → **Waterfall Chart**
> - Current key outputs: `<div className={styles.keyOutputsPanel}>` → `sectionTitle` "Key Outputs" → `keyOutputsGrid` (CSS grid `auto-fill minmax(160px, 1fr)`) → 6 `keyOutputItem` divs, each with `keyOutputLabel` (10px uppercase) + `keyOutputValue` (14px mono), showing: PV of FCFs, PV of Terminal Value, Enterprise Value, TV % of EV, Equity Value, Implied Price
> - Current waterfall: `<ResponsiveContainer width="100%" height={250}>` → `<BarChart>` with `CartesianGrid` (dashed, no vertical), `XAxis` (dataKey="label", angle=-30, height=50), `YAxis` (tickFormatter=fmtDollar), basic `Tooltip` (formatter shows `[fmtDollar(value), 'Value']`), `Bar` (dataKey="value", barSize=36) with `Cell` per entry colored by `STEP_COLORS`
> - `STEP_COLORS`: `{ start: '#3B82F6', subtotal: '#3B82F6', addition: '#22C55E', subtraction: '#EF4444', end: '#3B82F6' }`
> - Current recharts imports: `BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell` — **add**: `LabelList, ReferenceLine`
> - Current formatter imports: `fmtDollar, fmtPct, fmtFactor, fmtPrice` — **add**: `fmtMultiple, fmtNumber`
>
> `DCFScenarioResult` type (from `frontend/src/types/models.ts`):
> ```typescript
> interface DCFScenarioResult {
>   scenario_name: string;
>   scenario_weight: number;
>   projection_table: DCFYearRow[];
>   enterprise_value: number;
>   pv_fcf_total: number;
>   pv_terminal_value: number;
>   tv_pct_of_ev: number;
>   equity_value: number;
>   implied_price: number;
>   upside_downside_pct: number | null;
>   wacc: number;
>   terminal_growth_rate: number;
>   terminal_exit_multiple: number | null;
> }
> ```
> Does NOT have `net_debt` or `shares_outstanding` — derive: `netDebt = enterprise_value - equity_value`, `sharesOutstanding = equity_value / implied_price`.
>
> `WaterfallStep` type: `{ label: string, value: number, step_type: string }` — step_type values: `"start"`, `"addition"`, `"subtraction"`, `"subtotal"`, `"end"`
>
> `DCFResult` type: has `waterfall: { steps: WaterfallStep[] }`, `current_price: number`, `metadata: { projection_years: number, terminal_method: string, warnings: string[] }`
>
> `formatters.ts` (at `frontend/src/pages/ModelBuilder/Models/formatters.ts`):
> - `fmtDollar(v)` — handles T/B/M suffixes (`$1.7T`, `$500B`, `$23.5M`), returns `'—'` for null
> - `fmtPct(v)` — multiplies by 100, one decimal (`0.052 → "5.2%"`)
> - `fmtPrice(v)` — two decimals (`$178.45`)
> - `fmtMultiple(v)` — one decimal + x (`25.5x`)
> - `fmtNumber(v, decimals)` — locale-formatted with specified decimals
>
> `DCFView.module.css` — current classes: `.container` (flex column gap-4), `.scenarioTabs`/`.scenarioBtn`/`.scenarioBtnActive`, `.tableSection`/`.sectionTitle`/`.tableWrapper`/`.projectionTable`, `.keyOutputsPanel` (bg-secondary, border-subtle, radius-lg, padding), `.keyOutputsGrid` (CSS grid auto-fill minmax(160px, 1fr)), `.keyOutputItem`/`.keyOutputLabel` (10px uppercase tertiary)/`.keyOutputValue` (14px mono), `.waterfallSection` (bg-secondary, border-subtle, radius-lg), `.waterfallTitle` (11px uppercase)
>
> **Cross-cutting rules:**
> - Display Name Rule: All backend snake_case keys displayed in the UI must use the shared `displayNames.ts` utility (`import from '@/utils/displayNames'`). Never show raw keys. Never use inline `.replace(/_/g, ' ')`.
> - Chart Quality: All charts must meet Fidelity/Yahoo Finance information-density standards: proper labels, hover tooltips with full detail, value annotations on bars/lines, crosshairs, responsive formatting, compact axis labels.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%).
> - Scenario Order: Bear / Base / Bull (left to right), Base default.
>
> **Task 1: Key Outputs Redesign**
>
> Replace the flat 6-item `.keyOutputsGrid` with a storytelling panel inside the existing `.keyOutputsPanel` wrapper:
>
> 1. **Headline cards** (3 cards in a row): Enterprise Value, Equity Value, Implied Price. Each card: centered, `var(--bg-tertiary)` background, `var(--border-subtle)` border, `var(--radius-lg)`. Labels: 10px uppercase. Values: 22px monospaced bold. Implied Price card: accent border (`var(--accent-primary)`), subtle blue tint bg (`rgba(59, 130, 246, 0.08)`), upside/downside tag below value.
>
> 2. **Step-down calculation:**
>    - PV of FCFs — $X.XT (XX.X% of EV)
>    - PV of Terminal Value — $X.XT (XX.X% of EV)
>    - = Enterprise Value — $X.XT [subtotal: 1px top border, padding-top]
>    - Less: Net Debt — -$X.XB
>    - = Equity Value — $X.XT [subtotal: 1px top border]
>    - ÷ Shares Outstanding — X.XXB
>    - = Implied Price — $XXX.XX [final: 2px bold top border, 14px bold text]
>
>    Derive `netDebt = scenario.enterprise_value - scenario.equity_value`. Derive `sharesOutstanding = scenario.equity_value / scenario.implied_price`. Both as `useMemo` hooks. Guard with null checks — omit the row if null.
>
> 3. **Reference bar:** Flex row at bottom with `var(--bg-tertiary)` bg and top border. Items: WACC, Terminal Growth, TV % of EV, Exit Multiple (if `terminal_exit_multiple != null`). Labels 10px uppercase, values 12px mono.
>
> Remove old `.keyOutputsGrid`, `.keyOutputItem`, `.keyOutputLabel`, `.keyOutputValue` from CSS.
>
> **Task 2: Waterfall Chart Upgrade**
>
> Enhance the existing `<BarChart>` waterfall:
>
> 1. **Add imports:** `LabelList`, `ReferenceLine` from recharts. `fmtMultiple`, `fmtNumber` from `./formatters`.
>
> 2. **Enrich waterfallData** in the existing `useMemo`: for each step, compute `runningTotal` (accumulates for additions/subtractions, resets for start/subtotal/end), `pctOfEV` (`step.value / firstStepValue`), and `displayValue` (`fmtDollar(step.value)`).
>
> 3. **Bar value labels:** Add `<LabelList dataKey="displayValue" position="top" fill="#E5E5E5" fontSize={10} fontFamily="var(--font-mono)" />` inside `<Bar>`.
>
> 4. **Percentage annotations:** Create a `PctLabel` custom renderer that renders `"{X.X%} of EV"` text above each addition/subtraction bar (skip start/end/subtotal). Position at `y - 16` so it sits above the dollar label. Add as a second `<LabelList content={PctLabel} />` inside `<Bar>`.
>
> 5. **Market cap reference line:** Compute `marketCap = currentPrice × sharesOutstanding` as a `useMemo`. Add `<ReferenceLine y={marketCap} stroke="#F59E0B" strokeDasharray="5 5" strokeWidth={1} label={{ value: "Market Cap: $X.XT", fill: "#F59E0B", fontSize: 10, position: "right" }} />`. Only render when `marketCap != null`.
>
> 6. **Enhanced tooltip:** Replace the inline `formatter` tooltip with a custom `WaterfallTooltip` component. Shows: step name (bold), value (mono), running total (mono), and % of EV (for non-start steps). Style with new `.waterfallTooltip`, `.tooltipLabel`, `.tooltipRow` CSS classes.
>
> 7. **Chart sizing:** Increase height from 250 → 320. Set YAxis width to 70 (prevents label truncation on large values).
>
> **Task 3: CSS**
>
> In `DCFView.module.css`:
> - `.headlineCards` — `grid-template-columns: repeat(3, 1fr); gap: var(--space-3); margin-bottom: var(--space-4)`
> - `.headlineCard` — flex column centered, `var(--bg-tertiary)`, `var(--border-subtle)`, `var(--radius-lg)`, padding space-4/space-3
> - `.headlineCardAccent` — `border-color: var(--accent-primary); background: rgba(59, 130, 246, 0.08)`
> - `.headlineLabel` — 10px uppercase, letter-spacing 0.4px, `var(--text-tertiary)`
> - `.headlineValue` — 22px `var(--font-mono)` weight 700, `var(--text-primary)`
> - `.upsideTag` — 11px mono 600, `var(--color-positive)` | `.downsideTag` — same with `var(--color-negative)`
> - `.stepDown` — flex column, padding space-3/space-4
> - `.stepRow` — flex row align-center, padding space-1 vertical
> - `.stepLabel` — 12px sans, `var(--text-secondary)`, flex: 1
> - `.stepValue` — 13px mono 600, right-aligned, min-width 100px
> - `.stepAnnotation` — 11px mono, `var(--text-tertiary)`, margin-left space-2
> - `.stepRowSubtotal` — composes stepRow + `border-top: 1px solid var(--border-medium); padding-top: var(--space-2); margin-top: var(--space-1)`
> - `.stepRowFinal` — composes stepRow + `border-top: 2px solid var(--text-primary); padding-top: var(--space-2); margin-top: var(--space-1)` + nested label/value at 14px weight 700
> - `.refBar` — flex row, gap space-4, padding space-3/space-4, `var(--bg-tertiary)`, `border-top: 1px solid var(--border-subtle)`, bottom radius
> - `.refItem` — flex row align-center gap space-2
> - `.refLabel` — 10px uppercase 600, `var(--text-tertiary)` | `.refValue` — 12px mono 600, `var(--text-primary)`
> - `.waterfallTooltip` — `var(--bg-tertiary)`, `1px solid var(--border-medium)`, radius-md, padding space-2/space-3, min-width 180px
> - `.tooltipLabel` — 12px weight 600, `var(--text-primary)`, margin-bottom space-1
> - `.tooltipRow` — flex space-between, 11px, `var(--text-secondary)`, last-child span mono + `var(--text-primary)` + 500
> - Remove: `.keyOutputsGrid`, `.keyOutputItem`, `.keyOutputLabel`, `.keyOutputValue`
> - Responsive: `@media (max-width: 768px)` → `.headlineCards { grid-template-columns: 1fr }`, `.refBar { flex-wrap: wrap }`
>
> **Acceptance criteria:**
> 1. 3 headline cards with large values (EV, Equity Value, Implied Price)
> 2. Implied Price card has accent styling + upside tag
> 3. Step-down shows EV derivation with % of EV annotations
> 4. Subtotal/final rows have visual separators (1px and 2px)
> 5. Reference bar shows WACC, Terminal Growth, TV%, Exit Multiple
> 6. Waterfall bars have dollar value labels (LabelList)
> 7. Addition/subtraction bars have % of EV annotations
> 8. Market cap reference line (dashed amber) — gracefully omitted if not computable
> 9. Enhanced tooltips with running total and % of EV
> 10. Chart height 320px, YAxis width 70
> 11. Old flat grid fully replaced
> 12. Responsive at narrow viewports
> 13. No regressions on projection table, scenario tabs, ResultsCard
>
> **Files to create:** None
>
> **Files to modify:**
> - `frontend/src/pages/ModelBuilder/Models/DCFView.tsx`
> - `frontend/src/pages/ModelBuilder/Models/DCFView.module.css`
>
> **Technical constraints:**
> - Recharts for all charting (already loaded)
> - CSS modules for all styling (`.module.css`)
> - Dark theme: use CSS variables (`var(--bg-tertiary)`, `var(--text-primary)`, `var(--accent-primary)`, `var(--border-subtle)`, `var(--border-medium)`, `var(--color-positive)`, `var(--color-negative)`, `var(--radius-lg)`, `var(--radius-md)`, `var(--space-N)`, `var(--font-mono)`, `var(--font-sans)`)
> - Formatters: import `fmtDollar`, `fmtPct`, `fmtPrice`, `fmtMultiple`, `fmtNumber` from `./formatters` — all exist, just add the missing imports
> - `DCFScenarioResult` does NOT have `net_debt` or `shares_outstanding` — derive mathematically with null guards
> - No new dependencies — only recharts additions (`LabelList`, `ReferenceLine`) which are part of the existing recharts package
> - Keep ALL existing sections intact: ResultsCard, Scenario Tabs, Projection Table. Only replace Key Outputs and enhance Waterfall.
> - `SCENARIO_LABELS` and `STEP_COLORS` remain unchanged
