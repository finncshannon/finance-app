"""Monte Carlo Assumption Generation — runs N jittered trials and aggregates.

Pure computation orchestration, no I/O beyond what generate_assumptions already does.
"""

from __future__ import annotations

import copy
import logging
import math
import random
import statistics
from typing import TYPE_CHECKING

from .constants import (
    DEFAULT_ERP,
    MC_BETA_JITTER_STD,
    MC_DEFAULT_TRIALS,
    MC_ERP_JITTER_STD,
    MC_FADE_LAMBDA_STD,
    MC_INDUSTRY_WEIGHT_MAX,
    MC_INDUSTRY_WEIGHT_MIN,
    MC_MARGIN_CONVERGENCE_MAX,
    MC_MARGIN_CONVERGENCE_MIN,
    MC_SIZE_PREMIUM_JITTER_STD,
)
from .helpers import clamp
from .models import (
    AssumptionSet,
    FieldDistribution,
    MonteCarloAssumptionResult,
    TrialParameters,
)

if TYPE_CHECKING:
    from .pipeline import AssumptionEngine

logger = logging.getLogger("finance_app")


async def generate_assumptions_monte_carlo(
    engine: "AssumptionEngine",
    ticker: str,
    n_trials: int = MC_DEFAULT_TRIALS,
    seed: int | None = None,
    overrides: dict | None = None,
) -> MonteCarloAssumptionResult:
    """Run N jittered trials and aggregate via median statistics."""
    rng = random.Random(seed)
    trials: list[AssumptionSet] = []

    for i in range(n_trials):
        trial_params = _generate_trial_params(rng, i)
        try:
            result = await engine.generate_assumptions(
                ticker, overrides=overrides, trial_params=trial_params,
            )
            if result.scenarios is not None:
                trials.append(result)
        except Exception as e:
            logger.debug("Trial %d failed for %s: %s", i, ticker, e)

    if len(trials) < 10:
        logger.warning(
            "MC: only %d valid trials for %s (need >=10), falling back to deterministic",
            len(trials), ticker,
        )
        deterministic = await engine.generate_assumptions(ticker, overrides=overrides)
        deterministic.metadata.warnings.append(
            f"Monte Carlo fallback: only {len(trials)} valid trials"
        )
        return MonteCarloAssumptionResult(
            final_assumptions=deterministic,
            trial_count=n_trials,
            valid_trials=len(trials),
            confidence_method="deterministic_fallback",
        )

    # Aggregate
    final, distributions = _aggregate_trials(trials)

    # Override confidence with MC-derived scores
    if final.confidence and distributions:
        field_confs = [d.confidence for d in distributions.values()]
        if field_confs:
            mc_overall = round(statistics.mean(field_confs), 1)
            final.confidence.overall_score = mc_overall

    return MonteCarloAssumptionResult(
        final_assumptions=final,
        trial_count=n_trials,
        valid_trials=len(trials),
        distributions=distributions,
        confidence_method="monte_carlo_cv",
    )


def _generate_trial_params(rng: random.Random, trial_idx: int) -> TrialParameters:
    """Sample jittered parameters for a single trial."""
    # Dirichlet-like for regression window weights via Gamma
    alphas = [2.0, 3.0, 1.0]  # for [3yr, 5yr, 10yr]
    gammas = [rng.gammavariate(a, 1.0) for a in alphas]
    total = sum(gammas)
    if total > 0:
        normed = [g / total for g in gammas]
    else:
        normed = [1 / 3, 1 / 3, 1 / 3]
    regression_window_weights = {3: normed[0], 5: normed[1], 10: normed[2]}

    # Industry weight: uniform
    industry_weight = rng.uniform(MC_INDUSTRY_WEIGHT_MIN, MC_INDUSTRY_WEIGHT_MAX)

    # Fade lambda scale: normal, clamped
    fade_lambda_scale = max(0.5, rng.gauss(1.0, MC_FADE_LAMBDA_STD))

    # Margin convergence years: uniform int
    margin_convergence_years = rng.randint(MC_MARGIN_CONVERGENCE_MIN, MC_MARGIN_CONVERGENCE_MAX)

    # ERP override: normal jitter around default
    erp_override = clamp(DEFAULT_ERP + rng.gauss(0, MC_ERP_JITTER_STD), 0.03, 0.08)

    # Beta jitter: normal, clamped
    beta_jitter = clamp(rng.gauss(0, MC_BETA_JITTER_STD), -0.3, 0.3)

    # Size premium jitter: normal, clamped
    size_premium_jitter = clamp(rng.gauss(0, MC_SIZE_PREMIUM_JITTER_STD), -0.01, 0.01)

    return TrialParameters(
        regression_window_weights=regression_window_weights,
        outlier_mask=None,  # Could be randomized in future
        industry_weight=industry_weight,
        fade_lambda_scale=fade_lambda_scale,
        margin_convergence_years=margin_convergence_years,
        erp_override=erp_override,
        beta_jitter=beta_jitter,
        size_premium_jitter=size_premium_jitter,
    )


def _aggregate_trials(
    trials: list[AssumptionSet],
) -> tuple[AssumptionSet, dict[str, FieldDistribution]]:
    """Aggregate N trial results using median statistics."""
    distributions: dict[str, FieldDistribution] = {}

    # Collect per-scenario, per-field values
    scenario_fields: dict[str, dict[str, list[float]]] = {
        "base": {}, "bull": {}, "bear": {},
    }

    scalar_fields = [
        "wacc", "cost_of_equity", "capex_to_revenue",
        "nwc_change_to_revenue", "tax_rate", "terminal_growth_rate",
        "scenario_weight",
    ]
    array_fields = [
        "revenue_growth_rates", "gross_margins", "operating_margins",
        "ebitda_margins", "net_margins", "fcf_margins",
    ]

    for trial in trials:
        if trial.scenarios is None:
            continue
        for sc_name in ("base", "bull", "bear"):
            sc = getattr(trial.scenarios, sc_name)
            for field in scalar_fields:
                val = getattr(sc, field, None)
                if val is not None:
                    scenario_fields[sc_name].setdefault(field, []).append(val)

            for field in array_fields:
                arr = getattr(sc, field, None)
                if arr is not None:
                    for idx, val in enumerate(arr):
                        arr_key = f"{field}[{idx}]"
                        scenario_fields[sc_name].setdefault(arr_key, []).append(val)

    # Build median-based final AssumptionSet from the first trial as template
    template = trials[0]
    final = copy.deepcopy(template)

    if final.scenarios:
        for sc_name in ("base", "bull", "bear"):
            sc = getattr(final.scenarios, sc_name)
            fields_data = scenario_fields[sc_name]

            for field in scalar_fields:
                values = fields_data.get(field, [])
                if values:
                    median_val = round(statistics.median(values), 4)
                    setattr(sc, field, median_val)

                    # Build distribution
                    dist_key = f"{sc_name}.{field}"
                    distributions[dist_key] = _build_field_dist(dist_key, values)

            for field in array_fields:
                current_arr = getattr(sc, field, [])
                for idx in range(len(current_arr)):
                    arr_key = f"{field}[{idx}]"
                    values = fields_data.get(arr_key, [])
                    if values:
                        current_arr[idx] = round(statistics.median(values), 4)

                        dist_key = f"{sc_name}.{arr_key}"
                        distributions[dist_key] = _build_field_dist(dist_key, values)

    # Aggregate WACC breakdown if present
    wacc_fields_data: dict[str, list[float]] = {}
    for trial in trials:
        if trial.wacc_breakdown:
            for wf in ("wacc", "cost_of_equity", "cost_of_debt_pre_tax",
                        "cost_of_debt_after_tax", "risk_free_rate", "adjusted_beta",
                        "weight_equity", "weight_debt", "effective_tax_rate"):
                val = getattr(trial.wacc_breakdown, wf, None)
                if val is not None:
                    wacc_fields_data.setdefault(wf, []).append(val)

    if final.wacc_breakdown and wacc_fields_data:
        for wf, values in wacc_fields_data.items():
            if values:
                setattr(final.wacc_breakdown, wf, round(statistics.median(values), 4))
                dist_key = f"wacc_breakdown.{wf}"
                distributions[dist_key] = _build_field_dist(dist_key, values)

    return final, distributions


def _build_field_dist(field: str, values: list[float]) -> FieldDistribution:
    """Build a FieldDistribution from collected values."""
    if len(values) < 2:
        val = values[0] if values else 0.0
        return FieldDistribution(
            field=field, median=val, mean=val, std=0.0,
            p5=val, p95=val, confidence=50.0,
        )

    sorted_vals = sorted(values)
    n = len(sorted_vals)
    p5_idx = max(0, int(n * 0.05))
    p95_idx = min(n - 1, int(n * 0.95))

    return FieldDistribution(
        field=field,
        median=round(statistics.median(values), 6),
        mean=round(statistics.mean(values), 6),
        std=round(statistics.stdev(values), 6),
        p5=round(sorted_vals[p5_idx], 6),
        p95=round(sorted_vals[p95_idx], 6),
        confidence=_distribution_confidence(values),
    )


def _distribution_confidence(values: list[float]) -> float:
    """CV-based confidence scoring: tight distributions → high scores."""
    if len(values) < 2:
        return 50.0
    mean_val = statistics.mean(values)
    std_val = statistics.stdev(values)
    cv = std_val / abs(mean_val) if abs(mean_val) > 0.001 else 1.0
    score = max(50, min(95, 95 - (cv * 200)))
    return round(score, 0)
