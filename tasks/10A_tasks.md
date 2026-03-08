# Session 10A — CSV Import + Edit Position Backend
## Phase 10: Portfolio

**Priority:** Normal
**Type:** Backend Only
**Depends On:** None
**Spec Reference:** `specs/phase10_portfolio_holdings.md` → Areas 1A, 1B backend, 4B

---

## SCOPE SUMMARY

Create broker-specific CSV parsers (Fidelity, Schwab, IBKR, Generic) for portfolio position and transaction imports with clear error messages. Add transaction import endpoints (preview + execute). Add position and lot update endpoints for inline editing.

---

## TASKS

### Task 1: Broker-Specific CSV Parsers
**Description:** Create a dedicated CSV import module with parsers for Fidelity, Schwab, Interactive Brokers, and a flexible Generic parser that auto-detects common column name variants.

**Subtasks:**
- [ ] 1.1 — Create or refactor `backend/services/portfolio/csv_import.py` with a base parser and per-broker implementations:
  ```python
  from __future__ import annotations
  import csv
  import io
  import logging
  from dataclasses import dataclass, field

  logger = logging.getLogger("finance_app")

  @dataclass
  class ParsedPosition:
      ticker: str
      shares: float
      cost_basis_per_share: float | None = None
      account: str | None = None
      date_acquired: str | None = None
      company_name: str | None = None

  @dataclass
  class ParsedTransaction:
      date: str
      type: str  # BUY, SELL, DIVIDEND
      ticker: str
      shares: float
      price: float
      fees: float = 0.0
      account: str | None = None

  @dataclass
  class ParseResult:
      success: bool
      positions: list[ParsedPosition] = field(default_factory=list)
      transactions: list[ParsedTransaction] = field(default_factory=list)
      errors: list[str] = field(default_factory=list)
      warnings: list[str] = field(default_factory=list)
      row_count: int = 0
      skipped_count: int = 0
  ```

- [ ] 1.2 — Add Fidelity parser:
  - Expected headers: "Account Name/Number", "Symbol", "Description", "Quantity", "Last Price", "Current Value", "Cost Basis Total", "Average Cost Basis"
  - Map: Symbol → ticker, Quantity → shares, Average Cost Basis → cost_basis_per_share, Account Name/Number → account
  - Handle quirks: Fidelity includes a summary row at the bottom (where Symbol is empty or "Total") — skip it
  - Handle "Pending Activity" rows — skip them
  - Return clear error if headers don't match: "Expected Fidelity format but found columns: X, Y, Z. Try 'Generic CSV'."

- [ ] 1.3 — Add Schwab parser:
  - Expected headers: "Symbol", "Description", "Quantity", "Price", "Market Value", "Cost Basis", "Gain/Loss"
  - Map: Symbol → ticker, Quantity → shares, Cost Basis / Quantity → cost_basis_per_share
  - Handle: Schwab date format may differ

- [ ] 1.4 — Add IBKR parser:
  - Expected headers vary by report type. Common: "Symbol", "Position", "Avg Price", "Market Price", "Market Value"
  - IBKR CSVs have multi-section format (header row may say "Trades" or "Open Positions") — detect section headers and parse the right section
  - Map appropriately per section type

- [ ] 1.5 — Add Generic parser with auto-detection:
  ```python
  COLUMN_ALIASES = {
      "ticker": ["symbol", "ticker", "stock symbol", "stock", "instrument"],
      "shares": ["quantity", "qty", "shares", "position", "amount"],
      "cost_basis": ["cost basis", "avg cost", "average cost basis", "price paid", "avg price", "cost basis total"],
      "account": ["account", "acct", "account name", "account number", "account name/number"],
      "date": ["date", "date acquired", "purchase date", "trade date"],
      "name": ["description", "company name", "name", "security name"],
  }
  ```
  Auto-detect by checking each CSV header against aliases (case-insensitive). If auto-detection fails, return `success=False` with a message listing unmatched columns and suggesting manual mapping.

- [ ] 1.6 — Add a dispatcher function:
  ```python
  def parse_csv(content: str, broker: str, import_type: str = "positions") -> ParseResult:
      """Parse CSV content using the specified broker format."""
      if import_type == "transactions":
          return _parse_transactions(content, broker)
      parsers = {
          "fidelity": _parse_fidelity,
          "schwab": _parse_schwab,
          "ibkr": _parse_ibkr,
          "generic": _parse_generic,
      }
      parser = parsers.get(broker, _parse_generic)
      return parser(content)
  ```

---

### Task 2: Transaction Import Endpoints
**Description:** Add preview and execute endpoints for transaction CSV import. The preview parses and returns parsed transactions for user review. The execute creates transaction records and updates positions/lots.

**Subtasks:**
- [ ] 2.1 — In `backend/routers/portfolio_router.py`, add transaction import preview:
  ```python
  @router.post("/import/transactions/preview")
  async def preview_transaction_import(request: Request, body: ImportPreviewBody):
      from services.portfolio.csv_import import parse_csv
      result = parse_csv(body.csv_content, body.broker, import_type="transactions")
      return success_response(data={
          "success": result.success,
          "transactions": [t.__dict__ for t in result.transactions],
          "errors": result.errors,
          "warnings": result.warnings,
          "row_count": result.row_count,
          "skipped_count": result.skipped_count,
      })
  ```

- [ ] 2.2 — Add transaction import execute:
  ```python
  @router.post("/import/transactions/execute")
  async def execute_transaction_import(request: Request, body: ImportExecuteBody):
      svc: PortfolioService = request.app.state.portfolio_service
      results = await svc.import_transactions(body.transactions)
      return success_response(data=results)
  ```

- [ ] 2.3 — In `backend/services/portfolio/portfolio_service.py`, add `import_transactions()`:
  ```python
  async def import_transactions(self, transactions: list[dict]) -> dict:
      """Process a batch of imported transactions through the lot engine."""
      created = 0
      failed = 0
      for tx in transactions:
          try:
              await self.record_transaction(TransactionCreate(
                  ticker=tx["ticker"],
                  type=tx["type"],
                  shares=tx["shares"],
                  price=tx["price"],
                  fees=tx.get("fees", 0),
                  date=tx.get("date"),
                  account=tx.get("account"),
              ))
              created += 1
          except Exception as exc:
              logger.warning("Failed to import transaction: %s — %s", tx, exc)
              failed += 1
      return {"created": created, "failed": failed, "total": len(transactions)}
  ```

- [ ] 2.4 — Add request models for the import endpoints:
  ```python
  class ImportPreviewBody(BaseModel):
      csv_content: str
      broker: str = "generic"

  class ImportExecuteBody(BaseModel):
      transactions: list[dict]
  ```

---

### Task 3: Position and Lot Update Endpoints
**Description:** Add PUT endpoints for editing positions and individual lots.

**Subtasks:**
- [ ] 3.1 — In `backend/routers/portfolio_router.py`, add position update:
  ```python
  class UpdatePositionBody(BaseModel):
      shares: float | None = None
      cost_basis_per_share: float | None = None
      account: str | None = None
      date_acquired: str | None = None
      notes: str | None = None

  @router.put("/positions/{position_id}")
  async def update_position(position_id: int, body: UpdatePositionBody, request: Request):
      svc: PortfolioService = request.app.state.portfolio_service
      result = await svc.update_position(position_id, body.model_dump(exclude_none=True))
      if not result:
          return error_response("NOT_FOUND", f"Position {position_id} not found")
      return success_response(data=result)
  ```

- [ ] 3.2 — Add lot update:
  ```python
  class UpdateLotBody(BaseModel):
      shares: float | None = None
      cost_basis_per_share: float | None = None
      date_acquired: str | None = None

  @router.put("/lots/{lot_id}")
  async def update_lot(lot_id: int, body: UpdateLotBody, request: Request):
      svc: PortfolioService = request.app.state.portfolio_service
      result = await svc.update_lot(lot_id, body.model_dump(exclude_none=True))
      if not result:
          return error_response("NOT_FOUND", f"Lot {lot_id} not found")
      return success_response(data=result)
  ```

- [ ] 3.3 — In `backend/services/portfolio/portfolio_service.py`, add:
  ```python
  async def update_position(self, position_id: int, updates: dict) -> dict | None:
      """Partial update of a position."""
      return await self.repo.update_position(position_id, updates)

  async def update_lot(self, lot_id: int, updates: dict) -> dict | None:
      """Partial update of a single lot."""
      return await self.repo.update_lot(lot_id, updates)
  ```

- [ ] 3.4 — In `backend/repositories/portfolio_repo.py`, add update methods:
  ```python
  async def update_position(self, position_id: int, data: dict) -> dict | None:
      fields = [f"{k} = ?" for k in data if k != "id"]
      values = [data[k] for k in data if k != "id"]
      if not fields:
          return await self.get_position(position_id)
      values.append(position_id)
      await self.db.execute(
          f"UPDATE portfolio_positions SET {', '.join(fields)} WHERE id = ?",
          tuple(values),
      )
      await self.db.commit()
      return await self.get_position(position_id)

  async def update_lot(self, lot_id: int, data: dict) -> dict | None:
      fields = [f"{k} = ?" for k in data if k != "id"]
      values = [data[k] for k in data if k != "id"]
      if not fields:
          return await self.get_lot(lot_id)
      values.append(lot_id)
      await self.db.execute(
          f"UPDATE portfolio_lots SET {', '.join(fields)} WHERE id = ?",
          tuple(values),
      )
      await self.db.commit()
      return await self.get_lot(lot_id)
  ```
  Verify `get_position(id)` and `get_lot(id)` methods exist; add if not.

- [ ] 3.5 — Add validation in the service layer:
  ```python
  if "shares" in updates and updates["shares"] <= 0:
      raise ValueError("Shares must be positive")
  if "cost_basis_per_share" in updates and updates["cost_basis_per_share"] <= 0:
      raise ValueError("Cost basis must be positive")
  ```

---

## ACCEPTANCE CRITERIA

- [ ] AC-1: Fidelity CSV parser correctly maps Symbol, Quantity, Average Cost Basis, Account columns.
- [ ] AC-2: Fidelity parser skips summary/total rows and "Pending Activity" rows.
- [ ] AC-3: Schwab CSV parser correctly maps its specific column headers.
- [ ] AC-4: IBKR CSV parser handles multi-section format, extracting Open Positions.
- [ ] AC-5: Generic parser auto-detects common column aliases (case-insensitive).
- [ ] AC-6: Parser returns clear error message when headers don't match expected broker format.
- [ ] AC-7: Generic parser returns unmatched columns when auto-detection fails (for column mapping UI).
- [ ] AC-8: `POST /import/transactions/preview` parses transaction CSV and returns parsed transactions.
- [ ] AC-9: `POST /import/transactions/execute` creates transaction records via lot engine.
- [ ] AC-10: Transaction import processes BUY/SELL/DIVIDEND types correctly through existing lot engine.
- [ ] AC-11: `PUT /positions/{id}` accepts partial updates (shares, cost_basis, account, date_acquired, notes).
- [ ] AC-12: `PUT /lots/{lot_id}` accepts partial lot updates (shares, cost_basis, date_acquired).
- [ ] AC-13: Validation: shares > 0, cost_basis > 0.
- [ ] AC-14: Existing CSV position import still works (no regressions).
- [ ] AC-15: IBKR added as a 4th broker option.

---

## FILES TOUCHED

**New files:**
- None (csv_import.py may already exist — refactor if so, create if not)

**Modified files:**
- `backend/services/portfolio/csv_import.py` — broker-specific parsers (Fidelity, Schwab, IBKR, Generic), transaction parsing, `parse_csv()` dispatcher
- `backend/routers/portfolio_router.py` — transaction import preview/execute endpoints, position/lot PUT endpoints, request models
- `backend/services/portfolio/portfolio_service.py` — `import_transactions()`, `update_position()`, `update_lot()`
- `backend/repositories/portfolio_repo.py` — `update_position()`, `update_lot()` methods

---

## BUILDER PROMPT

> **Session 10A — CSV Import + Edit Position Backend**
>
> You are building session 10A of the Finance App v2.0 update.
>
> **What you're doing:** Three backend features: (1) Broker-specific CSV parsers for Fidelity, Schwab, IBKR, and a flexible Generic parser, (2) Transaction import endpoints (preview + execute), (3) Position and lot update endpoints for inline editing.
>
> **Context:** The current CSV import can only import positions (not transactions) and the parser likely can't handle actual broker CSV formats. There's also no way to edit a position without deleting and re-adding it.
>
> **Existing code:**
>
> `csv_import.py` (at `backend/services/portfolio/csv_import.py` — may or may not exist):
> - If it exists, it has a basic parser. Refactor to support multiple brokers.
> - If it doesn't exist, create it fresh.
>
> `portfolio_router.py` (at `backend/routers/portfolio_router.py`):
> - Has existing position import endpoints: `POST /import/preview`, `POST /import/execute`
> - Has `POST /positions` for adding positions, `DELETE /positions/{id}`
> - Uses `PortfolioService` via `request.app.state.portfolio_service`
> - Pattern: Pydantic `BaseModel` for request bodies, `success_response(data=...)` / `error_response(code, msg)`
>
> `portfolio_service.py` (at `backend/services/portfolio/portfolio_service.py`):
> - `PortfolioService.__init__(db, portfolio_repo, account_repo, transaction_repo, alert_repo, market_data_svc)`
> - Has `record_transaction(TransactionCreate)` — creates transaction and updates lots via `LotEngine`
> - Has `add_position(PositionCreate)` — creates a position record
> - Does NOT have `update_position()`, `update_lot()`, or `import_transactions()`
>
> `portfolio_repo.py` (at `backend/repositories/portfolio_repo.py`):
> - Has `get_all_positions()`, `get_position(id)`, `create_position()`, `delete_position()`
> - Has lot methods: `get_lots_for_position()`, `create_lot()`
> - Does NOT have `update_position()` or `update_lot()`
>
> **Cross-cutting rules:**
> - Data Format: All ratios/percentages as decimal ratios.
>
> **Task 1: Broker-Specific CSV Parsers**
> - Create `ParsedPosition`, `ParsedTransaction`, `ParseResult` dataclasses
> - Fidelity: maps Symbol/Quantity/Average Cost Basis/Account Name, skips summary rows
> - Schwab: maps Symbol/Quantity/Cost Basis/Price
> - IBKR: handles multi-section CSV, extracts Open Positions section
> - Generic: auto-detect via `COLUMN_ALIASES` dict (case-insensitive matching), return unmatched columns on failure
> - Dispatcher: `parse_csv(content, broker, import_type)` routes to correct parser
>
> **Task 2: Transaction Import Endpoints**
> - `POST /import/transactions/preview` — parse CSV, return parsed transactions
> - `POST /import/transactions/execute` — process through lot engine
> - Service method: `import_transactions(transactions)` iterates and calls `record_transaction()` per item
>
> **Task 3: Position/Lot Update Endpoints**
> - `PUT /positions/{id}` — partial update (shares, cost_basis, account, date_acquired, notes)
> - `PUT /lots/{lot_id}` — partial lot update
> - Validation: shares > 0, cost_basis > 0
> - Repo methods: dynamic UPDATE from dict
>
> **Acceptance criteria:**
> 1. Fidelity/Schwab/IBKR parsers handle their formats
> 2. Generic parser auto-detects common column names
> 3. Clear errors on format mismatch
> 4. Transaction import preview/execute work
> 5. Position/lot PUT endpoints work with partial updates
> 6. Validation enforced
> 7. No regressions on existing import
>
> **Files to create:** None (or `csv_import.py` if it doesn't exist)
> **Files to modify:** `csv_import.py`, `portfolio_router.py`, `portfolio_service.py`, `portfolio_repo.py`
>
> **Technical constraints:**
> - Python `csv` module for parsing
> - Pydantic `BaseModel` for request validation
> - `TransactionCreate` model from `services/portfolio/models.py`
> - `LotEngine` processes sells via FIFO/LIFO
> - Partial update pattern: dict comprehension excluding None values
> - Error pattern: `success_response` / `error_response` from `models.response`
