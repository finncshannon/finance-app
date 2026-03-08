# Phase 1B — DDM Model (Detailed Specification)
> Designer Agent | February 25, 2026
> Status: COMPLETE — APPROVED BY FINN
> Depends on: Phase 1A (DCF Model), Phase 0B (Database Schema), Phase 0D (UI/UX Framework)

---

## Overview

The Dividend Discount Model (DDM) estimates intrinsic value based on the present
value of expected future dividend payments. This is the second core valuation
model in the Model Builder, following the same architectural patterns as the DCF
but with dividend-specific inputs, projections, and analysis.

**Key decisions:**
- 3-stage DDM as default (high growth → transition → terminal) — institutional standard
- 2-stage available as simplified option
- Required return derived from CAPM (same components as WACC cost of equity)
- Dividend sustainability analysis integrated (payout ratio, FCF coverage, earnings coverage)
- Sub-tabs: Overview | Historical Data | Dividend Analysis | Assumptions | DDM Model | Sensitivity | History

---

## Model Structure

### Three-Stage DDM (Default)

```
Stage 1: High Growth Phase (Years 1-N, user-configurable, default 5)
  - Dividend grows at the "high growth rate"
  - Rate derived from recent dividend growth trend + earnings growth

Stage 2: Transition Phase (Years N+1 to M, user-configurable, default 3)
  - Growth rate linearly declines from high growth rate to terminal rate
  - Each year's growth = previous year - (step-down per year)

Stage 3: Terminal Phase (Year M+1 → perpetuity)
  - Dividend grows at terminal growth rate (GDP-anchored, default 2-3%)
  - Terminal value = D(M+1) / (required return - terminal growth)
```

### Two-Stage DDM (Simplified Option)

```
Stage 1: Growth Phase (Years 1-N)
  - Dividend grows at the high growth rate

Stage 2: Terminal Phase (Year N+1 → perpetuity)
  - Growth drops immediately to terminal rate
  - No transition period
```

User selects model type via toggle at top of Assumptions tab: `3-Stage (Default) | 2-Stage`

### Intrinsic Value Calculation

```
Intrinsic Value = Σ [D(t) / (1 + r)^t] for t = 1 to M
               + Terminal Value / (1 + r)^M

Where:
  D(t)  = Expected dividend per share in year t
  r     = Required return on equity
  M     = Last year of explicit projection (end of transition phase)
  Terminal Value = D(M+1) / (r - g_terminal)
```

---

## DDM-Specific Inputs

### Required Return (Cost of Equity)

Same CAPM-based calculation used in DCF's WACC for cost of equity:

```
Required Return = Risk-Free Rate + Beta × Equity Risk Premium

Components:
  Risk-Free Rate:   Auto-fetched from 10-year Treasury yield (overridable)
  Beta:             From Yahoo Finance (overridable)
  ERP:              User-set default (overridable per model)
```

This is intentionally the same as the cost of equity in WACC. If a user has
both a DCF and DDM for the same company, the required return in DDM should
match the cost of equity in DCF's WACC by default (user can override).

### Dividend Inputs

| Input | Source | Overridable |
|-------|--------|-------------|
| Current Annual DPS | Yahoo Finance (trailing 12M) | Yes |
| Dividend Growth Rate (Stage 1) | Assumption engine (from historical trend) | Yes |
| Transition Period Length | Assumption engine (default 3 years) | Yes |
| Terminal Growth Rate | Assumption engine (GDP-anchored, 2-3%) | Yes |
| High Growth Period Length | Assumption engine (default 5 years) | Yes |
| Payout Ratio (current) | Calculated: DPS / EPS | Display only |
| Payout Ratio (projected) | Assumption engine | Yes |

### Assumption Engine Behavior for DDM

The assumption engine generates DDM assumptions using:

1. **Dividend growth rate:** Weighted average of 3-year and 5-year dividend CAGR,
   with more weight on recent years. Adjusted downward if payout ratio is
   already high (>80%) since growth is constrained. Adjusted upward if
   earnings growth exceeds dividend growth (room for payout expansion).

2. **Stage durations:** High growth period defaults to 5 years for most companies.
   Shortened to 3 if the company is mature/low-growth. Extended to 7 if
   dividend growth has been accelerating. Transition period is always
   approximately half the high growth period (2-3 years).

3. **Terminal growth rate:** Anchored to long-term GDP growth (2-3%). Never
   exceeds risk-free rate. For utilities/REITs, may be set slightly higher
   (inflation-linked).

4. **Reasoning display:** Same pattern as DCF — every assumption shows a
   clickable reasoning string explaining the logic.

---

## Dividend Analysis Tab (DDM-Specific)

This tab does not exist in DCF. It provides deep insight into the company's
dividend characteristics before the user reviews assumptions.

### Dividend History Panel

```
DIVIDEND HISTORY — AAPL
──────────────────────────────────────────────
Year    Annual DPS   Growth    Payout Ratio
2019    $3.04        10.1%     24.8%
2020    $3.24         6.6%     27.1%
2021    $3.52         8.6%     25.5%
2022    $3.72         5.7%     25.1%
2023    $3.93         5.6%     25.9%
2024    $4.12         4.8%     24.2%
──────────────────────────────────────────────
3Y CAGR: 5.4%    5Y CAGR: 6.3%    10Y CAGR: 8.1%
```

- Bloomberg-style table: years down rows, metrics across columns
- Growth rates colored green/red per Phase 0D rules
- CAGR summary below the table

### Dividend Sustainability Panel

```
DIVIDEND SUSTAINABILITY METRICS
──────────────────────────────────────────────
                        Current    5Y Avg
Payout Ratio (EPS)      24.2%     25.3%      ● Healthy
Payout Ratio (FCF)      18.1%     19.8%      ● Healthy
Dividend Coverage (EPS)  4.1x      4.0x      ● Strong
Dividend Coverage (FCF)  5.5x      5.1x      ● Strong
──────────────────────────────────────────────
Consecutive Years of Growth: 12
Consecutive Years of Payment: 18
Dividend Yield: 0.52%
```

**Health indicators:**
- ● Green: Payout < 60%, Coverage > 1.5x
- ● Yellow: Payout 60-80%, Coverage 1.0-1.5x
- ● Red: Payout > 80%, Coverage < 1.0x

Color coding uses --color-positive, --color-warning, --color-negative.
The dot is the only colored element — labels stay --text-primary.

### Dividend vs. Earnings Growth Chart

Line chart showing DPS growth vs. EPS growth over time (10 years).
Helps visualize whether dividends are growing faster or slower than earnings.

- DPS line: --accent-primary (blue)
- EPS line: --text-secondary (gray)
- Divergence between lines tells the payout ratio story visually

---

## DDM Projection Table

Displayed in the DDM Model sub-tab. Bloomberg-style, years across top.

```
DDM PROJECTION — AAPL (3-Stage)
Required Return: 9.2%
────────────────────────────────────────────────────────────────────────
                  2025    2026    2027    2028    2029    2030    2031    2032    2033    Terminal
                  ──────  ──────  ──────  ──────  ──────  ──────  ──────  ──────  ──────  ────────
Stage             HIGH    HIGH    HIGH    HIGH    HIGH    TRANS   TRANS   TRANS   TERM    
Growth Rate       5.4%    5.4%    5.4%    5.4%    5.4%    4.3%    3.1%    2.0%    2.0%
DPS               $4.34   $4.58   $4.82   $5.08   $5.36   $5.59   $5.76   $5.88   $5.99
PV of Dividend    $3.98   $3.84   $3.71   $3.58   $3.46   $3.30   $3.12   $2.91
────────────────────────────────────────────────────────────────────────
PV of Stage 1 Dividends:                    $18.57
PV of Stage 2 Dividends:                     $9.33
PV of Terminal Value:                       $55.21
────────────────────────────────────────────────────────────────────────
INTRINSIC VALUE:                            $83.11
Current Price:                             $182.52
Upside/Downside:                           -54.5%
```

Stage labels shown as a row with colored backgrounds:
- HIGH: --accent-subtle (blue tint)
- TRANS: --bg-hover (neutral)
- TERM: --bg-active (slightly brighter neutral)

---

## DDM Waterfall Visualization

Same waterfall component as DCF, adapted for DDM:

```
[Stage 1 PV] + [Stage 2 PV] + [Terminal PV] = [Intrinsic Value] vs [Market Price]

Bars:
  Stage 1 Dividends PV    $18.57   (blue, additive)
  Stage 2 Dividends PV     $9.33   (blue, additive)
  Terminal Value PV        $55.21   (blue, additive)
  ──────────────────────────────
  Intrinsic Value          $83.11   (total bar)
  Market Price            $182.52   (reference line, dashed)
```

---

## DDM Sensitivity Analysis

Uses the same sensitivity sub-module as DCF (Sliders | Tornado | Monte Carlo | Tables)
but with DDM-relevant variables:

**Primary sensitivity variables:**
1. Required Return (cost of equity)
2. Terminal Growth Rate
3. Stage 1 Dividend Growth Rate
4. High Growth Period Duration (years)
5. Current DPS (starting point)

**Tornado chart:** Shows which variable has the most impact on intrinsic value.
Typically required return and terminal growth dominate, similar to DCF.

**Monte Carlo:** Simulates distributions around growth rates and required return.
Same 10,000-iteration default, same histogram + distribution curve output.

**Sensitivity tables:** 2D grid, default axes = Required Return × Terminal Growth Rate.

---

## Edge Cases

| Scenario | Behavior |
|----------|----------|
| Company doesn't pay dividends | DDM auto-detection score = 0. If user forces DDM, show warning: "This company does not currently pay dividends. DDM requires dividend history to generate meaningful results." Allow manual DPS input. |
| Dividend was recently cut | Warning flag in Dividend Analysis. Assumption engine uses post-cut DPS as baseline, notes the cut in reasoning. |
| Irregular/special dividends | Excluded from growth rate calculation. Noted in Dividend History table with asterisk. Only regular dividends used for trend analysis. |
| New dividend initiator (<3 years of history) | Limited historical data warning. Growth rate defaults to sector median dividend growth. Wider scenario spread due to uncertainty. |
| Payout ratio > 100% | Red health indicator. Warning in assumptions: "Current payout ratio exceeds earnings. Dividend may not be sustainable at current levels." |
| Required return < terminal growth | Mathematical error (negative terminal value). Block calculation, show error: "Required return must exceed terminal growth rate." |

---

## Sub-Tab Structure

```
DDM Model Builder Sub-Tabs:
  Overview | Historical Data | Dividend Analysis | Assumptions | DDM Model | Sensitivity | History
```

- **Overview:** Same as DCF — intrinsic value, waterfall, scenario comparison
- **Historical Data:** Same Bloomberg-style financial table, but with dividend-specific
  rows highlighted (DPS, payout ratio, dividend yield prominently displayed)
- **Dividend Analysis:** DDM-specific tab (described above)
- **Assumptions:** Same layout as DCF — all inputs with reasoning, overridable
- **DDM Model:** Projection table + waterfall
- **Sensitivity:** Sliders | Tornado | Monte Carlo | Tables (DDM variables)
- **History:** Same version history + diff view as DCF

---

*End of Phase 1B specification.*
