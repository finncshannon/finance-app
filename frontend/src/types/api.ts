/** Phase 0C — Response envelope types */

export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error: ApiError | null;
  meta: {
    timestamp: string;
    duration_ms: number;
    version: string;
  };
}

export interface ApiError {
  code: string;
  message: string;
  details: Record<string, unknown>;
}

/** Market data from /api/v1/companies/{ticker}/market */
export interface MarketData {
  ticker: string;
  current_price: number;
  previous_close: number;
  day_change: number;
  day_change_pct: number;
  day_high: number;
  day_low: number;
  fifty_two_week_high: number;
  fifty_two_week_low: number;
  volume: number;
  average_volume: number;
  market_cap: number;
  enterprise_value: number;
  pe_trailing: number | null;
  pe_forward: number | null;
  price_to_book: number | null;
  ev_to_ebitda: number | null;
  dividend_yield: number | null;
  beta: number;
  updated_at: string;
  is_stale: boolean;
}

/** WebSocket price update message */
export interface PriceUpdateMessage {
  type: 'price_update';
  data: Record<
    string,
    {
      current_price: number;
      day_change: number;
      day_change_pct: number;
      volume: number;
      updated_at: string;
    }
  >;
}

/** WebSocket system status message */
export interface SystemStatusMessage {
  type: 'system_status';
  data: {
    market_open: boolean;
    last_price_refresh: string | null;
    active_refresh_tickers: number;
    api_calls_remaining: number | null;
    backend_uptime_seconds: number;
  };
}

/** Health check response */
export interface HealthData {
  status: string;
  uptime: number;
  db_status: string;
}
