# Session 11C — Trend Chart Fidelity Upgrade + DuPont ROE Fix
## Phase 11: Research

**Priority:** Normal
**Type:** Frontend Only
**Depends On:** 11A (data accuracy must be fixed for chart values to be meaningful)
**Spec Reference:** `specs/phase11_research.md` → Area 5 (5A, 5B)

---

## SCOPE SUMMARY

Upgrade the Ratios tab trend chart to Fidelity-quality: larger chart, categorized metric selector with pill toggles, dual Y-axis for mixed format metrics, richer tooltips with YoY change, crosshair, and data point markers. Fix the DuPont ROE decomposition with contextual notes for extreme equity multiplier values, color coding, and historical sparklines for each component.

---

## TASKS

### Task 1: Trend Chart Fidelity Upgrade
**Description:** Overhaul the RatioTrendChart from a basic Recharts LineChart to an information-dense, interactive chart.

**Subtasks:**
- [ ] 1.1 — In `frontend/src/pages/Research/Ratios/RatioTrendChart.tsx`, increase chart height from 300px to 400px+ and make it the focal element of the Ratios tab.

- [ ] 1.2 — Redesign the metric selector from a row of small buttons to categorized pill groups:
  ```tsx
  const SELECTOR_CATEGORIES = [
    { label: 'Profitability', metrics: ['gross_margin', 'operating_margin', 'net_margin', 'ebitda_margin'] },
    { label: 'Returns', metrics: ['roe', 'roa', 'roic'] },
    { label: 'Leverage', metrics: ['debt_to_equity', 'current_ratio'] },
    { label: 'Growth', metrics: ['revenue_growth', 'eps_growth'] },
    { label: 'Efficiency', metrics: ['asset_turnover', 'fcf_margin'] },
  ];
  ```
  Each category label is a subtle header, metrics below are pill toggles. Active pills show a colored dot matching the line color.

- [ ] 1.3 — Implement dual Y-axis when mixing percentage and ratio metrics:
  ```tsx
  const hasPercent = selectedMetrics.some((m) => getMetricFormat(m) === 'percent');
  const hasRatio = selectedMetrics.some((m) => getMetricFormat(m) === 'ratio');
  const useDualAxis = hasPercent && hasRatio;
  ```
  Left Y-axis: percentage format (×100 + %). Right Y-axis: ratio format (x).
  ```tsx
  <YAxis yAxisId="left" tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
  {useDualAxis && (
    <YAxis yAxisId="right" orientation="right" tickFormatter={(v) => `${v.toFixed(1)}x`} />
  )}
  ```
  Assign each metric's `<Line>` to the appropriate yAxisId based on its format.

- [ ] 1.4 — Add a custom tooltip with YoY change:
  ```tsx
  const TrendTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
      <div className={styles.trendTooltip}>
        <div className={styles.tooltipYear}>{label}</div>
        {payload.map((p: any) => {
          const prevYear = chartData.find((d) => d.year === label - 1);
          const prevVal = prevYear?.[p.dataKey];
          const yoyChange = prevVal != null && p.value != null ? p.value - prevVal : null;
          return (
            <div key={p.dataKey} className={styles.tooltipRow}>
              <span style={{ color: p.color }}>●</span>
              <span>{getMetricLabel(p.dataKey)}:</span>
              <span>{formatMetricForTooltip(p.value, p.dataKey)}</span>
              {yoyChange != null && (
                <span className={yoyChange >= 0 ? styles.yoyPositive : styles.yoyNegative}>
                  ({yoyChange >= 0 ? '+' : ''}{formatMetricForTooltip(yoyChange, p.dataKey)})
                </span>
              )}
            </div>
          );
        })}
      </div>
    );
  };
  ```

- [ ] 1.5 — Add data point markers (`dot={true}` on `<Line>` components) and an `activeDot` for hover highlight.

- [ ] 1.6 — Add a dynamic chart title: "Margin Trends (10Y)" or "Returns vs Leverage (10Y)" based on selected category.

- [ ] 1.7 — In `RatioTrendChart.module.css`, add styles for: categorized selector (`.selectorCategory`, `.selectorLabel`, `.metricPill`, `.metricPillActive`, `.metricDot`), tooltip (`.trendTooltip`, `.tooltipYear`, `.tooltipRow`, `.yoyPositive`, `.yoyNegative`), chart title.

---

### Task 2: DuPont ROE Context Fix
**Description:** Add contextual notes, color coding, and sparklines to the DuPont decomposition for extreme values.

**Subtasks:**
- [ ] 2.1 — In `frontend/src/pages/Research/Ratios/DuPontDecomposition.tsx`, add contextual note when equity multiplier > 4x or stockholders_equity is negative:
  ```tsx
  {equityMultiplier > 4.0 && (
    <div className={styles.contextNote}>
      Elevated ROE driven by high financial leverage. {ticker}'s equity base is reduced
      by significant share buybacks, amplifying the equity multiplier. Common for mature
      companies with aggressive buyback programs.
    </div>
  )}
  {equityIsNegative && (
    <div className={styles.contextNote}>
      <strong>Negative Equity:</strong> Traditional ROE is not meaningful when
      stockholders' equity is negative. This typically results from accumulated buybacks
      exceeding retained earnings.
    </div>
  )}
  ```

- [ ] 2.2 — Color-code the equity multiplier value: green < 2x, yellow 2–4x, red > 4x:
  ```tsx
  const emColor = equityMultiplier < 2 ? 'var(--color-positive)' :
    equityMultiplier < 4 ? 'var(--color-warning)' : 'var(--color-negative)';
  ```

- [ ] 2.3 — Add small historical sparklines for each DuPont component (3–5 year trend). Fetch historical financials from the existing `/research/{ticker}/financials` endpoint and compute net margin, asset turnover, equity multiplier per year. Render as tiny inline Recharts LineChart (50px wide × 20px tall, no axes):
  ```tsx
  <ResponsiveContainer width={50} height={20}>
    <LineChart data={sparkData}>
      <Line type="monotone" dataKey="value" stroke={color} strokeWidth={1} dot={false} />
    </LineChart>
  </ResponsiveContainer>
  ```

- [ ] 2.4 — In `DuPontDecomposition.module.css`, add styles for `.contextNote` (warning background, rounded, padding), sparkline container, and color-coded multiplier.

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: Trend chart height is 400px+ (increased from 300px).
- [ ] AC-2: Metric selector grouped by category (Profitability, Returns, Leverage, Growth, Efficiency).
- [ ] AC-3: Active metric pills show colored dot matching line color.
- [ ] AC-4: Dual Y-axis enabled when mixing percent and ratio metrics (left: %, right: x).
- [ ] AC-5: Tooltip shows all selected metrics at hovered year with YoY change.
- [ ] AC-6: Data points visible as dots on lines; active dot highlighted on hover.
- [ ] AC-7: Dynamic chart title reflects selected metrics.
- [ ] AC-8: DuPont shows contextual note when equity multiplier > 4x.
- [ ] AC-9: DuPont shows "Negative Equity" note when applicable.
- [ ] AC-10: Equity multiplier color-coded: green < 2x, yellow 2–4x, red > 4x.
- [ ] AC-11: DuPont components have 3–5 year sparklines.
- [ ] AC-12: Chart meets Fidelity information-density standards.
- [ ] AC-13: No regressions on existing Ratios tab functionality.

---

## FILES TOUCHED

**New files:**
- None

**Modified files:**
- `frontend/src/pages/Research/Ratios/RatioTrendChart.tsx` — full chart overhaul: larger, categorized selector, dual Y-axis, rich tooltip with YoY, data markers
- `frontend/src/pages/Research/Ratios/RatioTrendChart.module.css` — selector, tooltip, chart title styles
- `frontend/src/pages/Research/Ratios/DuPontDecomposition.tsx` — context notes, color coding, sparklines
- `frontend/src/pages/Research/Ratios/DuPontDecomposition.module.css` — note, sparkline, color styles

---

## BUILDER PROMPT

> **Session 11C — Trend Chart Fidelity Upgrade + DuPont ROE Fix**
>
> You are building session 11C of the Finance App v2.0 update.
>
> **What you're doing:** Two things: (1) Full Fidelity upgrade of the Ratios trend chart — larger, categorized metric selector, dual Y-axis, rich tooltips with YoY change, data markers. (2) DuPont ROE context fix — notes for extreme equity multiplier, color coding, historical sparklines.
>
> **Context:** Session 11A fixed data accuracy. Chart values are now correct. This session makes them visually compelling and informative. The DuPont decomposition shows alarming numbers for companies like Apple (ROE >150%) without explaining that high leverage from buybacks is the cause.
>
> **Existing code:**
>
> `RatioTrendChart.tsx` — basic Recharts LineChart, 300px height, row of small toggle buttons for metrics, single Y-axis, basic tooltip. `dot={false}` on lines.
>
> `DuPontDecomposition.tsx` — shows ROE = Net Margin × Asset Turnover × Equity Multiplier. No context notes, no color coding, no sparklines.
>
> `ratioConfig.ts` — has metric definitions with categories. Can be used for the categorized selector.
>
> **Cross-cutting rules:**
> - Chart Quality: Fidelity-level detail — tooltips, crosshair, value labels, responsive.
> - Data Format: Decimal ratios. `fmtPct` multiplies by 100.
>
> **Files to modify:** `RatioTrendChart.tsx/css`, `DuPontDecomposition.tsx/css`
>
> **Technical constraints:**
> - Recharts for all charting. Dual Y-axis via `yAxisId="left"` / `yAxisId="right"`.
> - Sparklines: tiny `<ResponsiveContainer width={50} height={20}>` with no axes.
> - DuPont data comes from the financials already fetched for the Ratios tab.
> - Equity multiplier = total_assets / stockholders_equity. Color thresholds: green < 2x, yellow 2–4x, red > 4x.
