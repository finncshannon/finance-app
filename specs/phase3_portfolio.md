# Phase 3 — Portfolio Module
> Designer Agent | February 26, 2026
> Status: COMPLETE — APPROVED BY FINN
> Depends on: Phase 0A-0E (foundation specs), Phase 0D (UI/UX Framework)

---

## Overview

The Portfolio module tracks holdings, measures performance, and connects
positions to the rest of the app (Model Builder valuations, Scanner discovery,
Research analysis). It replaces the need to check Fidelity's dashboard by
providing better analytics in a unified interface.

**Key decisions:**
- Manual entry + broker CSV import + future broker API integration
- Institutional-grade performance metrics (TWR, MWRR, Sharpe, Sortino, etc.)
- Per-position detail: value, cost basis, shares, weight, gains (absolute + %)
- Benchmark comparison vs S&P 500 (and custom benchmarks)
- Sector/industry attribution analysis
- Live price updates via WebSocket (positions are Tier 1 refresh priority)

---

## Part 1: Position Management

### 1.1 Data Entry Methods

**Method 1: Manual Entry**

Always available, no dependencies.

```
ADD POSITION DIALOG
────────────────────────────────────────
  Ticker:        [AAPL          ] (autocomplete)
  Shares:        [100           ]
  Cost Basis:    [$ 142.50      ] per share
  Date Acquired: [2023-06-15    ]
  Account:       [Fidelity IRA ▼] (optional)
  Notes:         [               ] (optional)

  [Cancel]                    [Add Position]
────────────────────────────────────────
```

- Ticker autocomplete from scanner universe
- Cost basis per share (app calculates total cost)
- Date acquired used for holding period and tax lot tracking
- Account tag for multi-account organization
- Multiple lots for same ticker: each entry creates a separate lot

**Method 2: CSV / Excel Import**

```
IMPORT HOLDINGS
────────────────────────────────────────
  Source: [Fidelity ▼]  [Schwab]  [TD Ameritrade]  [Generic CSV]

  Drag & drop file or [Browse...]

  Preview:
  ┌──────────────────────────────────────────────────┐
  │ Ticker  Shares   Cost Basis  Date       Account  │
  │ AAPL    100      $142.50     2023-06-15 IRA      │
  │ MSFT    50       $285.30     2022-11-20 Taxable  │
  │ GOOGL   25       $98.45      2024-01-08 IRA      │
  │ ...                                              │
  └──────────────────────────────────────────────────┘

  Recognized: 47 positions across 2 accounts
  Warnings: 2 tickers not in universe (will be added)

  [Cancel]                    [Import All]
────────────────────────────────────────
```

Supported formats:
- Fidelity: CSV export from Positions page
- Schwab: CSV export from All Accounts → Positions
- TD Ameritrade / Schwab merged: CSV export
- Interactive Brokers: Activity Statement CSV
- Generic CSV: user maps columns (Ticker, Shares, Cost, Date)

Column mapping for Generic CSV:
```
Auto-detect common column names:
  "Symbol", "Ticker", "Sym" → Ticker
  "Quantity", "Shares", "Qty" → Shares
  "Cost Basis", "Avg Cost", "Price Paid" → Cost Basis
  "Date", "Purchase Date", "Acquired" → Date

If auto-detect fails, user maps manually:
  Column A → [Ticker ▼]
  Column B → [Shares ▼]
  Column C → [Cost Basis ▼]
  ...
```

**Method 3: Broker API (Future)**

Architecture designed to support direct broker integration:

```
BROKER CONNECTION (Future)
────────────────────────────────────────
  Settings → Portfolio → Connected Accounts

  ┌──────────────────────────────────────┐
  │  Fidelity          [Connect]         │
  │  Schwab            [Connect]         │
  │  Interactive Brokers [Connect]       │
  │  Alpaca            [Connect]         │
  └──────────────────────────────────────┘

  When connected:
  - Positions sync automatically (configurable frequency)
  - Transactions import in real-time or daily
  - Manual override always available (broker data as base, user edits on top)
```

Provider-agnostic design in backend:

```python
# backend/providers/base_broker.py

class BaseBrokerProvider:
    def authenticate(self, credentials) -> bool
    def get_positions(self) -> list[Position]
    def get_transactions(self, since: date) -> list[Transaction]
    def get_account_info(self) -> AccountInfo
    def sync(self) -> SyncResult

# Future implementations:
# providers/fidelity.py
# providers/schwab.py
# providers/alpaca.py
```

Not built for MVP, but the data model and API endpoints support it
without schema changes.

### 1.2 Position Editing

```
Any position can be edited after entry:
  - Adjust shares (for splits, corrections)
  - Adjust cost basis (for wash sales, corporate actions)
  - Add/remove lots
  - Change account tag
  - Add notes

Edit history preserved — every change logged with timestamp.
```

### 1.3 Transaction Log

Every portfolio action creates a transaction record:

```
TRANSACTION TYPES:
  BUY        — acquire shares
  SELL       — dispose shares (triggers realized gain/loss)
  DIVIDEND   — cash dividend received
  DRIP       — dividend reinvested (creates new lot)
  SPLIT      — stock split (adjusts shares and cost basis)
  SPINOFF    — new position from corporate action
  TRANSFER   — move between accounts
  ADJUSTMENT — manual correction

Each transaction records:
  - Type, ticker, date, shares, price, total amount
  - Fees/commission (if applicable)
  - Account
  - Auto-generated or manual flag
  - Notes
```

---

## Part 2: Portfolio Views

### 2.1 Holdings Table (Primary View)

The main portfolio view — all positions in a Bloomberg-style table.

```
PORTFOLIO HOLDINGS
────────────────────────────────────────────────────────────────────────────────
                                                        Today's
Ticker  Name          Shares  Avg Cost  Mkt Price  Value      Cost Basis  Gain/Loss    Gain %   Weight  
────────────────────────────────────────────────────────────────────────────────
AAPL    Apple Inc     100     $142.50   $182.52    $18,252    $14,250     +$4,002      +28.1%   22.4%
MSFT    Microsoft     50      $285.30   $415.80    $20,790    $14,265     +$6,525      +45.7%   25.5%
GOOGL   Alphabet      25      $98.45    $174.20    $4,355     $2,461      +$1,894      +77.0%   5.3%
META    Meta Platf    30      $320.00   $562.40    $16,872    $9,600      +$7,272      +75.8%   20.7%
JNJ     Johnson&J     75      $158.20   $152.80    $11,460    $11,865     -$405        -3.4%    14.1%
VZ      Verizon       200     $38.50    $48.90     $9,780     $7,700      +$2,080      +27.0%   12.0%
────────────────────────────────────────────────────────────────────────────────
TOTAL                                              $81,509    $60,141     +$21,368     +35.5%   100%
────────────────────────────────────────────────────────────────────────────────
```

**Column details:**
- Ticker + Name: left-aligned, Inter
- Shares: right-aligned, JetBrains Mono
- Avg Cost: volume-weighted average across all lots
- Mkt Price: live from WebSocket (Tier 1, 60s refresh)
- Value: Shares × Mkt Price
- Cost Basis: Shares × Avg Cost (total invested)
- Gain/Loss: Value - Cost Basis (absolute dollars)
  - Green for gains, red for losses
- Gain %: (Value - Cost Basis) / Cost Basis
  - Green for gains, red for losses
- Weight: Value / Total Portfolio Value
- Today's Change column (optional, toggleable):
  Day change in dollars and percent per position

**Table interactions:**
- Click row → expand to show individual lots, transaction history
- Double-click → open in Model Builder
- Right-click → context menu (same as Scanner + Sell, Edit, Remove)
- Sortable by any column
- Groupable by: Account, Sector, Industry

### 2.2 Summary Header

Above the holdings table, a persistent summary bar:

```
PORTFOLIO SUMMARY
────────────────────────────────────────────────────────────────────────
  Total Value          Day Change           Total Gain/Loss
  $81,509              +$342 (+0.42%)       +$21,368 (+35.5%)

  Positions: 6    Accounts: 2    Dividend Yield (weighted): 1.24%
────────────────────────────────────────────────────────────────────────
```

- Total Value: large number, 24px JetBrains Mono
- Day Change: colored green/red, 18px JetBrains Mono
- Total Gain/Loss: colored green/red, 18px JetBrains Mono
- Secondary metrics: 12px Inter, --text-secondary

### 2.3 Lot-Level Detail (Expanded Row)

When clicking a position row:

```
AAPL — Apple Inc. — 100 shares
────────────────────────────────────────────────────────────────
  LOT DETAIL
  ┌────────────────────────────────────────────────────────────┐
  │ Lot    Date Acquired  Shares  Cost/Share  Cost     Gain    │
  │ #1     2023-06-15     60      $135.00     $8,100   +42.6%  │
  │ #2     2024-02-20     40      $153.75     $6,150   +18.7%  │
  └────────────────────────────────────────────────────────────┘

  RECENT TRANSACTIONS
  ┌────────────────────────────────────────────────────────────┐
  │ Date        Type      Shares  Price    Amount              │
  │ 2024-11-15  DIVIDEND  —       $0.25    +$25.00            │
  │ 2024-08-15  DIVIDEND  —       $0.25    +$25.00            │
  │ 2024-02-20  BUY       40      $153.75  -$6,150.00         │
  │ 2023-06-15  BUY       60      $135.00  -$8,100.00         │
  └────────────────────────────────────────────────────────────┘

  Holding Period (Lot #1): 2y 8m — Long-term capital gains
  Holding Period (Lot #2): 1y 0m — Long-term capital gains

  [Edit Position]  [Record Transaction]  [Open in Model Builder]
────────────────────────────────────────────────────────────────
```

Holding period classification:
- < 1 year: "Short-term capital gains" (--text-secondary)
- ≥ 1 year: "Long-term capital gains" (--color-positive, subtle)

---

## Part 3: Allocation & Breakdown Views

### 3.1 Sector Allocation

```
SECTOR ALLOCATION
────────────────────────────────────────
  ┌──────────────────────────────────┐
  │                                  │
  │         DONUT CHART              │
  │    (sectors as colored arcs)     │
  │                                  │
  │       Total: $81,509             │
  │                                  │
  └──────────────────────────────────┘

  Technology        $60,269    74.0%   ████████████████████
  Healthcare        $11,460    14.1%   ████
  Communication     $9,780     12.0%   ███
────────────────────────────────────────
```

Donut chart colors: monochrome shades + blue accent for largest sector.
Keep it tasteful — not a rainbow. Use opacity variants of --accent-primary
and --text-secondary for differentiation.

### 3.2 Treemap View

Alternative visualization showing position sizes as proportional rectangles:

```
┌──────────────────────┬────────────┐
│                      │            │
│      MSFT 25.5%      │  AAPL      │
│      +45.7%          │  22.4%     │
│                      │  +28.1%    │
├──────────────────────┤            │
│                      ├────────────┤
│      META 20.7%      │  JNJ 14.1% │
│      +75.8%          │  -3.4%    │
│                      ├────────────┤
│                      │ VZ   12.0% │
├──────────────────────┤ +27.0%    │
│  GOOGL 5.3%  +77.0%  │           │
└──────────────────────┴────────────┘
```

- Rectangle size proportional to position weight
- Background color intensity proportional to gain/loss
  (deeper green = bigger gain, deeper red = bigger loss)
- Shows ticker, weight, and gain % in each rectangle
- Hover: full position details tooltip

### 3.3 Account View

Group positions by account:

```
ACCOUNT BREAKDOWN
────────────────────────────────────────────────────────────────
  Fidelity IRA                    $45,397    55.7%
    AAPL    100 shares   $18,252
    GOOGL    25 shares    $4,355
    JNJ      75 shares   $11,460
    VZ      200 shares    $9,780
    + 1 more position

  Fidelity Taxable                $36,112    44.3%
    MSFT     50 shares   $20,790
    META     30 shares   $16,872

  ──────────────────────────────────────────────
  Total across all accounts:      $81,509
────────────────────────────────────────────────────────────────
```

---

## Part 4: Performance Analytics

### 4.1 Return Metrics

```
PERFORMANCE METRICS
────────────────────────────────────────────────────────────────────────

  TIME-WEIGHTED RETURN (TWR)
  Measures portfolio performance independent of cash flows.
  Eliminates the effect of deposits/withdrawals.

    1M      3M      6M      YTD     1Y      3Y (ann)  Since Inception
    +2.4%   +8.1%   +14.2%  +12.8%  +28.3%  +18.5%    +35.5%

  MONEY-WEIGHTED RETURN (MWRR / IRR)
  Measures actual investor return, accounting for timing of cash flows.
  Reflects when you bought and sold.

    Since Inception: +31.2%  (annualized: +14.8%)

  COMPARISON TO TWR:
  "MWRR of 31.2% trails TWR of 35.5%, indicating that on average
   you added capital at higher prices (bought more as market rose)."
────────────────────────────────────────────────────────────────────────
```

**TWR Calculation:**
```
Daily portfolio returns excluding cash flows:
  R_daily = (V_end - V_start - CashFlow) / V_start
  TWR = Π(1 + R_daily) - 1 over the period
  Annualized TWR = (1 + TWR)^(365/days) - 1
```

**MWRR Calculation:**
```
Solve for r in:
  Σ [CashFlow_t / (1 + r)^t] = Current Value
Where CashFlow_t = deposits (positive) and withdrawals (negative)
Uses Newton-Raphson or similar numerical solver.
```

### 4.2 Benchmark Comparison

```
BENCHMARK COMPARISON
────────────────────────────────────────────────────────────────────────

  ┌──────────────────────────────────────────────────────────────┐
  │  PERFORMANCE CHART (Line)                                     │
  │                                                               │
  │  $140 ─                                    ╱──── Portfolio    │
  │  $130 ─                              ╱────╱                   │
  │  $120 ─                        ╱────╱  ╱──── S&P 500         │
  │  $110 ─                  ╱────╱──────╱                        │
  │  $100 ─ ───────────╱────╱                                     │
  │         Jan  Mar  May  Jul  Sep  Nov  Jan  Mar                │
  │                                                               │
  │  Period: [1M] [3M] [6M] [YTD] [1Y] [3Y] [ALL]              │
  └──────────────────────────────────────────────────────────────┘

  Indexed to $100 at start of period.
  Portfolio line: --accent-primary (blue, 2px)
  Benchmark line: --text-secondary (gray, 1.5px)
────────────────────────────────────────────────────────────────────────

  BENCHMARK SUMMARY
  ────────────────────────────────────────
                Portfolio    S&P 500    Alpha
  1 Month       +2.4%       +1.8%      +0.6%
  3 Month       +8.1%       +6.2%      +1.9%
  YTD           +12.8%      +9.5%      +3.3%
  1 Year        +28.3%      +22.1%     +6.2%
  Since Incept  +35.5%      +26.8%     +8.7%
  ────────────────────────────────────────
  Alpha = Portfolio TWR - Benchmark TWR
  Green when positive, red when negative.
```

**Benchmark options:**
- S&P 500 (default)
- Russell 3000
- Nasdaq Composite
- DJIA
- Custom: any ETF ticker (e.g., QQQ, XLK, VTV)

Benchmark data sourced from Yahoo Finance, cached in market_data table.

### 4.3 Risk Metrics

```
RISK ANALYSIS
────────────────────────────────────────────────────────────────────────

  Metric                   Portfolio    S&P 500     Interpretation
  ─────────────────────────────────────────────────────────────────
  Sharpe Ratio (1Y)        1.42        1.18        Above benchmark ●
  Sortino Ratio (1Y)       1.87        1.45        Above benchmark ●
  Max Drawdown (1Y)        -8.2%       -10.5%      Less severe ●
  Beta (vs S&P 500)        1.12        1.00        Slightly aggressive
  Volatility (ann.)        16.8%       15.2%       Slightly higher
  Tracking Error           4.2%        —
  Information Ratio        1.48        —

  ● = favorable compared to benchmark
────────────────────────────────────────────────────────────────────────
```

**Metric definitions:**
```
Sharpe Ratio = (Portfolio Return - Risk-Free Rate) / Portfolio Std Dev
  Measures risk-adjusted return. Higher = better.
  > 1.0 is good, > 2.0 is excellent.

Sortino Ratio = (Portfolio Return - Risk-Free Rate) / Downside Std Dev
  Like Sharpe but only penalizes downside volatility.
  Better measure when returns are asymmetric.

Max Drawdown = Largest peak-to-trough decline in portfolio value
  Measures worst-case loss. Smaller (less negative) = better.

Beta = Covariance(Portfolio, Benchmark) / Variance(Benchmark)
  Portfolio sensitivity to market moves.
  1.0 = moves with market, >1.0 = amplifies, <1.0 = dampens.

Volatility = Annualized standard deviation of daily returns
  Measures return dispersion. Lower = smoother ride.

Tracking Error = Std Dev of (Portfolio Return - Benchmark Return)
  How much portfolio deviates from benchmark. Lower = more index-like.

Information Ratio = (Portfolio Return - Benchmark Return) / Tracking Error
  Active return per unit of active risk. Higher = better stock picking.
```

### 4.4 Attribution Analysis

Where are returns coming from?

```
SECTOR ATTRIBUTION
────────────────────────────────────────────────────────────────────────
                   Port     Bench    Port      Bench     Allocation  Selection
Sector             Weight   Weight   Return    Return    Effect      Effect
────────────────────────────────────────────────────────────────────────
Technology         74.0%    32.0%    +38.2%    +29.5%    +4.1%       +6.4%
Healthcare         14.1%    12.5%    -3.4%     +8.2%     -0.1%       -1.6%
Communication      12.0%    8.8%     +27.0%    +18.4%    +0.3%       +1.0%
(Other sectors)    0.0%     46.7%    —         +14.2%    -3.8%       0.0%
────────────────────────────────────────────────────────────────────────
Total                                                    +0.5%       +5.8%
Total Active Return (Alpha):                                         +6.2%
────────────────────────────────────────────────────────────────────────

Allocation Effect: Did you overweight the right sectors?
Selection Effect: Did you pick the right stocks within each sector?
```

**Brinson Attribution Model:**
```
Allocation Effect = (Port Weight - Bench Weight) × (Bench Sector Return - Bench Total Return)
Selection Effect  = Bench Weight × (Port Sector Return - Bench Sector Return)
Interaction       = (Port Weight - Bench Weight) × (Port Sector Return - Bench Sector Return)
```

### 4.5 Position-Level Performance

```
POSITION PERFORMANCE
────────────────────────────────────────────────────────────────────────
                                                Contribution
Ticker  Name         Weight   Return   Gain/Loss   to Portfolio
────────────────────────────────────────────────────────────────────────
META    Meta Platf   20.7%    +75.8%   +$7,272     +12.1%
GOOGL   Alphabet     5.3%     +77.0%   +$1,894     +3.1%
MSFT    Microsoft    25.5%    +45.7%   +$6,525     +10.9%
AAPL    Apple Inc    22.4%    +28.1%   +$4,002     +6.7%
VZ      Verizon      12.0%    +27.0%   +$2,080     +3.5%
JNJ     Johnson&J    14.1%    -3.4%    -$405       -0.7%
────────────────────────────────────────────────────────────────────────
                                       +$21,368    +35.5%

Contribution = Position Gain / Total Portfolio Starting Value
Sorted by contribution (biggest contributors first).
```

---

## Part 5: Income Tracking

### 5.1 Dividend Income

```
DIVIDEND INCOME
────────────────────────────────────────────────────────────────────────
  2026 YTD:   $312.50        Projected Full Year: $1,450.00
  2025:       $1,280.00      2024: $1,105.00

  ┌──────────────────────────────────────────────────────────────┐
  │  MONTHLY DIVIDEND CHART (Bar)                                 │
  │  $150 ─  ██                                                   │
  │  $100 ─  ██  ██              ██  ██              ██  ██      │
  │   $50 ─  ██  ██  ██  ██  ██ ██  ██  ██  ██  ██ ██  ██      │
  │          Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec      │
  └──────────────────────────────────────────────────────────────┘

  DIVIDEND DETAIL
  ┌────────────────────────────────────────────────────────────┐
  │ Date        Ticker  Type        Amount    Yield on Cost    │
  │ 2026-02-15  AAPL    Quarterly   $25.00    1.8%             │
  │ 2026-02-01  VZ      Quarterly   $133.50   6.9%             │
  │ 2026-01-15  MSFT    Quarterly   $47.50    1.3%             │
  │ 2025-12-15  JNJ     Quarterly   $90.00    3.0%             │
  │ ...                                                        │
  └────────────────────────────────────────────────────────────┘

  Upcoming Ex-Dividend Dates:
  │ AAPL    Feb 28, 2026   Est: $0.25/share   Est: $25.00    │
  │ MSFT    Mar 12, 2026   Est: $0.95/share   Est: $47.50    │
────────────────────────────────────────────────────────────────────────
```

### 5.2 Realized Gains/Losses

```
REALIZED GAINS/LOSSES (Tax Year 2026)
────────────────────────────────────────────────────────────────────────
  Short-Term Gains:    $0.00
  Short-Term Losses:   $0.00
  Long-Term Gains:     $0.00
  Long-Term Losses:    $0.00
  Net Realized:        $0.00

  CLOSED POSITIONS (2026)
  ┌────────────────────────────────────────────────────────────┐
  │ Date Sold   Ticker  Shares  Proceeds  Cost    Gain   Type │
  │ (no closed positions this year)                            │
  └────────────────────────────────────────────────────────────┘

  Historical: [2025 ▼] [2024 ▼]
────────────────────────────────────────────────────────────────────────
```

Tax lot selection method: FIFO (First In, First Out) by default.
User can change to: Specific Lot, LIFO, Highest Cost, Lowest Cost.

---

## Part 6: Portfolio-to-Model Integration

### 6.1 Valuation Overlay

For positions that have valuation models built in Model Builder:

```
HOLDINGS TABLE — ENHANCED COLUMNS (toggleable)
────────────────────────────────────────────────────────────────────────
Ticker  Name      Value     Gain%    Intrinsic Value  Upside   Confidence
────────────────────────────────────────────────────────────────────────
AAPL    Apple     $18,252   +28.1%   $172 (DCF)       -5.8%    82/100
MSFT    Microsoft $20,790   +45.7%   $385 (DCF)       -7.4%    78/100
GOOGL   Alphabet  $4,355    +77.0%   —                —        —
META    Meta      $16,872   +75.8%   $490 (Comps)     -12.9%   71/100
JNJ     J&J       $11,460   -3.4%    $168 (DDM)       +9.9%    85/100
VZ      Verizon   $9,780    +27.0%   —                —        —
────────────────────────────────────────────────────────────────────────

  Intrinsic Value: base case from highest-confidence model
  Upside: (Intrinsic - Current Price) / Current Price
  Green = undervalued, Red = overvalued

  Positions without models show "—" with subtle prompt:
  Hover: "No valuation model. Click to build one."
```

### 6.2 Portfolio Valuation Summary

```
PORTFOLIO VALUATION ANALYSIS
────────────────────────────────────────
  Positions with models:     4 of 6 (67%)
  Portfolio-weighted upside: -4.2%
  Most undervalued:          JNJ (+9.9% upside)
  Most overvalued:           META (-12.9% upside)

  Unmodeled positions:       GOOGL, VZ
  [Build Models for Unmodeled →]
────────────────────────────────────────
```

---

## Part 7: Alerts & Calendar

### 7.1 Price Alerts

```
PRICE ALERTS
────────────────────────────────────────
  [+ New Alert]

  Active Alerts:
  │ AAPL   Above $200.00   (currently $182.52)   [Edit] [×] │
  │ JNJ    Below $145.00   (currently $152.80)   [Edit] [×] │
  │ MSFT   % Change > 5%   (daily)               [Edit] [×] │

  Alert types:
  - Price above/below threshold
  - % change (daily) exceeds threshold
  - Intrinsic value crossed (price crosses model value)
  - 52-week high/low reached

  Notification: Toast notification in app
  (Future: push notification via OpenClaw/Telegram integration)
────────────────────────────────────────
```

### 7.2 Earnings & Dividend Calendar

```
UPCOMING EVENTS
────────────────────────────────────────
  Feb 27  AAPL   Ex-Dividend     $0.25/share
  Mar 01  MSFT   Earnings (Q2)   After market close
  Mar 05  VZ     Ex-Dividend     $0.6675/share
  Mar 12  JNJ    Earnings (Q1)   Before market open
  Mar 15  MSFT   Ex-Dividend     $0.95/share
  ...

  Source: Yahoo Finance earnings/dividend calendars
  Shows events for portfolio holdings + watchlist
  Filterable: [All] [Earnings] [Dividends] [Ex-Div Dates]
────────────────────────────────────────
```

---

## Part 8: Sub-Tab Structure

```
Portfolio Sub-Tabs:
  Holdings │ Performance │ Allocation │ Income │ Transactions │ Alerts
```

- **Holdings:** Primary table with all positions, summary header, lot detail
- **Performance:** Return metrics, benchmark comparison chart, risk metrics, attribution
- **Allocation:** Sector donut, treemap, account breakdown
- **Income:** Dividend income tracking, upcoming ex-dates, projected annual income
- **Transactions:** Full transaction log, filterable by type/ticker/date/account
- **Alerts:** Price alerts, earnings calendar, dividend calendar

---

## Part 9: Multi-Account Support

```
Account structure:
  - User creates accounts with custom names (e.g., "Fidelity IRA", "Schwab Taxable")
  - Every position belongs to exactly one account
  - Portfolio summary shows all accounts combined (default)
  - Filter to single account via dropdown in summary header

  Account management:
  Settings → Portfolio → Accounts
  - Add / rename / remove accounts
  - Set default account for new positions
  - Set tax status per account (Taxable, Traditional IRA, Roth IRA, 401k)
  - Tax status affects realized gain/loss classification
```

---

*End of Phase 3 specification.*
