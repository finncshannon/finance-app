/* TypeScript types for Sensitivity Analysis & Model Overview API responses. */

// =========================================================================
// Model Overview
// =========================================================================

export interface FootballFieldRow {
  model_name: string;
  bear_price: number;
  base_price: number;
  bull_price: number;
  weight: number;
  confidence_score: number | null;
}

export interface FootballFieldResult {
  models: FootballFieldRow[];
  composite: FootballFieldRow | null;
  current_price: number;
  chart_min: number;
  chart_max: number;
}

export interface ModelWeightResult {
  weights: Record<string, number>;
  raw_scores: Record<string, number>;
  multipliers: Record<string, number>;
  adjusted_scores: Record<string, number>;
  excluded_models: string[];
  included_model_count: number;
}

export interface DivergencePair {
  model_a: string;
  model_b: string;
  divergence_pct: number;
}

export interface DivergenceMatrix {
  pairs: DivergencePair[];
  closest_pair: DivergencePair | null;
  most_divergent_pair: DivergencePair | null;
}

export interface AgreementAnalysis {
  level: string;
  max_spread: number | null;
  max_spread_pct: number | null;
  highest_model: string | null;
  highest_price: number | null;
  lowest_model: string | null;
  lowest_price: number | null;
  reasoning: string;
  divergence_matrix: DivergenceMatrix | null;
}

export interface ScenarioComparisonRow {
  model_name: string;
  bear: number;
  base: number;
  bull: number;
  confidence: number | null;
  weight: number;
  upside_base: number | null;
}

export interface ScenarioComparisonTable {
  rows: ScenarioComparisonRow[];
}

export interface ModelOverviewResult {
  ticker: string;
  current_price: number;
  football_field: FootballFieldResult;
  model_weights: ModelWeightResult;
  agreement: AgreementAnalysis;
  scenario_table: ScenarioComparisonTable;
  composite_bear: number;
  composite_base: number;
  composite_bull: number;
  composite_upside_pct: number | null;
  included_models: string[];
  excluded_models: string[];
  warnings: string[];
}

// =========================================================================
// Sensitivity Analysis
// =========================================================================

export interface SensitivityParameterDef {
  name: string;
  key_path: string;
  param_type: string;
  min_val: number;
  max_val: number;
  step: number;
  display_format: string;
  current_value: number | null;
}

export interface SliderResult {
  implied_price: number;
  delta_from_base: number;
  delta_pct: number;
  enterprise_value: number;
  overrides_applied: Record<string, number>;
  constraints_enforced: string[];
  computation_time_ms: number;
}

export interface TornadoBar {
  variable_name: string;
  variable_key: string;
  base_value: number;
  low_input: number;
  high_input: number;
  price_at_low_input: number;
  price_at_high_input: number;
  spread: number;
  base_price: number;
}

export interface TornadoResult {
  bars: TornadoBar[];
  base_price: number;
  current_price: number;
  variable_count: number;
  computation_time_ms: number;
}

export interface MCStatistics {
  mean: number;
  median: number;
  std_dev: number;
  p5: number;
  p10: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
  p95: number;
  prob_upside: number;
  prob_upside_15pct: number;
  prob_downside_15pct: number;
  var_5pct: number;
}

export interface HistogramBin {
  bin_start: number;
  bin_end: number;
  count: number;
  frequency: number;
}

export interface MCHistogram {
  bins: HistogramBin[];
  bin_count: number;
  range_min: number;
  range_max: number;
  outlier_count_low: number;
  outlier_count_high: number;
}

export interface MonteCarloResult {
  success: boolean;
  error: string | null;
  statistics: MCStatistics | null;
  histogram: MCHistogram | null;
  iteration_count: number;
  valid_iterations: number;
  skipped_iterations: number;
  seed: number | null;
  computation_time_ms: number;
}

export interface Table2DResult {
  row_variable: string;
  col_variable: string;
  row_values: number[];
  col_values: number[];
  price_matrix: number[][];
  upside_matrix: number[][];
  color_matrix: string[][];
  base_row_index: number;
  base_col_index: number;
  base_price: number;
  current_price: number;
  grid_size: number;
  computation_time_ms: number;
}

// =========================================================================
// DCF Engine
// =========================================================================

export interface DCFYearRow {
  year: number;
  revenue: number;
  revenue_growth: number;
  cogs: number;
  gross_profit: number;
  gross_margin: number;
  opex: number;
  ebit: number;
  operating_margin: number;
  da: number;
  ebitda: number;
  ebitda_margin: number;
  taxes: number;
  nopat: number;
  capex: number;
  nwc_change: number;
  fcf: number;
  fcf_margin: number;
  discount_factor: number;
  pv_fcf: number;
}

export interface WaterfallStep {
  label: string;
  value: number;
  step_type: string;
}

export interface DCFScenarioResult {
  scenario_name: string;
  scenario_weight: number;
  projection_table: DCFYearRow[];
  enterprise_value: number;
  pv_fcf_total: number;
  pv_terminal_value: number;
  tv_pct_of_ev: number;
  equity_value: number;
  implied_price: number;
  upside_downside_pct: number | null;
  wacc: number;
  terminal_growth_rate: number;
  terminal_exit_multiple: number | null;
}

export interface DCFResult {
  ticker: string;
  current_price: number;
  model_type: string;
  scenarios: Record<string, DCFScenarioResult>;
  weighted_implied_price: number;
  weighted_enterprise_value: number;
  weighted_upside_downside_pct: number | null;
  waterfall: { steps: WaterfallStep[] };
  metadata: { projection_years: number; terminal_method: string; warnings: string[] };
}

// =========================================================================
// DDM Engine
// =========================================================================

export interface DividendYearRow {
  year: number;
  stage: string;
  dps: number;
  growth_rate: number;
  discount_factor: number;
  pv: number;
}

export interface SustainabilityMetric {
  name: string;
  value: number | null;
  status: string;
  description: string;
}

export interface DDMScenarioResult {
  scenario_name: string;
  scenario_weight: number;
  intrinsic_value_per_share: number;
  upside_downside_pct: number | null;
  pv_stage1: number;
  pv_stage2: number | null;
  pv_terminal: number;
  tv_pct_of_total: number;
  dividend_growth_near_term: number;
  dividend_growth_terminal: number;
  dividend_schedule: DividendYearRow[];
}

export interface DDMResult {
  ticker: string;
  applicable: boolean;
  reason: string | null;
  current_price: number;
  model_type: string;
  scenarios: Record<string, DDMScenarioResult>;
  weighted_intrinsic_value: number;
  weighted_upside_downside_pct: number | null;
  sustainability: { metrics: SustainabilityMetric[]; overall_health: string };
  metadata: { ddm_variant: string; cost_of_equity: number; warnings: string[] };
}

// =========================================================================
// Comps Engine
// =========================================================================

export interface CompsTableRow {
  ticker: string;
  company_name: string;
  market_cap: number;
  enterprise_value: number;
  pe: number | null;
  ev_ebitda: number | null;
  ev_revenue: number | null;
  pb: number | null;
  p_fcf: number | null;
  revenue_growth: number | null;
  operating_margin: number | null;
  outlier_flags: Record<string, boolean>;
  peer_score: number;
}

export interface MultipleStats {
  mean: number;
  median: number;
  trimmed_mean: number;
  min: number;
  max: number;
  count: number;
}

export interface ImpliedValue {
  raw_implied_price: number;
  quality_adjusted_price: number;
  multiple_used: number;
  target_metric_used: number;
  upside_downside_pct: number | null;
}

export interface CompsFootballFieldRange {
  method: string;
  low: number;
  mid: number;
  high: number;
  adjusted_mid: number;
}

export interface CompsResult {
  ticker: string;
  current_price: number;
  model_type: string;
  status: string; // "ready" | "no_peers" | "error"
  peer_group: { peers: CompsTableRow[]; count: number };
  aggregate_multiples: Record<string, MultipleStats | null>;
  implied_values: Record<string, ImpliedValue | null>;
  quality_assessment: { factor_scores: Record<string, number>; composite_adjustment: number };
  football_field: { current_price: number; ranges: CompsFootballFieldRange[] };
  weighted_implied_price: number;
  metadata: { warnings: string[] };
}

// =========================================================================
// Revenue-Based Engine
// =========================================================================

export interface RevBasedScenarioResult {
  scenario_name: string;
  scenario_weight: number;
  projected_revenue: number[];
  revenue_growth_rates: number[];
  multiples_by_year: number[];
  primary_implied_price: number;
  avg_exit_price: number;
  upside_downside_pct: number | null;
}

export interface RevBasedResult {
  ticker: string;
  current_price: number;
  model_type: string;
  scenarios: Record<string, RevBasedScenarioResult>;
  weighted_implied_price: number;
  weighted_upside_downside_pct: number | null;
  growth_metrics: {
    rule_of_40: { score: number; status: string; revenue_growth_component: number; margin_component: number };
    ev_arr: number | null;
    magic_number: number | null;
    magic_number_status: string | null;
    psg_ratio: number | null;
  };
  metadata: { warnings: string[] };
}

// =========================================================================
// Assumption Engine
// =========================================================================

export interface ScenarioProjections {
  revenue_growth_rates: number[];
  terminal_growth_rate: number;
  gross_margins: number[];
  operating_margins: number[];
  ebitda_margins: number[];
  net_margins: number[];
  fcf_margins: number[];
  wacc: number;
  cost_of_equity: number;
  capex_to_revenue: number;
  nwc_change_to_revenue: number;
  tax_rate: number;
  scenario_weight: number;
}

export interface ScenarioSet {
  base: ScenarioProjections;
  bull: ScenarioProjections;
  bear: ScenarioProjections;
  uncertainty_score: number;
  spread: number;
}

export interface DCFAssumptions {
  projection_years: number;
  revenue_growth_rates: number[];
  operating_margins: number[];
  tax_rate: number;
  wacc: number;
  terminal_growth_rate: number;
  capex_to_revenue: number;
  depreciation_to_revenue: number;
  nwc_change_to_revenue: number;
  terminal_method: string;
  terminal_exit_multiple: number | null;
  shares_outstanding: number | null;
  net_debt: number | null;
  base_revenue: number | null;
}

export interface DDMAssumptions {
  current_annual_dividend_per_share: number;
  dividend_growth_rate_near_term: number;
  dividend_growth_rate_terminal: number;
  cost_of_equity: number;
  payout_ratio_current: number | null;
  model_type: string;
}

export interface ConfidenceDetail {
  category: string;
  score: number;
  reasoning: string;
}

export interface WACCBreakdown {
  wacc: number;
  cost_of_equity: number;
  cost_of_debt_pre_tax: number;
  cost_of_debt_after_tax: number;
  risk_free_rate: number;
  adjusted_beta: number;
  raw_beta: number;
  erp: number;
  size_premium: number;
  effective_tax_rate: number;
  weight_equity: number;
  weight_debt: number;
  market_cap: number | null;
  total_debt: number | null;
  warnings: string[];
}

export interface AssumptionSet {
  ticker: string;
  generated_at: string;
  data_quality_score: number;
  years_of_data: number;
  overrides_applied: string[];
  scenarios: ScenarioSet | null;
  model_assumptions: {
    dcf: DCFAssumptions | null;
    ddm: DDMAssumptions | null;
    comps: Record<string, unknown> | null;
    revenue_based: Record<string, unknown> | null;
  };
  wacc_breakdown: WACCBreakdown | null;
  confidence: { overall_score: number; details: ConfidenceDetail[] } | null;
  reasoning: Record<string, string>;
  metadata: { regime: string; uncertainty_score: number; data_gaps: string[]; warnings: string[] };
}

// =========================================================================
// Data Readiness
// =========================================================================

export interface FieldReadiness {
  field: string;
  label: string;
  status: 'present' | 'missing' | 'derived';
  years_available: number;
  source: string | null;
  reason: string;
}

export interface EngineReadiness {
  verdict: 'ready' | 'partial' | 'not_possible';
  verdict_label: string;
  detection_score: number | null;
  critical_fields: FieldReadiness[];
  important_fields: FieldReadiness[];
  helpful_fields: FieldReadiness[];
  missing_impact: string | null;
  notes: string[];
}

export interface FieldMetadataEntry {
  status: 'present' | 'missing' | 'derived';
  source: string | null;
  source_detail: string | null;
  years_available: number;
  engines: { engine: string; level: string; reason: string }[];
}

export interface DetectionSummary {
  recommended_model: string;
  confidence: string;
  confidence_percentage: number;
}

export interface DataReadinessResult {
  ticker: string;
  data_years_available: number;
  total_fields: number;
  populated_fields: number;
  coverage_pct: number;
  engines: Record<string, EngineReadiness>;
  field_metadata: Record<string, FieldMetadataEntry>;
  detection_result: DetectionSummary | null;
}

// =========================================================================
// Version History
// =========================================================================

export interface ModelVersion {
  id: number;
  model_id: number;
  version_number: number;
  annotation: string | null;
  snapshot_size_bytes: number | null;
  created_at: string;
  snapshot_blob?: string;
  snapshot?: Record<string, unknown>;
}
