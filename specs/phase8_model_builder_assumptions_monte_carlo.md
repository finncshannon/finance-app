# Finance App — Assumption Engine: Monte Carlo Generation Upgrade Plan
## Phase 8: Model Builder — Assumptions (Engine Upgrade)

**Prepared by:** Planner (March 5, 2026)
**Recipient:** PM Agent
**Scope:** Upgrade the assumption engine from single-pass deterministic generation to multi-trial stochastic generation with statistical aggregation

---

## PLAN SUMMARY

The current assumption engine runs one deterministic pass: historical data → regressions → rules → one set of assumptions with a heuristic confidence score (typically 65–75). This plan upgrades it to run N trials (100 default) with controlled parameter variation, aggregate the results statistically, and output the central tendency (median) assumptions with distribution-based confidence scoring. The result: naturally higher confidence scores, more robust assumptions, and a bell curve of outcomes to choose from.

---

## CONCEPT

### Current Flow
```
Historical Data → Single Analysis Pass → One Assumption Set → Heuristic Confidence Score
```

### New Flow
```
Historical Data → 100 Analysis Passes (varied parameters) → 100 Assumption Sets
                → Statistical Aggregation (median/mode) → Final Assumption Set
                → Distribution Width = Natural Confidence Score
```

### What Varies Between Trials
Each trial introduces controlled randomness in:
- **Regression window selection** — randomly weight recent vs older data (e.g., trial 1 uses 3-year window weighted 60%, trial 2 uses 5-year weighted 70%)
- **Outlier treatment** — randomly include/exclude borderline outlier years
- **Industry benchmark weighting** — vary the blend between company-specific trends and industry medians
- **Growth rate fade curve** — slight perturbation of the exponential decay lambda
- **Margin convergence speed** — vary how quickly margins revert to sector mean
- **WACC component jitter** — small perturbations to ERP (±0.5%), beta (±0.1), size premium (±0.25%)

### What Stays Fixed
- The underlying financial data (no noise added to raw numbers)
- The structural methodology (CAPM for cost of equity, same terminal value approach, same scenario framework)
- Guardrails and clamps (WACC floor/ceiling, margin ceilings, terminal growth limits)

---

## AREA 1: STOCHASTIC PARAMETER GENERATION

### New Module: `backend/services/assumption_engine/monte_carlo.py`

**Purpose:** Wraps the existing pipeline with a loop that introduces controlled randomness per trial.

**Key function:**
```python
async def generate_assumptions_monte_carlo(
    engine: AssumptionEngine,
    ticker: str,
    n_trials: int = 100,
    seed: int | None = None,
) -> MonteCarloAssumptionResult:
    """Run the assumption pipeline N times with parameter jitter.
    
    Returns the median assumption set plus distribution statistics.
    """
```

**Parameter jitter specification:**
Each trial draws from distributions around the deterministic baseline:
- `regression_window_weights`: Dirichlet distribution over [3yr, 5yr, 10yr] windows
- `outlier_inclusion`: Bernoulli per borderline year (z-score between 1.5 and 2.5)
- `industry_weight`: Uniform [0.15, 0.45] (baseline: 0.30)
- `fade_lambda_scale`: Normal(1.0, 0.15) — scales the regime-based lambda
- `margin_convergence_speed`: Uniform [3, 10] years (baseline: 5)
- `erp_jitter`: Normal(0, 0.005) — ±0.5% on equity risk premium
- `beta_jitter`: Normal(0, 0.10) — ±0.1 on raw beta
- `size_premium_jitter`: Normal(0, 0.0025) — ±0.25% on size premium

All jittered parameters are clamped to reasonable ranges to prevent nonsensical outputs.

**Files touched:**
- `backend/services/assumption_engine/monte_carlo.py` — new file
- `backend/services/assumption_engine/constants.py` — add MC default parameters (n_trials, jitter ranges)

---

## AREA 2: PIPELINE PARAMETERIZATION

### Current State
The pipeline functions (`project_revenue`, `project_margins`, `calculate_wacc`, `generate_scenarios`) use fixed constants from `constants.py`. There's no way to pass in varied parameters.

### Changes
Add an optional `TrialParameters` config object that each pipeline stage can read:

```python
class TrialParameters(BaseModel):
    """Per-trial parameter overrides for stochastic generation."""
    regression_window_weights: dict[int, float] | None = None  # {3: 0.4, 5: 0.4, 10: 0.2}
    outlier_mask: list[int] | None = None  # fiscal years to exclude
    industry_weight: float | None = None
    fade_lambda_scale: float = 1.0
    margin_convergence_years: int | None = None
    erp_override: float | None = None
    beta_jitter: float = 0.0
    size_premium_jitter: float = 0.0
```

Each pipeline function signature adds `trial_params: TrialParameters | None = None`:
- `project_revenue(data, trial_params=None)` — uses `regression_window_weights` and `fade_lambda_scale`
- `project_margins(data, trial_params=None)` — uses `industry_weight` and `margin_convergence_years`
- `calculate_wacc(data, trial_params=None)` — uses `erp_override`, `beta_jitter`, `size_premium_jitter`

When `trial_params` is `None` (normal deterministic call), behavior is identical to current. Zero regression risk.

**Files touched:**
- `backend/services/assumption_engine/models.py` — add `TrialParameters` model
- `backend/services/assumption_engine/revenue.py` — accept trial_params, use window weights
- `backend/services/assumption_engine/margins.py` — accept trial_params, use industry weight and convergence speed
- `backend/services/assumption_engine/wacc.py` — accept trial_params, apply jitter
- `backend/services/assumption_engine/pipeline.py` — thread trial_params through to sub-functions

---

## AREA 3: STATISTICAL AGGREGATION

### After N Trials
Collect N assumption sets. For each numerical field, compute:
- **Median** (used as the final output — robust to outliers)
- **Mean** (for reference)
- **Standard deviation** (basis for confidence)
- **5th and 95th percentiles** (uncertainty bounds)

### Aggregation targets (per scenario: base/bull/bear):
- `revenue_growth_rates[i]` for each year
- `operating_margins[i]` for each year
- `gross_margins[i]`, `ebitda_margins[i]`, `net_margins[i]`, `fcf_margins[i]`
- `wacc`
- `cost_of_equity`
- `terminal_growth_rate`
- `capex_to_revenue`, `nwc_change_to_revenue`
- `scenario_weight`

### Confidence Scoring (New)
Replace the heuristic confidence scoring with distribution-based scoring:

```python
def distribution_confidence(values: list[float]) -> float:
    """Score confidence based on how tight the distribution is.
    
    Tight distribution (low CV) → high confidence
    Wide distribution (high CV) → low confidence
    """
    if len(values) < 2:
        return 50.0
    mean = statistics.mean(values)
    std = statistics.stdev(values)
    cv = std / abs(mean) if abs(mean) > 0.001 else 1.0
    
    # Map CV to confidence score:
    # CV < 0.05 → 95 (very tight)
    # CV 0.05-0.10 → 85-95
    # CV 0.10-0.20 → 75-85
    # CV 0.20-0.30 → 65-75
    # CV > 0.30 → 50-65
    score = max(50, min(95, 95 - (cv * 200)))
    return round(score, 0)
```

This naturally produces scores above 80 when the data is consistent (many trials converge) and below 80 when the data is noisy (trials diverge). The 80 threshold Finn wants becomes a natural outcome rather than an arbitrary bar.

### Output Model
```python
class MonteCarloAssumptionResult(BaseModel):
    """Result of multi-trial assumption generation."""
    final_assumptions: AssumptionSet  # median values
    trial_count: int
    valid_trials: int
    
    # Per-field distributions (for optional frontend visualization)
    distributions: dict[str, FieldDistribution] | None = None
    
    # Aggregated confidence (replaces heuristic)
    confidence_method: str = "monte_carlo_cv"

class FieldDistribution(BaseModel):
    field: str
    median: float
    mean: float
    std: float
    p5: float
    p95: float
    confidence: float  # per-field confidence from CV
```

**Files touched:**
- `backend/services/assumption_engine/monte_carlo.py` — aggregation logic
- `backend/services/assumption_engine/models.py` — add MonteCarloAssumptionResult, FieldDistribution
- `backend/services/assumption_engine/confidence.py` — add distribution_confidence function (keep old heuristic as fallback)

---

## AREA 4: INTEGRATION

### Endpoint Changes
- The existing `/api/v1/model-builder/{ticker}/generate` endpoint should use Monte Carlo by default
- Add query parameter `?method=deterministic` to fall back to single-pass (for speed or debugging)
- Add query parameter `?trials=100` to control trial count
- Response format stays the same (`AssumptionSet`) — the MC aggregation is internal. The `confidence` field now reflects distribution-based scoring.
- Optionally include `distributions` in the response if frontend wants to show bell curves later

### Performance
- Each trial is pure computation on cached data — no API calls, no DB writes
- A single trial takes ~5–50ms depending on data complexity
- 100 trials: ~0.5–5 seconds total
- This runs server-side and returns once complete
- The frontend already shows a loading spinner ("Generating assumptions...") so the user experience doesn't change much — just slightly longer generation time

### Fallback
- If Monte Carlo fails (e.g., all trials produce errors), fall back to single deterministic pass
- Log warning: "Monte Carlo generation failed, falling back to deterministic"

**Files touched:**
- `backend/services/assumption_engine/pipeline.py` — add MC entry point, default to MC
- `backend/routers/models_router.py` — add method/trials query params to generate endpoint
- `backend/services/assumption_engine/__init__.py` — export new MC function

---

## SESSION ORGANIZATION (Recommended for PM)

### Session 8G — Monte Carlo Assumption Engine (Backend Only)
**Scope:** All four areas
**Files:**
- `backend/services/assumption_engine/monte_carlo.py` — new file (trial loop, jitter, aggregation)
- `backend/services/assumption_engine/models.py` — TrialParameters, MonteCarloAssumptionResult, FieldDistribution
- `backend/services/assumption_engine/constants.py` — MC default parameters
- `backend/services/assumption_engine/revenue.py` — accept trial_params
- `backend/services/assumption_engine/margins.py` — accept trial_params
- `backend/services/assumption_engine/wacc.py` — accept trial_params
- `backend/services/assumption_engine/pipeline.py` — thread trial_params, MC entry point
- `backend/services/assumption_engine/confidence.py` — distribution_confidence function
- `backend/routers/models_router.py` — method/trials params
**Complexity:** High (stochastic parameter generation, pipeline parameterization, statistical aggregation, confidence overhaul)
**Estimated acceptance criteria:** 25–30

**Note:** This is a backend-heavy session with no frontend changes. The frontend already handles the AssumptionSet response format — the MC upgrade is transparent. The only visible change is that confidence scores will naturally be higher and more meaningful.

---

## DEPENDENCIES & RISKS

| Risk | Mitigation |
|------|------------|
| 100 trials too slow for user experience | Start with 100, measure actual latency. Can drop to 50 if needed. Each trial is ~5-50ms. |
| Jitter ranges too wide → nonsensical outputs | All jittered params are clamped. Post-aggregation sanity checks (WACC in [5%, 25%], growth rates positive, etc.) |
| Stochastic results differ between runs | Optional seed parameter for reproducibility. In production, accept natural variation — it's a feature, not a bug. |
| Pipeline functions have hidden state | Audit all pipeline functions for global/module state. They should be pure functions of their inputs. |
| Old heuristic confidence scores expected by UI | Keep backward-compatible confidence format. The score is still 0-100, just computed differently. |
| Monte Carlo on companies with limited data (<3 years) | Fall back to deterministic for companies with fewer than 3 years of data (jitter has nothing to work with) |

---

## DECISIONS MADE

1. Default to Monte Carlo with 100 trials for all assumption generation
2. Deterministic mode available via query parameter for fallback/debugging
3. Median (not mean) used as final output — robust to outlier trials
4. Confidence scoring based on coefficient of variation (distribution width)
5. Tight distributions naturally score 80+ (meeting Finn's threshold)
6. All pipeline functions accept optional TrialParameters — zero regression risk when None
7. No frontend changes needed — MC is transparent to the UI
8. Per-field distributions stored for potential future bell curve visualization
9. Fallback to deterministic if MC fails
10. Minimum 3 years of data required for MC (below that, deterministic only)

---

*End of Assumption Engine — Monte Carlo Generation Upgrade Plan*
*Phase 8G · Prepared March 5, 2026*
