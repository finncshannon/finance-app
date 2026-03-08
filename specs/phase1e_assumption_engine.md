# Phase 1E — Assumption Engine Methodology
> Designer Agent | February 26, 2026
> Status: COMPLETE — APPROVED BY FINN
> Depends on: Phase 1A (DCF), Phase 1B (DDM), Phase 1C (Comps), Phase 1D (Revenue-Based)

---

## Overview

The Assumption Engine is the analytical brain of the Finance App. It examines
a company's historical financial data, market context, and sector characteristics
to generate every assumption needed by every valuation model — revenue growth rates,
margin projections, WACC components, scenario ranges, terminal values, and more.

This is NOT a simple heuristic system. It is a multi-layered analytical framework
that mirrors the judgment process of an experienced equity research analyst. Every
assumption it produces comes with a full reasoning trail explaining which data
points were examined, which methods were applied, and why the output value was chosen.

**Design philosophy:**
- Transparency over black-box magic — every assumption is explainable
- Multiple analytical lenses, not a single formula — the engine considers
  several approaches and synthesizes them
- Conservative by default, aggressive only when data justifies it
- Graceful degradation — works with limited data, gets better with more
- Always overridable — the engine suggests, the user decides

**Key decisions:**
- Revenue growth uses fixed analytical windows (3Y, 5Y, 10Y CAGR) with
  divergence detection and regime flagging
- Margin projection uses mean reversion for stable companies, trend continuation
  with caps for growth companies, with additional layered analysis
- Scenario spread uses both historical volatility AND multi-factor uncertainty
  scoring for robust range determination
- Every assumption includes a confidence score and reasoning string

---

## Part 1: Architecture

### 1.1 Engine Pipeline

Every assumption generation follows the same pipeline:

```
┌─────────────────────────────────────────────────────────────────┐
│                    ASSUMPTION ENGINE PIPELINE                    │
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│  │  GATHER   │ →  │ ANALYZE  │ →  │SYNTHESIZE│ →  │  OUTPUT   │ │
│  │          │    │          │    │          │    │          │ │
│  │ Pull all │    │ Run each │    │ Weight & │    │ Format   │ │
│  │ relevant │    │ analytical│   │ combine  │    │ assumption│ │
│  │ data for │    │ lens on  │    │ lens     │    │ + reason │ │
│  │ this     │    │ the data │    │ outputs  │    │ + conf.  │ │
│  │ company  │    │          │    │          │    │ score    │ │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘ │
│                                                                 │
│  Data Sources:    Analytical        Weighting       Output:     │
│  - Financials     Lenses:           Logic:          - Value     │
│  - Market data    - Trend           - Data quality  - Reasoning │
│  - Peer data      - Mean reversion  - Relevance     - Confidence│
│  - Sector stats   - Sector gravity  - Recency       - Method    │
│  - Filing data    - Regime detect   - Stability     - Sources   │
│  - Macro data     - Statistical                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Data Gathering Layer

Before any analysis begins, the engine assembles a complete data package
for the target company:

```
CompanyDataPackage {
  // Core financials (from financial_data table)
  revenue:            TimeSeriesData[]      // 10+ years if available
  grossProfit:        TimeSeriesData[]
  operatingIncome:    TimeSeriesData[]
  netIncome:          TimeSeriesData[]
  eps:                TimeSeriesData[]
  freeCashFlow:       TimeSeriesData[]
  totalDebt:          TimeSeriesData[]
  cashAndEquiv:       TimeSeriesData[]
  sharesOutstanding:  TimeSeriesData[]
  dividendsPerShare:  TimeSeriesData[]
  capex:              TimeSeriesData[]
  depreciation:       TimeSeriesData[]
  interestExpense:    TimeSeriesData[]
  taxExpense:         TimeSeriesData[]
  totalAssets:        TimeSeriesData[]
  totalEquity:        TimeSeriesData[]
  workingCapital:     TimeSeriesData[]

  // Market data (from market_data table / Yahoo Finance)
  currentPrice:       number
  marketCap:          number
  enterpriseValue:    number
  beta:               number
  sharesFloat:        number
  avgVolume:          number

  // Sector context (from scanner universe / peer data)
  sector:             string
  industry:           string
  sectorMedians: {
    revenueGrowth:    number
    operatingMargin:  number
    netMargin:        number
    roe:              number
    roic:             number
    debtToEbitda:     number
    evToEbitda:       number
    peRatio:          number
  }
  sectorPercentiles: {
    p10: SectorMedians
    p25: SectorMedians
    p50: SectorMedians
    p75: SectorMedians
    p90: SectorMedians
  }

  // Filing data (from research/filing cache)
  businessDescription:  string     // From 10-K
  riskFactors:          string[]   // Key risks from 10-K
  segmentRevenue:       SegmentData[]  // Revenue by segment if available

  // Macro data
  riskFreeRate:         number     // 10Y Treasury yield
  gdpGrowthRate:        number     // Long-term GDP growth estimate
  cpiInflation:         number     // Current CPI
}
```

**Data quality assessment:**

Before analysis, the engine scores data quality (0-100):

| Factor | Points | Criteria |
|--------|--------|----------|
| History depth | 0-30 | <3 years: 5, 3-5 years: 15, 5-10 years: 25, 10+: 30 |
| Data completeness | 0-25 | Percentage of line items with non-null values |
| Data consistency | 0-20 | No unexplained gaps, sign changes make sense |
| Filing availability | 0-15 | 10-K parsed: +10, 10-Q available: +5 |
| Market data freshness | 0-10 | Updated today: 10, this week: 7, older: 3 |

**Quality thresholds:**
- 80-100: Full confidence, all analytical lenses available
- 60-79: Good confidence, some lenses may be limited
- 40-59: Limited confidence, flag assumptions with wider uncertainty
- 20-39: Low confidence, warn user prominently
- 0-19: Insufficient data, block auto-generation, require manual input

---

## Part 2: Revenue Growth Projection

Revenue growth is the most important assumption in the system. It cascades
into every model — DCF projections, DDM dividend growth, Revenue-Based
valuation, and even Comps (growth profile affects peer selection).

### 2.1 Analytical Windows

The engine always computes three growth windows:

```
3-Year CAGR:  Most recent 3 fiscal years
5-Year CAGR:  Most recent 5 fiscal years
10-Year CAGR: Most recent 10 fiscal years (or max available)

Each window computed as:
  CAGR = (Revenue_end / Revenue_start)^(1/n) - 1
```

These are the foundation. The engine presents all three to the user and
explains which one it chose as the primary basis and why.

### 2.2 Divergence Detection

When the windows tell different stories, the engine flags it:

```
Divergence Score = max(|3Y - 5Y|, |3Y - 10Y|, |5Y - 10Y|)

If Divergence Score > 5 percentage points:
  → FLAG: "Growth windows show significant divergence"
  → Explain what changed (e.g., "3Y CAGR of 25% vs 10Y CAGR of 8%
     suggests a growth acceleration beginning around 2021")

If 3Y > 5Y > 10Y (accelerating):
  → FLAG: "Growth is accelerating"
  → Engine weights 3Y more heavily

If 3Y < 5Y < 10Y (decelerating):
  → FLAG: "Growth is decelerating"
  → Engine weights 3Y more heavily but projects further deceleration

If 3Y diverges from both 5Y and 10Y (which are similar):
  → FLAG: "Recent growth may be an anomaly"
  → Engine examines whether the 3Y period contains one-time events
     (acquisitions, divestitures, COVID impacts, etc.)
```

### 2.3 Regime Detection

The engine attempts to identify whether the company is in a stable growth
regime or at an inflection point:

```
REGIME CLASSIFICATION:

Stable Growth:
  - 3Y, 5Y, 10Y CAGRs within 3pp of each other
  - Year-over-year growth rates have low standard deviation (<5pp)
  - Action: Use full historical average with equal weighting

Accelerating Growth:
  - 3Y CAGR > 5Y CAGR by >5pp
  - Last 2 years show sequential acceleration
  - Action: Weight 3Y heavily, project continuation with deceleration curve

Decelerating Growth:
  - 3Y CAGR < 5Y CAGR by >5pp
  - Last 2 years show sequential slowdown
  - Action: Weight 3Y heavily, project continued deceleration toward
    terminal growth rate

Cyclical:
  - Year-over-year growth alternates between high and low
  - Standard deviation of YoY growth > 10pp
  - Action: Use through-cycle average (full history), note cyclicality

Inflection / Disruption:
  - Step-change in growth rate (>15pp shift in a single year)
  - Sustained at new level for 2+ years
  - Action: Discard pre-inflection data, use post-inflection window only

Recovery:
  - Negative growth in recent history followed by positive
  - Action: Use pre-decline growth rate as "normalized" target,
    model recovery trajectory toward it
```

### 2.4 Growth Curve Construction

Once the engine selects a base growth rate, it constructs the full
10-year projection curve:

```
GROWTH CURVE SHAPES:

Linear Deceleration (default for most companies):
  Year 1 growth = base rate
  Each subsequent year: growth decreases by fixed step
  Step = (base rate - terminal rate) / projection years
  Example: 15% → 13.7% → 12.4% → 11.1% → 9.8% → ... → 3%

S-Curve (for high-growth companies):
  Growth stays elevated for N years, then decelerates sharply
  Useful for companies with strong competitive moats and long runways
  Modeled as: g(t) = terminal + (base - terminal) / (1 + e^(k*(t-midpoint)))

Front-Loaded Deceleration (for mature growth companies):
  Growth drops more in early years, flattens toward terminal
  Modeled as exponential decay: g(t) = terminal + (base - terminal) * e^(-λt)

Custom (user override):
  User sets growth rate for each year individually
```

**How the engine selects the curve shape:**

| Company Profile | Growth Rate | Curve |
|-----------------|-------------|-------|
| Mature, stable (JNJ, PG) | <8% | Linear deceleration (short, gentle) |
| Moderate growth (AAPL, MSFT) | 8-15% | Linear deceleration |
| High growth (CRM, SNOW) | 15-30% | S-curve or front-loaded |
| Hyper growth (early-stage) | >30% | S-curve with steep deceleration |
| Cyclical (XOM, FCX) | Varies | Through-cycle average, flat |
| Turnaround / recovery | Negative → positive | Recovery curve to normalized |

### 2.5 Terminal Growth Rate

The long-run sustainable growth rate used in perpetuity calculations:

```
Base anchor: Long-term nominal GDP growth (currently ~4-5% nominal,
  which is ~2-3% real + ~2% inflation)

Adjustments:
  + Company grows faster than GDP historically AND has structural advantages
    → can justify up to GDP + 1% (max ~5-6%)
  - Company in secular decline, shrinking market
    → below GDP, potentially 0-1%

Hard constraints:
  - Terminal growth MUST be < risk-free rate (otherwise math breaks)
  - Terminal growth SHOULD be ≤ nominal GDP growth (a company cannot
    grow faster than the economy forever without becoming the economy)
  - Floor: 0% (companies can stagnate but we don't project negative
    perpetuity growth — that's a liquidation scenario)

Sector-specific defaults:
  Technology:       2.5% (slightly below GDP, reflects rapid change)
  Healthcare:       3.0% (aging population tailwind)
  Consumer Staples: 2.5% (inflation pass-through)
  Utilities:        2.0% (regulated, slow growth)
  Financials:       2.5% (GDP-linked)
  Energy:           1.5% (transition uncertainty)
  REITs:            2.5% (inflation-linked rents)
```

### 2.6 Revenue Growth Reasoning Output

For every revenue growth assumption, the engine produces:

```
REVENUE GROWTH ASSUMPTION: 12.5% (Year 1), declining to 3.0% (Terminal)
Confidence: 78/100
Curve: Linear deceleration

REASONING:
"Revenue growth set at 12.5% for Year 1 based on the 3-year CAGR of 13.4%,
which was selected as the primary window because:

  1. Growth windows: 3Y CAGR 13.4% | 5Y CAGR 11.2% | 10Y CAGR 9.1%
     → Moderate acceleration detected. 3Y reflects current trajectory.

  2. Regime: Stable-to-accelerating. Last 3 years: 11.8%, 13.1%, 15.4%.
     Sequential acceleration, but 15.4% appears elevated — using 3Y average
     (13.4%) as more sustainable than last single year.

  3. Slight haircut applied (13.4% → 12.5%) because:
     - Company is approaching sector P75 for growth (14.2%)
     - Larger companies historically find it harder to sustain high growth
     - Market cap of $2.8T implies significant base effect

  4. Terminal rate: 3.0% (sector default for Technology)

  5. Deceleration: Linear over 10 years from 12.5% to 3.0%.

Data quality: 92/100 (10 years of clean revenue data, recent 10-K parsed)
Primary data points: Annual revenue 2015-2024, sector growth distribution"
```

---

## Part 3: Margin Projections

The engine projects gross margin, operating margin, EBITDA margin, and net margin.
Each follows a layered analytical approach.

### 3.1 Analytical Lenses for Margins

The engine applies multiple lenses and synthesizes:

**Lens 1: Historical Mean Reversion**
```
Assumption: Margins tend to revert to the company's own long-term average.
Method:
  - Calculate 5Y average margin
  - Calculate 10Y average margin (if available)
  - Current margin vs. average tells direction
  - Project gradual convergence to average over 5-7 years
  - Speed of reversion depends on how far current is from average

When to weight heavily:
  - Stable businesses with consistent margins (score: HIGH)
  - Cyclical businesses at mid-cycle (score: MEDIUM)

When to weight lightly:
  - Company undergoing structural change (score: LOW)
  - Margins trending strongly in one direction for 3+ years (score: LOW)
```

**Lens 2: Trend Continuation with Caps**
```
Assumption: Current margin trajectory continues, bounded by sector reality.
Method:
  - Fit linear trend to last 5 years of margins
  - Extend trend forward
  - Cap expansion at sector P90 (90th percentile)
  - Floor contraction at sector P10 (10th percentile)
  - If trend would breach cap/floor, flatten at boundary

When to weight heavily:
  - Growth companies with expanding margins (score: HIGH)
  - Companies in active restructuring/cost-cutting (score: HIGH)
  - Clear secular trend supported by business model shift (score: HIGH)

When to weight lightly:
  - Mature companies with stable margins (score: LOW)
  - Short-lived margin spikes/dips (score: LOW)
```

**Lens 3: Sector Gravity**
```
Assumption: Competition pulls margins toward industry equilibrium over time.
Method:
  - Calculate sector median margin for the company's industry
  - Project gradual convergence toward sector median
  - Speed depends on competitive dynamics and barriers to entry

When to weight heavily:
  - Commodity businesses, low differentiation (score: HIGH)
  - Industries with intensifying competition (score: MEDIUM)
  - Companies with margins far from sector median (score: MEDIUM)

When to weight lightly:
  - Companies with structural moats (brands, network effects, patents)
  - Monopolies or oligopolies (score: LOW)
  - Companies in niche industries with no clear peers (score: LOW)
```

**Lens 4: Margin Decomposition (Advanced)**
```
Assumption: Understanding WHY margins are where they are predicts where they go.
Method:
  - Decompose operating margin into:
    Gross Margin (pricing power, COGS trends)
    SGA as % of Revenue (operating leverage, scaling)
    R&D as % of Revenue (investment phase vs. harvesting)
  - Project each component separately
  - Rebuild operating margin from components

When to use:
  - When filing data provides line-item detail
  - When one component is driving the margin story
    (e.g., SGA leverage as company scales)
  - When gross margin and operating margin tell different stories

This lens is the most sophisticated and is weighted heavily when
data quality is high and components show clear trends.
```

### 3.2 Lens Synthesis for Margins

The engine weights the lenses based on company characteristics:

```
WEIGHTING MATRIX:

                      Mean Rev.  Trend+Cap  Sector Grav.  Decomposition
Stable/Mature          0.45       0.10       0.20          0.25
Growth (expanding)     0.10       0.40       0.15          0.35
Cyclical (mid-cycle)   0.35       0.10       0.30          0.25
Cyclical (peak/trough) 0.15       0.10       0.45          0.30
Turnaround             0.05       0.45       0.20          0.30
Declining              0.20       0.30       0.30          0.20

Weights are normalized to sum to 1.0.
Decomposition weight is reduced to 0 if filing data is insufficient.
```

### 3.3 Margin-Specific Considerations

**Gross Margin:**
- Most stable of all margins — usually mean-reverts strongly
- Structural shifts (e.g., hardware → services) detected by 3+ year trend
- Inflation impact: if COGS is commodity-heavy, wider uncertainty band

**Operating Margin:**
- Subject to operating leverage effects (fixed costs vs. revenue growth)
- SGA leverage: if SGA as % of revenue is declining, margin expansion is
  structural (not just cyclical)
- R&D investment: high R&D spend depresses margins but may signal future growth

**EBITDA Margin:**
- Preferred for capital-intensive businesses
- Less affected by depreciation policy differences
- Engine calculates from Operating Income + D&A

**Net Margin:**
- Most volatile, affected by tax rates, interest, one-time items
- Engine normalizes for one-time charges before projecting
- Tax rate assumed to converge to effective rate (not statutory) unless
  there's a clear reason for change (e.g., tax reform, geographic shift)

### 3.4 Margin Reasoning Output

```
OPERATING MARGIN ASSUMPTION: 31.5% (Year 1), expanding to 33.0% (Year 5), 
  stable at 33.0% (Years 6-10)
Confidence: 82/100

REASONING:
"Operating margin projected at 31.5% for Year 1 (current TTM: 30.1%),
expanding modestly to 33.0% by Year 5. Synthesized from four analytical lenses:

  Lens 1 — Mean Reversion (weight: 0.15):
    5Y average: 29.8%. 10Y average: 28.2%. Current above both averages.
    This lens suggests slight contraction. However, weighted low because
    margins have been in a structural uptrend.

  Lens 2 — Trend Continuation (weight: 0.35):
    5Y linear trend: +0.8pp per year. Extending forward suggests 34.1% by
    Year 5. Capped at sector P90 (35.2%). This lens drives the expansion
    assumption.

  Lens 3 — Sector Gravity (weight: 0.15):
    Sector median operating margin: 22.4%. Company is well above sector
    median, but this appears structural (brand premium, ecosystem lock-in)
    rather than cyclical. Gravity effect minimal.

  Lens 4 — Decomposition (weight: 0.35):
    Gross margin: 45.2%, stable (±0.3pp over 5 years). No change projected.
    SGA/Revenue: declining from 15.2% to 13.8% over 5 years (operating leverage).
    R&D/Revenue: stable at 7.1%. Company maintains consistent R&D investment.
    → Rebuilt operating margin: 31.5% → 33.0% driven by SGA leverage.
    This is the most compelling lens and aligns with the trend continuation.

  Synthesis: Weighted output = 32.4%. Rounded to nearest 0.5pp = 31.5% Year 1
    (conservative start, giving room for the expansion story to play out).
    33.0% by Year 5 represents the convergence of trend and decomposition.
    Stable at 33.0% for Years 6-10 (operating leverage benefits fully realized).

  Key risk: Margin expansion assumes continued SGA leverage. If the company
  enters a new investment cycle (e.g., new product category), SGA could
  re-accelerate and compress margins."
```

---

## Part 4: WACC / Required Return Calibration

### 4.1 Cost of Equity (CAPM)

```
Cost of Equity = Risk-Free Rate + Beta × Equity Risk Premium

Components:
  Risk-Free Rate:
    Source: 10-year US Treasury yield (auto-fetched)
    Updated: daily (from Treasury API or Yahoo Finance)
    Override: user can set manually

  Beta:
    Source: Yahoo Finance (5-year monthly, vs S&P 500)
    Validation: if beta < 0.3 or > 3.0, flag as potentially unreliable
    Alternative: if Yahoo beta seems wrong, engine calculates from
      available price data as sanity check
    Override: user can set manually
    Default for private/limited data: sector average beta

  Equity Risk Premium (ERP):
    Source: User-configured default (stored in settings)
    Suggested range: 4.5% - 6.5%
    Default: 5.5% (Damodaran's current estimate as starting point)
    Context: engine shows Damodaran's current implied ERP for reference
    Override: per-model adjustable

  Size Premium (optional, advanced):
    For small-cap companies (market cap < $2B), academic research suggests
    an additional size premium of 1-3%
    Engine auto-applies based on market cap bracket:
      Mega cap (>$200B):  0.0%
      Large cap ($10-200B): 0.0%
      Mid cap ($2-10B):   0.5%
      Small cap ($300M-2B): 1.5%
      Micro cap (<$300M): 2.5%
    Display: shown as separate line item in WACC build-up
    Override: user can adjust or disable
```

### 4.2 Cost of Debt

```
Cost of Debt (pre-tax) = Interest Expense / Average Total Debt

If data available:
  - Use actual interest expense from income statement
  - Divide by average of beginning and ending total debt
  - This gives the company's actual borrowing cost

If interest expense not available:
  - Estimate from credit rating (if available in filings)
  - Fall back to: Risk-Free Rate + Credit Spread
  - Credit spread estimated from interest coverage ratio:
      Coverage > 8x:   +1.0% (AAA/AA equivalent)
      Coverage 4-8x:   +1.5% (A equivalent)
      Coverage 2.5-4x: +2.5% (BBB equivalent)
      Coverage 1.5-2.5x: +4.0% (BB equivalent)
      Coverage < 1.5x: +6.0% (B or below equivalent)

After-tax cost of debt = Pre-tax cost × (1 - Effective Tax Rate)

Effective Tax Rate:
  - Calculated from: Tax Expense / Pre-Tax Income
  - Use 3-year average to smooth one-time items
  - Floor: 0% (loss-making companies)
  - Cap: statutory rate of jurisdiction (21% US federal + state estimate)
  - If effective rate is far from statutory, note in reasoning
```

### 4.3 Capital Structure Weights

```
Equity Weight = Market Cap / (Market Cap + Total Debt)
Debt Weight = Total Debt / (Market Cap + Total Debt)

Use market values, not book values (finance theory standard).

For companies with no debt: WACC = Cost of Equity (debt weight = 0)
For companies with preferred stock: add as third component if material
```

### 4.4 WACC Assembly

```
WACC = (Equity Weight × Cost of Equity) + (Debt Weight × After-Tax Cost of Debt)

Example build-up:

WACC CALCULATION — AAPL
────────────────────────────────────────────────
COST OF EQUITY                           9.2%
  Risk-Free Rate            3.8%
  Beta                      1.24
  Equity Risk Premium       5.5%
  Size Premium              0.0%     (mega cap)
  Beta × ERP               6.8%
  Ke = 3.8% + 6.8%       = 10.6%

COST OF DEBT (after-tax)                 2.8%
  Interest Expense          $3.9B
  Average Total Debt        $112B
  Pre-tax Cost of Debt      3.5%
  Effective Tax Rate        16.2%
  Kd(1-t) = 3.5% × 83.8% = 2.9%

CAPITAL STRUCTURE
  Equity (market value)     $2,830B   96.2%
  Debt (book value)         $112B      3.8%

WACC = (96.2% × 10.6%) + (3.8% × 2.9%) = 10.3%
────────────────────────────────────────────────
```

### 4.5 WACC Reasonableness Checks

The engine validates the assembled WACC:

| Check | Trigger | Action |
|-------|---------|--------|
| WACC < 5% | Unusually low | Warning: "WACC below 5% is rare. Verify beta and ERP assumptions." |
| WACC > 15% | Unusually high | Warning: "WACC above 15% typically seen only in high-risk/emerging market companies." |
| WACC < risk-free rate | Mathematically problematic | Error: "WACC cannot be below risk-free rate. Check inputs." |
| Cost of debt > cost of equity | Unusual | Warning: "Cost of debt exceeding cost of equity is atypical. Company may be in financial distress." |
| Negative debt weight | Net cash position | Note: "Company has net cash. Debt weight set to 0." |

---

## Part 5: Scenario Generation

### 5.1 Uncertainty Scoring

The engine scores each company's uncertainty on a 0-100 scale using
multiple factors:

```
UNCERTAINTY SCORING MODEL

Factor 1: Earnings Volatility (0-20 points)
  Standard deviation of YoY EPS growth over available history
  Low (<10pp std dev):     5 points
  Medium (10-25pp):        12 points
  High (>25pp):            20 points

Factor 2: Revenue Predictability (0-15 points)
  Standard deviation of YoY revenue growth
  Low (<5pp):              3 points
  Medium (5-15pp):         8 points
  High (>15pp):            15 points

Factor 3: Margin Stability (0-15 points)
  Range (max - min) of operating margin over 5 years
  Narrow (<5pp range):     3 points
  Medium (5-15pp):         8 points
  Wide (>15pp):            15 points

Factor 4: Company Maturity (0-10 points)
  Public history + market cap as proxy for stability
  Large cap, 10+ years:    2 points
  Mid cap, 5-10 years:     5 points
  Small cap, <5 years:     8 points
  Recent IPO:              10 points

Factor 5: Sector Cyclicality (0-10 points)
  Based on sector classification:
  Defensive (utilities, staples, healthcare): 2 points
  Moderate (tech, industrials, financials):   5 points
  Cyclical (energy, materials, discretionary): 8 points
  Speculative (biotech, crypto-adjacent):     10 points

Factor 6: Data Quality (0-10 points)
  Inverse of data quality score from Part 1
  High quality (80-100):   2 points
  Medium (60-79):          5 points
  Low (<60):               10 points

Factor 7: Analyst Dispersion (0-10 points)
  If available: range of analyst price targets / median target
  Low dispersion (<20%):   2 points
  Medium (20-40%):         5 points
  High (>40%):             10 points
  Not available:           5 points (neutral)

Factor 8: Leverage Risk (0-10 points)
  Net Debt / EBITDA ratio
  Net cash or <1x:         2 points
  1-3x:                    5 points
  3-5x:                    8 points
  >5x:                     10 points

TOTAL: Sum of all factors (0-100)
────────────────────────────────────────────────
```

### 5.2 Mapping Uncertainty to Scenarios

```
UNCERTAINTY → SCENARIO CONFIGURATION

Score 0-25 (Low Uncertainty):
  Number of scenarios: 3 (Bear / Base / Bull)
  Spread method: ±1 standard deviation from base
  Typical spread: Revenue growth ±3-5pp, Margins ±2-3pp
  Example companies: JNJ, PG, KO, utilities

Score 26-50 (Moderate Uncertainty):
  Number of scenarios: 3 (Bear / Base / Bull)
  Spread method: ±1.5 standard deviations
  Typical spread: Revenue growth ±5-10pp, Margins ±3-5pp
  Example companies: AAPL, MSFT, JPM, HD

Score 51-75 (High Uncertainty):
  Number of scenarios: 5 (Deep Bear / Bear / Base / Bull / Deep Bull)
  Spread method: ±2 standard deviations for outer, ±1 for inner
  Typical spread: Revenue growth ±10-20pp, Margins ±5-10pp
  Example companies: TSLA, SNOW, growth tech, cyclicals at extremes

Score 76-100 (Very High Uncertainty):
  Number of scenarios: 5 (Deep Bear / Bear / Base / Bull / Deep Bull)
  Spread method: ±2.5 standard deviations for outer
  Typical spread: Revenue growth ±20-40pp, Margins ±10-15pp
  Plus: explicit "failure" scenario at Deep Bear (revenue decline, margin collapse)
  Example companies: Pre-revenue biotech, SPACs, turnarounds, IPOs
```

### 5.3 Historical Volatility Integration

The uncertainty score determines the NUMBER and SHAPE of scenarios.
Historical volatility calibrates the SPECIFIC VALUES:

```
For each projected variable (revenue growth, margins, etc.):

1. Calculate historical standard deviation of that variable
2. Use uncertainty score to determine spread multiplier (1x, 1.5x, 2x, 2.5x)
3. Scenario values:

   Base Case:       Engine's best estimate (from Parts 2-3)
   Bull Case:       Base + (std_dev × multiplier)
   Bear Case:       Base - (std_dev × multiplier)
   Deep Bull:       Base + (std_dev × multiplier × 1.5)  (if 5 scenarios)
   Deep Bear:       Base - (std_dev × multiplier × 1.5)  (if 5 scenarios)

4. Apply constraints:
   - Revenue growth floor: -30% (companies rarely shrink faster)
   - Margin floor: sector P5 (5th percentile)
   - Margin ceiling: sector P95
   - Terminal growth: same across all scenarios (economic, not company-specific)
   - WACC varies by scenario (bear case uses higher ERP, bull uses lower)
```

### 5.4 Scenario WACC Adjustment

Different scenarios imply different risk levels:

```
WACC SCENARIO ADJUSTMENT:

Deep Bear: WACC + 2.0pp (higher risk environment)
Bear:      WACC + 1.0pp
Base:      WACC (as calculated)
Bull:      WACC - 0.5pp (lower risk, stronger company)
Deep Bull: WACC - 1.0pp

Rationale: In a bear scenario, the company is performing worse,
which typically implies higher risk and higher required return.
This compounds the impact — lower cash flows discounted at a higher
rate — which is realistic (bad outcomes in finance are self-reinforcing).
```

### 5.5 Probability Weighting

Each scenario gets a probability weight for the weighted-average intrinsic value:

```
3-Scenario Weighting:
  Bear:  25%
  Base:  50%
  Bull:  25%

5-Scenario Weighting:
  Deep Bear: 10%
  Bear:      20%
  Base:      40%
  Bull:      20%
  Deep Bull: 10%

These are default weights. User can adjust via sliders in the Overview tab.
Probability-weighted intrinsic value = Σ(scenario value × weight)
```

### 5.6 Scenario Reasoning Output

```
SCENARIO CONFIGURATION
Uncertainty Score: 38/100 (Moderate)
Number of Scenarios: 3

REASONING:
"Moderate uncertainty score of 38 based on:
  - Earnings volatility: 8/20 (YoY EPS std dev of 12pp — moderate)
  - Revenue predictability: 5/15 (revenue growth std dev of 4pp — stable)
  - Margin stability: 4/15 (operating margin range of 4pp over 5Y — tight)
  - Company maturity: 2/10 (large cap, 40+ years public)
  - Sector cyclicality: 5/10 (technology — moderate)
  - Data quality: 2/10 (high quality, 10Y of data)
  - Analyst dispersion: 5/10 (not evaluated — using neutral)
  - Leverage risk: 2/10 (net cash position)

Scenario spread calibrated from historical volatility:
  Revenue growth: Base 12.5% | Bear 8.5% (-4pp) | Bull 16.5% (+4pp)
    (std dev of historical growth: 4.2pp, multiplier: 1.0x)
  Operating margin: Base 31.5% | Bear 28.5% (-3pp) | Bull 34.0% (+2.5pp)
    (std dev of historical margin: 2.8pp, multiplier: 1.0x)
  WACC: Base 10.3% | Bear 11.3% (+1pp) | Bull 9.8% (-0.5pp)"
```

---

## Part 6: Model-Specific Assumption Generation

### 6.1 DCF-Specific Assumptions

Beyond revenue and margins, DCF requires:

```
Capital Expenditure:
  Method: CapEx as % of revenue, based on 5Y average
  Adjustment: if company is in heavy investment phase (CapEx/Revenue
    rising), continue trend. If mature (stable ratio), hold flat.
  Depreciation follows CapEx with 1-2 year lag

Working Capital:
  Method: Net Working Capital as % of revenue, based on 3Y average
  Change in NWC each year = (NWC% × Revenue_t) - (NWC% × Revenue_t-1)
  Adjustment: if NWC% is trending (improving efficiency or deteriorating),
    extend trend moderately

Tax Rate:
  Method: 3Y average effective tax rate
  Floor: 10% (some companies have structural low rates — Ireland, etc.)
  Cap: 30% (above statutory is unusual, usually one-time)
  If loss-making: 0% for loss years, then normalized rate when profitable

Debt Schedule:
  Method: Current debt level, with assumption of gradual repayment or
    maintenance based on company's historical pattern
  If debt has been declining: continue trajectory
  If debt has been stable: hold flat
  If debt has been increasing: flag, note in reasoning

Share Count:
  Method: Current diluted shares, adjusted for historical trend
  If buybacks ongoing: slight annual decrease (use 3Y average buyback rate)
  If dilution ongoing: slight annual increase
  Impact: affects per-share intrinsic value
```

### 6.2 DDM-Specific Assumptions

```
Dividend Growth Rate:
  Primary: 3Y dividend CAGR
  Cross-check: earnings growth rate (dividends can't sustainably grow
    faster than earnings unless payout ratio is increasing)
  Constraint: if payout ratio > 70%, cap dividend growth at earnings growth
  If payout ratio < 30%: room for faster dividend growth than earnings

Stage Durations:
  High growth period:
    - Mature dividend aristocrats (25+ years of growth): 5 years
    - Established growers (10-25 years): 5-7 years
    - New/accelerating dividend: 3-5 years
  Transition period: ~half of high growth period (2-3 years)

Required Return:
  Same as cost of equity from WACC calculation
  Displayed separately in DDM for clarity
```

### 6.3 Comps-Specific Assumptions

```
Peer Selection:
  Automatic based on peer selection engine (see Phase 1C)
  Assumptions generated: which multiples to emphasize

Multiple Emphasis:
  Engine weights multiples based on company characteristics:
  - Profitable companies: EV/EBITDA and P/E weighted highest
  - High-growth companies: EV/Revenue and PEG weighted highest
  - Capital-light companies: P/E and P/FCF weighted highest
  - Capital-intensive: EV/EBITDA and EV/EBIT weighted highest
  - Financial companies: P/B and P/E weighted highest (no EV multiples)

Quality Premium/Discount:
  Auto-calculated from quality assessment framework (see Phase 1C)
  Each factor scored independently with reasoning
```

### 6.4 Revenue-Based Specific Assumptions

```
Exit Multiple:
  Method: find current EV/Revenue of companies growing at the projected
    exit-year growth rate of the target company
  Example: if target projected to grow 15% at Year 5, look at companies
    currently growing ~15% and their EV/Revenue multiples
  Use sector-adjusted median of that peer group

Multiple Compression Path:
  Start: current trading multiple
  End: exit multiple (as calculated above)
  Path: linear interpolation by default

Growth Deceleration:
  Follows same framework as Part 2 (Revenue Growth Projection)
  But often more aggressive deceleration for high-growth names
  — the engine uses a steeper decay factor for companies >30% growth
```

---

## Part 7: Missing Data Handling

### 7.1 Data Hierarchy

When primary data is missing, the engine uses fallback sources:

```
FALLBACK CHAIN (per data point):

Level 1: Company's own historical data (financial_data table)
  ↓ if missing
Level 2: Derived from available data
  Example: Operating Margin = Operating Income / Revenue
  Example: FCF = Operating Cash Flow - CapEx
  ↓ if still missing
Level 3: Sector median (from scanner universe)
  Apply sector median for the missing metric
  Flag in reasoning: "Using sector median due to missing company data"
  ↓ if sector data also insufficient
Level 4: All-company median (broadest fallback)
  Flag prominently: "Using broad market median — limited data available"
  ↓ if nothing available
Level 5: Manual input required
  Engine cannot generate this assumption
  Flag: "Insufficient data — manual input required for [metric]"
  Block model calculation until user provides input
```

### 7.2 Minimum Data Requirements

| Model | Minimum Required Data | Nice to Have |
|-------|----------------------|--------------|
| DCF | 3 years revenue, operating income, and CapEx | 5+ years all line items, filing data |
| DDM | 3 years DPS, EPS, and current price | 5+ years, payout history, FCF |
| Comps | Current market multiples, 3+ peers with data | 5+ peers, growth rates, margins |
| Revenue-Based | 3 years revenue, current EV | Segment data, SaaS metrics, margins |

### 7.3 Proxy Logic

When specific metrics are missing but others exist:

| Missing Metric | Proxy Calculation |
|---------------|-------------------|
| Free Cash Flow | Operating Income × (1 - Tax Rate) + D&A - CapEx - ΔNWC |
| CapEx | If D&A available: estimate CapEx ≈ D&A × 1.1 (maintenance CapEx) |
| Interest Expense | Total Debt × sector median cost of debt |
| Tax Rate | Use statutory rate (21% US) if effective rate unavailable |
| Beta | Sector average beta |
| Working Capital | Revenue × sector median NWC-to-Revenue ratio |
| Shares Outstanding | Market Cap / Current Price |
| Dividend | $0 (company doesn't pay dividends) |

Every proxy is flagged in the reasoning with lower confidence.

---

## Part 8: Confidence Scoring

### 8.1 Per-Assumption Confidence

Every assumption gets a confidence score (0-100):

```
CONFIDENCE CALCULATION:

Base: 50

+ Data depth bonus:
  10+ years of relevant data:  +20
  5-10 years:                  +10
  3-5 years:                   +5
  <3 years:                    +0

+ Data quality bonus:
  No missing values, clean data: +15
  Minor gaps, mostly complete:   +10
  Significant gaps:              +5
  Heavy reliance on proxies:     +0

+ Stability bonus:
  Low variance in historical data:  +10
  Moderate variance:                +5
  High variance:                    +0

+ Method confidence:
  Multiple lenses agree:            +10
  Lenses partially agree:           +5
  Lenses disagree significantly:    -5

- Uncertainty penalties:
  Using proxy data:                 -10
  Using sector median fallback:     -15
  Company in regime transition:     -10
  Recent structural change:         -10

FLOOR: 10 (never show 0% confidence — that means no assumption)
CAP: 95 (never show 100% — always room for uncertainty)
```

### 8.2 Overall Model Confidence

Aggregate confidence across all assumptions:

```
Model Confidence = Weighted average of per-assumption confidences

Weights based on impact:
  Revenue growth:     25%
  Operating margin:   20%
  WACC:               20%
  Terminal value:     15%
  Other assumptions:  20%

Displayed in Model Overview as:
  "Model Confidence: 78/100 — Good"

Thresholds:
  85-95:  Excellent (strong data, stable company)
  70-84:  Good (adequate data, reasonable certainty)
  50-69:  Fair (some data gaps or high uncertainty)
  30-49:  Low (significant data gaps, use with caution)
  10-29:  Very Low (minimal data, treat as directional only)
```

---

## Part 9: Reasoning Generation

### 9.1 Reasoning Template Structure

Every assumption's reasoning follows a consistent structure:

```
[ASSUMPTION NAME]: [VALUE]
Confidence: [SCORE]/100

REASONING:
"[One-sentence summary of the assumption and primary justification.]

  1. [Primary data point or analytical lens that drove the decision]
     → [Specific numbers and what they indicate]

  2. [Secondary data point or cross-check]
     → [How it confirms or adjusts the primary]

  3. [Adjustment applied, if any]
     → [Why the raw analytical output was modified]

  4. [Key risk or caveat]
     → [What could make this assumption wrong]

Data quality: [SCORE]/100 ([brief description])
Primary data points: [List of specific data used]"
```

### 9.2 Reasoning Depth Levels

The engine can generate reasoning at different verbosity levels:

```
Summary (default in UI):
  "Revenue growth set at 12.5% based on 3Y CAGR of 13.4% with
   slight haircut for base effect. Decelerating to 3% terminal."

Detailed (expandable in UI):
  Full multi-paragraph reasoning with all lenses, data points,
  and cross-checks (as shown in examples throughout this document)

Audit Trail (exportable):
  Complete record including raw data values, intermediate calculations,
  weight assignments, and decision logic at each step
  → Available in version history and Excel export
```

### 9.3 Key Reasoning Patterns

The engine uses consistent language patterns:

```
For trend-based assumptions:
  "Based on [N]-year [CAGR/average] of [X]%, which was selected because [reason]."

For mean-reversion assumptions:
  "Current [metric] of [X]% is [above/below] the [N]-year average of [Y]%.
   Projecting gradual convergence to [Z]% over [N] years."

For sector-anchored assumptions:
  "Using sector median of [X]% as the long-term anchor because [reason].
   Current [metric] of [Y]% projected to converge over [N] years."

For proxy-based assumptions:
  "Estimated from [proxy metric] due to missing direct data.
   [Proxy metric] of [X] suggests [assumption] of [Y]. Lower confidence
   due to indirect estimation."

For cross-check confirmations:
  "Cross-checked against [alternative method/metric], which yields [X]%,
   confirming the primary estimate of [Y]% is reasonable."

For flagged disagreements:
  "Note: [Lens A] suggests [X]% while [Lens B] suggests [Y]%.
   The divergence of [Z]pp reflects [explanation]. Weighted toward
   [chosen lens] because [reason]."
```

---

## Part 10: Calibration & Validation

### 10.1 Backtesting Framework

The engine can be validated by running it on historical data:

```
BACKTEST METHODOLOGY:

1. Pick a historical date (e.g., end of 2019)
2. Feed the engine only data available as of that date
3. Generate assumptions for 2020-2024
4. Compare projected values to actual outcomes
5. Score accuracy:
   - Revenue growth: within 3pp of actual = excellent
   - Margins: within 2pp of actual = excellent
   - Intrinsic value: within 20% of subsequent price = good

This is NOT run in real-time — it's a periodic validation exercise
to tune the engine's parameters. Results stored and referenced in
the engine's documentation.
```

### 10.2 Sanity Checks (Run Every Time)

Before presenting assumptions to the user, the engine runs:

```
AUTOMATED SANITY CHECKS:

□ Revenue growth Year 1 within 2x of 3Y CAGR (no wild jumps)
□ Terminal growth ≤ risk-free rate
□ Terminal growth ≤ nominal GDP growth
□ Operating margin within sector P5-P95 range
□ WACC between 4% and 20%
□ Cost of equity > cost of debt
□ Implied intrinsic value > $0 (no negative valuations)
□ FCF margins reasonable relative to operating margins
□ CapEx/Revenue ratio within 2x of historical average
□ Payout ratio (DDM) ≤ 100% in all projection years
□ No assumption creates a mathematical singularity
   (e.g., growth rate = discount rate in terminal value)

If any check fails:
  → Adjust the offending assumption to pass the check
  → Flag the adjustment in reasoning
  → Lower confidence score
```

### 10.3 Ongoing Monitoring

```
When a user re-runs a model after new data arrives (quarterly earnings, etc.):

1. Engine generates new assumptions
2. Compare to previous assumptions
3. If material change (>3pp on any key assumption):
   → Flag: "Assumption updated based on new data"
   → Show old vs. new with explanation of what changed
4. If minor change:
   → Update silently, note in version history

This helps users understand whether their valuation thesis has changed
after new data, or if it's just minor calibration.
```

---

## Part 11: Engine Configuration (Settings)

### 11.1 User-Configurable Defaults

These settings are accessible in Settings → Model Defaults:

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| ERP (Equity Risk Premium) | 5.5% | 3.0-10.0% | Applied to all new models |
| Terminal Growth Rate Override | None | 0-5% | If set, overrides engine for all models |
| Projection Period | 10 years | 5-15 years | Number of explicit projection years |
| Monte Carlo Iterations | 10,000 | 1,000-100,000 | Simulation count |
| Scenario Weighting | 25/50/25 | Custom | Bear/Base/Bull probability weights |
| Size Premium | Enabled | On/Off | Auto-apply small-cap premium |
| Reasoning Verbosity | Summary | Summary/Detailed | Default display level |

### 11.2 Per-Model Overrides

Every assumption generated by the engine can be overridden at the model level.
Overrides are preserved across re-runs — the engine will not overwrite a
user-modified assumption unless the user explicitly requests "Reset to Auto."

```
Override behavior:
  - User changes assumption → value turns BLUE to indicate manual override
  - Hovering shows: "Manually set. Engine suggested: [X]%"
  - "Reset to Auto" button next to each overridden assumption
  - "Reset All to Auto" button in Assumptions tab header
  - Overrides saved in model record, persist across sessions
```

---

*End of Phase 1E specification.*
