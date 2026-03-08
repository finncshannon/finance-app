# Finance App — Model Builder: Sensitivity Sub-Tab Update Plan
## Phase 8: Model Builder — Sensitivity

**Prepared by:** Planner (March 5, 2026)
**Recipient:** PM Agent
**Scope:** Model Builder → Sensitivity sub-tab (Sliders, Tornado, Monte Carlo, Data Tables)

---

## PLAN SUMMARY

Four sub-panel workstreams plus cross-cutting work:

1. **Sliders** — Percent formatting, current-assumption marker, smoother precision (extra decimal), state persistence, Push to Assumptions button
2. **Tornado** — Fidelity-level chart upgrade with better labels, value annotations, and clarity
3. **Monte Carlo** — Run from slider assumptions, show input parameter ranges/metrics, minor UI polish
4. **Data Tables** — Variable selectors for rows/columns, zoom/range control on axes, extended grid option
5. **Cross-cutting** — State persistence across tab switches, slider↔assumptions sync (completing 8D prep)

---

## AREA 1: SLIDERS PANEL

### Current Problems
- Numbers show as raw decimals (e.g., `0.112`) instead of percent format (`11.2%`) — the `formatParamValue` function handles this but the slider `value` attribute uses raw values
- No visual marker showing where the current model assumption sits on the slider
- Step precision too coarse: WACC step is `0.005` (0.5%), meaning you can only pick 11.0%, 11.5%, 12.0% — can't get 11.2% or 11.39%
- State resets when switching away from Sensitivity tab and back
- No way to push slider values into actual model assumptions

### Changes

#### 1A. Percent Formatting
**Current:** Slider displays raw values. The `formatParamValue` function converts for the label text, but the slider thumb position and range ticks show raw decimals.
**Fix:** Ensure all displayed values (slider value label, min/max labels, result banner) consistently use percent format. The slider input itself still operates on raw decimals internally — this is a display-layer fix.

#### 1B. Current Assumption Marker
**Goal:** A thin white vertical line on each slider track showing where the current model assumption value sits. As you drag the slider away from this marker, you can see how far you've deviated from the model's assumption.

**Implementation:**
- Each parameter definition already has `current_value` from the backend
- Render a positioned `<div>` on the slider track at `((current_value - min) / (max - min)) * 100%`
- Style: 2px white line, full height of the track, with a tiny label above ("Current") that appears on hover

#### 1C. Finer Precision (Extra Decimal)
**Current steps:**
- WACC: `0.005` (0.5% increments) → Change to `0.001` (0.1% increments, e.g., 11.2%, 11.3%)
- Terminal Growth: `0.0025` (0.25%) → Change to `0.001` (0.1%)
- Revenue Growth Y1: `0.01` (1%) → Change to `0.005` (0.5%)
- Operating Margin Y1: `0.01` (1%) → Change to `0.005` (0.5%)
- CapEx/Revenue: `0.005` (0.5%) → Change to `0.001` (0.1%)
- Tax Rate: `0.01` (1%) → Change to `0.005` (0.5%)
- Exit Multiple: `0.5` → Change to `0.1`
- NWC/Revenue: `0.005` (0.5%) → Change to `0.001` (0.1%)

This is a backend change to `parameter_defs.py` — the step sizes are defined there and the frontend reads them.

Also update `display_format` to show the extra decimal where needed:
- WACC: `"{:.1%}"` → `"{:.2%}"` (shows 11.20% instead of 11.2%)
- Same for Terminal Growth, CapEx/Revenue, NWC/Revenue

#### 1D. Smoother Slider UX
**Current:** Default HTML range input. Can feel jumpy.
**Changes:**
- Add CSS styling for the slider track and thumb (custom appearance for webkit/moz)
- Slightly larger thumb for easier grabbing
- Subtle track fill color (accent blue from left edge to thumb position)
- Optional: add a number input next to the slider for direct typing of precise values (e.g., type `11.39` directly instead of dragging)

#### 1E. State Persistence
**Problem:** Slider values and result reset when switching to another Model Builder sub-tab and back.
**Fix:** Store slider override state in `modelStore` (not local component state). The `SlidersPanel` reads from and writes to the store. Values persist for the duration of the session and for the current ticker.

**Store additions (completing 8D prep):**
- `modelStore.sliderOverrides: Record<string, number>` — current slider positions
- `modelStore.sliderResult: SliderResult | null` — last computed result
- `modelStore.setSliderOverride(key, value)` — update a single slider
- `modelStore.clearSliderOverrides()` — reset all to defaults

#### 1F. Push to Assumptions Button
**Goal:** After dialing in slider values, a button that pushes those values into the actual model assumptions (overriding the assumption engine's values).

**UI:** A button in the result banner area: "Apply to Model" (or "Push to Assumptions"). When clicked:
1. Copies all current slider overrides into the assumptions override map
2. Navigates to the Assumptions tab (or stays on Sensitivity with a confirmation toast)
3. The Assumptions tab shows the overridden values with "Manual" badges

**Also add:** A "Pull from Model" button that resets all sliders to match the current model assumptions (the reverse direction).

**Implementation:** Uses the `modelStore` methods from 8D prep (`pushSliderToAssumptions`, `pullAssumptionsToSliders`).

**Files touched (all of Area 1):**
- `backend/services/sensitivity/parameter_defs.py` — update step sizes, display formats
- `frontend/src/pages/ModelBuilder/Sensitivity/SlidersPanel.tsx` — current marker, formatting, precision input, push/pull buttons, read from store
- `frontend/src/pages/ModelBuilder/Sensitivity/SlidersPanel.module.css` — custom slider styles, marker, button styles
- `frontend/src/stores/modelStore.ts` — slider state persistence (completing 8D prep)

---

## AREA 2: TORNADO CHART UPGRADE

### Current Problems
- Bars lack value labels — you have to hover to see prices
- Variable names on Y-axis are cut off or small
- No indication of what input range was tested for each variable
- The diverging bar layout can be confusing — unclear which direction is "good" vs "bad"
- No base price annotation on the chart itself

### Changes (Fidelity Upgrade)

#### 2A. Value Labels on Bars
- Each bar endpoint gets a price label: `$165.20` on the left end (downside), `$192.40` on the right end (upside)
- Base price shown as a labeled vertical reference line: dashed white line with "$178.45" label at top

#### 2B. Input Range Annotations
- Next to each variable name on the Y-axis, show the tested range in parentheses: `WACC (8.0% – 14.0%)`
- This tells the user exactly what range was swept for each variable

#### 2C. Spread Labels
- At the right edge of each row, show the total spread: `$27.20` (the difference between the high and low price)
- This immediately tells you which variables have the most impact

#### 2D. Improved Color Coding
- Bars that move price UP from base: gradient green (light → dark as price increases)
- Bars that move price DOWN from base: gradient red (light → dark as price decreases)
- Currently uses flat colors — gradient adds visual weight proportional to magnitude

#### 2E. Variable Ranking Annotation
- Add a rank number (#1, #2, #3...) next to each variable name to make the priority order explicit
- Variables are already sorted by spread — this just makes it more scannable

#### 2F. Summary Bar Below Chart
- Below the chart: "Most sensitive to WACC ($27.20 spread) · Least sensitive to NWC/Revenue ($3.10 spread)"
- Quick takeaway without reading the whole chart

**Files touched:**
- `frontend/src/pages/ModelBuilder/Sensitivity/TornadoChart.tsx` — add labels, annotations, improved rendering
- `frontend/src/pages/ModelBuilder/Sensitivity/TornadoChart.module.css` — label positioning, gradient bars, summary bar

---

## AREA 3: MONTE CARLO PANEL

### Changes

#### 3A. Run from Slider Assumptions
**Goal:** Option to run Monte Carlo using the current slider overrides as the base case (instead of the default model assumptions).

**UI:** A toggle or checkbox: "Use slider assumptions as base" next to the Run button. When enabled, the MC simulation POSTs the current slider overrides along with the iteration request. The backend applies those overrides before running the simulation.

**Backend:** The `/sensitivity/monte-carlo` endpoint already accepts an `overrides` field in the request body. The frontend just needs to pass `modelStore.sliderOverrides` when the toggle is on.

#### 3B. Input Parameter Display
**Goal:** Show what parameters and ranges the MC simulation used, so the user understands what's being varied.

**UI:** A collapsible "Simulation Parameters" section below the header:
```
SIMULATION PARAMETERS                          [▾ Collapse]
─────────────────────────────────────────────────
Variable              Base Value    Range Tested
WACC                  10.2%         8.0% – 14.0%
Terminal Growth       2.5%          0.0% – 5.0%
Revenue Growth Y1     12.0%         -10% – 60%
Operating Margin Y1   18.5%         -20% – 60%
CapEx / Revenue       5.2%          1% – 25%
...
```

This data comes from the parameter definitions (already fetched for sliders) combined with the base assumption values.

#### 3C. UI Polish
- Histogram: add subtle gradient fill to bars (instead of flat color), smooth the bar edges
- Add a vertical line for the median price (in addition to current price line)
- Add a shaded region showing the P25–P75 interquartile range
- Stats panel: slightly better formatting — group Mean/Median/StdDev as "Central Tendency", percentiles as "Distribution", probabilities as "Risk Assessment"
- Keep all existing data and layout — this is polish, not restructure

**Files touched:**
- `frontend/src/pages/ModelBuilder/Sensitivity/MonteCarloPanel.tsx` — slider override toggle, parameter display, UI polish
- `frontend/src/pages/ModelBuilder/Sensitivity/MonteCarloPanel.module.css` — parameter table styles, chart polish

---

## AREA 4: DATA TABLES

### Changes

#### 4A. Variable Selectors
**Current:** Defaults to WACC × Terminal Growth. No way to change the row/column variables.
**Fix:** Add dropdown selectors for row variable and column variable, populated from the parameter definitions list.

**UI:**
```
Row Variable: [WACC                    ▾]
Col Variable: [Terminal Growth Rate     ▾]
                                    [Generate Table]
```

The backend already supports `row_variable` and `col_variable` parameters — the frontend just needs to pass them. The `DEFAULT_PAIRS` in the backend provide good presets, and the full `VARIABLE_RANGES` dict supports any combination.

**Add preset buttons** for common combinations:
- "WACC × Terminal Growth" (default)
- "WACC × Exit Multiple"
- "Revenue Growth × Op Margin"

#### 4B. Zoom / Range Control
**Goal:** Instead of always showing the full range (e.g., WACC 4%–20%), let the user zoom into a tighter range (e.g., 8%–12%) for more granular view.

**UI:** Under each variable selector, add min/max range inputs:
```
Row Variable: [WACC ▾]    Range: [ 8.0 ]% to [ 12.0 ]%
Col Variable: [Terminal Growth ▾]  Range: [ 1.0 ]% to [ 4.0 ]%
Grid Size: [9 ▾] (5 | 7 | 9 | 11 | 13)
                                    [Generate Table]
```

**Behavior:**
- Default ranges come from `VARIABLE_RANGES` in the backend
- User can narrow the range to zoom in — same number of grid cells but tighter spacing between them
- This gives you the "zoom" effect: at full range a 9×9 grid shows WACC in 2% steps, but zoomed to 8–12% it shows 0.5% steps
- Grid size selector: allow 5, 7, 9, 11, or 13 (backend already supports 5–13)

**Backend changes:** The `/sensitivity/table-2d` endpoint needs to accept optional `row_min`, `row_max`, `col_min`, `col_max` parameters. The `build_centered_steps` function already takes `range_min` and `range_max` — just need to override them from the request.

#### 4C. Table Polish
- Show the current base value highlighted more prominently (currently has `cellBase` class — make it stand out more, maybe a thicker border or glow)
- Add row/column headers that show which direction improves value (↑ or ↓ arrow)
- Hover on any cell shows a tooltip: "WACC: 10.0%, Terminal Growth: 3.0% → $185.20 (+16.3%)"

**Files touched:**
- `backend/services/sensitivity/tables_2d.py` — accept custom range parameters
- `backend/routers/models_router.py` — add range params to table-2d endpoint
- `frontend/src/pages/ModelBuilder/Sensitivity/DataTablePanel.tsx` — variable selectors, range inputs, grid size selector, presets, tooltip
- `frontend/src/pages/ModelBuilder/Sensitivity/DataTablePanel.module.css` — selector styles, range input styles, base cell emphasis

---

## AREA 5: CROSS-CUTTING

#### 5A. State Persistence
All four sensitivity panels should persist their state when switching tabs:
- Sliders: override values + last result → stored in `modelStore`
- Tornado: last result → stored in `modelStore`  
- Monte Carlo: last result + iteration count → stored in `modelStore`
- Data Tables: last result + variable selections + range settings → stored in `modelStore`

This prevents re-fetching/re-computing when the user switches to Assumptions and back.

#### 5B. Slider ↔ Assumptions Sync (Completing 8D)
Full implementation of the bidirectional sync:
- **Push to Assumptions:** Button on Sliders panel. Copies slider overrides to assumption overrides in modelStore. Shows confirmation.
- **Pull from Assumptions:** Button on Sliders panel. Resets sliders to match current assumption values. 
- **Pending changes banner:** When slider overrides differ from model assumptions, show a subtle banner: "Sliders differ from model assumptions. [Apply to Model] [Reset to Model]"

**Files touched (Area 5):**
- `frontend/src/stores/modelStore.ts` — sensitivity state persistence, sync methods
- `frontend/src/pages/ModelBuilder/Sensitivity/SlidersPanel.tsx` — sync buttons, banner

---

## SESSION ORGANIZATION (Recommended for PM)

### Session 8L — Sensitivity Backend Updates (Backend Only)
**Scope:** Areas 1C (step precision), 4B (range params)
**Files:**
- `backend/services/sensitivity/parameter_defs.py` — update step sizes, display formats
- `backend/services/sensitivity/tables_2d.py` — accept custom range parameters
- `backend/routers/models_router.py` — add range params to table-2d endpoint, update Table2DRequest model
**Complexity:** Low (parameter value changes, one new endpoint param)
**Estimated acceptance criteria:** 6–8

### Session 8M — Sliders + State Persistence + Sync (Frontend Only)
**Scope:** Areas 1A–1F, 5A, 5B
**Files:**
- `SlidersPanel.tsx` — formatting, marker, precision input, push/pull buttons, read from store
- `SlidersPanel.module.css` — custom slider styles, marker, buttons
- `modelStore.ts` — slider state, sensitivity persistence, sync methods
**Complexity:** Medium-High (custom slider styling, store integration, sync logic)
**Estimated acceptance criteria:** 18–22
**Depends on:** Session 8L (precision steps), Session 8D (sync prep)

### Session 8N — Tornado + Monte Carlo + Data Tables (Frontend Only)
**Scope:** Areas 2, 3, 4A–4C
**Files:**
- `TornadoChart.tsx` — labels, annotations, gradient bars, summary
- `TornadoChart.module.css` — new styles
- `MonteCarloPanel.tsx` — slider toggle, parameter display, UI polish
- `MonteCarloPanel.module.css` — new styles
- `DataTablePanel.tsx` — variable selectors, range inputs, grid size, presets, tooltip
- `DataTablePanel.module.css` — new styles
**Complexity:** Medium-High (three panels updated, chart enhancements, new controls)
**Estimated acceptance criteria:** 22–28
**Depends on:** Session 8L (backend range params for data tables)

---

## DEPENDENCIES & RISKS

| Risk | Mitigation |
|------|------------|
| Finer slider precision (0.1% steps) creates too many positions, feels imprecise with drag | Add direct number input field next to slider for precise typing; slider is for rough exploration, input is for exact values |
| Data table with custom tight ranges produces NaN (terminal growth ≥ WACC) | Backend already enforces terminal_growth < wacc constraint; add frontend validation on range inputs |
| Monte Carlo with slider overrides produces different results than expected | Show clear labeling: "Running with slider assumptions" vs "Running with model assumptions" |
| State persistence in modelStore grows large (MC histogram data) | Store only the result summary, not raw iteration data; histogram bins are already aggregated |
| Data table variable selectors allow same variable for both row and col | Frontend validation: disable the selected row variable in the column dropdown and vice versa |

---

## DECISIONS MADE

1. WACC slider precision: 0.1% steps (was 0.5%), all other parameters similarly refined
2. White marker line on each slider showing current model assumption value
3. Direct number input alongside each slider for precise value entry
4. Slider state persisted in modelStore across tab switches
5. Push/Pull buttons for bidirectional slider↔assumptions sync
6. Tornado gets value labels on bar endpoints, input range annotations, spread labels, rank numbers
7. Monte Carlo can run from slider overrides via toggle
8. Monte Carlo shows parameter ranges used for simulation
9. Data tables get variable selectors, zoom/range control on each axis, grid size selector
10. Data table zoom: user sets custom min/max per axis, same grid cells but tighter spacing
11. Preset buttons for common variable pairs on data tables

---

*End of Model Builder — Sensitivity Sub-Tab Update Plan*
*Phase 8L–8N · Prepared March 5, 2026*
