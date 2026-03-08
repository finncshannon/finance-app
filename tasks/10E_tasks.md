# Session 10E — Income Backend + Allocation ETF Fix
## Phase 10: Portfolio

**Priority:** Normal
**Type:** Backend Only
**Depends On:** None
**Spec Reference:** `specs/phase10_portfolio_remaining.md` → Areas 1 backend, 2 backend (2A, 2C, 2D backend)

---

## SCOPE SUMMARY

Fix ETF sector classification in the company service (detect ETF quoteType, set sector to "ETF"). Enhance the income backend with yield-on-cost calculations, projected annual income, dividend growth (5Y CAGR) per position, and an endpoint to fetch upcoming dividend events for portfolio tickers.

---

## TASKS

### Task 1: ETF Sector Classification
**Description:** When fetching company profiles for ETF tickers (SPY, QQQ, VTI), Yahoo returns sector as empty or "Financial Services". Detect ETFs via `quoteType` and classify them properly.

**Subtasks:**
- [ ] 1.1 — In `backend/providers/yahoo_finance.py`, update `get_company_info()` to include `quoteType` in the returned data:
  ```python
  quote_type = _safe(info, "quoteType", "EQUITY")
  
  return CompanyInfo(
      ticker=ticker.upper(),
      company_name=name,
      sector="ETF" if quote_type == "ETF" else _safe(info, "sector", "Unknown"),
      industry=_safe(info, "category", _safe(info, "industry", "Unknown")) if quote_type == "ETF" else _safe(info, "industry", "Unknown"),
      # ... rest unchanged
  )
  ```
  For ETFs, Yahoo's `category` field contains the fund category (e.g., "Large Blend", "Technology") — use that as industry.

- [ ] 1.2 — In `backend/services/company_service.py`, in `get_or_create_company()`, verify the ETF classification flows through correctly. The `CompanyInfo` model is passed to `company_repo.upsert()` which writes sector/industry to the DB. No additional changes needed if the provider returns the correct values.

- [ ] 1.3 — Add a `quote_type` field to the `CompanyInfo` dataclass in `backend/providers/base.py` (if not already present) so downstream consumers can check if a ticker is an ETF:
  ```python
  @dataclass
  class CompanyInfo:
      # ... existing fields
      quote_type: str = "EQUITY"  # EQUITY, ETF, MUTUALFUND, etc.
  ```
  Update the Yahoo provider to set this field.

---

### Task 2: Income Endpoint Enhancements
**Description:** Update the portfolio income endpoint to include yield-on-cost per position, projected annual income, and income growth YoY.

**Subtasks:**
- [ ] 2.1 — Create or extend `backend/services/portfolio/income_service.py` with enhanced income calculations:
  ```python
  class IncomeService:
      def __init__(self, db, market_data_svc, portfolio_repo):
          self.db = db
          self.mds = market_data_svc
          self.repo = portfolio_repo

      async def get_enhanced_income(self, account: str | None = None) -> dict:
          """Enhanced income with yield-on-cost, projections, and growth."""
          positions = await self.repo.get_all_positions(account)
          
          income_positions = []
          total_annual_income = 0.0
          total_cost_basis = 0.0
          total_market_value = 0.0

          for pos in positions:
              ticker = pos["ticker"]
              shares = pos.get("shares_held", 0)
              cost_per_share = pos.get("cost_basis_per_share", 0)
              
              # Get dividend data from market_data cache
              md = await self.db.fetchone(
                  "SELECT dividend_rate, dividend_yield, current_price FROM cache.market_data WHERE ticker = ?",
                  (ticker,),
              )
              if not md or not md.get("dividend_rate"):
                  continue  # Non-dividend position
              
              div_rate = md["dividend_rate"]  # Annual dividend per share
              current_price = md.get("current_price", 0)
              annual_income = div_rate * shares
              
              # Yield on cost
              yoc = div_rate / cost_per_share if cost_per_share > 0 else None
              
              # Market yield (for reference)
              market_yield = md.get("dividend_yield")  # Already decimal from Yahoo
              
              income_positions.append({
                  "ticker": ticker,
                  "shares": shares,
                  "dividend_rate": div_rate,
                  "annual_income": annual_income,
                  "monthly_income": annual_income / 12,
                  "cost_basis_per_share": cost_per_share,
                  "yield_on_cost": yoc,
                  "market_yield": market_yield,
                  "current_price": current_price,
              })
              
              total_annual_income += annual_income
              total_cost_basis += cost_per_share * shares
              total_market_value += current_price * shares

          # Portfolio-level metrics
          portfolio_yoc = total_annual_income / total_cost_basis if total_cost_basis > 0 else None
          portfolio_yield = total_annual_income / total_market_value if total_market_value > 0 else None

          return {
              "positions": income_positions,
              "summary": {
                  "total_annual_income": total_annual_income,
                  "total_monthly_income": total_annual_income / 12,
                  "projected_annual_income": total_annual_income,  # Same for now, could factor in growth
                  "yield_on_cost": portfolio_yoc,
                  "yield_on_market": portfolio_yield,
                  "dividend_position_count": len(income_positions),
                  "total_position_count": len(positions),
              },
          }
  ```

- [ ] 2.2 — Add a dividend growth calculation method:
  ```python
  async def get_dividend_growth(self, ticker: str) -> float | None:
      """Calculate 5-year dividend CAGR for a ticker using historical dividend data."""
      try:
          # yfinance Ticker.dividends returns a pandas Series of historical dividends
          import yfinance as yf
          import asyncio
          
          def _fetch():
              t = yf.Ticker(ticker)
              divs = t.dividends
              if divs is None or len(divs) < 2:
                  return None
              # Get annual totals for last 5 years
              annual = divs.resample('Y').sum()
              if len(annual) < 2:
                  return None
              recent = annual.iloc[-1]
              oldest = annual.iloc[-min(5, len(annual))]
              years = min(5, len(annual) - 1)
              if oldest <= 0 or years <= 0:
                  return None
              cagr = (recent / oldest) ** (1 / years) - 1
              return float(cagr)
          
          return await asyncio.to_thread(_fetch)
      except Exception:
          return None
  ```

- [ ] 2.3 — In `backend/routers/portfolio_router.py`, update the income endpoint to use the enhanced service:
  ```python
  @router.get("/income")
  async def get_income(request: Request, account: str | None = None):
      income_svc = request.app.state.income_service
      result = await income_svc.get_enhanced_income(account)
      return success_response(data=result)
  ```

- [ ] 2.4 — Initialize `IncomeService` in `main.py`:
  ```python
  from services.portfolio.income_service import IncomeService
  income_svc = IncomeService(db, market_data_svc, portfolio_repo)
  app.state.income_service = income_svc
  ```

---

### Task 3: Upcoming Dividends Endpoint
**Description:** Add an endpoint to fetch upcoming ex-dividend events for portfolio tickers. This pulls from the events cache built in Phase 7.

**Subtasks:**
- [ ] 3.1 — In `backend/routers/portfolio_router.py`, add an upcoming dividends endpoint:
  ```python
  @router.get("/income/upcoming-dividends")
  async def get_upcoming_dividends(request: Request, account: str | None = None):
      """Get upcoming ex-dividend dates for portfolio positions."""
      portfolio_svc: PortfolioService = request.app.state.portfolio_service
      positions = await portfolio_svc.repo.get_all_positions(account)
      tickers = list({p["ticker"] for p in positions})
      
      # Try to get events from the events service (Phase 7)
      events_svc = getattr(request.app.state, 'events_service', None)
      if not events_svc:
          return success_response(data={"upcoming": [], "message": "Events system not available"})
      
      try:
          upcoming = await events_svc.get_upcoming_events(
              tickers=tickers,
              event_types=["ex_dividend"],
              days_ahead=60,
          )
          # Enrich with shares held
          ticker_shares = {p["ticker"]: p.get("shares_held", 0) for p in positions}
          enriched = []
          for event in upcoming:
              shares = ticker_shares.get(event.get("ticker"), 0)
              amount = event.get("amount_per_share", 0)
              enriched.append({
                  **event,
                  "shares_held": shares,
                  "expected_income": amount * shares if amount else None,
              })
          return success_response(data={"upcoming": enriched})
      except Exception as exc:
          logger.warning("Failed to fetch upcoming dividends: %s", exc)
          return success_response(data={"upcoming": [], "message": "Could not fetch events"})
  ```

- [ ] 3.2 — The endpoint gracefully handles the case where Phase 7 events system hasn't been built yet — returns empty list with a message. This follows the Planner's directive: "If Phase 7 hasn't been built, show a placeholder."

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: ETF tickers (SPY, QQQ, VTI) get sector="ETF" when company profile is fetched.
- [ ] AC-2: ETF industry set to Yahoo's `category` field (e.g., "Large Blend").
- [ ] AC-3: Non-ETF tickers unaffected by the ETF classification logic.
- [ ] AC-4: `CompanyInfo` dataclass has `quote_type` field.
- [ ] AC-5: Income endpoint returns yield-on-cost per position (`annual_dividend / cost_basis_per_share`).
- [ ] AC-6: Income endpoint returns portfolio-level yield-on-cost and yield-on-market.
- [ ] AC-7: Income endpoint returns projected annual income.
- [ ] AC-8: Dividend growth (5Y CAGR) calculable for positions with sufficient history.
- [ ] AC-9: Upcoming dividends endpoint returns ex-dividend events for portfolio tickers.
- [ ] AC-10: Upcoming dividends enriched with shares_held and expected_income.
- [ ] AC-11: Upcoming dividends gracefully handles missing events system (returns empty + message).
- [ ] AC-12: `IncomeService` initialized in `main.py`.
- [ ] AC-13: No regressions on existing portfolio or income functionality.

---

## FILES TOUCHED

**New files:**
- `backend/services/portfolio/income_service.py` — IncomeService with yield-on-cost, projections, dividend growth

**Modified files:**
- `backend/providers/yahoo_finance.py` — ETF detection via `quoteType`, set sector/industry accordingly
- `backend/providers/base.py` — add `quote_type` to `CompanyInfo` dataclass
- `backend/services/company_service.py` — verify ETF classification flows through (minimal change)
- `backend/routers/portfolio_router.py` — update income endpoint, add upcoming-dividends endpoint
- `backend/main.py` — initialize `IncomeService`

---

## BUILDER PROMPT

> **Session 10E — Income Backend + Allocation ETF Fix**
>
> You are building session 10E of the Finance App v2.0 update.
>
> **What you're doing:** Two backend features: (1) Fix ETF sector classification so ETFs show as "ETF" instead of "Financial Services" in allocation views, (2) Enhance the income backend with yield-on-cost, projected income, dividend growth, and upcoming dividends endpoint.
>
> **Context:** The allocation donut/treemap show ~70% "Unknown" sector because company profiles aren't fetched (being fixed in 10C). But even when profiles ARE fetched, ETFs get wrong sectors. The income tab is basic — just a dividend history. Needs yield-on-cost, projections, and upcoming dividend events integration.
>
> **Existing code:**
>
> `yahoo_finance.py` `get_company_info()`:
> - Returns `CompanyInfo(sector=_safe(info, "sector", "Unknown"), industry=_safe(info, "industry", "Unknown"), ...)`
> - Yahoo's `info` dict has `quoteType` field: "EQUITY", "ETF", "MUTUALFUND"
> - For ETFs, `sector` is often empty or "Financial Services". `category` has the fund type (e.g., "Large Blend").
>
> `CompanyInfo` dataclass (at `backend/providers/base.py`):
> - Fields: ticker, company_name, sector, industry, cik, exchange, currency, description, employees, country, website, fiscal_year_end
> - Does NOT have `quote_type` — add it
>
> `company_service.py` `get_or_create_company()`:
> - Calls `market_svc.get_company(ticker)` which calls `provider.get_company_info(ticker)` then `company_repo.upsert(data)`
> - Sector/industry flow through from provider → repo → DB
>
> `portfolio_router.py`:
> - Has existing `GET /income` endpoint returning basic income data
> - Has `PortfolioService` via `request.app.state.portfolio_service`
> - Events service: `request.app.state.events_service` (from Phase 7 — may or may not exist at build time)
>
> `main.py`:
> - Services initialized with `app.state.xxx = xxx` pattern
> - `events_svc` registered as `app.state.events_service`
>
> **Cross-cutting rules:**
> - Data Format: All ratios as decimal ratios. `dividend_yield` from Yahoo is already decimal (0.005 = 0.5%).
>
> **Task 1: ETF Classification**
> - In `get_company_info()`: check `quoteType == "ETF"`, set sector to "ETF", industry to `info["category"]`
> - Add `quote_type: str = "EQUITY"` to `CompanyInfo` dataclass
>
> **Task 2: Income Service**
> - New `IncomeService` with `get_enhanced_income(account)`:
>   - Per position: dividend_rate, annual_income, monthly_income, yield_on_cost, market_yield
>   - Portfolio: total_annual, projected, portfolio yield-on-cost, portfolio yield-on-market
> - Dividend growth: 5Y CAGR from yfinance `.dividends` historical data
> - Initialize in main.py
>
> **Task 3: Upcoming Dividends**
> - `GET /income/upcoming-dividends` — fetches ex_dividend events for portfolio tickers from events service
> - Enriches with shares_held and expected_income
> - Gracefully handles missing events system (returns empty + message)
>
> **Acceptance criteria:**
> 1. ETFs get sector="ETF", industry=category
> 2. Income includes yield-on-cost per position and portfolio-level
> 3. Dividend growth (5Y CAGR) calculable
> 4. Upcoming dividends returns enriched events
> 5. Missing events system handled gracefully
> 6. No regressions
>
> **Files to create:** `backend/services/portfolio/income_service.py`
> **Files to modify:** `yahoo_finance.py`, `base.py`, `company_service.py`, `portfolio_router.py`, `main.py`
>
> **Technical constraints:**
> - `yfinance.Ticker.dividends` returns a pandas Series of historical dividends
> - Use `asyncio.to_thread()` for synchronous yfinance calls
> - `getattr(request.app.state, 'events_service', None)` for safe access to optional service
> - Yield-on-cost = annual_dividend_per_share / cost_basis_per_share (decimal ratio)
> - Market yield = Yahoo's `dividendYield` (already decimal)
