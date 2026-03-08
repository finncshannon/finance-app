# 10C ↔ 11A Coordination Document
## For: Builder agents, PM3, and anyone running sessions 10C or 11A

**Created by:** PM2 (March 6, 2026)
**Critical dependency:** Sessions 10C and 11A modify overlapping files and address the same root cause.

---

## THE PROBLEM

Sessions 10C (Live Data Fix) and 11A (Data Accuracy Normalization) both fix **data format mismatches** in the pipeline. Specifically:

- **10C** fixes: startup refresh, after-hours refresh interval, `day_change_pct` format bug, WebSocket subscription for portfolio, market status
- **11A** fixes: full pipeline audit across all 5 layers (Yahoo → provider models → cache write → API response → frontend display) for every field, normalizing all percentages/ratios to decimal format

They share the same root cause and modify overlapping files:

| File | 10C Changes | 11A Changes |
|------|-------------|-------------|
| `backend/providers/yahoo_finance.py` | Fix `day_change_pct` calculation (remove `* 100`) | Full audit of ALL returned values — `dividend_yield`, margins, growth rates, ratios |
| `backend/services/market_data_service.py` | Add startup refresh, after-hours interval | Verify all values pass through without format corruption |
| `backend/services/price_refresh_service.py` | Startup refresh, after-hours loop | May adjust what fields are refreshed |
| `backend/services/data_extraction_service.py` | — | Full normalization of extracted values |
| `backend/services/dashboard_service.py` | Fix market status calculation | Verify day_change_pct display format |

---

## RECOMMENDED BUILD ORDER

**Run 11A first, then 10C.**

### Why:
1. 11A is the **full audit** — it traces every field through all 5 layers and normalizes everything to decimal ratios. This is the comprehensive fix.
2. 10C then **layers on top**: startup refresh, after-hours refresh interval, WebSocket subscription, market status fix, refresh button. These don't conflict with 11A's normalization — they're additive features.
3. If 10C runs first and fixes only `day_change_pct`, then 11A runs and does the full audit, 11A might re-fix `day_change_pct` redundantly or conflict with 10C's approach.

### If merging into one session:
If the PM decides to merge them, the combined session should:
1. Do 11A's full audit first (trace every field, create normalization spec)
2. Apply 11A's fixes (normalize all values)
3. Then add 10C's features (startup refresh, after-hours, WebSocket, refresh button)

---

## THE `day_change_pct` BUG — ROOT CAUSE

**File:** `backend/providers/yahoo_finance.py`, method `get_quote()`

**Current code (line ~173):**
```python
day_change_pct = (day_change / prev_close) * 100
```

This returns `0.85` for a 0.85% daily change. But the app's convention (cross-cutting rule #3) is:
> **All ratios/percentages stored as decimal ratios (0.15 = 15%)**

So `day_change_pct` should be `0.0085`, not `0.85`.

The frontend's `fmtPct()` multiplies by 100: `0.85 * 100 = 85%` — which is the bug SPY shows.

**Fix:** Remove `* 100`:
```python
day_change_pct = day_change / prev_close  # 0.0085 for 0.85% change
```

**But wait** — 11A needs to audit whether other fields have the same issue:
- `dividend_yield` from Yahoo: is it already a decimal (0.005 = 0.5%) or a percentage (0.5)?
- `revenue_growth`, `gross_margin`, etc.: these are computed by the provider as `value / total` which gives decimals — correct.
- `beta`: not a percentage, no conversion needed.

**This is why 11A should run first** — it audits everything systematically, not just `day_change_pct`.

---

## FIELDS TO AUDIT (11A SCOPE)

These are the fields that pass through the pipeline and could have format issues:

### From `get_quote()` → `cache.market_data`:
- `day_change_pct` — **KNOWN BUG**: stored as percentage, should be decimal
- `dividend_yield` — from `get_key_statistics()`, Yahoo returns as decimal (0.005) — **verify**

### From `get_financials()` → `cache.financial_data`:
- `gross_margin` — computed as `gross / revenue` → decimal ✅
- `operating_margin` — computed as `ebit / revenue` → decimal ✅
- `net_margin` — computed as `net_income / revenue` → decimal ✅
- `fcf_margin` — computed as `fcf / revenue` → decimal ✅
- `ebitda_margin` — computed as `ebitda / revenue` → decimal ✅
- `revenue_growth` — computed as `(rev - prev) / prev` → decimal ✅
- `roe` — computed as `net_income / equity` → decimal ✅
- `debt_to_equity` — computed as `debt / equity` → decimal (but it's a ratio, not a %, so >1 is valid) ✅
- `payout_ratio` — computed as `|divs| / |net_income|` → decimal ✅

### From `get_key_statistics()` → `cache.market_data`:
- `pe_trailing`, `pe_forward` — raw multiples, no conversion ✅
- `price_to_book`, `price_to_sales` — raw multiples ✅
- `ev_to_revenue`, `ev_to_ebitda` — raw multiples ✅
- `dividend_yield` — Yahoo returns via `dividendYield` key. **yfinance returns this as a decimal** (e.g., 0.005 for 0.5%). Verify by testing with a known dividend stock.
- `beta` — raw number ✅

### Frontend display:
- `fmtPct(value)` — multiplies by 100, adds `%`. Expects decimal input.
- Scanner `formatMetricValue(value, "percent")` — multiplies by 100. Expects decimal.
- Dashboard `MarketOverviewWidget` — verify it uses `fmtPct` for `day_change_pct`.

---

## 11A DELIVERABLE: NORMALIZATION SPEC

The 11A Builder should produce a normalization spec document as one of its outputs:

| Field | Source (Yahoo key) | Provider Output | Cache Column | API Response | Frontend Display | Status |
|-------|-------------------|-----------------|--------------|-------------|-----------------|--------|
| day_change_pct | computed | decimal ratio | market_data.day_change_pct | decimal | fmtPct × 100 | ⚠️ FIX |
| dividend_yield | dividendYield | decimal | market_data.dividend_yield | decimal | fmtPct × 100 | ✅ verify |
| gross_margin | computed | decimal | financial_data.gross_margin | decimal | fmtPct × 100 | ✅ |
| ... | ... | ... | ... | ... | ... | ... |

This document should live at `specs/normalization_audit.md` and be referenced by the 10C Builder.

---

## FOR THE 10C BUILDER

**If 11A has already run:** The `day_change_pct` bug is fixed and all values are normalized. Your job is:
1. Add startup price refresh (one-time on app launch)
2. Add after-hours refresh interval (15 min outside market hours)
3. Fix market status timezone/DST handling
4. Add auto-fetch company profile on position create
5. Add profile backfill startup task

**If 11A has NOT run yet:** You should still fix `day_change_pct` as described above (remove `* 100`), but note in a comment: `# Normalized as part of 10C — see also 11A full audit`. The 11A Builder will see this and skip re-fixing it.

---

## FOR THE 11A BUILDER

Read this document before starting. Key points:
1. 10C may have already fixed `day_change_pct` — check the code before applying the fix again
2. Your primary deliverable is the **full normalization audit** across all 5 layers for every field
3. Produce `specs/normalization_audit.md` as a table mapping every field through the pipeline
4. Add temporary logging at each layer during development to verify values
5. The cross-cutting rule is: **all ratios/percentages as decimal ratios (0.15 = 15%)**

---

*End of 10C ↔ 11A Coordination Document*
*PM2 — March 6, 2026*
