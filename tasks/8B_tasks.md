# Session 8B — Data Readiness Backend (Dependency Map + Readiness Endpoint)
## Phase 8: Model Builder

**Priority:** Normal
**Type:** Backend Only
**Depends On:** None
**Spec Reference:** `specs/phase8_model_builder_historical.md` → Areas 1A, 1B

---

## SCOPE SUMMARY

Create a formal engine dependency map defining what financial fields each valuation engine requires at what criticality level. Build a new `/api/v1/model-builder/{ticker}/data-readiness` endpoint that checks cached financial data against this map and returns a structured readiness report per engine (Ready / Partial / Not Possible), including a flat `field_metadata` map for cell-level overlay support in the frontend.

---

## TASKS

### Task 1: Create Engine Dependency Map
**Description:** Define a single-source-of-truth Python module that maps each valuation engine to its required financial fields with criticality levels and reasoning.

**Subtasks:**
- [ ] 1.1 — Create `backend/services/engine_dependency_map.py` with an `ENGINE_DEPENDENCIES` dictionary.
- [ ] 1.2 — Define dependencies for 4 engines: `dcf`, `ddm`, `comps`, `revenue_based`.
- [ ] 1.3 — Each engine entry has 3 criticality tiers: `critical`, `important`, `helpful`. Each tier is a list of dicts with `field` (exact column name from `cache.financial_data`), `label` (display name), and `reason` (why this engine needs it).
- [ ] 1.4 — DCF critical fields: `revenue`, `operating_cash_flow`, `capital_expenditure`, `shares_outstanding`. Important: `net_debt`, `total_debt`, `cash_and_equivalents`, `ebit`, `gross_profit`, `stockholders_equity`, `depreciation_amortization`, `tax_provision`. Helpful: `ebitda`, `free_cash_flow`, `net_income`.
- [ ] 1.5 — DDM critical fields: `dividends_paid`, `shares_outstanding`. Important: `net_income`, `free_cash_flow`, `stockholders_equity`. Helpful: `revenue`, `operating_cash_flow`.
- [ ] 1.6 — Comps critical fields: `revenue`, `ebitda`, `net_income`, `shares_outstanding`. Important: `total_debt`, `cash_and_equivalents`, `free_cash_flow`, `stockholders_equity`. Helpful: `gross_profit`, `operating_margin`.
- [ ] 1.7 — Revenue-Based critical fields: `revenue`, `shares_outstanding`. Important: `operating_margin`, `gross_profit`, `ebitda`. Helpful: `free_cash_flow`, `net_income`.
- [ ] 1.8 — Add a module-level `KNOWN_DERIVATIONS` dict that maps computed fields to their derivation formula. E.g. `"free_cash_flow": "operating_cash_flow + capital_expenditure"`, `"net_debt": "total_debt - cash_and_equivalents"`, `"gross_margin": "gross_profit / revenue"`, etc.

**Implementation Notes:**
- Field names must exactly match column names in `cache.financial_data` schema (from `init_cache_db.py`). The full column list includes: `revenue, cost_of_revenue, gross_profit, operating_expense, rd_expense, sga_expense, ebit, interest_expense, tax_provision, net_income, ebitda, depreciation_amortization, eps_basic, eps_diluted, total_assets, current_assets, cash_and_equivalents, total_liabilities, current_liabilities, long_term_debt, short_term_debt, total_debt, stockholders_equity, working_capital, net_debt, operating_cash_flow, capital_expenditure, free_cash_flow, dividends_paid, change_in_working_capital, investing_cash_flow, financing_cash_flow, shares_outstanding, market_cap_at_period, beta_at_period, dividend_per_share, gross_margin, operating_margin, net_margin, fcf_margin, revenue_growth, ebitda_margin, roe, debt_to_equity, payout_ratio`.
- `KNOWN_DERIVATIONS` is used by the readiness service to distinguish "direct from Yahoo" vs. "computed from other fields" when annotating field sources.

---

### Task 2: Create Data Readiness Service
**Description:** Build a service that analyzes a ticker's cached financial data against the engine dependency map and produces a detailed readiness report.

**Subtasks:**
- [ ] 2.1 — Create `backend/services/data_readiness_service.py` with class `DataReadinessService`.
- [ ] 2.2 — Constructor: `__init__(self, db: DatabaseConnection, model_detection_svc)`. The detection service provides existing confidence scores/reasoning.
- [ ] 2.3 — Main method: `async def get_readiness(self, ticker: str) -> dict`:
  1. Fetch all financial records for the ticker from `cache.financial_data` (ordered by fiscal_year DESC)
  2. Fetch market data from `cache.market_data`
  3. Compute coverage stats: total fields, populated fields, coverage_pct, data_years_available
  4. For each engine in `ENGINE_DEPENDENCIES`:
     - Walk each field in critical/important/helpful tiers
     - Check if field is non-null in the most recent year
     - Count how many years have this field
     - Classify as `present`, `missing`, or `derived` (check `KNOWN_DERIVATIONS`)
     - Determine verdict: if any critical field is missing → `not_possible`; if any important field is missing → `partial`; else → `ready`
     - Generate `missing_impact` text for not_possible/partial cases
     - Include detection score from `model_detection_svc.detect(ticker)` if available
  5. Build the flat `field_metadata` map (for overlay support): every field in the financial schema → `{status, source, source_detail, years_available, engines: [{engine, level, reason}]}`
  6. Return full response dict
- [ ] 2.4 — Helper method `_classify_field(field_name, financial_rows) -> tuple[str, int, str]`: returns `(status, years_available, source_type)` where status is `present`/`missing`/`derived`, and source_type is `direct`/`computed from X`/`null`.
- [ ] 2.5 — Helper method `_generate_verdict(engine_name, field_statuses) -> tuple[str, str, str | None]`: returns `(verdict, verdict_label, missing_impact)`.
- [ ] 2.6 — Helper method `_build_field_metadata(financial_rows) -> dict`: builds the flat lookup map across all engines for every field in the schema.

**Implementation Notes:**
- The `_classify_field` method checks the most recent year's row first. If the field is non-null, it's `present`. If null but the field appears in `KNOWN_DERIVATIONS` and the source fields are present, classify as `derived`. Otherwise `missing`.
- Years available: count how many rows (fiscal years) have a non-null value for this field.
- Source types: `"direct"` (from Yahoo Finance), `"computed from {formula}"` (from KNOWN_DERIVATIONS), `null` (missing).
- Detection scores: call `model_detection_svc.detect(ticker)` and extract per-engine scores. If detection fails, use null scores.
- Coverage stats: iterate all columns in the most recent year's row, count non-null values. Total fields = number of financial columns (excluding id, ticker, fiscal_year, period_type, statement_date, data_source, fetched_at).

---

### Task 3: Add Data Readiness Endpoint
**Description:** Register the new endpoint in the models router.

**Subtasks:**
- [ ] 3.1 — In `backend/routers/models_router.py`, add:
  ```python
  @router.get("/{ticker}/data-readiness")
  async def get_data_readiness(ticker: str, request: Request):
      """Data readiness analysis for all engines."""
      try:
          svc = request.app.state.data_readiness_service
          result = await svc.get_readiness(ticker.upper())
          return success_response(data=result)
      except Exception as exc:
          logger.exception("Data readiness failed for %s", ticker)
          return error_response("DATA_READINESS_ERROR", str(exc))
  ```

---

### Task 4: Wire Up Service in main.py
**Description:** Initialize DataReadinessService during app startup and register on app.state.

**Subtasks:**
- [ ] 4.1 — In `backend/main.py`, in the lifespan function, after model_detection_svc is initialized:
  ```python
  from services.data_readiness_service import DataReadinessService
  data_readiness_svc = DataReadinessService(db=db, model_detection_svc=model_detection_svc)
  app.state.data_readiness_service = data_readiness_svc
  logger.info("Data readiness service initialized.")
  ```

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: `backend/services/engine_dependency_map.py` exists with `ENGINE_DEPENDENCIES` for dcf, ddm, comps, revenue_based.
- [ ] AC-2: Each engine has `critical`, `important`, `helpful` tiers with `field`, `label`, `reason` per entry.
- [ ] AC-3: Field names in dependency map exactly match `cache.financial_data` column names.
- [ ] AC-4: `KNOWN_DERIVATIONS` dict maps at least: `free_cash_flow`, `net_debt`, `gross_margin`, `operating_margin`, `net_margin`, `fcf_margin`, `ebitda_margin`, `roe`, `debt_to_equity`.
- [ ] AC-5: `backend/services/data_readiness_service.py` exists with `DataReadinessService` class.
- [ ] AC-6: `GET /api/v1/model-builder/{ticker}/data-readiness` returns a structured response.
- [ ] AC-7: Response includes `ticker`, `data_years_available`, `total_fields`, `populated_fields`, `coverage_pct`.
- [ ] AC-8: Response `engines` dict has entries for all 4 engines with `verdict`, `verdict_label`, `detection_score`.
- [ ] AC-9: Each engine entry has `critical_fields`, `important_fields`, `helpful_fields` arrays with per-field `status`, `years_available`, `source`.
- [ ] AC-10: Verdict logic: missing critical → `not_possible`, missing important → `partial`, all present → `ready`.
- [ ] AC-11: `missing_impact` text is populated for `not_possible` and `partial` verdicts with plain-English explanation.
- [ ] AC-12: Response includes `field_metadata` flat map with every financial field → `{status, source, source_detail, years_available, engines[]}`.
- [ ] AC-13: `field_metadata` engines array per field includes `{engine, level, reason}` for every engine that uses this field.
- [ ] AC-14: Response includes `detection_result` with `recommended_model`, `confidence`, `confidence_percentage` from the detection service.
- [ ] AC-15: Derived fields correctly classified as `"derived"` with source showing the formula (e.g. `"computed from operating_cash_flow + capital_expenditure"`).
- [ ] AC-16: Service is registered on `app.state.data_readiness_service` and endpoint is accessible.
- [ ] AC-17: Endpoint handles errors gracefully — returns error response, doesn't crash.

---

## FILES TOUCHED

**New files:**
- `backend/services/engine_dependency_map.py` — engine dependency map and known derivations
- `backend/services/data_readiness_service.py` — data readiness analysis service

**Modified files:**
- `backend/routers/models_router.py` — add `GET /{ticker}/data-readiness` endpoint
- `backend/main.py` — initialize and register DataReadinessService

---

## BUILDER PROMPT

> **Session 8B — Data Readiness Backend (Dependency Map + Readiness Endpoint)**
>
> You are building session 8B of the Finance App v2.0 update.
>
> **What you're doing:** Creating a formal engine dependency map and a data readiness analysis endpoint that checks a ticker's cached financial data against what each valuation engine requires, producing a structured per-engine readiness report.
>
> **Context:** The app has 4 valuation engines (DCF, DDM, Comps, Revenue-Based). Each requires different financial data fields to run. Currently, model detection scores engines 0-100, but there's no explicit dependency mapping or readiness analysis. You're creating this so the frontend can show users exactly what data exists, what's missing, and how it impacts each engine.
>
> **Existing code:**
> - `backend/services/model_detection_service.py` — `ModelDetectionService.detect(ticker)` returns `ModelDetectionResult` with per-engine scores (0-100), `recommended_model`, `confidence`. Constructor: `__init__(db, data_extraction)`.
> - `backend/repositories/market_data_repo.py` — `get_financials(ticker, years)` returns rows from `cache.financial_data`. `get_market_data(ticker)` returns from `cache.market_data`.
> - `backend/db/init_cache_db.py` — `cache.financial_data` schema with 48 columns including: `revenue, cost_of_revenue, gross_profit, operating_expense, rd_expense, sga_expense, ebit, interest_expense, tax_provision, net_income, ebitda, depreciation_amortization, eps_basic, eps_diluted, total_assets, current_assets, cash_and_equivalents, total_liabilities, current_liabilities, long_term_debt, short_term_debt, total_debt, stockholders_equity, working_capital, net_debt, operating_cash_flow, capital_expenditure, free_cash_flow, dividends_paid, change_in_working_capital, investing_cash_flow, financing_cash_flow, shares_outstanding, market_cap_at_period, beta_at_period, dividend_per_share, gross_margin, operating_margin, net_margin, fcf_margin, revenue_growth, ebitda_margin, roe, debt_to_equity, payout_ratio`. Non-data columns: `id, ticker, fiscal_year, period_type, statement_date, data_source, fetched_at`.
> - `backend/routers/models_router.py` — existing model builder routes under `/api/v1/model-builder`. You're adding a new GET endpoint.
> - `backend/main.py` — lifespan function initializes all services on `app.state`. `model_detection_svc` already exists.
>
> **Cross-cutting rules:**
> - Display Name Rule: All backend snake_case keys displayed in the UI must use the shared `displayNames.ts` utility. (Backend session — ensure field labels in the dependency map use proper display names.)
> - Chart Quality: All charts must meet Fidelity/Yahoo Finance information-density standards.
> - Data Format: All ratios/percentages stored as decimal ratios (0.15 = 15%).
> - Scenario Order: Bear / Base / Bull (left to right), Base default.
>
> **Task 1: Create Engine Dependency Map**
>
> Create `backend/services/engine_dependency_map.py`:
>
> ```python
> """Engine dependency map — defines what financial fields each valuation engine requires.
>
> Single source of truth. Referenced by DataReadinessService and diagnostic overlay.
> Field names must exactly match cache.financial_data column names.
> """
>
> ENGINE_DEPENDENCIES: dict[str, dict[str, list[dict]]] = {
>     "dcf": {
>         "critical": [
>             {"field": "revenue", "label": "Revenue", "reason": "Base for 10-year projection"},
>             {"field": "operating_cash_flow", "label": "Operating Cash Flow", "reason": "FCF derivation"},
>             {"field": "capital_expenditure", "label": "Capital Expenditures", "reason": "FCF derivation"},
>             {"field": "shares_outstanding", "label": "Shares Outstanding", "reason": "Per-share price calculation"},
>         ],
>         "important": [
>             {"field": "net_debt", "label": "Net Debt", "reason": "Equity bridge (EV to equity)"},
>             {"field": "total_debt", "label": "Total Debt", "reason": "WACC calculation"},
>             {"field": "cash_and_equivalents", "label": "Cash", "reason": "Net debt derivation"},
>             {"field": "ebit", "label": "EBIT", "reason": "Operating margin projection"},
>             {"field": "gross_profit", "label": "Gross Profit", "reason": "Margin analysis"},
>             {"field": "stockholders_equity", "label": "Equity", "reason": "WACC via CAPM"},
>             {"field": "depreciation_amortization", "label": "D&A", "reason": "EBITDA and non-cash add-back"},
>             {"field": "tax_provision", "label": "Tax Provision", "reason": "Effective tax rate"},
>         ],
>         "helpful": [
>             {"field": "ebitda", "label": "EBITDA", "reason": "Terminal value exit multiple"},
>             {"field": "free_cash_flow", "label": "Free Cash Flow", "reason": "Cross-check vs derived FCF"},
>             {"field": "net_income", "label": "Net Income", "reason": "Profitability validation"},
>         ],
>     },
>     "ddm": {
>         "critical": [
>             {"field": "dividends_paid", "label": "Dividends Paid", "reason": "Core DDM input — model impossible without dividend history"},
>             {"field": "shares_outstanding", "label": "Shares Outstanding", "reason": "Dividend per share calculation"},
>         ],
>         "important": [
>             {"field": "net_income", "label": "Net Income", "reason": "Payout ratio and sustainability"},
>             {"field": "free_cash_flow", "label": "Free Cash Flow", "reason": "Dividend coverage ratio"},
>             {"field": "stockholders_equity", "label": "Equity", "reason": "ROE for sustainable growth"},
>         ],
>         "helpful": [
>             {"field": "revenue", "label": "Revenue", "reason": "Growth context"},
>             {"field": "operating_cash_flow", "label": "Operating Cash Flow", "reason": "Cash coverage validation"},
>         ],
>     },
>     "comps": {
>         "critical": [
>             {"field": "revenue", "label": "Revenue", "reason": "EV/Revenue multiple"},
>             {"field": "ebitda", "label": "EBITDA", "reason": "EV/EBITDA multiple"},
>             {"field": "net_income", "label": "Net Income", "reason": "P/E multiple"},
>             {"field": "shares_outstanding", "label": "Shares Outstanding", "reason": "Per-share metrics"},
>         ],
>         "important": [
>             {"field": "total_debt", "label": "Total Debt", "reason": "Enterprise value calculation"},
>             {"field": "cash_and_equivalents", "label": "Cash", "reason": "Enterprise value calculation"},
>             {"field": "free_cash_flow", "label": "Free Cash Flow", "reason": "P/FCF multiple"},
>             {"field": "stockholders_equity", "label": "Equity", "reason": "P/B multiple"},
>         ],
>         "helpful": [
>             {"field": "gross_profit", "label": "Gross Profit", "reason": "Quality assessment"},
>             {"field": "operating_margin", "label": "Operating Margin", "reason": "Quality premium/discount"},
>         ],
>     },
>     "revenue_based": {
>         "critical": [
>             {"field": "revenue", "label": "Revenue", "reason": "Core input — model is entirely revenue-driven"},
>             {"field": "shares_outstanding", "label": "Shares Outstanding", "reason": "Per-share price calculation"},
>         ],
>         "important": [
>             {"field": "operating_margin", "label": "Operating Margin", "reason": "Rule of 40 calculation"},
>             {"field": "gross_profit", "label": "Gross Profit", "reason": "Margin profile for multiple selection"},
>             {"field": "ebitda", "label": "EBITDA", "reason": "Margin component of Rule of 40"},
>         ],
>         "helpful": [
>             {"field": "free_cash_flow", "label": "Free Cash Flow", "reason": "FCF margin for growth-quality assessment"},
>             {"field": "net_income", "label": "Net Income", "reason": "Profitability cross-check"},
>         ],
>     },
> }
>
> # Known field derivations (computed from other fields)
> KNOWN_DERIVATIONS: dict[str, str] = {
>     "free_cash_flow": "operating_cash_flow + capital_expenditure",
>     "net_debt": "total_debt - cash_and_equivalents",
>     "working_capital": "current_assets - current_liabilities",
>     "gross_margin": "gross_profit / revenue",
>     "operating_margin": "ebit / revenue",
>     "net_margin": "net_income / revenue",
>     "fcf_margin": "free_cash_flow / revenue",
>     "ebitda_margin": "ebitda / revenue",
>     "roe": "net_income / stockholders_equity",
>     "debt_to_equity": "total_debt / stockholders_equity",
>     "payout_ratio": "dividends_paid / net_income",
>     "ebitda": "ebit + depreciation_amortization",
> }
>
> # Financial columns (excluding metadata columns)
> FINANCIAL_COLUMNS: list[str] = [
>     "revenue", "cost_of_revenue", "gross_profit", "operating_expense",
>     "rd_expense", "sga_expense", "ebit", "interest_expense", "tax_provision",
>     "net_income", "ebitda", "depreciation_amortization", "eps_basic", "eps_diluted",
>     "total_assets", "current_assets", "cash_and_equivalents", "total_liabilities",
>     "current_liabilities", "long_term_debt", "short_term_debt", "total_debt",
>     "stockholders_equity", "working_capital", "net_debt", "operating_cash_flow",
>     "capital_expenditure", "free_cash_flow", "dividends_paid",
>     "change_in_working_capital", "investing_cash_flow", "financing_cash_flow",
>     "shares_outstanding", "market_cap_at_period", "beta_at_period",
>     "dividend_per_share", "gross_margin", "operating_margin", "net_margin",
>     "fcf_margin", "revenue_growth", "ebitda_margin", "roe", "debt_to_equity",
>     "payout_ratio",
> ]
> ```
>
> **Task 2: Create Data Readiness Service**
>
> Create `backend/services/data_readiness_service.py`:
>
> The service should:
> 1. Accept a ticker, fetch financial data rows + market data
> 2. Compute coverage stats across all financial columns
> 3. For each engine, walk the dependency map, classify each field, determine verdict
> 4. Call `model_detection_svc.detect(ticker)` to get detection scores (wrap in try/except)
> 5. Build the `field_metadata` flat map for overlay support
> 6. Return the full response dict
>
> Key methods:
> - `get_readiness(ticker: str) -> dict` — main entry point
> - `_classify_field(field_name: str, rows: list[dict]) -> tuple[str, int, str | None]` — returns (status, years_available, source_description)
> - `_determine_verdict(critical_statuses, important_statuses) -> tuple[str, str, str | None]` — returns (verdict, verdict_label, missing_impact)
> - `_build_field_metadata(rows: list[dict]) -> dict` — flat map of all fields
>
> Use `MarketDataRepo(db)` for data access (it already has `get_financials(ticker)` and `get_market_data(ticker)`).
>
> **Task 3: Add Endpoint**
>
> In `backend/routers/models_router.py`, add `GET /{ticker}/data-readiness` endpoint:
> ```python
> @router.get("/{ticker}/data-readiness")
> async def get_data_readiness(ticker: str, request: Request):
>     try:
>         svc = request.app.state.data_readiness_service
>         result = await svc.get_readiness(ticker.upper())
>         return success_response(data=result)
>     except Exception as exc:
>         logger.exception("Data readiness failed for %s", ticker)
>         return error_response("DATA_READINESS_ERROR", str(exc))
> ```
>
> **Task 4: Wire Up in main.py**
>
> After `model_detection_svc` initialization:
> ```python
> from services.data_readiness_service import DataReadinessService
> data_readiness_svc = DataReadinessService(db=db, model_detection_svc=model_detection_svc)
> app.state.data_readiness_service = data_readiness_svc
> logger.info("Data readiness service initialized.")
> ```
>
> **Acceptance criteria:**
> 1. `engine_dependency_map.py` exists with ENGINE_DEPENDENCIES for 4 engines, 3 tiers each
> 2. KNOWN_DERIVATIONS maps computed fields to formulas
> 3. Field names match cache.financial_data columns exactly
> 4. `data_readiness_service.py` exists with DataReadinessService class
> 5. `GET /model-builder/{ticker}/data-readiness` returns structured response
> 6. Response has coverage stats: ticker, data_years_available, total_fields, populated_fields, coverage_pct
> 7. Response has engines dict with verdict (ready/partial/not_possible), verdict_label, detection_score per engine
> 8. Each engine has critical/important/helpful field arrays with status/years_available/source
> 9. Verdict: missing critical → not_possible, missing important → partial, all present → ready
> 10. missing_impact text populated for non-ready verdicts
> 11. field_metadata flat map with every financial field → status, source, engines[]
> 12. detection_result included from model detection service
> 13. Derived fields classified correctly (e.g. free_cash_flow as "computed from...")
> 14. Error handling: graceful failure with error response
>
> **Files to create:**
> - `backend/services/engine_dependency_map.py`
> - `backend/services/data_readiness_service.py`
>
> **Files to modify:**
> - `backend/routers/models_router.py`
> - `backend/main.py`
>
> **Technical constraints:**
> - Python 3.12, FastAPI, asyncio
> - SQLite via DatabaseConnection async wrapper
> - All queries use parameterized `?` placeholders
> - MarketDataRepo for data access
> - Detection service may fail for tickers with no data — wrap in try/except, use nulls
> - Response is a plain dict (no Pydantic model needed for this endpoint, but use if preferred)
> - Keep the dependency map easy to maintain — single file, clear structure
