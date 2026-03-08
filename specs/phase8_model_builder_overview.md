# Finance App — Model Builder: Overview Sub-Tab Update Plan
## Phase 8: Model Builder — Overview

**Prepared by:** Planner (March 4, 2026)
**Recipient:** PM Agent
**Scope:** Model Builder → Overview sub-tab (OverviewTab.tsx and all child components)

---

## PLAN SUMMARY

Three workstreams:

1. **Layout Reorder** — Move Scenario Comparison to the top, Football Field to the bottom
2. **Football Field Overhaul** — Bigger, more information-dense chart with bear/bull price labels, wider gradient contrast, hover tooltips, and a composite detail section below
3. **Underscore Syntax Cleanup** — Audit and fix all display paths where raw backend keys (e.g., `revenue_based`, `SIGNIFICANT_DISAGREEMENT`) leak through to the UI without label mapping

**Standing directive for all future tabs:** Graphs and charts specifically must be upgraded from minimal/decorative to information-dense (Fidelity/Yahoo Finance level of detail) while maintaining the existing dark UI design system aesthetic.

---

## AREA 1: LAYOUT REORDER

### Current Order
1. Composite summary bar
2. Warnings
3. Models included tags
4. Football Field (full width) — card
5. Weights (40%) + Agreement (60%) — card row
6. Scenario Comparison Table (full width) — card

### New Order
1. Composite summary bar
2. Warnings
3. Models included tags
4. **Scenario Comparison Table (full width)** — moved to top
5. Weights (40%) + Agreement (60%) — stays in middle
6. **Football Field (full width)** — moved to bottom, larger

**Rationale:** Numbers-first workflow. The scenario table is the primary "at a glance" data. The football field is the visual reinforcement of the same data — it makes more sense below, where the user has already absorbed the numbers and can now see them spatially.

**Files touched:**
- `frontend/src/pages/ModelBuilder/Overview/OverviewTab.tsx` — reorder JSX grid sections

---

## AREA 2: FOOTBALL FIELD OVERHAUL

### Current Problems
- Bars are thin (16px) with a narrow gradient that barely differentiates bear from bull
- Only the base price shows on the right — bear and bull values are invisible without cross-referencing the scenario table
- No hover tooltips despite CSS class existing
- No detail section below composite
- Scale ticks at top are small and easy to miss
- Overall feels decorative rather than informational

### What Changes

#### 2A. Increased Size & Proportions
- Remove any max-height constraint on the football field container
- Increase bar height from 16px to 28–32px for model rows, 36–40px for composite
- Increase label column width from 140px to 160px to accommodate more info
- Add more vertical padding between rows (currently tight)
- Scale row height increased from 20px
- Overall the football field should feel substantial — it's the visual anchor of the Overview tab

**Files touched:**
- `frontend/src/pages/ModelBuilder/Overview/FootballField.module.css` — bar heights, spacing, track sizing

#### 2B. Bear/Bull Price Labels on Bars
**Goal:** Each bar shows three price annotations — bear at the left end, base at the marker, bull at the right end — directly on or adjacent to the bar. No need to cross-reference another table.

**Implementation:**
- Bear price label: positioned at the left edge of the bar, below or above the bar depending on space. Small mono font, lighter color.
- Bull price label: positioned at the right edge of the bar, same treatment.
- Base price label: positioned at the base marker (white vertical line), slightly bolder than bear/bull.
- For the right-side `priceText` column: keep it but change it to show the upside/downside percentage instead of redundant base price.

**Layout per row:**
```
 DCF          [$142]───────────────[|$178|]───────────────[$215]     +12.3%
 35% wt       bear                  base                  bull      upside
```

- Price labels use `position: absolute` within the track, anchored to their respective percentage positions
- Labels that would overlap (tight range) should collapse to tooltip-only
- Collision detection: if bear and base labels are within 40px of each other, hide the bear label and show on hover only. Same for bull/base.

**Files touched:**
- `frontend/src/pages/ModelBuilder/Overview/FootballField.tsx` — add price label elements per row, collision logic
- `frontend/src/pages/ModelBuilder/Overview/FootballField.module.css` — price label positioning, font styles

#### 2C. Wider Gradient Contrast
**Current:** `linear-gradient(90deg, #1E3A5F, #2563EB)` — dark navy to medium blue. Too subtle.
**New:** `linear-gradient(90deg, #60A5FA, #1D4ED8)` — light blue (bear/conservative) to deep blue (bull/aggressive). The bear end should feel cooler/lighter, the bull end should feel deeper/more saturated. This matches the legend dot colors already in place (`#60A5FA` for bear, `var(--accent-primary)` for bull).

For composite bar: `linear-gradient(90deg, #93C5FD, #2563EB)` — even wider range, slightly brighter.

**Files touched:**
- `frontend/src/pages/ModelBuilder/Overview/FootballField.module.css` — gradient values for `.bar` and `.barComposite`

#### 2D. Hover Tooltips
**Goal:** Hovering any bar shows a rich tooltip with full model detail.

**Tooltip content per model row:**
```
DCF Model
─────────────
Bear:   $142.30  (-10.2%)
Base:   $178.45  (+12.3%)
Bull:   $215.80  (+36.0%)
Weight: 35%
Confidence: 72
```

**Tooltip content for composite:**
```
Composite (Weighted Blend)
─────────────
Bear:   $155.20  (-2.1%)
Base:   $182.10  (+14.8%)
Bull:   $210.50  (+32.7%)
Models: DCF (35%), DDM (25%), Comps (25%), Rev (15%)
```

**Implementation:**
- Use a controlled hover state per row (React `useState` or CSS `:hover` + sibling selector)
- Tooltip positioned above the bar, centered on mouse X position
- Tooltip styled consistent with existing `.tooltip` CSS class (dark bg, border, mono font)
- Auto-dismiss on mouse leave

**Files touched:**
- `frontend/src/pages/ModelBuilder/Overview/FootballField.tsx` — hover state, tooltip rendering
- `frontend/src/pages/ModelBuilder/Overview/FootballField.module.css` — tooltip positioning and styling

#### 2E. Composite Detail Section Below Chart
**Goal:** After the composite bar row, add a summary section that surfaces the key takeaways without needing to look elsewhere.

**Content:**
```
┌──────────────────────────────────────────────────────────────────┐
│  COMPOSITE SUMMARY                                                │
│                                                                    │
│  Bear $155.20    Base $182.10    Bull $210.50    Current $158.65  │
│  Spread: $55.30 (35.7%)    Upside: +14.8%                        │
│  Agreement: Moderate    Highest: DCF ($195)    Lowest: DDM ($162) │
└──────────────────────────────────────────────────────────────────┘
```

- Sits directly below the composite row, inside the football field card (not a separate card)
- Compact horizontal layout with key stats
- Uses agreement level badge (same component/style as AgreementPanel)
- Effectively gives the user the "so what" without scrolling up

**Data available:** All of this already exists in `ModelOverviewResult` — `composite_bear`, `composite_base`, `composite_bull`, `current_price`, `composite_upside_pct`, `agreement.level`, `agreement.highest_model`, `agreement.lowest_model`. The football field component just needs to receive these as additional props.

**Files touched:**
- `frontend/src/pages/ModelBuilder/Overview/FootballField.tsx` — add composite summary section, accept new props
- `frontend/src/pages/ModelBuilder/Overview/FootballField.module.css` — summary section layout
- `frontend/src/pages/ModelBuilder/Overview/OverviewTab.tsx` — pass additional data props to FootballField

#### 2F. Scale Axis Improvements
**Current:** 5 ticks at top with small `$XXX.XX` labels. Easy to miss.
**Changes:**
- Add light vertical gridlines from each tick extending down through all rows (very subtle, `--border-subtle` at 30% opacity)
- Increase tick font size from 10px to 11px
- Add the current price as a labeled tick on the scale axis (yellow, matching the dashed line color)
- Keep the dashed yellow vertical line through all rows but add a small "Current: $XXX" label at the bottom of the chart

**Files touched:**
- `frontend/src/pages/ModelBuilder/Overview/FootballField.tsx` — gridlines, current price tick
- `frontend/src/pages/ModelBuilder/Overview/FootballField.module.css` — gridline styles

---

## AREA 3: UNDERSCORE SYNTAX CLEANUP

### Problem
Backend sends raw Python-style keys (`revenue_based`, `SIGNIFICANT_DISAGREEMENT`, `upside_base`, etc.). The frontend has `MODEL_LABELS` maps in each component, but there are gaps where raw keys leak through to the UI.

### Audit & Fix Plan

**Known leak points to verify and fix:**

1. **Model names in included/excluded tags** (`OverviewTab.tsx` line: `data.included_models.map((m) => <span className={styles.modelTag}>{m}</span>)`) — displays raw `revenue_based`. Needs `MODEL_LABELS[m] ?? m` mapping.

2. **Agreement level badge** (`AgreementPanel.tsx`) — `formatLevel()` does `replace(/_/g, ' ')` which works, but the output is "Significant Disagreement" in title case. Verify this renders correctly for all levels: `STRONG`, `MODERATE`, `WEAK`, `SIGNIFICANT_DISAGREEMENT`, `N/A`.

3. **Excluded models text** (`WeightsPanel.tsx` line: `excluded_models.join(', ')`) — displays raw keys. Needs label mapping.

4. **Divergence pair model names** (`AgreementPanel.tsx`) — uses `formatLabel()` which maps correctly via `MODEL_LABELS`. Confirmed OK.

5. **Scenario table model names** (`ScenarioTable.tsx`) — uses `MODEL_LABELS[row.model_name] ?? row.model_name`. Confirmed OK but `row.model_name` fallback could show raw key for unexpected model types.

6. **Football field model names** (`FootballField.tsx`) — uses `MODEL_LABELS[row.model_name] ?? row.model_name`. Same fallback concern.

7. **Warning messages** (`OverviewTab.tsx`) — warnings come from backend with text like "Revenue-Based engine failed: ...". The backend `service.py` uses display names in warning text. Confirmed OK.

8. **Reasoning text** (`agreement.py` backend) — uses `_display_name()` which maps correctly. Confirmed OK.

### Fix Approach
- Create a single shared `displayModelName(key: string): string` utility function in `frontend/src/utils/format.ts` (or similar) that all components import
- Replace all per-component `MODEL_LABELS` maps with this single utility
- The utility should handle: `dcf` → "DCF", `ddm` → "DDM", `comps` → "Comps", `revenue_based` → "Revenue-Based", `Composite` → "Composite"
- For agreement levels: create a `displayAgreementLevel(level: string): string` utility that handles all known levels cleanly
- Any unknown key should have underscores replaced with spaces and be title-cased as a fallback

**Files touched:**
- `frontend/src/utils/format.ts` — new file (or add to existing utility if one exists) with `displayModelName()` and `displayAgreementLevel()`
- `frontend/src/pages/ModelBuilder/Overview/OverviewTab.tsx` — use shared utility for included/excluded model tags
- `frontend/src/pages/ModelBuilder/Overview/FootballField.tsx` — replace local MODEL_LABELS
- `frontend/src/pages/ModelBuilder/Overview/ScenarioTable.tsx` — replace local MODEL_LABELS
- `frontend/src/pages/ModelBuilder/Overview/WeightsPanel.tsx` — replace local MODEL_LABELS, fix excluded_models display
- `frontend/src/pages/ModelBuilder/Overview/AgreementPanel.tsx` — replace local MODEL_LABELS and formatLevel
- `frontend/src/pages/ModelBuilder/ModelBuilderPage.tsx` — verify MODEL_TYPE_LABELS usage is consistent

---

## SESSION ORGANIZATION (Recommended for PM)

### Session 8A — Overview Tab Overhaul (Frontend Only)
**Scope:** All three areas (layout reorder, football field overhaul, underscore cleanup)
**Files:**
- `OverviewTab.tsx` — layout reorder, pass new props
- `FootballField.tsx` — full overhaul (size, labels, gradient, tooltips, composite detail, scale)
- `FootballField.module.css` — full overhaul
- `ScenarioTable.tsx` — use shared utility (minor)
- `WeightsPanel.tsx` — use shared utility, fix excluded display (minor)
- `AgreementPanel.tsx` — use shared utility (minor)
- `format.ts` or `utils/` — new shared display name utilities
- `OverviewTab.module.css` — minor spacing adjustments from reorder

**Complexity:** Medium-High (football field is the bulk of the work — positioning, collision detection, tooltips, responsive layout)
**Estimated acceptance criteria:** 20–25

**Note:** This is one session because all changes are frontend-only, all within the Overview directory, and the football field overhaul is the clear centerpiece. The underscore cleanup and layout reorder are quick additions that naturally fit alongside the chart work.

---

## DEPENDENCIES & RISKS

| Risk | Mitigation |
|------|------------|
| Price label collision on narrow ranges | Implement collision detection: hide overlapping labels, show in tooltip instead |
| Football field responsive breakpoints | Test at compact (1024px), standard (1280px), and wide (1600px+) layouts. Labels may need to hide at compact. |
| Tooltip positioning at chart edges | Clamp tooltip X position to stay within the football field container bounds |
| Shared format utility breaks other imports | Keep backward-compatible — existing local MODEL_LABELS can coexist during migration |

---

## DECISIONS MADE

1. Layout: Scenario Comparison at top, Football Field at bottom
2. Football field bars: taller (28–32px models, 36–40px composite), no max-height on container
3. Bear/bull price labels directly on bars with collision detection fallback to tooltip
4. Gradient: wider contrast from light blue (#60A5FA) to deep blue (#1D4ED8)
5. Hover tooltips with full model detail (prices, upside %, weight, confidence)
6. Composite detail summary section below composite bar inside the football field card
7. Right-side column switches from base price to upside/downside percentage
8. Scale axis gets subtle gridlines and a labeled current price tick
9. Single shared `displayModelName()` utility replaces all per-component MODEL_LABELS maps
10. Standing directive: all graphs across future tabs will follow this information-density standard

---

*End of Model Builder — Overview Sub-Tab Update Plan*
*Phase 8A · Prepared March 4, 2026*
