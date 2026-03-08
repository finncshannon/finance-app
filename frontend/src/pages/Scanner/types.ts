/* TypeScript types for the Scanner module — mirrors backend services/scanner/models.py */

export type FilterOperator =
  | 'gt' | 'gte' | 'lt' | 'lte' | 'eq' | 'neq'
  | 'between' | 'in_list' | 'top_pct' | 'bot_pct';

export interface ScannerFilter {
  metric: string;
  operator: FilterOperator;
  value?: number | null;
  low?: number | null;
  high?: number | null;
  values?: string[] | null;
  percentile?: number | null;
}

export interface ScannerRequest {
  filters: ScannerFilter[];
  text_query?: string | null;
  form_types: string[];
  sector_filter?: string | null;
  industry_filter?: string | null;
  universe: string;
  sort_by?: string | null;
  sort_desc: boolean;
  limit: number;
  offset: number;
}

export interface ScannerRow {
  ticker: string;
  company_name?: string | null;
  sector?: string | null;
  industry?: string | null;
  metrics: Record<string, number | null>;
  rank?: number | null;
  composite_score?: number | null;
}

export interface TextSearchHit {
  ticker: string;
  company_name?: string | null;
  form_type?: string | null;
  filing_date?: string | null;
  section_title?: string | null;
  snippet: string;
  word_count?: number | null;
}

export interface ScannerResult {
  rows: ScannerRow[];
  total_matches: number;
  text_hits: TextSearchHit[];
  text_hit_count: number;
  applied_filters: number;
  universe_size: number;
  computation_time_ms: number;
}

export interface MetricDefinition {
  key: string;
  label: string;
  category: string;
  format: string;
  description: string;
}

export interface MetricsCatalog {
  metrics: MetricDefinition[];
  categories: Record<string, string[]>;
}

export interface ScannerPreset {
  id: number | null;
  name: string;
  description?: string;
  is_built_in: boolean;
  filters: ScannerFilter[];
  text_query?: string | null;
  sector_filter?: string | null;
  universe: string;
  form_types: string[];
}

export interface RankingWeight {
  metric: string;
  weight: number;
  ascending: boolean;
}

/** Operator display info */
export const OPERATOR_OPTIONS: { value: FilterOperator; label: string }[] = [
  { value: 'gt', label: '>' },
  { value: 'gte', label: '>=' },
  { value: 'lt', label: '<' },
  { value: 'lte', label: '<=' },
  { value: 'eq', label: '=' },
  { value: 'neq', label: '!=' },
  { value: 'between', label: 'Between' },
  { value: 'top_pct', label: 'Top %' },
  { value: 'bot_pct', label: 'Bottom %' },
];

/** Default visible columns in ResultsTable */
export const DEFAULT_COLUMNS = [
  'current_price',
  'market_cap',
  'pe_trailing',
  'ev_to_ebitda',
  'roe',
  'revenue_growth',
  'dividend_yield',
];

/** Format a metric value for display */
export function formatMetricValue(value: number | null | undefined, format: string): string {
  if (value == null) return '\u2014';
  switch (format) {
    case 'currency':
      if (Math.abs(value) >= 1e12) return `$${(value / 1e12).toFixed(1)}T`;
      if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(1)}B`;
      if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
      if (Math.abs(value) >= 1e3) return `$${(value / 1e3).toFixed(1)}K`;
      return `$${value.toFixed(2)}`;
    case 'percent':
      return `${(value * 100).toFixed(1)}%`;
    case 'ratio':
      return `${value.toFixed(1)}x`;
    case 'integer':
      return value.toLocaleString('en-US', { maximumFractionDigits: 0 });
    default:
      return value.toFixed(2);
  }
}
