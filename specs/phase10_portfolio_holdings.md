# Finance App — Portfolio: Holdings Sub-Tab Update Plan
## Phase 10: Portfolio — Holdings

**Prepared by:** Planner (March 5, 2026)
**Recipient:** PM Agent
**Scope:** Portfolio → Holdings sub-tab (CSV import fix, context menu fix, company info card)

---

## PLAN SUMMARY

Four workstreams:

1. **CSV Import Fix + Transaction Import** — Fix header parsing for real broker exports (Fidelity, Schwab, IBKR), add transaction import mode so daily trades can be pasted in without rebuilding the entire portfolio
2. **Context Menu Overflow Fix** — Detect when right-click menu would clip below the viewport and flip it upward
3. **Company Info Hover Card** — Quick-glance company info card on hover or right-click for each position in the holdings table
4. **Edit Position** — Inline editing of existing positions (shares, cost basis, account) without needing to delete and re-add

---

## AREA 1: CSV IMPORT FIX + TRANSACTION IMPORT

### Current Problems
- The import modal has Fidelity/Schwab/Generic broker options but the backend parser likely can't handle actual broker CSV column headers (e.g., Fidelity exports with headers like "Account Name/Number", "Symbol", "Description", "Quantity", "Last Price", "Current Value")
- Import only supports positions (current snapshot) — no way to import a batch of transactions (BUY/SELL records for a day)
- If headers don't match the expected format, the parse fails silently or with an unhelpful error

### Changes

#### 1A. Backend — Broker-Specific CSV Parsers
**Goal:** Handle the actual CSV formats that Fidelity, Schwab, and Interactive Brokers export.

**Approach:** Create a parser per broker that maps their specific column headers to the internal format. Each parser:
1. Detects/validates the expected headers
2. Maps columns to internal fields (ticker, shares, cost basis, date, account)
3. Handles broker-specific quirks (Fidelity includes a summary row at the bottom, Schwab uses different date formats, IBKR has multi-section CSVs)
4. Returns clear error messages when headers don't match: "Expected Fidelity format but found columns: X, Y, Z. Try selecting 'Generic CSV' or check your export settings."

**Add IBKR** as a 4th broker option (Interactive Brokers is common for active traders).

**Generic CSV parser** should be more flexible:
- Auto-detect common column name variants: "Symbol"/"Ticker"/"Stock Symbol", "Qty"/"Quantity"/"Shares", "Cost Basis"/"Avg Cost"/"Price Paid", etc.
- If auto-detection fails, show a column mapping UI in the preview step where the user can manually assign which CSV column maps to which field

**Files touched:**
- `backend/services/portfolio/csv_import.py` — new or refactored file with per-broker parsers
- `backend/routers/portfolio_router.py` — update import preview/execute endpoints with better error handling

#### 1B. Transaction Import Mode
**Goal:** In addition to importing a position snapshot, allow importing a batch of transactions (BUY/SELL/DIVIDEND records).

**UI change in ImportModal:**
- Step 1 becomes: Select broker + Select import type
  - Import type: "Current Positions" (existing) or "Transactions" (new)
- When "Transactions" is selected:
  - Expected CSV format includes: Date, Type (BUY/SELL), Ticker, Shares, Price, Fees
  - Preview step shows parsed transactions instead of positions
  - Execute step creates transaction records and auto-updates positions/lots accordingly

**Backend:**
- New endpoint: `POST /api/v1/portfolio/import/transactions/preview` — parses transaction CSV
- New endpoint: `POST /api/v1/portfolio/import/transactions/execute` — creates transactions and updates positions
- Transaction import uses the existing lot engine (FIFO/LIFO) to process sells correctly

**Files touched:**
- `frontend/src/pages/Portfolio/Holdings/ImportModal.tsx` — add import type selector, transaction preview table, transaction-specific flow
- `frontend/src/pages/Portfolio/Holdings/ImportModal.module.css` — minor additions for type selector
- `backend/services/portfolio/csv_import.py` — add transaction parsing
- `backend/routers/portfolio_router.py` — add transaction import endpoints
- `backend/services/portfolio/portfolio_service.py` — process imported transactions through lot engine

#### 1C. Column Mapping Fallback UI
**Goal:** When the generic parser can't auto-detect columns, show a mapping interface in the preview step.

**UI:**
```
We couldn't auto-detect your CSV format. Please map the columns:

CSV Column          →  Maps To
─────────────────────────────────
"Stock Symbol"      →  [Ticker        ▾]
"Qty"               →  [Shares        ▾]
"Avg Cost"          →  [Cost Basis    ▾]
"Purchase Date"     →  [Date Acquired ▾]
"Acct"              →  [Account       ▾]

                        [Preview with this mapping]
```

This is only shown when auto-detection fails. Most Fidelity/Schwab/IBKR exports will be handled by the specific parsers.

**Files touched:**
- `frontend/src/pages/Portfolio/Holdings/ImportModal.tsx` — add column mapping step
- `frontend/src/pages/Portfolio/Holdings/ImportModal.module.css` — mapping UI styles

---

## AREA 2: CONTEXT MENU OVERFLOW FIX

### Current Problem
`ContextMenu.tsx` renders at `style={{ left: x, top: y }}` where x,y are the mouse click coordinates. When right-clicking a position near the bottom of the table, the menu extends below the viewport edge and gets cut off. The user can't see or click the bottom menu items.

### Fix
Before rendering, calculate whether the menu would overflow the viewport bottom (or right edge). If so, flip it:

```typescript
// In ContextMenu.tsx
const menuHeight = 160; // approximate height of 4 menu items + separator
const menuWidth = 200;

const adjustedY = (y + menuHeight > window.innerHeight)
  ? y - menuHeight  // flip upward
  : y;

const adjustedX = (x + menuWidth > window.innerWidth)
  ? x - menuWidth   // flip leftward
  : x;
```

Better approach: use a `ref` on the menu div, measure its actual rendered height after mount, then reposition if needed. This handles variable menu heights (e.g., when WatchlistPicker sub-menu is open).

**Files touched:**
- `frontend/src/pages/Portfolio/Holdings/HoldingsTable.tsx` — pass adjusted coordinates (or let ContextMenu self-adjust)
- `frontend/src/pages/Scanner/ResultsTable/ContextMenu.tsx` — same fix applied to Scanner's context menu (shared pattern)
- Both ContextMenu components: add viewport boundary detection and flip logic

**Note:** The Scanner's ContextMenu has the same bug. Fix both at once.

---

## AREA 3: COMPANY INFO HOVER CARD

### Goal
A quick-glance company info card for each position in the holdings table, showing key company data without navigating away from the portfolio.

### Trigger
- **Hover:** When the user hovers over a ticker cell in the holdings table for ~500ms, a small info card appears adjacent to the cell
- **Right-click option:** Add "Company Info" to the existing context menu — on click, shows the same card as a pinned popover that stays until dismissed
- **Left-click ticker:** Still navigates to Research tab (existing behavior, unchanged)

### Info Card Content
```
┌────────────────────────────────────┐
│ AAPL — Apple Inc.                  │
│ Technology · Consumer Electronics  │
│────────────────────────────────────│
│ Market Cap      $3.21T             │
│ P/E (Trailing)  32.5x              │
│ EV/EBITDA       24.8x              │
│ Revenue Growth  +8.2%              │
│ Operating Margin 30.1%             │
│ Dividend Yield  0.51%              │
│ Beta            1.24               │
│ 52W Range       $164 – $237       │
│────────────────────────────────────│
│ [Open in Research →]               │
└────────────────────────────────────┘
```

### Data Source
The data comes from `cache.market_data` (already fetched for each position since we need current price). Most of these fields are already in the market data cache (pe_trailing, ev_to_ebitda, dividend_yield, beta, fifty_two_week_high/low). The company profile (sector, industry) comes from the `companies` table.

**New endpoint:** `GET /api/v1/companies/{ticker}/quick-info` — returns a compact company card object with the fields above. Alternatively, combine existing quote + company profile endpoints on the frontend (but a single endpoint is cleaner).

### Implementation
- New component: `CompanyInfoCard.tsx` — renders the floating card
- Hover trigger: wrap each ticker cell in the HoldingsTable with a hover handler that shows the card after a delay
- Position: card appears to the right of the ticker cell (or left if near the right edge — same boundary detection as the context menu fix)
- Dismiss: on mouse leave, after a short delay (200ms grace period so you can move into the card)
- The card itself is hoverable — if you move your mouse into it, it stays open

**Files touched:**
- `frontend/src/pages/Portfolio/Holdings/CompanyInfoCard.tsx` — new file
- `frontend/src/pages/Portfolio/Holdings/CompanyInfoCard.module.css` — new file
- `frontend/src/pages/Portfolio/Holdings/HoldingsTable.tsx` — add hover handler on ticker cells, render CompanyInfoCard
- `frontend/src/pages/Portfolio/Holdings/HoldingsTable.module.css` — hover trigger styles
- `backend/routers/companies_router.py` — add quick-info endpoint (optional, can reuse existing)
- Context menu: add "Company Info" option that pins the card

---

## AREA 4: EDIT POSITION

### Current Problem
To change a position's shares or cost basis, the user has to delete the position and re-add it with the correct values. There's no way to edit an existing position in place.

### Changes

#### 4A. Edit Position Modal
A modal similar to AddPositionModal but pre-populated with the current position's data. Accessible via:
- A new "Edit" button in the PositionDetail expanded row (next to "Record Transaction")
- A new "Edit Position" option in the right-click context menu

**Editable fields:**
- Shares held (total, or per-lot if expanding individual lots)
- Cost basis per share
- Account assignment
- Date acquired
- Notes

**Behavior:**
- On save: PUTs to `/api/v1/portfolio/positions/{id}` with updated fields
- Only changed fields are sent (partial update)
- Lot-level editing: if the position has multiple lots, the modal shows each lot as an editable row so you can adjust individual lots without affecting others
- Refreshes the holdings table after successful save

#### 4B. Backend — Position Update Endpoint
**Endpoint:** `PUT /api/v1/portfolio/positions/{position_id}`

**Accepts:** Partial update body with any combination of: `shares`, `cost_basis_per_share`, `account`, `date_acquired`, `notes`

**Lot-level:** `PUT /api/v1/portfolio/lots/{lot_id}` for individual lot edits

**Validation:**
- Shares must be > 0
- Cost basis must be > 0
- If shares change, recalculate market_value, gain/loss, weight

**Files touched:**
- `frontend/src/pages/Portfolio/Holdings/EditPositionModal.tsx` — new file
- `frontend/src/pages/Portfolio/Holdings/EditPositionModal.module.css` — new file
- `frontend/src/pages/Portfolio/Holdings/PositionDetail.tsx` — add Edit button
- `frontend/src/pages/Portfolio/Holdings/HoldingsTable.tsx` — wire up edit modal, add to context menu
- `backend/routers/portfolio_router.py` — add PUT position and PUT lot endpoints
- `backend/services/portfolio/portfolio_service.py` — add update_position and update_lot methods
- `backend/repositories/portfolio_repo.py` — add update methods

---

## SESSION ORGANIZATION (Recommended for PM)

### Session 10A — CSV Import + Edit Position Backend (Backend Only)
**Scope:** Areas 1A, 1B backend, 4B
**Files:**
- `backend/services/portfolio/csv_import.py` — broker-specific parsers, transaction parsing
- `backend/routers/portfolio_router.py` — transaction import endpoints, better error messages
- `backend/services/portfolio/portfolio_service.py` — transaction import through lot engine, update_position, update_lot
- `backend/repositories/portfolio_repo.py` — add update methods
**Complexity:** Medium-High (broker format research, multiple parsers, transaction processing)
**Estimated acceptance criteria:** 15–18

### Session 10B — Holdings Frontend (Frontend Only)
**Scope:** Areas 1B–1C frontend, 2, 3, 4A
**Files:**
- `ImportModal.tsx` — import type selector, transaction preview, column mapping fallback
- `ImportModal.module.css` — type selector, mapping UI styles
- `HoldingsTable.tsx` — hover handler for company info card
- `HoldingsTable.module.css` — hover styles
- `CompanyInfoCard.tsx` — new component
- `CompanyInfoCard.module.css` — new styles
- `ContextMenu.tsx` (Portfolio) — overflow fix, add Company Info option
- `ContextMenu.tsx` (Scanner) — same overflow fix
- `ContextMenu.module.css` (both) — flip positioning styles
- `EditPositionModal.tsx` — new component
- `EditPositionModal.module.css` — new styles
- `PositionDetail.tsx` — add Edit button
- `HoldingsTable.tsx` — wire edit modal, add Edit to context menu
**Complexity:** Medium-High (column mapping UI, hover card with positioning, context menu fixes across two modules)
**Estimated acceptance criteria:** 20–25
**Depends on:** Session 10A (transaction import endpoints)

---

## DEPENDENCIES & RISKS

| Risk | Mitigation |
|------|------------|
| Broker CSV formats change over time | Parsers use flexible header matching (case-insensitive, partial match); column mapping fallback as safety net |
| Transaction import creates duplicate entries | Check for existing transactions with same ticker + date + type + amount before inserting; show duplicates in preview |
| Hover card fires too aggressively while scrolling | 500ms delay before showing; immediate dismiss on scroll |
| Company info card data not cached for all positions | Market data is already cached from the holdings table fetch; company profile may need a lightweight batch fetch on holdings load |
| Context menu overflow fix doesn't account for menu height changing (e.g., watchlist sub-menu) | Use ref-based measurement after render, reposition dynamically |

---

## DECISIONS MADE

1. Four broker options: Generic, Fidelity, Schwab, Interactive Brokers
2. Generic parser auto-detects common column variants; falls back to manual column mapping UI
3. Two import modes: Current Positions (existing) and Transactions (new)
4. Transaction import processes through existing lot engine (FIFO/LIFO)
5. Context menu flips upward/leftward when it would overflow viewport — fix applied to both Portfolio and Scanner context menus
6. Edit Position modal accessible from PositionDetail expanded row and context menu
7. Position update is partial — only changed fields sent
8. Lot-level editing supported for multi-lot positions
9. Company info card triggered on 500ms hover over ticker cell
10. Card data comes from existing cached market data + company profile
11. "Company Info" added as right-click context menu option for pinned view
12. Left-click on ticker still navigates to Research (unchanged)

---

*End of Portfolio — Holdings Sub-Tab Update Plan*
*Phase 10A–10B · Prepared March 5, 2026*
