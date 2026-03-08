# Session 11A — Data Accuracy Normalization (Full Pipeline Audit)
## Phase 11: Research

**Priority:** CRITICAL
**Type:** Backend Only
**Depends On:** None (but coordinate with 10C — see `specs/10C_11A_COORDINATION.md`)
**Spec Reference:** `specs/phase11_research.md` → Area 1 (1A, 1B)

---

## ⚠️ CRITICAL COORDINATION NOTE

**Read `specs/10C_11A_COORDINATION.md` before building.** This session overlaps with 10C (Live Data Fix). They modify the same files (`yahoo_finance.py`, `market_data_service.py`, `data_extraction_service.py`). Run 11A first for the full audit, then 10C adds startup refresh / WebSocket on top.

---

## SCOPE SUMMARY

Perform a full audit of every numerical field through the 5-layer data pipeline (Yahoo Provider → Provider Models → Cache Write → API Response → Frontend Display). Normalize all percentage/ratio fields to decimal ratio format (0.15 = 15%). Fix `day_change_pct` (if not already fixed by 10C), verify `dividend_yield`, audit all computed margins and growth metrics. Produce a normalization spec document (`specs/normalization_audit.md`) as a session deliverable.

---

## TASKS

### Task 1: Audit and Document Every Field
**Description:** Trace every numerical field through the pipeline and document its format at each layer. Produce `specs/normalization_audit.md` as a deliverable — a table mapping every field through all 5 layers with expected format.

**Subtasks:**
- [ ] 1.1 — Add temporary trace logging in `backend/providers/yahoo_finance.py` for `get_quote()` and `get_key_statistics()` — log raw values returned by yfinance for a test ticker (AAPL):
  ```python
  logger.debug("AUDIT get_quote %s: day_change_pct=%.6f, dividend_yield=%s", ticker, day_change_pct, stats.dividend_yield)
  ```
- [ ] 1.2 — Add temporary trace logging in `backend/services/market_data_service.py` `get_live_quote()` — log values being written to cache.
- [ ] 1.3 — Add temporary trace logging in `backend/services/data_extraction_service.py` `compute_all_metrics()` — log computed metric values.
- [ ] 1.4 — Run the app with AAPL, MSFT, and a high-dividend stock (e.g., T or VZ). Record the values at each layer.
- [ ] 1.5 — Create `specs/normalization_audit.md` documenting each field:

  | Field | Yahoo Raw | Provider Output | Cache Column | Expected Format | Status |
  |-------|-----------|-----------------|--------------|-----------------|--------|
  | day_change_pct | computed | × 100 (BUG) | market_data | decimal ratio | ⚠️ FIX |
  | dividend_yield | dividendYield | as-is | market_data | decimal ratio | ✅ verify |
  | gross_margin | computed | gross/revenue | financial_data | decimal ratio | ✅ |
  | operating_margin | computed | ebit/revenue | financial_data | decimal ratio | ✅ |
  | ... | ... | ... | ... | ... | ... |

---

### Task 2: Fix Provider-Level Format Issues
**Description:** Fix any fields in `yahoo_finance.py` that violate the decimal ratio convention.

**Subtasks:**
- [ ] 2.1 — Fix `day_change_pct` in `get_quote()` (if not already fixed by 10C):
  ```python
  # BEFORE: day_change_pct = (day_change / prev_close) * 100
  # AFTER:
  day_change_pct = day_change / prev_close  # decimal ratio: 0.0085 for 0.85%
  ```
- [ ] 2.2 — Verify `dividend_yield` from `get_key_statistics()`: Yahoo's `dividendYield` key returns a decimal (0.005 for 0.5%). Confirm by logging. If it's already a decimal, no change needed.
- [ ] 2.3 — Verify all computed fields in `get_financials()`: `gross_margin`, `operating_margin`, `net_margin`, `fcf_margin`, `ebitda_margin`, `revenue_growth`, `roe`, `debt_to_equity`, `payout_ratio`. These are all computed as `numerator / denominator` which produces decimal ratios — confirm each one.
- [ ] 2.4 — Check if `beta` needs any normalization (it shouldn't — it's a raw coefficient, not a percentage).

---

### Task 3: Add Normalization Safeguards
**Description:** Add defensive normalization helpers to catch format issues going forward.

**Subtasks:**
- [ ] 3.1 — In `backend/services/data_extraction_service.py`, add a validation helper:
  ```python
  def _validate_ratio(value: float | None, field_name: str, max_reasonable: float = 5.0) -> float | None:
      """Validate a ratio field. If > max_reasonable, it's likely a percentage — normalize."""
      if value is None:
          return None
      if abs(value) > max_reasonable:
          logger.warning("Suspicious ratio for %s: %.4f (expected < %.1f). Possible format mismatch.", field_name, value, max_reasonable)
      return value
  ```
  Apply to key computed metrics as a safety net.
- [ ] 3.2 — In `backend/services/market_data_service.py` `get_live_quote()`, add a normalization check on `day_change_pct` before writing to cache:
  ```python
  # Safeguard: day_change_pct should be a decimal ratio (e.g., 0.0085 not 0.85)
  dcp = quote.day_change_pct
  if dcp is not None and abs(dcp) > 1.0:
      logger.warning("day_change_pct appears to be percentage format (%.4f), normalizing", dcp)
      dcp = dcp / 100
  cache_data["day_change_pct"] = dcp
  ```
- [ ] 3.3 — Add similar safeguards for `dividend_yield` — if value > 0.5 (50% yield), it's almost certainly a format issue.

---

### Task 4: Audit DataExtractionService Computed Metrics
**Description:** The `DataExtractionService` computes 30+ financial metrics from cached data. Audit every computation to ensure inputs and outputs are in decimal ratio format.

**Subtasks:**
- [ ] 4.1 — In `backend/services/data_extraction_service.py`, verify every `_safe_div` computation produces a decimal ratio. The current code computes margins as `gross_profit / revenue` which is correct. Verify the following are all decimal:
  - `_gross_margin`, `_operating_margin`, `_net_margin`, `_ebitda_margin`, `_fcf_margin` — all `numerator / revenue` ✅
  - `_roe` — `net_income / equity` ✅ (can be > 1.0 legitimately)
  - `_roa` — `net_income / total_assets` ✅
  - `_roic` — `nopat / invested_capital` ✅
  - `_debt_to_equity` — `total_debt / equity` ✅ (ratio, not percentage)
  - `_current_ratio` — `current_assets / current_liabilities` ✅ (ratio)
  - `_payout_ratio` — `|dividends| / |net_income|` ✅
  - Revenue growth, EPS growth — computed as `(new - old) / old` ✅
  - CAGR metrics — `(end / begin) ^ (1/years) - 1` ✅
- [ ] 4.2 — Verify any growth rate computations don't accidentally multiply by 100.
- [ ] 4.3 — Check if `revenue_growth` in `yahoo_finance.py` `get_financials()` (line `rev_growth = (revenue - prev_revenue) / abs(prev_revenue)`) is consistent with the `DataExtractionService` computation. Both should produce decimal ratios.

---

### Task 5: Remove Temporary Logging
**Description:** After confirming all fixes, remove the temporary trace logging added in Task 1.

**Subtasks:**
- [ ] 5.1 — Remove all `logger.debug("AUDIT ...")` lines added for the audit.
- [ ] 5.2 — Keep the `logger.warning` safeguard lines from Task 3 — those are permanent defensive checks.

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: `specs/normalization_audit.md` produced — documents every numerical field through all 5 pipeline layers.
- [ ] AC-2: `day_change_pct` stored as decimal ratio (0.0085 for 0.85%). SPY no longer shows 85%.
- [ ] AC-3: `dividend_yield` confirmed as decimal ratio. Apple shows ~0.5% not 39%.
- [ ] AC-4: All margins (`gross_margin`, `operating_margin`, `net_margin`, `ebitda_margin`, `fcf_margin`) confirmed as decimal ratios.
- [ ] AC-5: `revenue_growth` confirmed as decimal ratio across both provider and extraction service.
- [ ] AC-6: `roe` correctly computed — can be > 1.0 for negative-equity companies (this is correct, not a bug).
- [ ] AC-7: `payout_ratio` confirmed as decimal ratio.
- [ ] AC-8: Safeguard: `day_change_pct` values > 1.0 logged as warnings and auto-normalized.
- [ ] AC-9: Safeguard: `dividend_yield` values > 0.5 logged as warnings.
- [ ] AC-10: No `* 100` multiplications in the provider or extraction service for ratio fields.
- [ ] AC-11: Temporary audit logging removed. Permanent warning safeguards retained.
- [ ] AC-12: DataExtractionService CAGR and growth computations verified as decimal ratios.
- [ ] AC-13: No regressions — all existing API responses still work correctly with normalized values.

---

## FILES TOUCHED

**New files:**
- `specs/normalization_audit.md` — full field-by-field audit document (session deliverable)

**Modified files:**
- `backend/providers/yahoo_finance.py` — fix `day_change_pct` (remove `* 100`), verify `dividend_yield`, add temp audit logging then remove
- `backend/services/market_data_service.py` — add normalization safeguard on `day_change_pct` and `dividend_yield` before cache write
- `backend/services/data_extraction_service.py` — add `_validate_ratio` helper, audit all computed metrics, add temp logging then remove

---

## BUILDER PROMPT

> **Session 11A — Data Accuracy Normalization (Full Pipeline Audit)**
>
> You are building session 11A of the Finance App v2.0 update. This is a **CRITICAL** session.
>
> ⚠️ **Read `specs/10C_11A_COORDINATION.md` first.** This session overlaps with 10C. If 10C has already fixed `day_change_pct`, verify rather than re-fix.
>
> **What you're doing:** Full audit of every numerical field through the 5-layer data pipeline, normalizing all percentages/ratios to decimal format (0.15 = 15%). Producing a normalization spec document as a deliverable.
>
> **Context:** The pipeline has format inconsistencies. `day_change_pct` is stored as a percentage (0.85) instead of decimal (0.0085), causing SPY to show 85%. Other fields may have similar issues. The cross-cutting rule is: all ratios/percentages as decimal ratios, frontend `fmtPct()` multiplies by 100.
>
> **Existing code:**
>
> `yahoo_finance.py` (at `backend/providers/yahoo_finance.py`):
> - `get_quote()`: computes `day_change_pct = (day_change / prev_close) * 100` — **BUG: remove × 100**
> - `get_key_statistics()`: reads `dividendYield` from Yahoo — yfinance returns as decimal (0.005). Verify.
> - `get_financials()`: computes margins as `numerator / revenue` (decimal ✅), `revenue_growth` as `(new - old) / old` (decimal ✅), `roe` as `net_income / equity` (decimal ✅)
> - All safe helpers: `_safe_float`, `_safe_int`, `_safe`
>
> `market_data_service.py` (at `backend/services/market_data_service.py`):
> - `get_live_quote()`: passes `quote.day_change_pct` through to cache as-is
> - Cache write: `cache_data["day_change_pct"] = quote.day_change_pct`
> - No normalization on write — values stored exactly as provider returns them
>
> `data_extraction_service.py` (at `backend/services/data_extraction_service.py`):
> - Computes 30+ metrics using `_safe_div(numerator, denominator)` pattern
> - All margin computations: `gross_profit / revenue`, `ebit / revenue`, etc. → decimal ✅
> - Growth: `(new - old) / old` → decimal ✅
> - CAGR: `(end / begin) ^ (1/years) - 1` → decimal ✅
> - No `* 100` anywhere in computed metrics (good)
> - Has `_cagr()` helper with proper formula
>
> **Cross-cutting rules:**
> - **Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%).** This is THE rule this session enforces.
>
> **Task 1: Audit** — Add temp logging at provider, cache write, and extraction layers. Run with AAPL + a dividend stock. Record values. Produce `specs/normalization_audit.md` table.
>
> **Task 2: Fix** — Fix `day_change_pct` (remove `* 100`). Verify `dividend_yield`. Verify all computed fields.
>
> **Task 3: Safeguards** — Add `_validate_ratio()` helper. Add normalization checks before cache writes for `day_change_pct` (auto-divide by 100 if > 1.0) and `dividend_yield` (warn if > 0.5).
>
> **Task 4: Verify Extraction** — Audit every `_safe_div` computation. Verify no accidental `* 100`. Confirm CAGR formula.
>
> **Task 5: Cleanup** — Remove temp logging. Keep permanent warning safeguards.
>
> **Key deliverable:** `specs/normalization_audit.md` — table mapping every field through all 5 layers.
>
> **Acceptance criteria:**
> 1. Normalization audit document produced
> 2. day_change_pct fixed (decimal ratio)
> 3. dividend_yield verified
> 4. All margins/growth confirmed decimal
> 5. Safeguards added for future protection
> 6. No regressions
>
> **Files to create:** `specs/normalization_audit.md`
> **Files to modify:** `yahoo_finance.py`, `market_data_service.py`, `data_extraction_service.py`
>
> **Technical constraints:**
> - `_safe_div(a, b)` returns None if either is None or b is zero
> - `_cagr(begin, end, years)` returns `(end/begin)^(1/years) - 1`
> - Yahoo's `dividendYield` key: yfinance typically returns as decimal (0.005 = 0.5%). Verify with a known stock.
> - The `* 100` on `day_change_pct` is the only known multiplication bug in the provider. All other computations use division only.
> - ROE can legitimately exceed 1.0 (100%) for companies with very low or negative equity (Apple, Home Depot). Do NOT cap it — just verify the format is correct.
