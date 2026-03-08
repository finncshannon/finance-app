/** Research TypeScript interfaces — mirrors backend research_service responses. */

// ─── Filing Types ────────────────────────────────────────
export interface FilingSummary {
  id: number;
  ticker: string;
  form_type: string;
  filing_date: string;
  accession_number: string | null;
}

export interface FilingSection {
  id: number;
  filing_id: number;
  section_key: string;
  section_title: string;
  content_text: string;
  word_count: number | null;
}

// ─── Financial Statement Types ───────────────────────────
export interface FinancialRow {
  fiscal_year: number;
  period_type: string;
  revenue: number | null;
  cost_of_revenue: number | null;
  gross_profit: number | null;
  operating_expense: number | null;
  rd_expense: number | null;
  sga_expense: number | null;
  ebit: number | null;
  interest_expense: number | null;
  tax_provision: number | null;
  net_income: number | null;
  ebitda: number | null;
  eps_basic: number | null;
  eps_diluted: number | null;
  total_assets: number | null;
  current_assets: number | null;
  cash_and_equivalents: number | null;
  total_liabilities: number | null;
  current_liabilities: number | null;
  long_term_debt: number | null;
  total_debt: number | null;
  stockholders_equity: number | null;
  operating_cash_flow: number | null;
  capital_expenditure: number | null;
  free_cash_flow: number | null;
  dividends_paid: number | null;
  shares_outstanding: number | null;
  investing_cash_flow: number | null;
  financing_cash_flow: number | null;
  working_capital: number | null;
  net_debt: number | null;
  gross_margin: number | null;
  operating_margin: number | null;
  net_margin: number | null;
  ebitda_margin: number | null;
  fcf_margin: number | null;
  revenue_growth: number | null;
  roe: number | null;
  debt_to_equity: number | null;
  depreciation_amortization: number | null;
  payout_ratio: number | null;
  [key: string]: number | string | null;
}

// ─── Profile Types ───────────────────────────────────────
export interface CompanyProfile {
  ticker: string;
  company_name: string;
  sector: string;
  industry: string;
  exchange: string;
  description: string | null;
  employees: number | null;
  country: string | null;
  website: string | null;
  quote?: {
    current_price: number;
    day_change: number;
    day_change_pct: number;
    fifty_two_week_high: number;
    fifty_two_week_low: number;
    market_cap: number;
    volume: number;
    beta: number;
  };
  metrics?: Record<string, number | null>;
  upcoming_events?: Array<{
    event_type: string;
    event_date: string;
    description: string;
  }>;
}

// ─── Ratio Types ─────────────────────────────────────────
export interface RatioGroup {
  [metricName: string]: number | null;
}

export interface RatioData {
  profitability: RatioGroup;
  returns: RatioGroup;
  leverage: RatioGroup;
  liquidity: RatioGroup;
  valuation: RatioGroup;
  efficiency: RatioGroup;
  growth: RatioGroup;
}

export interface RatioHistoryPoint {
  fiscal_year: number;
  value: number | null;
}

// ─── Research Notes ──────────────────────────────────────
export interface ResearchNote {
  id: number;
  ticker: string;
  note_text: string;
  note_type: string;
  created_at: string;
  updated_at: string | null;
}

// ─── Peer ────────────────────────────────────────────────
export interface PeerCompany {
  ticker: string;
  company_name: string | null;
  sector: string | null;
  industry: string | null;
  current_price: number | null;
  market_cap: number | null;
  pe_ratio: number | null;
  day_change_pct: number | null;
}

// ─── Formatters ──────────────────────────────────────────
export function fmtMillions(val: number | null | undefined): string {
  if (val == null) return '--';
  const abs = Math.abs(val);
  if (abs >= 1e9) return `${(val / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `${(val / 1e6).toFixed(1)}M`;
  if (abs >= 1e3) return `${(val / 1e3).toFixed(1)}K`;
  return val.toFixed(0);
}

export function fmtStatementVal(val: number | null | undefined): string {
  if (val == null) return '--';
  const inMillions = val / 1e6;
  if (val < 0) return `(${Math.abs(inMillions).toLocaleString('en-US', { maximumFractionDigits: 0 })})`;
  return inMillions.toLocaleString('en-US', { maximumFractionDigits: 0 });
}

export function fmtPct(val: number | null | undefined): string {
  if (val == null) return '--';
  return `${(val * 100).toFixed(1)}%`;
}

export function fmtDollar(val: number | null | undefined): string {
  if (val == null) return '--';
  return val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function fmtPerShare(val: number | null | undefined): string {
  if (val == null) return '--';
  if (val < 0) return `(${Math.abs(val).toFixed(2)})`;
  return val.toFixed(2);
}

export function fmtNumber(val: number | null | undefined, decimals: number = 1): string {
  if (val == null) return '--';
  return val.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function fmtRatio(val: number | null | undefined): string {
  if (val == null) return '--';
  return val.toFixed(2);
}

export function gainColor(val: number | null | undefined): string {
  if (val == null || val === 0) return 'var(--text-secondary)';
  return val > 0 ? 'var(--color-positive)' : 'var(--color-negative)';
}

export function negColor(val: number | null | undefined): string {
  if (val == null || val >= 0) return 'var(--text-primary)';
  return 'var(--color-negative)';
}
