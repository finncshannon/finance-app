# Phase 1D — Revenue-Based Model (Detailed Specification)
> Designer Agent | February 25, 2026
> Status: COMPLETE — APPROVED BY FINN
> Depends on: Phase 1A (DCF Model), Phase 1C (Comps Model), Phase 0B (Database Schema)

---

## Overview

The Revenue-Based model (model_type: "revbased") values companies primarily on
revenue multiples, used when earnings-based metrics are unreliable or unavailable.
This is the standard approach on Wall Street for pre-profit companies, high-growth
SaaS, early-stage tech, biotech pre-commercialization, and companies in turnaround
situations.

Investment banks like Goldman Sachs and Morgan Stanley routinely use EV/Revenue and
growth-adjusted revenue multiples in their coverage of high-growth names.

**Key decisions:**
- EV/Revenue as primary multiple, with growth-adjusted metrics (Rule of 40, EV/ARR for SaaS)
- Multiple compression/expansion modeling over projection period
- Path-to-profitability overlay: project when the company becomes profitable
- Sub-tabs: Overview | Historical Data | Revenue Analysis | Assumptions | Revenue Model | Sensitivity | History

---

## When Revenue-Based Applies

The auto-detection engine assigns a high score to Revenue-Based when:

- Negative net income (trailing 12 months)
- Negative operating income
- P/E ratio is negative or >100x (meaningless for valuation)
- Revenue growth > 20% (high-growth company where top-line matters more)
- Company is in SaaS, biotech, early-stage tech, or marketplace sectors
- EV/Revenue < 20x (if >20x, the multiple is so stretched that even
  revenue-based becomes unreliable — flag as speculative)

Revenue-Based can coexist with DCF when a company has negative earnings
but positive free cash flow. In that case, both models apply and the
Overview panel shows both.

---

## Model Structure

### Core Methodology

```
Step 1: Project Revenue Forward (5-10 years)
  - Start from current TTM revenue
  - Apply revenue growth rate per year (can decelerate over time)
  - Growth curve: user selects linear deceleration, S-curve, or custom

Step 2: Apply Target Multiple
  - Select appropriate EV/Revenue multiple
  - Multiple can compress or expand over the projection period
  - Multiple sources: current trading multiple, peer median, historical range

Step 3: Calculate Implied Enterprise Value at Each Year
  - EV(t) = Revenue(t) × Multiple(t)

Step 4: Discount Back to Present
  - Apply required return (WACC or cost of equity) to discount future EV
  - Implied Value = Discounted EV - Net Debt + Cash / Shares Outstanding

Alternative (Exit Multiple Approach):
  - Project revenue to a specific exit year (default: Year 5)
  - Apply exit multiple at that year
  - Discount the exit EV back to present
  - This is the more common Wall Street approach
```

### Growth-Adjusted Metrics

| Metric | Formula | Usage |
|--------|---------|-------|
| EV/Revenue | Enterprise Value / Revenue | Primary multiple for all companies |
| EV/ARR | Enterprise Value / Annual Recurring Revenue | SaaS companies with subscription revenue |
| Rule of 40 | Revenue Growth % + Profit Margin % | Quality-adjusted: companies scoring >40 deserve premium multiples |
| Magic Number | Net New ARR / Prior Quarter Sales & Marketing Spend | SaaS efficiency metric — measures sales efficiency |
| EV/GP | Enterprise Value / Gross Profit | Better than EV/Revenue when gross margins vary widely across peers |

### Multiple Compression/Expansion

High-growth companies typically see multiple compression as they mature.
The model projects how the multiple changes over time:

```
MULTIPLE TRAJECTORY
────────────────────────────────────────────────
Year          1      2      3      4      5
Rev Growth    40%    32%    25%    20%    15%
EV/Revenue    12.0x  10.5x  8.8x   7.2x   6.0x
────────────────────────────────────────────────

Compression logic:
  - Current multiple: from market data (or peer-implied)
  - Exit multiple: assumption engine suggests based on growth at exit year
  - Interpolation: linear compression from current to exit multiple
  - User can override any year's multiple
```

The assumption engine estimates the exit multiple by looking at where
companies with similar growth rates (at the exit year's projected growth)
currently trade. A company growing at 15% at Year 5 should trade at the
multiple that 15%-growers trade at today.

---

## Revenue Analysis Tab (Model-Specific)

### Revenue Decomposition

```
REVENUE ANALYSIS — SNOW (Snowflake)
────────────────────────────────────────────────────────────────────────
                    2021      2022      2023      2024      Growth
Product Revenue     $1,140    $1,939    $2,673    $3,228    +20.8%
Professional Svcs   $119      $157      $195      $222      +13.8%
────────────────────────────────────────────────────────────────────────
Total Revenue       $1,259    $2,096    $2,868    $3,450    +20.3%

YoY Growth          106%      67%       37%       20%
QoQ Growth (last)                                 5.2%
────────────────────────────────────────────────────────────────────────
Net Revenue Retention Rate: 127%
Remaining Performance Obligations: $5.2B
```

Where data is available from filings, break revenue into segments.
If not available, show total revenue with growth trends.

### Rule of 40 Tracker

```
RULE OF 40 — SNOW
────────────────────────────────────────────────────────────────────────
Year          2021    2022    2023    2024
Rev Growth    106%    67%     37%     20%
FCF Margin    -8%     5%      12%     18%
Rule of 40    98      72      49      38      ● Below threshold
────────────────────────────────────────────────────────────────────────
```

- Score ≥ 40: ● Green (healthy growth/profitability balance)
- Score 20-39: ● Yellow (watch)
- Score < 20: ● Red (concerning)

### Path to Profitability

For pre-profit companies, show when the company is expected to reach
breakeven and sustained profitability:

```
PATH TO PROFITABILITY
────────────────────────────────────────────────────────────────────────
                Current   2025    2026    2027    2028    2029
Revenue         $3.4B     $4.1B   $4.9B   $5.6B   $6.3B   $7.0B
Gross Margin    68%       70%     71%     72%     73%     73%
Operating Margin -5%      -1%     3%      6%      9%      11%
Net Margin      -8%       -4%     0%      3%      5%      7%
                                   ▲ Breakeven
────────────────────────────────────────────────────────────────────────
```

The breakeven year gets a visual marker (▲) and the row transitions
from --color-negative to --color-positive at that point.

---

## Revenue Model Projection Table

```
REVENUE-BASED VALUATION — SNOW (Exit Multiple Approach)
Required Return: 11.5%
────────────────────────────────────────────────────────────────────────
                  2025      2026      2027      2028      2029 (Exit)
────────────────────────────────────────────────────────────────────────
Revenue           $4.08B    $4.90B    $5.63B    $6.33B    $7.02B
Growth Rate       18.0%     20.0%     15.0%     12.5%     11.0%
EV/Revenue        10.5x     9.2x      8.0x      7.0x      6.0x
Implied EV        $42.8B    $45.1B    $45.0B    $44.3B    $42.1B
────────────────────────────────────────────────────────────────────────
Exit Year EV:                                             $42.1B
Discounted EV:                                            $24.5B
Less: Net Debt                                            -$1.2B
Plus: Cash                                                 $3.8B
────────────────────────────────────────────────────────────────────────
Implied Equity Value:                                     $27.1B
Shares Outstanding:                                       334M
────────────────────────────────────────────────────────────────────────
INTRINSIC VALUE (per share):                              $81.14
Current Price:                                            $162.38
Upside/Downside:                                          -50.0%
```

---

## Waterfall Visualization

```
[Exit Year Revenue] × [Exit Multiple] = [Exit EV]
  → [Discount to Present] = [PV of Exit EV]
  → [- Net Debt + Cash] = [Equity Value]
  → [÷ Shares] = [Intrinsic Value per Share]

Bars:
  Exit Year Revenue       $7.02B    (blue, context)
  × Exit Multiple (6.0x)  →        (connector)
  Exit Enterprise Value   $42.1B    (blue)
  Discount Factor         -$17.6B   (red, subtractive)
  PV of Exit EV           $24.5B    (blue)
  Net Cash                +$2.6B    (blue, additive)
  ────────────────────────────────
  Equity Value            $27.1B    (total)
  Per Share               $81.14    (final callout)
```

---

## Sensitivity Analysis

**Primary sensitivity variables:**
1. Exit Year EV/Revenue multiple
2. Revenue growth rate (Year 1)
3. Growth deceleration rate
4. Required return (discount rate)
5. Exit year selection (Year 3 vs Year 5 vs Year 7)

**Sensitivity tables:** Default axes = Exit Multiple × Revenue Growth Rate.

**Tornado chart:** Shows which variable drives the most valuation swing.

**Monte Carlo:** Simulates distributions around growth rates and exit multiples.
10,000 iterations, same histogram output as DCF/DDM.

**Sliders:** Real-time adjustment of growth rates and multiples.

---

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| Company has positive earnings | Revenue-Based still available but auto-detection scores lower. Show note: "Consider DCF or Comps for profitable companies." |
| Revenue declining | Warning: "Declining revenue — revenue multiple approach may overstate value." Negative growth rates supported in projections. |
| No comparable peers for multiple | Default to sector median EV/Revenue. Note in assumptions reasoning. |
| Extremely high multiple (>20x revenue) | Warning: "Current multiple implies very high growth expectations. Consider whether growth assumptions justify this valuation." |
| Pivoting business model | Revenue segments may shift dramatically. Flag: "Business model transition detected — historical growth rates may not be predictive." |
| SaaS metrics unavailable | If ARR/NRR/RPO data not in filings, skip SaaS-specific metrics. Use total revenue only. No error — just fewer data points in Revenue Analysis tab. |

---

## Sub-Tab Structure

```
Revenue-Based Model Builder Sub-Tabs:
  Overview | Historical Data | Revenue Analysis | Assumptions | Revenue Model | Sensitivity | History
```

- **Overview:** Intrinsic value, waterfall, scenario comparison
- **Historical Data:** Bloomberg-style financials with revenue metrics highlighted
- **Revenue Analysis:** Revenue decomposition, Rule of 40, path to profitability
- **Assumptions:** Growth rates, multiples, exit year, all with reasoning
- **Revenue Model:** Projection table + waterfall
- **Sensitivity:** Sliders | Tornado | Monte Carlo | Tables
- **History:** Version history + diff view

---

## Relationship to Other Models

Revenue-Based and DCF can both apply to the same company (e.g., a company
with negative earnings but positive FCF). When both apply:

- Both appear in the Model Builder with separate tabs
- Overview panel shows both intrinsic values side by side
- The Model Comparison view (Phase 1F) synthesizes them

Revenue-Based and Comps are related but distinct:
- **Comps** compares the target against specific peers using MULTIPLE multiples
- **Revenue-Based** projects the target's own revenue forward and applies a
  single multiple trajectory with compression modeling
- A company can have both — Comps as a cross-check on the Revenue-Based output

---

*End of Phase 1D specification.*
