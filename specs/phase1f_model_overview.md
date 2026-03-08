# Phase 1F — Model Comparison & Overview Panel
> Designer Agent | February 26, 2026
> Status: COMPLETE — APPROVED BY FINN
> Depends on: Phase 1A-1E (all model specs + assumption engine)

---

## Overview

When multiple valuation models apply to the same company, the Overview tab
synthesizes their outputs into a unified view. This is the first thing a user
sees after running models — the "so what's the answer?" screen.

**Key decisions:**
- Football field chart as PRIMARY visualization — side-by-side model ranges
- Blended weighted average as SECONDARY — available but not the hero element
- User-adjustable model weights with engine-suggested defaults
- Cross-model scenario comparison (Bear/Base/Bull across all models)

---

## Overview Tab Layout

When a company has multiple models, the Overview tab renders top to bottom:

```
┌─────────────────────────────────────────────────────────────────────┐
│  VALUATION OVERVIEW — AAPL                                         │
│  Apple Inc. · Technology · Consumer Electronics · NASDAQ            │
│  Current Price: $182.52                                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              FOOTBALL FIELD CHART (PRIMARY)                  │   │
│  │                                                              │   │
│  │                              Current: $182.52                │   │
│  │                                   │                          │   │
│  │  DCF          ████████████████████│██████████                │   │
│  │               $148      $172      │    $198                  │   │
│  │                                   │                          │   │
│  │  DDM          ██████████████      │                          │   │
│  │               $68       $83       │  $104                    │   │
│  │                                   │                          │   │
│  │  Comps              ██████████████│████████████████          │   │
│  │                     $165     $176 │       $216               │   │
│  │                                   │                          │   │
│  │  Rev-Based    ████████████████    │                          │   │
│  │               $72       $95       │                          │   │
│  │                                   │                          │   │
│  │  Composite          ██████████████│██████                    │   │
│  │                     $132     $159 │  $185                    │   │
│  │               ────────────────────────────────               │   │
│  │               $50  $100  $150  $200  $250  $300              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────┐  ┌──────────────────────────────┐   │
│  │  BLENDED INTRINSIC VALUE │  │  MODEL WEIGHTS               │   │
│  │                          │  │                               │   │
│  │       $158.72            │  │  DCF          ████████  40%  │   │
│  │   Upside: -13.0%        │  │  DDM          ███       15%  │   │
│  │                          │  │  Comps        ██████    30%  │   │
│  │  Probability-Weighted:   │  │  Rev-Based    ███       15%  │   │
│  │  Bear:    $131.58  (25%) │  │                               │   │
│  │  Base:    $158.72  (50%) │  │  [Reset to Suggested]        │   │
│  │  Bull:    $185.41  (25%) │  │                               │   │
│  └──────────────────────────┘  └──────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  SCENARIO COMPARISON TABLE                                   │   │
│  │                                                              │   │
│  │  Model       Bear     Base     Bull     Confidence           │   │
│  │  DCF         $148     $172     $198     82/100               │   │
│  │  DDM         $68      $83      $104     71/100               │   │
│  │  Comps       $165     $176     $216     75/100               │   │
│  │  Rev-Based   $72      $95      $118     58/100               │   │
│  │  ──────────────────────────────────────────────              │   │
│  │  Composite   $132     $159     $185                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  MODEL AGREEMENT ANALYSIS                                    │   │
│  │                                                              │   │
│  │  Agreement Level: MODERATE                                   │   │
│  │                                                              │   │
│  │  "DCF and Comps are broadly aligned ($172 vs $176 base),    │   │
│  │   suggesting the market is pricing AAPL near fair value on   │   │
│  │   an earnings basis. DDM and Revenue-Based produce lower     │   │
│  │   values ($83 and $95), which is expected — AAPL's low       │   │
│  │   dividend yield makes DDM less relevant, and AAPL is a      │   │
│  │   profitable company where revenue multiples understate       │   │
│  │   value. The DCF and Comps results should carry the most     │   │
│  │   weight for this company."                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Football Field Chart (Primary Visualization)

### Design Specification

```
Layout:
  - Horizontal bars, one per model + one Composite
  - Y-axis: model names (left-aligned labels)
  - X-axis: share price (bottom)
  - Current price: dashed vertical line (--text-primary, 1px dashed)

Each bar represents:
  - Left edge: Bear case intrinsic value
  - Bar center marker (tick): Base case intrinsic value
  - Right edge: Bull case intrinsic value
  - If 5 scenarios: thin extension lines for Deep Bear / Deep Bull

Bar styling:
  - Model bars: --accent-primary at 50% opacity, 24px height
  - Base case marker: solid --accent-primary vertical tick, 2px wide
  - Composite bar: --accent-primary at 80% opacity, 28px height (slightly larger)
  - Gap between bars: 16px

Current price line:
  - Dashed vertical line spanning full chart height
  - Label at top: "Current: $182.52" in --text-secondary
  - Line color: --text-primary at 60% opacity

Value labels:
  - Bear value: left of bar, 11px JetBrains Mono, --text-secondary
  - Base value: centered below bar, 12px JetBrains Mono, --text-primary
  - Bull value: right of bar, 11px JetBrains Mono, --text-secondary

Hover behavior:
  - Hover on any bar → tooltip shows all three scenario values for that model
  - Hover on Composite bar → shows blended value and weights
```

### Composite Bar Calculation

```
Composite Bear  = Σ (model_bear_value × model_weight)
Composite Base  = Σ (model_base_value × model_weight)
Composite Bull  = Σ (model_bull_value × model_weight)
```

---

## Model Weights

### Engine-Suggested Defaults

The engine suggests weights based on model confidence scores and
applicability to the specific company:

```
WEIGHT SUGGESTION ALGORITHM:

Step 1: Start with raw confidence scores
  DCF:       82
  DDM:       71
  Comps:     75
  Rev-Based: 58

Step 2: Apply applicability multiplier
  Each model gets a 0-1 multiplier based on how relevant it is:

  DCF:
    Positive FCF → 1.0
    Negative FCF, positive operating income → 0.7
    Negative operating income → 0.3

  DDM:
    Pays dividends, 5+ year history → 1.0
    Pays dividends, <5 year history → 0.6
    No dividends → 0.0 (excluded entirely)

  Comps:
    5+ quality peers found → 1.0
    3-4 peers → 0.7
    <3 peers → 0.3

  Revenue-Based:
    Pre-profit or >20% growth → 1.0
    Profitable, 10-20% growth → 0.5
    Mature, <10% growth → 0.2

Step 3: Compute weighted scores
  Adjusted score = confidence × applicability multiplier
  DCF:       82 × 1.0 = 82
  DDM:       71 × 1.0 = 71
  Comps:     75 × 1.0 = 75
  Rev-Based: 58 × 0.2 = 11.6

Step 4: Normalize to 100%
  Total = 82 + 71 + 75 + 11.6 = 239.6
  DCF:       82 / 239.6 = 34% → rounded to 35%
  DDM:       71 / 239.6 = 30% → rounded to 30%
  Comps:     75 / 239.6 = 31% → rounded to 25%
  Rev-Based: 11.6 / 239.6 = 5% → rounded to 10%

  (Rounding ensures weights sum to 100% and no model <5% unless excluded)
```

### User-Adjustable Weights

```
UI: Horizontal slider bars for each model, 0-100%
  - Sliders are linked — adjusting one redistributes the others proportionally
  - Double-click a slider to type an exact percentage
  - [Reset to Suggested] button restores engine defaults
  - Weights must sum to 100%
  - Setting a model to 0% effectively excludes it from the composite

Display:
  - Filled bar visualization next to percentage (visual weight)
  - Blended value updates in real-time as weights change
  - Football field Composite bar updates in real-time
```

---

## Model Agreement Analysis

The engine generates a brief analytical paragraph explaining how the
models relate to each other and what the disagreements mean.

### Agreement Level Classification

```
Calculate pairwise disagreement between all active models (base case values):
  Max Spread = (highest base - lowest base) / average base

  Max Spread < 15%:   STRONG agreement
  Max Spread 15-30%:  MODERATE agreement
  Max Spread 30-50%:  WEAK agreement
  Max Spread > 50%:   SIGNIFICANT DISAGREEMENT

Display:
  Strong:       ● Green dot + "STRONG"
  Moderate:     ● Yellow dot + "MODERATE"
  Weak:         ● Yellow dot + "WEAK"
  Disagreement: ● Red dot + "SIGNIFICANT DISAGREEMENT"
```

### Agreement Reasoning

Engine generates explanation using patterns:

```
When models agree (spread < 15%):
  "All [N] models converge around $[X]-$[Y], suggesting strong analytical
   consensus on fair value. The tight range increases confidence in the
   composite estimate."

When earnings models agree but others diverge:
  "DCF and Comps align at $[X]-$[Y], while [divergent model] suggests $[Z].
   This is [expected/unexpected] because [reason based on company characteristics].
   [Guidance on which to trust more]."

When models widely disagree:
  "Significant spread between models ($[low] to $[high]) reflects genuine
   uncertainty about [company]'s fair value. [Identify which model type is
   the outlier and explain why]. Consider which valuation framework best
   matches your investment thesis."
```

---

## Cross-Model Scenario Table

### Table Design

```
Standard Bloomberg-style table:

Headers:  Model | Bear | Base | Bull | Confidence | Weight
Data:     One row per model + Composite summary row
Format:   Dollar values in JetBrains Mono, right-aligned
          Confidence as "XX/100", colored by threshold
          Weight as "XX%"

Row interactions:
  - Click model name → navigates to that model's tab
  - Hover row → highlights corresponding bar in football field
```

---

## Single-Model Overview

When only one model has been run for a company, the Overview tab simplifies:

```
- No football field (only one bar would be meaningless)
- Show that model's waterfall chart instead
- Show scenario comparison (Bear/Base/Bull) for the single model
- Note: "Run additional models for cross-model comparison"
- Quick-action buttons: [Run DCF] [Run DDM] [Run Comps] [Run Revenue-Based]
  (only show buttons for models not yet run, grayed out if not applicable)
```

---

## Overview When No Models Exist

```
Before any models are run for a company:

  ┌─────────────────────────────────────────────────────┐
  │                                                     │
  │  AUTO-DETECTION RESULTS — AAPL                      │
  │                                                     │
  │  Recommended Models:                                │
  │  ● DCF              Score: 92    [Build Model →]    │
  │  ● Comps             Score: 85    [Build Model →]    │
  │  ● DDM               Score: 71    [Build Model →]    │
  │  ○ Revenue-Based     Score: 18    Not recommended    │
  │                                                     │
  │  "AAPL is a profitable, dividend-paying company     │
  │   with strong peer comparables. DCF is the primary  │
  │   recommended approach, supported by Comps for      │
  │   relative valuation context."                      │
  │                                                     │
  └─────────────────────────────────────────────────────┘
```

---

*End of Phase 1F specification.*
