# Finance App v2.0 — Master Update Plan Index
## For PM Agent: Single Source of Truth

**Prepared by:** Planner (March 5, 2026)
**Owner:** Finn
**App:** Finance App v1.0 → v2.0 (Desktop Equity Valuation Tool)
**Stack:** Electron + React + FastAPI + SQLite

---

## HOW TO USE THIS DOCUMENT

This is the master index for all update plans. Each phase has its own spec file(s) in `specs/`. The PM should:
1. Read this index to understand scope, session order, and dependencies
2. Read each spec file for full detail before writing Builder prompts
3. Follow the recommended build order below
4. Include the Display Name Rule (from `cross_cutting_underscore_cleanup.md`) in every Builder prompt

---

## PHASE STRUCTURE

| Phase | Module | Spec File(s) | Sessions | Est. Acceptance Criteria |
|-------|--------|--------------|----------|--------------------------|
| **7** | Dashboard | `phase7_dashboard.md` | 7A–7E | 59–75 |
| **8** | Model Builder | 7 spec files (see below) | 8A–8O | 260–335 |
| **9** | Scanner | `phase9_scanner.md` | 9A–9C | 40–49 |
| **10** | Portfolio | 3 spec files (see below) | 10A–10F | 107–133 |
| **11** | Research | `phase11_research.md` | 11A–11D | 68–87 |
| **12** | Settings | No changes | — | — |
| **13** | Export | No changes | — | — |
| **14** | Packaging | `phase14_packaging_distribution.md` | 14A (14B deferred) | 12–15 |
| **X** | Cross-cutting | `cross_cutting_underscore_cleanup.md` | Enforced in all sessions | — |

**Total: ~40 Builder sessions, ~550–700 acceptance criteria**

---

## SPEC FILE INVENTORY

```
specs/
├── MASTER_INDEX.md                              ← THIS FILE
├── cross_cutting_underscore_cleanup.md           ← Display name rules for ALL sessions
│
├── phase7_dashboard.md                           ← Sessions 7A–7E
│
├── phase8_model_builder_overview.md              ← Session 8A
├── phase8_model_builder_historical.md            ← Sessions 8B–8C
├── phase8_model_builder_assumptions_general.md   ← Session 8D
├── phase8_model_builder_assumptions_wacc.md      ← Sessions 8E–8F
├── phase8_model_builder_assumptions_monte_carlo.md ← Session 8G
├── phase8_model_builder_model.md                 ← Sessions 8H–8K
├── phase8_model_builder_sensitivity.md           ← Sessions 8L–8N
├── phase8_model_builder_history.md               ← Session 8O
│
├── phase9_scanner.md                             ← Sessions 9A–9C
│
├── phase10_portfolio_holdings.md                 ← Sessions 10A–10B
├── phase10_portfolio_performance.md              ← Sessions 10C–10D
├── phase10_portfolio_remaining.md                ← Sessions 10E–10F
│
├── phase11_research.md                           ← Sessions 11A–11D
│
└── phase14_packaging_distribution.md             ← Session 14A (14B deferred)
```

---

## COMPLETE SESSION MAP

### Phase 7 — Dashboard
| Session | Scope | Type | Depends On | Priority |
|---------|-------|------|------------|----------|
| 7A | Boot sequence + dashboard animations | Frontend | — | Normal |
| 7B | Sound infrastructure | Frontend | — | Low |
| 7C | Events backend (S&P 500 list, fetcher, filtered endpoint) | Backend | — | Normal |
| 7D | Events frontend (dashboard widget + portfolio sub-tab) | Frontend | 7C | Normal |
| 7E | Error handling polish | Frontend | — | Low |

### Phase 8 — Model Builder
| Session | Scope | Type | Depends On | Priority |
|---------|-------|------|------------|----------|
| 8A | Overview overhaul (football field, layout, **creates displayNames.ts**) | Frontend | — | Normal |
| 8B | Data Readiness backend (dependency map, readiness endpoint) | Backend | — | Normal |
| 8C | Data Readiness frontend + diagnostic overlay toggle | Frontend | 8B | Normal |
| 8D | Assumptions general fixes (terminal clip, scenario reorder, confidence, sync prep) | Frontend | — | Normal |
| 8E | WACC backend (expose components, override path) | Backend | — | Normal |
| 8F | WACC frontend (detailed buildout, live recalculation) | Frontend | 8E | Normal |
| 8G | Monte Carlo assumption engine | Backend | — | Normal |
| 8H | Comps backend (peer discovery, null safety) | Backend | — | **High** |
| 8I | Comps frontend + error boundary + underscore fix + export button | Frontend | 8H | **High** |
| 8J | DDM & Revenue-Based detail upgrade | Frontend | — | Normal |
| 8K | DCF key outputs & waterfall chart upgrade | Frontend | — | Normal |
| 8L | Sensitivity backend (precision, range params) | Backend | — | Normal |
| 8M | Sliders + state persistence + assumptions sync | Frontend | 8L, 8D | Normal |
| 8N | Tornado + Monte Carlo + Data Tables frontend | Frontend | 8L | Normal |
| 8O | History fix (auto-save on run, Save macro, snapshot formatting) | Mixed | — | Normal |

### Phase 9 — Scanner
| Session | Scope | Type | Depends On | Priority |
|---------|-------|------|------------|----------|
| 9A | Universe data files + backend loader | Backend | — | **High** |
| 9B | Universe hydration service (background fetch) | Backend | 9A | **High** |
| 9C | Scanner frontend (filters, dynamic columns, formatting) | Frontend | 9A | Normal |

### Phase 10 — Portfolio
| Session | Scope | Type | Depends On | Priority |
|---------|-------|------|------------|----------|
| 10A | CSV import + edit position backend | Backend | — | Normal |
| 10B | Holdings frontend (import, context menu, hover card, edit) | Frontend | 10A | Normal |
| 10C | **CRITICAL: Live data fix** (startup refresh, after-hours, day_change_pct, profiles) | Backend | — | **CRITICAL** |
| 10D | Performance frontend + refresh button + WebSocket subscription | Frontend | 10C | **High** |
| 10E | Income backend + allocation ETF fix | Backend | — | Normal |
| 10F | Income + allocation + transactions frontend | Frontend | 10E, Phase 7 events | Normal |

### Phase 11 — Research
| Session | Scope | Type | Depends On | Priority |
|---------|-------|------|------------|----------|
| 11A | **CRITICAL: Data accuracy normalization** (full pipeline audit) | Backend | — | **CRITICAL** |
| 11B | Profile + filings + frontend accuracy verification | Mixed | 11A | **High** |
| 11C | Trend chart Fidelity upgrade + DuPont ROE fix | Frontend | 11A | Normal |
| 11D | Stock price charts (line/candlestick, volume, MAs) | Frontend | — | Normal |

### Phase 14 — Packaging
| Session | Scope | Type | Depends On | Priority |
|---------|-------|------|------------|----------|
| 14A | Bundle Python + GitHub Releases distribution | Mixed | All features complete | Last |
| 14B | macOS build (DEFERRED) | Mixed | 14A, Apple Dev account | Deferred |

---

## RECOMMENDED BUILD ORDER

The PM should prioritize sessions in this order:

### Tier 1 — Critical Data Fixes (Do First)
These fix broken data that undermines every module:
1. **11A + 10C** (merge into one session) — Full data pipeline normalization + live refresh fix
2. **10D** — Performance frontend + WebSocket + refresh button (depends on 10C)

### Tier 2 — Blocking Bugs
3. **8H + 8I** — Comps crash fix + error boundary (the app literally crashes on Comps)
4. **8D** — Terminal value clipping + scenario reorder + sync prep

### Tier 3 — Universe & Infrastructure
5. **9A** — Universe data files (S&P 500, DOW, R3000) — shared asset needed by Phase 7 and 9
6. **9B** — Universe hydration (background data fetch)
7. **7C** — Events backend (uses S&P 500 list from 9A)

### Tier 4 — Feature Sessions (Any Order Within Phase)
Run remaining sessions grouped by phase, respecting dependency chains:
- Phase 7: 7A → 7D → 7B → 7E
- Phase 8: 8A → 8B → 8C → 8E → 8F → 8G → 8J → 8K → 8L → 8M → 8N → 8O
- Phase 9: 9C
- Phase 10: 10A → 10B → 10E → 10F
- Phase 11: 11B → 11C → 11D

### Tier 5 — Packaging (Last)
- Phase 14: 14A (after all features are complete and tested)

---

## SHARED ASSETS

| Asset | Created In | Used By | Note |
|-------|-----------|---------|------|
| `backend/data/sp500_tickers.json` | 9A | 7C, 9B | Build once, shared. Include company names, sectors, industries. |
| `backend/data/dow_tickers.json` | 9A | 9B | DOW 30 tickers with metadata |
| `backend/data/russell3000_tickers.json` | 9A | 9B | Russell 3000 tickers with metadata |
| `frontend/src/utils/displayNames.ts` | 8A | All frontend sessions | Shared display name utility. See `cross_cutting_underscore_cleanup.md` |

---

## CRITICAL CROSS-CUTTING RULES

### 1. Display Name Rule (Every Session)
> All backend snake_case keys displayed in the UI must use the shared `displayNames.ts` utility. Never show raw keys like `revenue_based` or `high_growth`. Never use inline `.replace(/_/g, ' ')`. Always import from `@/utils/displayNames`.

See `cross_cutting_underscore_cleanup.md` for full spec, known leak points, and utility code.

### 2. Chart Quality Directive (Every Frontend Session with Charts)
> All graphs and charts must meet Fidelity/Yahoo Finance information-density standards: proper labels, hover tooltips with full detail, crosshairs, value annotations on bars/lines, responsive formatting, compact axis labels. No decorative or minimal charts.

### 3. Data Format Convention (Every Backend Session)
> All ratios and percentages stored as decimal ratios (0.15 = 15%). Frontend `fmtPct()` multiplies by 100. No exceptions. See Session 11A for the full normalization spec.

### 4. Scenario Order Convention (Every Frontend Session with Scenarios)
> Bear / Base / Bull (left to right). Base is always the default selection. Applies to Assumptions, Model views, Sensitivity, and Overview.

---

## COORDINATION NOTES

### 10C ↔ 11A: Data Integrity
Sessions 10C and 11A both fix the same root cause (percentage format mismatch in the data pipeline). They modify overlapping files (`yahoo_finance.py`, `market_data_service.py`, `data_extraction_service.py`). The PM must either merge them into one session or run 11A first, then 10C.

### 8D ↔ 8M: Slider Sync
Session 8D creates the `modelStore` infrastructure for slider↔assumptions sync. Session 8M implements the full UI. 8D must run before 8M.

### 7C ↔ 9A: S&P 500 List
Phase 7C (events backend) needs the S&P 500 ticker list. Phase 9A creates it. Either run 9A first, or extract the S&P 500 JSON creation into a standalone micro-session before both.

### 8O ↔ 8I Area 7: Export Button
Session 8I adds export buttons to model views, but export requires `activeModelId` which only exists after 8O's auto-save-on-run feature. 8O should run before or alongside 8I.

### 10E/10F ↔ Phase 7: Upcoming Dividends
The Income tab's "Upcoming Dividends" component (10F) pulls from the events system built in Phase 7. If Phase 7 hasn't been built yet, show a placeholder.

---

*End of Master Update Plan Index*
*Prepared March 5, 2026*
