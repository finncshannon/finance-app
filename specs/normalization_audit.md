# Normalization Audit — Full Pipeline Field Map
## Session 11A Deliverable
**Date:** 2026-03-07 | **Convention:** All ratios/percentages as decimal ratios (0.15 = 15%)

---

## Pipeline Layers

1. **Yahoo Raw** — yfinance `.info` dict or computed from financial statements
2. **Provider Output** — `QuoteData`, `KeyStatistics`, `FinancialPeriod` Pydantic models
3. **Cache Write** — `market_data_service.py` `get_live_quote()` or `get_financials()`
4. **API Response** — Router returns cached values directly
5. **Frontend Display** — `fmtPct(val)` multiplies by 100 and adds `%`

---

## Market Data Fields (from `get_quote()` + `get_key_statistics()`)

| Field | Yahoo Raw Key | Computation | Provider Output | Cache Column | Frontend | Status |
|-------|--------------|-------------|-----------------|--------------|----------|--------|
| `current_price` | `currentPrice` | as-is | `QuoteData.current_price` | `market_data.current_price` | `fmtDollar()` | N/A (not a ratio) |
| `day_change` | computed | `price - prev_close` | `QuoteData.day_change` | `market_data.day_change` | `fmtSignedDollar()` | N/A (dollar amount) |
| `day_change_pct` | computed | `day_change / prev_close` | `QuoteData.day_change_pct` | `market_data.day_change_pct` | `fmtPct() * 100` | **FIXED (10C)** — removed `* 100` |
| `dividend_yield` | `dividendYield` | as-is (yfinance returns decimal) | `KeyStatistics.dividend_yield` | `market_data.dividend_yield` | `fmtPct() * 100` | **VERIFIED** — yfinance returns 0.005 for 0.5% |
| `dividend_rate` | `dividendRate` | as-is | `KeyStatistics.dividend_rate` | `market_data.dividend_rate` | `fmtDollar()` | N/A (dollar amount) |
| `pe_trailing` | `trailingPE` | as-is | `KeyStatistics.pe_trailing` | `market_data.pe_trailing` | raw multiple | N/A (not a ratio) |
| `pe_forward` | `forwardPE` | as-is | `KeyStatistics.pe_forward` | `market_data.pe_forward` | raw multiple | N/A |
| `price_to_book` | `priceToBook` | as-is | `KeyStatistics.price_to_book` | `market_data.price_to_book` | raw multiple | N/A |
| `price_to_sales` | `priceToSalesTrailing12Months` | as-is | `KeyStatistics.price_to_sales` | `market_data.price_to_sales` | raw multiple | N/A |
| `ev_to_revenue` | `enterpriseToRevenue` | as-is | `KeyStatistics.ev_to_revenue` | `market_data.ev_to_revenue` | raw multiple | N/A |
| `ev_to_ebitda` | `enterpriseToEbitda` | as-is | `KeyStatistics.ev_to_ebitda` | `market_data.ev_to_ebitda` | raw multiple | N/A |
| `beta` | `beta` | as-is | `KeyStatistics.beta` | `market_data.beta` | raw coefficient | N/A |
| `market_cap` | `marketCap` | as-is | `QuoteData.market_cap` | `market_data.market_cap` | `fmtDollar()` | N/A |
| `enterprise_value` | `enterpriseValue` | as-is | `QuoteData.enterprise_value` | `market_data.enterprise_value` | `fmtDollar()` | N/A |

---

## Financial Data Fields (from `get_financials()` → `FinancialPeriod`)

### Computed Margins (all decimal ratios)

| Field | Computation | Provider (yahoo_finance.py) | Cache Column | Status |
|-------|-------------|---------------------------|--------------|--------|
| `gross_margin` | `gross_profit / revenue` | division only | `financial_data.gross_margin` | **VERIFIED** |
| `operating_margin` | `ebit / revenue` | division only | `financial_data.operating_margin` | **VERIFIED** |
| `net_margin` | `net_income / revenue` | division only | `financial_data.net_margin` | **VERIFIED** |
| `ebitda_margin` | `ebitda / revenue` | division only | `financial_data.ebitda_margin` | **VERIFIED** |
| `fcf_margin` | `free_cash_flow / revenue` | division only | `financial_data.fcf_margin` | **VERIFIED** |
| `revenue_growth` | `(rev - prev_rev) / abs(prev_rev)` | division only | `financial_data.revenue_growth` | **VERIFIED** |
| `roe` | `net_income / equity` | division only | `financial_data.roe` | **VERIFIED** (can be >1.0) |
| `debt_to_equity` | `total_debt / equity` | division only | `financial_data.debt_to_equity` | **VERIFIED** (ratio, not %) |
| `payout_ratio` | `abs(divs_paid) / abs(net_income)` | division only | `financial_data.payout_ratio` | **VERIFIED** |

**Key finding:** No `* 100` exists in any margin/ratio computation in `yahoo_finance.py`. All produce decimal ratios.

---

## DataExtractionService Computed Metrics

### Single-Period Metrics (all decimal ratios via `_safe_div`)

| Metric | Computation | Output Format | Status |
|--------|-------------|---------------|--------|
| `gross_margin` | `gross_profit / revenue` | decimal | **VERIFIED** + `_validate_ratio` added |
| `operating_margin` | `ebit / revenue` | decimal | **VERIFIED** + `_validate_ratio` added |
| `net_margin` | `net_income / revenue` | decimal | **VERIFIED** + `_validate_ratio` added |
| `ebitda_margin` | `ebitda / revenue` | decimal | **VERIFIED** + `_validate_ratio` added |
| `fcf_margin` | `free_cash_flow / revenue` | decimal | **VERIFIED** + `_validate_ratio` added |
| `roe` | `net_income / equity` | decimal | **VERIFIED** (can be >1.0 for negative equity companies) |
| `roa` | `net_income / total_assets` | decimal | **VERIFIED** |
| `roic` | `ebit * (1 - tax_rate) / invested_capital` | decimal | **VERIFIED** |
| `debt_to_equity` | `total_debt / equity` | ratio | **VERIFIED** (>1.0 is normal) |
| `net_debt_to_ebitda` | `(total_debt - cash) / ebitda` | ratio | **VERIFIED** |
| `interest_coverage` | `ebit / interest_expense` | ratio | **VERIFIED** |
| `debt_to_assets` | `total_debt / total_assets` | decimal | **VERIFIED** |
| `asset_turnover` | `revenue / total_assets` | ratio | **VERIFIED** |
| `fcf_yield` | `free_cash_flow / market_cap` | decimal | **VERIFIED** |
| `earnings_yield` | `eps_diluted / current_price` | decimal | **VERIFIED** |
| `dividend_yield` | passthrough from `market_data` | decimal | **VERIFIED** |

### Valuation Multiples (raw, not ratios)

| Metric | Source | Status |
|--------|--------|--------|
| `pe_ratio` | `market_data.pe_trailing` | N/A (raw multiple) |
| `pe_forward` | `market_data.pe_forward` | N/A |
| `price_to_book` | `market_data.price_to_book` | N/A |
| `price_to_sales` | `market_data.price_to_sales` | N/A |
| `ev_to_ebitda` | `market_data.ev_to_ebitda` | N/A |
| `ev_to_revenue` | `market_data.ev_to_revenue` | N/A |

### Growth Metrics (all decimal ratios)

| Metric | Computation | Status |
|--------|-------------|--------|
| `revenue_growth_yoy` | `(curr - prev) / abs(prev)` | **VERIFIED** + `_validate_ratio` added |
| `net_income_growth_yoy` | `(curr - prev) / abs(prev)` | **VERIFIED** |
| `eps_growth_yoy` | `(curr - prev) / abs(prev)` | **VERIFIED** |
| `ebitda_growth_yoy` | `(curr - prev) / abs(prev)` | **VERIFIED** |
| `fcf_growth_yoy` | `(curr - prev) / abs(prev)` | **VERIFIED** |
| `revenue_cagr_3y` | `(end/begin)^(1/3) - 1` | **VERIFIED** |
| `revenue_cagr_5y` | `(end/begin)^(1/5) - 1` | **VERIFIED** |
| `eps_cagr_3y` | `(end/begin)^(1/3) - 1` | **VERIFIED** |
| `eps_cagr_5y` | `(end/begin)^(1/5) - 1` | **VERIFIED** |

**Key finding:** `_cagr()` uses `(end / begin) ** (1 / years) - 1` which produces a decimal ratio. No `* 100`.

---

## Safeguards Added (11A)

### `market_data_service.py` — Cache Write Layer
1. **`day_change_pct`**: If `abs(value) > 1.0`, log warning and auto-divide by 100
2. **`dividend_yield`**: If `value > 0.5`, log warning (50%+ yield is almost certainly a format issue)

### `data_extraction_service.py` — Extraction Layer
3. **`_validate_ratio()`**: Helper function that warns if `abs(value) > max_reasonable`
4. Applied to: `gross_margin`, `operating_margin`, `net_margin`, `ebitda_margin`, `fcf_margin` (max 1.5)
5. Applied to: `_yoy_growth` (max 10.0 — 1000% growth would be suspicious)

---

## Summary

| Issue Found | Layer | Fix Applied | Session |
|-------------|-------|-------------|---------|
| `day_change_pct * 100` | Provider (`yahoo_finance.py`) | Removed `* 100` | **10C** |
| No other `* 100` bugs | All layers | None needed | 11A (verified) |
| Missing safeguards | Cache write + extraction | Added `_validate_ratio` + cache normalization | **11A** |

**Conclusion:** The only actual format bug was `day_change_pct` (fixed in 10C). All other fields correctly use decimal ratio convention throughout the pipeline. Safeguards have been added to catch future regressions.
