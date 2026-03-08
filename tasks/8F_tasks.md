# Session 8F — WACC Frontend (Detailed Buildout, Live Recalculation)
## Phase 8: Model Builder

**Priority:** Normal
**Type:** Frontend Only
**Depends On:** 8E (backend must expose wacc_breakdown in AssumptionSet response)
**Spec Reference:** `specs/phase8_model_builder_assumptions_wacc.md` → Areas 2, 3 (frontend)

---

## SCOPE SUMMARY

Replace the current 3-card WACC section (WACC, Cost of Equity, Tax Rate) with a full interactive WACCBreakdown component. Show all WACC components organized into 4 sub-sections (Cost of Equity CAPM, Cost of Debt, Capital Structure, Final WACC). Make inputs editable with live browser-side recalculation — no backend round-trip needed. The final WACC becomes a computed output, not a directly editable field. Add the WACCBreakdown TypeScript interface.

---

## TASKS

### Task 1: Add WACCBreakdown TypeScript Interface
**Description:** Define the TypeScript type matching the backend `WACCResult` model.

**Subtasks:**
- [ ] 1.1 — In `frontend/src/types/models.ts`, add:
  ```typescript
  export interface WACCBreakdown {
    wacc: number;
    cost_of_equity: number;
    cost_of_debt_pre_tax: number;
    cost_of_debt_after_tax: number;
    risk_free_rate: number;
    adjusted_beta: number;
    raw_beta: number;
    erp: number;
    size_premium: number;
    effective_tax_rate: number;
    weight_equity: number;
    weight_debt: number;
    market_cap: number | null;
    total_debt: number | null;
    warnings: string[];
  }
  ```
- [ ] 1.2 — Update the `AssumptionSet` TypeScript interface to include `wacc_breakdown: WACCBreakdown | null`. Check if `AssumptionSet` is already defined in `types/models.ts` — if not (it may be imported from elsewhere), add the field where the type is defined.

**Implementation Notes:**
- The `AssumptionSet` type is currently imported in AssumptionsTab.tsx from `'../../../types/models'`. Check if it's defined there or if it's a more complex path. The backend `AssumptionSet` Pydantic model is in `assumption_engine/models.py` — the frontend mirror should match.

---

### Task 2: Create WACCBreakdown Component
**Description:** Build the full interactive WACC component with 4 sub-sections, editable inputs, and live recalculation.

**Subtasks:**
- [ ] 2.1 — Create `frontend/src/pages/ModelBuilder/Assumptions/WACCBreakdown.tsx`:

**Props:**
```typescript
interface WACCBreakdownProps {
  data: WACCBreakdown;
  overrides: Record<string, number>;
  onOverride: (path: string, value: number) => void;
  confidenceScore?: number;
  reasoning?: string;
}
```

**Internal state (editable inputs):**
```typescript
// Initialize from data, override from overrides map
const rf = overrides['wacc_breakdown.risk_free_rate'] ?? data.risk_free_rate;
const rawBeta = overrides['wacc_breakdown.raw_beta'] ?? data.raw_beta;
const erp = overrides['wacc_breakdown.erp'] ?? data.erp;
const sizePremium = overrides['wacc_breakdown.size_premium'] ?? data.size_premium;
const kdPre = overrides['wacc_breakdown.cost_of_debt_pre_tax'] ?? data.cost_of_debt_pre_tax;
const taxRate = overrides['wacc_breakdown.effective_tax_rate'] ?? data.effective_tax_rate;
const we = overrides['wacc_breakdown.weight_equity'] ?? data.weight_equity;
const wd = overrides['wacc_breakdown.weight_debt'] ?? data.weight_debt;
```

**Computed values (useMemo):**
```typescript
const adjustedBeta = useMemo(() => Math.min((2/3) * rawBeta + (1/3) * 1.0, 2.5), [rawBeta]);
const costOfEquity = useMemo(() => rf + (adjustedBeta * erp) + sizePremium, [rf, adjustedBeta, erp, sizePremium]);
const kdAfter = useMemo(() => kdPre * (1 - taxRate), [kdPre, taxRate]);
const finalWacc = useMemo(() => {
  if (wd === 0) return costOfEquity;
  return (we * costOfEquity) + (wd * kdAfter);
}, [we, wd, costOfEquity, kdAfter]);
```

**Override handler wrapper:**
- When an input changes, call `onOverride('wacc_breakdown.{field}', value)`
- For linked weights: when equity weight changes, also override debt weight as `1 - newEquityWeight` and vice versa

- [ ] 2.2 — Render 4 sub-sections:

**Sub-section 1: Cost of Equity (CAPM)**
| Field | Type | Source Note |
|-------|------|------------|
| Risk-Free Rate | editable % | "Current 10Y Treasury" |
| Equity Risk Premium | editable % | "Market consensus" |
| Raw Beta | editable number | "From Yahoo Finance" |
| Blume Adjusted Beta | computed (read-only) | "(2/3 × raw + 1/3 × 1.0)" |
| Size Premium | editable % | tier label e.g. "Large cap ($10B–$200B)" |
| → Cost of Equity | computed result | "Rf + β(ERP) + SP" |

**Sub-section 2: Cost of Debt**
| Field | Type | Source Note |
|-------|------|------------|
| Interest Expense | read-only $ | "From financials" |
| Total Debt | read-only $ | "From balance sheet" |
| Pre-Tax Cost of Debt | editable % | "Interest / Debt" |
| Effective Tax Rate | editable % | "From tax provision" |
| → After-Tax Cost of Debt | computed result | "Kd × (1 - t)" |

**Sub-section 3: Capital Structure**
| Field | Type | Source Note |
|-------|------|------------|
| Market Cap | read-only $ | "From market data" |
| Total Debt | read-only $ | "From balance sheet" |
| Equity Weight (E/V) | editable % (linked) | |
| Debt Weight (D/V) | editable % (linked) | |

**Sub-section 4: Final WACC**
| Field | Type |
|-------|------|
| Computed WACC | result display | formula breakdown shown |

- [ ] 2.3 — Each editable field uses a small inline input (similar to AssumptionCard but inline in a row layout rather than a card). Show an override indicator (blue left border or "Manual" badge) when the value differs from the engine default.

- [ ] 2.4 — Each computed result row shows the formula and the computed value prominently (e.g., `→ Cost of Equity: 12.55%   Rf + β(ERP) + SP`).

- [ ] 2.5 — Final WACC section shows the full formula: `WACC = (94.1% × 12.55%) + (5.9% × 6.16%) = 12.17%` with the actual numbers filled in.

- [ ] 2.6 — Warnings section: if `data.warnings` has entries, show them at the bottom in a subtle warning style.

- [ ] 2.7 — Size premium tier label helper:
```typescript
function getSizeTierLabel(marketCap: number | null): string {
  if (!marketCap) return 'Unknown';
  if (marketCap > 200e9) return 'Mega cap (>$200B)';
  if (marketCap > 10e9) return 'Large cap ($10B–$200B)';
  if (marketCap > 2e9) return 'Mid cap ($2B–$10B)';
  if (marketCap > 300e6) return 'Small cap ($300M–$2B)';
  return 'Micro cap (<$300M)';
}
```

---

### Task 3: Create WACCBreakdown Styles
**Description:** CSS module for the new component.

**Subtasks:**
- [ ] 3.1 — Create `frontend/src/pages/ModelBuilder/Assumptions/WACCBreakdown.module.css`:
  - `.container` — full width, flex column
  - `.computedWacc` — prominent display at top: large font, accent color, mono font for the value
  - `.subSection` — grouped section with header label and horizontal rule
  - `.subSectionTitle` — small uppercase label (e.g., "COST OF EQUITY (CAPM)")
  - `.fieldRow` — flex row: label (left), dots/spacer (middle), input or value (right), source note (far right)
  - `.fieldLabel` — 12px sans, secondary color
  - `.fieldInput` — small inline input matching AssumptionCard's input style (mono font, right-aligned, compact)
  - `.fieldValue` — mono font, right-aligned (for read-only and computed values)
  - `.fieldSource` — 10px, tertiary color, italic
  - `.computedResult` — slightly emphasized row: `→` prefix, bold value, formula note
  - `.overrideIndicator` — blue left border on the field row when overridden
  - `.formulaDisplay` — final WACC formula row: mono font, centered, accent color, slightly larger
  - `.linkedNote` — small text: "Equity and debt weights must sum to 100%"
  - `.warningsList` — styled warning items at bottom

---

### Task 4: Replace WACC Section in AssumptionsTab
**Description:** Swap the current 3-card WACC section with the new WACCBreakdown component.

**Subtasks:**
- [ ] 4.1 — In `AssumptionsTab.tsx`, import the new component:
  ```typescript
  import { WACCBreakdownComponent } from './WACCBreakdown';
  ```
- [ ] 4.2 — Replace the current WACC & Cost of Capital `<Section>` block (which has 3 AssumptionCards for WACC, Cost of Equity, Tax Rate) with:
  ```tsx
  {/* WACC & Cost of Capital */}
  <Section
    title="WACC & Cost of Capital"
    confidence={waccConf}
    reasoning={reasoning['wacc']}
    overallScore={overallScore}
  >
    {data.wacc_breakdown ? (
      <WACCBreakdownComponent
        data={data.wacc_breakdown}
        overrides={overrides}
        onOverride={handleOverride}
        confidenceScore={waccConf?.score}
        reasoning={waccConf?.reasoning}
      />
    ) : (
      <>
        {/* Fallback: old 3-card layout if wacc_breakdown not available */}
        <AssumptionCard
          label="WACC"
          value={overrides[`scenarios.${scenario}.wacc`] ?? scenarioData.wacc}
          unit="pct"
          confidenceScore={waccConf?.score}
          reasoning={waccConf?.reasoning}
          isOverridden={`scenarios.${scenario}.wacc` in overrides}
          onChange={(v) => handleOverride(`scenarios.${scenario}.wacc`, v)}
        />
        <AssumptionCard
          label="Cost of Equity"
          value={overrides[`scenarios.${scenario}.cost_of_equity`] ?? scenarioData.cost_of_equity}
          unit="pct"
          confidenceScore={waccConf?.score}
          isOverridden={`scenarios.${scenario}.cost_of_equity` in overrides}
          onChange={(v) => handleOverride(`scenarios.${scenario}.cost_of_equity`, v)}
        />
        <AssumptionCard
          label="Tax Rate"
          value={overrides[`scenarios.${scenario}.tax_rate`] ?? scenarioData.tax_rate}
          unit="pct"
          confidenceScore={waccConf?.score}
          isOverridden={`scenarios.${scenario}.tax_rate` in overrides}
          onChange={(v) => handleOverride(`scenarios.${scenario}.tax_rate`, v)}
        />
      </>
    )}
  </Section>
  ```
  This keeps backward compatibility — if the backend hasn't been updated yet (no `wacc_breakdown`), the old 3-card layout still works.

- [ ] 4.3 — Update `applyOverrideLocally()` at the bottom of AssumptionsTab.tsx to handle `wacc_breakdown.*` paths:
  ```typescript
  // Parse "wacc_breakdown.risk_free_rate" style paths
  const waccMatch = path.match(/^wacc_breakdown\.(\w+)$/);
  if (waccMatch && next.wacc_breakdown) {
    const field = waccMatch[1];
    if (field && field in next.wacc_breakdown) {
      (next.wacc_breakdown as unknown as Record<string, unknown>)[field] = value;
    }
    return next;
  }
  ```

---

### Task 5: Dollar Formatting Helper
**Description:** Add a compact dollar formatter for read-only fields (Interest Expense, Total Debt, Market Cap).

**Subtasks:**
- [ ] 5.1 — In `WACCBreakdown.tsx`, add a helper:
  ```typescript
  function fmtDollarCompact(v: number | null): string {
    if (v == null) return '—';
    const abs = Math.abs(v);
    const sign = v < 0 ? '-' : '';
    if (abs >= 1e12) return `${sign}$${(abs / 1e12).toFixed(1)}T`;
    if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(1)}B`;
    if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(1)}M`;
    return `${sign}$${abs.toLocaleString()}`;
  }
  ```
  (Similar to the one in Dashboard types, but local to this component.)

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: `WACCBreakdown` TypeScript interface exists in `types/models.ts` matching backend `WACCResult`.
- [ ] AC-2: `AssumptionSet` TypeScript type includes `wacc_breakdown: WACCBreakdown | null`.
- [ ] AC-3: `WACCBreakdownComponent` exists as a new file with 4 sub-sections.
- [ ] AC-4: Cost of Equity sub-section shows: Risk-Free Rate (editable), ERP (editable), Raw Beta (editable), Blume Adjusted Beta (computed), Size Premium (editable), → Cost of Equity (computed).
- [ ] AC-5: Cost of Debt sub-section shows: Interest Expense (read-only), Total Debt (read-only), Pre-Tax Cost of Debt (editable), Tax Rate (editable), → After-Tax Cost of Debt (computed).
- [ ] AC-6: Capital Structure sub-section shows: Market Cap (read-only), Total Debt (read-only), Equity Weight (editable, linked), Debt Weight (editable, linked).
- [ ] AC-7: Final WACC section shows the full formula with actual numbers.
- [ ] AC-8: All computed values update instantly when inputs change (no backend round-trip).
- [ ] AC-9: Blume adjustment formula: `(2/3 × raw + 1/3 × 1.0)`, capped at 2.5.
- [ ] AC-10: CAPM formula: `Rf + β(ERP) + SP`.
- [ ] AC-11: After-tax Kd formula: `Kd × (1 - t)`.
- [ ] AC-12: WACC formula: `(We × Ke) + (Wd × Kd_after)`.
- [ ] AC-13: Linked weights: changing equity weight auto-adjusts debt weight to sum to 100% (and vice versa).
- [ ] AC-14: Overridden fields show visual indicator (blue left border or "Manual" badge).
- [ ] AC-15: Override paths use `wacc_breakdown.*` prefix (e.g., `wacc_breakdown.risk_free_rate`).
- [ ] AC-16: Size premium shows tier label (e.g., "Large cap ($10B–$200B)").
- [ ] AC-17: Read-only dollar fields (Interest Expense, Total Debt, Market Cap) use compact formatting ($15.3B).
- [ ] AC-18: Source notes shown for each field (e.g., "Current 10Y Treasury", "From Yahoo Finance").
- [ ] AC-19: Warnings from `data.warnings` displayed at bottom.
- [ ] AC-20: Falls back to old 3-card layout if `wacc_breakdown` is null (backward compatible).
- [ ] AC-21: `applyOverrideLocally()` handles `wacc_breakdown.*` paths.
- [ ] AC-22: No regressions on other Assumptions sections (revenue, margins, terminal, capital structure, DDM).

---

## FILES TOUCHED

**New files:**
- `frontend/src/pages/ModelBuilder/Assumptions/WACCBreakdown.tsx` — full interactive WACC breakdown component
- `frontend/src/pages/ModelBuilder/Assumptions/WACCBreakdown.module.css` — component styles

**Modified files:**
- `frontend/src/types/models.ts` — add `WACCBreakdown` interface, update `AssumptionSet` type
- `frontend/src/pages/ModelBuilder/Assumptions/AssumptionsTab.tsx` — replace WACC section with new component, update `applyOverrideLocally()`

---

## BUILDER PROMPT

> **Session 8F — WACC Frontend (Detailed Buildout, Live Recalculation)**
>
> You are building session 8F of the Finance App v2.0 update.
>
> **What you're doing:** Replacing the current 3-card WACC section with a full interactive WACCBreakdown component that shows all CAPM/WACC components, allows editing individual inputs, and recomputes the final WACC live in the browser.
>
> **Context:** Session 8E added `wacc_breakdown: WACCResult` to the backend `AssumptionSet` response. This gives the frontend access to all WACC components: risk_free_rate, raw_beta, adjusted_beta, erp, size_premium, cost_of_equity, cost_of_debt_pre_tax/after_tax, effective_tax_rate, weight_equity/debt, market_cap, total_debt, warnings. Currently, the Assumptions tab shows 3 simple AssumptionCards (WACC, Cost of Equity, Tax Rate). You're replacing those with a detailed interactive breakdown.
>
> **Existing code:**
> - `AssumptionsTab.tsx` — renders sections: Revenue Growth, Operating Margins, **WACC & Cost of Capital** (3 AssumptionCards), Terminal Value, Capital Structure, DDM Inputs. The WACC section targets: `scenarios.{scenario}.wacc`, `scenarios.{scenario}.cost_of_equity`, `scenarios.{scenario}.tax_rate`. Override handler: `handleOverride(path, value)` updates `overrides` state and calls `applyOverrideLocally()`.
> - `AssumptionCard.tsx` — compact editable field card. Props: `label, value, unit ('pct'|'abs'|'ratio'|'multiple'), confidenceScore, reasoning, isOverridden, onChange`. Handles display↔internal conversion (pct: display is `value*100`, stored is decimal).
> - `applyOverrideLocally()` — handles `scenarios.*` and `model_assumptions.*` paths. Needs new case for `wacc_breakdown.*`.
> - `types/models.ts` — has `AssumptionSet` (imported from somewhere), `ScenarioProjections`, `ConfidenceDetail`, etc. Needs `WACCBreakdown` interface.
>
> **Cross-cutting rules:**
> - Display Name Rule: All backend snake_case keys displayed in the UI must use the shared `displayNames.ts` utility. Never show raw keys. Never use inline `.replace(/_/g, ' ')`. Import from `@/utils/displayNames`.
> - Chart Quality: All charts must meet Fidelity/Yahoo Finance information-density standards.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%). Display to user as percentages.
> - Scenario Order: Bear / Base / Bull (left to right), Base default.
>
> **Task 1: TypeScript Interface**
>
> In `frontend/src/types/models.ts`, add:
> ```typescript
> export interface WACCBreakdown {
>   wacc: number;
>   cost_of_equity: number;
>   cost_of_debt_pre_tax: number;
>   cost_of_debt_after_tax: number;
>   risk_free_rate: number;
>   adjusted_beta: number;
>   raw_beta: number;
>   erp: number;
>   size_premium: number;
>   effective_tax_rate: number;
>   weight_equity: number;
>   weight_debt: number;
>   market_cap: number | null;
>   total_debt: number | null;
>   warnings: string[];
> }
> ```
>
> Add `wacc_breakdown: WACCBreakdown | null` to the `AssumptionSet` interface/type.
>
> **Task 2: Create WACCBreakdown Component**
>
> Create `frontend/src/pages/ModelBuilder/Assumptions/WACCBreakdown.tsx`:
>
> ```tsx
> interface WACCBreakdownProps {
>   data: WACCBreakdown;
>   overrides: Record<string, number>;
>   onOverride: (path: string, value: number) => void;
>   confidenceScore?: number;
>   reasoning?: string;
> }
> ```
>
> Key implementation patterns:
>
> 1. **Reading values** — check overrides first, fall back to data:
>    ```typescript
>    const rf = overrides['wacc_breakdown.risk_free_rate'] ?? data.risk_free_rate;
>    ```
>
> 2. **Live computation** via useMemo:
>    ```typescript
>    const adjustedBeta = useMemo(() => Math.min((2/3) * rawBeta + (1/3) * 1.0, 2.5), [rawBeta]);
>    const costOfEquity = useMemo(() => rf + (adjustedBeta * erp) + sizePremium, [...]);
>    const kdAfter = useMemo(() => kdPre * (1 - taxRate), [...]);
>    const finalWacc = useMemo(() => wd === 0 ? costOfEquity : (we * costOfEquity) + (wd * kdAfter), [...]);
>    ```
>
> 3. **Editable input** — small inline number input. When changed, call:
>    ```typescript
>    onOverride('wacc_breakdown.risk_free_rate', newValue);
>    ```
>    Values are stored as decimals (0.04 = 4%). Display as percentage in the input.
>
> 4. **Linked weights** — when equity weight changes:
>    ```typescript
>    onOverride('wacc_breakdown.weight_equity', newWe);
>    onOverride('wacc_breakdown.weight_debt', 1 - newWe);
>    ```
>
> 5. **Override indicator** — show blue left border on the row when the field key exists in overrides.
>
> 6. **Sub-sections**: Cost of Equity (CAPM), Cost of Debt, Capital Structure, Final WACC. Each has a small header label, horizontal rule, and list of field rows.
>
> 7. **Computed result rows** start with "→" and show both the value and the formula:
>    ```
>    → Cost of Equity: 12.55%    Rf + β(ERP) + SP
>    ```
>
> 8. **Final WACC formula display**:
>    ```
>    WACC = (94.1% × 12.55%) + (5.9% × 6.16%) = 12.17%
>    ```
>    Fill in the actual computed numbers.
>
> 9. **Read-only fields** (Interest Expense, Total Debt, Market Cap) show compact dollar format and are not editable.
>
> 10. **Source notes** next to each field: "Current 10Y Treasury", "From Yahoo Finance", "Interest / Debt", "From tax provision", "From market data", etc.
>
> 11. **Size tier label**: show next to Size Premium: "Large cap ($10B–$200B)" based on market_cap.
>
> **Task 3: Styles**
>
> Create `WACCBreakdown.module.css` with:
> - Sub-section headers (small uppercase, horizontal rule below)
> - Field rows: flex, label left, value/input right, source note far right
> - Computed result rows: slightly emphasized, `→` prefix, formula in lighter color
> - Final WACC formula: centered, slightly larger, mono font, accent underline
> - Override indicator: `border-left: 3px solid var(--accent-primary)` on overridden rows
> - Read-only fields: no hover effect, slightly dimmer
> - Editable inputs: match AssumptionCard input style (compact, mono, right-aligned, ~60px wide)
> - Linked weight note: small italic text
> - Warnings: muted style at bottom
>
> **Task 4: Replace WACC Section in AssumptionsTab**
>
> In `AssumptionsTab.tsx`:
> - Import the new component
> - Replace the 3-card WACC section with the new component (inside existing Section wrapper)
> - Keep fallback to old layout if `data.wacc_breakdown` is null
> - Add `wacc_breakdown.*` path handling in `applyOverrideLocally()`
>
> **Acceptance criteria:**
> 1. WACCBreakdown TypeScript interface exists
> 2. New WACCBreakdown component with 4 sub-sections (CAPM, Debt, Structure, Final)
> 3. Editable: risk_free_rate, raw_beta, erp, size_premium, cost_of_debt_pre_tax, effective_tax_rate, weight_equity, weight_debt
> 4. Computed: adjusted_beta, cost_of_equity, after_tax_cost_of_debt, final WACC — all update live
> 5. Read-only: interest_expense, total_debt, market_cap (compact dollar format)
> 6. Linked weights sum to 100%
> 7. Override paths: `wacc_breakdown.*` prefix
> 8. Override indicators on modified fields
> 9. Source notes on each field
> 10. Size tier label
> 11. Formula display for final WACC
> 12. Backward compatible (falls back to old 3-card if no wacc_breakdown)
> 13. No regressions on other Assumptions sections
>
> **Files to create:**
> - `frontend/src/pages/ModelBuilder/Assumptions/WACCBreakdown.tsx`
> - `frontend/src/pages/ModelBuilder/Assumptions/WACCBreakdown.module.css`
>
> **Files to modify:**
> - `frontend/src/types/models.ts`
> - `frontend/src/pages/ModelBuilder/Assumptions/AssumptionsTab.tsx`
>
> **Technical constraints:**
> - CSS modules for all styling
> - CSS variables from design system
> - Values stored as decimals (0.04 = 4%), displayed as percentages in inputs
> - useMemo for all computed values — no side effects, no backend calls for live recalc
> - Override paths: `wacc_breakdown.risk_free_rate`, `wacc_breakdown.raw_beta`, etc.
> - Blume constants: 2/3 and 1/3 (hardcoded, matching backend)
> - Inputs should use the same compact inline style as AssumptionCard (mono font, right-aligned, ~60px)
> - The "Regenerate" button (in parent) already sends overrides to backend — this component just needs to register overrides via `onOverride()`
