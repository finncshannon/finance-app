# PM2 Startup Prompt — Finish Phase 8 (Sessions 8K–8O) + Continue Phases 9–14

## YOUR ROLE

You are **PM2**, continuing the Finance App v2.0 PM workflow. PM1 completed sessions 7A–8J at full production quality but ran out of context before finishing Phase 8. Your first job is to **rewrite sessions 8K–8O to full quality** using the context provided below. After that, continue producing new task files for Phases 9–14.

Follow the same process and template as PM1. Read `tasks/8F_tasks.md` or `tasks/8I_tasks.md` as your quality reference. Those files have the gold standard: full "Existing code" sections with actual source references, inline code examples in the Builder prompt, and complete technical constraints. The 8K–8O files currently have correct tasks and acceptance criteria but their Builder prompts are skeletal.

Read `specs/MASTER_INDEX.md` and `specs/cross_cutting_underscore_cleanup.md` before starting, then follow the PM1 startup prompt workflow at `PM1_STARTUP_PROMPT.md` (uploaded to this conversation) for the full template and rules.

---

## PHASE 8 INCOMPLETE SESSIONS — SOURCE CODE CONTEXT

Below is the actual source code PM2 needs to write complete Builder prompts for 8K–8O. This saves PM2 from having to re-read every file.

---

### SESSION 8K — DCF Key Outputs & Waterfall Chart Upgrade

**Spec:** `specs/phase8_model_builder_model.md` → Area 6
**Current task file:** `tasks/8K_tasks.md` — tasks/AC are correct, Builder prompt needs "Existing code" + inline examples

**Source: `frontend/src/pages/ModelBuilder/Models/DCFView.tsx`**

Current component structure:
- Props: `{ result: DCFResult }`
- State: `activeScenario` (ScenarioKey), computed `availableScenarios`, `scenario`, `projectionTable`, `waterfallData`, `secondaryValues`
- Renders: ResultsCard → Scenario Tabs → Projection Table → **Key Outputs Panel** (section d) → **Waterfall Chart** (section e)
- Key Outputs is currently a flat `.keyOutputsGrid` with 6 `.keyOutputItem` divs (PV of FCFs, PV Terminal, EV, TV%, Equity Value, Implied Price)
- Waterfall uses Recharts `BarChart` with `Cell` per bar colored by `STEP_COLORS` map (start=#3B82F6, addition=#22C55E, subtraction=#EF4444). `XAxis` dataKey="label", angle=-30. `YAxis` tickFormatter uses `fmtDollar`. Basic `Tooltip` with no running total.
- Formatters imported from `./formatters`: `fmtDollar`, `fmtPct`, `fmtFactor`, `fmtPrice`
- `DCFScenarioResult` has: `enterprise_value`, `pv_fcf_total`, `pv_terminal_value`, `tv_pct_of_ev`, `equity_value`, `implied_price`, `upside_downside_pct`, `wacc`, `terminal_growth_rate`, `terminal_exit_multiple`
- `DCFWaterfall.steps[]` has: `{label: string, value: number, step_type: "start"|"addition"|"subtraction"|"subtotal"|"end"}`
- Missing from current key outputs: net debt, shares outstanding (these are in DCFResult but not displayed — check metadata or look in the scenario data)
- Recharts imports already present: `BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell`. Will need to add `LabelList, ReferenceLine` for the upgrade.

**CSS: `DCFView.module.css`** has: `.keyOutputsPanel`, `.keyOutputsGrid` (CSS grid), `.keyOutputItem`, `.keyOutputLabel`, `.keyOutputValue`, `.waterfallSection`, `.waterfallTitle`, `.sectionTitle`, `.container`, `.scenarioTabs`, `.scenarioBtn`, `.scenarioBtnActive`, `.tableSection`, `.tableWrapper`, `.projectionTable`

---

### SESSION 8L — Sensitivity Backend Updates

**Spec:** `specs/phase8_model_builder_sensitivity.md` → Areas 1C, 4B
**Current task file:** `tasks/8L_tasks.md` — tasks/AC correct, Builder prompt needs existing code

**Source: `backend/services/sensitivity/parameter_defs.py`**

Current parameter definitions (exact current values):
```python
DCF_PARAMETERS = [
    SensitivityParameterDef(name="WACC", key_path="scenarios.{s}.wacc", param_type="float_pct", min_val=0.04, max_val=0.20, step=0.005, display_format="{:.1%}"),
    SensitivityParameterDef(name="Terminal Growth Rate", key_path="scenarios.{s}.terminal_growth_rate", param_type="float_pct", min_val=0.00, max_val=0.05, step=0.0025, display_format="{:.2%}"),
    SensitivityParameterDef(name="Revenue Growth Y1", key_path="scenarios.{s}.revenue_growth_rates[0]", param_type="float_pct", min_val=-0.10, max_val=0.60, step=0.01, display_format="{:.1%}"),
    SensitivityParameterDef(name="Operating Margin Y1", key_path="scenarios.{s}.operating_margins[0]", param_type="float_pct", min_val=-0.20, max_val=0.60, step=0.01, display_format="{:.1%}"),
    SensitivityParameterDef(name="CapEx / Revenue", key_path="model_assumptions.dcf.capex_to_revenue", param_type="float_ratio", min_val=0.01, max_val=0.25, step=0.005, display_format="{:.1%}"),
    SensitivityParameterDef(name="Tax Rate", key_path="model_assumptions.dcf.tax_rate", param_type="float_pct", min_val=0.00, max_val=0.40, step=0.01, display_format="{:.1%}"),
    SensitivityParameterDef(name="Exit Multiple (EV/EBITDA)", key_path="model_assumptions.dcf.terminal_exit_multiple", param_type="float_abs", min_val=4.0, max_val=30.0, step=0.5, display_format="{:.1f}x"),
    SensitivityParameterDef(name="NWC Change / Revenue", key_path="model_assumptions.dcf.nwc_change_to_revenue", param_type="float_ratio", min_val=-0.05, max_val=0.10, step=0.005, display_format="{:.1%}"),
]
```

**Source: `backend/services/sensitivity/tables_2d.py`**

Key constants and structures:
- `VARIABLE_RANGES: dict[str, tuple[float, float]]` — maps key_path to (min, max) for each of 8 variables
- `VARIABLE_NAMES: dict[str, str]` — maps key_path to display name
- `DEFAULT_PAIRS` — 3 tuples of (row_key_path, col_key_path)
- `build_centered_steps(center, range_min, range_max, n_steps)` — generates evenly-spaced values around center
- `run_table_2d(assumptions, data, current_price, row_variable, col_variable, grid_size)` — currently does NOT accept custom min/max range params
- Uses `_deep_clone_assumptions` and `_apply_override` from `sliders.py`

**Source: `backend/routers/models_router.py`** — `Table2DRequest` currently has: `overrides: dict | None`, `row_variable: str | None`, `col_variable: str | None`, `grid_size: int = 9`. Does NOT have `row_min/max`, `col_min/max`.

---

### SESSION 8M — Sliders + State Persistence + Assumptions Sync

**Spec:** `specs/phase8_model_builder_sensitivity.md` → Areas 1A–1F, 5A, 5B
**Current task file:** `tasks/8M_tasks.md` — tasks/AC correct, Builder prompt needs existing code

**Source: `frontend/src/pages/ModelBuilder/Sensitivity/SlidersPanel.tsx`**

Current component structure:
- Reads `activeTicker` from modelStore
- Local state: `params` (SensitivityParameterDef[]), `overrides` (Record<string, number>), `result` (SliderResult | null), `loading`, `error`, `computing`
- On mount: fetches parameter defs from `GET /sensitivity/parameters`, seeds `overrides` with `current_value` per param
- On slider change: debounced (300ms) POST to `/sensitivity/slider` with current overrides
- Renders: result banner (implied price, delta, compute time) → constraints → slider list
- Each slider row: label, HTML `<input type="range">`, min/max labels, current value display
- `formatParamValue(value, format)` handles pct/currency/multiple/integer formatting
- Currently all state is local — resets when switching tabs
- No current-assumption marker on tracks
- No direct number input — only slider drag

**Source: `frontend/src/stores/modelStore.ts`** (after 8D session adds):
- Will have: `pendingSliderOverrides: Record<string, number>`, `sensitivityParams: Record<string, unknown> | null`
- Will have: `pushSliderToAssumptions()`, `pullAssumptionsToSliders()`, `clearSliderOverrides()`, `setSensitivityParams()`
- 8M needs to add: `sliderOverrides: Record<string, number>`, `sliderResult: SliderResult | null`, `setSliderOverride(key, value)`, `setSliderResult(result)`

**Key UX patterns from spec:**
- Current assumption marker: white 2px vertical line at `((current_value - min) / (max - min)) * 100%` on the track
- Direct number input: small inline `<input type="number">` next to each slider, displays formatted value, converts to/from raw decimal
- State persistence: read from / write to modelStore instead of local state
- Push to Assumptions: button that calls `modelStore.pushSliderToAssumptions()` which merges `sliderOverrides` → `assumptions`
- Pull from Model: button that resets sliders to match current assumption values

---

### SESSION 8N — Tornado + Monte Carlo + Data Tables Frontend Upgrade

**Spec:** `specs/phase8_model_builder_sensitivity.md` → Areas 2, 3, 4
**Current task file:** `tasks/8N_tasks.md` — tasks/AC correct, Builder prompt needs existing code

**Source: `frontend/src/pages/ModelBuilder/Sensitivity/TornadoChart.tsx`**

Current component structure:
- Fetches from `POST /sensitivity/tornado` on mount
- Transforms `TornadoResult.bars[]` into `TornadoChartDatum[]` with `lowSpread`, `highSpread` (deviations from base)
- Renders: header (title + base price + current price + compute time) → legend (Downside/Upside) → Recharts `BarChart` layout="vertical"
- Chart: `XAxis` type="number" (dollar delta), `YAxis` type="category" dataKey="name" width=140, `ReferenceLine` at x=0
- Two stacked `<Bar>` components: lowSpread (red) and highSpread (green) with `Cell` coloring
- Tooltip: basic, shows $value for each side
- **Missing:** value labels on bar endpoints, input range annotations, spread labels, rank numbers, gradient bars, summary bar

**Source: `frontend/src/pages/ModelBuilder/Sensitivity/MonteCarloPanel.tsx`**

Current component structure:
- State: `iterations` (default 10000), `data` (MonteCarloResult), `loading`, `error`
- Fetches from `POST /sensitivity/monte-carlo` with `{iterations}`
- Renders: header with iteration selector dropdown + Run button → histogram (Recharts BarChart) → stats panel
- Histogram: `BarChart` with bins, colored cells (green for bins around mean, red for tails), `ReferenceLine` for current price
- Stats panel: flat grid showing mean, median, std_dev, p5/p10/p25/p50/p75/p90/p95, prob_above_current, prob_above_10pct, etc.
- **Missing:** "Use slider assumptions" toggle, parameter display section, gradient bar fill, median line, IQR shading, reorganized stats

**Source: `frontend/src/pages/ModelBuilder/Sensitivity/DataTablePanel.tsx`**

Current component structure:
- Fetches from `POST /sensitivity/table-2d` with `{grid_size: 9}` on mount
- Renders: header (title + base price + current + grid size + compute time) → variable labels (static Row/Col display) → table grid
- Table: column headers from `data.col_values`, row headers from `data.row_values`, cells from `data.price_matrix[ri][ci]` + `data.upside_matrix[ri][ci]` + `data.color_matrix[ri][ci]`
- Cell coloring via `colorClass()` mapping backend color names to CSS classes
- Base cell highlighted with `.cellBase` class
- **Missing:** variable selector dropdowns, range min/max inputs, grid size selector, preset buttons, enhanced tooltips

---

### SESSION 8O — History Fix (Auto-Save on Run, Save Macro, Snapshot Formatting)

**Spec:** `specs/phase8_model_builder_history.md` → Areas 1, 2, 3
**Current task file:** `tasks/8O_tasks.md` — tasks/AC correct, Builder prompt needs existing code

**Source: `backend/repositories/model_repo.py`**

- `ModelRepo` with: `get_model(id)`, `get_models_for_ticker(ticker)`, `get_model_by_ticker_type(ticker, model_type)`, `create_model(data)`, `update_model(model_id, data)`
- **Missing:** `get_or_create_model(ticker, model_type)` — should check if exists, update `last_run_at` if yes, create if no

**Source: `backend/routers/models_router.py` — run endpoints**

Current `run_dcf` pattern:
```python
@router.post("/{ticker}/run/dcf")
async def run_dcf(ticker: str, body: RunRequest, request: Request):
    try:
        engine = request.app.state.assumption_engine
        assumptions = await engine.generate_assumptions(ticker, model_type="dcf", overrides=body.overrides)
        data, price = await _gather_engine_data(ticker, request)
        result = DCFEngine.run(assumptions, data, price)
        return success_response(data=result.model_dump(mode="json"))
    except Exception as exc:
        ...
```
Same pattern for `run_ddm`, `run_comps`, `run_revbased`. None currently persist to DB or return `model_id`.
`model_repo` is on `app.state.model_repo`.

**Source: `frontend/src/pages/ModelBuilder/Models/ModelTab.tsx`**

Current run flow:
```typescript
const data = await api.post<ModelResult>(`/api/v1/model-builder/${ticker}/run/${endpoint}`, {});
setResult(data);
```
Does NOT set `activeModelId`. Response currently has no `model_id` field.

**Source: `frontend/src/pages/ModelBuilderPage.tsx`**

Header area currently has: search input, dropdown, model type pills, ExportDropdown (shown when `activeModelId` exists), detection bar. **No Save button**.
The `ExportDropdown` is conditional: `{activeTicker && useModelStore.getState().activeModelId && ( <ExportDropdown ... /> )}`

**Source: `frontend/src/pages/ModelBuilder/History/HistoryTab.tsx`**

- Resolves `modelId` from `activeModelId` in store or falls back to API lookup
- If no model found: shows "No model found for {ticker}. Run a valuation first."
- Version list: table with version_number, date, annotation, size, actions (Load/View)
- Snapshot viewer: modal overlay with `<pre>` showing `JSON.stringify(viewingVersion.snapshot, null, 2)` — raw JSON dump
- Save dialog: inline input for annotation + Save/Cancel buttons, POSTs to `/model/{modelId}/save-version`
- Load button currently just opens the viewer (same as View) — does NOT restore assumptions

---

## AFTER PHASE 8: Continue to Phases 9–14

Once 8K–8O are rewritten, produce new task files for the remaining 14 sessions. Follow the same process PM1 used (described in `PM1_STARTUP_PROMPT.md`):

| Phase | Sessions | Spec File(s) | Priority |
|-------|----------|-------------|----------|
| **9** Scanner | 9A, 9B, 9C | `specs/phase9_scanner.md` | 9A: High (shared asset) |
| **10** Portfolio | 10A–10F | `phase10_portfolio_holdings.md`, `phase10_portfolio_performance.md`, `phase10_portfolio_remaining.md` | **10C: CRITICAL**, 10D: High |
| **11** Research | 11A–11D | `specs/phase11_research.md` | **11A: CRITICAL** |
| **14** Packaging | 14A | `specs/phase14_packaging_distribution.md` | Last |

For each session: read the spec → read the actual source code → write the task file with full Builder prompt to `tasks/{session_id}_tasks.md`.

---

## CROSS-CUTTING RULES (Include in Every Builder Prompt)

1. **Display Name Rule:** All backend snake_case keys displayed in the UI must use the shared `displayNames.ts` utility (`import from '@/utils/displayNames'`). Never show raw keys. Never use inline `.replace(/_/g, ' ')`.
2. **Chart Quality:** All charts must meet Fidelity/Yahoo Finance information-density standards: proper labels, hover tooltips with full detail, value annotations on bars/lines, crosshairs, responsive formatting.
3. **Data Format:** All ratios/percentages stored as decimal ratios (0.15 = 15%).
4. **Scenario Order:** Bear / Base / Bull (left to right), Base default.

---

*PM2 Startup Prompt — March 6, 2026*
*Priority 1: Rewrite 8K–8O to full quality*
*Priority 2: Produce 9A–14A as new task files*
