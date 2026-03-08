export interface RatioMetricDef {
  key: string;
  label: string;
  format: 'pct' | 'ratio' | 'multiple';
  suffix?: string;
  higherIsBetter?: boolean;
}

export interface RatioCategoryDef {
  id: string;
  label: string;
  metrics: RatioMetricDef[];
}

export const RATIO_CATEGORIES: RatioCategoryDef[] = [
  {
    id: 'profitability',
    label: 'PROFITABILITY',
    metrics: [
      { key: 'gross_margin', label: 'Gross Margin', format: 'pct', higherIsBetter: true },
      { key: 'operating_margin', label: 'Operating Margin', format: 'pct', higherIsBetter: true },
      { key: 'net_margin', label: 'Net Margin', format: 'pct', higherIsBetter: true },
      { key: 'ebitda_margin', label: 'EBITDA Margin', format: 'pct', higherIsBetter: true },
      { key: 'fcf_margin', label: 'FCF Margin', format: 'pct', higherIsBetter: true },
    ],
  },
  {
    id: 'returns',
    label: 'RETURNS',
    metrics: [
      { key: 'roe', label: 'Return on Equity', format: 'pct', higherIsBetter: true },
      { key: 'roa', label: 'Return on Assets', format: 'pct', higherIsBetter: true },
      { key: 'roic', label: 'Return on Invested Capital', format: 'pct', higherIsBetter: true },
    ],
  },
  {
    id: 'leverage',
    label: 'LEVERAGE',
    metrics: [
      { key: 'debt_to_equity', label: 'Debt / Equity', format: 'ratio', suffix: 'x' },
      { key: 'net_debt_to_ebitda', label: 'Net Debt / EBITDA', format: 'ratio', suffix: 'x' },
      { key: 'interest_coverage', label: 'Interest Coverage', format: 'ratio', suffix: 'x', higherIsBetter: true },
      { key: 'debt_to_assets', label: 'Debt / Assets', format: 'pct' },
    ],
  },
  {
    id: 'valuation',
    label: 'VALUATION',
    metrics: [
      { key: 'pe_ratio', label: 'P/E (TTM)', format: 'ratio', suffix: 'x' },
      { key: 'pe_forward', label: 'P/E (Forward)', format: 'ratio', suffix: 'x' },
      { key: 'ev_to_ebitda', label: 'EV / EBITDA', format: 'ratio', suffix: 'x' },
      { key: 'ev_to_revenue', label: 'EV / Revenue', format: 'ratio', suffix: 'x' },
      { key: 'price_to_book', label: 'Price / Book', format: 'ratio', suffix: 'x' },
      { key: 'fcf_yield', label: 'FCF Yield', format: 'pct', higherIsBetter: true },
      { key: 'earnings_yield', label: 'Earnings Yield', format: 'pct', higherIsBetter: true },
      { key: 'dividend_yield', label: 'Dividend Yield', format: 'pct' },
    ],
  },
  {
    id: 'efficiency',
    label: 'EFFICIENCY',
    metrics: [
      { key: 'asset_turnover', label: 'Asset Turnover', format: 'ratio', suffix: 'x', higherIsBetter: true },
    ],
  },
  {
    id: 'growth',
    label: 'GROWTH',
    metrics: [
      { key: 'revenue_growth_yoy', label: 'Revenue Growth (YoY)', format: 'pct', higherIsBetter: true },
      { key: 'net_income_growth_yoy', label: 'Net Income Growth', format: 'pct', higherIsBetter: true },
      { key: 'eps_growth_yoy', label: 'EPS Growth', format: 'pct', higherIsBetter: true },
      { key: 'ebitda_growth_yoy', label: 'EBITDA Growth', format: 'pct', higherIsBetter: true },
      { key: 'fcf_growth_yoy', label: 'FCF Growth', format: 'pct', higherIsBetter: true },
      { key: 'revenue_cagr_3y', label: 'Revenue CAGR (3Y)', format: 'pct', higherIsBetter: true },
      { key: 'revenue_cagr_5y', label: 'Revenue CAGR (5Y)', format: 'pct', higherIsBetter: true },
    ],
  },
];

export function formatMetricValue(val: number | null | undefined, def: RatioMetricDef): string {
  if (val == null) return '--';
  if (def.format === 'pct') return `${(val * 100).toFixed(1)}%`;
  if (def.format === 'ratio' || def.format === 'multiple') return `${val.toFixed(1)}${def.suffix ?? 'x'}`;
  return val.toFixed(2);
}

export function metricColor(val: number | null | undefined, def: RatioMetricDef): string {
  if (val == null || def.higherIsBetter == null) return 'var(--text-primary)';
  if (def.higherIsBetter) return val > 0 ? 'var(--color-positive)' : 'var(--color-negative)';
  return 'var(--text-primary)';
}
