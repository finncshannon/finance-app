# Phase 4 — Research Module
> Designer Agent | February 26, 2026
> Status: COMPLETE — APPROVED BY FINN
> Depends on: Phase 0A-0E (foundation specs), Phase 2 (Scanner — filing data)

---

## Overview

The Research module is the analytical workbench — where you read SEC filings,
examine financial statements line by line, study company fundamentals, and
build a deep understanding of a business before (or alongside) building
valuation models.

This is the Bloomberg Terminal's FA (Fundamental Analysis) function meets
SEC EDGAR, with a modern interface and everything connected to the rest
of the app.

**Key decisions:**
- Comprehensive filing viewer with parsed 10-K/10-Q sections
- Full financial statements in Bloomberg-style tables (IS, BS, CF)
- Ratio analysis with trend visualization
- Peer comparison tables
- Company profile with business description, key stats, management
- All data flows from the same database that powers Scanner and Model Builder

---

## Part 1: Filing Viewer

### 1.1 Filing Library

```
FILINGS — AAPL
────────────────────────────────────────────────────────────────────────
  Filter: [All ▼]  [10-K]  [10-Q]  [8-K]  [Proxy]      [Search filings...]

  ┌────────────────────────────────────────────────────────────────┐
  │ Form    Period        Filed         Description                │
  │ 10-K    FY 2024      2024-10-31    Annual Report              │
  │ 10-Q    Q3 2024      2024-08-02    Quarterly Report           │
  │ 10-Q    Q2 2024      2024-05-03    Quarterly Report           │
  │ 8-K     —            2024-08-01    Earnings Release Q3 2024   │
  │ 10-Q    Q1 2024      2024-01-31    Quarterly Report           │
  │ 10-K    FY 2023      2023-11-03    Annual Report              │
  │ DEF 14A FY 2024      2024-01-05    Proxy Statement            │
  │ ...                                                            │
  └────────────────────────────────────────────────────────────────┘

  Source: SEC EDGAR (fetched and parsed by backend)
  Storage: filing_text table in database
  Retention: last 5 years of 10-K/10-Q, last 1 year of 8-K
────────────────────────────────────────────────────────────────────────
```

### 1.2 Parsed Section Viewer

When you open a 10-K or 10-Q, the filing is pre-parsed into navigable sections:

```
10-K VIEWER — AAPL FY 2024
────────────────────────────────────────────────────────────────────────
  SECTIONS (left sidebar)              CONTENT (right panel)
  ┌──────────────────────┐             ┌──────────────────────────────┐
  │ ▸ Item 1: Business   │             │ ITEM 1: BUSINESS             │
  │   Item 1A: Risk      │             │                              │
  │   Item 1B: Unresolved│             │ Apple Inc. ("Apple") designs,│
  │ ▸ Item 2: Properties │             │ manufactures, and markets    │
  │ ▸ Item 3: Legal      │             │ smartphones, personal        │
  │ ▸ Item 5: Market     │             │ computers, tablets, wearables│
  │ ▸ Item 6: [Reserved] │             │ and accessories, and sells   │
  │ ▸ Item 7: MD&A       │             │ a variety of related         │
  │ ▸ Item 7A: Quant Disc│             │ services...                  │
  │ ▸ Item 8: Financials │             │                              │
  │ ▸ Item 9: Changes    │             │ Products                     │
  │ ▸ Item 10: Directors │             │ ─────────                    │
  │ ▸ Item 11: Exec Comp │             │ iPhone                       │
  │ ▸ Item 12: Security  │             │ The Company's line of        │
  │ ▸ Item 13: Relations │             │ smartphones...               │
  │ ▸ Item 14: Fees      │             │                              │
  │ ▸ Item 15: Exhibits  │             │ [continues...]               │
  └──────────────────────┘             └──────────────────────────────┘

  Section sidebar:
  - Click to jump to section
  - Active section highlighted with --accent-primary left border
  - Collapsible sub-sections within each Item
  - Scroll position syncs between sidebar and content

  Content panel:
  - Clean typography: 14px Inter, 1.6 line-height
  - Tables in filings rendered as proper HTML tables
  - Numbers in filing tables: JetBrains Mono
  - Search within filing: Ctrl+F opens search bar at top of content
  - Text highlighting: user can select text (preserved for session)
```

### 1.3 Filing Comparison

Compare sections across different periods:

```
COMPARE FILINGS
────────────────────────────────────────────────────────────────────────
  Left:  [10-K FY 2024 ▼]     Right: [10-K FY 2023 ▼]
  Section: [Item 1A: Risk Factors ▼]

  ┌─────────────────────────┐  ┌─────────────────────────┐
  │ FY 2024 Risk Factors    │  │ FY 2023 Risk Factors    │
  │                         │  │                         │
  │ The Company is subject  │  │ The Company is subject  │
  │ to risks associated     │  │ to risks associated     │
  │ with global economic    │  │ with global economic    │
  │ conditions, including   │  │ conditions...           │
  │ ██ inflationary         │  │                         │
  │ ██ pressures and        │  │                         │
  │ ██ AI-related risks...  │  │                         │
  │                         │  │                         │
  └─────────────────────────┘  └─────────────────────────┘

  ██ = New text (highlighted in --accent-subtle)
  Diff computed at paragraph level, not word-by-word
  Useful for spotting new risk factors, strategy changes, language shifts
────────────────────────────────────────────────────────────────────────
```

### 1.4 Key Metrics Extraction

The parser automatically extracts key data points from filings:

```
EXTRACTED METRICS — AAPL 10-K FY 2024
────────────────────────────────────────────────────────────────────────
  From Item 1 (Business):
    Segments: iPhone, Mac, iPad, Wearables/Home/Accessories, Services
    Employees: ~164,000
    Geographic regions: Americas, Europe, Greater China, Japan, Rest of Asia

  From Item 7 (MD&A):
    Revenue guidance mentions: [none — Apple doesn't guide]
    Key growth drivers cited: Services, iPhone upgrades
    Key risks cited: China exposure, regulatory, supply chain

  From Item 8 (Financials):
    Effective tax rate: 16.2%
    Share repurchase authorization remaining: $90B
    Segment revenue breakdown extracted → stored in financial_data

  These extracted data points feed into:
  - Assumption Engine (business description → peer selection)
  - Scanner (text search matches)
  - Company Profile (summary view)
────────────────────────────────────────────────────────────────────────
```

---

## Part 2: Financial Statements

### 2.1 Statement Views

Three core financial statements in Bloomberg-style tables:

```
INCOME STATEMENT — AAPL
────────────────────────────────────────────────────────────────────────
                        FY2020    FY2021    FY2022    FY2023    FY2024
────────────────────────────────────────────────────────────────────────
Revenue                 274,515   365,817   394,328   383,285   391,035
  YoY Growth                      33.3%     7.8%     -2.8%     2.0%
Cost of Revenue         169,559   212,981   223,546   214,137   210,352
GROSS PROFIT            104,956   152,836   170,782   169,148   180,683
  Gross Margin           38.2%    41.8%     43.3%     44.1%     46.2%

Research & Development   18,752    21,914    26,251    29,915    31,370
SG&A                     19,916    21,973    25,094    24,932    25,188
TOTAL OPERATING EXP      38,668    43,887    51,345    54,847    56,558

OPERATING INCOME         66,288   108,949   119,437   114,301   124,125
  Operating Margin       24.1%    29.8%     30.3%     29.8%     31.7%

Interest Income           3,763     2,843     2,825     3,999     4,092
Interest Expense         -2,873    -2,645    -2,931    -3,468    -3,892
Other Income/(Expense)      803       258       228      -565      -382
INCOME BEFORE TAX        67,981   109,405   119,559   114,267   123,943

Income Tax Expense       10,987    17,523    19,300    18,107    20,079
  Effective Tax Rate     16.2%    16.0%     16.1%     15.8%     16.2%

NET INCOME               56,994    91,882   100,259    96,160   103,864
  Net Margin             20.8%    25.1%     25.4%     25.1%     26.6%

EPS (Diluted)             3.28      5.61      6.15      6.13      6.42
Shares (Diluted, M)      17,352    16,382    16,320    15,696    16,170
────────────────────────────────────────────────────────────────────────
  All values in $M except per-share data.
  Computed metrics (margins, growth) in --text-secondary.
```

**Design rules:**
- Years across top, line items down rows (Bloomberg standard)
- Annual (default) or Quarterly toggle
- Section headers (GROSS PROFIT, OPERATING INCOME, NET INCOME) in bold
- Computed ratios (margins, growth) inserted inline in --text-secondary
- Negative values in parentheses and --color-negative
- All numbers: JetBrains Mono, right-aligned
- Line items: Inter, left-aligned
- Zebra striping on data rows
- Sticky first column (line item names) during horizontal scroll

**Same format for:**

```
BALANCE SHEET — AAPL
  Assets (Current → Non-Current → Total)
  Liabilities (Current → Non-Current → Total)
  Shareholders' Equity
  Computed: Working Capital, Book Value, Tangible Book Value
  Computed: Current Ratio, Debt/Equity, Net Debt

CASH FLOW STATEMENT — AAPL
  Operating Activities (Net Income → adjustments → changes in WC → total)
  Investing Activities (CapEx, acquisitions, investments → total)
  Financing Activities (debt, buybacks, dividends → total)
  Net Change in Cash
  Computed: Free Cash Flow = Operating CF - CapEx
  Computed: FCF Margin, FCF Yield
```

### 2.2 Statement Interactions

```
Click any number:
  → Tooltip shows: exact value, YoY change, % of revenue (if applicable)
  → "View in filing" link jumps to the relevant section of the 10-K/10-Q

Right-click any line item:
  → Chart this metric (opens mini chart overlay showing 5-10Y trend)
  → Copy value
  → Compare to peers (opens peer comparison for this specific line item)

Column header (year):
  → Click to highlight column
  → Link to the filing for that period
```

### 2.3 Custom Financial Views

```
CUSTOM VIEW BUILDER
────────────────────────────────────────
  Drag line items from any statement into a custom table:

  My Custom View:
  │ Revenue
  │ Gross Profit
  │ Operating Income
  │ Free Cash Flow
  │ EPS (Diluted)
  │ Gross Margin
  │ Operating Margin
  │ FCF Margin
  │ Revenue Growth
  │ EPS Growth

  Saved custom views persist per user.
  Useful for quickly comparing the metrics you care about most
  across all companies without scrolling through full statements.
```

---

## Part 3: Ratio Analysis

### 3.1 Ratio Dashboard

```
RATIO ANALYSIS — AAPL
────────────────────────────────────────────────────────────────────────

  PROFITABILITY                              RETURNS
  ┌─────────────────────────────┐            ┌─────────────────────────┐
  │ Gross Margin      46.2%    │            │ ROE              171.6% │
  │ Operating Margin  31.7%    │            │ ROA               28.4% │
  │ Net Margin        26.6%    │            │ ROIC              56.2% │
  │ FCF Margin        25.8%    │            │ ROCE              68.3% │
  │ EBITDA Margin     35.4%    │            │ Asset Turnover     1.07 │
  └─────────────────────────────┘            └─────────────────────────┘

  LEVERAGE                                   LIQUIDITY
  ┌─────────────────────────────┐            ┌─────────────────────────┐
  │ Debt / Equity       6.2x   │            │ Current Ratio      0.99 │
  │ Net Debt / EBITDA   0.3x   │            │ Quick Ratio        0.83 │
  │ Interest Coverage  31.9x   │            │ Cash / Assets     16.5% │
  │ Debt / Assets      34.8%   │            │ FCF / Debt        18.2% │
  └─────────────────────────────┘            └─────────────────────────┘

  VALUATION                                  EFFICIENCY
  ┌─────────────────────────────┐            ┌─────────────────────────┐
  │ P/E (TTM)          28.5x   │            │ Days Sales Out.    58.2 │
  │ P/E (Forward)      27.2x   │            │ Days Inventory     12.8 │
  │ EV/EBITDA          22.1x   │            │ Days Payable      105.3 │
  │ EV/Revenue          8.4x   │            │ Cash Conversion    0.86 │
  │ P/FCF              26.8x   │            │ CapEx / Revenue    2.8% │
  │ PEG Ratio           2.1x   │            │ R&D / Revenue      8.0% │
  │ FCF Yield           3.7%   │            │ SGA / Revenue      6.4% │
  │ Dividend Yield      0.52%  │            │                         │
  └─────────────────────────────┘            └─────────────────────────┘
```

Each ratio is clickable → expands to show:
- 5-year trend (sparkline)
- Sector median comparison
- Percentile rank within sector

### 3.2 Ratio Trend Charts

```
RATIO TRENDS — AAPL (5 Year)
────────────────────────────────────────────────────────────────────────
  Select metrics: [Gross Margin ✓] [Op Margin ✓] [Net Margin ✓] [FCF Margin]

  ┌──────────────────────────────────────────────────────────────┐
  │  50% ─ ──────────────────────────── Gross Margin             │
  │  40% ─                                                       │
  │  30% ─     ─────────────────────── Operating Margin          │
  │  25% ─     ──────────────────────── Net Margin               │
  │  20% ─                                                       │
  │        2020    2021    2022    2023    2024                   │
  └──────────────────────────────────────────────────────────────┘

  Toggle between:
  - Line chart (default — trends)
  - Bar chart (comparison across years)
  - vs. Sector median overlay (adds dashed line for sector median)
```

### 3.3 DuPont Analysis

Decomposition of ROE into its drivers:

```
DUPONT DECOMPOSITION — AAPL
────────────────────────────────────────────────────────────────────────

  ROE = Net Margin × Asset Turnover × Equity Multiplier
  171.6% = 26.6%   ×  1.07         ×  6.03

  ┌───────────┐     ┌──────────────┐     ┌──────────────────┐
  │ Profitab.  │  ×  │ Efficiency   │  ×  │ Leverage          │
  │            │     │              │     │                    │
  │ Net Margin │     │ Asset        │     │ Equity             │
  │  26.6%     │     │ Turnover     │     │ Multiplier         │
  │            │     │  1.07x       │     │  6.03x             │
  │ Trend: ↑   │     │ Trend: →     │     │ Trend: ↑           │
  └───────────┘     └──────────────┘     └──────────────────┘

  Interpretation:
  "AAPL's high ROE is primarily driven by leverage (equity multiplier
   of 6.0x due to share buybacks reducing equity base) and strong
   profitability (26.6% net margin). Asset efficiency is average at 1.07x.
   The high leverage figure is notable but not concerning — the company
   has net cash and the leverage is due to buybacks, not debt."
```

---

## Part 4: Company Profile

### 4.1 Profile Header

```
COMPANY PROFILE — AAPL
────────────────────────────────────────────────────────────────────────
  Apple Inc.                                    NASDAQ: AAPL
  Technology · Consumer Electronics             Cupertino, CA

  Market Cap: $2.83T    EV: $2.89T    Employees: ~164,000
  52W Range: $142.18 — $198.23        Avg Volume: 48.2M
  Beta: 1.24            Shares Out: 15.5B

  ABOUT
  Apple Inc. designs, manufactures, and markets smartphones, personal
  computers, tablets, wearables and accessories, and sells a variety
  of related services. The Company's products include iPhone, Mac,
  iPad, and Wearables, Home and Accessories. [Read more in 10-K →]

  SEGMENTS
  iPhone: 52%  |  Services: 24%  |  Mac: 10%  |  iPad: 7%  |  Other: 7%

  KEY DATES
  Next Earnings: Apr 24, 2026 (estimated)
  Next Ex-Dividend: Feb 28, 2026
  Fiscal Year End: September
────────────────────────────────────────────────────────────────────────
```

### 4.2 Peer Comparison Quick View

```
PEER COMPARISON
────────────────────────────────────────────────────────────────────────
                MCap     Rev Gr   Op Margin  ROE     P/E    EV/EBITDA
────────────────────────────────────────────────────────────────────────
► AAPL          $2.83T   2.0%     31.7%      171.6%  28.5   22.1x
  MSFT          $3.10T   13.4%    42.3%      38.2%   34.2   24.8x
  GOOGL         $2.05T   11.2%    28.7%      28.4%   24.1   17.2x
  META          $1.42T   15.8%    35.2%      32.1%   26.3   16.5x
  AMZN          $1.89T   12.1%    10.8%      22.8%   58.1   22.3x
────────────────────────────────────────────────────────────────────────
  Sector Med    —        10.2%    24.5%      18.5%   26.8   18.4x

  Peers auto-populated from Comps model if built.
  Otherwise uses Scanner peer detection.
  [Customize Peers →]  [Open Full Comps →]
────────────────────────────────────────────────────────────────────────
```

### 4.3 News & Events Feed

```
RECENT EVENTS — AAPL
────────────────────────────────────────────────────────────────────────
  ● Feb 25  8-K Filed    Earnings Release Q1 FY2026
  ● Feb 15  Ex-Dividend  $0.25 per share (record date: Feb 17)
  ● Jan 30  Earnings     Q1 FY2026: Revenue $124.3B (+4%), EPS $2.40
  ● Nov 03  10-K Filed   Annual Report FY 2025
  ● Oct 31  Earnings     Q4 FY2025: Revenue $95.4B (+6%), EPS $1.64

  Source: SEC EDGAR filing dates + Yahoo Finance earnings calendar
  [View All Events →]
────────────────────────────────────────────────────────────────────────
```

---

## Part 5: Segment Analysis

For companies with multiple business segments:

```
SEGMENT ANALYSIS — AAPL
────────────────────────────────────────────────────────────────────────

  REVENUE BY SEGMENT
  ┌──────────────────────────────────────────────────────────────┐
  │ $400B ─ ┌──┐                                                 │
  │         │  │                                                 │
  │ $300B ─ │  │ ┌──┐ ┌──┐ ┌──┐ ┌──┐                           │
  │         │  │ │  │ │  │ │  │ │  │                            │
  │ $200B ─ │  │ │  │ │  │ │  │ │  │                            │
  │         │  │ │  │ │  │ │  │ │  │                            │
  │ $100B ─ │  │ │  │ │  │ │  │ │  │                            │
  │         │  │ │  │ │  │ │  │ │  │                            │
  │         2020 2021 2022 2023 2024                             │
  │         ■ iPhone  ■ Services  ■ Mac  ■ iPad  ■ Other        │
  └──────────────────────────────────────────────────────────────┘
  Stacked bar chart — each segment a different shade

  SEGMENT DETAIL TABLE
  ┌────────────────────────────────────────────────────────────┐
  │ Segment      FY2022    FY2023    FY2024   Growth   % Total │
  │ iPhone       205,489   200,583   201,183  +0.3%    51.5%   │
  │ Services      78,129    85,200    96,169   +12.9%  24.6%   │
  │ Mac           40,177    29,357    30,746   +4.7%    7.9%   │
  │ iPad          29,292    28,300    26,694   -5.7%    6.8%   │
  │ Wearables     41,241    39,845    36,243   -9.0%    9.3%   │
  │ ─────────────────────────────────────────────────────────  │
  │ Total        394,328   383,285   391,035  +2.0%    100%    │
  └────────────────────────────────────────────────────────────┘

  GEOGRAPHIC BREAKDOWN (if available from filings)
  Americas: 42%  |  Europe: 26%  |  Greater China: 17%  |  Other: 15%
────────────────────────────────────────────────────────────────────────
```

---

## Part 6: Research Sub-Tab Structure

```
Research Sub-Tabs:
  Profile │ Financials │ Ratios │ Filings │ Segments │ Peers
```

- **Profile:** Company overview, key stats, description, events
- **Financials:** IS / BS / CF statements with custom view builder
- **Ratios:** Full ratio dashboard, trend charts, DuPont analysis
- **Filings:** Filing library, section viewer, filing comparison
- **Segments:** Revenue/profit breakdown by segment and geography
- **Peers:** Peer comparison table, relative metrics

---

## Part 7: Research Data Architecture

### 7.1 Data Flow

```
SEC EDGAR → Parser → filing_text table → Filing Viewer
                   → financial_data table → Financial Statements
                   → company_profiles table → Company Profile
                                            → Scanner (text search)
                                            → Assumption Engine (descriptions)
                                            → Comps (peer selection)

Yahoo Finance → market_data table → Valuation ratios
                                  → Price data
                                  → Earnings calendar

Everything feeds from the same database. Research doesn't fetch its own
data — it reads what's already been collected and parsed.
```

### 7.2 Filing Parser Specification

```
PARSER PIPELINE:

1. Fetch filing from SEC EDGAR (XBRL or HTML format)
2. Identify filing type (10-K, 10-Q, 8-K, DEF 14A)
3. Parse into sections based on Item headers
4. Extract financial tables → normalize to standard schema
5. Extract key text sections → store as searchable text
6. Extract segment data → store in segment tables
7. Compute derived metrics (margins, growth, ratios)
8. Update company_profiles with latest description and stats
9. Index text for full-text search (used by Scanner)

Parser handles:
  - XBRL inline (modern filings)
  - HTML-formatted filings (older)
  - Tables within filings (revenue segments, debt schedules, etc.)
  - Footnotes and annotations

Error handling:
  - If parser fails on a section, skip and flag
  - Never block entire filing parse due to one bad section
  - Log parse quality score per filing
```

---

## Part 8: Performance Targets

```
Filing section load:             < 500ms (text from database)
Financial statement render:      < 300ms (data already in DB)
Ratio calculation (all ratios):  < 200ms
Filing comparison (diff):        < 2s
Full filing text search:         < 3s (leverages Scanner index)
Segment chart render:            < 300ms
Peer comparison table:           < 500ms (data from Scanner/Comps)
```

---

*End of Phase 4 specification.*
