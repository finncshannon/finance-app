# Session 10D — Performance Frontend + Refresh Button + WebSocket Subscription
## Phase 10: Portfolio

**Priority:** High
**Type:** Frontend Only
**Depends On:** 10C (backend data fixes — startup refresh, after-hours interval, day_change_pct fix)
**Spec Reference:** `specs/phase10_portfolio_performance.md` → Areas 1, 2, 3, 5E, 6

---

## SCOPE SUMMARY

Upgrade the BenchmarkChart from raw SVG to Recharts with Fidelity-quality detail (hover tooltips, crosshair, proper legend, responsive formatting). Fix the Attribution table's "Unknown" sector handling. Add short timeframe period options (1D, 3D, 5D, 2W). Subscribe portfolio tickers to the WebSocket price feed for live updates. Add a Refresh button to the Portfolio page header.

---

## TASKS

### Task 1: BenchmarkChart Fidelity Upgrade
**Description:** Replace the raw SVG BenchmarkChart with a Recharts LineChart featuring proper tooltips, crosshair, responsive formatting, and clear legends.

**Subtasks:**
- [ ] 1.1 — In `frontend/src/pages/Portfolio/Performance/BenchmarkChart.tsx`, replace the SVG implementation with Recharts:
  ```tsx
  import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
  ```
  Build chart data by merging portfolio and benchmark normalized series into a single array:
  ```tsx
  const chartData = useMemo(() => {
    const portNorm = normalize(benchmark.portfolio_series);
    const benchNorm = normalize(benchmark.benchmark_series);
    const maxLen = Math.max(portNorm.length, benchNorm.length);
    return Array.from({ length: maxLen }, (_, i) => ({
      date: portNorm[i]?.date ?? benchNorm[i]?.date ?? '',
      portfolio: portNorm[i]?.value ?? null,
      benchmark: benchNorm[i]?.value ?? null,
    }));
  }, [benchmark]);
  ```

- [ ] 1.2 — Render the Recharts LineChart:
  ```tsx
  <ResponsiveContainer width="100%" height={300}>
    <LineChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 8 }}>
      <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
      <XAxis dataKey="date" tick={{ fill: '#A3A3A3', fontSize: 10 }} stroke="#333"
        tickFormatter={formatDateTick} interval="preserveStartEnd" />
      <YAxis tick={{ fill: '#A3A3A3', fontSize: 11 }} stroke="#333"
        tickFormatter={(v) => `${v.toFixed(0)}`} domain={['dataMin - 2', 'dataMax + 2']} />
      <Tooltip content={<BenchmarkTooltip />} />
      <Legend verticalAlign="top" height={30} />
      <ReferenceLine y={100} stroke="#555" strokeDasharray="3 3" label={{ value: 'Start', fill: '#666', fontSize: 10 }} />
      <Line type="monotone" dataKey="portfolio" name="Portfolio" stroke="var(--accent-primary)" strokeWidth={2} dot={false} />
      <Line type="monotone" dataKey="benchmark" name="SPY Benchmark" stroke="#F59E0B" strokeWidth={1.5} dot={false} strokeDasharray="4 4" />
    </LineChart>
  </ResponsiveContainer>
  ```

- [ ] 1.3 — Create a custom tooltip component:
  ```tsx
  const BenchmarkTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    const port = payload.find((p: any) => p.dataKey === 'portfolio')?.value;
    const bench = payload.find((p: any) => p.dataKey === 'benchmark')?.value;
    const alpha = port != null && bench != null ? port - bench : null;
    return (
      <div className={styles.tooltip}>
        <div className={styles.tooltipDate}>{label}</div>
        {port != null && <div className={styles.tooltipRow}><span>Portfolio:</span><span>{port.toFixed(1)}</span></div>}
        {bench != null && <div className={styles.tooltipRow}><span>Benchmark:</span><span>{bench.toFixed(1)}</span></div>}
        {alpha != null && <div className={styles.tooltipRow}><span>Alpha:</span><span style={{ color: alpha >= 0 ? 'var(--color-positive)' : 'var(--color-negative)' }}>{alpha >= 0 ? '+' : ''}{alpha.toFixed(1)}</span></div>}
      </div>
    );
  };
  ```

- [ ] 1.4 — Update `BenchmarkChart.module.css`: remove old SVG styles, add Recharts tooltip styles matching the dark theme pattern used in Model Builder charts.

- [ ] 1.5 — Keep the existing `normalize()` function (it works correctly). Add a `formatDateTick` helper that shows "Jan 25", "Feb 25" etc. and thins out labels at longer timeframes.

---

### Task 2: Return Metrics + Risk Metrics Responsive Fix
**Description:** Fix number formatting and responsive layout for the ReturnMetrics and RiskMetrics panels.

**Subtasks:**
- [ ] 2.1 — In `ReturnMetrics.tsx`, verify all percentage values use `fmtPct` (×100 + %). Ensure `+` prefix for positive returns. Use compact dollar format for absolute values.
- [ ] 2.2 — In `ReturnMetrics.module.css`, ensure the metrics grid stacks vertically on narrow viewports (`@media (max-width: 768px)`).
- [ ] 2.3 — Same audit and responsive fix for `RiskMetrics.tsx` and `RiskMetrics.module.css`.

---

### Task 3: Attribution Table "Unknown" Sector Fix
**Description:** Handle "Unknown" sectors gracefully in the attribution table. Show count and a suggestion to refresh.

**Subtasks:**
- [ ] 3.1 — In `frontend/src/pages/Portfolio/Performance/AttributionTable.tsx`, when sectors include "Unknown", show the count and a note:
  ```tsx
  {unknownCount > 0 && (
    <div className={styles.unknownNote}>
      {unknownCount} position{unknownCount > 1 ? 's' : ''} with unknown sector.
      <button className={styles.refreshLink} onClick={onRefreshProfiles}>Refresh company data</button> to classify.
    </div>
  )}
  ```
- [ ] 3.2 — Accept `onRefreshProfiles` callback prop (triggers `POST /portfolio/refresh-profiles` from 10C).
- [ ] 3.3 — In `AttributionTable.module.css`, add `.unknownNote` and `.refreshLink` styles.

---

### Task 4: Short Timeframe Period Options
**Description:** Add 1D, 3D, 5D, 2W period options before the existing set.

**Subtasks:**
- [ ] 4.1 — In `frontend/src/pages/Portfolio/Performance/PerformanceTab.tsx`, update the PERIODS array:
  ```tsx
  const PERIODS = ['1D', '3D', '5D', '2W', '1M', '3M', '6M', 'YTD', '1Y', '3Y', 'ALL'] as const;
  ```
- [ ] 4.2 — The backend already accepts `period` as a string parameter. For short periods (1D, 3D, 5D, 2W), if the backend doesn't yet support them, the API will return empty data — the frontend should handle this gracefully: "Insufficient data for this period" message.
- [ ] 4.3 — For short periods, the benchmark chart may show "Intraday data not available — showing daily close" if sub-daily data isn't available.

---

### Task 5: WebSocket Price Subscription for Portfolio
**Description:** When the Portfolio page loads, subscribe all position tickers to the WebSocket price feed so they get live updates during market hours.

**Subtasks:**
- [ ] 5.1 — In `frontend/src/pages/Portfolio/PortfolioPage.tsx`, add WebSocket subscription:
  ```tsx
  useEffect(() => {
    if (positions.length === 0) return;
    const tickers = positions.map((p) => p.ticker);

    // Connect to WebSocket and subscribe
    const ws = new WebSocket(`ws://localhost:8000/ws/prices`);
    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'subscribe', tickers }));
    };
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'price_update') {
        // Update positions with new prices
        setPositions((prev) => prev.map((p) => {
          const update = message.data?.find((u: any) => u.ticker === p.ticker);
          if (update) {
            return {
              ...p,
              current_price: update.current_price ?? p.current_price,
              day_change_pct: update.day_change_pct ?? p.day_change_pct,
              market_value: (update.current_price ?? p.current_price) * p.shares_held,
            };
          }
          return p;
        }));
      }
    };
    return () => ws.close();
  }, [positions.length]);  // Re-subscribe when position count changes
  ```

- [ ] 5.2 — Alternatively, if there's an existing `useWebSocket` hook or `wsManager` utility, use that instead of raw WebSocket. Check the existing codebase for a WebSocket utility pattern.

---

### Task 6: Refresh Button
**Description:** Add a Refresh button to the Portfolio page header.

**Subtasks:**
- [ ] 6.1 — In `PortfolioPage.tsx`, add a refresh button in the header area:
  ```tsx
  const [refreshing, setRefreshing] = useState(false);

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const tickers = positions.map((p) => p.ticker);
      await api.post('/api/v1/market-data/refresh-batch', { tickers });
      await loadData();
    } catch {
      // Silently fail
    } finally {
      setRefreshing(false);
    }
  }, [positions, loadData]);
  ```
  Render:
  ```tsx
  <button className={styles.refreshBtn} onClick={handleRefresh} disabled={refreshing}>
    {refreshing ? '↻ Refreshing...' : '↻ Refresh'}
  </button>
  ```

- [ ] 6.2 — In `PortfolioPage.module.css`, style the refresh button (same pattern as other header buttons).

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: BenchmarkChart uses Recharts LineChart (not raw SVG).
- [ ] AC-2: Portfolio line: solid accent blue, 2px. Benchmark line: dashed amber, 1.5px.
- [ ] AC-3: Hover tooltip shows date, portfolio value, benchmark value, and alpha.
- [ ] AC-4: Reference line at y=100 (starting value).
- [ ] AC-5: Chart legend clearly labels "Portfolio" and "SPY Benchmark".
- [ ] AC-6: X-axis labels readable, thinned at longer timeframes.
- [ ] AC-7: Chart responsive at 1024/1280/1600px.
- [ ] AC-8: ReturnMetrics/RiskMetrics use proper percentage formatting with +/- prefix.
- [ ] AC-9: Metrics panels stack on narrow viewports.
- [ ] AC-10: Attribution table shows "N positions with unknown sector" with refresh link when applicable.
- [ ] AC-11: Period pills include: 1D, 3D, 5D, 2W, 1M, 3M, 6M, YTD, 1Y, 3Y, ALL.
- [ ] AC-12: Short periods show graceful message if insufficient data.
- [ ] AC-13: Portfolio positions subscribe to WebSocket for live price updates.
- [ ] AC-14: Price updates from WebSocket reactively update the holdings table values.
- [ ] AC-15: Refresh button in Portfolio header triggers data refresh.
- [ ] AC-16: Refresh button shows loading state while refreshing.
- [ ] AC-17: No regressions on existing performance, allocation, or holdings functionality.

---

## FILES TOUCHED

**New files:**
- None

**Modified files:**
- `frontend/src/pages/Portfolio/Performance/BenchmarkChart.tsx` — Recharts rewrite with tooltips, legend, responsive
- `frontend/src/pages/Portfolio/Performance/BenchmarkChart.module.css` — remove SVG styles, add Recharts tooltip styles
- `frontend/src/pages/Portfolio/Performance/ReturnMetrics.tsx` — formatting audit, +/- prefix
- `frontend/src/pages/Portfolio/Performance/ReturnMetrics.module.css` — responsive stacking
- `frontend/src/pages/Portfolio/Performance/RiskMetrics.tsx` — formatting audit
- `frontend/src/pages/Portfolio/Performance/RiskMetrics.module.css` — responsive stacking
- `frontend/src/pages/Portfolio/Performance/AttributionTable.tsx` — unknown sector handling, refresh link
- `frontend/src/pages/Portfolio/Performance/AttributionTable.module.css` — unknown note styles
- `frontend/src/pages/Portfolio/Performance/PerformanceTab.tsx` — add short periods
- `frontend/src/pages/Portfolio/PortfolioPage.tsx` — WebSocket subscription, Refresh button
- `frontend/src/pages/Portfolio/PortfolioPage.module.css` — refresh button styles

---

## BUILDER PROMPT

> **Session 10D — Performance Frontend + Refresh Button + WebSocket Subscription**
>
> You are building session 10D of the Finance App v2.0 update.
>
> **What you're doing:** Six things: (1) Recharts rewrite of BenchmarkChart with Fidelity-quality tooltips/legend, (2) Formatting + responsive fix for ReturnMetrics/RiskMetrics, (3) Attribution table unknown sector handling, (4) Short timeframe periods, (5) WebSocket subscription for portfolio prices, (6) Refresh button.
>
> **Context:** Session 10C fixed backend data issues (startup refresh, after-hours refresh, day_change_pct format). The frontend now needs: a proper chart library for benchmarks, responsive panels, live price updates via WebSocket, and a refresh button.
>
> **Existing code:**
>
> `BenchmarkChart.tsx` (at `frontend/src/pages/Portfolio/Performance/BenchmarkChart.tsx`):
> - Currently renders raw SVG with `buildPath()` helper — no Recharts
> - Has `normalize(series)` function that converts to base-100 index
> - Takes `benchmark: BenchmarkResult | null` prop
> - `BenchmarkResult` has: `portfolio_series: DailySnapshot[]`, `benchmark_series: DailySnapshot[]`
> - `DailySnapshot`: `{ date: string, portfolio_value: number }`
> - **Replace entirely with Recharts LineChart**
>
> `PerformanceTab.tsx`:
> - `PERIODS = ['1M', '3M', '6M', 'YTD', '1Y', '3Y', 'ALL']` — **add short periods before these**
> - Fetches performance, benchmark, attribution on period change
> - Props: `selectedAccount`
>
> `AttributionTable.tsx`:
> - Shows sector allocation vs benchmark with effect columns
> - Unknown sectors appear when company profiles not fetched
>
> `PortfolioPage.tsx`:
> - State: positions, summary, accounts, selectedAccount, loading, showAddModal, showImportModal
> - `loadData()` fetches positions + summary + accounts
> - Header: account selector, Export, Import CSV, + Add Position
> - **No Refresh button, no WebSocket subscription**
> - WebSocket endpoint: `ws://localhost:8000/ws/prices` — accepts `{ type: "subscribe", tickers: [...] }`, sends `{ type: "price_update", data: [...] }`
>
> **Cross-cutting rules:**
> - Display Name Rule: Use `displayNames.ts` for backend keys.
> - Chart Quality: Fidelity-level — tooltips, crosshair, legends, responsive.
> - Data Format: Decimals for ratios. `fmtPct` multiplies by 100.
> - Scenario Order: Bear / Base / Bull.
>
> **Acceptance criteria:**
> 1. Recharts benchmark chart with tooltip, legend, reference line
> 2. Responsive panels
> 3. Attribution handles Unknown sectors with refresh link
> 4. Short periods: 1D, 3D, 5D, 2W
> 5. WebSocket subscription for live prices
> 6. Refresh button works
> 7. No regressions
>
> **Files to create:** None
> **Files to modify:** `BenchmarkChart.tsx/css`, `ReturnMetrics.tsx/css`, `RiskMetrics.tsx/css`, `AttributionTable.tsx/css`, `PerformanceTab.tsx`, `PortfolioPage.tsx/css`
>
> **Technical constraints:**
> - Recharts for charting (already loaded app-wide)
> - CSS modules, dark theme variables
> - WebSocket: `ws://localhost:8000/ws/prices`, subscribe message format: `{ type: "subscribe", tickers }`, update format: `{ type: "price_update", data: [{ ticker, current_price, day_change_pct, ... }] }`
> - `fmtPct`, `fmtDollar`, `gainColor` from `../types`
> - `api.post` for refresh batch (may need endpoint verification)
