# Phase 1C — Comparable Companies (Comps) Model
> Designer Agent | February 25, 2026
> Status: COMPLETE — APPROVED BY FINN
> Depends on: Phase 1A (DCF Model), Phase 0B (Database Schema), Phase 0D (UI/UX Framework)

---

## Overview

The Comparable Companies model (Comps) estimates value by comparing a company's
trading multiples against a group of similar companies. This is a relative
valuation approach — it doesn't calculate intrinsic value from fundamentals
like DCF/DDM, but instead answers "what should this company be worth if it
traded like its peers?"

This is standard practice on Wall Street — every equity research report includes
a comps table alongside the DCF.

**Key decisions:**
- Auto-suggest peers with manual override (engine uses stored company data,
  financial metrics, and 10-K business descriptions)
- Comprehensive comparable tables with multiples, growth, and profitability metrics
- Quality premium/discount framework for adjusting implied valuation
- Sub-tabs: Overview | Historical Data | Peer Selection | Comps Table | Valuation | Sensitivity | History

---

## Peer Selection Engine

### How Auto-Selection Works

The engine finds comparable companies using data already in our database:

```
Step 1: Industry Match
  - Pull companies in the same GICS sector/industry from scanner universe
  - Use 10-K business descriptions (stored in research/filing cache) to
    identify companies with similar business models
  - Weight: 40% of similarity score

Step 2: Size Match
  - Filter to companies within 0.3x - 3.0x market cap range of target
  - Closer market cap = higher score
  - Weight: 25% of similarity score

Step 3: Growth Profile Match
  - Compare revenue growth rates (3Y CAGR)
  - Compare earnings growth rates (3Y CAGR)
  - Closer growth profile = higher score
  - Weight: 20% of similarity score

Step 4: Profitability Match
  - Compare operating margins, ROE, ROIC
  - Weight: 15% of similarity score

Output: Ranked list of candidates with similarity scores (0-100)
Default selection: Top 5-8 peers with score > 60
```

### Data Sources for Peer Selection

All from existing database tables — no external API calls needed at selection time:

- **Company profiles:** Sector, industry, market cap, business description
  (from scanner data + 10-K parsing)
- **Financial metrics:** Revenue, earnings, margins, growth rates
  (from financial_data table)
- **Market data:** Current multiples, market cap
  (from market_data table / Yahoo Finance cache)

### Peer Selection UI

```
PEER SELECTION — AAPL
────────────────────────────────────────────────────────────────────────
  Auto-Selected Peers (5)                           [+ Add Peer]

  ┌────────────────────────────────────────────────────────────────┐
  │  ✓  MSFT   Microsoft Corp      Tech · Software    Score: 87   │  [×]
  │  ✓  GOOGL  Alphabet Inc        Tech · Internet    Score: 82   │  [×]
  │  ✓  SAMSUNG Samsung Elec       Tech · Hardware    Score: 74   │  [×]
  │  ✓  META   Meta Platforms      Tech · Internet    Score: 71   │  [×]
  │  ✓  AMZN   Amazon.com          Tech · E-Commerce  Score: 68   │  [×]
  └────────────────────────────────────────────────────────────────┘

  Suggested Alternatives:
  │  ○  NVDA   NVIDIA Corp         Tech · Semicon     Score: 65   │  [+]
  │  ○  CRM    Salesforce          Tech · Software    Score: 62   │  [+]
  │  ○  ADBE   Adobe Inc           Tech · Software    Score: 61   │  [+]

  [Search to add any company...]
────────────────────────────────────────────────────────────────────────
  Min peers: 3    Max peers: 15    Recommended: 5-8
```

- Checkmark (✓) = included in analysis
- [×] = remove from selection
- [+] = add to selection
- Score displayed but subtle (--text-secondary)
- Search bar at bottom allows adding any company in the database
- User has full control — can ignore all suggestions and pick manually

---

## Comps Table

The core output. Bloomberg-style comparable company table with the target
company highlighted.

### Standard Multiples

| Category | Multiples |
|----------|-----------|
| Earnings | P/E (trailing), P/E (forward), PEG Ratio |
| Enterprise Value | EV/EBITDA, EV/EBIT, EV/Revenue |
| Book Value | P/B, P/TBV (tangible book) |
| Cash Flow | P/FCF, EV/FCF |

### Growth & Profitability Metrics (displayed alongside multiples)

| Category | Metrics |
|----------|---------|
| Growth | Revenue Growth (1Y, 3Y CAGR), EPS Growth (1Y, 3Y CAGR) |
| Profitability | Gross Margin, Operating Margin, Net Margin, ROE, ROIC |
| Returns | Dividend Yield, Total Return (1Y) |
| Size | Market Cap, Enterprise Value, Revenue (TTM) |

### Table Layout

```
COMPARABLE COMPANIES TABLE — AAPL
────────────────────────────────────────────────────────────────────────────────
                MCap     EV/      EV/     P/E    P/E    PEG    P/FCF   Rev     Op
Company         ($B)     EBITDA   Rev     (TTM)  (Fwd)  Ratio  (TTM)   Gr 3Y   Margin
────────────────────────────────────────────────────────────────────────────────
► AAPL          2,830    22.1x    8.4x    28.5   27.2   2.1x   26.8    8.2%    30.1%
  MSFT          3,100    24.8x    12.1x   34.2   31.5   1.8x   32.1    13.4%   42.3%
  GOOGL         2,050    17.2x    6.8x    24.1   22.8   1.2x   22.5    11.2%   28.7%
  META          1,420    16.5x    8.2x    26.3   24.1   1.1x   21.8    15.8%   35.2%
  AMZN          1,890    22.3x    3.2x    58.1   42.3   2.8x   38.2    12.1%   10.8%
  SAMSUNG         380    8.4x     1.8x    18.2   15.4   1.4x   14.2    4.2%    15.3%
────────────────────────────────────────────────────────────────────────────────
  Mean                   17.8x    6.4x    32.2   27.2   1.7x   25.9    11.3%   26.4%
  Median                 19.7x    7.5x    27.4   25.5   1.5x   24.2    12.1%   29.4%
  Trimmed Mean           19.2x    7.2x    28.5   25.8   1.4x   24.8    11.8%   28.3%
────────────────────────────────────────────────────────────────────────────────
```

**Design rules:**
- Target company (AAPL) highlighted with ► arrow and --accent-subtle background
- Summary statistics at bottom separated by a thicker border
- All multiples right-aligned, JetBrains Mono
- Company names left-aligned, Inter
- Column headers: 11px Inter Semi-Bold UPPERCASE
- Zebra striping on peer rows (not on target or summary rows)
- Columns sortable by clicking header
- Outliers highlighted in --text-tertiary (dimmed) — see outlier handling below

### Outlier Handling

Outliers distort averages. The engine handles them automatically:

```
Method: Modified Z-Score

1. Calculate median and MAD (Median Absolute Deviation) for each multiple
2. Flag values with Modified Z-Score > 3.0 as outliers
3. Outlier values displayed in --text-tertiary (dimmed) in the table
4. Trimmed Mean excludes outliers
5. User can manually include/exclude flagged outliers via toggle

Summary row shows three statistics:
  Mean:          Simple average (includes outliers, for reference)
  Median:        Middle value (naturally resistant to outliers)
  Trimmed Mean:  Mean excluding flagged outliers (PRIMARY metric for valuation)
```

---

## Valuation Tab — Implied Value Range

### Implied Valuation from Each Multiple

```
IMPLIED VALUATION — AAPL
Using Trimmed Mean of Peer Multiples
────────────────────────────────────────────────────────────────────────
Multiple        Peer Trimmed Mean    AAPL Metric    Implied Price
────────────────────────────────────────────────────────────────────────
EV/EBITDA       19.2x               $129.6B         $196.42
EV/Revenue      7.2x                $394.3B         $177.83
P/E (Fwd)       25.8x               $6.82            $175.96
P/FCF           24.8x               $112.4B          $174.21
EV/EBIT         22.4x               $118.7B         $168.54
PEG             1.4x                (EPS Gr: 8.2%)   $164.92
P/E (TTM)       28.5x               $6.42            $183.07
────────────────────────────────────────────────────────────────────────
Implied Range:                      $164.92 — $196.42
Median Implied:                     $175.96
Current Price:                      $182.52
────────────────────────────────────────────────────────────────────────
```

### Quality Premium/Discount Adjustment

Not all companies deserve to trade at the peer median. The engine assesses
whether the target company deserves a premium or discount:

```
QUALITY ASSESSMENT — AAPL
────────────────────────────────────────────────────────────────────────
Factor                  vs. Peers       Assessment      Adjustment
────────────────────────────────────────────────────────────────────────
Revenue Growth          Below median     Discount        -5%
Operating Margin        Above median     Premium         +5%
ROE                     Above median     Premium         +5%
Earnings Consistency    High             Premium         +3%
Balance Sheet Strength  Strong           Premium         +2%
────────────────────────────────────────────────────────────────────────
Net Quality Adjustment:                                  +10%

Adjusted Implied Range:   $181.41 — $216.06
Adjusted Median:          $193.56
```

**Quality factors and their logic:**

| Factor | Metric | Premium Trigger | Discount Trigger |
|--------|--------|-----------------|------------------|
| Revenue Growth | 3Y CAGR vs peer median | > peer P75 → +5% | < peer P25 → -5% |
| Operating Margin | Op margin vs peer median | > peer P75 → +5% | < peer P25 → -5% |
| Return on Equity | ROE vs peer median | > peer P75 → +5% | < peer P25 → -5% |
| Earnings Consistency | Std dev of EPS growth | Low vol → +3% | High vol → -3% |
| Balance Sheet | Net Debt/EBITDA | < 1.0x → +2% | > 3.0x → -2% |
| Dividend Track Record | Consecutive growth years | > 10 years → +2% | Cuts → -2% |

Maximum total adjustment: ±20%
All adjustments are overridable by the user.

### Valuation Visualization — Football Field Chart

```
COMPS VALUATION RANGE — AAPL
                                        Current: $182.52
                                             │
  EV/EBITDA    ████████████████████████████   │
  EV/Revenue   ██████████████████████         │
  P/E (Fwd)    █████████████████████          │
  P/FCF        ████████████████████           │
  Composite    ██████████████████████████     │
               ────────────────────────────────────
               $140   $160   $180   $200   $220

  Blue bars:     Raw peer-implied range (P25 to P75 of peer multiples)
  Current price: Dashed vertical line (--text-primary)
```

Each bar shows the range from P25 to P75 of the implied values using
that multiple across all peers (not just the trimmed mean). This gives
a visual sense of the spread.

---

## Sensitivity for Comps

Comps sensitivity differs from DCF/DDM because it's relative valuation.
The Sensitivity sub-tab shows:

**Sliders:** Adjust the quality premium/discount. See how implied value
changes as you adjust individual quality factors.

**Tables:** 2D grid showing implied value at different combinations of
peer median multiples. Default axes: EV/EBITDA × P/E, showing implied
share price at each intersection.

**Tornado:** Which multiple has the biggest impact on the composite
implied value? Shows sensitivity of the final number to each multiple's
peer median.

**Monte Carlo:** Not applicable for Comps (no probabilistic model).
This sub-tab is hidden when viewing a Comps model.

---

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| Fewer than 3 peers available | Warning: "Insufficient peers for reliable comparison. Add more comparable companies." Allow calculation but flag as low confidence. |
| Target company is unique (no good peers) | Low auto-detection score for Comps. If user forces it, suggest broadening industry definition or using global peers. |
| Peer has negative earnings (P/E undefined) | Exclude that peer from P/E calculations. Note in table: "N/M" (Not Meaningful). |
| Extreme outlier peer (10x larger/smaller) | Flagged by outlier detection, dimmed in table, excluded from trimmed mean. |
| Missing data for a peer | Show "—" for missing fields. Peer still included in calculations where data exists. |
| All peers are in different country | Currency conversion applied automatically. Note in table footer. |

---

## Sub-Tab Structure

```
Comps Model Builder Sub-Tabs:
  Overview | Historical Data | Peer Selection | Comps Table | Valuation | Sensitivity | History
```

- **Overview:** Composite implied value, football field chart, quality adjustment summary
- **Historical Data:** Same Bloomberg-style table as DCF/DDM — target company financials
- **Peer Selection:** Auto-suggest + manual peer management (described above)
- **Comps Table:** Full comparable table with multiples + growth + profitability
- **Valuation:** Implied value from each multiple, quality premium/discount, range
- **Sensitivity:** Sliders (quality factors) | Tornado | Tables (no Monte Carlo)
- **History:** Version history + diff view (same pattern as DCF/DDM)

---

*End of Phase 1C specification.*
