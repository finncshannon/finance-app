"""Pydantic models for Assumption Engine input/output structures."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# CompanyDataPackage (GATHER stage output)
# ---------------------------------------------------------------------------

class CompanyProfile(BaseModel):
    sector: str = "Unknown"
    industry: str = "Unknown"
    market_cap: float | None = None
    employee_count: int | None = None
    country: str = "US"


class QuoteData(BaseModel):
    current_price: float | None = None
    beta: float | None = None
    market_cap: float | None = None
    forward_pe: float | None = None
    trailing_pe: float | None = None
    price_to_book: float | None = None
    enterprise_value: float | None = None
    ev_to_ebitda: float | None = None
    ev_to_revenue: float | None = None
    dividend_yield: float | None = None
    payout_ratio: float | None = None


class AnalystEstimates(BaseModel):
    revenue_estimate_current_year: float | None = None
    revenue_estimate_next_year: float | None = None
    earnings_estimate_current_year: float | None = None
    earnings_estimate_next_year: float | None = None
    revenue_growth_estimate: float | None = None
    earnings_growth_5yr: float | None = None


class IndustryBenchmarks(BaseModel):
    median_gross_margin: float | None = None
    median_operating_margin: float | None = None
    median_net_margin: float | None = None
    median_ebitda_margin: float | None = None
    median_fcf_margin: float | None = None
    median_ev_ebitda: float | None = None
    median_pe: float | None = None
    median_ps: float | None = None
    median_pb: float | None = None
    median_beta: float | None = None
    median_revenue_growth: float | None = None


class CompanyDataPackage(BaseModel):
    ticker: str
    company_profile: CompanyProfile
    annual_financials: list[dict] = Field(default_factory=list)  # oldest→newest
    years_available: int = 0
    quote_data: QuoteData = Field(default_factory=QuoteData)
    analyst_estimates: AnalystEstimates = Field(default_factory=AnalystEstimates)
    industry_benchmarks: IndustryBenchmarks = Field(default_factory=IndustryBenchmarks)
    risk_free_rate: float = 0.04


# ---------------------------------------------------------------------------
# ANALYZE stage outputs
# ---------------------------------------------------------------------------

class RevenueProjection(BaseModel):
    base_growth_rates: list[float]         # 5 values
    terminal_growth_rate: float
    regime: str
    regime_transition: bool = False
    starting_growth_rate: float
    historical_cagrs: dict[int, float] = Field(default_factory=dict)
    growth_volatility: float = 0.0
    analyst_available: bool = False
    divergence_flag: bool = False
    divergence_type: str | None = None


class MarginLensResult(BaseModel):
    margin_type: str
    projections: list[float]               # 5 values
    lens_outputs: dict[str, list[float]] = Field(default_factory=dict)
    weights_used: dict[str, float] = Field(default_factory=dict)
    trend_r_squared: float | None = None
    outlier_years: list[int] = Field(default_factory=list)
    current_margin: float | None = None
    historical_mean: float | None = None
    industry_median: float | None = None


class WACCResult(BaseModel):
    wacc: float
    cost_of_equity: float
    cost_of_debt_pre_tax: float = 0.0
    cost_of_debt_after_tax: float = 0.0
    risk_free_rate: float
    adjusted_beta: float
    raw_beta: float
    erp: float
    size_premium: float
    effective_tax_rate: float
    weight_equity: float
    weight_debt: float
    market_cap: float | None = None
    total_debt: float | None = None
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# SYNTHESIZE stage outputs
# ---------------------------------------------------------------------------

class ScenarioProjections(BaseModel):
    """Single scenario (base, bull, or bear)."""
    revenue_growth_rates: list[float]      # 5 values
    terminal_growth_rate: float
    gross_margins: list[float]
    operating_margins: list[float]
    ebitda_margins: list[float]
    net_margins: list[float]
    fcf_margins: list[float]
    wacc: float
    cost_of_equity: float
    capex_to_revenue: float
    nwc_change_to_revenue: float
    tax_rate: float
    scenario_weight: float


class ScenarioSet(BaseModel):
    base: ScenarioProjections
    bull: ScenarioProjections
    bear: ScenarioProjections
    uncertainty_score: float
    spread: float


# ---------------------------------------------------------------------------
# Model-specific assumptions (Design Section 6)
# ---------------------------------------------------------------------------

class DCFAssumptions(BaseModel):
    projection_years: int = 5
    revenue_growth_rates: list[float]
    operating_margins: list[float]
    tax_rate: float
    wacc: float
    terminal_growth_rate: float
    capex_to_revenue: float
    depreciation_to_revenue: float
    nwc_change_to_revenue: float
    terminal_method: str = "perpetuity_growth"
    terminal_exit_multiple: float | None = None
    shares_outstanding: float | None = None
    net_debt: float | None = None
    base_revenue: float | None = None


class DDMAssumptions(BaseModel):
    current_annual_dividend_per_share: float
    dividend_growth_rate_near_term: float
    dividend_growth_rate_terminal: float
    cost_of_equity: float
    payout_ratio_current: float | None = None
    payout_ratio_projected: float | None = None
    model_type: str = "gordon"             # "gordon" or "two_stage"
    shares_outstanding: float | None = None


class CompsAssumptions(BaseModel):
    applicable_multiples: dict[str, float] = Field(default_factory=dict)
    peer_selection_criteria: dict = Field(default_factory=dict)
    premium_discount: dict[str, float] = Field(default_factory=dict)


class RevenueBasedAssumptions(BaseModel):
    base_revenue: float | None = None
    revenue_growth_rates: list[float] = Field(default_factory=list)
    current_ev_revenue: float | None = None
    terminal_ev_revenue: float | None = None
    growth_adjusted_multiple: float | None = None
    enterprise_value: float | None = None
    net_debt: float | None = None
    shares_outstanding: float | None = None


class ModelAssumptions(BaseModel):
    dcf: DCFAssumptions | None = None
    ddm: DDMAssumptions | None = None
    comps: CompsAssumptions | None = None
    revenue_based: RevenueBasedAssumptions | None = None


# ---------------------------------------------------------------------------
# Confidence & Reasoning
# ---------------------------------------------------------------------------

class ConfidenceDetail(BaseModel):
    category: str
    score: float                           # 0–100
    reasoning: str


class AssumptionConfidence(BaseModel):
    overall_score: float                   # 0–100
    details: list[ConfidenceDetail] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Final OUTPUT: AssumptionSet
# ---------------------------------------------------------------------------

class AssumptionMetadata(BaseModel):
    regime: str = "unknown"
    uncertainty_score: float = 0.5
    data_gaps: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AssumptionSet(BaseModel):
    ticker: str
    generated_at: datetime
    data_quality_score: float = 0.0
    years_of_data: int = 0
    overrides_applied: list[str] = Field(default_factory=list)

    scenarios: ScenarioSet | None = None
    model_assumptions: ModelAssumptions = Field(default_factory=ModelAssumptions)
    wacc_breakdown: WACCResult | None = None
    confidence: AssumptionConfidence | None = None
    reasoning: dict[str, str] = Field(default_factory=dict)
    metadata: AssumptionMetadata = Field(default_factory=AssumptionMetadata)


# ---------------------------------------------------------------------------
# Monte Carlo Types (Session 8G)
# ---------------------------------------------------------------------------

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
