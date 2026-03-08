# Phase 2 — Scanner / Screener Module
> Designer Agent | February 26, 2026
> Status: COMPLETE — APPROVED BY FINN
> Depends on: Phase 0A-0E (foundation specs), Phase 0D (UI/UX Framework)

---

## Overview

The Scanner is the app's discovery engine — how you find companies worth
investigating. It combines financial screening (filter by metrics) with
text-based filing search (find keywords in 10-K/10-Q filings) in a single
unified interface. Think Bloomberg EQS meets SEC EDGAR full-text search,
with a modern UI and real-time results.

**Key decisions:**
- Full Russell 3000 as base universe (~3,000 companies)
- User-expandable universe (add any ticker, future: add by ETF holdings)
- Combined financial filters + filing keyword search in one screen
- Preset screens for common strategies (value, growth, quality, dividend, etc.)
- Deep filter library with custom filter builder
- Results flow directly into Model Builder and Research modules

---

## Part 1: Universe Management

### 1.1 Default Universe

```
BASE: Russell 3000
  - ~3,000 US-listed companies
  - Covers approximately 98% of US equity market by market cap
  - Includes large, mid, small, and micro cap
  - Refreshed periodically (Russell reconstitution is annual in June)

ALWAYS INCLUDED (regardless of index membership):
  - S&P 500 constituents (redundant with R3000 but ensures coverage)
  - Any ticker the user has ever searched for in Model Builder
  - Any ticker in any watchlist
  - Any ticker in portfolio holdings
  - Any manually added ticker

DATA MAINTENANCE:
  - Financial data refreshed in batches (not all 3,000 at once)
  - Priority tiers:
    Tier 1 (refresh daily):   Portfolio + Watchlist + Open Models (~50-100)
    Tier 2 (refresh weekly):  S&P 500 (~500)
    Tier 3 (refresh monthly): Full Russell 3000 (~3,000)
  - Stale data indicator: show age of data in scanner results
  - Manual "Refresh Universe" button for on-demand full refresh
```

### 1.2 Universe Expansion

```
Current capabilities:
  - [+ Add Ticker] — add any US-listed ticker to the universe
  - Auto-add: any ticker searched in Model Builder joins the universe
  - Auto-add: any ticker added to watchlist or portfolio joins

Future capabilities (post-MVP, architecture supports):
  - "Add ETF holdings" — enter an ETF ticker (e.g., XLK, ARKK),
    app fetches holdings and adds all constituent companies
  - "Add index" — add Nasdaq 100, DJIA, sector indices
  - "Add custom list" — CSV import of tickers
  - International expansion — non-US listed companies

Universe management UI:
  Settings → Scanner → Universe Management
  - Shows current universe size and composition
  - List of all tickers with source tags (R3000, Manual, Portfolio, etc.)
  - Remove individual tickers
  - Reset to default (R3000 only)
```

### 1.3 Data Storage for Universe

Each company in the universe has a record in the database with:

```
companies table:
  - ticker, company_name, sector, industry, market_cap
  - exchange, country, description (from 10-K)
  - universe_source (r3000, manual, portfolio, watchlist)
  - data_last_updated timestamp

financial_data table:
  - All line items (wide table format per Phase 0B)
  - 10+ years where available

market_data table (cache):
  - Current price, P/E, EV/EBITDA, dividend yield, etc.
  - Updated per refresh tier schedule

filing_text table:
  - Parsed sections from 10-K and 10-Q filings
  - Full text searchable
  - Filing date, period, form type
```

---

## Part 2: Financial Filters

### 2.1 Filter Categories

The scanner offers filters organized into categories. Every filter supports:
- Min/max range (e.g., P/E between 10 and 20)
- Greater than / less than (e.g., Revenue Growth > 15%)
- Top/bottom N (e.g., Top 50 by ROE)
- Percentile rank (e.g., Top quartile by margin)

```
VALUATION FILTERS
─────────────────────────────────
  P/E Ratio (TTM)
  P/E Ratio (Forward)
  PEG Ratio
  EV/EBITDA
  EV/EBIT
  EV/Revenue
  EV/FCF
  P/B (Price to Book)
  P/TBV (Price to Tangible Book)
  P/FCF (Price to Free Cash Flow)
  P/S (Price to Sales)
  Dividend Yield
  FCF Yield
  Earnings Yield (inverse P/E)
  Shareholder Yield (div + buyback)

GROWTH FILTERS
─────────────────────────────────
  Revenue Growth (YoY)
  Revenue Growth (3Y CAGR)
  Revenue Growth (5Y CAGR)
  EPS Growth (YoY)
  EPS Growth (3Y CAGR)
  EPS Growth (5Y CAGR)
  EBITDA Growth (YoY)
  EBITDA Growth (3Y CAGR)
  Dividend Growth (3Y CAGR)
  Dividend Growth (5Y CAGR)
  FCF Growth (3Y CAGR)
  Book Value Growth (5Y CAGR)

PROFITABILITY FILTERS
─────────────────────────────────
  Gross Margin
  Operating Margin
  EBITDA Margin
  Net Margin
  FCF Margin
  Return on Equity (ROE)
  Return on Assets (ROA)
  Return on Invested Capital (ROIC)
  Return on Capital Employed (ROCE)
  Asset Turnover
  Gross Profit / Total Assets (Novy-Marx)

FINANCIAL HEALTH FILTERS
─────────────────────────────────
  Current Ratio
  Quick Ratio
  Debt to Equity
  Net Debt / EBITDA
  Interest Coverage Ratio
  Altman Z-Score
  Piotroski F-Score
  Cash / Total Assets
  FCF / Total Debt
  Working Capital / Revenue

SIZE & LIQUIDITY FILTERS
─────────────────────────────────
  Market Cap
  Enterprise Value
  Revenue (TTM)
  Total Assets
  Shares Outstanding
  Average Daily Volume
  Float Percentage
  Institutional Ownership (if available)

DIVIDEND FILTERS
─────────────────────────────────
  Dividend Yield
  Payout Ratio (Earnings)
  Payout Ratio (FCF)
  Dividend Coverage Ratio
  Consecutive Years of Dividend Growth
  Consecutive Years of Dividend Payment
  Ex-Dividend Date (upcoming within N days)

MOMENTUM & TECHNICAL FILTERS
─────────────────────────────────
  52-Week High (% from)
  52-Week Low (% from)
  Price Change (1 month)
  Price Change (3 month)
  Price Change (6 month)
  Price Change (YTD)
  Price Change (1 year)
  Relative Strength vs S&P 500 (3M, 6M, 1Y)
  Beta

QUALITY COMPOSITE FILTERS
─────────────────────────────────
  Rule of 40 Score (growth + margin)
  Quality Score (composite: ROE + margin stability + low leverage)
  Earnings Quality (accruals ratio)
  Revenue Consistency (low std dev of growth)
  Margin Stability (low std dev of operating margin)
  Capital Efficiency (ROIC - WACC spread)

SECTOR & CLASSIFICATION FILTERS
─────────────────────────────────
  Sector (GICS Level 1)
  Industry Group (GICS Level 2)
  Industry (GICS Level 3)
  Sub-Industry (GICS Level 4)
  Exchange (NYSE, NASDAQ, AMEX)
  Country
  Index Membership (S&P 500, Russell 1000, etc.)
```

### 2.2 Filter Interactions

```
Multiple filters within same category:  AND logic
  Example: P/E < 20 AND EV/EBITDA < 12
  → Company must pass BOTH filters

Multiple filters across categories:     AND logic
  Example: P/E < 20 AND Revenue Growth > 10% AND Sector = Technology
  → Company must pass ALL filters

Within a single filter:                 Range logic
  Example: Market Cap between $10B and $200B
  → Inclusive on both ends

Special filter: "Exclude" mode
  Any filter can be inverted
  Example: Exclude Sector = Financials
  → Removes all financials from results
```

### 2.3 Custom Filter Builder

For advanced users who want metrics not in the standard library:

```
CUSTOM FILTER BUILDER

Formula:  [Metric A] [operator] [Metric B]

Examples:
  FCF / Market Cap > 0.08
    → Companies with FCF yield above 8%

  (Revenue - Revenue_prev) / Revenue_prev > Operating Margin
    → Rule of 40: revenue growth + margin > threshold

  EBITDA / Interest Expense > 5
    → Strong interest coverage

  (Net Income - Operating Cash Flow) / Total Assets < 0.05
    → Low accruals (high earnings quality)

Available operators: +, -, ×, ÷, >, <, >=, <=, =, !=
Available functions: ABS(), MIN(), MAX(), AVG() (over time periods)
Available time suffixes: _1Y, _2Y, _3Y (for year-over-year comparisons)

Custom filters can be saved with a name and reused in presets.
```

---

## Part 3: Filing Text Search

### 3.1 Search Capabilities

```
FULL-TEXT SEARCH across parsed SEC filings:

Supported filing types:
  - 10-K (Annual Report) — all parsed sections
  - 10-Q (Quarterly Report) — all parsed sections
  - 8-K (Current Report) — material events

Searchable sections (from 10-K):
  - Business Description (Item 1)
  - Risk Factors (Item 1A)
  - MD&A — Management Discussion & Analysis (Item 7)
  - Financial Statements & Notes (Item 8)
  - Full filing text

Search syntax:
  Simple:        "artificial intelligence"
  Boolean:       "AI" AND "machine learning"
  Phrase:        "recurring revenue"
  Exclusion:     "cloud" NOT "mining"
  Proximity:     "margin" NEAR/5 "expansion"  (within 5 words)
  Wildcard:      "block*" (matches blockchain, blockbuster, etc.)
  Section filter: section:risk_factors "cybersecurity"
```

### 3.2 Search Result Context

When a filing text match is found, the scanner shows:

```
FILING MATCH — SNOW (Snowflake Inc.)
10-K Filed: 2024-03-28 | Period: FY2024

Section: Business Description (Item 1)
"...Our platform enables customers to consolidate data into a single
 source of truth to drive meaningful business insights, build data-
 driven applications, and share data and data products. We deliver
 our platform through a customer-centric, consumption-based business
 model, only charging customers for the resources they use..."
 ─── Match: "consumption-based" ───

Section: Risk Factors (Item 1A)
"...We have a history of net losses, and we may not be able to
 achieve or sustain profitability in the future..."
 ─── Match: "net losses" ───

[View Full Filing →]  [Open in Research →]
```

- Matched terms highlighted in --accent-primary
- Show surrounding context (50 words before and after)
- Multiple matches per filing shown as expandable list
- Link to full filing in Research module

### 3.3 Combined Search

The power of the scanner is combining financial filters with text search:

```
EXAMPLE: Find SaaS companies transitioning to profitability

Financial Filters:
  Revenue Growth (3Y CAGR) > 20%
  Operating Margin > -10% AND < 10%    (near breakeven)
  EV/Revenue < 15
  Sector = Technology

Filing Text Search:
  "recurring revenue" AND ("path to profitability" OR "margin expansion")

→ Returns companies that are:
  1. Growing fast
  2. Near profitability inflection
  3. Reasonably valued
  4. Self-describing as recurring revenue with margin improvement narrative
```

---

## Part 4: Preset Screens

### 4.1 Built-In Presets

Pre-configured screens that users can run with one click:

```
VALUE SCREENS
─────────────────────────────────
  Classic Value (Graham-Style)
    P/E < 15, P/B < 1.5, Current Ratio > 2.0, Debt/Equity < 0.5
    Positive earnings for last 5 years

  Deep Value
    P/E < 10, P/B < 1.0, FCF Yield > 8%
    Market Cap > $500M (avoids value traps in micro-caps)

  Magic Formula (Greenblatt)
    Ranked by: Earnings Yield (EBIT/EV) + Return on Capital (EBIT/Net Fixed Assets + NWC)
    Top 50 composite rank

  Dividend Value
    Dividend Yield > 3%, Payout Ratio < 70%, 5+ years consecutive growth
    P/E < 20, Debt/Equity < 1.0

GROWTH SCREENS
─────────────────────────────────
  Growth at Reasonable Price (GARP)
    EPS Growth (3Y CAGR) > 15%, PEG < 1.5
    ROE > 15%, Positive FCF

  High Growth
    Revenue Growth (3Y CAGR) > 25%
    Market Cap > $1B
    Ranked by revenue growth

  Emerging Compounder
    Revenue Growth (3Y CAGR) > 15%, ROIC > 12%
    Operating Margin expanding (current > 3Y average)
    Debt/EBITDA < 2.0

QUALITY SCREENS
─────────────────────────────────
  Quality Compounder
    ROE > 20%, ROIC > 15%
    Operating Margin > 20%, Net Margin > 10%
    Revenue Growth (5Y CAGR) > 5%
    Debt/EBITDA < 2.0

  Wide Moat
    Gross Margin > 50%, Operating Margin > 25%
    ROE > 20%, stable (std dev < 5pp over 5Y)
    Revenue Growth > 5%
    Filing search: "competitive advantage" OR "barriers to entry" OR "pricing power"

  Piotroski High F-Score
    F-Score >= 8 (out of 9)
    Market Cap > $500M

  Dividend Aristocrat-Style
    Consecutive years of dividend growth >= 10
    Payout Ratio < 75%
    FCF Coverage > 1.5x

SECTOR-SPECIFIC SCREENS
─────────────────────────────────
  SaaS / Cloud
    Revenue Growth > 20%, Gross Margin > 60%
    Rule of 40 Score > 40
    Filing search: "recurring revenue" OR "SaaS" OR "subscription"

  Bank Screen
    P/B < 1.5, ROE > 10%
    Net Interest Margin > 2.5% (if available in data)
    Dividend Yield > 2%

  REIT Screen
    Dividend Yield > 4%
    Payout Ratio (FFO-based if available, else earnings) < 85%
    Debt/EBITDA < 6.0

MOMENTUM SCREENS
─────────────────────────────────
  52-Week High Momentum
    Within 5% of 52-week high
    Revenue Growth > 10%
    Relative Strength vs S&P 500 (6M) > 0

  Fallen Angel Recovery
    Price Change (6M) < -25%
    Current Ratio > 1.5, Positive FCF
    P/E < sector median
    Piotroski F-Score >= 6

CUSTOM SCREENS
─────────────────────────────────
  User-created screens saved here
  Full filter + text search combinations
  Named, dated, shareable (export as JSON)
```

### 4.2 Preset Management

```
UI: Dropdown / sidebar showing all presets organized by category

Actions per preset:
  [Run]           — execute screen, show results
  [Edit]          — open filters in editor (creates a copy for custom)
  [Duplicate]     — copy to Custom Screens for modification
  [Export]        — save preset as JSON file
  [Import]        — load preset from JSON file

Built-in presets cannot be modified (but can be duplicated + edited).
Custom presets fully editable, renameable, deletable.
```

---

## Part 5: Scanner UI Layout

### 5.1 Main Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  DASHBOARD │ MODEL BUILDER │ ▸SCANNER │ PORTFOLIO │ RESEARCH │ ...  │
├─────────────────────────────────────────────────────────────────────┤
│  Screens │ Filters │ Results │ Universe                             │
├──────────────┬──────────────────────────────────────────────────────┤
│              │                                                      │
│  FILTER      │  RESULTS TABLE                                      │
│  PANEL       │                                                      │
│  (left)      │  ┌──────────────────────────────────────────────┐   │
│              │  │ 147 companies match │ [Export] [Save Screen]  │   │
│  ┌────────┐  │  ├──────────────────────────────────────────────┤   │
│  │Presets ▼│  │  │ Ticker  Name         MCap    P/E   EV/EB.. │   │
│  ├────────┤  │  │ AAPL    Apple Inc    $2.8T   28.5  22.1x   │   │
│  │        │  │  │ MSFT    Microsoft    $3.1T   34.2  24.8x   │   │
│  │VALUAT. │  │  │ GOOGL   Alphabet     $2.1T   24.1  17.2x   │   │
│  │P/E ────│  │  │ META    Meta Platf   $1.4T   26.3  16.5x   │   │
│  │  5  25 │  │  │ ...                                         │   │
│  │EV/EBIT │  │  │                                              │   │
│  │  ── 15 │  │  │                                              │   │
│  │        │  │  │                                              │   │
│  │GROWTH  │  │  │                                              │   │
│  │Rev Gr. │  │  │                                              │   │
│  │ 10% ── │  │  │                                              │   │
│  │        │  │  │                                              │   │
│  │TEXT    │  │  │                                              │   │
│  │[search]│  │  │                                              │   │
│  │        │  │  │                                              │   │
│  │[+Filter]│ │  │                                              │   │
│  │[Clear] │  │  │                                              │   │
│  └────────┘  │  └──────────────────────────────────────────────┘   │
│              │                                                      │
│  Width: ~280px│  Width: remaining                                   │
└──────────────┴──────────────────────────────────────────────────────┘
```

### 5.2 Filter Panel (Left Side)

```
FILTER PANEL DESIGN

Top section: Preset selector
  Dropdown: "Select a preset screen..."
  When selected, all filters populate automatically
  [Clear All] button to reset

Filter groups: collapsible accordions
  Each category (Valuation, Growth, etc.) is a collapsible section
  Active filters show a blue dot on the section header
  Count of active filters shown: "Valuation (3)"

Individual filter:
  ┌─────────────────────────────┐
  │ P/E Ratio (TTM)            │
  │ ○───────●──────○           │
  │ 5              25          │
  │ [Min: 5 ] to [Max: 25]    │
  └─────────────────────────────┘

  - Dual-handle range slider (--accent-primary track)
  - Numeric inputs below for precise entry
  - Leave one side empty for open-ended (e.g., P/E > 5)
  - [×] to remove this filter

Text search section:
  ┌─────────────────────────────┐
  │ Filing Text Search          │
  │ ┌─────────────────────────┐ │
  │ │ "recurring revenue"     │ │
  │ └─────────────────────────┘ │
  │ Filing type: [10-K ▼]      │
  │ Section:    [All ▼]        │
  │ Boolean:    AND / OR / NOT │
  └─────────────────────────────┘

[+ Add Filter] button opens filter picker:
  - Shows all available filters organized by category
  - Search/filter the filter list
  - Click to add to active filters

[Clear All] — removes all filters and text search
[Save as Screen] — save current filter set as custom preset

Filter panel is scrollable independently from results table.
Width: 280px fixed, collapsible to icon-only (40px) for more results space.
```

### 5.3 Results Table (Right Side)

```
RESULTS TABLE DESIGN

Header bar:
  "147 companies match" (updates in real-time as filters change)
  [Columns ▼] — choose which columns to display
  [Export ▼] — Export to Excel / Export to CSV
  [Save Screen] — save current filter + column configuration

Table:
  - Bloomberg-style: companies as rows, metrics as columns
  - Default columns: Ticker, Company Name, Sector, Market Cap,
    P/E, EV/EBITDA, Rev Growth (3Y), Op Margin, ROE, Div Yield
  - ALL columns sortable (click header to sort, click again to reverse)
  - Columns resizable by dragging header borders
  - Column order draggable (rearrange by drag-and-drop)
  - Fixed first column (Ticker) — doesn't scroll horizontally
  - Zebra striping per Phase 0D
  - Virtualized rendering (react-window) for smooth scrolling at 3,000 rows

Row interactions:
  - Click row → expands inline detail panel (key metrics, sparkline, description)
  - Double-click row → opens company in Model Builder
  - Right-click row → context menu:
    - Open in Model Builder
    - Open in Research
    - Add to Watchlist
    - Add to Portfolio
    - Run Auto-Detection
    - View Filing Matches (if text search active)

Inline detail panel (on single click):
  ┌─────────────────────────────────────────────────────────────┐
  │  AAPL — Apple Inc. · Technology · Consumer Electronics      │
  │                                                             │
  │  Price: $182.52 (+0.68%)   MCap: $2.83T   EV: $2.89T      │
  │                                                             │
  │  Revenue (5Y)  ──────────╱                                  │
  │  Op Margin     ─────═════                                   │
  │                                                             │
  │  "Apple Inc. designs, manufactures, and markets             │
  │   smartphones, personal computers, tablets..."              │
  │                                                             │
  │  [Open in Model Builder]  [Open in Research]  [+ Watchlist] │
  └─────────────────────────────────────────────────────────────┘

  - 5Y revenue sparkline (tiny line chart, --accent-primary)
  - 5Y operating margin sparkline
  - Truncated business description (from 10-K)
  - Quick action buttons
```

### 5.4 Real-Time Filtering

```
Filters apply in real-time as the user adjusts them.
No "Run" button — results update immediately.

Performance strategy:
  1. All financial data for the universe is pre-loaded in the database
  2. Filter queries run against SQLite (fast for 3,000 rows)
  3. Text search queries run against filing_text table (indexed)
  4. Results streamed to frontend as they compute
  5. Target: < 2 seconds for financial-only filters
  6. Target: < 5 seconds for combined financial + text search

Loading behavior:
  - Skeleton loader on results table while computing
  - Results count updates incrementally: "Searching... 89 matches so far"
  - If > 5 seconds, show progress indicator
```

---

## Part 6: Scanner Sub-Tabs

```
Scanner Sub-Tabs:
  Screens │ Filters │ Results │ Universe
```

### Screens Tab
- Grid of preset screen cards (built-in + custom)
- Each card shows: name, brief description, number of results last run
- Click to run screen → switches to Results tab automatically
- [+ New Custom Screen] button

### Filters Tab
- The full filter panel in expanded view (full width, not sidebar)
- Useful for building complex screens with many filters
- Same functionality as the sidebar filter panel but more space

### Results Tab
- The primary view (filter panel sidebar + results table)
- This is where users spend most of their time
- Default tab when navigating to Scanner

### Universe Tab
- Universe management interface
- List all companies in universe with source tags
- Add/remove tickers
- Universe statistics (total companies, by sector, data freshness)
- [Refresh Universe Data] button

---

## Part 7: Scanner-to-Module Workflows

### Scanner → Model Builder
```
User finds interesting company in scanner results
→ Double-click or right-click → "Open in Model Builder"
→ Model Builder opens with that ticker loaded
→ Auto-detection runs, recommended models shown
→ User builds valuation model

The scanner remains accessible — user can switch back to Scanner tab
and their results/filters are preserved.
```

### Scanner → Research
```
Right-click → "Open in Research"
→ Research module opens with company profile
→ Filing data, financial statements, notes available
→ User reads 10-K sections, particularly those matching text search
```

### Scanner → Portfolio
```
Right-click → "Add to Watchlist" (select which watchlist)
Right-click → "Add to Portfolio" → position entry dialog
```

### Batch Operations
```
Select multiple rows (Shift+click or Ctrl+click):
  - Add all to watchlist
  - Export selected to Excel
  - Compare selected (opens side-by-side comparison view)
  - Run auto-detection on all (batch scoring)
```

---

## Part 8: Ranking & Scoring

### 8.1 Composite Ranking

When a screen returns results, users can rank by composite scores:

```
Rank by: [Single Metric ▼]  or  [Composite Score ▼]

Single Metric: sort by any column (standard table sort)

Composite Score: weight multiple metrics for a combined rank

COMPOSITE SCORE BUILDER:
  Metric             Weight    Direction
  ─────────────────────────────────────
  P/E Ratio          30%       Lower is better
  Revenue Growth     25%       Higher is better
  ROE                20%       Higher is better
  Debt/Equity        15%       Lower is better
  Dividend Yield     10%       Higher is better
  ─────────────────────────────────────
  [Calculate Rankings]

Each metric is converted to a percentile rank (0-100) within the
result set, then weighted and combined into a composite score.
Companies ranked 1 to N by composite score.

Composite configurations can be saved as part of custom presets.
```

### 8.2 Relative Metrics

For any numeric column, the scanner can show:

```
Display mode toggle (per column):
  [Absolute] — raw value (P/E = 22.1)
  [Percentile] — rank within result set (P/E = 65th percentile)
  [vs Sector] — relative to sector median (P/E = 1.2x sector median)
  [Z-Score] — standard deviations from result set mean (P/E = +0.8σ)
```

---

## Part 9: Data Freshness & Quality

### 9.1 Stale Data Handling

```
Data age indicators in results table:

  ● Green:  Updated today
  ● Yellow: Updated this week
  ● Orange: Updated this month
  ● Red:    Older than 1 month

Indicator shown as a small dot next to the data value.
Hover shows: "Last updated: Feb 25, 2026"

For text search results, filing date is always shown.
Older filings (>1 year) are flagged: "⚠ Filing from 2023 — newer filing may be available"
```

### 9.2 Missing Data in Filters

```
When a company has missing data for a filter:

Default behavior: EXCLUDE from results
  (If you filter P/E < 20, companies with no P/E data are excluded)

Toggle option: [Include companies with missing data]
  When enabled, companies with missing filter values are included
  in results with "—" in the relevant column
  Useful for finding under-covered companies
```

---

## Part 10: Performance Targets

```
Financial-only screen (all 3,000 companies):     < 2 seconds
Financial + text search:                          < 5 seconds
Typing in text search (debounced 300ms):          Results update < 3 seconds
Sorting results table:                            < 200ms
Adding/removing a filter:                         Results update < 2 seconds
Loading inline detail panel:                      < 500ms
Exporting results to Excel:                       < 3 seconds
Preset screen load:                               < 2 seconds
Universe data refresh (full):                     Background, < 5 minutes
                                                  (does not block UI)
```

---

*End of Phase 2 specification.*
