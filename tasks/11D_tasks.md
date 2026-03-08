# Session 11D — Stock Price Charts
## Phase 11: Research

**Priority:** Normal
**Type:** Frontend Only
**Depends On:** None (backend already has `/companies/{ticker}/historical` endpoint)
**Spec Reference:** `specs/phase11_research.md` → Area 6 (6A, 6B)

---

## SCOPE SUMMARY

Add interactive stock price charts to the Research page — a line/candlestick chart with period selector, volume bars, 50/200-day moving average overlays, crosshair tooltip, and current price reference line. Placed between the TickerHeaderBar and sub-tabs as a collapsible, always-visible chart providing price context regardless of which sub-tab is active.

---

## TASKS

### Task 1: Price Chart Component
**Description:** Create a new `PriceChart` component with interactive price visualization.

**Subtasks:**
- [ ] 1.1 — Create `frontend/src/pages/Research/PriceChart/PriceChart.tsx`:
  ```tsx
  interface Props {
    ticker: string;
  }

  const PERIODS = ['1D', '5D', '1M', '3M', '6M', 'YTD', '1Y', '5Y', 'MAX'] as const;
  type Period = (typeof PERIODS)[number];
  type ChartType = 'line' | 'candlestick';
  ```
  State: `period` (default '1Y'), `chartType` (default 'line'), `showMA50`, `showMA200`, `collapsed`, `data` (PriceBar[]), `loading`.

- [ ] 1.2 — Fetch historical data on mount and period change:
  ```tsx
  useEffect(() => {
    if (!ticker) return;
    setLoading(true);
    api.get<{ bars: PriceBar[] }>(
      `/api/v1/companies/${ticker}/historical?period=${period}`
    ).then((d) => { setData(d.bars); setLoading(false); })
    .catch(() => setLoading(false));
  }, [ticker, period]);
  ```
  The `PriceBar` type: `{ date: string, open: number, high: number, low: number, close: number, volume: number }`.

- [ ] 1.3 — Compute moving averages from the price data:
  ```tsx
  const ma50 = useMemo(() => computeMA(data, 50), [data]);
  const ma200 = useMemo(() => computeMA(data, 200), [data]);

  function computeMA(bars: PriceBar[], window: number): { date: string; value: number }[] {
    return bars.map((_, i) => {
      if (i < window - 1) return { date: bars[i].date, value: NaN };
      const slice = bars.slice(i - window + 1, i + 1);
      const avg = slice.reduce((sum, b) => sum + b.close, 0) / window;
      return { date: bars[i].date, value: avg };
    }).filter((d) => !isNaN(d.value));
  }
  ```

- [ ] 1.4 — Render the line chart (default mode) using Recharts:
  ```tsx
  <ResponsiveContainer width="100%" height={300}>
    <ComposedChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
      <XAxis dataKey="date" tick={{ fill: '#A3A3A3', fontSize: 10 }} stroke="#333"
        tickFormatter={formatDateTick} interval="preserveStartEnd" />
      <YAxis yAxisId="price" tick={{ fill: '#A3A3A3', fontSize: 11 }} stroke="#333"
        domain={['auto', 'auto']} tickFormatter={(v) => `$${v.toFixed(0)}`} />
      <YAxis yAxisId="volume" orientation="right" tick={false} stroke="transparent"
        domain={[0, (max: number) => max * 4]} />
      <Tooltip content={<PriceTooltip />} />
      <Bar yAxisId="volume" dataKey="volume" fill="#333" fillOpacity={0.4} />
      <Line yAxisId="price" type="monotone" dataKey="close" stroke="var(--accent-primary)"
        strokeWidth={1.5} dot={false} />
      {showMA50 && (
        <Line yAxisId="price" type="monotone" dataKey="ma50" stroke="#F59E0B"
          strokeWidth={1} dot={false} strokeDasharray="4 4" name="50-Day MA" />
      )}
      {showMA200 && (
        <Line yAxisId="price" type="monotone" dataKey="ma200" stroke="#EF4444"
          strokeWidth={1} dot={false} strokeDasharray="4 4" name="200-Day MA" />
      )}
      <ReferenceLine yAxisId="price" y={currentPrice} stroke="#555" strokeDasharray="2 2" />
    </ComposedChart>
  </ResponsiveContainer>
  ```
  Merge price data + MA data + volume into a single `chartData` array keyed by date.

- [ ] 1.5 — Render the candlestick chart (toggle mode). Use custom Recharts `<Bar>` shapes or a custom SVG renderer for OHLC candles:
  ```tsx
  // Simplified: use error bars or custom shapes for candle wicks
  // Each candle: body from open→close (green if close>open, red if close<open)
  // Wicks from low→high
  ```
  This can be complex with Recharts — if Recharts candlestick is too involved, use a custom SVG overlay approach or a lightweight candlestick helper.

- [ ] 1.6 — Create a custom tooltip:
  ```tsx
  const PriceTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    return (
      <div className={styles.priceTooltip}>
        <div className={styles.tooltipDate}>{d.date}</div>
        <div className={styles.tooltipRow}><span>Open:</span><span>${d.open?.toFixed(2)}</span></div>
        <div className={styles.tooltipRow}><span>High:</span><span>${d.high?.toFixed(2)}</span></div>
        <div className={styles.tooltipRow}><span>Low:</span><span>${d.low?.toFixed(2)}</span></div>
        <div className={styles.tooltipRow}><span>Close:</span><span>${d.close?.toFixed(2)}</span></div>
        <div className={styles.tooltipRow}><span>Volume:</span><span>{d.volume?.toLocaleString()}</span></div>
      </div>
    );
  };
  ```

- [ ] 1.7 — Render controls bar: period pills, chart type toggle (Line / Candle), MA checkboxes, collapse toggle.

---

### Task 2: Placement on Research Page
**Description:** Add the PriceChart between the TickerHeaderBar and the sub-tabs on the Research page. Make it collapsible.

**Subtasks:**
- [ ] 2.1 — In `frontend/src/pages/Research/ResearchPage.tsx`, import and render `PriceChart` between the header and tabs:
  ```tsx
  {activeTicker && (
    <PriceChart ticker={activeTicker} />
  )}
  ```
  The chart has its own collapse toggle — when collapsed, it shows a thin bar: "Price Chart [▸ Expand]".

- [ ] 2.2 — In `ResearchPage.module.css`, add a chart area section with appropriate spacing.

---

### Task 3: CSS
**Description:** Style the price chart component.

**Subtasks:**
- [ ] 3.1 — Create `frontend/src/pages/Research/PriceChart/PriceChart.module.css`:
  - `.container` — bg-secondary, border-subtle, radius-lg, padding
  - `.controlsBar` — flex row with period pills, chart type toggle, MA checkboxes, collapse button
  - `.periodPill` / `.periodPillActive` — same pattern as other pill toggles
  - `.chartTypeToggle` — small toggle buttons: Line / Candle
  - `.maCheckbox` — inline checkbox + label for 50-day MA, 200-day MA
  - `.collapseBtn` — small button to collapse/expand
  - `.collapsed` — thin bar with "Price Chart [▸]"
  - `.priceTooltip` — dark theme tooltip matching other charts
  - `.tooltipDate`, `.tooltipRow` — standard tooltip row pattern
  - Volume bars should be subtle (low opacity) behind the price line

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: Price chart visible on Research page between header and sub-tabs.
- [ ] AC-2: Period selector with 9 options: 1D, 5D, 1M, 3M, 6M, YTD, 1Y, 5Y, MAX.
- [ ] AC-3: Default view is line chart (1Y period).
- [ ] AC-4: Chart type toggle switches between line and candlestick.
- [ ] AC-5: Volume bars shown below the price chart (same x-axis, separate y-scale).
- [ ] AC-6: 50-day MA overlay toggle (dashed amber line).
- [ ] AC-7: 200-day MA overlay toggle (dashed red line).
- [ ] AC-8: Current price reference line (subtle dashed gray).
- [ ] AC-9: Hover tooltip shows: date, open, high, low, close, volume.
- [ ] AC-10: Chart is collapsible — collapsed state shows a thin expandable bar.
- [ ] AC-11: Chart responds to ticker changes (re-fetches data).
- [ ] AC-12: Responsive at 1024/1280/1600px.
- [ ] AC-13: No backend changes needed — uses existing `GET /companies/{ticker}/historical` endpoint.
- [ ] AC-14: No regressions on existing Research page functionality.

---

## FILES TOUCHED

**New files:**
- `frontend/src/pages/Research/PriceChart/PriceChart.tsx` — interactive price chart component
- `frontend/src/pages/Research/PriceChart/PriceChart.module.css` — chart styles

**Modified files:**
- `frontend/src/pages/Research/ResearchPage.tsx` — add PriceChart between header and tabs
- `frontend/src/pages/Research/ResearchPage.module.css` — chart area spacing

---

## BUILDER PROMPT

> **Session 11D — Stock Price Charts**
>
> You are building session 11D of the Finance App v2.0 update.
>
> **What you're doing:** Adding interactive stock price charts to the Research page — line/candlestick chart with period selector, volume bars, moving average overlays, tooltip, and current price reference line. Placed between header and sub-tabs, collapsible.
>
> **Context:** The Research page currently has no price visualization — just a current price number in the header. Adding a chart makes it a proper research hub. The backend already has `GET /api/v1/companies/{ticker}/historical?period=1y` returning OHLCV bars. No backend changes needed.
>
> **Existing code:**
>
> `ResearchPage.tsx` — renders: TickerHeaderBar → Sub-tabs (Filings, Financials, Ratios, Profile, Peers). The chart will go between header and tabs.
>
> Backend endpoint: `GET /api/v1/companies/{ticker}/historical?period={period}` — returns `PriceBar[]` where `PriceBar = { date: string, open: number, high: number, low: number, close: number, volume: number }`. Periods: "1d", "5d", "1mo", "3mo", "6mo", "ytd", "1y", "5y", "max".
>
> **Cross-cutting rules:**
> - Chart Quality: Fidelity-level — tooltips, crosshair, proper legends, responsive.
> - Data Format: Prices in raw dollars. Volume as integers.
>
> **Task 1: PriceChart Component**
> - Period selector: 1D, 5D, 1M, 3M, 6M, YTD, 1Y, 5Y, MAX
> - Chart type toggle: Line (default) / Candlestick
> - Volume bars on secondary Y-axis (low opacity, behind price)
> - 50-day and 200-day MA toggles (computed client-side from price data)
> - Current price reference line (dashed gray)
> - Tooltip: date, OHLCV
> - Collapsible with thin bar in collapsed state
>
> **Task 2: Placement**
> - In ResearchPage, render between header and tabs when ticker is active
>
> **Technical constraints:**
> - Recharts `ComposedChart` for mixing Line + Bar (volume). Import: `ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine`
> - MA computation: client-side rolling average from close prices
> - Candlestick: complex with pure Recharts. Options: (a) custom Bar shapes with wick rendering, (b) simple colored bars for body + error bars for wicks. Keep it clean — if too complex, default to line and note candlestick as a stretch goal.
> - Period string mapping: UI shows "1M" but API may expect "1mo" — map before fetching
> - `PriceBar` type: define locally or import if it exists in types
> - No new dependencies needed — Recharts already loaded
