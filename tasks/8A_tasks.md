# Session 8A — Overview Tab Overhaul (Layout, Football Field, displayNames.ts)
## Phase 8: Model Builder

**Priority:** Normal
**Type:** Frontend Only
**Depends On:** None
**Spec Reference:** `specs/phase8_model_builder_overview.md` → Areas 1, 2, 3

---

## SCOPE SUMMARY

Reorder the Overview tab layout (Scenario Table on top, Football Field on bottom). Overhaul the Football Field chart with taller bars, bear/bull price labels, wider gradient contrast, hover tooltips, a composite detail summary section, and scale axis gridlines. Create the shared `displayNames.ts` utility and migrate all per-component `MODEL_LABELS` maps to it. This session creates the foundational display name utility used by every subsequent frontend session.

---

## TASKS

### Task 1: Create Shared displayNames.ts Utility
**Description:** Create the `frontend/src/utils/displayNames.ts` file that all components will import for converting backend snake_case keys to display names. This is the single source of truth defined in `cross_cutting_underscore_cleanup.md`.

**Subtasks:**
- [ ] 1.1 — Create directory `frontend/src/utils/`
- [ ] 1.2 — Create `frontend/src/utils/displayNames.ts` with the following exports:
  - `displayModelName(key: string): string` — maps `dcf`→"DCF", `ddm`→"DDM", `comps`→"Comps", `revenue_based`→"Revenue-Based", `Composite`→"Composite"
  - `displayAgreementLevel(level: string): string` — maps `STRONG`→"Strong Agreement", `MODERATE`→"Moderate Agreement", `WEAK`→"Weak Agreement", `SIGNIFICANT_DISAGREEMENT`→"Significant Disagreement", `N/A`→"N/A"
  - `displayStageName(stage: string): string` — maps `high_growth`→"High Growth", `transition`→"Transition", `terminal`→"Terminal"
  - `displayEventType(type: string): string` — maps `earnings`→"Earnings", `ex_dividend`→"Ex-Dividend", `dividend`→"Dividend", `filing`→"Filing"
  - `displayAlertType(type: string): string` — maps `price_above`→"Price Above", `price_below`→"Price Below", `pct_change`→"% Change", `intrinsic_cross`→"Intrinsic Cross"
  - `displayTransactionType(type: string): string` — maps `BUY`→"Buy", `SELL`→"Sell", `DIVIDEND`→"Dividend", `DRIP`→"DRIP", `SPLIT`→"Split", `ADJUSTMENT`→"Adjustment"
  - `displayLabel(key: string): string` — catch-all that checks all maps, falls back to `titleCase()`
  - Private `titleCase(str: string): string` — replaces underscores with spaces, capitalizes first letter of each word
- [ ] 1.3 — All known maps should be defined as module-level `Record<string, string>` constants (not exported directly — accessed through the functions).

**Implementation Notes:**
- This file follows the exact spec from `cross_cutting_underscore_cleanup.md`.
- The `@/utils/displayNames` import path will work because `tsconfig.json` has `"@/*": ["src/*"]`.
- Future sessions will import from this utility. This session migrates the Overview components; subsequent sessions (8I, etc.) migrate other modules.

---

### Task 2: Layout Reorder
**Description:** Move Scenario Comparison Table above the Weights+Agreement row, and Football Field below it.

**Subtasks:**
- [ ] 2.1 — In `frontend/src/pages/ModelBuilder/Overview/OverviewTab.tsx`, reorder the JSX grid sections:
  - Current order: CompositeBar → Warnings → ModelTags → **FootballField** → Weights+Agreement → **ScenarioTable**
  - New order: CompositeBar → Warnings → ModelTags → **ScenarioTable** → Weights+Agreement → **FootballField**
- [ ] 2.2 — In `OverviewTab.tsx`, update the included_models tags to use `displayModelName()` instead of raw key:
  ```tsx
  {data.included_models.map((m) => (
    <span key={m} className={styles.modelTag}>{displayModelName(m)}</span>
  ))}
  ```
- [ ] 2.3 — Update the excluded models count text (if desired, show the excluded model names using `displayModelName()`).
- [ ] 2.4 — Pass additional props to `<FootballField>` for the composite detail section: `currentPrice`, `compositeUpsidePct`, `agreement` (level, highest_model, highest_price, lowest_model, lowest_price).

**Implementation Notes:**
- The grid layout uses `styles.gridRow` and `styles.gridFull` / `styles.gridMiddle`. The reorder is just moving JSX blocks — no CSS grid changes needed.

---

### Task 3: Football Field Size & Proportions
**Description:** Make the football field larger and more substantial.

**Subtasks:**
- [ ] 3.1 — In `FootballField.module.css`:
  - Increase `.row` height from 32px to 48px (model rows)
  - Increase `.bar` height from 16px to 28px, adjust `top` accordingly
  - Increase `.barComposite` height from 20px to 36px
  - Increase `.baseMarker` height to match new bar height
  - Increase `.label` flex-basis from 140px to 160px
  - Increase `.scaleRow` height from 20px to 24px, adjust margin-left to 160px
  - Increase `.priceText` flex-basis from 80px to 90px
  - Add more vertical padding between rows: increase gap from `var(--space-2)` to `var(--space-3)`
  - Increase `.rowComposite` margin-top and padding-top
  - `.track` height should match new bar heights (28px for model, 36px for composite)

---

### Task 4: Bear/Bull Price Labels on Bars
**Description:** Add price annotations directly on each bar — bear at left edge, base at marker, bull at right edge.

**Subtasks:**
- [ ] 4.1 — In `FootballField.tsx`, for each model row, add three `<span>` price label elements positioned absolutely within the `.track`:
  - Bear label: positioned at `left: {bearLeft}%`, anchored to bar left edge
  - Base label: positioned at `left: {baseLeft}%`, anchored to base marker
  - Bull label: positioned at `left: {bullLeft}%`, anchored to bar right edge
- [ ] 4.2 — Implement collision detection: if two labels are within 40px of each other (based on percentage-to-pixel conversion), hide the less important one (bear and bull hide before base). Use a simple heuristic: calculate pixel distance based on track width (may need a ref to measure).
  - Simpler approach: if `Math.abs(bearLeft - baseLeft) < 8` (percentage points), hide bear label. If `Math.abs(bullLeft - baseLeft) < 8`, hide bull label. Hidden labels will be visible in the hover tooltip.
- [ ] 4.3 — Change the right-side `priceText` column from showing `base_price` to showing upside/downside percentage: `+12.3%` or `-5.2%` (using `(base_price - current_price) / current_price * 100`).
- [ ] 4.4 — Same treatment for composite row: bear/bull/base labels + upside percentage on right.
- [ ] 4.5 — In `FootballField.module.css`, add styles for price labels:
  - `.priceOnBar` — `position: absolute; font-family: var(--font-mono); font-size: 9px; color: var(--text-tertiary); transform: translateX(-50%); top: -14px; white-space: nowrap;`
  - `.priceOnBarBase` — same but `font-weight: 600; color: var(--text-secondary); font-size: 10px;`
  - `.priceOnBarHidden` — `display: none;` (applied when collision detected)

---

### Task 5: Wider Gradient Contrast
**Description:** Increase the visual differentiation between bear and bull ends of the bar.

**Subtasks:**
- [ ] 5.1 — In `FootballField.module.css`, update `.bar` gradient:
  - Old: `linear-gradient(90deg, #1E3A5F, #2563EB)`
  - New: `linear-gradient(90deg, #60A5FA, #1D4ED8)` (light blue → deep blue)
- [ ] 5.2 — Update `.barComposite` gradient:
  - New: `linear-gradient(90deg, #93C5FD, #2563EB)` (brighter range)
- [ ] 5.3 — Increase `.bar` opacity from 0.7 to 0.8. `.barComposite` from 0.85 to 0.9.

---

### Task 6: Hover Tooltips
**Description:** Hovering any bar shows a rich tooltip with full model detail.

**Subtasks:**
- [ ] 6.1 — In `FootballField.tsx`, add hover state tracking: `const [hoveredRow, setHoveredRow] = useState<string | null>(null)` and `const [mouseX, setMouseX] = useState(0)`.
- [ ] 6.2 — On each `.track` div, add `onMouseEnter`, `onMouseMove` (to track X position), and `onMouseLeave` handlers.
- [ ] 6.3 — When `hoveredRow` matches a model row, render a tooltip positioned above the track, centered on `mouseX`:
  ```
  DCF Model
  ─────────────
  Bear:   $142.30  (-10.2%)
  Base:   $178.45  (+12.3%)
  Bull:   $215.80  (+36.0%)
  Weight: 35%
  Confidence: 72
  ```
- [ ] 6.4 — For composite row tooltip:
  ```
  Composite (Weighted Blend)
  ─────────────
  Bear:   $155.20  (-2.1%)
  Base:   $182.10  (+14.8%)
  Bull:   $210.50  (+32.7%)
  ```
- [ ] 6.5 — In `FootballField.module.css`, style the tooltip:
  - Dark background (`var(--bg-primary)`), border (`var(--border-medium)`), rounded
  - Mono font, 10–11px
  - `position: absolute; z-index: 10; pointer-events: none;`
  - Clamp position to stay within container bounds (CSS `max()` / `min()` or JS clamping)

---

### Task 7: Composite Detail Summary Section
**Description:** Add a summary stats section below the composite bar row, inside the football field card.

**Subtasks:**
- [ ] 7.1 — In `FootballField.tsx`, accept new props: `currentPrice: number`, `compositeUpsidePct: number | null`, `agreement: { level: string; highest_model: string | null; highest_price: number | null; lowest_model: string | null; lowest_price: number | null }`.
- [ ] 7.2 — After the composite row, render a `.compositeSummary` section:
  ```
  COMPOSITE SUMMARY
  Bear $155.20    Base $182.10    Bull $210.50    Current $158.65
  Spread: $55.30 (35.7%)    Upside: +14.8%
  Agreement: Moderate    Highest: DCF ($195)    Lowest: DDM ($162)
  ```
- [ ] 7.3 — Use `displayModelName()` for highest/lowest model names and `displayAgreementLevel()` for the agreement level badge.
- [ ] 7.4 — In `FootballField.module.css`, add `.compositeSummary` styles:
  - Compact horizontal layout, light separator above
  - Small font (11px), mono for numbers, sans for labels
  - Agreement level uses a badge with color based on level (reuse badge color logic from AgreementPanel)

---

### Task 8: Scale Axis Improvements
**Description:** Add gridlines, increase tick font, add current price tick at bottom.

**Subtasks:**
- [ ] 8.1 — In `FootballField.tsx`, add subtle vertical gridlines extending from each scale tick down through all rows. Render as positioned `<div>` elements inside the container.
- [ ] 8.2 — In `FootballField.module.css`:
  - `.gridline` — `position: absolute; top: 0; bottom: 0; width: 1px; background: var(--border-subtle); opacity: 0.3; pointer-events: none; z-index: 0;`
  - Increase `.scaleTick` font-size from 10px to 11px
- [ ] 8.3 — Add a "Current: $XXX" label at the bottom of the chart, positioned at the current price line's X position, styled in `var(--color-warning)`.

---

### Task 9: Migrate Overview Components to Shared Utility
**Description:** Replace all per-component `MODEL_LABELS` maps with imports from `displayNames.ts`.

**Subtasks:**
- [ ] 9.1 — In `FootballField.tsx`: remove local `MODEL_LABELS`, import `displayModelName` from `@/utils/displayNames`. Replace `MODEL_LABELS[row.model_name] ?? row.model_name` with `displayModelName(row.model_name)`.
- [ ] 9.2 — In `ScenarioTable.tsx`: remove local `MODEL_LABELS`, import `displayModelName`. Replace all usages.
- [ ] 9.3 — In `WeightsPanel.tsx`: remove local `MODEL_LABELS`, import `displayModelName`. Replace all usages. Fix excluded models display: `excluded_models.map(m => displayModelName(m)).join(', ')`.
- [ ] 9.4 — In `AgreementPanel.tsx`: remove local `MODEL_LABELS` and `formatLevel()`. Import `displayModelName` and `displayAgreementLevel`. Replace `formatLabel(key)` with `displayModelName(key)`. Replace `formatLevel(level)` with `displayAgreementLevel(level)`.
- [ ] 9.5 — In `OverviewTab.tsx`: import `displayModelName`. Use for included/excluded model tags.

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: `frontend/src/utils/displayNames.ts` exists and exports `displayModelName`, `displayAgreementLevel`, `displayStageName`, `displayEventType`, `displayAlertType`, `displayTransactionType`, `displayLabel`.
- [ ] AC-2: `displayModelName('revenue_based')` returns "Revenue-Based", `displayModelName('dcf')` returns "DCF".
- [ ] AC-3: `displayAgreementLevel('SIGNIFICANT_DISAGREEMENT')` returns "Significant Disagreement".
- [ ] AC-4: `displayLabel()` catch-all checks all maps before falling back to titleCase.
- [ ] AC-5: Layout order is: CompositeBar → Warnings → ModelTags → ScenarioTable → Weights+Agreement → FootballField.
- [ ] AC-6: Football field bars are taller: ~28px for models, ~36px for composite.
- [ ] AC-7: Bear/bull/base price labels are visible on each bar.
- [ ] AC-8: Price labels have collision detection — overlapping labels are hidden.
- [ ] AC-9: Right-side column shows upside/downside percentage instead of redundant base price.
- [ ] AC-10: Gradient is wider: `#60A5FA` → `#1D4ED8` for model bars.
- [ ] AC-11: Hovering a bar shows a rich tooltip with bear/base/bull prices, upside %, weight, confidence.
- [ ] AC-12: Tooltip stays within container bounds.
- [ ] AC-13: Composite detail summary section appears below composite bar with: prices, spread, upside, agreement level, highest/lowest model.
- [ ] AC-14: Composite summary uses `displayModelName()` and `displayAgreementLevel()`.
- [ ] AC-15: Subtle vertical gridlines extend from scale ticks through all rows.
- [ ] AC-16: Scale tick font is 11px (was 10px).
- [ ] AC-17: "Current: $XXX" label appears at bottom of chart at current price position.
- [ ] AC-18: No per-component `MODEL_LABELS` maps remain in Overview components — all use shared utility.
- [ ] AC-19: Excluded models in WeightsPanel display properly (e.g., "Revenue-Based" not "revenue_based").
- [ ] AC-20: Included model tags in OverviewTab display properly (e.g., "Revenue-Based" not "revenue_based").
- [ ] AC-21: Agreement level badge displays properly (e.g., "Significant Disagreement" not "SIGNIFICANT_DISAGREEMENT").
- [ ] AC-22: No `replace(/_/g, ' ')` inline calls remain in Overview components.
- [ ] AC-23: Label column width is 160px (was 140px).
- [ ] AC-24: Football field feels substantial — no max-height constraints, generous spacing.
- [ ] AC-25: All chart elements are responsive at 1024px, 1280px, and 1600px+ widths.

---

## FILES TOUCHED

**New files:**
- `frontend/src/utils/displayNames.ts` — shared display name utility (created in this session, used by all future frontend sessions)

**Modified files:**
- `frontend/src/pages/ModelBuilder/Overview/OverviewTab.tsx` — layout reorder, import displayNames, pass new props to FootballField
- `frontend/src/pages/ModelBuilder/Overview/OverviewTab.module.css` — minor spacing adjustments
- `frontend/src/pages/ModelBuilder/Overview/FootballField.tsx` — full overhaul: taller bars, price labels, collision detection, hover tooltips, composite summary, gridlines, current price label, migrate to displayNames
- `frontend/src/pages/ModelBuilder/Overview/FootballField.module.css` — full overhaul: bar heights, gradient, price label styles, tooltip, gridlines, composite summary
- `frontend/src/pages/ModelBuilder/Overview/ScenarioTable.tsx` — remove MODEL_LABELS, import displayModelName
- `frontend/src/pages/ModelBuilder/Overview/WeightsPanel.tsx` — remove MODEL_LABELS, import displayModelName, fix excluded display
- `frontend/src/pages/ModelBuilder/Overview/AgreementPanel.tsx` — remove MODEL_LABELS and formatLevel, import displayModelName and displayAgreementLevel

---

## BUILDER PROMPT

> **Session 8A — Overview Tab Overhaul (Layout, Football Field, displayNames.ts)**
>
> You are building session 8A of the Finance App v2.0 update.
>
> **What you're doing:** Creating the shared `displayNames.ts` utility (used by all future sessions), reordering the Overview tab layout, and overhauling the Football Field chart to be information-dense with price labels, tooltips, a composite summary, and improved visuals.
>
> **Context:** The Model Builder Overview tab shows a composite valuation summary: scenario table, football field chart, model weights, and agreement analysis. Currently the football field has thin bars, no price annotations, no tooltips, and subtle gradients. Each component has its own local `MODEL_LABELS` map. You're upgrading all of this.
>
> **Existing code:**
> - `OverviewTab.tsx` — renders: CompositeBar → Warnings → ModelTags → FootballField → Weights+Agreement → ScenarioTable. Uses `api.post<ModelOverviewResult>('/api/v1/model-builder/{ticker}/overview')`. Model tags show raw keys (`data.included_models.map(m => <span>{m}</span>)`).
> - `FootballField.tsx` — renders horizontal bar chart with model rows + composite. Local `MODEL_LABELS` map. Bars are 16px tall. Shows `base_price` on right side. Has `.tooltip` CSS class but no tooltip rendering. Props: `{ data: FootballFieldResult }`.
> - `FootballField.module.css` — `.bar` height 16px, gradient `#1E3A5F→#2563EB`, `.label` flex-basis 140px, `.scaleTick` 10px, `.row` height 32px.
> - `ScenarioTable.tsx` — local `MODEL_LABELS` map. Renders rows with model_name, bear/base/bull prices, confidence, weight, upside.
> - `WeightsPanel.tsx` — local `MODEL_LABELS` (shorter: `revenue_based`→"Rev"). Shows excluded models as `excluded_models.join(', ')` (raw keys).
> - `AgreementPanel.tsx` — local `MODEL_LABELS`, local `formatLevel()` using `replace(/_/g, ' ')`. Badge class based on level.
> - `types/models.ts` — `FootballFieldRow { model_name, bear_price, base_price, bull_price, weight, confidence_score }`, `FootballFieldResult { models, composite, current_price, chart_min, chart_max }`, `ModelOverviewResult { ...all overview data }`.
> - No `utils/` directory exists yet — you're creating it.
> - `tsconfig.json` has path alias `"@/*": ["src/*"]`.
>
> **Cross-cutting rules:**
> - Display Name Rule: All backend snake_case keys displayed in the UI must use the shared `displayNames.ts` utility. Never show raw keys. Never use inline `.replace(/_/g, ' ')`. Import from `@/utils/displayNames`.
> - Chart Quality: All charts must meet Fidelity/Yahoo Finance information-density standards. Proper labels, hover tooltips with full detail, crosshairs, value annotations on bars/lines, responsive formatting, compact axis labels. No decorative or minimal charts.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%).
> - Scenario Order: Bear / Base / Bull (left to right), Base default.
>
> **Task 1: Create `frontend/src/utils/displayNames.ts`**
>
> Create directory `frontend/src/utils/` if it doesn't exist.
>
> Create `frontend/src/utils/displayNames.ts` with the following content (reference implementation — implement exactly this API):
>
> ```typescript
> const MODEL_NAMES: Record<string, string> = {
>   dcf: 'DCF', ddm: 'DDM', comps: 'Comps',
>   revenue_based: 'Revenue-Based', Composite: 'Composite',
> };
> const AGREEMENT_LEVELS: Record<string, string> = {
>   STRONG: 'Strong Agreement', MODERATE: 'Moderate Agreement',
>   WEAK: 'Weak Agreement', SIGNIFICANT_DISAGREEMENT: 'Significant Disagreement',
>   'N/A': 'N/A',
> };
> const DDM_STAGES: Record<string, string> = {
>   high_growth: 'High Growth', transition: 'Transition', terminal: 'Terminal',
> };
> const EVENT_TYPES: Record<string, string> = {
>   earnings: 'Earnings', ex_dividend: 'Ex-Dividend', dividend: 'Dividend', filing: 'Filing',
> };
> const ALERT_TYPES: Record<string, string> = {
>   price_above: 'Price Above', price_below: 'Price Below',
>   pct_change: '% Change', intrinsic_cross: 'Intrinsic Cross',
> };
> const TX_TYPES: Record<string, string> = {
>   BUY: 'Buy', SELL: 'Sell', DIVIDEND: 'Dividend',
>   DRIP: 'DRIP', SPLIT: 'Split', ADJUSTMENT: 'Adjustment',
> };
>
> function titleCase(str: string): string {
>   return str.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
> }
>
> export function displayModelName(key: string): string {
>   return MODEL_NAMES[key] ?? titleCase(key);
> }
> export function displayAgreementLevel(level: string): string {
>   return AGREEMENT_LEVELS[level] ?? titleCase(level);
> }
> export function displayStageName(stage: string): string {
>   return DDM_STAGES[stage] ?? titleCase(stage);
> }
> export function displayEventType(type: string): string {
>   return EVENT_TYPES[type] ?? titleCase(type);
> }
> export function displayAlertType(type: string): string {
>   return ALERT_TYPES[type] ?? titleCase(type);
> }
> export function displayTransactionType(type: string): string {
>   return TX_TYPES[type] ?? type;
> }
> export function displayLabel(key: string): string {
>   return MODEL_NAMES[key] ?? AGREEMENT_LEVELS[key] ?? DDM_STAGES[key]
>     ?? EVENT_TYPES[key] ?? ALERT_TYPES[key] ?? TX_TYPES[key] ?? titleCase(key);
> }
> ```
>
> **Task 2: Layout Reorder**
>
> In `OverviewTab.tsx`, swap the JSX order:
> - Move the ScenarioTable `gridRow` block above the Weights+Agreement `gridMiddle` block
> - Move the FootballField `gridRow` block below the Weights+Agreement block
> - Final order: CompositeBar → Warnings → ModelTags → ScenarioTable → Weights+Agreement → FootballField
>
> Also:
> - Import `displayModelName` from `@/utils/displayNames`
> - Replace `{m}` in model tags with `{displayModelName(m)}`
> - Pass new props to `<FootballField>`:
>   ```tsx
>   <FootballField
>     data={data.football_field}
>     currentPrice={data.current_price}
>     compositeUpsidePct={data.composite_upside_pct}
>     agreement={{
>       level: data.agreement.level,
>       highest_model: data.agreement.highest_model,
>       highest_price: data.agreement.highest_price,
>       lowest_model: data.agreement.lowest_model,
>       lowest_price: data.agreement.lowest_price,
>     }}
>   />
>   ```
>
> **Task 3: Football Field Overhaul**
>
> This is the main body of work. In `FootballField.tsx` and `FootballField.module.css`:
>
> *Size & proportions:*
> - `.row` height → 48px, `.bar` height → 28px, `.barComposite` height → 36px
> - `.label` flex-basis → 160px, `.scaleRow` margin-left → 160px
> - Container gap → `var(--space-3)`
> - `.track` height → 28px (model) / 36px (composite via separate class)
>
> *Price labels on bars:*
> - Add bear/base/bull price `<span>` elements positioned absolutely in each track
> - Collision detection: if `Math.abs(bearLeft - baseLeft) < 8` percentage points, hide bear label; same for bull/base
> - Right column: show upside % instead of base price
>
> *Gradient:*
> - `.bar` → `linear-gradient(90deg, #60A5FA, #1D4ED8)`, opacity 0.8
> - `.barComposite` → `linear-gradient(90deg, #93C5FD, #2563EB)`, opacity 0.9
>
> *Hover tooltips:*
> - Track hover state per row, render tooltip above hovered bar
> - Tooltip content: model name, bear/base/bull prices with upside %, weight, confidence
> - Style: dark bg, border, mono font, z-index 10, pointer-events none
> - Clamp X position to container
>
> *Composite detail summary:*
> - Accept new props: `currentPrice`, `compositeUpsidePct`, `agreement`
> - Render below composite row: Bear/Base/Bull/Current prices, Spread, Upside %, Agreement badge, Highest/Lowest model
> - Use `displayModelName()` and `displayAgreementLevel()`
>
> *Scale improvements:*
> - Subtle gridlines from each tick through all rows (`.gridline { opacity: 0.3; background: var(--border-subtle); }`)
> - Tick font 11px
> - "Current: $XXX" label at bottom in warning color
>
> *Import migration:*
> - Remove local `MODEL_LABELS`, import `displayModelName` from `@/utils/displayNames`
>
> **Task 4: Migrate Remaining Overview Components**
>
> - `ScenarioTable.tsx`: remove `MODEL_LABELS`, import `displayModelName`
> - `WeightsPanel.tsx`: remove `MODEL_LABELS`, import `displayModelName`, fix excluded: `excluded_models.map(m => displayModelName(m)).join(', ')`
> - `AgreementPanel.tsx`: remove `MODEL_LABELS` and `formatLevel()`, import `displayModelName` and `displayAgreementLevel`
>
> **Acceptance criteria:**
> 1. `displayNames.ts` exists at `frontend/src/utils/displayNames.ts` with all 7 exports
> 2. `displayModelName('revenue_based')` → "Revenue-Based"
> 3. `displayAgreementLevel('SIGNIFICANT_DISAGREEMENT')` → "Significant Disagreement"
> 4. Layout: ScenarioTable above Weights+Agreement, FootballField at bottom
> 5. Football field bars: 28px models, 36px composite
> 6. Bear/bull/base price labels on bars with collision detection
> 7. Right column shows upside % not base price
> 8. Gradient: light blue → deep blue (`#60A5FA` → `#1D4ED8`)
> 9. Hover tooltip with full model detail (prices, upside, weight, confidence)
> 10. Composite summary section below chart with prices, spread, agreement, highest/lowest
> 11. Gridlines from scale ticks, tick font 11px, "Current" label at bottom
> 12. No local `MODEL_LABELS` maps remain in any Overview component
> 13. No `replace(/_/g, ' ')` calls remain in Overview components
> 14. Excluded models display "Revenue-Based" not "revenue_based"
> 15. Included model tags display "Revenue-Based" not "revenue_based"
> 16. Chart responsive at 1024px/1280px/1600px
>
> **Files to create:**
> - `frontend/src/utils/displayNames.ts`
>
> **Files to modify:**
> - `frontend/src/pages/ModelBuilder/Overview/OverviewTab.tsx`
> - `frontend/src/pages/ModelBuilder/Overview/OverviewTab.module.css` (minor spacing)
> - `frontend/src/pages/ModelBuilder/Overview/FootballField.tsx` (full overhaul)
> - `frontend/src/pages/ModelBuilder/Overview/FootballField.module.css` (full overhaul)
> - `frontend/src/pages/ModelBuilder/Overview/ScenarioTable.tsx`
> - `frontend/src/pages/ModelBuilder/Overview/WeightsPanel.tsx`
> - `frontend/src/pages/ModelBuilder/Overview/AgreementPanel.tsx`
>
> **Technical constraints:**
> - CSS modules (`.module.css`) for all styling
> - Use existing CSS variables from the design system
> - Zustand stores for state (modelStore for ticker, no uiStore needed here)
> - `@/utils/displayNames` import path (tsconfig has `"@/*": ["src/*"]`)
> - Responsive: test at 1024px, 1280px, 1600px
> - Tooltips: use React state for hover, not CSS-only (need dynamic content)
> - No external charting libraries — the football field is custom DOM elements
> - The `FootballFieldResult` type is unchanged — you're just rendering it better
