"""Pydantic models for Model Overview — football field, weights, agreement."""

from __future__ import annotations

from pydantic import BaseModel, Field


# =========================================================================
# Football Field
# =========================================================================

class FootballFieldRow(BaseModel):
    model_name: str
    bear_price: float = 0.0
    base_price: float = 0.0
    bull_price: float = 0.0
    weight: float = 0.0
    confidence_score: float | None = None


class FootballFieldResult(BaseModel):
    models: list[FootballFieldRow] = Field(default_factory=list)
    composite: FootballFieldRow | None = None
    current_price: float = 0.0
    chart_min: float = 0.0
    chart_max: float = 0.0


# =========================================================================
# Model Weights
# =========================================================================

class ModelWeightResult(BaseModel):
    weights: dict[str, float] = Field(default_factory=dict)
    raw_scores: dict[str, float] = Field(default_factory=dict)
    multipliers: dict[str, float] = Field(default_factory=dict)
    adjusted_scores: dict[str, float] = Field(default_factory=dict)
    excluded_models: list[str] = Field(default_factory=list)
    included_model_count: int = 0


# =========================================================================
# Agreement Analysis
# =========================================================================

class DivergencePair(BaseModel):
    model_a: str
    model_b: str
    divergence_pct: float


class DivergenceMatrix(BaseModel):
    pairs: list[DivergencePair] = Field(default_factory=list)
    closest_pair: DivergencePair | None = None
    most_divergent_pair: DivergencePair | None = None


class AgreementAnalysis(BaseModel):
    level: str = "N/A"
    max_spread: float | None = None
    max_spread_pct: float | None = None
    highest_model: str | None = None
    highest_price: float | None = None
    lowest_model: str | None = None
    lowest_price: float | None = None
    reasoning: str = ""
    divergence_matrix: DivergenceMatrix | None = None


# =========================================================================
# Scenario Comparison
# =========================================================================

class ScenarioComparisonRow(BaseModel):
    model_name: str
    bear: float = 0.0
    base: float = 0.0
    bull: float = 0.0
    confidence: float | None = None
    weight: float = 0.0
    upside_base: float | None = None


class ScenarioComparisonTable(BaseModel):
    rows: list[ScenarioComparisonRow] = Field(default_factory=list)


# =========================================================================
# Full Overview Result
# =========================================================================

class ModelOverviewResult(BaseModel):
    ticker: str
    current_price: float = 0.0
    football_field: FootballFieldResult = Field(default_factory=FootballFieldResult)
    model_weights: ModelWeightResult = Field(default_factory=ModelWeightResult)
    agreement: AgreementAnalysis = Field(default_factory=AgreementAnalysis)
    scenario_table: ScenarioComparisonTable = Field(default_factory=ScenarioComparisonTable)
    composite_bear: float = 0.0
    composite_base: float = 0.0
    composite_bull: float = 0.0
    composite_upside_pct: float | None = None
    included_models: list[str] = Field(default_factory=list)
    excluded_models: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
