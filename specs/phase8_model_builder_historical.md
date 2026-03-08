# Finance App — Model Builder: Historical Data Sub-Tab Update Plan
## Phase 8: Model Builder — Historical Data (Sessions 8B–8C)

**Prepared by:** Planner (March 5, 2026)
**Recipient:** PM Agent
**Scope:** Model Builder → Historical Data sub-tab, including new "Data Readiness" sub-sub-tab

---

## PLAN SUMMARY

Three workstreams:

1. **Data Readiness Sub-Tab (New)** — A 4th sub-tab inside Historical Data (alongside Income Statement, Balance Sheet, Cash Flow) that shows per-engine data dependency analysis, coverage diagnostics, and plain-English notes about what's missing and how it affects model outputs
2. **Diagnostic Overlay Toggle** — A toggle on the Income Statement, Balance Sheet, and Cash Flow tables that adds an interactive inspection layer: populated cells get a glass-bubble indicator, hoverable to reveal source, engine usage, and derivation info; missing cells that are critical/important for engines get a subtle warning marker
3. **Minor Historical Data Polish** — Small improvements to the existing financial table

---

## AREA 1: DATA READINESS SUB-TAB

### Concept

Before running any model, the user can check this tab to see:
- What data the system has for this ticker (coverage summary)
- What each engine needs to run (explicit dependency map)
- Which fields are present, missing, or derived from fallbacks
- A per-engine readiness verdict: Ready / Partial / Not Possible, with plain-English explanations like "DDM not possible: no dividend history found"

### What's Needed

#### 1A. Backend — Engine Dependency Map (New Data Structure)

**Goal:** Define a formal, explicit map of what financial fields each engine requires, at what criticality level.

**Structure:**
```python
# New file: backend/services/engine_dependency_map.py

ENGINE_DEPENDENCIES = {
    "dcf": {
        "critical": [
            {"field": "revenue", "label": "Revenue", "reason": "Base for 10-year projection"},
            {"field": "operating_cash_flow", "label": "Operating Cash Flow", "reason": "FCF derivation"},
            {"field": "capital_expenditure", "label": "Capital Expenditures", "reason": "FCF derivation"},
            {"field": "shares_outstanding", "label": "Shares Outstanding", "reason": "Per-share price calculation"},
        ],
        "important": [
            {"field": "net_debt", "label": "Net Debt", "reason": "Equity bridge (EV to equity)"},
            {"field": "total_debt", "label": "Total Debt", "reason": "WACC calculation"},
            {"field": "cash_and_equivalents", "label": "Cash", "reason": "Net debt derivation"},
            {"field": "ebit", "label": "EBIT", "reason": "Operating margin projection"},
            {"field": "gross_profit", "label": "Gross Profit", "reason": "Margin analysis"},
            {"field": "stockholders_equity", "label": "Equity", "reason": "WACC via CAPM"},
            {"field": "depreciation_amortization", "label": "D&A", "reason": "EBITDA and non-cash add-back"},
            {"field": "tax_provision", "label": "Tax Provision", "reason": "Effective tax rate"},
        ],
        "helpful": [
            {"field": "ebitda", "label": "EBITDA", "reason": "Terminal value exit multiple"},
            {"field": "free_cash_flow", "label": "Free Cash Flow", "reason": "Cross-check vs derived FCF"},
            {"field": "net_income", "label": "Net Income", "reason": "Profitability validation"},
        ],
    },
    "ddm": {
        "critical": [
            {"field": "dividends_paid", "label": "Dividends Paid", "reason": "Core DDM input — model impossible without dividend history"},
            {"field": "shares_outstanding", "label": "Shares Outstanding", "reason": "Dividend per share calculation"},
        ],
        "important": [
            {"field": "net_income", "label": "Net Income", "reason": "Payout ratio and sustainability"},
            {"field": "free_cash_flow", "label": "Free Cash Flow", "reason": "Dividend coverage ratio"},
            {"field": "stockholders_equity", "label": "Equity", "reason": "ROE for sustainable growth"},
        ],
        "helpful": [
            {"field": "revenue", "label": "Revenue", "reason": "Growth context"},
            {"field": "operating_cash_flow", "label": "Operating Cash Flow", "reason": "Cash coverage validation"},
        ],
    },
    "comps": {
        "critical": [
            {"field": "revenue", "label": "Revenue", "reason": "EV/Revenue multiple"},
            {"field": "ebitda", "label": "EBITDA", "reason": "EV/EBITDA multiple"},
            {"field": "net_income", "label": "Net Income", "reason": "P/E multiple"},
            {"field": "shares_outstanding", "label": "Shares Outstanding", "reason": "Per-share metrics"},
        ],
        "important": [
            {"field": "total_debt", "label": "Total Debt", "reason": "Enterprise value calculation"},
            {"field": "cash_and_equivalents", "label": "Cash", "reason": "Enterprise value calculation"},
            {"field": "free_cash_flow", "label": "Free Cash Flow", "reason": "P/FCF multiple"},
            {"field": "stockholders_equity", "label": "Equity", "reason": "P/B multiple"},
        ],
        "helpful": [
            {"field": "gross_profit", "label": "Gross Profit", "reason": "Quality assessment"},
            {"field": "operating_margin", "label": "Operating Margin", "reason": "Quality premium/discount"},
        ],
    },
    "revenue_based": {
        "critical": [
            {"field": "revenue", "label": "Revenue", "reason": "Core input — model is entirely revenue-driven"},
            {"field": "shares_outstanding", "label": "Shares Outstanding", "reason": "Per-share price calculation"},
        ],
        "important": [
            {"field": "operating_margin", "label": "Operating Margin", "reason": "Rule of 40 calculation"},
            {"field": "gross_profit", "label": "Gross Profit", "reason": "Margin profile for multiple selection"},
            {"field": "ebitda", "label": "EBITDA", "reason": "Margin component of Rule of 40"},
        ],
        "helpful": [
            {"field": "free_cash_flow", "label": "Free Cash Flow", "reason": "FCF margin for growth-quality assessment"},
            {"field": "net_income", "label": "Net Income", "reason": "Profitability cross-check"},
        ],
    },
}
```

**Criticality levels:**
- **Critical** — Engine cannot produce meaningful output without this. Verdict: "Not Possible"
- **Important** — Engine will run but uses fallbacks/defaults, reducing accuracy. Verdict: "Partial"
- **Helpful** — Nice to have for validation and secondary calculations. Verdict still "Ready" if missing

**Files touched:**
- `backend/services/engine_dependency_map.py` — new file with the dependency map

#### 1B. Backend — Data Readiness Endpoint

**Goal:** New endpoint that takes a ticker, checks its cached financial data against the dependency map, and returns a structured readiness report.

**Endpoint:** `GET /api/v1/model-builder/{ticker}/data-readiness`

**Logic:**
1. Fetch the most recent financial record for the ticker from `cache.financial_data`
2. Fetch market data from `cache.market_data`
3. For each engine, walk the dependency map:
   - Check if each field is non-null in the most recent year
   - Check how many years of history have this field (data depth)
   - Classify each field as: `present`, `missing`, or `derived` (if the field was computed from other fields — e.g., `free_cash_flow = operating_cash_flow + capital_expenditure`)
4. Produce a per-engine verdict:
   - **Ready** — all critical fields present, all important fields present
   - **Partial** — all critical fields present, some important fields missing (list which ones and what the fallback behavior is)
   - **Not Possible** — one or more critical fields missing (list which ones)
5. Include the detection service's existing confidence scores and reasoning if available
6. Include data coverage stats

**Response format:**
```json
{
  "ticker": "AAPL",
  "data_years_available": 8,
  "total_fields": 48,
  "populated_fields": 42,
  "coverage_pct": 0.875,
  "engines": {
    "dcf": {
      "verdict": "ready",
      "verdict_label": "Ready",
      "detection_score": 82,
      "critical_fields": [
        {"field": "revenue", "label": "Revenue", "status": "present", "years_available": 8, "source": "direct"},
        {"field": "operating_cash_flow", "label": "Operating Cash Flow", "status": "present", "years_available": 8, "source": "direct"},
        {"field": "capital_expenditure", "label": "Capital Expenditures", "status": "present", "years_available": 8, "source": "direct"},
        {"field": "shares_outstanding", "label": "Shares Outstanding", "status": "present", "years_available": 8, "source": "direct"}
      ],
      "important_fields": [
        {"field": "net_debt", "label": "Net Debt", "status": "derived", "years_available": 8, "source": "computed from total_debt - cash_and_equivalents"},
        {"field": "total_debt", "label": "Total Debt", "status": "present", "years_available": 7, "source": "direct"}
      ],
      "helpful_fields": [...],
      "missing_impact": null,
      "notes": []
    },
    "ddm": {
      "verdict": "not_possible",
      "verdict_label": "Not Possible",
      "detection_score": 15,
      "critical_fields": [
        {"field": "dividends_paid", "label": "Dividends Paid", "status": "missing", "years_available": 0, "source": null}
      ],
      "important_fields": [...],
      "helpful_fields": [...],
      "missing_impact": "DDM not possible: no dividend history found. This company does not appear to pay dividends.",
      "notes": ["No dividend data in any of the 8 available fiscal years"]
    }
  },
  "detection_result": {
    "recommended_model": "dcf",
    "confidence": "High",
    "confidence_percentage": 82
  }
}
```

**Files touched:**
- `backend/services/data_readiness_service.py` — new file with readiness analysis logic
- `backend/routers/models_router.py` — add new endpoint
- `backend/main.py` — initialize and register data readiness service on app.state

#### 1C. Frontend — Data Readiness Sub-Tab

**Goal:** 4th sub-tab inside Historical Data that renders the readiness report.

**Layout:**
```
┌─────────────────────────────────────────────────────────────────────┐
│ [Income Statement] [Balance Sheet] [Cash Flow] [Data Readiness]     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ DATA COVERAGE                                                        │
│ ┌──────────────────────────────────────────────────────┐            │
│ │ 8 years available · 42/48 fields populated (87.5%)   │            │
│ │ ████████████████████████████████████░░░░░             │            │
│ └──────────────────────────────────────────────────────┘            │
│                                                                      │
│ ENGINE READINESS                                                     │
│                                                                      │
│ ┌── DCF ──────────────────────────────────────── ✓ Ready ──────┐   │
│ │ Detection Score: 82/100                                        │   │
│ │                                                                │   │
│ │ Critical (4/4 present)                                         │   │
│ │  ✓ Revenue .............. 8 years · direct from Yahoo Finance  │   │
│ │  ✓ Operating Cash Flow .. 8 years · direct from Yahoo Finance  │   │
│ │  ✓ Capital Expenditures . 8 years · direct from Yahoo Finance  │   │
│ │  ✓ Shares Outstanding ... 8 years · direct from Yahoo Finance  │   │
│ │                                                                │   │
│ │ Important (7/8 present)                                        │   │
│ │  ✓ Net Debt ............. 8 years · computed (debt - cash)     │   │
│ │  ✓ Total Debt ........... 7 years · direct from Yahoo Finance  │   │
│ │  ✗ Tax Provision ........ 0 years · MISSING                    │   │
│ │    → Fallback: uses default 21% corporate rate                 │   │
│ │  ...                                                           │   │
│ └────────────────────────────────────────────────────────────────┘   │
│                                                                      │
│ ┌── DDM ─────────────────────────────────── ✗ Not Possible ────┐   │
│ │ Detection Score: 15/100                                        │   │
│ │                                                                │   │
│ │ Critical (1/2 present)                                         │   │
│ │  ✗ Dividends Paid ....... 0 years · MISSING                    │   │
│ │    → DDM not possible: no dividend history found               │   │
│ │  ✓ Shares Outstanding ... 8 years · direct from Yahoo Finance  │   │
│ └────────────────────────────────────────────────────────────────┘   │
│                                                                      │
│ ┌── Comps ───────────────────────────────────── ✓ Ready ───────┐   │
│ │ ...                                                            │   │
│ └────────────────────────────────────────────────────────────────┘   │
│                                                                      │
│ ┌── Revenue-Based ───────────────────────── ⚠ Partial ─────────┐   │
│ │ ...                                                            │   │
│ └────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

**Behavior:**
- Each engine section is a collapsible card (expanded by default for engines with issues, collapsed for "Ready" engines)
- Verdict badge color-coded: green "Ready", yellow "Partial", red "Not Possible"
- Detection score shown per engine (from the existing model detection service)
- Each field row shows: status icon (✓/✗/~), field label, years of data, source type (direct/computed/missing)
- Missing fields with important or critical status show an indented note explaining the downstream impact
- Coverage bar at top is a simple progress bar
- Data refreshes when the ticker changes (same pattern as other tabs)

**State:**
- Fetches from the new `/api/v1/model-builder/{ticker}/data-readiness` endpoint
- Local component state only (no store needed — this is read-only diagnostic data)

**Files touched:**
- `frontend/src/pages/ModelBuilder/Historical/DataReadinessTab.tsx` — new file
- `frontend/src/pages/ModelBuilder/Historical/DataReadinessTab.module.css` — new file
- `frontend/src/pages/ModelBuilder/Historical/HistoricalDataTab.tsx` — add 4th sub-tab, import DataReadinessTab
- `frontend/src/types/models.ts` — add DataReadinessResult interfaces

---

## AREA 2: DIAGNOSTIC OVERLAY TOGGLE

### Concept

A toggle switch on the financial statement tables (Income Statement, Balance Sheet, Cash Flow) that activates a diagnostic inspection layer. When off, the table looks exactly as it does now. When on, cells become interactive inspection targets showing where each number came from and how it's used downstream.

### What Changes

#### 2A. Toggle Control

**UI:** A small toggle switch in the sub-tab bar area, right-aligned. Label: "Inspect" or a small magnifying glass icon. Apple-style liquid glass aesthetic — subtle frosted/translucent look.

**Behavior:**
- Default: off. Table looks exactly as it does now.
- When toggled on: populated cells gain a glass-bubble visual treatment, missing-but-important cells gain a warning marker.
- Toggle state persists during the session (stored in local component state or uiStore) but resets on app restart.

**Files touched:**
- `frontend/src/pages/ModelBuilder/Historical/HistoricalDataTab.tsx` — add toggle state, pass to table rendering
- `frontend/src/pages/ModelBuilder/Historical/HistoricalDataTab.module.css` — toggle switch styles

#### 2B. Populated Cell Treatment (Glass Bubble)

**Visual:**
- Each populated cell gets a subtle glass-bubble indicator: a slight frosted/translucent background with a very faint border, giving a "liquid glass" feel. Think: iOS frosted glass effect but minimal — just enough to signal interactivity.
- The bubble should not disrupt readability of the number. The number stays the same size, color, and position.
- On hover: the bubble highlights slightly brighter, cursor changes to indicate clickability.

**Popover on hover/click:**
A small detail card appears to the right of the cell (or left if near the edge). Contents:
```
┌──────────────────────────────────┐
│ Revenue · FY 2024                │
│ $394.3B                          │
│──────────────────────────────────│
│ Source: Yahoo Finance (direct)   │
│ Years available: 8               │
│──────────────────────────────────│
│ Used by:                         │
│  • DCF — critical (projection)  │
│  • Comps — critical (EV/Rev)    │
│  • Revenue — critical (core)    │
│  • DDM — helpful (context)      │
└──────────────────────────────────┘
```

- Shows: field label, fiscal year, formatted value, source type (direct/computed with derivation formula), years of data, and which engines use this field at which criticality level.
- Popover dismisses on mouse leave or clicking elsewhere.
- For computed/derived fields, source shows the formula: "Computed: operating_cash_flow + capital_expenditure"

**Data source:** The same data readiness endpoint (`/api/v1/model-builder/{ticker}/data-readiness`) provides all the metadata needed. The frontend fetches this once when the toggle is activated and caches it for the session. A lookup map is built: `field_key → {source, years, engines[]}` so each cell can be annotated without additional API calls.

**Files touched:**
- `frontend/src/pages/ModelBuilder/Historical/HistoricalDataTab.tsx` — cell rendering logic when overlay is active, popover component
- `frontend/src/pages/ModelBuilder/Historical/HistoricalDataTab.module.css` — glass bubble styles, popover styles, hover states

#### 2C. Missing-but-Important Cell Treatment

**Visual:**
- Missing cells ("—") that are flagged as **critical** for any engine: subtle red/amber dot or underline indicator. No glass bubble (nothing to inspect in the number), but the indicator signals "this gap matters."
- Missing cells that are **important** (not critical) for any engine: subtle amber dot.
- Missing cells with no engine dependency: nothing. Left as plain "—".

**On hover:** Same popover pattern, but content focuses on impact:
```
┌──────────────────────────────────┐
│ Dividends Paid · FY 2024         │
│ NOT REPORTED                     │
│──────────────────────────────────│
│ Impact:                          │
│  • DDM — CRITICAL (missing)     │
│    DDM not possible without      │
│    dividend history               │
│  • DCF — not needed              │
└──────────────────────────────────┘
```

**Files touched:**
- `frontend/src/pages/ModelBuilder/Historical/HistoricalDataTab.tsx` — missing cell indicator logic
- `frontend/src/pages/ModelBuilder/Historical/HistoricalDataTab.module.css` — indicator dot styles, impact popover styles

#### 2D. Backend Support

The existing data readiness endpoint (Area 1B) already provides everything needed:
- Per-field status (present/missing/derived)
- Per-field source type and derivation info
- Per-field engine usage with criticality level
- Years available per field

The frontend builds a lookup map from this response. **No additional backend work needed** beyond what's already planned in Area 1B.

To support the cell-level overlay, the data readiness response should also include a flat `field_metadata` map for quick lookup:
```json
{
  "field_metadata": {
    "revenue": {
      "status": "present",
      "source": "direct",
      "source_detail": "Yahoo Finance",
      "years_available": 8,
      "engines": [
        {"engine": "dcf", "level": "critical", "reason": "Base for 10-year projection"},
        {"engine": "comps", "level": "critical", "reason": "EV/Revenue multiple"},
        {"engine": "revenue_based", "level": "critical", "reason": "Core input"},
        {"engine": "ddm", "level": "helpful", "reason": "Growth context"}
      ]
    },
    "dividends_paid": {
      "status": "missing",
      "source": null,
      "source_detail": null,
      "years_available": 0,
      "engines": [
        {"engine": "ddm", "level": "critical", "reason": "Core DDM input"}
      ]
    }
  }
}
```

This flat map is added to the data readiness endpoint response (Area 1B) so the frontend can look up any field instantly.

**Files touched:**
- `backend/services/data_readiness_service.py` — add `field_metadata` flat map to response (minor addition to existing Area 1B work)

---

## AREA 3: MINOR HISTORICAL DATA POLISH

#### 3A. Blank Field Awareness
**Current:** Blank fields show as "—" with no explanation.
**Change:** When hovering over a "—" cell, show a small tooltip: "Not reported by {ticker}" or "Not available from Yahoo Finance." This helps distinguish "this company doesn't report this" from "there's a data extraction bug."

**Files touched:**
- `frontend/src/pages/ModelBuilder/Historical/HistoricalDataTab.tsx` — add hover tooltip on missing cells
- `frontend/src/pages/ModelBuilder/Historical/HistoricalDataTab.module.css` — tooltip styles

#### 3B. Data Freshness Indicator
**Current:** No indication of when the data was last fetched.
**Change:** Small text below the sub-tab bar: "Data as of {date} · {N} fiscal years" with a refresh button that force-refetches from Yahoo Finance.

**Files touched:**
- `frontend/src/pages/ModelBuilder/Historical/HistoricalDataTab.tsx` — add freshness indicator, refresh button
- Backend already supports `force_refresh` parameter on the financials endpoint

---

## SESSION ORGANIZATION (Recommended for PM)

### Session 8B — Data Readiness Backend (Backend Only)
**Scope:** Areas 1A, 1B (including field_metadata flat map for overlay support)
**Files:**
- `backend/services/engine_dependency_map.py` — new file
- `backend/services/data_readiness_service.py` — new file (includes field_metadata map)
- `backend/routers/models_router.py` — add endpoint
- `backend/main.py` — wire up service
**Complexity:** Medium (dependency map is design work, analysis logic is straightforward queries)
**Estimated acceptance criteria:** 12–15

### Session 8C — Data Readiness Tab + Diagnostic Overlay + Historical Polish (Frontend Only)
**Scope:** Areas 1C, 2A–2D, 3A, 3B
**Files:**
- `frontend/src/pages/ModelBuilder/Historical/DataReadinessTab.tsx` — new file
- `frontend/src/pages/ModelBuilder/Historical/DataReadinessTab.module.css` — new file
- `frontend/src/pages/ModelBuilder/Historical/HistoricalDataTab.tsx` — add 4th sub-tab, overlay toggle, glass bubble rendering, popover, missing cell indicators, tooltip, freshness
- `frontend/src/pages/ModelBuilder/Historical/HistoricalDataTab.module.css` — glass bubble styles, popover, toggle, indicator dots, tooltip styles
- `frontend/src/types/models.ts` — add interfaces
**Complexity:** Medium-High (Data Readiness tab is straightforward; overlay toggle with glass bubbles, popovers, and cell-level metadata lookup adds significant frontend work)
**Estimated acceptance criteria:** 22–28
**Depends on:** Session 8B (backend endpoint must exist)

---

## DEPENDENCIES & RISKS

| Risk | Mitigation |
|------|------------|
| Engine dependency map becomes stale as engines evolve | Keep dependency map as a single-source-of-truth file that's easy to update; add a comment in each engine file referencing it |
| Derived field detection accuracy | Start with known derivations (FCF = OCF + CapEx, net_debt = debt - cash, margins = X/revenue). Unknown derivations labeled as "direct" |
| Companies with unusual reporting (banks, REITs, etc.) | Add a note in the response when sector is Financial — "Some fields may not apply to financial companies" |
| Field names between cache DB and dependency map diverge | Dependency map uses the exact column names from `cache.financial_data` schema |

---

## DECISIONS MADE

1. Data Readiness is a 4th sub-tab inside Historical Data (not a standalone Model Builder tab)
2. Three criticality levels: Critical, Important, Helpful
3. Three verdicts per engine: Ready, Partial, Not Possible
4. Source tracking: direct (from Yahoo), computed (derived from other fields), missing
5. Collapsible engine cards — expanded by default when issues exist, collapsed when Ready
6. Dependency map is a single Python file that all services can reference
7. Detection scores from existing model_detection_service surfaced alongside readiness
8. Diagnostic overlay toggle on financial tables — off by default, activates glass-bubble cell inspection
9. Populated cells get glass-bubble + hover popover showing source, engine usage, derivation
10. Missing cells only get indicators if they are critical or important for an engine — plain missing cells stay as "—" with no marker
11. Overlay uses same data readiness endpoint data (field_metadata flat map) — no extra API calls
12. Hover tooltips on blank "—" cells in the financial table for context
13. Data freshness indicator with manual refresh option

---

*End of Model Builder — Historical Data Sub-Tab Update Plan*
*Phase 8B–8C · Prepared March 5, 2026*
