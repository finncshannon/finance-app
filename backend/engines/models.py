"""Pydantic output models for all 4 valuation engines."""

from __future__ import annotations

from pydantic import BaseModel, Field, computed_field


# =========================================================================
# DCF Models
# =========================================================================

class DCFYearRow(BaseModel):
    year: int
    revenue: float
    revenue_growth: float
    cogs: float
    gross_profit: float
    gross_margin: float
    opex: float
    ebit: float
    operating_margin: float
    da: float
    ebitda: float
    ebitda_margin: float
    taxes: float
    nopat: float
    capex: float
    nwc_change: float
    fcf: float
    fcf_margin: float
    discount_factor: float
    pv_fcf: float


class WaterfallStep(BaseModel):
    label: str
    value: float
    step_type: str  # "start" | "addition" | "subtraction" | "subtotal" | "end"


class DCFWaterfall(BaseModel):
    steps: list[WaterfallStep] = Field(default_factory=list)


class DCFScenarioResult(BaseModel):
    scenario_name: str
    scenario_weight: float
    projection_table: list[DCFYearRow] = Field(default_factory=list)
    enterprise_value: float = 0.0
    pv_fcf_total: float = 0.0
    pv_terminal_value: float = 0.0
    tv_pct_of_ev: float = 0.0
    equity_value: float = 0.0
    implied_price: float = 0.0
    upside_downside_pct: float | None = None
    wacc: float = 0.0
    terminal_growth_rate: float = 0.0
    terminal_exit_multiple: float | None = None


class DCFMetadata(BaseModel):
    projection_years: int = 10
    terminal_method: str = "perpetuity_growth"
    tv_perpetuity: float = 0.0
    tv_exit_multiple: float | None = None
    tv_delta: float | None = None
    tv_delta_pct: float | None = None
    warnings: list[str] = Field(default_factory=list)


class DCFResult(BaseModel):
    ticker: str
    current_price: float
    model_type: str = "dcf"
    scenarios: dict[str, DCFScenarioResult] = Field(default_factory=dict)
    weighted_implied_price: float = 0.0
    weighted_enterprise_value: float = 0.0
    weighted_upside_downside_pct: float | None = None
    waterfall: DCFWaterfall = Field(default_factory=DCFWaterfall)
    metadata: DCFMetadata = Field(default_factory=DCFMetadata)


# =========================================================================
# DDM Models
# =========================================================================

class DividendYearRow(BaseModel):
    year: int
    stage: str  # "high_growth" | "transition" | "terminal"
    dps: float
    growth_rate: float
    discount_factor: float
    pv: float


class SustainabilityMetric(BaseModel):
    name: str
    value: float | None = None
    status: str  # "green" | "yellow" | "red"
    description: str = ""


class DividendSustainability(BaseModel):
    metrics: list[SustainabilityMetric] = Field(default_factory=list)
    overall_health: str = "caution"  # "healthy" | "caution" | "at_risk"


class DDMScenarioResult(BaseModel):
    scenario_name: str
    scenario_weight: float
    intrinsic_value_per_share: float = 0.0
    upside_downside_pct: float | None = None
    pv_stage1: float = 0.0
    pv_stage2: float | None = None
    pv_terminal: float = 0.0
    tv_pct_of_total: float = 0.0
    dividend_growth_near_term: float = 0.0
    dividend_growth_terminal: float = 0.0
    dividend_schedule: list[DividendYearRow] = Field(default_factory=list)


class DDMMetadata(BaseModel):
    ddm_variant: str = "two_stage"
    cost_of_equity: float = 0.0
    warnings: list[str] = Field(default_factory=list)


class DDMResult(BaseModel):
    ticker: str
    applicable: bool = True
    reason: str | None = None
    current_price: float = 0.0
    model_type: str = "ddm"
    scenarios: dict[str, DDMScenarioResult] = Field(default_factory=dict)
    weighted_intrinsic_value: float = 0.0
    weighted_upside_downside_pct: float | None = None
    sustainability: DividendSustainability = Field(default_factory=DividendSustainability)
    metadata: DDMMetadata = Field(default_factory=DDMMetadata)


# =========================================================================
# Comps Models
# =========================================================================

class CompsTableRow(BaseModel):
    ticker: str
    company_name: str = ""
    market_cap: float = 0.0
    enterprise_value: float = 0.0
    revenue: float = 0.0
    ebitda: float = 0.0
    net_income: float = 0.0
    fcf: float = 0.0
    book_value: float = 0.0
    pe: float | None = None
    ev_ebitda: float | None = None
    ev_revenue: float | None = None
    pb: float | None = None
    p_fcf: float | None = None
    revenue_growth: float | None = None
    operating_margin: float | None = None
    roe: float | None = None
    outlier_flags: dict[str, bool] = Field(default_factory=dict)
    peer_score: float = 0.0


class MultipleStats(BaseModel):
    mean: float = 0.0
    median: float = 0.0
    trimmed_mean: float = 0.0
    min: float = 0.0
    max: float = 0.0
    count: int = 0


class ImpliedValue(BaseModel):
    raw_implied_price: float = 0.0
    quality_adjusted_price: float = 0.0
    multiple_used: float = 0.0
    target_metric_used: float = 0.0
    upside_downside_pct: float | None = None


class FootballFieldRange(BaseModel):
    method: str
    low: float = 0.0
    mid: float = 0.0
    high: float = 0.0
    adjusted_mid: float = 0.0


class FootballField(BaseModel):
    current_price: float = 0.0
    ranges: list[FootballFieldRange] = Field(default_factory=list)


class QualityAssessment(BaseModel):
    factor_scores: dict[str, float] = Field(default_factory=dict)
    composite_adjustment: float = 0.0


class CompsMetadata(BaseModel):
    warnings: list[str] = Field(default_factory=list)


class CompsResult(BaseModel):
    ticker: str
    current_price: float = 0.0
    model_type: str = "comps"
    status: str = "ready"  # "ready" | "no_peers" | "error"
    peer_group: dict = Field(default_factory=lambda: {"peers": [], "count": 0})
    aggregate_multiples: dict[str, MultipleStats | None] = Field(default_factory=dict)
    implied_values: dict[str, ImpliedValue | None] = Field(default_factory=dict)
    quality_assessment: QualityAssessment = Field(default_factory=QualityAssessment)
    football_field: FootballField = Field(default_factory=FootballField)
    metadata: CompsMetadata = Field(default_factory=CompsMetadata)

    @computed_field
    @property
    def weighted_implied_price(self) -> float:
        """Quality-adjusted midpoint from football field for DB storage."""
        if self.football_field and self.football_field.ranges:
            adj_mids = [r.adjusted_mid for r in self.football_field.ranges if r.adjusted_mid > 0]
            if adj_mids:
                return round(sum(adj_mids) / len(adj_mids), 2)
        # Fallback: average of all non-None quality-adjusted prices
        prices = []
        for iv in self.implied_values.values():
            if iv is not None and iv.quality_adjusted_price > 0:
                prices.append(iv.quality_adjusted_price)
        return round(sum(prices) / len(prices), 2) if prices else 0.0


# =========================================================================
# Revenue-Based Models
# =========================================================================

class ExitYearResult(BaseModel):
    exit_year: int
    exit_revenue: float = 0.0
    exit_multiple: float = 0.0
    exit_ev: float = 0.0
    discount_factor: float = 0.0
    pv_exit_ev: float = 0.0
    pv_equity: float = 0.0
    implied_price: float = 0.0


class RevBasedScenarioResult(BaseModel):
    scenario_name: str
    scenario_weight: float
    projected_revenue: list[float] = Field(default_factory=list)
    revenue_growth_rates: list[float] = Field(default_factory=list)
    multiples_by_year: list[float] = Field(default_factory=list)
    terminal_ev_revenue: float = 0.0
    exit_valuations: list[ExitYearResult] = Field(default_factory=list)
    primary_implied_price: float = 0.0
    avg_exit_price: float = 0.0
    current_multiple_price: float | None = None
    upside_downside_pct: float | None = None


class RuleOf40(BaseModel):
    score: float = 0.0
    status: str = "fail"
    revenue_growth_component: float = 0.0
    margin_component: float = 0.0


class GrowthMetrics(BaseModel):
    rule_of_40: RuleOf40 = Field(default_factory=RuleOf40)
    ev_arr: float | None = None
    magic_number: float | None = None
    magic_number_status: str | None = None
    psg_ratio: float | None = None


class RevBasedMetadata(BaseModel):
    multiple_direction: str = "stable"
    warnings: list[str] = Field(default_factory=list)


class RevBasedResult(BaseModel):
    ticker: str
    current_price: float = 0.0
    model_type: str = "revenue_based"
    scenarios: dict[str, RevBasedScenarioResult] = Field(default_factory=dict)
    weighted_implied_price: float = 0.0
    weighted_upside_downside_pct: float | None = None
    growth_metrics: GrowthMetrics = Field(default_factory=GrowthMetrics)
    profitability_trajectory: dict = Field(default_factory=dict)
    metadata: RevBasedMetadata = Field(default_factory=RevBasedMetadata)
