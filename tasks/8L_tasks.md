# Session 8L — Sensitivity Backend Updates (Step Precision, Range Params)
## Phase 8: Model Builder

**Priority:** Normal
**Type:** Backend Only
**Depends On:** None
**Spec Reference:** `specs/phase8_model_builder_sensitivity.md` → Areas 1C (step precision), 4B (range params)

---

## SCOPE SUMMARY

Update slider step sizes and display formats in `parameter_defs.py` for finer precision (WACC from 0.5% steps to 0.1%, etc.). Add optional `row_min`, `row_max`, `col_min`, `col_max` parameters to the `/sensitivity/table-2d` endpoint so the frontend can zoom into tighter ranges on data tables.

---

## TASKS

### Task 1: Update Slider Step Sizes & Display Formats
**Description:** Reduce step sizes for all 8 DCF sensitivity parameters to allow finer control. Update display formats to show the extra decimal where needed.

**Subtasks:**
- [ ] 1.1 — In `backend/services/sensitivity/parameter_defs.py`, update the `DCF_PARAMETERS` list with new step sizes and display formats. Current → New values:

  | Parameter | Current Step | New Step | Current Format | New Format |
  |-----------|-------------|----------|----------------|------------|
  | WACC | 0.005 (0.5%) | 0.001 (0.1%) | `"{:.1%}"` | `"{:.2%}"` |
  | Terminal Growth Rate | 0.0025 (0.25%) | 0.001 (0.1%) | `"{:.2%}"` | `"{:.2%}"` (unchanged) |
  | Revenue Growth Y1 | 0.01 (1%) | 0.005 (0.5%) | `"{:.1%}"` | `"{:.1%}"` (unchanged) |
  | Operating Margin Y1 | 0.01 (1%) | 0.005 (0.5%) | `"{:.1%}"` | `"{:.1%}"` (unchanged) |
  | CapEx / Revenue | 0.005 (0.5%) | 0.001 (0.1%) | `"{:.1%}"` | `"{:.2%}"` |
  | Tax Rate | 0.01 (1%) | 0.005 (0.5%) | `"{:.1%}"` | `"{:.1%}"` (unchanged) |
  | Exit Multiple | 0.5 | 0.1 | `"{:.1f}x"` | `"{:.1f}x"` (unchanged) |
  | NWC Change / Revenue | 0.005 (0.5%) | 0.001 (0.1%) | `"{:.1%}"` | `"{:.2%}"` |

  The updated `DCF_PARAMETERS` list:
  ```python
  DCF_PARAMETERS: list[SensitivityParameterDef] = [
      SensitivityParameterDef(
          name="WACC", key_path="scenarios.{s}.wacc",
          param_type="float_pct", min_val=0.04, max_val=0.20,
          step=0.001, display_format="{:.2%}",
      ),
      SensitivityParameterDef(
          name="Terminal Growth Rate", key_path="scenarios.{s}.terminal_growth_rate",
          param_type="float_pct", min_val=0.00, max_val=0.05,
          step=0.001, display_format="{:.2%}",
      ),
      SensitivityParameterDef(
          name="Revenue Growth Y1", key_path="scenarios.{s}.revenue_growth_rates[0]",
          param_type="float_pct", min_val=-0.10, max_val=0.60,
          step=0.005, display_format="{:.1%}",
      ),
      SensitivityParameterDef(
          name="Operating Margin Y1", key_path="scenarios.{s}.operating_margins[0]",
          param_type="float_pct", min_val=-0.20, max_val=0.60,
          step=0.005, display_format="{:.1%}",
      ),
      SensitivityParameterDef(
          name="CapEx / Revenue", key_path="model_assumptions.dcf.capex_to_revenue",
          param_type="float_ratio", min_val=0.01, max_val=0.25,
          step=0.001, display_format="{:.2%}",
      ),
      SensitivityParameterDef(
          name="Tax Rate", key_path="model_assumptions.dcf.tax_rate",
          param_type="float_pct", min_val=0.00, max_val=0.40,
          step=0.005, display_format="{:.1%}",
      ),
      SensitivityParameterDef(
          name="Exit Multiple (EV/EBITDA)", key_path="model_assumptions.dcf.terminal_exit_multiple",
          param_type="float_abs", min_val=4.0, max_val=30.0,
          step=0.1, display_format="{:.1f}x",
      ),
      SensitivityParameterDef(
          name="NWC Change / Revenue", key_path="model_assumptions.dcf.nwc_change_to_revenue",
          param_type="float_ratio", min_val=-0.05, max_val=0.10,
          step=0.001, display_format="{:.2%}",
      ),
  ]
  ```

**Implementation Notes:**
- The `SensitivityParameterDef` model (in `backend/services/sensitivity/models.py`) is a Pydantic model with fields: `name`, `key_path`, `param_type`, `min_val`, `max_val`, `step`, `display_format`, `current_value` (populated at runtime).
- The `get_dcf_parameter_defs()` function just returns the `DCF_PARAMETERS` list — no changes needed to it.
- The frontend reads these definitions via `GET /sensitivity/parameters` and uses `step` for the HTML range input's `step` attribute and `display_format` for value formatting. Smaller steps = more slider positions = finer control.

---

### Task 2: Add Range Parameters to Table-2D Endpoint
**Description:** Allow the frontend to specify custom min/max ranges for row and column variables in the 2D sensitivity table. This enables a "zoom" feature where the user can narrow the range (e.g., WACC 8%–12% instead of 4%–20%) for more granular view.

**Subtasks:**
- [ ] 2.1 — In `backend/routers/models_router.py`, add range fields to `Table2DRequest`:
  ```python
  class Table2DRequest(BaseModel):
      overrides: dict | None = None
      row_variable: str | None = None
      col_variable: str | None = None
      grid_size: int = 9
      row_min: float | None = None
      row_max: float | None = None
      col_min: float | None = None
      col_max: float | None = None
  ```

- [ ] 2.2 — In the `run_sensitivity_table_2d` endpoint (same file), pass the range params through to the service:
  ```python
  result = await svc.run_table_2d(
      assumptions, data, price,
      row_variable=body.row_variable,
      col_variable=body.col_variable,
      grid_size=body.grid_size,
      row_min=body.row_min,
      row_max=body.row_max,
      col_min=body.col_min,
      col_max=body.col_max,
  )
  ```

- [ ] 2.3 — In `backend/services/sensitivity/service.py`, update the `run_table_2d` method signature to accept and forward range params:
  ```python
  async def run_table_2d(
      self,
      assumption_set: AssumptionSet,
      data: dict,
      current_price: float,
      row_variable: str | None = None,
      col_variable: str | None = None,
      grid_size: int = 9,
      row_min: float | None = None,
      row_max: float | None = None,
      col_min: float | None = None,
      col_max: float | None = None,
  ) -> Table2DResult:
      return build_2d_table(
          assumption_set, data, current_price,
          row_key=row_variable,
          col_key=col_variable,
          n_steps=grid_size,
          row_min=row_min,
          row_max=row_max,
          col_min=col_min,
          col_max=col_max,
      )
  ```

- [ ] 2.4 — In `backend/services/sensitivity/tables_2d.py`, update `build_2d_table` to accept and use custom range params. Add `row_min`, `row_max`, `col_min`, `col_max` parameters:
  ```python
  def build_2d_table(
      assumption_set: AssumptionSet,
      data: dict,
      current_price: float,
      row_key: str | None = None,
      col_key: str | None = None,
      n_steps: int = TABLE_DEFAULT_STEPS,
      row_min: float | None = None,
      row_max: float | None = None,
      col_min: float | None = None,
      col_max: float | None = None,
  ) -> Table2DResult:
  ```
  After the existing `row_range = VARIABLE_RANGES.get(...)` lines, override with custom ranges if provided:
  ```python
  # Default ranges from VARIABLE_RANGES
  row_range = VARIABLE_RANGES.get(row_key, (row_base * 0.5, row_base * 1.5))
  col_range = VARIABLE_RANGES.get(col_key, (col_base * 0.5, col_base * 1.5))

  # Override with custom ranges if provided
  if row_min is not None and row_max is not None:
      row_range = (row_min, row_max)
  if col_min is not None and col_max is not None:
      col_range = (col_min, col_max)
  ```

- [ ] 2.5 — Add validation before the range override. If min ≥ max, raise a `ValueError`:
  ```python
  if row_min is not None and row_max is not None and row_min >= row_max:
      raise ValueError(f"row_min ({row_min}) must be less than row_max ({row_max})")
  if col_min is not None and col_max is not None and col_min >= col_max:
      raise ValueError(f"col_min ({col_min}) must be less than col_max ({col_max})")
  ```
  The existing `try/except` in the router endpoint will catch this and return `error_response("ENGINE_ERROR", str(exc))`.

**Implementation Notes:**
- The current `build_2d_table` function gets ranges from `VARIABLE_RANGES` dict. The custom params just override those tuple values.
- `build_centered_steps(base, range_min, range_max, n_steps)` already accepts min/max — no changes needed to that function.
- Default behavior is preserved: when `row_min`/`row_max` are `None`, the existing `VARIABLE_RANGES` lookup is used unchanged.
- The validation raises `ValueError` which the router's existing `except Exception` block catches and returns as an error response.

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: WACC slider step is 0.001 (0.1% increments) — allows values like 10.1%, 10.2%, etc.
- [ ] AC-2: Terminal Growth step is 0.001 (0.1% increments).
- [ ] AC-3: Revenue Growth Y1 and Operating Margin Y1 steps are 0.005 (0.5% increments).
- [ ] AC-4: CapEx/Revenue and NWC/Revenue steps are 0.001 (0.1% increments).
- [ ] AC-5: Tax Rate step is 0.005 (0.5% increments).
- [ ] AC-6: Exit Multiple step is 0.1 (allows 15.1x, 15.2x, etc.).
- [ ] AC-7: Display formats for WACC, CapEx/Revenue, NWC/Revenue show 2 decimal places (e.g., `11.20%` not `11.2%`).
- [ ] AC-8: `GET /sensitivity/parameters` returns updated step sizes and display formats.
- [ ] AC-9: `POST /sensitivity/table-2d` accepts optional `row_min`, `row_max`, `col_min`, `col_max` fields.
- [ ] AC-10: Custom ranges override `VARIABLE_RANGES` defaults in step generation.
- [ ] AC-11: When custom ranges not provided, default behavior is unchanged.
- [ ] AC-12: Invalid ranges (min ≥ max) return an error response.
- [ ] AC-13: The `build_centered_steps` function works correctly with custom ranges (no code changes needed to it, just verifying).

---

## FILES TOUCHED

**New files:**
- None

**Modified files:**
- `backend/services/sensitivity/parameter_defs.py` — update step sizes (8 params) and display formats (4 params)
- `backend/services/sensitivity/tables_2d.py` — add `row_min`, `row_max`, `col_min`, `col_max` params to `build_2d_table()`, override `VARIABLE_RANGES` when custom ranges provided, add validation
- `backend/services/sensitivity/service.py` — update `run_table_2d()` method signature to pass range params through to `build_2d_table()`
- `backend/routers/models_router.py` — add `row_min`, `row_max`, `col_min`, `col_max` fields to `Table2DRequest` Pydantic model, pass them to `svc.run_table_2d()`

---

## BUILDER PROMPT

> **Session 8L — Sensitivity Backend Updates (Step Precision + Range Params)**
>
> You are building session 8L of the Finance App v2.0 update.
>
> **What you're doing:** Two backend changes: (1) Update slider parameter step sizes for finer precision across all 8 DCF sensitivity parameters, (2) Add custom range parameters to the table-2d sensitivity endpoint for zoom control.
>
> **Context:** The slider parameters (WACC, Terminal Growth, etc.) currently have coarse steps (e.g., WACC at 0.5% increments, meaning you can only pick 11.0%, 11.5%, 12.0% — can't get 11.2%). The 2D sensitivity table always shows the full variable range (e.g., WACC 4%–20%). Frontend needs the ability to zoom in (e.g., 8%–12%) for more granular analysis.
>
> **Existing code:**
>
> `parameter_defs.py` (at `backend/services/sensitivity/parameter_defs.py`):
> - Defines `DCF_PARAMETERS: list[SensitivityParameterDef]` — 8 parameter definitions
> - Each `SensitivityParameterDef` has: `name`, `key_path`, `param_type`, `min_val`, `max_val`, `step`, `display_format`
> - Current values:
>   - WACC: step=0.005, format=`"{:.1%}"`
>   - Terminal Growth Rate: step=0.0025, format=`"{:.2%}"`
>   - Revenue Growth Y1: step=0.01, format=`"{:.1%}"`
>   - Operating Margin Y1: step=0.01, format=`"{:.1%}"`
>   - CapEx / Revenue: step=0.005, format=`"{:.1%}"`
>   - Tax Rate: step=0.01, format=`"{:.1%}"`
>   - Exit Multiple (EV/EBITDA): step=0.5, format=`"{:.1f}x"`
>   - NWC Change / Revenue: step=0.005, format=`"{:.1%}"`
> - `get_dcf_parameter_defs()` just returns `DCF_PARAMETERS`
>
> `tables_2d.py` (at `backend/services/sensitivity/tables_2d.py`):
> - `build_2d_table(assumption_set, data, current_price, row_key=None, col_key=None, n_steps=9)` — builds N×N grid of implied prices
> - Uses `VARIABLE_RANGES: dict[str, tuple[float, float]]` for per-variable min/max (e.g., WACC: (0.04, 0.20))
> - Gets ranges via: `row_range = VARIABLE_RANGES.get(row_key, (row_base * 0.5, row_base * 1.5))`
> - Calls `build_centered_steps(base, range_min, range_max, n_steps)` — generates evenly-spaced values centered on base within range
> - Currently does NOT accept custom min/max range parameters from the caller
> - Uses `_deep_clone_assumptions` and `_apply_override` from `sliders.py` for each grid cell
> - Enforces `terminal_growth_rate < wacc` constraint in each cell
>
> `service.py` (at `backend/services/sensitivity/service.py`):
> - `SensitivityService.run_table_2d(assumption_set, data, current_price, row_variable=None, col_variable=None, grid_size=9)`
> - Calls `build_2d_table()` with `row_key=row_variable, col_key=col_variable, n_steps=grid_size`
> - Currently does NOT pass range params
>
> `models_router.py` (at `backend/routers/models_router.py`):
> - `Table2DRequest(BaseModel)`: `overrides: dict | None`, `row_variable: str | None`, `col_variable: str | None`, `grid_size: int = 9`
> - Does NOT have `row_min`, `row_max`, `col_min`, `col_max`
> - Endpoint: `POST /{ticker}/sensitivity/table-2d` — calls `svc.run_table_2d(assumptions, data, price, row_variable=body.row_variable, col_variable=body.col_variable, grid_size=body.grid_size)`
> - Existing error handling: `try/except` catches `Exception` and returns `error_response("ENGINE_ERROR", str(exc))`
>
> **Cross-cutting rules:**
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%). The step values and ranges are all in decimal form.
>
> **Task 1: Update Step Sizes & Display Formats**
>
> In `parameter_defs.py`, update the `DCF_PARAMETERS` list:
> - WACC: step 0.005 → 0.001, format `"{:.1%}"` → `"{:.2%}"`
> - Terminal Growth Rate: step 0.0025 → 0.001 (format already `"{:.2%}"`)
> - Revenue Growth Y1: step 0.01 → 0.005 (format unchanged)
> - Operating Margin Y1: step 0.01 → 0.005 (format unchanged)
> - CapEx / Revenue: step 0.005 → 0.001, format `"{:.1%}"` → `"{:.2%}"`
> - Tax Rate: step 0.01 → 0.005 (format unchanged)
> - Exit Multiple: step 0.5 → 0.1 (format unchanged)
> - NWC Change / Revenue: step 0.005 → 0.001, format `"{:.1%}"` → `"{:.2%}"`
>
> **Task 2: Add Range Parameters to Table-2D**
>
> 1. In `models_router.py`, add 4 optional fields to `Table2DRequest`:
>    ```python
>    row_min: float | None = None
>    row_max: float | None = None
>    col_min: float | None = None
>    col_max: float | None = None
>    ```
>    Pass them through in the endpoint call to `svc.run_table_2d()`.
>
> 2. In `service.py`, update `run_table_2d()` signature to accept and forward `row_min`, `row_max`, `col_min`, `col_max`.
>
> 3. In `tables_2d.py`, update `build_2d_table()` signature to accept `row_min`, `row_max`, `col_min`, `col_max` (all `float | None = None`). After the existing `VARIABLE_RANGES.get(...)` lookups, override with custom values:
>    ```python
>    if row_min is not None and row_max is not None:
>        row_range = (row_min, row_max)
>    if col_min is not None and col_max is not None:
>        col_range = (col_min, col_max)
>    ```
>    Add validation before override: if `row_min >= row_max` or `col_min >= col_max`, raise `ValueError`. The router's existing `except Exception` block will catch it and return `error_response`.
>
> 4. Default behavior unchanged — when range params are `None`, `VARIABLE_RANGES` is used as before.
>
> **Acceptance criteria:**
> 1. WACC step is 0.001, Terminal Growth 0.001, Rev Growth/Op Margin 0.005, CapEx/NWC 0.001, Tax 0.005, Exit Multiple 0.1
> 2. Display formats show 2 decimals for WACC, CapEx, NWC (e.g., `11.20%`)
> 3. `GET /sensitivity/parameters` returns updated values
> 4. `POST /sensitivity/table-2d` accepts row_min/max, col_min/max
> 5. Custom ranges override defaults
> 6. Default behavior unchanged when params not provided
> 7. Invalid ranges return error
>
> **Files to create:** None
>
> **Files to modify:**
> - `backend/services/sensitivity/parameter_defs.py`
> - `backend/services/sensitivity/tables_2d.py`
> - `backend/services/sensitivity/service.py`
> - `backend/routers/models_router.py`
>
> **Technical constraints:**
> - Pydantic `BaseModel` for request validation (`Table2DRequest`)
> - All ratio/percentage values in decimal form (0.10 = 10%)
> - `build_centered_steps(base, range_min, range_max, n_steps)` — existing function, no changes needed
> - `_deep_clone_assumptions` and `_apply_override` from `sliders.py` — existing helpers, no changes needed
> - Error pattern: raise `ValueError` → caught by router's `except Exception` → `error_response("ENGINE_ERROR", str(exc))`
