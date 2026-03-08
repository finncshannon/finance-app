# Session 10F — Income + Allocation + Transactions Frontend
## Phase 10: Portfolio

**Priority:** Normal
**Type:** Frontend Only
**Depends On:** 10E (income backend with yield-on-cost, ETF classification), Phase 7 events backend (for upcoming dividends — use fallback if not built)
**Spec Reference:** `specs/phase10_portfolio_remaining.md` → Areas 1 frontend, 2 frontend (2A–2E), 3

---

## SCOPE SUMMARY

Upgrade the Income tab with enhanced summary metrics (projected income, yield-on-cost), stacked monthly dividend chart by ticker, monthly breakdown calendar, yield-on-cost per position table, upcoming dividends integration (with Phase 7 fallback), and a meaningful empty state for non-dividend portfolios. Fix allocation donut/treemap to handle "ETF" as a valid sector with distinct color. Add "Import Transactions" button to the Transactions tab.

---

## TASKS

### Task 1: Allocation — ETF Sector Handling
**Description:** The sector donut and treemap need to handle "ETF" as a valid sector (from 10E's backend ETF classification) with its own distinct color.

**Subtasks:**
- [ ] 1.1 — In `frontend/src/pages/Portfolio/Allocation/SectorDonut.tsx`, add "ETF" to the sector color map:
  ```tsx
  const SECTOR_COLORS: Record<string, string> = {
    // ... existing sector colors
    'ETF': '#8B5CF6',  // Purple — visually distinct from equity sectors
  };
  ```
  Ensure the donut renders "ETF" as a proper sector slice, not lumped into "Other" or "Unknown".

- [ ] 1.2 — In `frontend/src/pages/Portfolio/Allocation/Treemap.tsx`, add ETF grouping. ETFs should appear as their own group in the treemap with the same purple color. Verify the label shows "ETF" not "Financial Services".

- [ ] 1.3 — In both components, handle the case where sector is still "Unknown" for some positions — show "Unknown (N)" with a muted color, consistent with 10D's attribution handling.

---

### Task 2: Income Summary Header Enhancement
**Description:** Enhance the income summary with projected annual income, yield-on-cost, yield-on-market, and income growth.

**Subtasks:**
- [ ] 2.1 — In `frontend/src/pages/Portfolio/Income/IncomeTab.tsx`, update the data fetch to use the enhanced income endpoint (10E returns yield-on-cost and projections):
  ```tsx
  const [incomeData, setIncomeData] = useState<EnhancedIncomeResult | null>(null);

  // Fetch from enhanced endpoint
  api.get<EnhancedIncomeResult>(`/api/v1/portfolio/income${accountParam}`)
    .then(setIncomeData);
  ```

- [ ] 2.2 — Render enhanced summary metrics at the top:
  ```tsx
  <div className={styles.summaryGrid}>
    <div className={styles.summaryCard}>
      <span className={styles.summaryLabel}>Annual Income</span>
      <span className={styles.summaryValue}>{fmtDollar(summary.total_annual_income)}</span>
    </div>
    <div className={styles.summaryCard}>
      <span className={styles.summaryLabel}>Monthly Income</span>
      <span className={styles.summaryValue}>{fmtDollar(summary.total_monthly_income)}</span>
    </div>
    <div className={styles.summaryCard}>
      <span className={styles.summaryLabel}>Yield on Cost</span>
      <span className={styles.summaryValue}>{fmtPct(summary.yield_on_cost)}</span>
    </div>
    <div className={styles.summaryCard}>
      <span className={styles.summaryLabel}>Yield on Market</span>
      <span className={styles.summaryValue}>{fmtPct(summary.yield_on_market)}</span>
    </div>
    <div className={styles.summaryCard}>
      <span className={styles.summaryLabel}>Dividend Positions</span>
      <span className={styles.summaryValue}>{summary.dividend_position_count} / {summary.total_position_count}</span>
    </div>
  </div>
  ```

- [ ] 2.3 — Add YTD income (existing computation stays) as part of the summary row.

---

### Task 3: Stacked Monthly Dividend Chart
**Description:** Upgrade the DividendChart from simple bars to stacked bars by ticker showing which stocks contribute to each month's income.

**Subtasks:**
- [ ] 3.1 — In `frontend/src/pages/Portfolio/Income/DividendChart.tsx`, restructure chart data to group by month with per-ticker breakdown:
  ```tsx
  // Build monthly data: { month: 'Jan', AAPL: 52, JNJ: 45, KO: 45, ... }
  const chartData = useMemo(() => {
    const months = Array.from({ length: 12 }, (_, i) => ({
      month: MONTH_LABELS[i],
      ...Object.fromEntries(topTickers.map((t) => [t, 0])),
      other: 0,
    }));
    // Fill from dividend transactions
    for (const tx of divTxns) {
      const monthIdx = new Date(tx.transaction_date).getMonth();
      const ticker = tx.ticker;
      if (topTickers.includes(ticker)) {
        months[monthIdx][ticker] += tx.total_amount ?? 0;
      } else {
        months[monthIdx].other += tx.total_amount ?? 0;
      }
    }
    return months;
  }, [divTxns, topTickers]);
  ```
  Cap at top 8 tickers by total income contribution; group the rest as "Other".

- [ ] 3.2 — Render as Recharts stacked BarChart:
  ```tsx
  <ResponsiveContainer width="100%" height={250}>
    <BarChart data={chartData}>
      <CartesianGrid strokeDasharray="3 3" stroke="#262626" vertical={false} />
      <XAxis dataKey="month" tick={{ fill: '#A3A3A3', fontSize: 11 }} stroke="#333" />
      <YAxis tickFormatter={(v) => `$${v}`} tick={{ fill: '#A3A3A3', fontSize: 11 }} stroke="#333" />
      <Tooltip content={<MonthlyTooltip />} />
      <Legend />
      {topTickers.map((ticker, i) => (
        <Bar key={ticker} dataKey={ticker} stackId="income" fill={TICKER_COLORS[i]} />
      ))}
      {hasOther && <Bar dataKey="other" stackId="income" name="Other" fill="#666" />}
    </BarChart>
  </ResponsiveContainer>
  ```

- [ ] 3.3 — Create a color palette for stacked tickers (8 distinct colors).

---

### Task 4: Monthly Income Calendar/Breakdown
**Description:** Add a month-by-month breakdown table below the chart showing which stocks pay in each month.

**Subtasks:**
- [ ] 4.1 — Create `frontend/src/pages/Portfolio/Income/DividendCalendar.tsx`:
  ```tsx
  interface Props {
    divTxns: Transaction[];
  }
  ```
  Groups transactions by month and shows: month name, total income for that month, and a list of contributing tickers with amounts.

- [ ] 4.2 — Render as a compact table/list:
  ```tsx
  {monthlyData.map((m) => (
    <div key={m.month} className={styles.calendarRow}>
      <span className={styles.calendarMonth}>{m.monthLabel}</span>
      <span className={styles.calendarTotal}>{fmtDollar(m.total)}</span>
      <span className={styles.calendarDetail}>
        {m.tickers.map((t) => `${t.ticker} (${fmtDollar(t.amount)})`).join(', ')}
      </span>
    </div>
  ))}
  ```

- [ ] 4.3 — Create `DividendCalendar.module.css` with compact row styles.

---

### Task 5: Yield-on-Cost per Position Table
**Description:** Enhance the income positions table with cost basis and yield-on-cost columns.

**Subtasks:**
- [ ] 5.1 — In `IncomeTab.tsx`, render the positions table from the enhanced income data (10E returns `positions` array with `yield_on_cost`, `cost_basis_per_share`, `market_yield`):
  ```tsx
  <table className={styles.positionsTable}>
    <thead>
      <tr>
        <th>Ticker</th>
        <th>Shares</th>
        <th>Div Rate</th>
        <th>Annual Income</th>
        <th>Cost Basis</th>
        <th>Yield on Cost</th>
        <th>Market Yield</th>
      </tr>
    </thead>
    <tbody>
      {incomeData.positions.map((p) => (
        <tr key={p.ticker}>
          <td>{p.ticker}</td>
          <td>{fmtShares(p.shares)}</td>
          <td>{fmtDollar(p.dividend_rate)}</td>
          <td>{fmtDollar(p.annual_income)}</td>
          <td>{fmtDollar(p.cost_basis_per_share)}</td>
          <td className={styles.yocValue}>{p.yield_on_cost != null ? fmtPct(p.yield_on_cost) : '—'}</td>
          <td>{p.market_yield != null ? fmtPct(p.market_yield) : '—'}</td>
        </tr>
      ))}
    </tbody>
  </table>
  ```

- [ ] 5.2 — Add sortability to the table (sort by yield_on_cost to find best income positions).

---

### Task 6: Upcoming Dividends Component
**Description:** Replace the "Phase 5" placeholder with real upcoming dividend events from the events system. Gracefully handle missing events system.

**Subtasks:**
- [ ] 6.1 — Create `frontend/src/pages/Portfolio/Income/UpcomingDividends.tsx`:
  ```tsx
  interface Props {
    selectedAccount: string;
  }
  ```
  Fetches from `GET /api/v1/portfolio/income/upcoming-dividends?account=...` (from 10E).

- [ ] 6.2 — Render upcoming events:
  ```tsx
  {upcoming.length > 0 ? (
    <div className={styles.upcomingList}>
      {upcoming.map((event, i) => (
        <div key={i} className={styles.upcomingRow}>
          <span className={styles.upcomingDate}>{formatDate(event.event_date)}</span>
          <span className={styles.upcomingTicker}>{event.ticker}</span>
          <span>{fmtDollar(event.amount_per_share)}/share</span>
          <span>{event.shares_held} shares</span>
          <span className={styles.upcomingIncome}>{fmtDollar(event.expected_income)}</span>
        </div>
      ))}
    </div>
  ) : (
    <div className={styles.upcomingEmpty}>
      {message || 'No upcoming dividend events found.'}
    </div>
  )}
  ```

- [ ] 6.3 — **Phase 7 fallback:** If the response has `message: "Events system not available"`, show:
  ```tsx
  <div className={styles.upcomingPlaceholder}>
    Enable events to see upcoming dividends.
  </div>
  ```
  This follows the Planner directive: "If Phase 7 hasn't been built, show a placeholder with 'Enable events to see upcoming dividends' instead of crashing."

- [ ] 6.4 — Create `UpcomingDividends.module.css`.

---

### Task 7: Non-Dividend Portfolio Empty State
**Description:** When the portfolio has no dividend-paying positions, show a meaningful empty state instead of a blank tab.

**Subtasks:**
- [ ] 7.1 — In `IncomeTab.tsx`, when `incomeData.summary.dividend_position_count === 0`:
  ```tsx
  <div className={styles.emptyState}>
    <div className={styles.emptyIcon}>📈</div>
    <h3 className={styles.emptyTitle}>No Dividend Income</h3>
    <p className={styles.emptyText}>
      Your current holdings generate returns through capital appreciation.
      None of your {incomeData.summary.total_position_count} positions currently pay dividends.
    </p>
  </div>
  ```

---

### Task 8: Transactions Tab — Import Button
**Description:** Add an "Import Transactions" button to the Transactions tab header that opens the ImportModal pre-configured for transaction mode.

**Subtasks:**
- [ ] 8.1 — In `frontend/src/pages/Portfolio/Transactions/TransactionsTab.tsx`, add import button and modal state:
  ```tsx
  const [showImport, setShowImport] = useState(false);
  ```
  In the header:
  ```tsx
  <button className={styles.importBtn} onClick={() => setShowImport(true)}>
    📥 Import Transactions
  </button>
  ```
  Render modal with `defaultImportType`:
  ```tsx
  {showImport && (
    <ImportModal
      onClose={() => setShowImport(false)}
      onSuccess={() => { setShowImport(false); onRefresh(); }}
      defaultImportType="transactions"
    />
  )}
  ```

- [ ] 8.2 — Import `ImportModal` from `../Holdings/ImportModal` (it accepts `defaultImportType` prop from 10B).

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: Allocation donut has "ETF" as a distinct sector with purple color.
- [ ] AC-2: Treemap shows ETF positions in their own group.
- [ ] AC-3: Income summary shows: Annual Income, Monthly Income, Yield on Cost, Yield on Market, Dividend Position count.
- [ ] AC-4: Monthly dividend chart is stacked by ticker (top 8 + "Other").
- [ ] AC-5: Chart tooltip shows per-ticker breakdown for the hovered month.
- [ ] AC-6: Monthly calendar/breakdown table shows month, total, and contributing tickers.
- [ ] AC-7: Positions table includes Cost Basis and Yield on Cost columns.
- [ ] AC-8: Positions table sortable by yield-on-cost.
- [ ] AC-9: Upcoming Dividends section shows ex-dividend events with shares and expected income.
- [ ] AC-10: Upcoming Dividends shows fallback message when events system not available: "Enable events to see upcoming dividends."
- [ ] AC-11: Non-dividend portfolios show meaningful empty state (not blank/broken).
- [ ] AC-12: "Import Transactions" button on Transactions tab opens ImportModal in transactions mode.
- [ ] AC-13: Import modal pre-selects "Transactions" as import type when opened from Transactions tab.
- [ ] AC-14: No regressions on existing income, allocation, or transaction functionality.

---

## FILES TOUCHED

**New files:**
- `frontend/src/pages/Portfolio/Income/DividendCalendar.tsx` — monthly breakdown component
- `frontend/src/pages/Portfolio/Income/DividendCalendar.module.css` — calendar styles
- `frontend/src/pages/Portfolio/Income/UpcomingDividends.tsx` — upcoming dividends component (with Phase 7 fallback)
- `frontend/src/pages/Portfolio/Income/UpcomingDividends.module.css` — upcoming styles

**Modified files:**
- `frontend/src/pages/Portfolio/Allocation/SectorDonut.tsx` — add ETF color, handle Unknown
- `frontend/src/pages/Portfolio/Allocation/Treemap.tsx` — add ETF grouping
- `frontend/src/pages/Portfolio/Income/IncomeTab.tsx` — enhanced summary, yield-on-cost positions table, integrate DividendCalendar + UpcomingDividends, non-dividend empty state
- `frontend/src/pages/Portfolio/Income/IncomeTab.module.css` — summary grid, positions table, empty state styles
- `frontend/src/pages/Portfolio/Income/DividendChart.tsx` — stacked bars by ticker
- `frontend/src/pages/Portfolio/Income/DividendChart.module.css` — stacked bar color palette
- `frontend/src/pages/Portfolio/Transactions/TransactionsTab.tsx` — add Import Transactions button + ImportModal integration

---

## BUILDER PROMPT

> **Session 10F — Income + Allocation + Transactions Frontend**
>
> You are building session 10F of the Finance App v2.0 update.
>
> **What you're doing:** Major Income tab upgrade (enhanced summary, stacked chart, monthly calendar, yield-on-cost table, upcoming dividends, non-dividend empty state), ETF handling in allocation views, and Import Transactions button on the Transactions tab.
>
> **Context:** Session 10E built the backend: ETF classification, enhanced income with yield-on-cost, dividend growth, upcoming dividends endpoint. Phase 7 may or may not have built the events system — the upcoming dividends endpoint handles this gracefully.
>
> **Existing code:**
>
> `IncomeTab.tsx` (at `frontend/src/pages/Portfolio/Income/IncomeTab.tsx`):
> - Props: `selectedAccount`
> - State: `income` (IncomeResult), `divTxns` (Transaction[]), `loading`, `error`, `sortKey`, `sortDir`
> - Fetches: `GET /portfolio/income` + `GET /portfolio/transactions?type=DIVIDEND`
> - Renders: summary section (annual/monthly/weighted yield/YTD), DividendChart, dividend history table
> - Summary has 4 metrics; YTD computed from current-year transactions
> - Placeholder text: "Upcoming Dividend Events" section says "Phase 5" — **replace with real component**
>
> `DividendChart.tsx` — basic monthly bar chart, NOT stacked by ticker. Uses Recharts BarChart with single `<Bar>`.
>
> `SectorDonut.tsx` (at `frontend/src/pages/Portfolio/Allocation/SectorDonut.tsx`):
> - Has `SECTOR_COLORS` record mapping sector names to hex colors
> - Does NOT currently have "ETF" as a key
>
> `Treemap.tsx` — groups positions by sector. No special ETF handling.
>
> `TransactionsTab.tsx` (at `frontend/src/pages/Portfolio/Transactions/TransactionsTab.tsx`):
> - Props: `accounts`, `onRefresh`
> - Has "Record Transaction" button opening `RecordTransactionModal`
> - No Import Transactions button
>
> `ImportModal.tsx` (after 10B): accepts `defaultImportType?: 'positions' | 'transactions'` prop.
>
> **Cross-cutting rules:**
> - Display Name Rule: Use `displayNames.ts` for backend keys (use `displayTransactionType` for TX type badges).
> - Chart Quality: Fidelity-level stacked charts with tooltips.
> - Data Format: Decimals for ratios. `fmtPct` multiplies by 100.
>
> **Task 1: ETF in Allocation**
> - SectorDonut: add `'ETF': '#8B5CF6'` to SECTOR_COLORS
> - Treemap: ETF appears as own group
> - Handle "Unknown" with muted color
>
> **Task 2: Income Summary Enhancement**
> - Fetch from enhanced endpoint (returns summary with yield_on_cost, yield_on_market, projected)
> - Render 5 summary cards: Annual Income, Monthly, Yield on Cost, Yield on Market, Dividend Position count
>
> **Task 3: Stacked Dividend Chart**
> - Group dividend transactions by month + ticker
> - Top 8 tickers by contribution, rest as "Other"
> - Recharts stacked BarChart with per-ticker `<Bar>` components
> - Tooltip shows per-ticker breakdown
>
> **Task 4: Monthly Calendar**
> - New `DividendCalendar` component: rows per month showing total + contributing tickers
>
> **Task 5: Yield-on-Cost Table**
> - Positions table with: Ticker, Shares, Div Rate, Annual Income, Cost Basis, Yield on Cost, Market Yield
> - Sortable by yield-on-cost
>
> **Task 6: Upcoming Dividends**
> - New `UpcomingDividends` component: fetches `GET /income/upcoming-dividends`
> - Shows events with date, ticker, amount/share, shares held, expected income
> - **Fallback:** if response message says "Events system not available", show: "Enable events to see upcoming dividends"
>
> **Task 7: Non-Dividend Empty State**
> - When `dividend_position_count === 0`: show icon + "No Dividend Income" + explanation text
>
> **Task 8: Import Transactions Button**
> - Add to TransactionsTab header: "📥 Import Transactions" button
> - Opens `ImportModal` with `defaultImportType="transactions"`
>
> **Acceptance criteria:**
> 1. ETF sector in donut/treemap with purple color
> 2. Enhanced income summary with 5 metrics
> 3. Stacked chart by ticker (top 8 + Other)
> 4. Monthly calendar breakdown
> 5. Yield-on-cost table, sortable
> 6. Upcoming dividends with events or fallback placeholder
> 7. Non-dividend empty state
> 8. Import Transactions button works
> 9. No regressions
>
> **Files to create:** `DividendCalendar.tsx/css`, `UpcomingDividends.tsx/css`
> **Files to modify:** `SectorDonut.tsx`, `Treemap.tsx`, `IncomeTab.tsx/css`, `DividendChart.tsx/css`, `TransactionsTab.tsx`
>
> **Technical constraints:**
> - Recharts for stacked bar chart (already loaded)
> - CSS modules, dark theme variables
> - `fmtDollar`, `fmtPct`, `fmtShares` from `../types`
> - Income positions data from 10E endpoint: `{ positions: [{ ticker, shares, dividend_rate, annual_income, monthly_income, cost_basis_per_share, yield_on_cost, market_yield }], summary: { total_annual_income, total_monthly_income, yield_on_cost, yield_on_market, dividend_position_count, total_position_count } }`
> - Upcoming dividends: `GET /income/upcoming-dividends` returns `{ upcoming: [...], message?: string }`
> - `ImportModal` from `../Holdings/ImportModal` accepts `defaultImportType` prop (from 10B)
> - Top 8 tickers: sort all dividend-paying tickers by total annual income desc, take first 8, group rest as "Other"
> - Stacked bar colors: use a palette of 8 visually distinct colors for tickers
