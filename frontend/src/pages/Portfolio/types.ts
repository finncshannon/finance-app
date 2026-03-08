/** Portfolio TypeScript interfaces — mirrors backend Pydantic models. */

// ─── Account ─────────────────────────────────────────────
export interface Account {
  id: number;
  name: string;
  account_type: string;
  is_default: boolean;
  created_at: string;
}

export interface AccountCreate {
  name: string;
  account_type?: string;
  is_default?: boolean;
}

// ─── Position ────────────────────────────────────────────
export interface Position {
  id: number;
  ticker: string;
  company_name: string | null;
  shares_held: number;
  cost_basis_per_share: number | null;
  current_price: number | null;
  market_value: number | null;
  total_cost: number | null;
  gain_loss: number | null;
  gain_loss_pct: number | null;
  day_change: number | null;
  day_change_pct: number | null;
  weight: number | null;
  sector: string | null;
  industry: string | null;
  account: string;
  added_at: string;
  lots: Lot[];
}

export interface PositionCreate {
  ticker: string;
  shares: number;
  cost_basis_per_share: number;
  date_acquired?: string;
  account?: string;
  notes?: string | null;
}

// ─── Lot ─────────────────────────────────────────────────
export interface Lot {
  id: number;
  position_id: number;
  shares: number;
  cost_basis_per_share: number;
  date_acquired: string;
  date_sold: string | null;
  sale_price: number | null;
  realized_gain: number | null;
  holding_period_days: number | null;
  is_long_term: boolean | null;
  lot_method: string | null;
  notes: string | null;
}

// ─── Transaction ─────────────────────────────────────────
export interface Transaction {
  id: number;
  ticker: string;
  transaction_type: string;
  shares: number | null;
  price_per_share: number | null;
  total_amount: number | null;
  transaction_date: string;
  account: string | null;
  fees: number;
  notes: string | null;
  created_at: string;
}

export interface TransactionCreate {
  ticker: string;
  transaction_type: string;
  shares?: number | null;
  price_per_share?: number | null;
  total_amount?: number | null;
  transaction_date: string;
  account?: string | null;
  fees?: number;
  notes?: string | null;
  lot_method?: string;
  specific_lot_ids?: number[] | null;
}

// ─── Alert ───────────────────────────────────────────────
export interface Alert {
  id: number;
  ticker: string;
  alert_type: string;
  threshold: number;
  is_active: boolean;
  triggered_at: string | null;
  created_at: string;
  current_price: number | null;
}

export interface AlertCreate {
  ticker: string;
  alert_type: string;
  threshold: number;
}

// ─── Summary ─────────────────────────────────────────────
export interface PortfolioSummary {
  total_value: number;
  total_cost: number;
  total_gain_loss: number;
  total_gain_loss_pct: number;
  day_change: number;
  day_change_pct: number;
  position_count: number;
  account_count: number;
  weighted_dividend_yield: number | null;
}

// ─── Performance ─────────────────────────────────────────
export interface DailySnapshot {
  date: string;
  portfolio_value: number;
  cash_flow: number;
}

export interface PerformanceResult {
  twr: Record<string, number | null>;
  mwrr: number | null;
  mwrr_annualized: number | null;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  max_drawdown: number | null;
  beta: number | null;
  volatility: number | null;
  tracking_error: number | null;
  information_ratio: number | null;
  daily_values: DailySnapshot[];
}

// ─── Benchmark ───────────────────────────────────────────
export interface BenchmarkPeriod {
  portfolio: number | null;
  benchmark: number | null;
  alpha: number | null;
}

export interface BenchmarkResult {
  benchmark_ticker: string;
  periods: Record<string, BenchmarkPeriod>;
  portfolio_series: DailySnapshot[];
  benchmark_series: DailySnapshot[];
}

// ─── Attribution ─────────────────────────────────────────
export interface SectorAttribution {
  sector: string;
  port_weight: number;
  bench_weight: number;
  port_return: number;
  bench_return: number;
  allocation_effect: number;
  selection_effect: number;
  interaction_effect: number;
}

export interface AttributionResult {
  sectors: SectorAttribution[];
  total_allocation: number;
  total_selection: number;
  total_interaction: number;
  total_alpha: number;
}

// ─── Income ──────────────────────────────────────────────
export interface IncomePosition {
  ticker: string;
  shares: number;
  dividend_rate: number;
  dividend_yield: number;
  annual_income: number;
  monthly_income: number;
}

export interface IncomeResult {
  total_annual_income: number;
  total_monthly_income: number;
  weighted_yield: number | null;
  positions: IncomePosition[];
}

// Enhanced income (from 10E backend)
export interface EnhancedIncomePosition {
  ticker: string;
  shares: number;
  dividend_rate: number;
  annual_income: number;
  monthly_income: number;
  cost_basis_per_share: number;
  yield_on_cost: number | null;
  market_yield: number | null;
  current_price: number;
}

export interface EnhancedIncomeSummary {
  total_annual_income: number;
  total_monthly_income: number;
  projected_annual_income: number;
  yield_on_cost: number | null;
  yield_on_market: number | null;
  dividend_position_count: number;
  total_position_count: number;
}

export interface EnhancedIncomeResult {
  positions: EnhancedIncomePosition[];
  summary: EnhancedIncomeSummary;
}

export interface UpcomingDividendEvent {
  ticker: string;
  event_type: string;
  event_date: string;
  amount_per_share: number | null;
  shares_held: number;
  expected_income: number | null;
}

// ─── Import ──────────────────────────────────────────────
export interface ImportPreview {
  positions: PositionCreate[];
  account_count: number;
  warnings: string[];
  row_count: number;
}

export interface ImportResult {
  imported: number;
  skipped: number;
  warnings: string[];
}

// ─── Formatters ──────────────────────────────────────────

export function fmtDollar(n: number | null | undefined): string {
  if (n == null) return '—';
  const abs = Math.abs(n);
  const formatted = abs.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return n >= 0 ? `$${formatted}` : `-$${formatted}`;
}

export function fmtSignedDollar(n: number | null | undefined): string {
  if (n == null) return '—';
  const abs = Math.abs(n);
  const formatted = abs.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return n >= 0 ? `+$${formatted}` : `-$${formatted}`;
}

export function fmtPct(n: number | null | undefined): string {
  if (n == null) return '—';
  const sign = n >= 0 ? '+' : '';
  return `${sign}${(n * 100).toFixed(1)}%`;
}

export function fmtShares(n: number): string {
  return n % 1 === 0 ? n.toLocaleString() : n.toFixed(4);
}

export function gainColor(n: number | null | undefined): string {
  if (n == null || n === 0) return 'var(--text-secondary)';
  return n > 0 ? 'var(--color-positive)' : 'var(--color-negative)';
}

export function fmtHoldingPeriod(days: number | null): string {
  if (days == null) return '—';
  const years = Math.floor(days / 365);
  const months = Math.floor((days % 365) / 30);
  if (years > 0) return `${years}y ${months}m`;
  if (months > 0) return `${months}m`;
  return `${days}d`;
}
