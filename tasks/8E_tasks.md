# Session 8E — WACC Backend (Expose Components, Override Path)
## Phase 8: Model Builder

**Priority:** Normal
**Type:** Backend Only
**Depends On:** None
**Spec Reference:** `specs/phase8_model_builder_assumptions_wacc.md` → Areas 1, 3 (backend)

---

## SCOPE SUMMARY

Expose the full `WACCResult` breakdown in the `AssumptionSet` response so the frontend can render all WACC components. Add a `calculate_wacc_from_overrides()` function that recomputes WACC from user-provided component overrides (risk-free rate, beta, ERP, etc.) instead of running the full 8-step calculation. Update the pipeline to handle `wacc_breakdown.*` override paths.

---

## TASKS

### Task 1: Add wacc_breakdown Field to AssumptionSet
**Description:** Preserve the full WACCResult in the assumption response so the frontend has access to all intermediate WACC components.

**Subtasks:**
- [ ] 1.1 — In `backend/services/assumption_engine/models.py`, add a new field to `AssumptionSet`:
  ```python
  class AssumptionSet(BaseModel):
      # ... existing fields ...
      wacc_breakdown: WACCResult | None = None
  ```
- [ ] 1.2 — Import `WACCResult` in the models file if not already imported (it's defined in the same file, so no import needed — just add the field).

**Implementation Notes:**
- `WACCResult` is already defined in `models.py` with all the fields: `wacc`, `cost_of_equity`, `cost_of_debt_pre_tax`, `cost_of_debt_after_tax`, `risk_free_rate`, `adjusted_beta`, `raw_beta`, `erp`, `size_premium`, `effective_tax_rate`, `weight_equity`, `weight_debt`, `market_cap`, `total_debt`, `warnings`.
- Adding `wacc_breakdown: WACCResult | None = None` means existing consumers get `null` until the pipeline populates it.

---

### Task 2: Attach WACCResult to Pipeline Output
**Description:** In the pipeline's `generate_assumptions()` method, attach the computed `wacc_result` to the final `AssumptionSet`.

**Subtasks:**
- [ ] 2.1 — In `backend/services/assumption_engine/pipeline.py`, in the `generate_assumptions()` method, where the `AssumptionSet` is constructed (the `result = AssumptionSet(...)` block), add:
  ```python
  wacc_breakdown=wacc_result,
  ```
- [ ] 2.2 — The `wacc_result` variable is already computed earlier in the pipeline (`wacc_result = calculate_wacc(data)`). Just pass it through.

**Implementation Notes:**
- The pipeline currently computes `wacc_result` and uses it for scenario generation and model mappings, but discards it from the final output. This change simply includes it.
- The existing `result = AssumptionSet(...)` constructor call needs the new kwarg added.

---

### Task 3: Add calculate_wacc_from_overrides Function
**Description:** Add a function that computes WACC from user-provided component values instead of running the full data-driven calculation.

**Subtasks:**
- [ ] 3.1 — In `backend/services/assumption_engine/wacc.py`, add a new function:
  ```python
  def calculate_wacc_from_overrides(
      base_result: WACCResult,
      overrides: dict[str, float],
  ) -> WACCResult:
      """Recompute WACC from user-provided component overrides.
      
      Starts from base_result values, applies overrides, then
      recomputes all derived values (Blume beta, cost of equity,
      after-tax cost of debt, final WACC).
      
      Supported override keys:
          risk_free_rate, raw_beta, erp, size_premium,
          cost_of_debt_pre_tax, effective_tax_rate,
          weight_equity, weight_debt
      """
  ```
- [ ] 3.2 — Implementation logic:
  1. Start with all values from `base_result`
  2. Apply overrides: for each key in overrides, replace the corresponding value
  3. Recompute Blume adjusted beta: `adjusted_beta = (2/3 * raw_beta) + (1/3 * 1.0)`
  4. Recompute cost of equity: `cost_of_equity = risk_free_rate + (adjusted_beta * erp) + size_premium`
  5. Recompute after-tax cost of debt: `cost_of_debt_after_tax = cost_of_debt_pre_tax * (1 - effective_tax_rate)`
  6. If `weight_equity` is overridden but `weight_debt` is not: auto-adjust `weight_debt = 1 - weight_equity` (and vice versa)
  7. Recompute WACC: `wacc = (weight_equity * cost_of_equity) + (weight_debt * cost_of_debt_after_tax)`
  8. Clamp WACC to `[WACC_FLOOR, WACC_CEILING]`
  9. Return a new `WACCResult` with all updated values, plus a warning noting "Computed from user overrides"

**Implementation Notes:**
- Use the existing `BLUME_WEIGHT_RAW`, `BLUME_WEIGHT_MARKET`, `WACC_FLOOR`, `WACC_CEILING` constants from `constants.py`.
- The `clamp` helper from `helpers.py` is already available.
- This function is pure computation — no I/O.

---

### Task 4: Handle WACC Component Overrides in Pipeline
**Description:** When the pipeline receives overrides with `wacc_breakdown.*` paths, use `calculate_wacc_from_overrides` instead of the standard WACC calculation.

**Subtasks:**
- [ ] 4.1 — In `backend/services/assumption_engine/pipeline.py`, in `generate_assumptions()`, after computing `wacc_result = calculate_wacc(data)`:
  ```python
  # Check for WACC component overrides
  wacc_overrides = {
      k.replace("wacc_breakdown.", ""): v
      for k, v in overrides.items()
      if k.startswith("wacc_breakdown.")
  }
  if wacc_overrides:
      from .wacc import calculate_wacc_from_overrides
      wacc_result = calculate_wacc_from_overrides(wacc_result, wacc_overrides)
      logger.info("WACC recomputed from %d override(s)", len(wacc_overrides))
  ```
- [ ] 4.2 — After the WACC override recomputation, update the scenario generation to use the overridden WACC values. The `generate_scenarios()` function already receives `wacc_result` — ensure the overridden version is passed.
- [ ] 4.3 — Track WACC component overrides in `overrides_applied` list. Add each applied wacc override key to the list.
- [ ] 4.4 — Also update `_apply_overrides()` to skip `wacc_breakdown.*` keys (since they're handled earlier in the pipeline, not as scenario field overrides):
  ```python
  for key, value in overrides.items():
      if key.startswith("wacc_breakdown."):
          continue  # handled separately
      # ... existing scenario override logic ...
  ```

---

### Task 5: Ensure Override Path Support in Router
**Description:** Verify that the models router passes overrides through correctly for WACC paths.

**Subtasks:**
- [ ] 5.1 — In `backend/routers/models_router.py`, verify the `/generate` endpoint passes the `overrides` dict from the request body to `assumption_engine.generate_assumptions(ticker, overrides=overrides)`.
- [ ] 5.2 — Verify that the request body model (`GenerateRequest`) has `overrides: dict | None = None`. This already exists — just confirm.
- [ ] 5.3 — No changes likely needed — the router already passes overrides through. This task is verification only.

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: `AssumptionSet` model has `wacc_breakdown: WACCResult | None` field.
- [ ] AC-2: `GET /api/v1/model-builder/{ticker}/generate` response includes `wacc_breakdown` with all WACC components (risk_free_rate, raw_beta, adjusted_beta, erp, size_premium, cost_of_equity, cost_of_debt_pre_tax, cost_of_debt_after_tax, effective_tax_rate, weight_equity, weight_debt, market_cap, total_debt, warnings).
- [ ] AC-3: `wacc_breakdown` is populated for all tickers that have sufficient data (not null when data exists).
- [ ] AC-4: `calculate_wacc_from_overrides()` function exists in `wacc.py`.
- [ ] AC-5: Overrides for `wacc_breakdown.risk_free_rate`, `wacc_breakdown.raw_beta`, `wacc_breakdown.erp`, `wacc_breakdown.size_premium`, `wacc_breakdown.cost_of_debt_pre_tax`, `wacc_breakdown.effective_tax_rate`, `wacc_breakdown.weight_equity`, `wacc_breakdown.weight_debt` are all handled.
- [ ] AC-6: Blume adjusted beta is recomputed when `raw_beta` is overridden: `(2/3 * raw_beta) + (1/3 * 1.0)`.
- [ ] AC-7: Cost of equity is recomputed: `Rf + adjusted_beta * ERP + size_premium`.
- [ ] AC-8: After-tax cost of debt is recomputed: `Kd_pre * (1 - tax_rate)`.
- [ ] AC-9: When `weight_equity` is overridden, `weight_debt` auto-adjusts to `1 - weight_equity` (and vice versa).
- [ ] AC-10: Final WACC is clamped to `[WACC_FLOOR, WACC_CEILING]`.
- [ ] AC-11: WACC component overrides are applied before scenario generation (so scenarios use the overridden WACC).
- [ ] AC-12: `wacc_breakdown.*` keys are skipped in `_apply_overrides()` (no double-processing).
- [ ] AC-13: WACC component override keys tracked in `overrides_applied` list.
- [ ] AC-14: Existing WACC calculation still works when no overrides are present (backward compatible).
- [ ] AC-15: Existing scenario overrides (`scenarios.base.revenue_growth_rates`, etc.) still work.

---

## FILES TOUCHED

**New files:**
- None

**Modified files:**
- `backend/services/assumption_engine/models.py` — add `wacc_breakdown: WACCResult | None` to `AssumptionSet`
- `backend/services/assumption_engine/pipeline.py` — attach `wacc_result` to output, handle `wacc_breakdown.*` overrides, skip in `_apply_overrides()`
- `backend/services/assumption_engine/wacc.py` — add `calculate_wacc_from_overrides()` function

---

## BUILDER PROMPT

> **Session 8E — WACC Backend (Expose Components, Override Path)**
>
> You are building session 8E of the Finance App v2.0 update.
>
> **What you're doing:** Exposing the full WACC component breakdown in the AssumptionSet API response and adding a component-level override path so the frontend can edit individual WACC inputs (risk-free rate, beta, ERP, etc.) and have the backend recompute WACC from those components.
>
> **Context:** The assumption engine already computes a detailed `WACCResult` with all 8 CAPM/WACC components during `generate_assumptions()`. But the result is only used internally — the final `AssumptionSet` response only includes the top-level `wacc` and `cost_of_equity` values in scenario projections. The frontend needs all components for an interactive WACC breakdown UI.
>
> **Existing code:**
>
> `models.py` (`backend/services/assumption_engine/models.py`):
> - `WACCResult(BaseModel)` — already defined with: `wacc, cost_of_equity, cost_of_debt_pre_tax, cost_of_debt_after_tax, risk_free_rate, adjusted_beta, raw_beta, erp, size_premium, effective_tax_rate, weight_equity, weight_debt, market_cap, total_debt, warnings`
> - `AssumptionSet(BaseModel)` — final output, currently has: `ticker, generated_at, data_quality_score, years_of_data, overrides_applied, scenarios, model_assumptions, confidence, reasoning, metadata`. Missing: `wacc_breakdown`.
>
> `wacc.py` (`backend/services/assumption_engine/wacc.py`):
> - `calculate_wacc(data: CompanyDataPackage) -> WACCResult` — full 8-step calculation using company data
> - Uses constants: `BLUME_WEIGHT_RAW` (2/3), `BLUME_WEIGHT_MARKET` (1/3), `DEFAULT_BETA`, `DEFAULT_ERP`, `DEFAULT_RISK_FREE_RATE`, `DEFAULT_TAX_RATE`, `SIZE_PREMIUM_*`, `WACC_FLOOR`, `WACC_CEILING`
> - Uses helpers: `clamp()`, `safe_div()`
>
> `pipeline.py` (`backend/services/assumption_engine/pipeline.py`):
> - `generate_assumptions(ticker, model_type, overrides)` — main entry point
> - Calls `wacc_result = calculate_wacc(data)` in the ANALYZE stage
> - Passes `wacc_result` to `generate_scenarios()` and `map_all_models()`
> - Constructs `result = AssumptionSet(...)` at the end — currently doesn't include `wacc_result`
> - `_apply_overrides(scenarios, overrides)` — applies `scenarios.base.field` style overrides
>
> `models_router.py`:
> - `POST /{ticker}/generate` — calls `assumption_engine.generate_assumptions(ticker, overrides=body.overrides)`
> - `GenerateRequest(BaseModel)` has `model_type: str | None`, `overrides: dict | None`
>
> **Cross-cutting rules:**
> - Display Name Rule: All backend snake_case keys displayed in the UI must use the shared `displayNames.ts` utility.
> - Chart Quality: All charts must meet Fidelity/Yahoo Finance information-density standards.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%).
> - Scenario Order: Bear / Base / Bull (left to right), Base default.
>
> **Task 1: Add wacc_breakdown to AssumptionSet**
>
> In `backend/services/assumption_engine/models.py`, add to `AssumptionSet`:
> ```python
> wacc_breakdown: WACCResult | None = None
> ```
> `WACCResult` is already defined in the same file. No import needed.
>
> **Task 2: Attach WACCResult to Pipeline Output**
>
> In `backend/services/assumption_engine/pipeline.py`, in `generate_assumptions()`, find the `result = AssumptionSet(...)` constructor call and add:
> ```python
> wacc_breakdown=wacc_result,
> ```
> The `wacc_result` variable is already computed earlier: `wacc_result = calculate_wacc(data)`.
>
> **Task 3: Add calculate_wacc_from_overrides**
>
> In `backend/services/assumption_engine/wacc.py`, add:
> ```python
> def calculate_wacc_from_overrides(
>     base_result: WACCResult,
>     overrides: dict[str, float],
> ) -> WACCResult:
>     """Recompute WACC from user-provided component overrides."""
>     # Start from base values
>     rf = overrides.get("risk_free_rate", base_result.risk_free_rate)
>     raw_beta = overrides.get("raw_beta", base_result.raw_beta)
>     erp = overrides.get("erp", base_result.erp)
>     sp = overrides.get("size_premium", base_result.size_premium)
>     kd_pre = overrides.get("cost_of_debt_pre_tax", base_result.cost_of_debt_pre_tax)
>     tax = overrides.get("effective_tax_rate", base_result.effective_tax_rate)
>
>     # Weights (linked — one adjusts the other)
>     if "weight_equity" in overrides and "weight_debt" not in overrides:
>         we = overrides["weight_equity"]
>         wd = 1.0 - we
>     elif "weight_debt" in overrides and "weight_equity" not in overrides:
>         wd = overrides["weight_debt"]
>         we = 1.0 - wd
>     elif "weight_equity" in overrides and "weight_debt" in overrides:
>         we = overrides["weight_equity"]
>         wd = overrides["weight_debt"]
>     else:
>         we = base_result.weight_equity
>         wd = base_result.weight_debt
>
>     # Recompute derived values
>     adjusted_beta = BLUME_WEIGHT_RAW * raw_beta + BLUME_WEIGHT_MARKET * 1.0
>     adjusted_beta = min(adjusted_beta, 2.5)
>     cost_of_equity = rf + (adjusted_beta * erp) + sp
>     kd_after = kd_pre * (1 - tax)
>
>     if wd == 0:
>         wacc = cost_of_equity
>     else:
>         wacc = (we * cost_of_equity) + (wd * kd_after)
>     wacc = clamp(wacc, WACC_FLOOR, WACC_CEILING)
>
>     warnings = list(base_result.warnings) + ["Computed from user overrides"]
>
>     return WACCResult(
>         wacc=round(wacc, 4),
>         cost_of_equity=round(cost_of_equity, 4),
>         cost_of_debt_pre_tax=round(kd_pre, 4),
>         cost_of_debt_after_tax=round(kd_after, 4),
>         risk_free_rate=round(rf, 4),
>         adjusted_beta=round(adjusted_beta, 4),
>         raw_beta=round(raw_beta, 4),
>         erp=erp,
>         size_premium=sp,
>         effective_tax_rate=round(tax, 4),
>         weight_equity=round(we, 4),
>         weight_debt=round(wd, 4),
>         market_cap=base_result.market_cap,
>         total_debt=base_result.total_debt,
>         warnings=warnings,
>     )
> ```
>
> **Task 4: Handle WACC Overrides in Pipeline**
>
> In `pipeline.py`, in `generate_assumptions()`, after `wacc_result = calculate_wacc(data)`:
> ```python
> # Check for WACC component overrides
> wacc_overrides = {
>     k.replace("wacc_breakdown.", ""): v
>     for k, v in overrides.items()
>     if k.startswith("wacc_breakdown.")
> }
> if wacc_overrides:
>     from .wacc import calculate_wacc_from_overrides
>     wacc_result = calculate_wacc_from_overrides(wacc_result, wacc_overrides)
>     logger.info("WACC recomputed from %d override(s)", len(wacc_overrides))
>     warnings.append(f"WACC computed from {len(wacc_overrides)} user override(s)")
> ```
>
> In `_apply_overrides()`, add at the top of the for loop:
> ```python
> if key.startswith("wacc_breakdown."):
>     continue  # handled in pipeline before scenario generation
> ```
>
> Track WACC overrides in the applied list: add the full `wacc_breakdown.*` keys to `overrides_applied`.
>
> **Task 5: Verify Router (No Changes Expected)**
>
> Confirm that `POST /{ticker}/generate` passes `overrides` from request body to engine. `GenerateRequest.overrides: dict | None` already exists. No changes needed.
>
> **Acceptance criteria:**
> 1. `AssumptionSet` has `wacc_breakdown: WACCResult | None`
> 2. `/generate` response includes full WACC breakdown with all components
> 3. `calculate_wacc_from_overrides()` exists and works
> 4. Overrides for all 8 WACC component keys are handled
> 5. Blume beta recomputed on raw_beta override
> 6. Cost of equity recomputed from components
> 7. Linked weights: override one → auto-adjust the other
> 8. WACC clamped to floor/ceiling
> 9. Overridden WACC flows through to scenario generation
> 10. `wacc_breakdown.*` keys skipped in `_apply_overrides()`
> 11. Backward compatible: no overrides → standard WACC calculation
>
> **Files to create:** None
>
> **Files to modify:**
> - `backend/services/assumption_engine/models.py`
> - `backend/services/assumption_engine/pipeline.py`
> - `backend/services/assumption_engine/wacc.py`
>
> **Technical constraints:**
> - Python 3.12, Pydantic v2
> - Pure computation in `calculate_wacc_from_overrides` — no I/O
> - Use existing constants from `constants.py` (BLUME_WEIGHT_RAW, BLUME_WEIGHT_MARKET, WACC_FLOOR, WACC_CEILING)
> - Use existing `clamp()` from `helpers.py`
> - All ratios as decimals (0.10 = 10%)
> - WACCResult values rounded to 4 decimal places
