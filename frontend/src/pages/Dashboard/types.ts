/** Dashboard TypeScript interfaces — mirrors backend dashboard_service responses. */

// ─── Market Overview ─────────────────────────────────────
export interface IndexData {
  symbol: string;
  name: string;
  value: number;
  change: number;
  change_pct: number;
}

export interface MarketStatus {
  status: 'open' | 'pre_market' | 'after_hours' | 'closed';
  label: string;
  countdown: string;
  color: 'green' | 'yellow' | 'gray';
}

export interface MarketOverview {
  indices: IndexData[];
  status: MarketStatus;
}

// ─── Portfolio Summary ───────────────────────────────────
export interface PortfolioSummary {
  total_value: number;
  total_cost: number;
  total_gain_loss: number;
  total_gain_loss_pct: number;
  day_change: number;
  day_change_pct: number;
  position_count: number;
  best_performer: { ticker: string; gain_pct: number } | null;
  worst_performer: { ticker: string; gain_pct: number } | null;
}

// ─── Watchlist ───────────────────────────────────────────
export interface WatchlistSummary {
  id: number;
  name: string;
  sort_order: number;
  item_count: number;
}

export interface WatchlistItem {
  ticker: string;
  company_name: string | null;
  current_price: number | null;
  day_change: number | null;
  day_change_pct: number | null;
  pe_ratio: number | null;
  market_cap: number | null;
  volume: number | null;
  added_at: string;
}

export interface WatchlistDetail {
  id: number;
  name: string;
  items: WatchlistItem[];
}

// ─── Recent Models ───────────────────────────────────────
export interface RecentModel {
  ticker: string;
  model_type: string;
  intrinsic_value: number | null;
  current_price: number | null;
  upside_pct: number | null;
  last_run_at: string;
}

// ─── Upcoming Events ─────────────────────────────────────
export interface UpcomingEvent {
  date: string;
  ticker: string;
  event_type: string;
  detail: string;
  source: 'portfolio' | 'watchlist' | 'market';
  is_estimated: boolean;
}

export interface FilteredEventsResponse {
  events: UpcomingEvent[];
  total_count: number;
  has_more: boolean;
}

// ─── Dashboard Summary (full payload) ────────────────────
export interface DashboardSummary {
  market: MarketOverview;
  portfolio: PortfolioSummary | null;
  recent_models: RecentModel[];
  events: UpcomingEvent[];
  watchlists: WatchlistSummary[];
}

// ─── Formatters ──────────────────────────────────────────
export function fmtDollar(val: number | null | undefined): string {
  if (val == null) return '--';
  return val.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function fmtCompactDollar(val: number | null | undefined): string {
  if (val == null) return '--';
  if (Math.abs(val) >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
  if (Math.abs(val) >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
  if (Math.abs(val) >= 1e6) return `$${(val / 1e6).toFixed(2)}M`;
  if (Math.abs(val) >= 1e3) return `$${(val / 1e3).toFixed(1)}K`;
  return fmtDollar(val);
}

export function fmtPct(val: number | null | undefined): string {
  if (val == null) return '--';
  return `${(val * 100).toFixed(2)}%`;
}

export function fmtSignedPct(val: number | null | undefined): string {
  if (val == null) return '--';
  const pct = val * 100;
  const sign = pct >= 0 ? '+' : '';
  return `${sign}${pct.toFixed(2)}%`;
}

export function fmtSignedDollar(val: number | null | undefined): string {
  if (val == null) return '--';
  const sign = val >= 0 ? '+' : '';
  return `${sign}${fmtDollar(val)}`;
}

export function gainColor(val: number | null | undefined): string {
  if (val == null || val === 0) return 'var(--text-secondary)';
  return val > 0 ? 'var(--color-positive)' : 'var(--color-negative)';
}

export function statusColor(status: MarketStatus): string {
  switch (status.color) {
    case 'green': return 'var(--color-positive)';
    case 'yellow': return 'var(--color-warning)';
    default: return 'var(--text-tertiary)';
  }
}
