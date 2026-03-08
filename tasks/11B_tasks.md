# Session 11B — Profile + Filings + Frontend Accuracy Verification
## Phase 11: Research

**Priority:** High
**Type:** Mixed (Backend + Frontend)
**Depends On:** 11A (normalization must be done before frontend verification is meaningful)
**Spec Reference:** `specs/phase11_research.md` → Areas 1C–1D (frontend verification), 2 (profile), 3 (filings), 4 (peers)

---

## SCOPE SUMMARY

Verify frontend formatting after 11A's normalization fix — ensure `fmtPct` receives decimal ratios everywhere, add extreme value handling for ROE. Enhance the Research Profile tab with enterprise value and shares outstanding in key stats, plus a Business Overview card from 10-K filings. Add a "Fetch Filings" button to the Filings tab. Verify Peers tab accuracy.

---

## TASKS

### Task 1: Frontend Accuracy Verification
**Description:** After 11A normalizes all backend values, verify the frontend correctly displays them. Check all components that use `fmtPct` or display percentage values.

**Subtasks:**
- [ ] 1.1 — In `frontend/src/pages/Research/Profile/KeyStatsCard.tsx`, verify all percentage metrics use `fmtPct(value)` where value is a decimal ratio. Check: dividend yield, revenue growth, margins.
- [ ] 1.2 — In `frontend/src/pages/Research/Ratios/RatioPanel.tsx`, add extreme value handling for ROE:
  ```tsx
  {metric.key === 'roe' && value != null && Math.abs(value) > 1.0 && (
    <span className={styles.extremeNote}>
      Elevated due to {value > 0 ? 'low' : 'negative'} equity (buybacks)
    </span>
  )}
  ```
- [ ] 1.3 — In `frontend/src/pages/Research/Peers/PeerTable.tsx`, verify metric formatting. After normalization, `day_change_pct` and other fields should display correctly. Audit each column's formatter.
- [ ] 1.4 — In `frontend/src/pages/Dashboard/MarketOverview/MarketOverviewWidget.tsx`, verify `day_change_pct` display uses `fmtPct` correctly (value is now a decimal ratio after 11A).
- [ ] 1.5 — Add CSS for `.extremeNote` in `RatioPanel.module.css`:
  ```css
  .extremeNote {
    font-size: 10px;
    color: var(--color-warning);
    display: block;
    margin-top: 2px;
  }
  ```

---

### Task 2: Profile — Add Enterprise Value and Shares Outstanding
**Description:** Ensure enterprise value and shares outstanding display in the key stats card. These values exist in cache but may not be surfaced in the metrics dict.

**Subtasks:**
- [ ] 2.1 — In `backend/services/company_service.py`, in the method that builds the metrics dict for the profile endpoint, ensure `enterprise_value` and `shares_outstanding` are included from `cache.market_data` and `cache.financial_data` respectively:
  ```python
  # In get_company_with_metrics or equivalent:
  market_data = await self.market_svc.market_repo.get_market_data(ticker)
  if market_data:
      metrics["enterprise_value"] = market_data.get("enterprise_value")
  
  financials = await self.market_svc.market_repo.get_financials(ticker)
  if financials:
      latest = financials[0]  # newest first
      metrics["shares_outstanding"] = latest.get("shares_outstanding")
  ```
- [ ] 2.2 — In `KeyStatsCard.tsx`, verify the template renders enterprise_value and shares_outstanding. They're likely already in the template but showing "--" because the data wasn't populated. After this fix, they should render.

---

### Task 3: Profile — Business Overview from 10-K
**Description:** Add a Business Overview card on the Profile tab showing text from the 10-K's Item 1 (Business Description) section.

**Subtasks:**
- [ ] 3.1 — Create `frontend/src/pages/Research/Profile/BusinessOverview.tsx`:
  ```tsx
  interface Props {
    ticker: string;
  }
  ```
  Fetches the most recent 10-K's Item 1 text from the filings cache. Uses `GET /api/v1/research/{ticker}/filings` filtered to `form_type=10-K`, then fetches the filing sections to find "Item 1" or "Business" section.

- [ ] 3.2 — Render a card with the first ~500 words of the business description, truncated with "Read full filing →" link to the Filings tab.

- [ ] 3.3 — If no 10-K filing cached: show "No 10-K filing available." with a "Fetch Latest →" button that triggers the filing fetch (Task 4).

- [ ] 3.4 — Create `BusinessOverview.module.css` — card styles matching the dark theme.

- [ ] 3.5 — In `frontend/src/pages/Research/Profile/ProfileTab.tsx`, add `<BusinessOverview ticker={ticker} />` below the existing company overview section.

---

### Task 4: Filings — Fetch Filings Button
**Description:** Add a "Fetch Filings" button on the Filings tab that triggers a fresh fetch from SEC EDGAR.

**Subtasks:**
- [ ] 4.1 — In `backend/routers/research_router.py`, add a filings fetch endpoint:
  ```python
  @router.post("/{ticker}/filings/fetch")
  async def fetch_filings(ticker: str, request: Request):
      """Trigger a fresh filing fetch from SEC EDGAR."""
      try:
          research_svc = request.app.state.research_service
          result = await research_svc.fetch_filings(ticker)
          return success_response(data=result)
      except Exception as exc:
          logger.exception("Filing fetch failed for %s", ticker)
          return error_response("FETCH_ERROR", str(exc))
  ```

- [ ] 4.2 — In `backend/services/research_service.py`, add `fetch_filings()` method:
  ```python
  async def fetch_filings(self, ticker: str) -> dict:
      """Fetch and cache filings from SEC EDGAR."""
      filings = await self.filing_repo.get_filings_for_ticker(ticker)
      if not filings:
          # Fetch from EDGAR
          sec_filings = await self.company_svc.sec.get_filings(ticker)
          # Process and cache...
      return {"ticker": ticker, "filings_count": len(filings)}
  ```
  Use existing `SECEdgarProvider` and `XBRLService` for fetching and parsing.

- [ ] 4.3 — In `frontend/src/pages/Research/Filings/FilingsTab.tsx`, add the fetch button:
  ```tsx
  const [fetching, setFetching] = useState(false);

  const handleFetch = async () => {
    setFetching(true);
    try {
      await api.post(`/api/v1/research/${ticker}/filings/fetch`, {});
      await loadFilings();  // Refresh the filing list
    } catch { /* ... */ }
    finally { setFetching(false); }
  };
  ```
  Show button when: no filings exist OR most recent filing is > 90 days old.
  ```tsx
  <button className={styles.fetchBtn} onClick={handleFetch} disabled={fetching}>
    {fetching ? '🔄 Fetching...' : '🔄 Fetch Latest Filings'}
  </button>
  ```

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: All frontend components using `fmtPct` verified to receive decimal ratios after 11A.
- [ ] AC-2: ROE values > 100% show contextual note: "Elevated due to low/negative equity (buybacks)".
- [ ] AC-3: Peers tab metrics display correctly after normalization.
- [ ] AC-4: Dashboard market overview `day_change_pct` displays correctly.
- [ ] AC-5: Enterprise Value shows in Profile key stats (not "--").
- [ ] AC-6: Shares Outstanding shows in Profile key stats (not "--").
- [ ] AC-7: Business Overview card on Profile tab shows 10-K Item 1 text (first ~500 words).
- [ ] AC-8: Business Overview shows "No 10-K available" with fetch button when no filing cached.
- [ ] AC-9: "Fetch Latest Filings" button on Filings tab triggers SEC EDGAR fetch.
- [ ] AC-10: Fetch button shows loading state while fetching.
- [ ] AC-11: Filing list refreshes after successful fetch.
- [ ] AC-12: Fetch button visible when no filings or filings are stale (>90 days).
- [ ] AC-13: No regressions on existing Research functionality.

---

## FILES TOUCHED

**New files:**
- `frontend/src/pages/Research/Profile/BusinessOverview.tsx` — 10-K business description card
- `frontend/src/pages/Research/Profile/BusinessOverview.module.css` — card styles

**Modified files:**
- `frontend/src/pages/Research/Profile/KeyStatsCard.tsx` — formatting verification
- `frontend/src/pages/Research/Ratios/RatioPanel.tsx` — extreme ROE handling
- `frontend/src/pages/Research/Ratios/RatioPanel.module.css` — extreme note styles
- `frontend/src/pages/Research/Peers/PeerTable.tsx` — formatting verification
- `frontend/src/pages/Research/Profile/ProfileTab.tsx` — add BusinessOverview component
- `frontend/src/pages/Research/Filings/FilingsTab.tsx` — fetch filings button
- `frontend/src/pages/Research/Filings/FilingsTab.module.css` — button styles
- `frontend/src/pages/Dashboard/MarketOverview/MarketOverviewWidget.tsx` — verify day_change_pct
- `backend/services/company_service.py` — ensure EV + shares in metrics
- `backend/routers/research_router.py` — filings fetch endpoint
- `backend/services/research_service.py` — fetch_filings method

---

## BUILDER PROMPT

> **Session 11B — Profile + Filings + Frontend Accuracy Verification**
>
> You are building session 11B of the Finance App v2.0 update.
>
> **What you're doing:** Four areas: (1) Verify frontend formatting after 11A normalization, add ROE extreme value handling, (2) Add EV + shares to Profile key stats, (3) Add Business Overview card from 10-K filings, (4) Add Fetch Filings button.
>
> **Context:** Session 11A normalized all backend values to decimal ratios. The frontend should now display correctly, but needs verification. The Profile tab is missing enterprise value and shares outstanding. The Filings tab has no way to trigger a fetch from SEC EDGAR.
>
> **Existing code:**
>
> `KeyStatsCard.tsx` — renders key stats grid. Has template slots for enterprise_value and shares_outstanding but shows "--" when data missing.
>
> `RatioPanel.tsx` — renders ratio categories with values. Uses `fmtPct` for percentage metrics. No extreme value handling.
>
> `PeerTable.tsx` — renders peer comparison table with metrics. Uses formatting from types.
>
> `ProfileTab.tsx` — renders company overview + key stats. No Business Overview section.
>
> `FilingsTab.tsx` — renders filing list with type filters. No fetch button. Shows "No filings" when empty.
>
> `company_service.py` `get_company_with_metrics()` — builds metrics dict. May not include enterprise_value or shares_outstanding from cache.
>
> `research_router.py` — has `GET /{ticker}/filings`, `GET /{ticker}/financials`, etc. No POST for fetching filings.
>
> **Cross-cutting rules:**
> - Display Name Rule: Use `displayNames.ts`.
> - Data Format: Decimal ratios after 11A. `fmtPct` multiplies by 100.
>
> **Files to create:** `BusinessOverview.tsx/css`
> **Files to modify:** `KeyStatsCard.tsx`, `RatioPanel.tsx/css`, `PeerTable.tsx`, `ProfileTab.tsx`, `FilingsTab.tsx/css`, `MarketOverviewWidget.tsx`, `company_service.py`, `research_router.py`, `research_service.py`
>
> **Technical constraints:**
> - `fmtPct(value)` expects decimal ratio, multiplies by 100
> - ROE > 1.0 is legitimate for negative-equity companies — show note, don't cap
> - 10-K text from `filing_sections` table, section_title matching "Item 1" or "Business"
> - SEC EDGAR fetch uses existing `SECEdgarProvider` and `XBRLService`
> - Business overview truncated at ~500 words with "Read full filing →" link
