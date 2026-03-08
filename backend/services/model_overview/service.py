"""ModelOverviewService — orchestrates football field, weights, agreement."""

from __future__ import annotations

import logging

from engines import DCFEngine, DDMEngine, CompsEngine, RevBasedEngine
from engines.engine_utils import upside_downside
from services.assumption_engine.models import AssumptionSet

from .models import (
    ModelOverviewResult, FootballFieldRow,
    ScenarioComparisonRow, ScenarioComparisonTable,
)
from .football_field import extract_model_prices, build_football_field
from .weights import calculate_weights
from .agreement import calculate_agreement

logger = logging.getLogger("finance_app")


class ModelOverviewService:
    """Generates the unified Model Overview with football field,
    weights, agreement analysis, and scenario comparison."""

    def __init__(self, db=None, settings_service=None):
        self._db = db
        self._settings = settings_service

    async def generate_overview(
        self,
        ticker: str,
        assumption_set: AssumptionSet,
        data: dict,
        current_price: float,
        detection_scores: dict[str, float] | None = None,
        peer_data: list[dict] | None = None,
    ) -> ModelOverviewResult:
        """Run all engines and assemble the overview.

        1. Run all 4 engines
        2. Extract bear/base/bull prices
        3. Compute weights
        4. Build football field with composite
        5. Agreement analysis
        6. Scenario comparison table
        """
        warnings: list[str] = []

        # --- 1. Run all engines ---
        engine_results: dict[str, dict] = {}

        try:
            dcf_result = DCFEngine.run(assumption_set, data, current_price)
            engine_results["dcf"] = dcf_result.model_dump(mode="json")
        except Exception as exc:
            warnings.append(f"DCF engine failed: {exc}")

        try:
            ddm_result = DDMEngine.run(assumption_set, data, current_price)
            engine_results["ddm"] = ddm_result.model_dump(mode="json")
        except Exception as exc:
            warnings.append(f"DDM engine failed: {exc}")

        try:
            comps_result = CompsEngine.run(assumption_set, data, current_price, peer_data)
            engine_results["comps"] = comps_result.model_dump(mode="json")
        except Exception as exc:
            warnings.append(f"Comps engine failed: {exc}")

        try:
            rev_result = RevBasedEngine.run(assumption_set, data, current_price)
            engine_results["revenue_based"] = rev_result.model_dump(mode="json")
        except Exception as exc:
            warnings.append(f"Revenue-Based engine failed: {exc}")

        # --- 2. Extract prices ---
        model_rows = extract_model_prices(engine_results, current_price)

        # --- 3. Compute weights ---
        if detection_scores is None:
            detection_scores = {m: 50.0 for m in engine_results}
        weight_result = calculate_weights(detection_scores, engine_results, data)

        # Apply weights to model rows
        for model_name, row in model_rows.items():
            row.weight = weight_result.weights.get(model_name, 0)
            row.confidence_score = detection_scores.get(model_name)

        # --- 4. Build football field with composite ---
        ff = build_football_field(model_rows, current_price)

        # Composite = weighted average
        included = [n for n in model_rows if weight_result.weights.get(n, 0) > 0]
        excluded = weight_result.excluded_models

        comp_bear = sum(
            model_rows[n].bear_price * weight_result.weights.get(n, 0)
            for n in included if n in model_rows
        )
        comp_base = sum(
            model_rows[n].base_price * weight_result.weights.get(n, 0)
            for n in included if n in model_rows
        )
        comp_bull = sum(
            model_rows[n].bull_price * weight_result.weights.get(n, 0)
            for n in included if n in model_rows
        )

        composite_row = FootballFieldRow(
            model_name="Composite",
            bear_price=round(comp_bear, 2),
            base_price=round(comp_base, 2),
            bull_price=round(comp_bull, 2),
            weight=1.0,
        )
        ff.composite = composite_row

        comp_upside = upside_downside(comp_base, current_price)

        # --- 5. Agreement analysis ---
        agreement = calculate_agreement(model_rows, engine_results, current_price)

        # --- 6. Scenario comparison table ---
        scenario_table = _build_scenario_table(
            model_rows, detection_scores, weight_result.weights, current_price,
            comp_bear, comp_base, comp_bull,
        )

        return ModelOverviewResult(
            ticker=ticker,
            current_price=current_price,
            football_field=ff,
            model_weights=weight_result,
            agreement=agreement,
            scenario_table=scenario_table,
            composite_bear=round(comp_bear, 2),
            composite_base=round(comp_base, 2),
            composite_bull=round(comp_bull, 2),
            composite_upside_pct=round(comp_upside, 4) if comp_upside is not None else None,
            included_models=included,
            excluded_models=excluded,
            warnings=warnings,
        )


def _build_scenario_table(
    model_rows: dict[str, FootballFieldRow],
    detection_scores: dict[str, float],
    weights: dict[str, float],
    current_price: float,
    comp_bear: float,
    comp_base: float,
    comp_bull: float,
) -> ScenarioComparisonTable:
    """Build the scenario comparison table rows."""
    rows: list[ScenarioComparisonRow] = []

    for model_name, row in model_rows.items():
        upside = upside_downside(row.base_price, current_price)
        rows.append(ScenarioComparisonRow(
            model_name=model_name,
            bear=round(row.bear_price, 2),
            base=round(row.base_price, 2),
            bull=round(row.bull_price, 2),
            confidence=detection_scores.get(model_name),
            weight=weights.get(model_name, 0),
            upside_base=round(upside, 4) if upside is not None else None,
        ))

    # Composite row
    comp_upside = upside_downside(comp_base, current_price)
    rows.append(ScenarioComparisonRow(
        model_name="Composite",
        bear=round(comp_bear, 2),
        base=round(comp_base, 2),
        bull=round(comp_bull, 2),
        weight=1.0,
        upside_base=round(comp_upside, 4) if comp_upside is not None else None,
    ))

    return ScenarioComparisonTable(rows=rows)
