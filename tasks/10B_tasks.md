# Session 10B — Holdings Frontend (Import UX, Context Menu, Hover Card, Edit Position)
## Phase 10: Portfolio

**Priority:** Normal
**Type:** Frontend Only
**Depends On:** 10A (transaction import endpoints, position/lot PUT endpoints)
**Spec Reference:** `specs/phase10_portfolio_holdings.md` → Areas 1B–1C frontend, 2, 3, 4A

---

## SCOPE SUMMARY

Upgrade the ImportModal with import type selector (Positions vs Transactions), transaction preview table, and column mapping fallback UI for generic CSV. Fix context menu viewport overflow in both Portfolio and Scanner modules. Add a company info hover card on ticker cells in the holdings table. Add an EditPositionModal accessible from the PositionDetail expanded row and context menu.

---

## TASKS

### Task 1: ImportModal — Import Type Selector + Transaction Flow
**Description:** Add a "Positions" / "Transactions" toggle in step 1 of the ImportModal. When "Transactions" is selected, the preview step shows parsed transactions and the execute step creates transaction records.

**Subtasks:**
- [ ] 1.1 — In `frontend/src/pages/Portfolio/Holdings/ImportModal.tsx`, add import type state and IBKR broker option:
  ```tsx
  type ImportType = 'positions' | 'transactions';
  type Broker = 'generic' | 'fidelity' | 'schwab' | 'ibkr';

  const BROKERS: { value: Broker; label: string }[] = [
    { value: 'generic', label: 'Generic CSV' },
    { value: 'fidelity', label: 'Fidelity' },
    { value: 'schwab', label: 'Schwab' },
    { value: 'ibkr', label: 'Interactive Brokers' },
  ];

  const [importType, setImportType] = useState<ImportType>('positions');
  ```

- [ ] 1.2 — In step 1 UI, add an import type toggle before the broker selector:
  ```tsx
  <div className={styles.importTypeToggle}>
    <button className={importType === 'positions' ? styles.typeActive : styles.typeBtn}
      onClick={() => setImportType('positions')}>Current Positions</button>
    <button className={importType === 'transactions' ? styles.typeActive : styles.typeBtn}
      onClick={() => setImportType('transactions')}>Transactions</button>
  </div>
  ```

- [ ] 1.3 — Update `handlePreview` to use the correct endpoint based on import type:
  ```tsx
  const endpoint = importType === 'transactions'
    ? '/api/v1/portfolio/import/transactions/preview'
    : '/api/v1/portfolio/import/preview';
  const data = await api.post(endpoint, { csv_content: content, broker });
  ```

- [ ] 1.4 — In the preview step (step 3), render differently based on import type:
  - Positions: existing preview table (ticker, shares, cost basis)
  - Transactions: new table showing Date, Type (BUY/SELL badge), Ticker, Shares, Price, Fees

- [ ] 1.5 — Update `handleExecute` similarly:
  ```tsx
  const endpoint = importType === 'transactions'
    ? '/api/v1/portfolio/import/transactions/execute'
    : '/api/v1/portfolio/import/execute';
  ```

- [ ] 1.6 — Accept an optional `defaultImportType` prop so the Transactions tab (session 10F) can open the modal pre-configured:
  ```tsx
  interface Props {
    onClose: () => void;
    onSuccess: () => void;
    defaultImportType?: ImportType;
  }
  ```
  Initialize `importType` from `defaultImportType ?? 'positions'`.

- [ ] 1.7 — In `ImportModal.module.css`, add import type toggle styles.

---

### Task 2: Column Mapping Fallback UI
**Description:** When the generic CSV parser can't auto-detect columns, show a mapping interface where the user assigns CSV columns to internal fields.

**Subtasks:**
- [ ] 2.1 — In `ImportModal.tsx`, detect when the preview response indicates auto-detection failed (e.g., `success: false` with unmatched columns in the error):
  ```tsx
  const [showMapping, setShowMapping] = useState(false);
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [columnMap, setColumnMap] = useState<Record<string, string>>({});
  ```

- [ ] 2.2 — When auto-detection fails, extract CSV headers from the first row and show the mapping UI:
  ```tsx
  {showMapping && (
    <div className={styles.mappingSection}>
      <p>We couldn't auto-detect your CSV format. Please map the columns:</p>
      <div className={styles.mappingGrid}>
        {csvHeaders.map((header) => (
          <div key={header} className={styles.mappingRow}>
            <span className={styles.csvHeader}>"{header}"</span>
            <span className={styles.mappingArrow}>→</span>
            <select value={columnMap[header] ?? ''} onChange={(e) =>
              setColumnMap({ ...columnMap, [header]: e.target.value })
            }>
              <option value="">Skip</option>
              <option value="ticker">Ticker</option>
              <option value="shares">Shares</option>
              <option value="cost_basis">Cost Basis</option>
              <option value="date_acquired">Date Acquired</option>
              <option value="account">Account</option>
              <option value="name">Company Name</option>
            </select>
          </div>
        ))}
      </div>
      <button onClick={handlePreviewWithMapping}>Preview with this mapping</button>
    </div>
  )}
  ```

- [ ] 2.3 — `handlePreviewWithMapping` sends the column mapping to a modified preview endpoint (or sends the raw CSV + mapping and lets the backend apply it).

- [ ] 2.4 — In `ImportModal.module.css`, add mapping section styles.

---

### Task 3: Context Menu Viewport Overflow Fix
**Description:** Fix the context menu in both Portfolio HoldingsTable and Scanner ResultsTable to detect when it would overflow the viewport and flip its position.

**Subtasks:**
- [ ] 3.1 — In `frontend/src/pages/Scanner/ResultsTable/ContextMenu.tsx`, add a ref and viewport boundary detection:
  ```tsx
  const menuRef = useRef<HTMLDivElement>(null);
  const [adjustedPos, setAdjustedPos] = useState({ x, y });

  useEffect(() => {
    if (!menuRef.current) return;
    const rect = menuRef.current.getBoundingClientRect();
    let newX = x;
    let newY = y;
    if (y + rect.height > window.innerHeight) {
      newY = y - rect.height;  // flip upward
    }
    if (x + rect.width > window.innerWidth) {
      newX = x - rect.width;  // flip leftward
    }
    setAdjustedPos({ x: newX, y: newY });
  }, [x, y]);
  ```
  Use `adjustedPos` in the style: `style={{ left: adjustedPos.x, top: adjustedPos.y }}`.

- [ ] 3.2 — The Portfolio HoldingsTable renders its own inline context menu (not a separate component file). Apply the same ref-based boundary detection to the context menu rendered in `HoldingsTable.tsx`. If the context menu is inline JSX, extract it to a shared pattern or apply the same useRef + useEffect logic.

- [ ] 3.3 — Add "Company Info" and "Edit Position" to the Portfolio context menu options (for Task 5 and Task 4).

---

### Task 4: Company Info Hover Card
**Description:** A floating info card that appears when hovering over a ticker cell in the holdings table for 500ms. Shows key company metrics from cached market data.

**Subtasks:**
- [ ] 4.1 — Create `frontend/src/pages/Portfolio/Holdings/CompanyInfoCard.tsx`:
  ```tsx
  interface CompanyInfoCardProps {
    ticker: string;
    x: number;
    y: number;
    onClose: () => void;
  }
  ```
  The card fetches data from `GET /api/v1/companies/{ticker}/quick-info` (or combines existing quote + profile data). Renders: ticker + name, sector + industry, then a grid of metrics (Market Cap, P/E, EV/EBITDA, Revenue Growth, Op Margin, Dividend Yield, Beta, 52W Range). Footer: "Open in Research →" link.

- [ ] 4.2 — Create `frontend/src/pages/Portfolio/Holdings/CompanyInfoCard.module.css` — floating dark card with subtle border, shadow, z-index above table.

- [ ] 4.3 — In `HoldingsTable.tsx`, add hover tracking on ticker cells:
  ```tsx
  const [hoverCard, setHoverCard] = useState<{ ticker: string; x: number; y: number } | null>(null);
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  const handleTickerMouseEnter = (ticker: string, e: React.MouseEvent) => {
    const rect = (e.target as HTMLElement).getBoundingClientRect();
    hoverTimerRef.current = setTimeout(() => {
      setHoverCard({ ticker, x: rect.right + 8, y: rect.top });
    }, 500);
  };

  const handleTickerMouseLeave = () => {
    clearTimeout(hoverTimerRef.current);
    // Grace period: don't close immediately (200ms)
    setTimeout(() => {
      setHoverCard(null);
    }, 200);
  };
  ```

- [ ] 4.4 — Render the `CompanyInfoCard` when `hoverCard` is set:
  ```tsx
  {hoverCard && (
    <CompanyInfoCard
      ticker={hoverCard.ticker}
      x={hoverCard.x}
      y={hoverCard.y}
      onClose={() => setHoverCard(null)}
    />
  )}
  ```

- [ ] 4.5 — Apply viewport boundary detection to the card position (same pattern as context menu — flip left/up if near edge).

- [ ] 4.6 — The card itself should be hoverable — if user moves mouse into the card, it stays open. Use `onMouseEnter`/`onMouseLeave` on the card to manage this.

---

### Task 5: Edit Position Modal
**Description:** A modal pre-populated with current position data for inline editing. Accessible from PositionDetail and context menu.

**Subtasks:**
- [ ] 5.1 — Create `frontend/src/pages/Portfolio/Holdings/EditPositionModal.tsx`:
  ```tsx
  interface Props {
    position: Position;
    onClose: () => void;
    onSuccess: () => void;
  }
  ```
  Pre-populate form with: `position.shares_held`, `position.cost_basis_per_share`, `position.account`, `position.date_acquired`, `position.notes`. On save, PUT to `/api/v1/portfolio/positions/${position.id}` with only changed fields.

- [ ] 5.2 — Show lots as editable rows if position has multiple lots:
  ```tsx
  {lots.map((lot) => (
    <div className={styles.lotRow}>
      <input value={lot.shares} onChange={...} />
      <input value={lot.cost_basis_per_share} onChange={...} />
      <span>{lot.date_acquired}</span>
    </div>
  ))}
  ```
  Each lot saves independently via `PUT /api/v1/portfolio/lots/${lot.id}`.

- [ ] 5.3 — Create `EditPositionModal.module.css` — similar styling to AddPositionModal.

- [ ] 5.4 — In `PositionDetail.tsx`, add an "Edit" button next to "Record Transaction":
  ```tsx
  <button className={styles.editBtn} onClick={() => onEditPosition(position)}>
    Edit Position
  </button>
  ```
  Add `onEditPosition` to the Props interface and pass through from HoldingsTable.

- [ ] 5.5 — In `HoldingsTable.tsx`, wire up the edit modal:
  ```tsx
  const [editingPosition, setEditingPosition] = useState<Position | null>(null);
  ```
  Render when set:
  ```tsx
  {editingPosition && (
    <EditPositionModal
      position={editingPosition}
      onClose={() => setEditingPosition(null)}
      onSuccess={() => { setEditingPosition(null); onRefresh(); }}
    />
  )}
  ```

- [ ] 5.6 — Add "Edit Position" to the context menu (Task 3.3).

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: ImportModal has "Current Positions" / "Transactions" toggle in step 1.
- [ ] AC-2: IBKR added as a 4th broker option.
- [ ] AC-3: Transaction import uses correct preview/execute endpoints.
- [ ] AC-4: Transaction preview shows Date, Type, Ticker, Shares, Price, Fees.
- [ ] AC-5: Column mapping UI shown when generic parser auto-detection fails.
- [ ] AC-6: Column mapping lets user assign CSV columns to internal fields.
- [ ] AC-7: `defaultImportType` prop allows pre-selecting Transactions mode.
- [ ] AC-8: Scanner ContextMenu flips upward when near bottom of viewport.
- [ ] AC-9: Scanner ContextMenu flips leftward when near right edge.
- [ ] AC-10: Portfolio context menu has same overflow fix.
- [ ] AC-11: Company info hover card appears after 500ms hover on ticker cell.
- [ ] AC-12: Hover card shows: ticker, name, sector, industry, Market Cap, P/E, EV/EBITDA, Revenue Growth, Op Margin, Dividend Yield, Beta, 52W Range.
- [ ] AC-13: Hover card has "Open in Research →" link.
- [ ] AC-14: Hover card flips position when near viewport edges.
- [ ] AC-15: Hover card stays open when mouse moves into the card.
- [ ] AC-16: EditPositionModal pre-populated with current position data.
- [ ] AC-17: Edit saves via PUT, only changed fields sent (partial update).
- [ ] AC-18: Lot-level editing for multi-lot positions.
- [ ] AC-19: Edit accessible from PositionDetail "Edit" button and context menu.
- [ ] AC-20: Holdings table refreshes after successful edit.
- [ ] AC-21: "Company Info" and "Edit Position" added to Portfolio context menu.
- [ ] AC-22: No regressions on existing import, context menu, or holdings functionality.

---

## FILES TOUCHED

**New files:**
- `frontend/src/pages/Portfolio/Holdings/CompanyInfoCard.tsx` — hover card component
- `frontend/src/pages/Portfolio/Holdings/CompanyInfoCard.module.css` — hover card styles
- `frontend/src/pages/Portfolio/Holdings/EditPositionModal.tsx` — edit modal
- `frontend/src/pages/Portfolio/Holdings/EditPositionModal.module.css` — edit modal styles

**Modified files:**
- `frontend/src/pages/Portfolio/Holdings/ImportModal.tsx` — import type toggle, IBKR broker, transaction flow, column mapping UI, `defaultImportType` prop
- `frontend/src/pages/Portfolio/Holdings/ImportModal.module.css` — type toggle, mapping section styles
- `frontend/src/pages/Portfolio/Holdings/HoldingsTable.tsx` — hover card trigger, edit modal wiring, context menu additions (Company Info + Edit)
- `frontend/src/pages/Portfolio/Holdings/HoldingsTable.module.css` — hover trigger styles
- `frontend/src/pages/Portfolio/Holdings/PositionDetail.tsx` — add Edit button, `onEditPosition` prop
- `frontend/src/pages/Scanner/ResultsTable/ContextMenu.tsx` — viewport overflow fix (ref + boundary detection)
- `frontend/src/pages/Scanner/ResultsTable/ContextMenu.module.css` — no changes needed (positioning is inline style)

---

## BUILDER PROMPT

> **Session 10B — Holdings Frontend (Import UX, Context Menu, Hover Card, Edit Position)**
>
> You are building session 10B of the Finance App v2.0 update.
>
> **What you're doing:** Five things: (1) ImportModal upgrade with Positions/Transactions toggle + IBKR broker + column mapping fallback, (2) Context menu viewport overflow fix for both Portfolio and Scanner, (3) Company info hover card on ticker cells, (4) EditPositionModal for inline editing, (5) Wire everything into HoldingsTable and context menu.
>
> **Context:** Session 10A built the backend: broker-specific CSV parsers, transaction import endpoints, position/lot PUT endpoints. The frontend ImportModal currently only supports position import with 3 brokers. Context menus clip when near viewport edges. There's no way to hover for company info or edit positions inline.
>
> **Existing code:**
>
> `ImportModal.tsx` (at `frontend/src/pages/Portfolio/Holdings/ImportModal.tsx`):
> - Props: `onClose`, `onSuccess`
> - State: `step` (1-4), `broker` ('generic'|'fidelity'|'schwab'), `content`, `preview`, `result`, `error`, `loading`
> - 3 brokers: Generic, Fidelity, Schwab — **add IBKR**
> - Steps: 1=Select broker + paste/upload CSV → 2=unused → 3=Preview table → 4=Results
> - `handlePreview` posts to `/api/v1/portfolio/import/preview`
> - `handleExecute` posts to `/api/v1/portfolio/import/execute`
> - No import type toggle (only positions), no column mapping
>
> `ContextMenu.tsx` (Scanner, at `frontend/src/pages/Scanner/ResultsTable/ContextMenu.tsx`):
> - Props: `x`, `y`, `ticker`, `onClose`
> - Renders overlay + menu div at `style={{ left: x, top: y }}` — **no boundary detection**
> - Items: Open in Model Builder, Open in Research, Add to Watchlist, Copy Ticker
>
> `HoldingsTable.tsx` (at `frontend/src/pages/Portfolio/Holdings/HoldingsTable.tsx`):
> - Props: `positions`, `expandedId`, `onExpand`, `onRecordTx`, `onRefresh`
> - State: `sortKey`, `sortDir`, `groupBy`, `ctxMenu` ({x, y, position}), `impliedPrices`
> - Context menu is rendered inline (not a separate component) — it uses `ctxMenu` state
> - No hover card, no edit modal wiring
>
> `PositionDetail.tsx` (at `frontend/src/pages/Portfolio/Holdings/PositionDetail.tsx`):
> - Props: `position`, `onRecordTx`
> - Shows: lots table, transaction history table, buttons for Record Transaction
> - No Edit button
>
> `AddPositionModal.tsx` exists — use similar styling/pattern for EditPositionModal.
>
> **Cross-cutting rules:**
> - Display Name Rule: Use `displayNames.ts` for any backend keys shown in UI.
> - Chart Quality: Fidelity-level information density.
> - Data Format: Ratios/percentages as decimal ratios.
>
> **Task 1: ImportModal Upgrade**
> - Add `ImportType` toggle: "Current Positions" / "Transactions"
> - Add IBKR as 4th broker
> - Route preview/execute to correct endpoint based on importType
> - Transaction preview: table with Date, Type badge, Ticker, Shares, Price, Fees
> - Accept `defaultImportType` prop for pre-selection from Transactions tab
>
> **Task 2: Column Mapping Fallback**
> - Detect auto-detection failure from preview response
> - Show mapping UI: CSV column → dropdown (Ticker/Shares/Cost Basis/Date/Account/Skip)
> - Re-preview with mapping applied
>
> **Task 3: Context Menu Overflow Fix**
> - Scanner ContextMenu: add `menuRef`, measure rendered height via `useEffect`, flip if exceeds viewport
> - Portfolio HoldingsTable: apply same fix to inline context menu
> - Add "Company Info" and "Edit Position" to Portfolio context menu
>
> **Task 4: Company Info Hover Card**
> - New `CompanyInfoCard` component: fetches quick company data, renders floating card
> - 500ms delay on ticker cell hover, 200ms grace period on leave
> - Card is hoverable (stays open when mouse enters card)
> - Viewport boundary detection (flip if near edge)
> - Content: ticker+name, sector+industry, 8 metrics, "Open in Research" link
>
> **Task 5: EditPositionModal**
> - Pre-populated from position data
> - Saves via `PUT /positions/{id}` (partial update, only changed fields)
> - Shows lot-level editing for multi-lot positions (`PUT /lots/{lot_id}`)
> - Accessible from PositionDetail "Edit" button + context menu "Edit Position"
> - Refreshes holdings on success
>
> **Acceptance criteria:**
> 1. Import type toggle + IBKR broker
> 2. Transaction preview/execute use correct endpoints
> 3. Column mapping shown on auto-detect failure
> 4. Context menus flip when near viewport edges (both modules)
> 5. Hover card appears after 500ms, shows metrics, stays on mouse-in
> 6. Edit modal pre-populated, partial PUT, lot editing
> 7. Edit accessible from detail row + context menu
> 8. No regressions
>
> **Files to create:** `CompanyInfoCard.tsx/css`, `EditPositionModal.tsx/css`
> **Files to modify:** `ImportModal.tsx/css`, `HoldingsTable.tsx/css`, `PositionDetail.tsx`, Scanner `ContextMenu.tsx`
>
> **Technical constraints:**
> - CSS modules for all styling
> - `api.get<T>` / `api.post<T>` / `api.put<T>` for data fetching
> - `useRef` + `useEffect` for context menu/hover card boundary detection
> - `setTimeout` with 500ms delay for hover, 200ms grace on leave
> - Position types from `../types` (Position, Lot interfaces)
> - `navigationService.goToResearch(ticker)` for "Open in Research" link
> - AddPositionModal pattern: modal overlay, form fields, Save/Cancel buttons
> - Partial update: `body.model_dump(exclude_none=True)` pattern on backend, send only changed fields from frontend
