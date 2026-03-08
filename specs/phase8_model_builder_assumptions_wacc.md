# Finance App — Model Builder: WACC Detailed Buildout Plan
## Phase 8: Model Builder — Assumptions (WACC)

**Prepared by:** Planner (March 5, 2026)
**Recipient:** PM Agent
**Scope:** Full WACC component breakdown in the Assumptions tab — editable inputs, live frontend recalculation, CAPM visualization

---

## PLAN SUMMARY

The current WACC section shows two editable fields (WACC, Cost of Equity) and Tax Rate. The backend already computes all WACC components via an 8-step process (risk-free rate, beta, Blume adjustment, size premium, CAPM cost of equity, cost of debt, capital weights, final WACC). But none of these intermediate values are exposed to the frontend.

This plan:
1. Surfaces all WACC components from backend to frontend
2. Replaces the current 3-field WACC section with a detailed, interactive component breakdown
3. Makes each input editable, with WACC recomputing live in the browser
4. The final WACC becomes a computed output, not a directly editable number

---

## AREA 1: BACKEND — EXPOSE WACC COMPONENTS

### Current State
The `WACCResult` model already contains all components:
```python
class WACCResult(BaseModel):
    wacc: float
    cost_of_equity: float
    cost_of_debt_pre_tax: float
    cost_of_debt_after_tax: float
    risk_free_rate: float
    adjusted_beta: float
    raw_beta: float
    erp: float                    # Equity Risk Premium
    size_premium: float
    effective_tax_rate: float
    weight_equity: float
    weight_debt: float
    market_cap: float | None
    total_debt: float | None
    warnings: list[str]
```

But the `AssumptionSet` response only passes through the final `wacc` and `cost_of_equity` values into the scenario projections. The full `WACCResult` is computed during `generate_assumptions()` but discarded.

### Changes
- Preserve the full `WACCResult` in the `AssumptionSet` response
- Add a new field to `AssumptionSet`: `wacc_breakdown: WACCResult | None`
- In the assumption engine pipeline, after calling `calculate_wacc()`, attach the result to the output
- Frontend TypeScript types updated to include `WACCBreakdown` interface

**Files touched:**
- `backend/services/assumption_engine/models.py` — add `wacc_breakdown` field to `AssumptionSet`
- `backend/services/assumption_engine/pipeline.py` — attach `WACCResult` to output
- `frontend/src/types/models.ts` — add `WACCBreakdown` interface matching `WACCResult`

---

## AREA 2: FRONTEND — WACC SECTION REDESIGN

### Current Layout
```
WACC & COST OF CAPITAL                    [confidence badge]
  WACC .................. [  10.2  ] %    [72]  (i)
  Cost of Equity ........ [  12.5  ] %    [72]  (i)
  Tax Rate .............. [  21.0  ] %         (i)
```

### New Layout
```
WACC & COST OF CAPITAL                              [confidence badge]
  Computed WACC: 10.2%                               [Reasoning tooltip]

  ── Cost of Equity (CAPM) ──────────────────────────────────────
  Risk-Free Rate ............ [  4.0   ] %    Current 10Y Treasury
  Equity Risk Premium ....... [  5.5   ] %    Market consensus
  Raw Beta .................. [  1.15  ]      From Yahoo Finance
  Blume Adjusted Beta ....... [  1.10  ]      (2/3 × raw + 1/3 × 1.0)
  Size Premium .............. [  0.5   ] %    Large cap ($10B-$200B)
  ─────────────────────────────────────────
  → Cost of Equity:           12.55%          Rf + β(ERP) + SP

  ── Cost of Debt ───────────────────────────────────────────────
  Interest Expense .......... $1.2B           From financials
  Total Debt ................ $15.3B          From balance sheet
  Pre-Tax Cost of Debt ...... [  7.8   ] %    Interest / Debt
  Effective Tax Rate ........ [  21.0  ] %    From tax provision
  ─────────────────────────────────────────
  → After-Tax Cost of Debt:   6.16%          Kd × (1 - t)

  ── Capital Structure ──────────────────────────────────────────
  Market Cap ................  $245.0B        From market data
  Total Debt ................  $15.3B         From balance sheet
  ─────────────────────────────────────────
  Equity Weight (E/V) ....... [  94.1  ] %
  Debt Weight (D/V) ......... [   5.9  ] %

  ── Final WACC ─────────────────────────────────────────────────
  ═══════════════════════════════════════
  WACC = (94.1% × 12.55%) + (5.9% × 6.16%) = 12.17%
  ═══════════════════════════════════════

  [Warnings if any]
```

### Behavior

**Editable fields** (user can change these):
- Risk-Free Rate
- Equity Risk Premium
- Raw Beta (Blume adjustment auto-recomputes)
- Size Premium
- Pre-Tax Cost of Debt
- Effective Tax Rate
- Equity Weight / Debt Weight (linked — changing one auto-adjusts the other to sum to 100%)

**Computed fields** (auto-update when inputs change):
- Blume Adjusted Beta = `(2/3 × raw_beta) + (1/3 × 1.0)`
- Cost of Equity = `Rf + adjusted_beta × ERP + size_premium`
- After-Tax Cost of Debt = `pre_tax_cost_of_debt × (1 - tax_rate)`
- Final WACC = `(weight_equity × cost_of_equity) + (weight_debt × after_tax_cost_of_debt)`

**Read-only display fields** (informational, from backend data):
- Interest Expense (from financials)
- Total Debt (from balance sheet)
- Market Cap (from market data)

**Live recalculation:**
- All computed fields update instantly in the browser as the user types
- The WACC formula is simple arithmetic — no backend round-trip needed
- Uses React state: editable inputs stored as local state, computed values derived via `useMemo`
- The "Regenerate" button in the header sends the user's final input values to the backend to rerun the full model

**Override tracking:**
- Each editable field uses the existing override system (blue left border + "Manual" badge when changed from engine defaults)
- When the user changes an input, the computed WACC auto-updates AND the override is registered for the downstream model run

### Component Structure
- Replace the current WACC section in `AssumptionsTab.tsx` with a new `WACCBreakdown` component
- The component receives the `WACCResult` data as props
- Internally manages editable state with `useState` for each input
- Computes derived values with `useMemo` chains
- Calls `handleOverride()` on the parent when inputs change (same pattern as existing AssumptionCards)

**Files touched:**
- `frontend/src/pages/ModelBuilder/Assumptions/WACCBreakdown.tsx` — new file
- `frontend/src/pages/ModelBuilder/Assumptions/WACCBreakdown.module.css` — new file
- `frontend/src/pages/ModelBuilder/Assumptions/AssumptionsTab.tsx` — replace WACC section with new component
- `frontend/src/types/models.ts` — add WACCBreakdown interface (if not already added in backend changes)

---

## AREA 3: WACC OVERRIDE PATH TO ENGINE

### Problem
Currently, when overrides are applied, they target paths like `scenarios.base.wacc`. But with the new component, the user is editing individual inputs (risk_free_rate, beta, erp, etc.) and the WACC is computed from those.

### Solution
- The override map needs to support WACC component paths:
  - `wacc_breakdown.risk_free_rate`
  - `wacc_breakdown.raw_beta`
  - `wacc_breakdown.erp`
  - `wacc_breakdown.size_premium`
  - `wacc_breakdown.cost_of_debt_pre_tax`
  - `wacc_breakdown.effective_tax_rate`
  - `wacc_breakdown.weight_equity`
  - `wacc_breakdown.weight_debt`
- When "Regenerate" is clicked, the backend receives these component overrides
- The backend's assumption engine pipeline needs to accept WACC component overrides and recompute WACC from them (instead of running the full WACC calculation from scratch)
- If no WACC overrides are present, the engine runs its normal 8-step process

**Backend changes:**
- Add an `overrides` parameter to the `/generate` endpoint that can include `wacc_component` overrides
- In the pipeline, if WACC component overrides exist, skip the normal WACC calculation and compute directly from the provided components
- Apply the same Blume adjustment, CAPM formula, and weighted average using the overridden values

**Files touched:**
- `backend/services/assumption_engine/pipeline.py` — handle WACC component overrides
- `backend/services/assumption_engine/wacc.py` — add `calculate_wacc_from_overrides()` function
- `backend/routers/models_router.py` — ensure override path supports wacc_breakdown fields
- `frontend/src/pages/ModelBuilder/Assumptions/AssumptionsTab.tsx` — update `applyOverrideLocally()` to handle wacc_breakdown paths

---

## SESSION ORGANIZATION (Recommended for PM)

### Session 8E — WACC Backend (Backend Only)
**Scope:** Area 1, Area 3 backend
**Files:**
- `backend/services/assumption_engine/models.py` — add wacc_breakdown field
- `backend/services/assumption_engine/pipeline.py` — attach WACCResult, handle component overrides
- `backend/services/assumption_engine/wacc.py` — add override recalculation function
- `backend/routers/models_router.py` — support wacc component override paths
**Complexity:** Medium (WACCResult already exists, mainly wiring and override logic)
**Estimated acceptance criteria:** 10–12

### Session 8F — WACC Frontend (Frontend Only)
**Scope:** Area 2, Area 3 frontend
**Files:**
- `WACCBreakdown.tsx` — new component (full interactive WACC section)
- `WACCBreakdown.module.css` — new styles
- `AssumptionsTab.tsx` — swap WACC section for new component
- `types/models.ts` — WACCBreakdown TypeScript interface
**Complexity:** Medium-High (live recalculation, linked weight inputs, override tracking, new layout)
**Estimated acceptance criteria:** 18–22
**Depends on:** Session 8E (backend must expose WACCResult in assumptions response)

---

## DEPENDENCIES & RISKS

| Risk | Mitigation |
|------|------------|
| Linked weight inputs (equity + debt must sum to 100%) cause UX confusion | Show both as editable but auto-adjust the other. Add a small note: "Equity and debt weights must sum to 100%" |
| Blume adjustment confuses users unfamiliar with it | Show the formula inline: "(2/3 × raw + 1/3 × 1.0)" as a small note below adjusted beta |
| Frontend WACC calculation diverges from backend | Use identical arithmetic. The formula is trivial. Add a unit test or assertion that frontend and backend produce the same result for the same inputs |
| Override path collision with existing scenario overrides | Use distinct prefix `wacc_breakdown.*` that doesn't conflict with `scenarios.*` paths |
| Size premium tiers not obvious to user | Show the tier label next to the value: "Large cap ($10B–$200B)" |

---

## DECISIONS MADE

1. WACC becomes a computed output, not a directly editable field
2. All WACC component inputs are editable with live browser-side recalculation
3. No backend round-trip for live WACC updates — arithmetic only
4. "Regenerate" button sends component overrides to backend for full model rerun
5. Backend already has full WACCResult — just needs to be surfaced in the response
6. Equity/Debt weights are linked (auto-adjust to sum to 100%)
7. Read-only informational fields (interest expense, total debt, market cap) shown for context
8. Override tracking uses `wacc_breakdown.*` path prefix
9. Backend adds `calculate_wacc_from_overrides()` for when user has changed components

---

*End of Model Builder — WACC Detailed Buildout Plan*
*Phase 8E–8F · Prepared March 5, 2026*
