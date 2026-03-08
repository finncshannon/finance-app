# Session 8G — Monte Carlo Assumption Engine (Backend Only)
## Phase 8: Model Builder

**Priority:** Normal
**Type:** Backend Only
**Depends On:** None (but benefits from 8E's wacc_breakdown field)
**Spec Reference:** `specs/phase8_model_builder_assumptions_monte_carlo.md` → Areas 1–4

---

## SCOPE SUMMARY

Upgrade the assumption engine from single-pass deterministic generation to multi-trial stochastic generation (100 trials default). Add a `TrialParameters` model for per-trial parameter jitter. Parameterize pipeline functions (`project_revenue`, `project_margins`, `calculate_wacc`) to accept optional trial parameters. Build a `monte_carlo.py` module that runs N jittered trials, aggregates results statistically (median), and produces distribution-based confidence scores. Make Monte Carlo the default generation method with a deterministic fallback.

---

## TASKS

### Task 1: Add New Models (TrialParameters, MonteCarloAssumptionResult, FieldDistribution)
**Description:** Define the Pydantic models for per-trial parameters and the aggregated MC result.

**Subtasks:**
- [ ] 1.1 — In `backend/services/assumption_engine/models.py`, add:
  ```python
  class TrialParameters(BaseModel):
      """Per-trial parameter overrides for stochastic generation."""
      regression_window_weights: dict[int, float] | None = None
      outlier_mask: list[int] | None = None  # fiscal years to exclude
      industry_weight: float | None = None
      fade_lambda_scale: float = 1.0
      margin_convergence_years: int | None = None
      erp_override: float | None = None
      beta_jitter: float = 0.0
      size_premium_jitter: float = 0.0

  class FieldDistribution(BaseModel):
      field: str
      median: float
      mean: float
      std: float
      p5: float
      p95: float
      confidence: float

  class MonteCarloAssumptionResult(BaseModel):
      final_assumptions: AssumptionSet
      trial_count: int
      valid_trials: int
      distributions: dict[str, FieldDistribution] | None = None
      confidence_method: str = "monte_carlo_cv"
  ```

---

### Task 2: Add MC Default Constants
**Description:** Add Monte Carlo default parameters to the constants module.

**Subtasks:**
- [ ] 2.1 — In `backend/services/assumption_engine/constants.py`, add at the end:
  ```python
  # ---------------------------------------------------------------------------
  # Monte Carlo Defaults (Session 8G)
  # ---------------------------------------------------------------------------
  MC_DEFAULT_TRIALS = 100
  MC_MIN_YEARS_FOR_MC = 3  # below this, fall back to deterministic
  MC_INDUSTRY_WEIGHT_MIN = 0.15
  MC_INDUSTRY_WEIGHT_MAX = 0.45
  MC_INDUSTRY_WEIGHT_DEFAULT = 0.30
  MC_FADE_LAMBDA_STD = 0.15
  MC_MARGIN_CONVERGENCE_MIN = 3
  MC_MARGIN_CONVERGENCE_MAX = 10
  MC_MARGIN_CONVERGENCE_DEFAULT = 5
  MC_ERP_JITTER_STD = 0.005
  MC_BETA_JITTER_STD = 0.10
  MC_SIZE_PREMIUM_JITTER_STD = 0.0025
  ```

---

### Task 3: Parameterize Pipeline Functions
**Description:** Add optional `trial_params: TrialParameters | None` to revenue, margin, and WACC pipeline functions. When `None`, behavior is identical to current (zero regression risk).

**Subtasks:**
- [ ] 3.1 — In `backend/services/assumption_engine/revenue.py`:
  - Update `project_revenue(data, trial_params=None)` signature
  - When `trial_params` is not None:
    - Use `trial_params.regression_window_weights` to weight CAGR windows if provided (instead of equal weighting)
    - Use `trial_params.fade_lambda_scale` to scale the lambda for exponential decay
    - Use `trial_params.outlier_mask` to exclude specific fiscal years from regression
  - When `trial_params` is None: exact same behavior as before
- [ ] 3.2 — In `backend/services/assumption_engine/margins.py`:
  - Update `project_margins(data, regime, trial_params=None)` signature
  - When `trial_params` is not None:
    - Use `trial_params.industry_weight` as the industry benchmark blending weight
    - Use `trial_params.margin_convergence_years` for convergence speed
  - When `trial_params` is None: exact same behavior
- [ ] 3.3 — In `backend/services/assumption_engine/wacc.py`:
  - Update `calculate_wacc(data, trial_params=None)` signature
  - When `trial_params` is not None:
    - Apply `trial_params.beta_jitter` to raw_beta (additive)
    - Apply `trial_params.size_premium_jitter` to size_premium (additive)
    - Use `trial_params.erp_override` as ERP if provided (instead of default)
  - When `trial_params` is None: exact same behavior
- [ ] 3.4 — In `backend/services/assumption_engine/pipeline.py`:
  - Update `generate_assumptions()` to accept `trial_params: TrialParameters | None = None`
  - Thread it through to `project_revenue(data, trial_params)`, `project_margins(data, regime, trial_params)`, `calculate_wacc(data, trial_params)`

**Implementation Notes:**
- This is the most delicate task. Each function must check `if trial_params is not None` before using any parameter. The default codepath (`None`) must be EXACTLY identical to current behavior.
- For revenue: the window weights currently use `compute_cagr` for [3, 5, 10] year windows with equal or regime-based weighting. `trial_params.regression_window_weights` would be like `{3: 0.4, 5: 0.4, 10: 0.2}` — a dict of window → weight.
- For margins: the current `project_margins` uses `INDUSTRY_WEIGHT` from constants (or similar). The trial_params overrides this.
- For WACC: jitter is additive — `raw_beta + trial_params.beta_jitter`, then proceed with Blume adjustment as normal.

---

### Task 4: Create Monte Carlo Module
**Description:** Build the main MC orchestration module that runs N jittered trials and aggregates results.

**Subtasks:**
- [ ] 4.1 — Create `backend/services/assumption_engine/monte_carlo.py`:
  - Main function: `async def generate_assumptions_monte_carlo(engine, ticker, n_trials=100, seed=None, overrides=None) -> MonteCarloAssumptionResult`
  - Jitter generator: `def _generate_trial_params(rng: random.Random, trial_idx: int) -> TrialParameters` — samples from the distributions specified in the spec (Dirichlet for window weights, Uniform for industry weight, Normal for jitters, etc.)
  - Aggregation: `def _aggregate_trials(trials: list[AssumptionSet]) -> tuple[AssumptionSet, dict[str, FieldDistribution]]` — computes median for each numeric field, builds field distributions
  - Confidence: `def _distribution_confidence(values: list[float]) -> float` — CV-based scoring
- [ ] 4.2 — The trial loop:
  ```python
  rng = random.Random(seed)
  trials = []
  for i in range(n_trials):
      trial_params = _generate_trial_params(rng, i)
      try:
          result = await engine.generate_assumptions(ticker, overrides=overrides, trial_params=trial_params)
          if result.scenarios is not None:
              trials.append(result)
      except Exception as e:
          logger.debug("Trial %d failed for %s: %s", i, ticker, e)
  ```
- [ ] 4.3 — Jitter parameter generation:
  - `regression_window_weights`: Use `rng.dirichlet`-like sampling (since Python's `random` doesn't have Dirichlet, use Gamma(alpha, 1) and normalize). Alpha = [2, 3, 1] for [3yr, 5yr, 10yr].
  - `outlier_mask`: For each borderline year (could pass a list of candidate years), include with probability 0.5
  - `industry_weight`: `rng.uniform(MC_INDUSTRY_WEIGHT_MIN, MC_INDUSTRY_WEIGHT_MAX)`
  - `fade_lambda_scale`: `max(0.5, rng.gauss(1.0, MC_FADE_LAMBDA_STD))`
  - `margin_convergence_years`: `rng.randint(MC_MARGIN_CONVERGENCE_MIN, MC_MARGIN_CONVERGENCE_MAX)`
  - `erp_override`: `DEFAULT_ERP + rng.gauss(0, MC_ERP_JITTER_STD)`, clamped to [0.03, 0.08]
  - `beta_jitter`: `rng.gauss(0, MC_BETA_JITTER_STD)`, clamped to [-0.3, 0.3]
  - `size_premium_jitter`: `rng.gauss(0, MC_SIZE_PREMIUM_JITTER_STD)`, clamped to [-0.01, 0.01]
- [ ] 4.4 — Aggregation logic:
  - Extract all numeric fields from each scenario (base/bull/bear) across all trials
  - For each field: compute median, mean, stdev, 5th percentile, 95th percentile
  - Build the final `AssumptionSet` using median values
  - Compute per-field confidence using `_distribution_confidence()`
  - Compute overall confidence as the weighted average of per-field confidences
  - Preserve WACC breakdown, model assumptions, metadata from the median trial (or reconstruct)
- [ ] 4.5 — `_distribution_confidence()`:
  ```python
  def _distribution_confidence(values: list[float]) -> float:
      if len(values) < 2:
          return 50.0
      mean_val = statistics.mean(values)
      std_val = statistics.stdev(values)
      cv = std_val / abs(mean_val) if abs(mean_val) > 0.001 else 1.0
      score = max(50, min(95, 95 - (cv * 200)))
      return round(score, 0)
  ```
- [ ] 4.6 — Fallback: if fewer than 10 valid trials, fall back to deterministic and log a warning.

---

### Task 5: Add MC Entry Point to Pipeline
**Description:** Add a method on `AssumptionEngine` that uses Monte Carlo by default.

**Subtasks:**
- [ ] 5.1 — In `backend/services/assumption_engine/pipeline.py`, add method to `AssumptionEngine`:
  ```python
  async def generate_assumptions_mc(
      self,
      ticker: str,
      n_trials: int = MC_DEFAULT_TRIALS,
      seed: int | None = None,
      overrides: dict | None = None,
  ) -> AssumptionSet:
      """Generate assumptions using Monte Carlo method.
      Falls back to deterministic if MC fails or insufficient data."""
      from .monte_carlo import generate_assumptions_monte_carlo
      from .constants import MC_MIN_YEARS_FOR_MC
      
      # Check if MC is viable
      try:
          data = await gather_company_data(...)
          if data.years_available < MC_MIN_YEARS_FOR_MC:
              logger.info("MC skipped for %s: only %d years of data", ticker, data.years_available)
              return await self.generate_assumptions(ticker, overrides=overrides)
      except:
          return await self.generate_assumptions(ticker, overrides=overrides)
      
      try:
          mc_result = await generate_assumptions_monte_carlo(
              engine=self, ticker=ticker, n_trials=n_trials,
              seed=seed, overrides=overrides,
          )
          return mc_result.final_assumptions
      except Exception as e:
          logger.warning("MC failed for %s, falling back to deterministic: %s", ticker, e)
          return await self.generate_assumptions(ticker, overrides=overrides)
  ```

---

### Task 6: Update Router to Support MC
**Description:** Add method/trials query parameters to the generate endpoint.

**Subtasks:**
- [ ] 6.1 — In `backend/routers/models_router.py`, update the `POST /{ticker}/generate` endpoint:
  ```python
  @router.post("/{ticker}/generate")
  async def generate_assumptions(
      ticker: str,
      request: Request,
      method: str = "monte_carlo",  # "monte_carlo" or "deterministic"
      trials: int = 100,
  ):
      body = await request.json() if ... else {}
      overrides = body.get("overrides")
      engine = request.app.state.assumption_engine
      
      if method == "deterministic":
          result = await engine.generate_assumptions(ticker, overrides=overrides)
      else:
          result = await engine.generate_assumptions_mc(
              ticker, n_trials=trials, overrides=overrides,
          )
      return success_response(data=result.model_dump())
  ```
- [ ] 6.2 — Alternatively, keep the endpoint interface identical but make MC the default internally. The `method` and `trials` can be query parameters for advanced/debug use.

---

### Task 7: Update Exports
**Description:** Export the new MC function from the package.

**Subtasks:**
- [ ] 7.1 — In `backend/services/assumption_engine/__init__.py`, update:
  ```python
  from .pipeline import AssumptionEngine
  from .monte_carlo import generate_assumptions_monte_carlo
  
  __all__ = ["AssumptionEngine", "generate_assumptions_monte_carlo"]
  ```

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: `TrialParameters` model exists with all 8 jitter fields.
- [ ] AC-2: `MonteCarloAssumptionResult` and `FieldDistribution` models exist.
- [ ] AC-3: MC default constants added to `constants.py` (trials=100, jitter ranges).
- [ ] AC-4: `project_revenue()` accepts `trial_params` and uses window weights + fade lambda scale when provided.
- [ ] AC-5: `project_margins()` accepts `trial_params` and uses industry weight + convergence speed when provided.
- [ ] AC-6: `calculate_wacc()` accepts `trial_params` and applies beta/ERP/size premium jitter when provided.
- [ ] AC-7: When `trial_params=None`, all pipeline functions behave identically to before (zero regression).
- [ ] AC-8: `monte_carlo.py` exists with `generate_assumptions_monte_carlo()` function.
- [ ] AC-9: Jitter generation uses controlled randomness: Dirichlet for window weights, Normal for jitters, Uniform for industry weight/convergence.
- [ ] AC-10: All jittered parameters are clamped to reasonable ranges.
- [ ] AC-11: Aggregation uses median (not mean) for final output.
- [ ] AC-12: Per-field distributions computed: median, mean, std, p5, p95, confidence.
- [ ] AC-13: `_distribution_confidence()` maps CV to 50–95 score range. Tight distributions → 80+.
- [ ] AC-14: Overall confidence is weighted average of per-field confidences.
- [ ] AC-15: Confidence scores naturally land above 80 for companies with consistent data.
- [ ] AC-16: Falls back to deterministic if: <3 years of data, MC fails, or <10 valid trials.
- [ ] AC-17: `generate_assumptions_mc()` method exists on `AssumptionEngine`.
- [ ] AC-18: Generate endpoint accepts `method` and `trials` parameters (default: MC with 100).
- [ ] AC-19: Optional `seed` parameter for reproducible results.
- [ ] AC-20: Response format unchanged — still returns `AssumptionSet` (backward compatible for frontend).
- [ ] AC-21: Performance: 100 trials completes within 5 seconds for typical tickers.
- [ ] AC-22: Fallback to deterministic logged as a warning.
- [ ] AC-23: Module exported from `__init__.py`.

---

## FILES TOUCHED

**New files:**
- `backend/services/assumption_engine/monte_carlo.py` — MC orchestration, jitter generation, aggregation, distribution confidence

**Modified files:**
- `backend/services/assumption_engine/models.py` — add TrialParameters, FieldDistribution, MonteCarloAssumptionResult
- `backend/services/assumption_engine/constants.py` — add MC default parameters
- `backend/services/assumption_engine/revenue.py` — accept trial_params (window weights, fade scale)
- `backend/services/assumption_engine/margins.py` — accept trial_params (industry weight, convergence)
- `backend/services/assumption_engine/wacc.py` — accept trial_params (beta/ERP/size premium jitter)
- `backend/services/assumption_engine/pipeline.py` — thread trial_params, add generate_assumptions_mc()
- `backend/services/assumption_engine/confidence.py` — add distribution_confidence() (keep heuristic as fallback)
- `backend/services/assumption_engine/__init__.py` — export MC function
- `backend/routers/models_router.py` — add method/trials query params

---

## BUILDER PROMPT

> **Session 8G — Monte Carlo Assumption Engine (Backend Only)**
>
> You are building session 8G of the Finance App v2.0 update.
>
> **What you're doing:** Upgrading the assumption engine from single-pass deterministic generation to multi-trial Monte Carlo generation (100 trials default). Each trial introduces controlled parameter jitter, results are aggregated using median statistics, and confidence scores are computed from distribution width (CV-based).
>
> **Context:** The current assumption engine runs one deterministic pass: historical data → regressions → rules → one assumption set with heuristic confidence (typically 65–75). You're wrapping this in a trial loop that varies regression windows, outlier treatment, industry benchmark weights, decay curves, and WACC components across 100 trials, then takes the median. Confidence becomes a natural outcome of distribution tightness.
>
> **Existing code:**
>
> Pipeline architecture:
> - `pipeline.py` → `AssumptionEngine.generate_assumptions(ticker, model_type, overrides)` — main entry point. Calls: `gather_company_data()` → `project_revenue(data)` → `project_margins(data, regime)` → `calculate_wacc(data)` → `generate_scenarios(...)` → `map_all_models(...)` → `score_confidence(...)` → `generate_reasoning(...)` → returns `AssumptionSet`.
> - `revenue.py` → `project_revenue(data: CompanyDataPackage) -> RevenueProjection`. Pure computation. Uses CAGR windows [3, 5, 10], exponential decay with `LAMBDA_BY_REGIME`, analyst blending.
> - `margins.py` → `project_margins(data, regime) -> dict[str, MarginLensResult]`. 4-lens approach: trend, mean reversion, sector gravity, management guidance. Uses industry benchmarks with a weight constant.
> - `wacc.py` → `calculate_wacc(data: CompanyDataPackage) -> WACCResult`. 8-step CAPM/WACC. Uses `DEFAULT_ERP`, raw beta, size premium.
> - `confidence.py` → `score_confidence(data, revenue, margins, wacc) -> AssumptionConfidence`. Heuristic scoring 0–100.
> - `constants.py` → all named constants including CAGR_WINDOWS, LAMBDA_BY_REGIME, DEFAULT_ERP, BLUME_WEIGHT_*, WACC_FLOOR/CEILING, SIZE_PREMIUM_*.
> - `models.py` → `CompanyDataPackage`, `RevenueProjection`, `MarginLensResult`, `WACCResult`, `ScenarioProjections`, `ScenarioSet`, `AssumptionSet`, etc.
> - `__init__.py` → exports `AssumptionEngine`.
>
> **Cross-cutting rules:**
> - Display Name Rule: All backend snake_case keys displayed in the UI must use the shared `displayNames.ts` utility.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%).
> - Scenario Order: Bear / Base / Bull (left to right), Base default.
>
> **Task 1: New Models**
>
> In `models.py`, add `TrialParameters`, `FieldDistribution`, `MonteCarloAssumptionResult` (see spec for exact fields).
>
> **Task 2: MC Constants**
>
> In `constants.py`, add MC defaults: `MC_DEFAULT_TRIALS=100`, `MC_MIN_YEARS_FOR_MC=3`, jitter ranges for industry weight (0.15–0.45), fade lambda std (0.15), margin convergence (3–10), ERP jitter std (0.005), beta jitter std (0.10), size premium jitter std (0.0025).
>
> **Task 3: Parameterize Pipeline Functions**
>
> Update function signatures to accept `trial_params: TrialParameters | None = None`. When None, behavior must be EXACTLY identical to current (zero regression risk). When provided, apply the relevant jitter.
>
> - `revenue.py` → `project_revenue(data, trial_params=None)`: use `regression_window_weights` for CAGR window weighting, `fade_lambda_scale` to scale lambda, `outlier_mask` to exclude years.
> - `margins.py` → `project_margins(data, regime, trial_params=None)`: use `industry_weight` and `margin_convergence_years`.
> - `wacc.py` → `calculate_wacc(data, trial_params=None)`: apply `beta_jitter` (additive to raw_beta), `size_premium_jitter` (additive), `erp_override` (replaces DEFAULT_ERP).
> - `pipeline.py` → `generate_assumptions(ticker, ..., trial_params=None)`: thread trial_params to all sub-functions.
>
> **CRITICAL**: Test that `generate_assumptions(ticker)` with no trial_params produces identical output to before. This is the zero-regression guarantee.
>
> **Task 4: Create monte_carlo.py**
>
> New file with:
> - `generate_assumptions_monte_carlo(engine, ticker, n_trials, seed, overrides)` — runs N trials with jittered params, aggregates, returns `MonteCarloAssumptionResult`
> - `_generate_trial_params(rng, trial_idx)` — samples jitter from distributions
> - `_aggregate_trials(trials: list[AssumptionSet])` — median aggregation per field
> - `_distribution_confidence(values)` — CV-based scoring: `max(50, min(95, 95 - cv * 200))`
>
> For Dirichlet-like sampling without numpy: use Gamma distribution via `rng.gammavariate(alpha, 1.0)` for each window, then normalize to sum to 1.0.
>
> Fallback: if <10 valid trials, return deterministic result with a warning.
>
> **Task 5: MC Entry Point on Pipeline**
>
> Add `generate_assumptions_mc(ticker, n_trials, seed, overrides)` to `AssumptionEngine`. Checks data years >= MC_MIN_YEARS_FOR_MC before running MC. Falls back to deterministic on failure.
>
> **Task 6: Router Update**
>
> Add `method: str = "monte_carlo"` and `trials: int = 100` query params to `POST /{ticker}/generate`. Default to MC. `method=deterministic` skips MC.
>
> **Task 7: Update Exports**
>
> Export `generate_assumptions_monte_carlo` from `__init__.py`.
>
> **Acceptance criteria:**
> 1. TrialParameters, MonteCarloAssumptionResult, FieldDistribution models exist
> 2. MC constants added (trials=100, jitter ranges)
> 3. Pipeline functions accept trial_params; None = identical behavior (ZERO REGRESSION)
> 4. monte_carlo.py runs N trials with jitter, aggregates via median
> 5. Per-field distributions: median, mean, std, p5, p95, confidence
> 6. Distribution confidence: CV → 50–95 score. Tight data → 80+
> 7. Falls back to deterministic: <3 years data, MC failure, <10 valid trials
> 8. Generate endpoint: method=monte_carlo (default), trials=100 (default)
> 9. Seed parameter for reproducibility
> 10. Response format unchanged (AssumptionSet) — backward compatible
> 11. Performance: 100 trials < 5 seconds typical
>
> **Files to create:**
> - `backend/services/assumption_engine/monte_carlo.py`
>
> **Files to modify:**
> - `backend/services/assumption_engine/models.py`
> - `backend/services/assumption_engine/constants.py`
> - `backend/services/assumption_engine/revenue.py`
> - `backend/services/assumption_engine/margins.py`
> - `backend/services/assumption_engine/wacc.py`
> - `backend/services/assumption_engine/pipeline.py`
> - `backend/services/assumption_engine/confidence.py`
> - `backend/services/assumption_engine/__init__.py`
> - `backend/routers/models_router.py`
>
> **Technical constraints:**
> - Python 3.12, Pydantic v2, asyncio
> - Pure computation — no additional API calls or DB writes per trial
> - Use `random.Random(seed)` for reproducible jitter (not module-level `random`)
> - Gamma distribution for Dirichlet-like sampling: `rng.gammavariate(alpha, 1.0)`
> - All jitter values clamped to prevent nonsensical outputs
> - Median for final output (robust to outlier trials)
> - Statistics module: `statistics.mean`, `statistics.stdev`, `statistics.median`, `statistics.quantiles`
> - The MC upgrade must be transparent to the frontend — same AssumptionSet response shape
